"""Adoption assessment entry point.

Measures whether each area of the Databricks platform is used at all.

    # from a laptop - SQL warehouse, no cluster, no pyspark
    python -m datavail_assessment.adoption.run --profile P --warehouse-id W

    # inside a workspace job - Spark on serverless
    python -m datavail_assessment.adoption.run --spark

Add --dry-run to score everything and print, writing nothing.
"""

from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timedelta, timezone

from datavail_assessment.adoption import checks as checks_mod
from datavail_assessment.adoption import scoring
from datavail_assessment.core.sqlutil import lit, split_sql

RESULTS_TABLE = "adoption_check_history"
SECTION_TABLE = "adoption_section_score"

DDL = """
CREATE TABLE IF NOT EXISTS {base}.adoption_check_history (
  run_id     STRING    COMMENT 'Unique run identifier',
  run_ts     TIMESTAMP COMMENT 'When the adoption check ran',
  section    STRING    COMMENT 'Workspace | SQL | Data Engineering | AI/ML',
  check_id   STRING    COMMENT 'Check number, e.g. 1.1, 2.5, 4.12',
  check_name STRING    COMMENT 'Human-readable check name',
  raw_value  DOUBLE    COMMENT 'Measured value behind the score',
  score      INT       COMMENT '0 = NONE, 1 = MINIMAL, 2 = ACTIVE',
  label      STRING    COMMENT 'NONE | MINIMAL | ACTIVE',
  detail     STRING    COMMENT 'Supporting evidence, where a check has any',
  error      STRING    COMMENT 'Why a check could not be measured; NULL when it was'
)
USING DELTA
COMMENT 'Per-check adoption scores, one row per check per run.';

CREATE TABLE IF NOT EXISTS {base}.adoption_section_score (
  run_id        STRING    COMMENT 'Run this rollup belongs to',
  run_ts        TIMESTAMP COMMENT 'When the adoption check ran',
  section       STRING    COMMENT 'Section name, or OVERALL for the weighted total',
  points        INT       COMMENT 'Points scored, two per ACTIVE check',
  max_points    INT       COMMENT 'Points available in this section',
  score_pct     DOUBLE    COMMENT 'points / max_points as a percentage',
  grade         STRING    COMMENT 'NOT ADOPTED | EARLY | DEVELOPING | STRONG',
  active_count  INT       COMMENT 'Checks scoring 2',
  minimal_count INT       COMMENT 'Checks scoring 1',
  none_count    INT       COMMENT 'Checks scoring 0',
  weight        DOUBLE    COMMENT 'Section weight in the overall score'
)
USING DELTA
COMMENT 'Per-section adoption rollup, plus one OVERALL row per run.';
"""


def ensure_columns(executor, fqn: str, wanted: dict[str, str]) -> None:
    """Add any missing columns to an existing table, additively."""
    try:
        have = {r["col_name"].lower() for r in executor.query(f"DESCRIBE TABLE {fqn}")
                if r.get("col_name") and not r["col_name"].startswith("#")}
    except Exception:  # noqa: BLE001 - table is new, CREATE already handled it
        return
    missing = [(c, t) for c, t in wanted.items() if c.lower() not in have]
    for col, coltype in missing:
        executor.execute(f"ALTER TABLE {fqn} ADD COLUMN {col} {coltype}")
        print(f"  added missing column {fqn}.{col}")


def scalar(executor, sql: str, params: dict):
    """First column of the first row, or an error string."""
    try:
        rows = executor.query(sql.format(**params))
    except Exception as exc:  # noqa: BLE001 - reported per check, never fatal
        return None, f"{type(exc).__name__}: {exc}"[:400]
    if not rows:
        return 0.0, None
    v = list(rows[0].values())[0]
    return (0.0 if v is None else float(v)), None


