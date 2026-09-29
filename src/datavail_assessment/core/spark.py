"""Spark-side execution, for running an assessment inside a workspace job."""

from __future__ import annotations

def get_spark():
    try:
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.getOrCreate()
    except Exception:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()


class SparkCapability:
    """Probes which system tables and columns this run can actually read.

    Every check declares the objects it needs. Anything missing — because
    the schema is not enabled, the runner lacks grants, or the column was
    renamed — turns into NOT_AVAILABLE with a precise reason, rather than
    a stack trace or, worse, a silently optimistic score.
    """

    def __init__(self, spark):
        self._spark = spark
        self._cache: dict[str, set[str] | None] = {}

    def columns(self, fqn: str) -> set[str] | None:
        """Lowercased column names for `fqn`, or None if unreadable."""
        if fqn not in self._cache:
            try:
                cols = {f.name.lower() for f in self._spark.table(fqn).schema.fields}
                self._cache[fqn] = cols
            except Exception:
                self._cache[fqn] = None
        return self._cache[fqn]

    def missing(self, requires: dict[str, list[str]]) -> str | None:
        """Return a human reason if anything required is unavailable."""
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
                    f"`{fqn}` is readable but lacks expected column(s): "
                    f"{', '.join(absent)}. The system table schema has likely changed; "
                    f"the check needs updating."
                )
        return None


class SparkExecutor:
    """Adapts a Spark session to the interface core.runner expects."""

    def __init__(self, spark=None):
        self.spark = spark or get_spark()
        self.capability = SparkCapability(self.spark)

    def query(self, sql: str):
        return [r.asDict() for r in self.spark.sql(sql).collect()]

    def execute(self, sql: str) -> None:
        self.spark.sql(sql)

    def catalogs(self) -> set:
        try:
            return {r[0] for r in self.spark.sql("SHOW CATALOGS").collect()}
        except Exception:  # noqa: BLE001
            return set()

    def context(self) -> dict:
        out = {}
        for key, sql in (("metastore_id", "SELECT current_metastore() AS v"),
                         ("runner_principal", "SELECT current_user() AS v")):
            try:
                out[key] = self.spark.sql(sql).collect()[0]["v"]
            except Exception:  # noqa: BLE001
                out[key] = None
        out["account_id"] = out.get("metastore_id")
        return out

    def write(self, fqn: str, cols: list, rows: list) -> None:
        if not rows:
            return
        schema = self.spark.table(fqn).schema
        target = [f.name for f in schema.fields]
        norm = [{c: r.get(c) for c in target} for r in rows]
        self.spark.createDataFrame(norm, schema=schema).write.mode("append").saveAsTable(fqn)
