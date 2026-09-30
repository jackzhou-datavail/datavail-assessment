"""Checks added after the first wave, registered into the same CHECKS dict.

`platform-usage-profile` was attempted and removed rather than shipped:
42k of 50k billing rows are NETWORKING and LAKEBASE infrastructure SKUs
that carry no workload id by design, and the serverless-jobs SKU billed
under SQL carries none either. Whether that is an attribution gap or a
metadata quirk of those SKUs could not be established, so there is no
defensible denominator. It stays impl: false.

Kept out of `checks.py` only to keep that file reviewable; these are
ordinary SYSTEM_TABLE checks in every other respect. `register()` is
called at the end of `checks.py` with its `check()` helper, so an entry
here is indistinguishable from one defined there.

Unlike the original wave, every query here was executed against a live
workspace before being committed, and every column was confirmed to
exist in `system.information_schema.columns` first. Two columns that
earlier checks assumed do not exist under the names the docs use -
`system.compute.clusters.delete_time` is not `deleted_time` - which is
why the confirmation step is worth keeping.

Note on map columns: `query_tags` and `custom_tags` are
`map<string,string>`, so emptiness is `size(...) = 0`, never `= ''`.
"""

from __future__ import annotations

# Column names that suggest data a mask or row filter should cover. A
# heuristic, and labelled as one in the check's note - there is no
# classification to join to unless the workspace runs UC classification.
SENSITIVE_COL_RX = (
    r"(email|e_mail|ssn|social_security|phone|mobile|dob|date_of_birth|birth_date"
    r"|salary|compensation|credit_card|card_number|passport|national_id|tax_id"
    r"|account_number|first_name|last_name|full_name|home_address)"
)

# Legacy access modes. Anything not single-user or shared cannot enforce
# Unity Catalog, so a cluster on one is a governance hole as well as a
# cost one.
LEGACY_SECURITY_MODES = "('NONE', 'LEGACY_PASSTHROUGH', 'LEGACY_TABLE_ACL', 'LEGACY_SINGLE_USER')"