def run_checks(executor, params: dict) -> list[dict]:
    """Score all 51 checks. A failed query is recorded, not raised."""
    out = []

    for cid, c in checks_mod.CHECKS.items():
        value, err = scalar(executor, c["sql"], params)
        if err:
            out.append({"check_id": cid, "section": c["section"], "check_name": c["name"],
                        "raw_value": None, "score": 0, "label": "NONE",
                        "detail": None, "error": err})
            continue
        score = scoring.score_thresholds(value, c["minimal"], c["active"])
        out.append({"check_id": cid, "section": c["section"], "check_name": c["name"],
                    "raw_value": value, "score": score,
                    "label": scoring.LABELS[score], "detail": None, "error": None})

    for cid, c in checks_mod.COMPOUND_CHECKS.items():
        vals, err = {}, None
        for key, sql in c["queries"].items():
            v, e = scalar(executor, sql, params)
            if e:
                err = e
                break
            vals[key] = v
        if err:
            out.append({"check_id": cid, "section": c["section"], "check_name": c["name"],
                        "raw_value": None, "score": 0, "label": "NONE",
                        "detail": None, "error": err})
            continue
        value, score, detail = c["combine"](vals)
        out.append({"check_id": cid, "section": c["section"], "check_name": c["name"],
                    "raw_value": float(value), "score": score,
                    "label": scoring.LABELS[score], "detail": detail, "error": None})

    out.sort(key=lambda r: [int(x) for x in r["check_id"].split(".")])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the adoption assessment")
    ap.add_argument("--spark", action="store_true",
                    help="Execute through Spark instead of a SQL warehouse")
    ap.add_argument("--profile", help="CLI profile; required unless --spark")
    ap.add_argument("--warehouse-id", help="SQL warehouse id; required unless --spark")
    ap.add_argument("--results-catalog",
                    default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"))
    ap.add_argument("--results-schema",
                    default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.spark:
        from datavail_assessment.core.spark import SparkExecutor
        executor = SparkExecutor()
    else:
        if not args.profile or not args.warehouse_id:
            ap.error("--profile and --warehouse-id are required unless --spark is given")
        from datavail_assessment.core.warehouse import WarehouseExecutor
        executor = WarehouseExecutor(args.profile, args.warehouse_id, args.verbose)

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    params = {
        "DAYS_30": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        "DAYS_90": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
    }
    print(f"run_id={run_id}  30d>={params['DAYS_30']}  90d>={params['DAYS_90']}\n")

    results = run_checks(executor, params)
    blocks = {2: "##", 1: "++", 0: ".."}
    section_now = None
    for r in results:
        if r["section"] != section_now:
            section_now = r["section"]
            print(f"\n  --- {section_now} ---")
        flag = " !" if r["error"] else ""
        val = "err" if r["raw_value"] is None else f"{r['raw_value']:g}"
        print(f"  [{blocks[r['score']]}] {r['check_id']:>4}  {r['check_name'][:44]:<44} "
              f"{val:>8}  {r['label']}{flag}")

    sections, overall, grade = scoring.roll_up(results, checks_mod.SECTIONS)
    print("\n--- adoption scorecard ---")
    for s in sections:
        bar = "#" * int(s["score_pct"] / 2) + "." * (50 - int(s["score_pct"] / 2))
        print(f"  {s['section']:<18} [{bar}] {s['score_pct']:5.1f}%  {s['grade']}")
        print(f"  {'':18}  active={s['active_count']} minimal={s['minimal_count']} "
              f"none={s['none_count']}  ({s['points']}/{s['max_points']} pts)")
    errs = sum(1 for r in results if r["error"])
    print(f"\nOVERALL ADOPTION {overall:.1f}%  -  {grade}   "
          f"(checks: {len(results)}, unmeasurable: {errs})")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    base = f"{args.results_catalog}.{args.results_schema}"
    print(f"\nCreating adoption tables in {base}...")
    for stmt in split_sql(DDL.replace("{base}", base)):
        executor.execute(stmt)
    # CREATE TABLE IF NOT EXISTS no-ops against a table created by an
    # earlier version of this assessment, so a column added since would
    # be silently missing at INSERT time. Reconcile additively - never
    # drop or retype, since the existing rows are real history.
    ensure_columns(executor, f"{base}.{RESULTS_TABLE}", {"error": "STRING"})

    print("Writing results...")
    cols = ["run_id", "run_ts", "section", "check_id", "check_name",
            "raw_value", "score", "label", "detail", "error"]
    executor.write(f"{base}.{RESULTS_TABLE}", cols,
                   [dict(run_id=run_id, run_ts=now, **r) for r in results])

    scols = ["run_id", "run_ts", "section", "points", "max_points", "score_pct",
             "grade", "active_count", "minimal_count", "none_count", "weight"]
    rows = [dict(run_id=run_id, run_ts=now, **s) for s in sections]
    rows.append({"run_id": run_id, "run_ts": now, "section": "OVERALL",
                 "points": sum(s["points"] for s in sections),
                 "max_points": sum(s["max_points"] for s in sections),
                 "score_pct": overall, "grade": grade,
                 "active_count": sum(s["active_count"] for s in sections),
                 "minimal_count": sum(s["minimal_count"] for s in sections),
                 "none_count": sum(s["none_count"] for s in sections),
                 "weight": 1.0})
    executor.write(f"{base}.{SECTION_TABLE}", scols, rows)

    print(f"\nWritten to {base}. run_id={run_id}")
    print(f"  SELECT * FROM {base}.{SECTION_TABLE} WHERE run_id = '{run_id}';")
    return 0


if __name__ == "__main__":
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
