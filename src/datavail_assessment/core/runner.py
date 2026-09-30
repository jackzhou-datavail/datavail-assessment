"""The assessment run loop, shared by every assessment in this repo.

An assessment supplies three things:

  items     scorable definitions (severity, weight, tier, thresholds)
  checks    a module exposing CHECKS / PY_CHECKS, keyed by item id
  executor  how to run SQL and write rows (warehouse or Spark)

Everything else - scope probing, preflight, the MEASURED /
NOT_AVAILABLE / NOT_APPLICABLE / ERROR decision, scoring and
persistence - happens here, so a second assessment does not reimplement
it.
"""

from __future__ import annotations

import os
import time
import uuid

from . import scoring
from .paths import package_file
from .model import ERROR, MEASURED, NOT_APPLICABLE, NOT_AVAILABLE, TIER_REASONS, Outcome, utcnow
from .sqlutil import split_sql

ALWAYS_EXCLUDED = ["system", "samples", "__databricks_internal"]


# ---------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------

def probe_facts(executor) -> dict[str, bool]:
    """Detect what exists, so irrelevant items score NOT_APPLICABLE.

    Nothing here is assessment-specific: it asks what kinds of workload
    the workspace actually runs.
    """
    cap = executor.capability

    def any_rows(fqn: str) -> bool:
        if cap.columns(fqn) is None:
            return False
        try:
            rows = executor.query(f"SELECT COUNT(*) AS n FROM {fqn} LIMIT 1")
            return bool(rows) and int(rows[0]["n"] or 0) > 0
        except Exception:  # noqa: BLE001 - absence is the answer
            return False

    has_ml = any_rows("system.mlflow.experiments_latest") or any_rows("system.serving.served_entities")
    facts = {
        "IF_ML": has_ml,
        "IF_GENAI": any_rows("system.ai_gateway.usage") or has_ml,
        "IF_STREAMING": any_rows("system.lakeflow.pipelines"),
        "IF_SHARING": any_rows("system.sharing.materialization_events"),
        "IF_MULTI_WORKSPACE": False,
    }
    if cap.columns("system.billing.usage"):
        try:
            rows = executor.query(
                "SELECT COUNT(DISTINCT workspace_id) AS n FROM system.billing.usage "
                "WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS"
            )
            facts["IF_MULTI_WORKSPACE"] = int(rows[0]["n"] or 0) > 1
        except Exception:  # noqa: BLE001
            pass
    return facts


# ---------------------------------------------------------------------
# One check
# ---------------------------------------------------------------------

def run_check(executor, item, params: dict, checks) -> Outcome:
    """Resolve one item to a percentage or an explicit reason."""
    iid = item.id

    if not item.implemented:
        return Outcome(iid, NOT_AVAILABLE, reason=TIER_REASONS.get(item.tier))

    py = getattr(checks, "PY_CHECKS", {})
    if iid in py:
        unit, fn = py[iid]
        try:
            num, den, findings = fn(executor, params)
        except Exception as exc:  # noqa: BLE001
            return Outcome(iid, ERROR, reason=f"{type(exc).__name__}: {exc}"[:800])
        if den == 0:
            return Outcome(iid, NOT_APPLICABLE, unit=unit, reason="Nothing in scope to assess.")
        return Outcome(iid, MEASURED, unit=unit,
                       conformance_pct=round(100.0 * num / den, 2),
                       numerator=num, denominator=den, findings=findings,
                       evidence_query="python:" + fn.__name__)

    spec = checks.CHECKS.get(iid)
    if spec is None:
        return Outcome(iid, NOT_AVAILABLE,
                       reason="Marked implemented in the registry, but no check is defined.")

    missing = executor.capability.missing(spec["requires"])
    if missing:
        return Outcome(iid, NOT_AVAILABLE, unit=spec["unit"], reason=missing)

    sql = spec["measure"].format(**params)
    try:
        rows = executor.query(sql)
    except Exception as exc:  # noqa: BLE001
        return Outcome(iid, ERROR, unit=spec["unit"],
                       reason=f"{type(exc).__name__}: {exc}"[:800], evidence_query=sql)
    if not rows:
        return Outcome(iid, NOT_APPLICABLE, unit=spec["unit"],
                       reason="Measure query returned no rows.", evidence_query=sql)

    num = int(rows[0].get("numerator") or 0)
    den = int(rows[0].get("denominator") or 0)
    if den == 0:
        return Outcome(iid, NOT_APPLICABLE, unit=spec["unit"], denominator=0, evidence_query=sql,
                       reason=f"No {spec['unit']} in scope within the {params['lookback']}-day window.")

    findings = []
    if spec.get("findings"):
        try:
            for r in executor.query(spec["findings"].format(**params)):
                findings.append({
                    "object_type": r.get("object_type"),
                    "object_id": None if r.get("object_id") is None else str(r.get("object_id")),
                    "object_name": r.get("object_name"),
                    "owner": r.get("owner"),
                    "metric_name": r.get("metric_name"),
                    "metric_value": float(r["metric_value"]) if r.get("metric_value") is not None else None,
                    "detail": None,
                })
        except Exception as exc:  # noqa: BLE001 - evidence is best-effort
            findings.append({"object_type": "ERROR", "object_id": None, "object_name": None,
                             "owner": None, "metric_name": "findings_query_failed",
                             "metric_value": None, "detail": f"{type(exc).__name__}: {exc}"[:400]})

    return Outcome(iid, MEASURED, unit=spec["unit"],
                   conformance_pct=round(100.0 * num / den, 2),
                   numerator=num, denominator=den, evidence_query=sql, findings=findings)


