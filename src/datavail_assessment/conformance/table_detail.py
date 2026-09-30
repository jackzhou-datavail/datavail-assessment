"""Checks that need per-table Delta facts (registry tier TABLE_DETAIL).

Partition and clustering columns, file counts, table size and table
properties are not in system tables; the only source is DESCRIBE DETAIL,
one call per table. That is why this whole tier sat unimplemented behind
the reason "needs a per-object scan pass" - accurate, but it reads as a
blocker when it is really just a description of the work. The adoption
assessment already samples exactly this way.

One scan serves every check here. The runner calls each check
separately, so the sample is cached per executor rather than rescanned
six times.

Thresholds come from the pattern documents, not from taste:

    1 TB     partitioning floor       over-partitioning.md
    ~100 MB  small-file threshold     small-file-accumulation.md
    7 days   vacuum retention floor   unmanaged-vacuum-retention.md

Each check takes the executor rather than a Spark session, so the same
code runs through a SQL warehouse or through a job.
"""

from __future__ import annotations

import json
import re

# Bounded on purpose: a workspace can hold tens of thousands of tables and
# this is one round trip each. Every check reports a percentage over the
# sample, which is what the SQL checks do over their own populations.
TABLE_SAMPLE_SIZE = 50

_ONE_TB = 1024 ** 4
_MIN_AVG_FILE_BYTES = 100 * 1024 ** 2   # 100 MB
_MIN_VACUUM_DAYS = 7
# Below this, file count says nothing useful and compaction would not pay
# for itself, so small-file accumulation is not judged.
_JUDGEABLE_BYTES = 1024 ** 3

_SAMPLE_CACHE: dict[int, list[dict]] = {}


def _coerce(value):
    """DESCRIBE DETAIL returns maps and arrays as JSON text through a SQL
    warehouse and as native objects through Spark. Normalise both."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if text in ("", "null", "NULL"):
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if text[0] in "[{":
        try:
            return json.loads(text)
        except Exception:  # noqa: BLE001 - malformed detail is not fatal
            return None
    return text


def _as_list(value) -> list:
    v = _coerce(value)
    if isinstance(v, list):
        return v
    return [] if v is None else [v]


def _as_map(value) -> dict:
    v = _coerce(value)
    return v if isinstance(v, dict) else {}


_INTERVAL = re.compile(r"(\d+(?:\.\d+)?)\s*(day|hour|week|minute)", re.I)
_UNIT_DAYS = {"day": 1.0, "hour": 1 / 24, "week": 7.0, "minute": 1 / 1440}


def _to_days(value):
    """Delta writes retention as 'interval 7 days'. Returns None when the
    property is absent or unparseable, which callers read as 'not
    explicitly set' rather than as a violation."""
    if value is None:
        return None
    m = _INTERVAL.search(str(value))
    if not m:
        return None
    return float(m.group(1)) * _UNIT_DAYS[m.group(2).lower()]


def table_sample(executor, params) -> list[dict]:
    """DESCRIBE DETAIL over a bounded sample of managed Delta tables."""
    key = id(executor)
    if key in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[key]

    rows = executor.query(
        "SELECT CONCAT_WS('.', table_catalog, table_schema, table_name) AS fq, "
        "       table_owner AS owner "
        "FROM system.information_schema.tables "
        "WHERE table_type = 'MANAGED' "
        "  AND data_source_format = 'DELTA' "
        "  AND table_schema != 'information_schema' "
        "  AND table_catalog NOT IN ('system', 'samples', '__databricks_internal') "
        f"LIMIT {TABLE_SAMPLE_SIZE}"
    )

    sample: list[dict] = []
    for r in rows:
        fq = r["fq"]
        try:
            detail = executor.query(f"DESCRIBE DETAIL {fq}")
        except Exception:  # noqa: BLE001 - an unreadable table is skipped, not fatal
            continue
        if not detail:
            continue
        d = detail[0]
        props = _as_map(d.get("properties"))
        sample.append({
            "fq": fq,
            "owner": r.get("owner"),
            "partitions": _as_list(d.get("partitionColumns")),
            "clustering": _as_list(d.get("clusteringColumns")),
            "features": [str(f).lower() for f in _as_list(d.get("tableFeatures"))],
            "num_files": int(d.get("numFiles") or 0),
            "size": int(d.get("sizeInBytes") or 0),
            "props": props,
            "vacuum_days": _to_days(props.get("delta.deletedFileRetentionDuration")),
            "log_days": _to_days(props.get("delta.logRetentionDuration")),
        })

    _SAMPLE_CACHE[key] = sample
    return sample


