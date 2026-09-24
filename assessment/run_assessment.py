"""Databricks platform assessment collector.

Reads the pattern registry, runs every implemented check against this
workspace's system tables, and writes results to a dedicated catalog
that is itself excluded from assessment scope.

Every pattern produces exactly one row in `check_result`, with either a
conformance percentage or an explicit reason why no measurement was
possible. The headline score is always published alongside a coverage
percentage, so a high score computed from thin evidence is visible as
such rather than mistaken for a clean bill of health.

Run as a Databricks job task or notebook:

    %run ./run_assessment.py  --results-catalog assessment \
                              --lookback-days 30

Or with spark-submit / Databricks CLI bundle run. Requires SELECT on the
`system` catalog; several checks need account-admin visibility (notably
`system.query.history`) and will report NOT_AVAILABLE without it.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

def _here() -> str:
    """Directory holding this script, its registry and its schema.

    `spark_python_task` on serverless compute exec()s the file, so
    `__file__` is not defined there. Fall back to locating the directory
    by the files we know sit beside this one.
    """
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    candidates = [os.getcwd(), *sys.path]
    for cand in candidates:
        if cand and os.path.exists(os.path.join(cand, "registry.yaml")):
            return os.path.abspath(cand)
    for cand in candidates:
        nested = os.path.join(cand or "", "assessment")
        if os.path.exists(os.path.join(nested, "registry.yaml")):
            return os.path.abspath(nested)
    return os.getcwd()


HERE = _here()
sys.path.insert(0, HERE)

import checks as checks_mod  # noqa: E402
import lib  # noqa: E402

DEFAULT_PATTERNS_DIR = os.path.join(os.path.dirname(HERE), "patterns")

# Catalogs never assessed: the results catalog is added at runtime.
ALWAYS_EXCLUDED = ["system", "samples", "__databricks_internal"]


def get_spark():
    try:
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.getOrCreate()
    except Exception:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()


# ---------------------------------------------------------------------
# Workspace facts — decide which pattern groups are in scope at all.
# ---------------------------------------------------------------------

def probe_facts(spark, cap: lib.Capability) -> dict[str, bool]:
    """Detect what exists, so irrelevant patterns score NOT_APPLICABLE."""

    def any_rows(fqn: str, where: str = "1=1") -> bool:
        if cap.columns(fqn) is None:
            return False
        try:
            row = spark.sql(f"SELECT COUNT(*) AS n FROM {fqn} WHERE {where} LIMIT 1").collect()
            return bool(row and row[0]["n"] > 0)
        except Exception:
            return False

    has_ml = any_rows("system.mlflow.experiments_latest") or any_rows("system.serving.served_entities")
    has_genai = any_rows("system.ai_gateway.usage")
    facts = {
        "IF_ML": has_ml,
        "IF_GENAI": has_genai or has_ml,
        "IF_STREAMING": any_rows("system.lakeflow.pipelines"),
        "IF_SHARING": any_rows("system.sharing.materialization_events")
        if cap.columns("system.sharing.materialization_events")
        else False,
        "IF_MULTI_WORKSPACE": False,
    }
    if cap.columns("system.billing.usage"):
        try:
            n = spark.sql(
                "SELECT COUNT(DISTINCT workspace_id) AS n FROM system.billing.usage "
                "WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS"
            ).collect()[0]["n"]
            facts["IF_MULTI_WORKSPACE"] = n > 1
        except Exception:
            pass
    return facts


# ---------------------------------------------------------------------
# Check execution
# ---------------------------------------------------------------------

def run_check(spark, cap: lib.Capability, pattern: lib.Pattern, params: dict) -> lib.Outcome:
    pid = pattern.id

    if not pattern.implemented:
        return lib.Outcome(
            pattern_id=pid,
            status=lib.NOT_AVAILABLE,
            reason=lib.TIER_REASONS.get(pattern.tier, "No collector check implemented."),
        )

    # Python-evaluated checks
    if pid in checks_mod.PY_CHECKS:
        unit, fn = checks_mod.PY_CHECKS[pid]
        try:
            num, den, findings = fn(spark, params)
        except Exception as exc:  # noqa: BLE001
            return lib.Outcome(pattern_id=pid, status=lib.ERROR, reason=f"{type(exc).__name__}: {exc}"[:1000])
        if den == 0:
            return lib.Outcome(pattern_id=pid, status=lib.NOT_APPLICABLE, unit=unit,
                               reason="Nothing in scope to assess.")
        return lib.Outcome(
            pattern_id=pid, status=lib.MEASURED, unit=unit,
            conformance_pct=round(100.0 * num / den, 2),
            numerator=num, denominator=den, findings=findings,
            evidence_query="python:" + fn.__name__,
        )

    spec = checks_mod.CHECKS.get(pid)
    if spec is None:
        return lib.Outcome(
            pattern_id=pid,
            status=lib.NOT_AVAILABLE,
            reason="Registry marks this pattern implemented, but no check is defined. Registry/code drift.",
        )

    missing = cap.missing(spec["requires"])
    if missing:
        return lib.Outcome(pattern_id=pid, status=lib.NOT_AVAILABLE, unit=spec["unit"], reason=missing)

    sql = spec["measure"].format(**params)
    try:
        row = spark.sql(sql).collect()[0]
        num = int(row["numerator"] or 0)
        den = int(row["denominator"] or 0)
    except Exception as exc:  # noqa: BLE001
        return lib.Outcome(
            pattern_id=pid, status=lib.ERROR, unit=spec["unit"],
            reason=f"{type(exc).__name__}: {exc}"[:1000], evidence_query=sql,
        )

    if den == 0:
        return lib.Outcome(
            pattern_id=pid, status=lib.NOT_APPLICABLE, unit=spec["unit"],
            denominator=0, evidence_query=sql,
            reason=f"No {spec['unit']} in scope within the {params['lookback']}-day window.",
        )

    findings: list[dict] = []
    if spec.get("findings"):
        try:
            fsql = spec["findings"].format(**params)
            for r in spark.sql(fsql).collect():
                d = r.asDict()
                findings.append(
                    {
                        "object_type": d.get("object_type"),
                        "object_id": str(d.get("object_id")) if d.get("object_id") is not None else None,
                        "object_name": d.get("object_name"),
                        "owner": d.get("owner"),
                        "metric_name": d.get("metric_name"),
                        "metric_value": float(d["metric_value"]) if d.get("metric_value") is not None else None,
                        "detail": None,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            findings.append(
                {
                    "object_type": "ERROR", "object_id": None, "object_name": None, "owner": None,
                    "metric_name": "findings_query_failed", "metric_value": None,
                    "detail": f"{type(exc).__name__}: {exc}"[:500],
                }
            )

    return lib.Outcome(
        pattern_id=pid, status=lib.MEASURED, unit=spec["unit"],
        conformance_pct=round(100.0 * num / den, 2),
        numerator=num, denominator=den, evidence_query=sql, findings=findings,
    )


# ---------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------

def ensure_schema(spark, results_catalog: str, results_schema: str) -> None:
    ddl = open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read()
    ddl = ddl.replace("${results_catalog}", results_catalog).replace("${results_schema}", results_schema)

    # On metastores using Default Storage, CREATE CATALOG IF NOT EXISTS still
    # validates the storage root and fails even when the catalog is present.
    # Skip the statement entirely when the catalog already exists.
    try:
        existing = {r[0] for r in spark.sql("SHOW CATALOGS").collect()}
    except Exception:  # noqa: BLE001 - fall back to attempting the create
        existing = set()
    if results_catalog in existing:
        print(f"  catalog '{results_catalog}' already exists - skipping CREATE CATALOG")

    for stmt in lib.split_sql(ddl):
        if stmt.upper().startswith("CREATE CATALOG") and results_catalog in existing:
            continue
        spark.sql(stmt)


def write_rows(spark, fqn: str, rows: list[dict]) -> None:
    if not rows:
        return
    target_cols = [f.name for f in spark.table(fqn).schema.fields]
    normalized = [{c: r.get(c) for c in target_cols} for r in rows]
    df = spark.createDataFrame(normalized, schema=spark.table(fqn).schema)
    df.write.mode("append").saveAsTable(fqn)


# ---------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Databricks platform assessment collector")
    ap.add_argument(
        "--results-catalog",
        default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"),
        help="Dedicated catalog for assessment output. Created if absent and always "
             "excluded from assessment scope. Env: ASSESSMENT_RESULTS_CATALOG",
    )
    ap.add_argument(
        "--results-schema",
        default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"),
        help="Schema within the results catalog. Env: ASSESSMENT_RESULTS_SCHEMA",
    )
    ap.add_argument("--patterns-dir", default=DEFAULT_PATTERNS_DIR)
    ap.add_argument("--registry", default=os.path.join(HERE, "registry.yaml"))
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--exclude-catalog", action="append", default=[])
    ap.add_argument("--notes", default="")
    ap.add_argument("--dry-run", action="store_true", help="Run checks and print, write nothing")
    args = ap.parse_args(argv)

    # The results catalog must be a dedicated one. Writing results into a
    # catalog that is itself under assessment would let the act of
    # measuring change what is measured.
    if args.results_catalog in ALWAYS_EXCLUDED:
        ap.error(
            f"--results-catalog cannot be '{args.results_catalog}'. "
            "Use a dedicated catalog such as 'assessment'."
        )

    spark = get_spark()
    started = time.time()
    run_id = str(uuid.uuid4())

    # The results catalog is added to the exclusion list unconditionally,
    # so no check can ever read the tables this run is writing.
    excluded = sorted(set(ALWAYS_EXCLUDED + args.exclude_catalog + [args.results_catalog]))
    params = {
        "lookback": args.lookback_days,
        "excluded": ", ".join(f"'{c}'" for c in excluded),
    }

    patterns, registry_version, registry_checksum = lib.load_registry(args.registry, args.patterns_dir)
    cap = lib.Capability(spark)
    facts = probe_facts(spark, cap)

    print(f"run_id={run_id}  registry={registry_version}  lookback={args.lookback_days}d")
    print(f"excluded catalogs: {', '.join(excluded)}")
    print(f"scope facts: {facts}\n")

    outcomes: dict[str, lib.Outcome] = {}
    for p in patterns:
        if not lib.applicable(p, facts):
            outcomes[p.id] = lib.Outcome(
                pattern_id=p.id, status=lib.NOT_APPLICABLE,
                reason=f"Not applicable: workspace has no {p.applicability.replace('IF_', '').lower()} workloads.",
            )
        else:
            outcomes[p.id] = run_check(spark, cap, p, params)
        o = outcomes[p.id]
        pct = f"{o.conformance_pct:6.2f}%" if o.conformance_pct is not None else "    -- "
        print(f"  {o.status:<15} {pct}  {p.id}")

    cats, overall = lib.score(patterns, outcomes, facts)

    print("\n--- category scores ---")
    for c in cats:
        s = f"{c['weighted_score']:.1f}" if c["weighted_score"] is not None else "n/a"
        print(f"  {c['category']:<28} score={s:>6}  coverage={c['coverage_pct']:.0f}%  "
              f"measured={c['n_measured']} unavailable={c['n_not_available']} n/a={c['n_not_applicable']}")
    o_score = f"{overall['overall_score']:.1f}" if overall["overall_score"] is not None else "n/a"
    print(f"\nOVERALL {o_score} / 100   coverage {overall['coverage_pct']:.0f}% "
          f"({overall['confidence']} confidence)   critical gaps: {overall['critical_gaps']}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    ensure_schema(spark, args.results_catalog, args.results_schema)
    base = f"{args.results_catalog}.{args.results_schema}"
    now = lib.utcnow()

    ctx = {}
    for key, sql in (
        ("account_id", "SELECT current_metastore() AS v"),
        ("runner_principal", "SELECT current_user() AS v"),
    ):
        try:
            ctx[key] = spark.sql(sql).collect()[0]["v"]
        except Exception:
            ctx[key] = None
    try:
        ws = spark.conf.get("spark.databricks.workspaceUrl", None)
    except Exception:
        ws = None

    write_rows(spark, f"{base}.assessment_run", [{
        "run_id": run_id, "run_ts": now, "status": "COMPLETE",
        "account_id": ctx.get("account_id"), "workspace_id": ws,
        "metastore_id": ctx.get("account_id"), "runner_principal": ctx.get("runner_principal"),
        "scope_catalogs": [], "excluded_catalogs": excluded,
        "lookback_days": args.lookback_days, "registry_version": registry_version,
        "registry_checksum": registry_checksum, "library_commit": os.environ.get("GIT_COMMIT"),
        "duration_seconds": round(time.time() - started, 2), "notes": args.notes,
    }])

    write_rows(spark, f"{base}.pattern_registry", [{
        "run_id": run_id, "pattern_id": p.id, "category": p.category, "title": p.title,
        "is_anti_pattern": p.is_anti_pattern, "severity": p.severity, "weight": p.weight,
        "check_tier": p.tier, "implemented": p.implemented, "target_pct": p.target_pct,
        "floor_pct": p.floor_pct, "applicability": p.applicability, "root_cause": p.root_cause,
        "doc_path": p.doc_path,
    } for p in patterns])

    by_id = {p.id: p for p in patterns}
    write_rows(spark, f"{base}.check_result", [{
        "run_id": run_id, "pattern_id": p.id, "category": p.category,
        "status": outcomes[p.id].status,
        "conformance_pct": outcomes[p.id].conformance_pct,
        "grade": outcomes[p.id].grade(p),
        "numerator": outcomes[p.id].numerator,
        "denominator": outcomes[p.id].denominator,
        "unit": outcomes[p.id].unit,
        "reason": outcomes[p.id].reason,
        "evidence_query": outcomes[p.id].evidence_query,
        "finding_count": len(outcomes[p.id].findings),
        "measured_at": now,
    } for p in patterns])

    findings_rows = []
    for pid, o in outcomes.items():
        for f in o.findings:
            findings_rows.append({
                "run_id": run_id, "pattern_id": pid,
                "object_type": f.get("object_type"), "object_id": f.get("object_id"),
                "object_name": f.get("object_name"), "workspace_id": ws,
                "owner": f.get("owner"), "metric_name": f.get("metric_name"),
                "metric_value": f.get("metric_value"), "detail": f.get("detail"),
                "observed_at": now,
            })
    write_rows(spark, f"{base}.check_finding", findings_rows)

    write_rows(spark, f"{base}.category_score", [dict(run_id=run_id, **c) for c in cats])
    write_rows(spark, f"{base}.assessment_score", [dict(run_id=run_id, **overall)])

    print(f"\nWritten to {base}. run_id={run_id}")
    print(f"  SELECT * FROM {base}.v_latest_report ORDER BY category, severity;")
    return 0


if __name__ == "__main__":
    # Do NOT `raise SystemExit(main())` unconditionally. `spark_python_task`
    # on serverless compute exec()s this file inside an IPython kernel, where
    # even SystemExit(0) is surfaced as a workload failure — the collector
    # completes, writes its results, and the task still reports
    # RUN_EXECUTION_ERROR. Return normally on success; signal only on failure.
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