# ---------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------

SCHEMA_SQL = package_file("core", "schema.sql")


def ensure_schema(executor, catalog: str, schema: str) -> None:
    ddl = open(SCHEMA_SQL, encoding="utf-8").read()
    ddl = ddl.replace("${results_catalog}", catalog).replace("${results_schema}", schema)

    # On metastores using Default Storage, CREATE CATALOG IF NOT EXISTS
    # still validates the storage root and fails even when the catalog
    # is present. Skip the statement entirely when it already exists.
    existing = executor.catalogs()
    if catalog in existing:
        print(f"  catalog '{catalog}' already exists - skipping CREATE CATALOG")
    for stmt in split_sql(ddl):
        if stmt.upper().startswith("CREATE CATALOG") and catalog in existing:
            continue
        executor.execute(stmt)


def persist(executor, base: str, run_id: str, items, outcomes, cats, overall, meta: dict) -> None:
    now = utcnow()
    executor.write(f"{base}.assessment_run",
        ["run_id", "run_ts", "status", "account_id", "workspace_id", "metastore_id",
         "runner_principal", "scope_catalogs", "excluded_catalogs", "lookback_days",
         "registry_version", "registry_checksum", "library_commit", "duration_seconds", "notes"],
        [{"run_id": run_id, "run_ts": now, "status": "COMPLETE", **meta}])

    executor.write(f"{base}.pattern_registry",
        ["run_id", "pattern_id", "category", "title", "is_anti_pattern", "severity", "weight",
         "check_tier", "implemented", "target_pct", "floor_pct", "applicability", "root_cause", "doc_path"],
        [{"run_id": run_id, "pattern_id": p.id, "category": p.category, "title": p.title,
          "is_anti_pattern": p.is_anti_pattern, "severity": p.severity, "weight": p.weight,
          "check_tier": p.tier, "implemented": p.implemented, "target_pct": p.target_pct,
          "floor_pct": p.floor_pct, "applicability": p.applicability,
          "root_cause": p.root_cause, "doc_path": p.doc_path} for p in items])

    executor.write(f"{base}.check_result",
        ["run_id", "pattern_id", "category", "status", "conformance_pct", "grade",
         "numerator", "denominator", "unit", "reason", "evidence_query", "finding_count", "measured_at"],
        [{"run_id": run_id, "pattern_id": p.id, "category": p.category,
          "status": outcomes[p.id].status, "conformance_pct": outcomes[p.id].conformance_pct,
          "grade": outcomes[p.id].grade(p), "numerator": outcomes[p.id].numerator,
          "denominator": outcomes[p.id].denominator, "unit": outcomes[p.id].unit,
          "reason": (outcomes[p.id].reason or "")[:1000] or None,
          "evidence_query": (outcomes[p.id].evidence_query or "")[:4000] or None,
          "finding_count": len(outcomes[p.id].findings), "measured_at": now} for p in items])

    frows = [{"run_id": run_id, "pattern_id": pid, "workspace_id": meta.get("workspace_id"),
              "observed_at": now, **f}
             for pid, o in outcomes.items() for f in o.findings[:200]]
    if frows:
        executor.write(f"{base}.check_finding",
            ["run_id", "pattern_id", "object_type", "object_id", "object_name", "workspace_id",
             "owner", "metric_name", "metric_value", "detail", "observed_at"], frows)

    executor.write(f"{base}.category_score",
        ["run_id", "category", "weighted_score", "coverage_pct", "weight_applicable",
         "weight_measured", "n_measured", "n_not_available", "n_not_applicable", "n_error", "n_poor"],
        [dict(run_id=run_id, **c) for c in cats])
    executor.write(f"{base}.assessment_score",
        ["run_id", "overall_score", "coverage_pct", "confidence", "weight_applicable",
         "weight_measured", "n_patterns", "n_measured", "n_not_available", "n_not_applicable",
         "n_error", "critical_gaps"],
        [dict(run_id=run_id, **overall)])


