"""Checks whose evidence exists only over REST.

Most of the WORKSPACE_API tier turned out to be reachable from system
tables after all - job timeouts, health rules, bundle deployment and
grants all moved to SQL. What is left here genuinely is not: a job's
notification routing and its task types live in the Jobs API, and
secret scopes have no system table at all.

Each sampler makes one list call plus one call per object, so the
object counts matter: a workspace with thousands of jobs would want
sampling the way table_detail does. Jobs are usually tens, so this
walks all of them and caches the result for every check that needs it.

If the execution path cannot make REST calls, `executor.api` raises
NotImplementedError and the runner records NOT_AVAILABLE with that
reason - the check is sound, the path just cannot reach it.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Task kinds that run packaged, reviewable code. Everything else is a
# notebook, which is the artifact the anti-pattern is about.
_PACKAGED_TASK_KINDS = {
    "python_wheel_task", "spark_jar_task", "spark_python_task",
    "sql_task", "dbt_task", "run_job_task", "pipeline_task",
    "condition_task", "for_each_task",
}

_JOBS_CACHE: dict[int, list[dict]] = {}
_SCOPES_CACHE: dict[int, list[dict]] = {}


def _api(executor, path: str) -> dict:
    fn = getattr(executor, "api", None)
    if fn is None:
        raise NotImplementedError(
            "Needs a REST call, which this execution path does not support.")
    return fn("GET", path)


def job_specs(executor, params) -> list[dict]:
    """Full settings for every live job."""
    key = id(executor)
    if key in _JOBS_CACHE:
        return _JOBS_CACHE[key]

    listing = _api(executor, "/api/2.2/jobs/list?limit=100")
    specs: list[dict] = []
    for j in listing.get("jobs") or []:
        jid = j.get("job_id")
        if jid is None:
            continue
        try:
            full = _api(executor, f"/api/2.2/jobs/get?job_id={jid}")
        except NotImplementedError:
            raise
        except Exception:  # noqa: BLE001 - a job we cannot read is skipped
            continue
        s = full.get("settings") or {}
        specs.append({
            "job_id": jid,
            "name": s.get("name") or str(jid),
            "run_as": (full.get("run_as_user_name")
                       or s.get("run_as", {}).get("user_name")),
            "email": s.get("email_notifications") or {},
            "webhook": s.get("webhook_notifications") or {},
            "health": s.get("health") or {},
            "tasks": s.get("tasks") or [],
        })

    _JOBS_CACHE[key] = specs
    return specs


def secret_scope_acls(executor, params) -> list[dict]:
    """Every secret scope with the principals that can read it."""
    key = id(executor)
    if key in _SCOPES_CACHE:
        return _SCOPES_CACHE[key]

    listing = _api(executor, "/api/2.0/secrets/scopes/list")
    out: list[dict] = []
    for sc in listing.get("scopes") or []:
        name = sc.get("name")
        if not name:
            continue
        try:
            acls = _api(executor, f"/api/2.0/secrets/acls/list?scope={name}")
        except NotImplementedError:
            raise
        except Exception:  # noqa: BLE001
            acls = {}
        principals = [i.get("principal") for i in (acls.get("items") or [])
                      if i.get("principal")]
        out.append({
            "name": name,
            "backend": sc.get("backend_type"),
            "principals": principals,
            "individuals": [p for p in principals if _EMAIL.match(p)],
        })

    _SCOPES_CACHE[key] = out
    return out


def _has_failure_route(spec: dict) -> bool:
    email = spec["email"]
    if email.get("on_failure"):
        return True
    wh = spec["webhook"]
    return bool(wh.get("on_failure") or wh.get("on_duration_warning_threshold_exceeded"))


def check_failure_notifications(executor, params):
    """A failing job nobody is told about is a silent failure.

    Conforming = somebody is routed on failure, by email or webhook.
    The duration-threshold half of this pattern is measured separately
    by unbounded-task-execution, from system tables.
    """
    specs = job_specs(executor, params)
    num = sum(1 for s in specs if _has_failure_route(s))
    findings = [
        {"object_type": "JOB", "object_id": str(s["job_id"]), "object_name": s["name"],
         "owner": s["run_as"], "metric_name": "no_failure_notification",
         "metric_value": 1.0, "detail": "no on_failure email or webhook recipient"}
        for s in specs if not _has_failure_route(s)
    ][:500]
    return num, len(specs), findings


def check_notebooks_as_production_code(executor, params):
    """Anti-pattern: production work running as notebooks.

    Conforming = the task runs packaged code - a wheel, jar, script, SQL
    or another job - rather than a notebook whose cells are the
    deployable unit.
    """
    specs = job_specs(executor, params)
    num = den = 0
    findings = []
    for s in specs:
        for t in s["tasks"]:
            kinds = [k for k in t if k.endswith("_task")]
            if not kinds:
                continue
            den += 1
            if any(k in _PACKAGED_TASK_KINDS for k in kinds):
                num += 1
            else:
                findings.append({
                    "object_type": "JOB_TASK",
                    "object_id": f"{s['job_id']}:{t.get('task_key')}",
                    "object_name": f"{s['name']} / {t.get('task_key')}",
                    "owner": s["run_as"],
                    "metric_name": "notebook_task",
                    "metric_value": 1.0,
                    "detail": ", ".join(kinds),
                })
    return num, den, findings[:500]


def check_secrets_management(executor, params):
    """Secret scopes reachable only by groups and service principals.

    Scope existence alone says little - almost every workspace has one.
    What distinguishes managed secrets from shared ones is whether
    access is granted to identities that outlive an individual.
    """
    scopes = secret_scope_acls(executor, params)
    num = sum(1 for s in scopes if s["principals"] and not s["individuals"])
    findings = [
        {"object_type": "SECRET_SCOPE", "object_id": s["name"], "object_name": s["name"],
         "owner": ", ".join(s["individuals"][:3]) or None,
         "metric_name": "individual_acl_on_scope",
         "metric_value": float(len(s["individuals"])),
         "detail": ("no ACL entries returned" if not s["principals"]
                    else "granted directly to " + ", ".join(s["individuals"][:5]))}
        for s in scopes if not s["principals"] or s["individuals"]
    ][:500]
    return num, len(scopes), findings
