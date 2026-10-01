"""Databricks SQL Statement Execution API client, driven through the CLI.

Lets an assessment run from a laptop with no cluster, no pyspark and no
databricks-connect - only a CLI profile and a warehouse id.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

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


class WarehouseExecutor:
    """Adapts the warehouse client to the interface core.runner expects."""

    def __init__(self, profile: str, warehouse_id: str, verbose: bool = False):
        self.client = WarehouseClient(profile, warehouse_id, verbose)
        self.capability = SqlCapability(self.client)
        self.warehouse_id = warehouse_id

    def query(self, sql: str):
        return self.client.query(sql)

    def execute(self, sql: str) -> None:
        self.client.execute(sql)

    def api(self, method: str, path: str, payload: dict | None = None) -> dict:
        """A REST call, for checks whose evidence is not in any system
        table - job notifications, secret scope ACLs, task types. Uses
        the same CLI transport as the SQL path, so it needs no extra
        credentials."""
        # The CLI subcommand is lowercase: `databricks api get`.
        return self.client._call(method.lower(), path, payload)

    def catalogs(self) -> set:
        try:
            return {r.get("catalog") for r in self.client.query("SHOW CATALOGS")}
        except SqlError:
            return set()

    def context(self) -> dict:
        try:
            r = self.client.query("SELECT current_metastore() AS m, current_user() AS u")[0]
            return {"metastore_id": r["m"], "account_id": r["m"], "runner_principal": r["u"]}
        except SqlError:
            return {}

    def write(self, fqn: str, cols: list, rows: list, batch: int = 50) -> None:
        from .sqlutil import lit
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            values = ",\n".join(
                "(" + ", ".join(lit(r.get(c)) for c in cols) + ")" for r in chunk)
            self.client.execute(
                f"INSERT INTO {fqn} ({', '.join(cols)}) VALUES\n{values}")