# ---------------------------------------------------------------------
# Whole run
# ---------------------------------------------------------------------

def execute(executor, items, checks, args, meta_extra: dict | None = None) -> int:
    """Run every item, score, print, and (unless dry-run) persist."""
    started, run_id = time.time(), str(uuid.uuid4())
    excluded = sorted(set(ALWAYS_EXCLUDED + list(args.exclude_catalog or []) + [args.results_catalog]))
    params = {"lookback": args.lookback_days,
              "excluded": ", ".join(f"'{c}'" for c in excluded)}

    # `impl` in the registry is a hand-written assertion that a check
    # exists. The runner already reports impl:true with no check, as a
    # reason on the result. The reverse - a check written but the flag
    # never flipped - would otherwise be silent: the check sits in the
    # module and never runs, and the item reports "no collector
    # implemented yet" forever. Fail loudly instead.
    orphaned = sorted(
        (set(getattr(checks, "CHECKS", {})) | set(getattr(checks, "PY_CHECKS", {})))
        - {i.id for i in items if i.implemented}
    )
    if orphaned:
        raise SystemExit(
            "%d check(s) are defined but marked impl: false in the registry, so "
            "they would never run: %s" % (len(orphaned), ", ".join(orphaned)))

    print(f"run_id={run_id}  lookback={args.lookback_days}d")
    print(f"excluded catalogs: {', '.join(excluded)}")
    facts = probe_facts(executor)
    print(f"scope facts: {facts}\n")

    outcomes: dict[str, Outcome] = {}
    for item in items:
        if not scoring.applicable(item, facts):
            outcomes[item.id] = Outcome(
                item.id, NOT_APPLICABLE,
                reason=f"Not applicable: no {item.applicability.replace('IF_', '').lower()} workloads.")
        else:
            outcomes[item.id] = run_check(executor, item, params, checks)
        o = outcomes[item.id]
        pct = f"{o.conformance_pct:6.2f}%" if o.conformance_pct is not None else "    -- "
        extra = f"  ({o.numerator}/{o.denominator} {o.unit})" if o.status == MEASURED else ""
        print(f"  {o.status:<15}{pct}  {item.id}{extra}")

    cats, overall = scoring.score(items, outcomes, facts)
    print("\n--- category scores ---")
    for c in cats:
        s = f"{c['weighted_score']:.1f}" if c["weighted_score"] is not None else "n/a"
        print(f"  {c['category']:<28} score={s:>6}  coverage={c['coverage_pct']:5.1f}%  "
              f"measured={c['n_measured']:>2} unavailable={c['n_not_available']:>2} n/a={c['n_not_applicable']:>2}")
    o_s = f"{overall['overall_score']:.1f}" if overall["overall_score"] is not None else "n/a"
    print(f"\nOVERALL {o_s} / 100   coverage {overall['coverage_pct']:.1f}% "
          f"({overall['confidence']})   critical gaps: {overall['critical_gaps']}")

    if getattr(args, "dry_run", False):
        print("\n--dry-run: nothing written.")
        return 0

    print("\nCreating result schema...")
    ensure_schema(executor, args.results_catalog, args.results_schema)
    base = f"{args.results_catalog}.{args.results_schema}"

    meta = {"account_id": None, "workspace_id": None, "metastore_id": None,
            "runner_principal": None, "scope_catalogs": [], "excluded_catalogs": excluded,
            "lookback_days": args.lookback_days, "registry_version": None,
            "registry_checksum": None, "library_commit": os.environ.get("GIT_COMMIT"),
            "duration_seconds": round(time.time() - started, 2), "notes": ""}
    meta.update(meta_extra or {})
    meta["duration_seconds"] = round(time.time() - started, 2)

    print("Writing results...")
    persist(executor, base, run_id, items, outcomes, cats, overall, meta)
    print(f"\nWritten to {base}. run_id={run_id}")
    print(f"  SELECT * FROM {base}.v_latest_report ORDER BY category, severity;")
    return 0
