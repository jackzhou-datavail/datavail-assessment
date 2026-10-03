"""Deriving a workspace's URL and id from a CLI profile.

The dashboards bake absolute console links into their generated JSON,
because a dashboard's own SQL cannot learn its host and `?o=<id>` is
what stops a link opening the wrong workspace on a multi-workspace
account. Asking an operator to pass both by hand is one more thing to
get wrong on a new workspace, so derive them from the profile they are
already passing.

Two values, two sources, because neither is available from one place:

  host    read from ~/.databrickscfg. Offline, no failure modes.
          `${workspace.host}` in a bundle resolves EMPTY when the host
          comes from a profile rather than being written in
          databricks.yml, which is why this exists at all.

  org id  GET /api/2.1/unity-catalog/current-metastore-assignment,
          which returns workspace_id outright. Falls back to parsing
          `?o=` out of a job run URL if that endpoint is unavailable -
          a workspace with no metastore assigned.

Everything goes through the Databricks CLI rather than a direct HTTPS
call. On a machine behind TLS interception the workspace host is
unreachable from Python and from curl, while the CLI works:

  urllib:  CERTIFICATE_VERIFY_FAILED - Basic Constraints of CA cert
           not marked critical
  curl:    schannel ... CRYPT_E_NO_REVOCATION_CHECK

So reading the X-Databricks-Org-Id response header - the obvious way to
get this - is not an option here, and neither is any other direct
request. The CLI is the only transport that reaches the workspace.
"""

from __future__ import annotations

import json
import os
import re
import subprocess


def host_from_profile(profile: str) -> str | None:
    """The `host` line of a profile in ~/.databrickscfg."""
    path = os.path.expanduser("~/.databrickscfg")
    if not os.path.exists(path):
        return None
    in_section = False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("["):
                in_section = line == f"[{profile}]"
            elif in_section and line.lower().startswith("host"):
                return line.split("=", 1)[1].strip().rstrip("/")
    return None


def _cli_json(path: str, profile: str) -> dict | None:
    """GET an API path through the CLI, parsed. None on any failure."""
    try:
        proc = subprocess.run(
            ["databricks", "api", "get", path, "-p", profile],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "MSYS_NO_PATHCONV": "1"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def org_id_from_profile(profile: str) -> str | None:
    """Workspace id for the ?o= parameter.

    Unity Catalog reports it directly, which is why that is tried
    first: it needs no jobs, clusters or warehouses to exist.
    """
    body = _cli_json("/api/2.1/unity-catalog/current-metastore-assignment",
                     profile) or {}
    wid = body.get("workspace_id")
    if wid:
        return str(wid)

    # No metastore assigned. Any job run URL carries ?o=, so fall back
    # to that rather than giving up.
    runs = (_cli_json("/api/2.2/jobs/runs/list?limit=1", profile) or {}).get("runs") or []
    for run in runs:
        m = re.search(r"[?&]o=(\d+)", run.get("run_page_url") or "")
        if m:
            return m.group(1)
    return None


def derive(profile: str) -> tuple[str | None, str | None]:
    """(host, org_id) for a profile. Either may be None."""
    return host_from_profile(profile), org_id_from_profile(profile)