def register(check) -> None:
    """Add this wave's checks to the shared CHECKS registry."""

    # ------------------------------------------------------------------
    # Data Engineering
    # ------------------------------------------------------------------

    check(
        "sla-tracking-and-data-freshness",
        unit="job runs",
        requires={"system.lakeflow.job_run_timeline":
                  ["job_id", "run_id", "result_state", "period_end_time"]},
        note=("Pipeline-side SLA attainment: the share of terminal job runs that "
              "succeeded, which is the rollup the pattern describes. Table-side "
              "freshness needs system.data_quality_monitoring, which only exists "
              "once anomaly detection is enabled."),
        measure="""
            SELECT
              COUNT_IF(result_state = 'SUCCEEDED') AS numerator,
              COUNT(*) AS denominator
            FROM system.lakeflow.job_run_timeline
            WHERE period_end_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              AND result_state IS NOT NULL
        """,
        findings="""
            SELECT 'JOB_RUN' AS object_type,
                   CAST(run_id AS STRING) AS object_id,
                   CONCAT('job ', CAST(job_id AS STRING)) AS object_name,
                   NULL AS owner,
                   'result_state' AS metric_name, 1.0 AS metric_value
            FROM system.lakeflow.job_run_timeline
            WHERE period_end_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              AND result_state IS NOT NULL
              AND result_state <> 'SUCCEEDED'
            LIMIT 500
        """,
    )

    # ------------------------------------------------------------------
    # Governance & Security
    # ------------------------------------------------------------------

    check(
        "row-filters-and-column-masks",
        unit="sensitive columns",
        requires={"system.information_schema.columns":
                  ["table_catalog", "table_schema", "table_name", "column_name"],
                  "system.information_schema.column_masks":
                  ["table_catalog", "table_schema", "table_name", "column_name"]},
        note=("Scope is columns whose NAME suggests personal or sensitive data - a "
              "heuristic, not a classification. Conforming = that column carries a "
              "mask, or its table carries a row filter."),
        measure=f"""
            WITH sensitive AS (
              SELECT c.table_catalog, c.table_schema, c.table_name, c.column_name
              FROM system.information_schema.columns c
              WHERE c.table_catalog NOT IN ({{excluded}})
                AND c.table_schema <> 'information_schema'
                AND lower(c.column_name) RLIKE '{SENSITIVE_COL_RX}'
            )
            SELECT
              COUNT_IF(m.column_name IS NOT NULL OR f.table_name IS NOT NULL) AS numerator,
              COUNT(*) AS denominator
            FROM sensitive s
            LEFT JOIN system.information_schema.column_masks m
              ON  m.table_catalog = s.table_catalog AND m.table_schema = s.table_schema
              AND m.table_name = s.table_name AND m.column_name = s.column_name
            LEFT JOIN system.information_schema.row_filters f
              ON  f.table_catalog = s.table_catalog AND f.table_schema = s.table_schema
              AND f.table_name = s.table_name
        """,
        findings=f"""
            WITH sensitive AS (
              SELECT c.table_catalog, c.table_schema, c.table_name, c.column_name
              FROM system.information_schema.columns c
              WHERE c.table_catalog NOT IN ({{excluded}})
                AND c.table_schema <> 'information_schema'
                AND lower(c.column_name) RLIKE '{SENSITIVE_COL_RX}'
            )
            SELECT 'COLUMN' AS object_type,
                   CONCAT_WS('.', s.table_catalog, s.table_schema, s.table_name,
                             s.column_name) AS object_id,
                   CONCAT_WS('.', s.table_catalog, s.table_schema, s.table_name,
                             s.column_name) AS object_name,
                   NULL AS owner,
                   'unmasked_sensitive_column' AS metric_name, 1.0 AS metric_value
            FROM sensitive s
            LEFT JOIN system.information_schema.column_masks m
              ON  m.table_catalog = s.table_catalog AND m.table_schema = s.table_schema
              AND m.table_name = s.table_name AND m.column_name = s.column_name
            LEFT JOIN system.information_schema.row_filters f
              ON  f.table_catalog = s.table_catalog AND f.table_schema = s.table_schema
              AND f.table_name = s.table_name
            WHERE m.column_name IS NULL AND f.table_name IS NULL
            LIMIT 500
        """,
    )

    check(
        "security-audit-monitoring",
        unit="weeks",
        requires={"system.query.history": ["statement_text", "start_time"]},
        note=("The pattern's point is that a log nobody reads detects nothing, so "
              "this measures whether anyone queries the audit log - weeks in the "
              "window with at least one query against system.access.audit. Weekly "
              "rather than daily because a weekly review is a defensible cadence."),
        measure="""
            WITH weeks AS (
              SELECT explode(sequence(
                       date_trunc('WEEK', CURRENT_DATE() - INTERVAL {lookback} DAYS),
                       date_trunc('WEEK', CURRENT_DATE()),
                       INTERVAL 1 WEEK)) AS wk
            ),
            seen AS (
              SELECT DISTINCT date_trunc('WEEK', start_time) AS wk
              FROM system.query.history
              WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
                AND statement_text IS NOT NULL
                AND lower(statement_text) LIKE '%system.access.audit%'
            )
            SELECT COUNT(s.wk) AS numerator, COUNT(*) AS denominator
            FROM weeks w LEFT JOIN seen s ON s.wk = w.wk
        """,
    )

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------

    check(
        "misconfigured-classic-compute",
        unit="clusters",
        requires={"system.compute.clusters":
                  ["cluster_id", "change_time", "delete_time",
                   "auto_termination_minutes", "data_security_mode"]},
        note=("Latest row per cluster, still live. Conforming = auto-termination "
              "set between 1 and 120 minutes AND a Unity-Catalog-capable access "
              "mode. Null or zero auto-termination means it runs until someone "
              "notices."),
        measure=f"""
            WITH latest AS (
              SELECT cluster_id,
                     MAX_BY(delete_time, change_time) AS delete_time,
                     MAX_BY(auto_termination_minutes, change_time) AS autoterm,
                     MAX_BY(data_security_mode, change_time) AS mode,
                     MAX_BY(cluster_name, change_time) AS cluster_name,
                     MAX_BY(owned_by, change_time) AS owned_by
              FROM system.compute.clusters
              GROUP BY cluster_id
            )
            SELECT
              COUNT_IF(autoterm BETWEEN 1 AND 120
                       AND (mode IS NULL OR mode NOT IN {LEGACY_SECURITY_MODES})) AS numerator,
              COUNT(*) AS denominator
            FROM latest
            WHERE delete_time IS NULL
        """,
        findings=f"""
            WITH latest AS (
              SELECT cluster_id,
                     MAX_BY(delete_time, change_time) AS delete_time,
                     MAX_BY(auto_termination_minutes, change_time) AS autoterm,
                     MAX_BY(data_security_mode, change_time) AS mode,
                     MAX_BY(cluster_name, change_time) AS cluster_name,
                     MAX_BY(owned_by, change_time) AS owned_by
              FROM system.compute.clusters
              GROUP BY cluster_id
            )
            SELECT 'CLUSTER' AS object_type, cluster_id AS object_id,
                   cluster_name AS object_name, owned_by AS owner,
                   'auto_termination_minutes' AS metric_name,
                   COALESCE(CAST(autoterm AS DOUBLE), 0.0) AS metric_value
            FROM latest
            WHERE delete_time IS NULL
              AND NOT (autoterm BETWEEN 1 AND 120
                       AND (mode IS NULL OR mode NOT IN {LEGACY_SECURITY_MODES}))
            LIMIT 500
        """,
    )

    check(
        "spend-trend-monitoring",
        unit="weeks",
        requires={"system.query.history": ["statement_text", "start_time"]},
        note=("Whether anyone actually looks at spend: weeks in the window with at "
              "least one query against system.billing.usage. A cost dashboard "
              "nobody opens is the same as no dashboard."),
        measure="""
            WITH weeks AS (
              SELECT explode(sequence(
                       date_trunc('WEEK', CURRENT_DATE() - INTERVAL {lookback} DAYS),
                       date_trunc('WEEK', CURRENT_DATE()),
                       INTERVAL 1 WEEK)) AS wk
            ),
            seen AS (
              SELECT DISTINCT date_trunc('WEEK', start_time) AS wk
              FROM system.query.history
              WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
                AND statement_text IS NOT NULL
                AND lower(statement_text) LIKE '%system.billing.usage%'
            )
            SELECT COUNT(s.wk) AS numerator, COUNT(*) AS denominator
            FROM weeks w LEFT JOIN seen s ON s.wk = w.wk
        """,
    )

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    check(
        "cost-per-query-attribution",
        unit="warehouse queries",
        requires={"system.query.history":
                  ["start_time", "query_tags", "executed_by", "compute"]},
        note=("Attributing warehouse cost to a team needs the query to carry a tag; "
              "query_tags is a map, so conforming = a non-empty map. Scope is "
              "warehouse queries, since cluster queries attribute via the cluster."),
        measure="""
            SELECT
              COUNT_IF(query_tags IS NOT NULL AND size(query_tags) > 0) AS numerator,
              COUNT(*) AS denominator
            FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              AND compute.warehouse_id IS NOT NULL
        """,
    )
