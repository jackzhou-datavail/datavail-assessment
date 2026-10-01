"""Grant checks, which need SHOW GRANTS per securable.

The registry files these under WORKSPACE_API, but SHOW GRANTS is
ordinary SQL - it just cannot be expressed as one statement over a
system table, because there is no system table of grants. So this is a
scan pass like table_detail, not an API capability.

Scope is catalogs rather than every table. Grants inherit downward, so
catalog-level grants are where group-vs-individual is decided, and
scanning every table would be thousands of round trips to re-learn the
same answer.

A catalog the run cannot read is skipped, not failed: SHOW GRANTS needs
USE CATALOG, and an assessment should report on what it can see rather
than erroring on the first catalog it cannot.
"""

from __future__ import annotations

import re

# A principal that looks like an email address is a person. Groups and
# service principals come back as names or UUIDs.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_SAMPLE_CACHE: dict[int, list[dict]] = {}


def grant_sample(executor, params) -> list[dict]:
    """Every catalog-level grant the run can see."""
    key = id(executor)
    if key in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[key]

    skip = {"system", "samples", "__databricks_internal"}
    try:
        catalogs = sorted(c for c in executor.catalogs() if c not in skip)
    except Exception:  # noqa: BLE001
        catalogs = []

    rows: list[dict] = []
    for cat in catalogs:
        try:
            got = executor.query(f"SHOW GRANTS ON CATALOG `{cat}`")
        except Exception:  # noqa: BLE001 - no USE CATALOG; not this check's finding
            continue
        for r in got:
            principal = (r.get("Principal") or "").strip()
            if not principal:
                continue
            rows.append({
                "catalog": cat,
                "principal": principal,
                "action": r.get("ActionType"),
                "is_person": bool(_EMAIL.match(principal)),
            })

    _SAMPLE_CACHE[key] = rows
    return rows


def _finding(g: dict, metric: str) -> dict:
    return {
        "object_type": "GRANT",
        "object_id": f"{g['catalog']}:{g['principal']}:{g['action']}",
        "object_name": f"{g['action']} ON {g['catalog']}",
        "owner": g["principal"],
        "metric_name": metric,
        "metric_value": 1.0,
        "detail": f"granted directly to {g['principal']}",
    }


def check_individual_user_grants(executor, params):
    """Anti-pattern: permissions granted to people rather than groups.

    Conforming = the grant went to a group or service principal, so it
    survives the grantee changing team.
    """
    sample = grant_sample(executor, params)
    num = sum(1 for g in sample if not g["is_person"])
    findings = [_finding(g, "grant_to_individual") for g in sample if g["is_person"]][:500]
    return num, len(sample), findings


def check_group_based_access_control(executor, params):
    """The same evidence seen per principal rather than per grant.

    Counting grants would weight a person holding five privileges five
    times; what matters is how many of the identities with any access
    are groups.
    """
    sample = grant_sample(executor, params)
    seen: dict[str, bool] = {}
    for g in sample:
        seen.setdefault(g["principal"], g["is_person"])
    num = sum(1 for is_person in seen.values() if not is_person)
    findings = [
        {"object_type": "PRINCIPAL", "object_id": p, "object_name": p, "owner": p,
         "metric_name": "individual_with_direct_access", "metric_value": 1.0,
         "detail": "holds catalog grants directly rather than through a group"}
        for p, is_person in seen.items() if is_person
    ][:500]
    return num, len(seen), findings
