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


def register(check, BRONZE_RX, GOLD_RX, EMAIL_RX) -> None:
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

    # ------------------------------------------------------------------
    # Wave 3
    # ------------------------------------------------------------------

    check(
        "tagging-strategy",
        unit="relations",
        requires={"system.information_schema.tables":
                  ["table_catalog", "table_schema", "table_name"],
                  "system.information_schema.table_tags":
                  ["catalog_name", "schema_name", "table_name"]},
        note=("Conforming = the relation carries a tag of its own, or inherits one "
              "from a tagged schema or catalog. Tag coverage is the measurable half "
              "of the pattern; near-duplicate tag KEYS need the Tag Policies API."),
        measure="""
            SELECT
              COUNT_IF(tt.table_name IS NOT NULL
                       OR st.schema_name IS NOT NULL
                       OR ct.catalog_name IS NOT NULL) AS numerator,
              COUNT(*) AS denominator
            FROM system.information_schema.tables t
            LEFT JOIN (SELECT DISTINCT catalog_name, schema_name, table_name
                       FROM system.information_schema.table_tags) tt
              ON  tt.catalog_name = t.table_catalog AND tt.schema_name = t.table_schema
              AND tt.table_name = t.table_name
            LEFT JOIN (SELECT DISTINCT catalog_name, schema_name
                       FROM system.information_schema.schema_tags) st
              ON  st.catalog_name = t.table_catalog AND st.schema_name = t.table_schema
            LEFT JOIN (SELECT DISTINCT catalog_name
                       FROM system.information_schema.catalog_tags) ct
              ON  ct.catalog_name = t.table_catalog
            WHERE t.table_catalog NOT IN ({excluded})
              AND t.table_schema <> 'information_schema'
        """,
        findings="""
            SELECT 'TABLE' AS object_type,
                   CONCAT_WS('.', t.table_catalog, t.table_schema, t.table_name) AS object_id,
                   CONCAT_WS('.', t.table_catalog, t.table_schema, t.table_name) AS object_name,
                   t.table_owner AS owner,
                   'untagged' AS metric_name, 1.0 AS metric_value
            FROM system.information_schema.tables t
            LEFT JOIN (SELECT DISTINCT catalog_name, schema_name, table_name
                       FROM system.information_schema.table_tags) tt
              ON  tt.catalog_name = t.table_catalog AND tt.schema_name = t.table_schema
              AND tt.table_name = t.table_name
            LEFT JOIN (SELECT DISTINCT catalog_name, schema_name
                       FROM system.information_schema.schema_tags) st
              ON  st.catalog_name = t.table_catalog AND st.schema_name = t.table_schema
            LEFT JOIN (SELECT DISTINCT catalog_name
                       FROM system.information_schema.catalog_tags) ct
              ON  ct.catalog_name = t.table_catalog
            WHERE t.table_catalog NOT IN ({excluded})
              AND t.table_schema <> 'information_schema'
              AND tt.table_name IS NULL AND st.schema_name IS NULL AND ct.catalog_name IS NULL
            LIMIT 500
        """,
    )

    check(
        "materialized-views-for-serving-layers",
        unit="gold relations",
        requires={"system.information_schema.tables":
                  ["table_catalog", "table_schema", "table_name", "table_type"]},
        note=("Scope is gold-layer relations, identified by schema or table naming - "
              "a heuristic. Conforming = anything but a plain VIEW: a materialized "
              "view, streaming table or managed table can serve a dashboard without "
              "recomputing the whole query on every load."),
        measure=f"""
            SELECT
              COUNT_IF(table_type <> 'VIEW') AS numerator,
              COUNT(*) AS denominator
            FROM system.information_schema.tables
            WHERE table_catalog NOT IN ({{excluded}})
              AND table_schema <> 'information_schema'
              AND (lower(table_schema) RLIKE '{GOLD_RX}' OR lower(table_name) RLIKE '{GOLD_RX}')
        """,
        findings=f"""
            SELECT 'VIEW' AS object_type,
                   CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_id,
                   CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_name,
                   table_owner AS owner,
                   'plain_view_in_gold' AS metric_name, 1.0 AS metric_value
            FROM system.information_schema.tables
            WHERE table_catalog NOT IN ({{excluded}})
              AND table_schema <> 'information_schema'
              AND (lower(table_schema) RLIKE '{GOLD_RX}' OR lower(table_name) RLIKE '{GOLD_RX}')
              AND table_type = 'VIEW'
            LIMIT 500
        """,
    )

    check(
        "third-party-bi-tool-integration",
        unit="BI tool queries",
        requires={"system.query.history":
                  ["start_time", "client_application", "executed_by"]},
        note=("Scope is queries from non-Databricks client applications. Conforming = "
              "run as a service principal rather than a personal account, which is "
              "the shared-credential failure the pattern warns about: a whole BI tool "
              "behind one human's identity loses per-user attribution and breaks when "
              "that person leaves."),
        measure=f"""
            SELECT
              COUNT_IF(executed_by IS NOT NULL AND NOT executed_by RLIKE '{EMAIL_RX}') AS numerator,
              COUNT(*) AS denominator
            FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
              AND client_application IS NOT NULL
              AND client_application NOT LIKE 'Databricks%'
              AND client_application NOT IN ('unknown', '', 'SPARK_CONNECT', 'JobRun', 'DatabricksGenie')
        """,
    )

    check(
        "data-copies-instead-of-sharing",
        unit="write statements",
        requires={"system.query.history": ["start_time", "statement_text", "statement_type"]},
        note=("Conforming = a write that stays inside the lakehouse. Exporting to an "
              "external path or directory is the copy the pattern argues against, "
              "since a copy is stale the moment it lands and carries no grants."),
        measure="""
            SELECT
              COUNT_IF(NOT lower(statement_text) RLIKE
                       '(insert +overwrite +directory|copy +into +[^ ]*(s3|abfss|gs|wasbs)://|location +.(s3|abfss|gs|wasbs)://)') AS numerator,
              COUNT(*) AS denominator
            FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              AND statement_text IS NOT NULL
              AND statement_type IN ('INSERT', 'CREATE', 'REPLACE', 'MERGE', 'UPDATE')
        """,
        findings="""
            SELECT 'QUERY' AS object_type, statement_id AS object_id,
                   SUBSTRING(statement_text, 1, 200) AS object_name,
                   executed_by AS owner,
                   'external_copy' AS metric_name, 1.0 AS metric_value
            FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              AND statement_text IS NOT NULL
              AND statement_type IN ('INSERT', 'CREATE', 'REPLACE', 'MERGE', 'UPDATE')
              AND lower(statement_text) RLIKE
                  '(insert +overwrite +directory|copy +into +[^ ]*(s3|abfss|gs|wasbs)://|location +.(s3|abfss|gs|wasbs)://)'
            LIMIT 500
        """,
    )

    check(
        "compute-right-sizing",
        unit="clusters",
        requires={"system.compute.node_timeline":
                  ["cluster_id", "start_time", "cpu_user_percent"]},
        note=("Conforming = average CPU utilisation at or above 20% over the window. "
              "Below that the cluster is paying for cores it never uses. Needs "
              "node_timeline, which only has rows for classic compute - a "
              "serverless-only workspace has nothing to size."),
        measure="""
            WITH per_cluster AS (
              SELECT cluster_id, AVG(cpu_user_percent) AS avg_cpu
              FROM system.compute.node_timeline
              WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              GROUP BY cluster_id
            )
            SELECT COUNT_IF(avg_cpu >= 20.0) AS numerator, COUNT(*) AS denominator
            FROM per_cluster
        """,
        findings="""
            WITH per_cluster AS (
              SELECT cluster_id, AVG(cpu_user_percent) AS avg_cpu
              FROM system.compute.node_timeline
              WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
              GROUP BY cluster_id
            )
            SELECT 'CLUSTER' AS object_type, cluster_id AS object_id,
                   cluster_id AS object_name, NULL AS owner,
                   'avg_cpu_user_percent' AS metric_name, avg_cpu AS metric_value
            FROM per_cluster WHERE avg_cpu < 20.0
            LIMIT 500
        """,
    )

    # ------------------------------------------------------------------
    # Wave 4
    # ------------------------------------------------------------------

    check(
        "deploy-code-not-models",
        unit="MLflow runs",
        requires={"system.mlflow.runs_latest": ["run_id", "created_by", "start_time"]},
        note=("Conforming = the training run was created by an automation principal, "
              "not a person. A model whose runs all originate from an individual was "
              "trained by hand somewhere and carried forward, which is the artifact "
              "promotion the pattern argues against."),
        measure=f"""
            SELECT
              COUNT_IF(created_by IS NOT NULL AND NOT created_by RLIKE '{EMAIL_RX}') AS numerator,
              COUNT(*) AS denominator
            FROM system.mlflow.runs_latest
            WHERE delete_time IS NULL
              AND start_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
        """,
        findings=f"""
            SELECT 'MLFLOW_RUN' AS object_type, run_id AS object_id,
                   COALESCE(run_name, run_id) AS object_name, created_by AS owner,
                   'personal_training_run' AS metric_name, 1.0 AS metric_value
            FROM system.mlflow.runs_latest
            WHERE delete_time IS NULL
              AND start_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
              AND (created_by IS NULL OR created_by RLIKE '{EMAIL_RX}')
            LIMIT 500
        """,
    )

    check(
        "cicd-for-ml-pipelines",
        unit="ML jobs",
        requires={"system.lakeflow.jobs":
                  ["job_id", "name", "deployment", "run_as_user_name", "delete_time"]},
        note=("Scope is jobs whose name suggests training, inference or feature work "
              "- a heuristic. Conforming = deployed from a bundle rather than created "
              "by hand in the UI, which is the reconciliation the pattern asks for."),
        measure="""
            WITH latest AS (
              SELECT job_id,
                     MAX_BY(name, change_time) AS name,
                     MAX_BY(deployment, change_time) AS deployment,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.jobs
              GROUP BY job_id
            )
            SELECT COUNT_IF(deployment IS NOT NULL) AS numerator, COUNT(*) AS denominator
            FROM latest
            WHERE delete_time IS NULL
              AND lower(name) RLIKE '(train|model|ml[_ -]|inference|feature|mlflow|predict)'
        """,
    )

    check(
        "genai-evaluation-and-human-feedback",
        unit="experiments",
        requires={"system.mlflow.experiments_latest": ["experiment_id", "name"],
                  "system.mlflow.runs_latest": ["experiment_id", "start_time"]},
        note=("Conforming = the experiment has at least one run inside the window. "
              "An experiment serving production traffic with no recent runs has no "
              "live evaluation behind it, which is the finding the pattern names."),
        measure="""
            WITH ex AS (
              SELECT experiment_id, name FROM system.mlflow.experiments_latest
              WHERE delete_time IS NULL
            ),
            recent AS (
              SELECT DISTINCT experiment_id FROM system.mlflow.runs_latest
              WHERE delete_time IS NULL
                AND start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            )
            SELECT COUNT(r.experiment_id) AS numerator, COUNT(*) AS denominator
            FROM ex LEFT JOIN recent r ON r.experiment_id = ex.experiment_id
        """,
        findings="""
            WITH ex AS (
              SELECT experiment_id, name FROM system.mlflow.experiments_latest
              WHERE delete_time IS NULL
            ),
            recent AS (
              SELECT DISTINCT experiment_id FROM system.mlflow.runs_latest
              WHERE delete_time IS NULL
                AND start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            )
            SELECT 'EXPERIMENT' AS object_type, ex.experiment_id AS object_id,
                   ex.name AS object_name, NULL AS owner,
                   'no_recent_runs' AS metric_name, 1.0 AS metric_value
            FROM ex LEFT JOIN recent r ON r.experiment_id = ex.experiment_id
            WHERE r.experiment_id IS NULL
            LIMIT 500
        """,
    )

    check(
        "genai-readiness-foundations",
        unit="GenAI capabilities",
        requires={"system.billing.usage": ["usage_date", "billing_origin_product"]},
        note=("Readiness measured as breadth: how many of the GenAI building blocks "
              "show any billed usage in the window. Deliberately a capability count "
              "rather than a quality measure - the pattern is about having the "
              "foundations at all."),
        measure="""
            WITH expected AS (
              SELECT explode(array('MODEL_SERVING', 'VECTOR_SEARCH', 'AI_GATEWAY',
                                   'GENIE', 'APPS', 'AGENT_BRICKS')) AS product
            ),
            seen AS (
              SELECT DISTINCT billing_origin_product AS product
              FROM system.billing.usage
              WHERE usage_date >= CURRENT_DATE() - INTERVAL {lookback} DAYS
            )
            SELECT COUNT(s.product) AS numerator, COUNT(*) AS denominator
            FROM expected e LEFT JOIN seen s ON s.product = e.product
        """,
    )

    check(
        "security-analysis-tool-baseline",
        unit="SAT installation",
        requires={"system.lakeflow.jobs": ["job_id", "name"],
                  "system.information_schema.schemata": ["catalog_name", "schema_name"]},
        note=("Binary: is the Security Analysis Tool installed at all. Detected by a "
              "SAT job or a SAT output schema. If it is not installed, running it is "
              "itself the pattern's recommendation, so there is nothing partial to "
              "measure."),
        measure="""
            WITH found AS (
              SELECT 1 AS hit FROM system.lakeflow.jobs
              WHERE delete_time IS NULL
                AND lower(name) RLIKE '(security[_ -]analysis[_ -]tool|\\\\bsat\\\\b[_ -]|security_analysis)'
              UNION ALL
              SELECT 1 FROM system.information_schema.schemata
              WHERE lower(schema_name) RLIKE '(security_analysis|^sat$|sat_)'
            )
            SELECT LEAST(COUNT(*), 1) AS numerator, 1 AS denominator FROM found
        """,
    )

    check(
        "separate-ingestion-and-transformation-pipelines",
        unit="pipelines",
        requires={"system.access.table_lineage":
                  ["entity_type", "entity_id", "target_table_schema", "event_time"]},
        note=("Conforming = a pipeline whose write targets do not span bronze AND "
              "gold. One pipeline writing to both is doing ingestion and "
              "transformation at once, which is the coupling the pattern warns "
              "about. Layers identified by schema or table naming - a heuristic."),
        measure=f"""
            WITH writes AS (
              SELECT entity_id,
                     MAX(CASE WHEN lower(target_table_schema) RLIKE '{BRONZE_RX}'
                               OR lower(target_table_name) RLIKE '{BRONZE_RX}' THEN 1 ELSE 0 END) AS hits_bronze,
                     MAX(CASE WHEN lower(target_table_schema) RLIKE '{GOLD_RX}'
                               OR lower(target_table_name) RLIKE '{GOLD_RX}' THEN 1 ELSE 0 END) AS hits_gold
              FROM system.access.table_lineage
              WHERE entity_type = 'PIPELINE'
                AND entity_id IS NOT NULL
                AND target_table_full_name IS NOT NULL
                AND event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
              GROUP BY entity_id
            )
            SELECT COUNT_IF(NOT (hits_bronze = 1 AND hits_gold = 1)) AS numerator,
                   COUNT(*) AS denominator
            FROM writes
        """,
        findings=f"""
            WITH writes AS (
              SELECT entity_id,
                     MAX(CASE WHEN lower(target_table_schema) RLIKE '{BRONZE_RX}'
                               OR lower(target_table_name) RLIKE '{BRONZE_RX}' THEN 1 ELSE 0 END) AS hits_bronze,
                     MAX(CASE WHEN lower(target_table_schema) RLIKE '{GOLD_RX}'
                               OR lower(target_table_name) RLIKE '{GOLD_RX}' THEN 1 ELSE 0 END) AS hits_gold
              FROM system.access.table_lineage
              WHERE entity_type = 'PIPELINE'
                AND entity_id IS NOT NULL
                AND target_table_full_name IS NOT NULL
                AND event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
              GROUP BY entity_id
            )
            SELECT 'PIPELINE' AS object_type, entity_id AS object_id,
                   entity_id AS object_name, NULL AS owner,
                   'writes_bronze_and_gold' AS metric_name, 1.0 AS metric_value
            FROM writes WHERE hits_bronze = 1 AND hits_gold = 1
            LIMIT 500
        """,
    )

    # ------------------------------------------------------------------
    # Wave 5 - filed WORKSPACE_API in the registry, but measurable from
    # system tables after all. Job settings are in system.lakeflow.jobs;
    # only notification routing needs the Jobs API.
    # ------------------------------------------------------------------

    check(
        "unbounded-task-execution",
        unit="jobs",
        requires={"system.lakeflow.jobs":
                  ["job_id", "timeout_seconds", "health_rules", "change_time", "delete_time"]},
        note=("Conforming = the job has a bound of some kind: a timeout, or a "
              "duration health rule. health_rules is an array and arrives as an "
              "empty array rather than NULL, so emptiness is size() = 0 - IS NOT "
              "NULL would pass every job."),
        measure="""
            WITH latest AS (
              SELECT job_id,
                     MAX_BY(name, change_time) AS name,
                     MAX_BY(timeout_seconds, change_time) AS timeout_seconds,
                     MAX_BY(health_rules, change_time) AS health_rules,
                     MAX_BY(run_as_user_name, change_time) AS run_as_user_name,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.jobs GROUP BY job_id
            )
            SELECT
              COUNT_IF(COALESCE(timeout_seconds, 0) > 0
                       OR size(COALESCE(health_rules, array())) > 0) AS numerator,
              COUNT(*) AS denominator
            FROM latest WHERE delete_time IS NULL
        """,
        findings="""
            WITH latest AS (
              SELECT job_id,
                     MAX_BY(name, change_time) AS name,
                     MAX_BY(timeout_seconds, change_time) AS timeout_seconds,
                     MAX_BY(health_rules, change_time) AS health_rules,
                     MAX_BY(run_as_user_name, change_time) AS run_as_user_name,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.jobs GROUP BY job_id
            )
            SELECT 'JOB' AS object_type, CAST(job_id AS STRING) AS object_id,
                   name AS object_name, run_as_user_name AS owner,
                   'no_timeout_or_duration_rule' AS metric_name, 1.0 AS metric_value
            FROM latest
            WHERE delete_time IS NULL
              AND COALESCE(timeout_seconds, 0) = 0
              AND size(COALESCE(health_rules, array())) = 0
            LIMIT 500
        """,
    )

    check(
        "git-backed-development-and-cicd",
        unit="jobs",
        requires={"system.lakeflow.jobs":
                  ["job_id", "deployment", "change_time", "delete_time"]},
        note=("Conforming = the job was deployed from a bundle, which only happens "
              "when its definition lives in source control. A job created in the UI "
              "has no deployment and exists only in the workspace."),
        measure="""
            WITH latest AS (
              SELECT job_id,
                     MAX_BY(name, change_time) AS name,
                     MAX_BY(deployment, change_time) AS deployment,
                     MAX_BY(run_as_user_name, change_time) AS run_as_user_name,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.jobs GROUP BY job_id
            )
            SELECT COUNT_IF(deployment IS NOT NULL) AS numerator, COUNT(*) AS denominator
            FROM latest WHERE delete_time IS NULL
        """,
        findings="""
            WITH latest AS (
              SELECT job_id,
                     MAX_BY(name, change_time) AS name,
                     MAX_BY(deployment, change_time) AS deployment,
                     MAX_BY(run_as_user_name, change_time) AS run_as_user_name,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.jobs GROUP BY job_id
            )
            SELECT 'JOB' AS object_type, CAST(job_id AS STRING) AS object_id,
                   name AS object_name, run_as_user_name AS owner,
                   'not_bundle_deployed' AS metric_name, 1.0 AS metric_value
            FROM latest WHERE delete_time IS NULL AND deployment IS NULL
            LIMIT 500
        """,
    )

    check(
        "retries-and-timeouts-on-every-task",
        unit="job tasks",
        requires={"system.lakeflow.job_tasks":
                  ["job_id", "task_key", "timeout_seconds", "health_rules",
                   "change_time", "delete_time"]},
        note=("Per TASK, not per job - a job-level bound does not stop one task "
              "hanging. Conforming = the task has a timeout or a duration health "
              "rule. RETRIES are not in system tables and are NOT covered here; "
              "that half needs the Jobs API."),
        measure="""
            WITH latest AS (
              SELECT job_id, task_key,
                     MAX_BY(timeout_seconds, change_time) AS timeout_seconds,
                     MAX_BY(health_rules, change_time) AS health_rules,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.job_tasks GROUP BY job_id, task_key
            )
            SELECT
              COUNT_IF(COALESCE(timeout_seconds, 0) > 0
                       OR size(COALESCE(health_rules, array())) > 0) AS numerator,
              COUNT(*) AS denominator
            FROM latest WHERE delete_time IS NULL
        """,
        findings="""
            WITH latest AS (
              SELECT job_id, task_key,
                     MAX_BY(timeout_seconds, change_time) AS timeout_seconds,
                     MAX_BY(health_rules, change_time) AS health_rules,
                     MAX_BY(delete_time, change_time) AS delete_time
              FROM system.lakeflow.job_tasks GROUP BY job_id, task_key
            )
            SELECT 'JOB_TASK' AS object_type,
                   CONCAT(CAST(job_id AS STRING), ':', task_key) AS object_id,
                   CONCAT('job ', CAST(job_id AS STRING), ' task ', task_key) AS object_name,
                   NULL AS owner,
                   'no_task_timeout' AS metric_name, 1.0 AS metric_value
            FROM latest
            WHERE delete_time IS NULL
              AND COALESCE(timeout_seconds, 0) = 0
              AND size(COALESCE(health_rules, array())) = 0
            LIMIT 500
        """,
    )
