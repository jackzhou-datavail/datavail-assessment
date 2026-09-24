"""Run the assessment through a SQL warehouse instead of Spark.

Same registry, same checks, same result schema as `run_assessment.py` —
but statements go through the Databricks SQL Statement Execution API via
the CLI, so no cluster, pyspark, or databricks-connect is needed.

    python run_via_sql_warehouse.py \
        --profile uc-semantics \
        --warehouse-id <id> \
        --results-catalog assessment \
        --lookback-days 30

Add --dry-run to execute every check and print the result without
creating the results catalog or writing any rows.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks as checks_mod  # noqa: E402
import lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATTERNS_DIR = os.path.join(os.path.dirname(HERE), "patterns")
ALWAYS_EXCLUDED = ["system", "samples", "__databricks_internal"]


class SqlError(Exception):
    pass


class WarehouseClient:
    """Thin Statement Execution API client driven through the CLI."""

    def __init__(self, profile: str, warehouse_id: str, verbose: bool = False):
        self.profile = profile
        self.warehouse_id = warehouse_id
        self.verbose = verbose
        self._env = {**os.environ, "MSYS_NO_PATHCONV": "1"}

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        cmd = ["databricks", "api", method, path, "-p", self.profile]
        if payload is not None:
            cmd += ["--json", json.dumps(payload)]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=self._env)
        if proc.returncode != 0:
            raise SqlError(f"CLI call failed: {proc.stderr.strip()[:500]}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise SqlError(f"Unparseable CLI response: {proc.stdout[:300]}") from exc

    def query(self, statement: str, timeout_s: int = 300) -> list[dict]:
        """Execute a statement and return rows as dicts."""
        if self.verbose:
            print(f"    SQL: {' '.join(statement.split())[:150]}")
        resp = self._call(
            "post",
            "/api/2.0/sql/statements",
            {
                "warehouse_id": self.warehouse_id,
                "statement": statement,
                "wait_timeout": "50s",
                "on_wait_timeout": "CONTINUE",
                "format": "JSON_ARRAY",
                "disposition": "INLINE",
            },
        )
        deadline = time.time() + timeout_s
        while resp.get("status", {}).get("state") in ("PENDING", "RUNNING"):
            if time.time() > deadline:
                raise SqlError(f"Statement timed out after {timeout_s}s")
            time.sleep(2)
            resp = self._call("get", f"/api/2.0/sql/statements/{resp['statement_id']}")

        state = resp.get("status", {}).get("state")
        if state != "SUCCEEDED":
            err = resp.get("status", {}).get("error", {})
            raise SqlError(f"{err.get('error_code', state)}: {err.get('message', '')}"[:800])

        manifest = resp.get("manifest", {})
        cols = [c["name"] for c in manifest.get("schema", {}).get("columns", [])]
        data = (resp.get("result") or {}).get("data_array") or []
        return [dict(zip(cols, row)) for row in data]

    def execute(self, statement: str, timeout_s: int = 300) -> None:
        self.query(statement, timeout_s)


class SqlCapability:
    """Column probing over the warehouse, mirroring lib.Capability."""

    def __init__(self, client: WarehouseClient):
        self.c = client
        self._cache: dict[str, set[str] | None] = {}

    def columns(self, fqn: str) -> set[str] | None:
        if fqn not in self._cache:
            try:
                rows = self.c.query(f"DESCRIBE TABLE {fqn}")
                names = set()
                for r in rows:
                    name = (r.get("col_name") or "").strip()
                    if not name or name.startswith("#"):
                        continue
                    names.add(name.lower())
                self._cache[fqn] = names or None
            except SqlError:
                self._cache[fqn] = None
        return self._cache[fqn]

    def missing(self, requires: dict[str, list[str]]) -> str | None:
        for fqn, needed in requires.items():
            cols = self.columns(fqn)
            if cols is None:
                return (
                    f"`{fqn}` is not readable from this workspace — the system schema "
                    f"may not be enabled, or the runner lacks SELECT on it."
                )
            absent = [c for c in needed if c.lower() not in cols]
            if absent:
                return (
                    f"`{fqn}` is readable but lacks expected column(s): {', '.join(absent)}. "
                    f"The system table schema has likely changed; the check needs updating."
                )
        return None


# ---------------------------------------------------------------------

def probe_facts(client: WarehouseClient, cap: SqlCapability) -> dict[str, bool]:
    def any_rows(fqn: str) -> bool:
        if cap.columns(fqn) is None:
            return False
        try:
            rows = client.query(f"SELECT COUNT(*) AS n FROM {fqn} LIMIT 1")
            return bool(rows) and int(rows[0]["n"] or 0) > 0
        except SqlError:
            return False

    has_ml = any_rows("system.mlflow.experiments_latest") or any_rows("system.serving.served_entities")
    facts = {
        "IF_ML": has_ml,
        "IF_GENAI": any_rows("system.ai_gateway.usage") or has_ml,
        "IF_STREAMING": any_rows("system.lakeflow.pipelines"),
        "IF_SHARING": False,
        "IF_MULTI_WORKSPACE": False,
    }
    if cap.columns("system.billing.usage"):
        try:
            rows = client.query(
                "SELECT COUNT(DISTINCT workspace_id) AS n FROM system.billing.usage "
                "WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS"
            )
            facts["IF_MULTI_WORKSPACE"] = int(rows[0]["n"] or 0) > 1
        except SqlError:
            pass
    return facts


def py_system_schemas(client: WarehouseClient, _params) -> tuple[int, int, list[dict]]:
    enabled, findings = 0, []
    for schema in checks_mod.REQUIRED_SYSTEM_SCHEMAS:
        try:
            client.query(f"SHOW TABLES IN system.{schema}")
            enabled += 1
        except SqlError as exc:
            findings.append({
                "object_type": "SCHEMA", "object_id": f"system.{schema}",
                "object_name": f"system.{schema}", "owner": None,
                "metric_name": "not_readable", "metric_value": 1.0,
                "detail": str(exc)[:400],
            })
    return enabled, len(checks_mod.REQUIRED_SYSTEM_SCHEMAS), findings


def run_check(client, cap, pattern: lib.Pattern, params: dict) -> lib.Outcome:
    pid = pattern.id
    if not pattern.implemented:
        return lib.Outcome(pid, lib.NOT_AVAILABLE, reason=lib.TIER_REASONS.get(pattern.tier))

    if pid in checks_mod.PY_CHECKS:
        try:
            num, den, findings = py_system_schemas(client, params)
        except Exception as exc:  # noqa: BLE001
            return lib.Outcome(pid, lib.ERROR, reason=f"{type(exc).__name__}: {exc}"[:800])
        return lib.Outcome(
            pid, lib.MEASURED, unit="system_schemas",
            conformance_pct=round(100.0 * num / den, 2), numerator=num, denominator=den,
            findings=findings, evidence_query="python:system_schema_enablement",
        )

    spec = checks_mod.CHECKS.get(pid)
    if spec is None:
        return lib.Outcome(pid, lib.NOT_AVAILABLE,
                           reason="Registry marks this implemented but no check is defined.")

    missing = cap.missing(spec["requires"])
    if missing:
        return lib.Outcome(pid, lib.NOT_AVAILABLE, unit=spec["unit"], reason=missing)

    sql = spec["measure"].format(**params)
    try:
        rows = client.query(sql)
    except SqlError as exc:
        return lib.Outcome(pid, lib.ERROR, unit=spec["unit"],
                           reason=str(exc)[:800], evidence_query=sql)
    if not rows:
        return lib.Outcome(pid, lib.NOT_APPLICABLE, unit=spec["unit"],
                           reason="Measure query returned no rows.", evidence_query=sql)

    num = int(rows[0].get("numerator") or 0)
    den = int(rows[0].get("denominator") or 0)
    if den == 0:
        return lib.Outcome(pid, lib.NOT_APPLICABLE, unit=spec["unit"], denominator=0,
                           evidence_query=sql,
                           reason=f"No {spec['unit']} in scope within the {params['lookback']}-day window.")

    findings = []
    if spec.get("findings"):
        try:
            for r in client.query(spec["findings"].format(**params)):
                findings.append({
                    "object_type": r.get("object_type"),
                    "object_id": r.get("object_id"),
                    "object_name": r.get("object_name"),
                    "owner": r.get("owner"),
                    "metric_name": r.get("metric_name"),
                    "metric_value": float(r["metric_value"]) if r.get("metric_value") else None,
                    "detail": None,
                })
        except SqlError as exc:
            findings.append({
                "object_type": "ERROR", "object_id": None, "object_name": None, "owner": None,
                "metric_name": "findings_query_failed", "metric_value": None,
                "detail": str(exc)[:400],
            })

    return lib.Outcome(pid, lib.MEASURED, unit=spec["unit"],
                       conformance_pct=round(100.0 * num / den, 2),
                       numerator=num, denominator=den, evidence_query=sql, findings=findings)


# --- SQL literal helpers ---------------------------------------------

def lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "array(" + ", ".join(lit(x) for x in v) + ")" if v else "array()"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def insert_rows(client: WarehouseClient, fqn: str, cols: list[str], rows: list[dict], batch: int = 50):
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        values = ",\n".join("(" + ", ".join(lit(r.get(c)) for c in cols) + ")" for r in chunk)
        client.execute(f"INSERT INTO {fqn} ({', '.join(cols)}) VALUES\n{values}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the assessment through a SQL warehouse")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--warehouse-id", required=True)
    ap.add_argument("--results-catalog", default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"))
    ap.add_argument("--results-schema", default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"))
    ap.add_argument("--patterns-dir", default=DEFAULT_PATTERNS_DIR)
    ap.add_argument("--registry", default=os.path.join(HERE, "registry.yaml"))
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--exclude-catalog", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.results_catalog in ALWAYS_EXCLUDED:
        ap.error(f"--results-catalog cannot be '{args.results_catalog}'.")

    client = WarehouseClient(args.profile, args.warehouse_id, args.verbose)
    cap = SqlCapability(client)
    started, run_id = time.time(), str(uuid.uuid4())

    excluded = sorted(set(ALWAYS_EXCLUDED + args.exclude_catalog + [args.results_catalog]))
    params = {"lookback": args.lookback_days, "excluded": ", ".join(f"'{c}'" for c in excluded)}

    patterns, registry_version, registry_checksum = lib.load_registry(args.registry, args.patterns_dir)
    print(f"run_id={run_id}  registry={registry_version}  lookback={args.lookback_days}d")
    print(f"excluded catalogs: {', '.join(excluded)}")

    facts = probe_facts(client, cap)
    print(f"scope facts: {facts}\n")

    outcomes: dict[str, lib.Outcome] = {}
    for p in patterns:
        if not lib.applicable(p, facts):
            outcomes[p.id] = lib.Outcome(
                p.id, lib.NOT_APPLICABLE,
                reason=f"Not applicable: no {p.applicability.replace('IF_', '').lower()} workloads.")
        else:
            outcomes[p.id] = run_check(client, cap, p, params)
        o = outcomes[p.id]
        pct = f"{o.conformance_pct:6.2f}%" if o.conformance_pct is not None else "    -- "
        extra = ""
        if o.status == lib.MEASURED:
            extra = f"  ({o.numerator}/{o.denominator} {o.unit})"
        print(f"  {o.status:<15}{pct}  {p.id}{extra}")

    cats, overall = lib.score(patterns, outcomes, facts)
    print("\n--- category scores ---")
    for c in cats:
        s = f"{c['weighted_score']:.1f}" if c["weighted_score"] is not None else "n/a"
        print(f"  {c['category']:<28} score={s:>6}  coverage={c['coverage_pct']:5.1f}%  "
              f"measured={c['n_measured']:>2} unavailable={c['n_not_available']:>2} n/a={c['n_not_applicable']:>2}")
    os_ = f"{overall['overall_score']:.1f}" if overall["overall_score"] is not None else "n/a"
    print(f"\nOVERALL {os_} / 100   coverage {overall['coverage_pct']:.1f}% "
          f"({overall['confidence']})   critical gaps: {overall['critical_gaps']}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    print("\nCreating result schema...")
    ddl = open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read()
    ddl = ddl.replace("${results_catalog}", args.results_catalog).replace("${results_schema}", args.results_schema)

    # On metastores using Default Storage, CREATE CATALOG IF NOT EXISTS still
    # validates the storage root and fails even when the catalog is present.
    # Skip the statement entirely when the catalog already exists.
    existing = {r.get("catalog") for r in client.query("SHOW CATALOGS")}
    if args.results_catalog in existing:
        print(f"  catalog '{args.results_catalog}' already exists — skipping CREATE CATALOG")

    for body in lib.split_sql(ddl):
        if body.upper().startswith("CREATE CATALOG") and args.results_catalog in existing:
            continue
        client.execute(body)

    base = f"{args.results_catalog}.{args.results_schema}"
    now = "current_timestamp()"
    ctx = client.query("SELECT current_metastore() AS m, current_user() AS u")[0]

    print("Writing results...")
    insert_rows(client, f"{base}.assessment_run",
                ["run_id", "run_ts", "status", "account_id", "workspace_id", "metastore_id",
                 "runner_principal", "scope_catalogs", "excluded_catalogs", "lookback_days",
                 "registry_version", "registry_checksum", "library_commit", "duration_seconds", "notes"],
                [{"run_id": run_id, "run_ts": None, "status": "COMPLETE",
                  "account_id": ctx["m"], "workspace_id": None, "metastore_id": ctx["m"],
                  "runner_principal": ctx["u"], "scope_catalogs": [], "excluded_catalogs": excluded,
                  "lookback_days": args.lookback_days, "registry_version": registry_version,
                  "registry_checksum": registry_checksum, "library_commit": None,
                  "duration_seconds": round(time.time() - started, 2),
                  "notes": "run via SQL warehouse " + args.warehouse_id}])
    client.execute(f"UPDATE {base}.assessment_run SET run_ts = {now} WHERE run_id = {lit(run_id)} AND run_ts IS NULL")

    insert_rows(client, f"{base}.pattern_registry",
                ["run_id", "pattern_id", "category", "title", "is_anti_pattern", "severity", "weight",
                 "check_tier", "implemented", "target_pct", "floor_pct", "applicability",
                 "root_cause", "doc_path"],
                [{"run_id": run_id, "pattern_id": p.id, "category": p.category, "title": p.title,
                  "is_anti_pattern": p.is_anti_pattern, "severity": p.severity, "weight": p.weight,
                  "check_tier": p.tier, "implemented": p.implemented, "target_pct": p.target_pct,
                  "floor_pct": p.floor_pct, "applicability": p.applicability,
                  "root_cause": p.root_cause, "doc_path": p.doc_path} for p in patterns])

    insert_rows(client, f"{base}.check_result",
                ["run_id", "pattern_id", "category", "status", "conformance_pct", "grade",
                 "numerator", "denominator", "unit", "reason", "evidence_query", "finding_count"],
                [{"run_id": run_id, "pattern_id": p.id, "category": p.category,
                  "status": outcomes[p.id].status, "conformance_pct": outcomes[p.id].conformance_pct,
                  "grade": outcomes[p.id].grade(p), "numerator": outcomes[p.id].numerator,
                  "denominator": outcomes[p.id].denominator, "unit": outcomes[p.id].unit,
                  "reason": (outcomes[p.id].reason or "")[:1000] or None,
                  "evidence_query": (outcomes[p.id].evidence_query or "")[:4000] or None,
                  "finding_count": len(outcomes[p.id].findings)} for p in patterns])
    client.execute(f"UPDATE {base}.check_result SET measured_at = {now} WHERE run_id = {lit(run_id)} AND measured_at IS NULL")

    frows = [{"run_id": run_id, "pattern_id": pid, **f}
             for pid, o in outcomes.items() for f in o.findings[:200]]
    if frows:
        insert_rows(client, f"{base}.check_finding",
                    ["run_id", "pattern_id", "object_type", "object_id", "object_name",
                     "owner", "metric_name", "metric_value", "detail"], frows)
        client.execute(f"UPDATE {base}.check_finding SET observed_at = {now} WHERE run_id = {lit(run_id)} AND observed_at IS NULL")

    insert_rows(client, f"{base}.category_score",
                ["run_id", "category", "weighted_score", "coverage_pct", "weight_applicable",
                 "weight_measured", "n_measured", "n_not_available", "n_not_applicable",
                 "n_error", "n_poor"],
                [dict(run_id=run_id, **c) for c in cats])
    insert_rows(client, f"{base}.assessment_score",
                ["run_id", "overall_score", "coverage_pct", "confidence", "weight_applicable",
                 "weight_measured", "n_patterns", "n_measured", "n_not_available",
                 "n_not_applicable", "n_error", "critical_gaps"],
                [dict(run_id=run_id, **overall)])

    print(f"\nWritten to {base}. run_id={run_id}")
    print(f"  SELECT * FROM {base}.v_latest_report ORDER BY category, severity;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