def _finding(t: dict, metric: str, value: float, detail: str) -> dict:
    return {
        "object_type": "TABLE",
        "object_id": t["fq"],
        "object_name": t["fq"],
        "owner": t.get("owner"),
        "metric_name": metric,
        "metric_value": float(value),
        "detail": detail[:500],
    }


def check_over_partitioning(executor, params):
    """Tables under 1 TB should not be partitioned at all.

    The threshold is the pattern's own: below 1 TB, Hive-style partitions
    cannot reach the recommended 1 GB per partition, so they make the
    layout strictly worse.
    """
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        den += 1
        if t["partitions"] and t["size"] < _ONE_TB:
            cols = ",".join(str(c) for c in t["partitions"])
            findings.append(_finding(
                t, "partitioned_below_1tb", t["size"],
                f"partitioned by {cols} at {t['size'] / 1024 ** 3:.1f} GB"))
        else:
            num += 1
    return num, den, findings


def check_liquid_clustering(executor, params):
    """Of the tables that made a layout choice, how many chose clustering.

    Tables with neither partitioning nor clustering are out of scope -
    they made no choice that could be wrong - so the denominator is
    tables that did one or the other.
    """
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        if not t["partitions"] and not t["clustering"]:
            continue
        den += 1
        if t["clustering"]:
            num += 1
        else:
            cols = ",".join(str(c) for c in t["partitions"])
            findings.append(_finding(
                t, "partitioned_not_clustered", t["size"],
                f"partitioned by {cols}, no clustering keys"))
    return num, den, findings


def check_small_files(executor, params):
    """Average file size against the pattern's ~100 MB floor."""
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        if t["size"] < _JUDGEABLE_BYTES or t["num_files"] < 1:
            continue
        den += 1
        avg = t["size"] / t["num_files"]
        if avg >= _MIN_AVG_FILE_BYTES:
            num += 1
        else:
            findings.append(_finding(
                t, "avg_file_bytes", avg,
                f"{t['num_files']} files averaging {avg / 1024 ** 2:.0f} MB"))
    return num, den, findings


def check_deletion_vectors(executor, params):
    """Deletion vectors enabled, by table feature or explicit property."""
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        den += 1
        prop = str(t["props"].get("delta.enableDeletionVectors", "")).lower()
        if "deletionvectors" in t["features"] or prop == "true":
            num += 1
        else:
            findings.append(_finding(
                t, "deletion_vectors_disabled", 1,
                "delta.enableDeletionVectors not set and the table feature is absent"))
    return num, den, findings


def check_vacuum_retention(executor, params):
    """Retention never below 7 days, which Databricks strongly recommends.

    Unset is conforming: the Delta default is already 7 days, so only an
    explicit lowering is a finding.
    """
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        den += 1
        days = t["vacuum_days"]
        if days is None or days >= _MIN_VACUUM_DAYS:
            num += 1
        else:
            findings.append(_finding(
                t, "vacuum_retention_days", days,
                f"delta.deletedFileRetentionDuration is {days:g} days, "
                f"below the {_MIN_VACUUM_DAYS}-day floor"))
    return num, den, findings


def check_retention_policy(executor, params):
    """An explicit retention decision, rather than silently inheriting the
    Delta defaults of 30-day log and 7-day deleted-file retention."""
    num = den = 0
    findings = []
    for t in table_sample(executor, params):
        den += 1
        if t["vacuum_days"] is not None or t["log_days"] is not None:
            num += 1
        else:
            findings.append(_finding(
                t, "no_explicit_retention", 1,
                "neither delta.logRetentionDuration nor "
                "delta.deletedFileRetentionDuration is set"))
    return num, den, findings
