"""Check definitions — how each implementable pattern is measured.

Each entry declares the system objects it needs (`requires`) and a
`measure` query returning exactly one row with `numerator` (objects
following the good practice) and `denominator` (objects in scope).
Optional `findings` returns the offending objects as evidence.

IMPORTANT — none of this SQL has been executed against a live
workspace. Column names were taken from Databricks system-table
documentation where available and inferred from schema descriptions
otherwise. Anything wrong degrades to NOT_AVAILABLE via the `requires`
preflight, naming the missing object, rather than failing the run or
inflating a score.

Placeholders substituted before execution:
  {lookback}      integer days
  {excluded}      quoted, comma-separated catalog names to skip

Several checks rely on naming heuristics (a "bronze" or "gold" layer is
identified by schema or table name). Those are approximations and are
labelled as such in the pattern's `reason`/detail so a reader does not
mistake them for exact measurements.
"""

# Regexes used across checks to classify objects by naming convention.
BRONZE_RX = r"(^|[._])(bronze|raw|landing|stg|staging)([._]|$)"
GOLD_RX = r"(^|[._])(gold|mart|semantic|reporting|presentation)([._]|$)"
EMAIL_RX = r"^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$"

CHECKS: dict[str, dict] = {}


def check(pattern_id, unit, requires, measure, findings=None, note=None):
    CHECKS[pattern_id] = {
        "unit": unit,
        "requires": requires,
        "measure": measure,
        "findings": findings,
        "note": note,
    }


# ======================================================================
# Unity Catalog governance
# ======================================================================

check(
    "unowned-catalog-objects",
    unit="tables",
    requires={"system.information_schema.tables": ["table_catalog", "table_schema", "table_name", "table_owner"]},
    note="Conforming = owned by a group or service principal (owner does not look like a personal email).",
    measure=f"""
        SELECT
          COUNT_IF(table_owner IS NOT NULL AND NOT table_owner RLIKE '{EMAIL_RX}') AS numerator,
          COUNT(*) AS denominator
        FROM system.information_schema.tables
        WHERE table_catalog NOT IN ({{excluded}})
          AND table_schema <> 'information_schema'
    """,
    findings=f"""
        SELECT 'TABLE' AS object_type,
               CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_id,
               CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_name,
               table_owner AS owner,
               'personal_owner' AS metric_name, 1.0 AS metric_value
        FROM system.information_schema.tables
        WHERE table_catalog NOT IN ({{excluded}})
          AND table_schema <> 'information_schema'
          AND (table_owner IS NULL OR table_owner RLIKE '{EMAIL_RX}')
        LIMIT 500
    """,
)

check(
    "legacy-hive-metastore-usage",
    unit="queries",
    requires={"system.query.history": ["statement_text", "start_time", "statement_id"]},
    note="Conforming = statements that do not reference hive_metastore or dbfs:/ paths.",
    measure="""
        SELECT
          COUNT_IF(NOT lower(statement_text) RLIKE '(hive_metastore|dbfs:/)') AS numerator,
          COUNT(*) AS denominator
        FROM system.query.history
        WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
          AND statement_text IS NOT NULL
    """,
    findings="""
        SELECT 'QUERY' AS object_type, statement_id AS object_id,
               SUBSTRING(statement_text, 1, 200) AS object_name,
               executed_by_user_id AS owner,
               'legacy_reference' AS metric_name, 1.0 AS metric_value
        FROM system.query.history
        WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
          AND lower(statement_text) RLIKE '(hive_metastore|dbfs:/)'
        LIMIT 500
    """,
)

check(
    "unclassified-sensitive-data",
    unit="tables",
    requires={"system.data_classification.results": ["table_full_name"]},
    note="Conforming = table has been scanned by automated classification.",
    measure="""
        WITH scanned AS (
          SELECT DISTINCT lower(table_full_name) AS fq FROM system.data_classification.results
        ), t AS (
          SELECT lower(CONCAT_WS('.', table_catalog, table_schema, table_name)) AS fq
          FROM system.information_schema.tables
          WHERE table_catalog NOT IN ({excluded}) AND table_schema <> 'information_schema'
        )
        SELECT COUNT_IF(s.fq IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM t LEFT JOIN scanned s ON s.fq = t.fq
    """,
)

check(
    "automated-pii-classification",
    unit="tables",
    requires={"system.data_classification.results": ["table_full_name"]},
    note="Same source as unclassified-sensitive-data; measures scan coverage.",
    measure="""
        WITH scanned AS (
          SELECT DISTINCT lower(table_full_name) AS fq FROM system.data_classification.results
        ), t AS (
          SELECT lower(CONCAT_WS('.', table_catalog, table_schema, table_name)) AS fq
          FROM system.information_schema.tables
          WHERE table_catalog NOT IN ({excluded}) AND table_schema <> 'information_schema'
        )
        SELECT COUNT_IF(s.fq IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM t LEFT JOIN scanned s ON s.fq = t.fq
    """,
)

# ======================================================================
# Data ingestion / layering
# ======================================================================

check(
    "direct-writes-to-bronze-tables",
    unit="writes",
    requires={"system.access.table_lineage": ["target_table_full_name", "entity_type", "event_time"]},
    note="Conforming = writes to bronze/raw tables originating from a job or pipeline, not an interactive notebook or SQL query.",
    measure=f"""
        SELECT
          COUNT_IF(entity_type IS NULL OR entity_type NOT IN ('NOTEBOOK', 'DBSQL_QUERY')) AS numerator,
          COUNT(*) AS denominator
        FROM system.access.table_lineage
        WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
          AND target_table_full_name IS NOT NULL
          AND lower(target_table_full_name) RLIKE '{BRONZE_RX}'
    """,
    findings=f"""
        SELECT 'TABLE' AS object_type, target_table_full_name AS object_id,
               target_table_full_name AS object_name,
               created_by AS owner,
               'adhoc_writes' AS metric_name, COUNT(*) * 1.0 AS metric_value
        FROM system.access.table_lineage
        WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
          AND lower(target_table_full_name) RLIKE '{BRONZE_RX}'
          AND entity_type IN ('NOTEBOOK', 'DBSQL_QUERY')
        GROUP BY target_table_full_name, created_by
        ORDER BY metric_value DESC
        LIMIT 500
    """,
)

check(
    "bronze-layer-immutability",
    unit="tables",
    requires={"system.access.table_lineage": ["target_table_full_name", "entity_type", "event_time"]},
    note="Conforming = bronze tables that received no interactive/ad-hoc writes in the window.",
    measure=f"""
        WITH w AS (
          SELECT lower(target_table_full_name) AS fq,
                 COUNT_IF(entity_type IN ('NOTEBOOK', 'DBSQL_QUERY')) AS adhoc
          FROM system.access.table_lineage
          WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
            AND lower(target_table_full_name) RLIKE '{BRONZE_RX}'
          GROUP BY lower(target_table_full_name)
        )
        SELECT COUNT_IF(adhoc = 0) AS numerator, COUNT(*) AS denominator FROM w
    """,
)

check(
    "full-reload-instead-of-incremental",
    unit="statements",
    requires={"system.query.history": ["statement_text", "start_time"]},
    note="Conforming = write statements that are not full-table overwrites.",
    measure="""
        WITH w AS (
          SELECT lower(statement_text) AS s
          FROM system.query.history
          WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            AND lower(statement_text) RLIKE '^\\\\s*(insert|create or replace table|merge|update|delete)'
        )
        SELECT COUNT_IF(NOT s RLIKE '(insert overwrite|create or replace table)') AS numerator,
               COUNT(*) AS denominator
        FROM w
    """,
)

# ======================================================================
# Table maintenance
# ======================================================================

check(
    "predictive-optimization-autopilot",
    unit="tables",
    requires={
        "system.storage.predictive_optimization_operations_history": ["metastore_name", "catalog_name", "schema_name", "table_name"],
    },
    note="Conforming = managed tables with at least one predictive optimization operation in the window.",
    measure="""
        WITH po AS (
          SELECT DISTINCT lower(CONCAT_WS('.', catalog_name, schema_name, table_name)) AS fq
          FROM system.storage.predictive_optimization_operations_history
        ), t AS (
          SELECT lower(CONCAT_WS('.', table_catalog, table_schema, table_name)) AS fq
          FROM system.information_schema.tables
          WHERE table_catalog NOT IN ({excluded})
            AND table_schema <> 'information_schema'
            AND table_type = 'MANAGED'
        )
        SELECT COUNT_IF(po.fq IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM t LEFT JOIN po ON po.fq = t.fq
    """,
)

# ======================================================================
# Platform: identity, compute, cost, IaC
# ======================================================================

_RUN_AS_MEASURE = f"""
    WITH w AS (
      SELECT run_as FROM (
        SELECT run_as, ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.jobs
      ) WHERE rn = 1
      UNION ALL
      SELECT run_as FROM (
        SELECT run_as, ROW_NUMBER() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.pipelines
      ) WHERE rn = 1
    )
    SELECT COUNT_IF(run_as IS NOT NULL AND NOT run_as RLIKE '{EMAIL_RX}') AS numerator,
           COUNT(*) AS denominator
    FROM w
"""

check(
    "personal-identity-in-production",
    unit="workloads",
    requires={
        "system.lakeflow.jobs": ["job_id", "run_as", "change_time"],
        "system.lakeflow.pipelines": ["pipeline_id", "run_as", "change_time"],
    },
    note="Conforming = job/pipeline run_as is a service principal (not a personal email).",
    measure=_RUN_AS_MEASURE,
    findings=f"""
        SELECT 'JOB' AS object_type, CAST(job_id AS STRING) AS object_id, name AS object_name,
               run_as AS owner, 'personal_run_as' AS metric_name, 1.0 AS metric_value
        FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) rn
              FROM system.lakeflow.jobs) WHERE rn = 1 AND run_as RLIKE '{EMAIL_RX}'
        LIMIT 500
    """,
)

check(
    "service-principals-for-automation",
    unit="workloads",
    requires={
        "system.lakeflow.jobs": ["job_id", "run_as", "change_time"],
        "system.lakeflow.pipelines": ["pipeline_id", "run_as", "change_time"],
    },
    note="Same measure as personal-identity-in-production, stated positively; shares root cause non-human-identity.",
    measure=_RUN_AS_MEASURE,
)

check(
    "compute-policies-and-standard-sizing",
    unit="clusters",
    requires={"system.compute.clusters": ["cluster_id", "policy_id", "delete_time"]},
    note="Conforming = classic cluster created under a compute policy.",
    measure="""
        WITH c AS (
          SELECT * FROM (
            SELECT cluster_id, policy_id, cluster_name, delete_time,
                   ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY change_time DESC) rn
            FROM system.compute.clusters
          ) WHERE rn = 1 AND delete_time IS NULL
        )
        SELECT COUNT_IF(policy_id IS NOT NULL) AS numerator, COUNT(*) AS denominator FROM c
    """,
)

check(
    "serverless-first-compute",
    unit="dbus",
    requires={"system.billing.usage": ["sku_name", "usage_quantity", "usage_date"]},
    note="Conforming = DBUs consumed on serverless SKUs.",
    measure="""
        SELECT
          CAST(SUM(CASE WHEN upper(sku_name) LIKE '%SERVERLESS%' THEN usage_quantity ELSE 0 END) AS BIGINT) AS numerator,
          CAST(SUM(usage_quantity) AS BIGINT) AS denominator
        FROM system.billing.usage
        WHERE usage_date >= CURRENT_DATE() - INTERVAL {lookback} DAYS
    """,
)

check(
    "all-purpose-compute-for-jobs",
    unit="dbus",
    requires={"system.billing.usage": ["sku_name", "usage_quantity", "usage_date"]},
    note="Conforming = DBUs NOT consumed on all-purpose SKUs.",
    measure="""
        SELECT
          CAST(SUM(CASE WHEN upper(sku_name) LIKE '%ALL_PURPOSE%' THEN 0 ELSE usage_quantity END) AS BIGINT) AS numerator,
          CAST(SUM(usage_quantity) AS BIGINT) AS denominator
        FROM system.billing.usage
        WHERE usage_date >= CURRENT_DATE() - INTERVAL {lookback} DAYS
    """,
)

_TAG_MEASURE = """
    SELECT
      CAST(SUM(CASE WHEN custom_tags IS NOT NULL AND size(map_keys(custom_tags)) > 0
                    THEN usage_quantity ELSE 0 END) AS BIGINT) AS numerator,
      CAST(SUM(usage_quantity) AS BIGINT) AS denominator
    FROM system.billing.usage
    WHERE usage_date >= CURRENT_DATE() - INTERVAL {lookback} DAYS
"""

check(
    "cost-attribution-tagging-and-budgets",
    unit="dbus",
    requires={"system.billing.usage": ["custom_tags", "usage_quantity", "usage_date"]},
    note="Conforming = DBUs whose usage records carry at least one custom tag. Budget configuration is NOT covered here (Account API).",
    measure=_TAG_MEASURE,
)

check(
    "untagged-unmonitored-spend",
    unit="dbus",
    requires={"system.billing.usage": ["custom_tags", "usage_quantity", "usage_date"]},
    note="Same measure as cost-attribution-tagging-and-budgets, stated as the anti-pattern.",
    measure=_TAG_MEASURE,
)

_BUNDLE_MEASURE = """
    WITH j AS (
      SELECT * FROM (
        SELECT job_id, name, creator_id, run_as,
               ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.jobs
      ) WHERE rn = 1
    )
    SELECT COUNT_IF(name RLIKE '^\\\\[[a-zA-Z0-9_-]+\\\\]') AS numerator,
           COUNT(*) AS denominator
    FROM j
"""

check(
    "infrastructure-as-code-terraform-and-bundles",
    unit="jobs",
    requires={"system.lakeflow.jobs": ["job_id", "name", "change_time"]},
    note="Heuristic: conforming = job name carries the '[target]' prefix that bundle deployment applies. Undercounts Terraform-managed jobs.",
    measure=_BUNDLE_MEASURE,
)

check(
    "manually-configured-workspaces",
    unit="jobs",
    requires={"system.lakeflow.jobs": ["job_id", "name", "change_time"]},
    note="Same heuristic as infrastructure-as-code-terraform-and-bundles, stated as the anti-pattern.",
    measure=_BUNDLE_MEASURE,
)

# ======================================================================
# ML & AI
# ======================================================================

# Only CUSTOM_MODEL entities can be Unity Catalog registered models.
# Databricks-hosted FOUNDATION_MODEL and provider EXTERNAL_MODEL entities
# are not, and counting them would manufacture a false finding.
_UC_MODEL_MEASURE = """
    WITH e AS (
      SELECT DISTINCT entity_name, endpoint_name
      FROM system.serving.served_entities
      WHERE entity_name IS NOT NULL AND upper(entity_type) = 'CUSTOM_MODEL'
    )
    SELECT COUNT_IF(size(split(entity_name, '\\\\.')) >= 3) AS numerator,
           COUNT(*) AS denominator
    FROM e
"""

check(
    "models-in-unity-catalog",
    unit="custom_models",
    requires={"system.serving.served_entities": ["entity_name", "endpoint_name", "entity_type"]},
    note="Conforming = served custom model resolves to a three-level Unity Catalog name. Foundation and external models are excluded; they are never UC-registered.",
    measure=_UC_MODEL_MEASURE,
    findings="""
        SELECT 'ENDPOINT' AS object_type, endpoint_name AS object_id,
               CONCAT(endpoint_name, ' -> ', entity_name) AS object_name,
               created_by AS owner, 'non_uc_model' AS metric_name, 1.0 AS metric_value
        FROM system.serving.served_entities
        WHERE entity_name IS NOT NULL AND upper(entity_type) = 'CUSTOM_MODEL'
          AND size(split(entity_name, '\\\\.')) < 3
        LIMIT 500
    """,
)

check(
    "legacy-workspace-model-registry",
    unit="custom_models",
    requires={"system.serving.served_entities": ["entity_name", "endpoint_name", "entity_type"]},
    note="Same measure as models-in-unity-catalog, stated as the anti-pattern.",
    measure=_UC_MODEL_MEASURE,
)

check(
    "mlflow-experiment-tracking",
    unit="experiments",
    requires={
        "system.mlflow.experiments_latest": ["experiment_id", "delete_time"],
        "system.mlflow.runs_latest": ["experiment_id", "run_id"],
    },
    note="Conforming = experiment has at least one recorded run.",
    measure="""
        WITH e AS (
          SELECT experiment_id FROM system.mlflow.experiments_latest WHERE delete_time IS NULL
        ), r AS (
          SELECT DISTINCT experiment_id FROM system.mlflow.runs_latest
        )
        SELECT COUNT_IF(r.experiment_id IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM e LEFT JOIN r USING (experiment_id)
    """,
)

check(
    "untracked-model-development",
    unit="runs",
    requires={"system.mlflow.runs_latest": ["run_id", "params", "aggregated_metrics", "start_time"]},
    note="Conforming = run logged both parameters and metrics.",
    measure="""
        SELECT
          COUNT_IF(params IS NOT NULL AND size(params) > 0
                   AND aggregated_metrics IS NOT NULL AND size(aggregated_metrics) > 0) AS numerator,
          COUNT(*) AS denominator
        FROM system.mlflow.runs_latest
        WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
    """,
)

check(
    "stale-models-in-production",
    unit="experiments",
    requires={"system.mlflow.experiments_latest": ["experiment_id", "name", "update_time", "delete_time"]},
    note="PROXY: conforming = experiment updated within the window. A direct endpoint-to-training-run join is not yet implemented.",
    measure="""
        SELECT
          COUNT_IF(update_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS) AS numerator,
          COUNT(*) AS denominator
        FROM system.mlflow.experiments_latest
        WHERE delete_time IS NULL
    """,
    findings="""
        SELECT 'EXPERIMENT' AS object_type, experiment_id AS object_id, name AS object_name,
               NULL AS owner, 'days_since_update' AS metric_name,
               DATEDIFF(CURRENT_DATE(), CAST(update_time AS DATE)) * 1.0 AS metric_value
        FROM system.mlflow.experiments_latest
        WHERE delete_time IS NULL
          AND update_time < CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
        ORDER BY metric_value DESC
        LIMIT 500
    """,
)

check(
    "gateway-governance-for-llm-endpoints",
    unit="endpoints",
    requires={
        "system.serving.served_entities": ["endpoint_name", "entity_type"],
        "system.ai_gateway.usage": ["endpoint_name"],
    },
    note="Conforming = serving endpoint appears in gateway usage, i.e. its traffic is governed.",
    measure="""
        WITH e AS (SELECT DISTINCT endpoint_name FROM system.serving.served_entities),
             g AS (SELECT DISTINCT endpoint_name FROM system.ai_gateway.usage)
        SELECT COUNT_IF(g.endpoint_name IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM e LEFT JOIN g USING (endpoint_name)
    """,
)

check(
    "ungoverned-external-llm-access",
    unit="endpoints",
    requires={
        "system.serving.served_entities": ["endpoint_name", "entity_type"],
        "system.ai_gateway.usage": ["endpoint_name"],
    },
    note="Scoped to EXTERNAL_MODEL endpoints, which is what this pattern is about. Direct provider SDK calls that bypass endpoints entirely are invisible here and need a repo scan.",
    measure="""
        WITH e AS (
          SELECT DISTINCT endpoint_name FROM system.serving.served_entities
          WHERE upper(entity_type) = 'EXTERNAL_MODEL'
        ), g AS (SELECT DISTINCT endpoint_name FROM system.ai_gateway.usage)
        SELECT COUNT_IF(g.endpoint_name IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM e LEFT JOIN g ON g.endpoint_name = e.endpoint_name
    """,
)

check(
    "inference-tables-and-drift-monitoring",
    unit="endpoints",
    requires={"system.serving.served_entities": ["endpoint_name", "inference_table_catalog", "inference_table_schema"]},
    note="Conforming = endpoint has an inference table configured.",
    measure="""
        WITH e AS (
          SELECT endpoint_name,
                 MAX(CASE WHEN inference_table_catalog IS NOT NULL THEN 1 ELSE 0 END) AS has_it
          FROM system.serving.served_entities
          GROUP BY endpoint_name
        )
        SELECT SUM(has_it) AS numerator, COUNT(*) AS denominator FROM e
    """,
)

check(
    "production-serving-endpoint-configuration",
    unit="endpoints",
    requires={"system.serving.served_entities": ["endpoint_name", "scale_to_zero_enabled"]},
    note="Conforming = endpoint does not scale to zero (not recommended for production).",
    measure="""
        WITH e AS (
          SELECT endpoint_name, MAX(CASE WHEN scale_to_zero_enabled THEN 1 ELSE 0 END) AS stz
          FROM system.serving.served_entities GROUP BY endpoint_name
        )
        SELECT COUNT_IF(stz = 0) AS numerator, COUNT(*) AS denominator FROM e
    """,
)

# ======================================================================
# SQL & analytics
# ======================================================================

check(
    "documented-tables-and-columns",
    unit="columns",
    requires={"system.information_schema.columns": ["table_catalog", "table_schema", "column_name", "comment"]},
    note="Conforming = column carries a comment longer than 3 characters that is not just the column name.",
    measure="""
        SELECT
          COUNT_IF(comment IS NOT NULL AND length(trim(comment)) > 3
                   AND lower(trim(comment)) <> lower(column_name)) AS numerator,
          COUNT(*) AS denominator
        FROM system.information_schema.columns
        WHERE table_catalog NOT IN ({excluded})
          AND table_schema <> 'information_schema'
    """,
    findings="""
        SELECT 'TABLE' AS object_type,
               CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_id,
               CONCAT_WS('.', table_catalog, table_schema, table_name) AS object_name,
               NULL AS owner, 'undocumented_columns' AS metric_name,
               COUNT(*) * 1.0 AS metric_value
        FROM system.information_schema.columns
        WHERE table_catalog NOT IN ({excluded})
          AND table_schema <> 'information_schema'
          AND (comment IS NULL OR length(trim(comment)) <= 3)
        GROUP BY table_catalog, table_schema, table_name
        ORDER BY metric_value DESC
        LIMIT 500
    """,
)

check(
    "serverless-sql-warehouses",
    unit="warehouses",
    requires={"system.compute.warehouses": ["warehouse_id", "warehouse_type", "delete_time", "change_time"]},
    note="Conforming = warehouse type is SERVERLESS.",
    measure="""
        WITH w AS (
          SELECT * FROM (
            SELECT warehouse_id, warehouse_type, warehouse_name, delete_time,
                   ROW_NUMBER() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) rn
            FROM system.compute.warehouses
          ) WHERE rn = 1 AND delete_time IS NULL
        )
        SELECT COUNT_IF(upper(warehouse_type) = 'SERVERLESS') AS numerator,
               COUNT(*) AS denominator FROM w
    """,
)

check(
    "always-on-oversized-warehouses",
    unit="warehouses",
    requires={
        "system.compute.warehouses": ["warehouse_id", "warehouse_name", "delete_time", "change_time"],
        "system.query.history": ["compute", "start_time"],
    },
    note=("PROXY: auto-stop and size-vs-load are not exposed by system.compute.warehouses, "
          "so this measures whether each live warehouse ran any query in the window. "
          "Idle-but-running warehouses are the detectable subset of this anti-pattern."),
    measure="""
        WITH w AS (
          SELECT warehouse_id, warehouse_name FROM (
            SELECT warehouse_id, warehouse_name, delete_time,
                   ROW_NUMBER() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) rn
            FROM system.compute.warehouses
          ) x WHERE rn = 1 AND delete_time IS NULL
        ), q AS (
          SELECT DISTINCT compute.warehouse_id AS wid
          FROM system.query.history
          WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            AND compute.warehouse_id IS NOT NULL
        )
        SELECT COUNT_IF(q.wid IS NOT NULL) AS numerator, COUNT(*) AS denominator
        FROM w LEFT JOIN q ON q.wid = w.warehouse_id
    """,
    findings="""
        WITH w AS (
          SELECT warehouse_id, warehouse_name FROM (
            SELECT warehouse_id, warehouse_name, delete_time,
                   ROW_NUMBER() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) rn
            FROM system.compute.warehouses
          ) x WHERE rn = 1 AND delete_time IS NULL
        ), q AS (
          SELECT DISTINCT compute.warehouse_id AS wid
          FROM system.query.history
          WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            AND compute.warehouse_id IS NOT NULL
        )
        SELECT 'WAREHOUSE' AS object_type, w.warehouse_id AS object_id,
               w.warehouse_name AS object_name, NULL AS owner,
               'no_queries_in_window' AS metric_name, 1.0 AS metric_value
        FROM w LEFT JOIN q ON q.wid = w.warehouse_id
        WHERE q.wid IS NULL
        LIMIT 500
    """,
)

check(
    "analytics-on-raw-tables",
    unit="reads",
    requires={"system.access.table_lineage": ["source_table_full_name", "entity_type", "event_time"]},
    note="Conforming = interactive/dashboard reads that target a non-bronze table.",
    measure=f"""
        SELECT
          COUNT_IF(NOT lower(source_table_full_name) RLIKE '{BRONZE_RX}') AS numerator,
          COUNT(*) AS denominator
        FROM system.access.table_lineage
        WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL {{lookback}} DAYS
          AND source_table_full_name IS NOT NULL
          AND entity_type IN ('NOTEBOOK', 'DBSQL_QUERY', 'DASHBOARD')
    """,
)

check(
    "medallion-layering-for-analytics",
    unit="tables",
    requires={"system.information_schema.tables": ["table_catalog", "table_schema", "table_name"]},
    note="Heuristic: conforming = table name or schema identifies a medallion layer, i.e. layering is expressed structurally.",
    measure=f"""
        SELECT
          COUNT_IF(lower(CONCAT_WS('.', table_schema, table_name)) RLIKE '{BRONZE_RX}'
                OR lower(CONCAT_WS('.', table_schema, table_name)) RLIKE '{GOLD_RX}'
                OR lower(table_schema) RLIKE '(silver|curated|refined|cleansed)') AS numerator,
          COUNT(*) AS denominator
        FROM system.information_schema.tables
        WHERE table_catalog NOT IN ({{excluded}}) AND table_schema <> 'information_schema'
    """,
)

check(
    "metric-views-as-semantic-layer",
    unit="gold_schemas",
    requires={"system.information_schema.tables": ["table_catalog", "table_schema", "table_type"]},
    note="Conforming = a gold/reporting schema that contains at least one metric view. Depends on METRIC_VIEW appearing as a table_type.",
    measure=f"""
        WITH s AS (
          SELECT table_catalog, table_schema,
                 MAX(CASE WHEN upper(table_type) LIKE '%METRIC%' THEN 1 ELSE 0 END) AS has_mv
          FROM system.information_schema.tables
          WHERE table_catalog NOT IN ({{excluded}})
            AND lower(table_schema) RLIKE '{GOLD_RX}'
          GROUP BY table_catalog, table_schema
        )
        SELECT SUM(has_mv) AS numerator, COUNT(*) AS denominator FROM s
    """,
)

_FOREIGN_MEASURE = """
    WITH f AS (
      SELECT DISTINCT lower(catalog_name) AS c
      FROM system.information_schema.catalogs
      WHERE upper(COALESCE(catalog_type, '')) LIKE '%FOREIGN%'
    ), q AS (
      SELECT lower(statement_text) AS s
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
        AND statement_text IS NOT NULL
    )
    SELECT COUNT_IF(NOT EXISTS (SELECT 1 FROM f WHERE q.s LIKE CONCAT('%', f.c, '.%'))) AS numerator,
           COUNT(*) AS denominator
    FROM q
"""

check(
    "federated-queries-in-production-pipelines",
    unit="queries",
    requires={
        "system.information_schema.catalogs": ["catalog_name", "catalog_type"],
        "system.query.history": ["statement_text", "start_time"],
    },
    note="Conforming = statements that do not read a foreign (federated) catalog. Does not yet separate scheduled from interactive callers.",
    measure=_FOREIGN_MEASURE,
)

check(
    "federation-for-ad-hoc-access",
    unit="queries",
    requires={
        "system.information_schema.catalogs": ["catalog_name", "catalog_type"],
        "system.query.history": ["statement_text", "start_time"],
    },
    note="Same measure as federated-queries-in-production-pipelines.",
    measure=_FOREIGN_MEASURE,
)

check(
    "scheduled-snapshot-rebuilds",
    unit="statements",
    requires={"system.query.history": ["statement_text", "start_time"]},
    note="Conforming = write statements that are not full replacements of a target table.",
    measure="""
        WITH w AS (
          SELECT lower(statement_text) AS s
          FROM system.query.history
          WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
            AND lower(statement_text) RLIKE '(insert|create or replace table|merge)'
        )
        SELECT COUNT_IF(NOT s RLIKE '(create or replace table|insert overwrite)') AS numerator,
               COUNT(*) AS denominator FROM w
    """,
)

check(
    "query-performance-fundamentals",
    unit="queries",
    requires={"system.query.history": ["start_time", "total_duration_ms", "read_bytes", "produced_rows"]},
    note="PROXY: conforming = query did not scan more than 1 GB while producing fewer than 1000 rows (a data-skipping failure signature).",
    measure="""
        SELECT
          COUNT_IF(NOT (read_bytes > 1073741824 AND COALESCE(produced_rows, 0) < 1000)) AS numerator,
          COUNT(*) AS denominator
        FROM system.query.history
        WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
          AND read_bytes IS NOT NULL
    """,
)

# ======================================================================
# Orchestration & reliability
# ======================================================================

check(
    "silent-job-failures",
    unit="job_runs",
    requires={"system.lakeflow.job_run_timeline": ["job_id", "result_state", "period_start_time"]},
    note="Conforming = job run that terminated successfully. A low rate indicates failures nobody is acting on.",
    measure="""
        SELECT COUNT_IF(upper(result_state) = 'SUCCEEDED') AS numerator,
               COUNT(*) AS denominator
        FROM system.lakeflow.job_run_timeline
        WHERE period_start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
          AND result_state IS NOT NULL
    """,
    findings="""
        SELECT 'JOB' AS object_type, CAST(job_id AS STRING) AS object_id,
               CAST(job_id AS STRING) AS object_name, NULL AS owner,
               'failed_runs' AS metric_name, COUNT(*) * 1.0 AS metric_value
        FROM system.lakeflow.job_run_timeline
        WHERE period_start_time >= CURRENT_TIMESTAMP() - INTERVAL {lookback} DAYS
          AND upper(result_state) IN ('FAILED', 'TIMED_OUT', 'ERROR')
        GROUP BY job_id
        ORDER BY metric_value DESC
        LIMIT 500
    """,
)

_DEPENDS_MEASURE = """
    WITH t AS (
      SELECT job_id, COUNT(*) AS n_tasks,
             COUNT_IF(depends_on_keys IS NOT NULL AND size(depends_on_keys) > 0) AS n_dep
      FROM system.lakeflow.job_tasks
      GROUP BY job_id
    )
    SELECT COUNT_IF(n_dep > 0) AS numerator, COUNT(*) AS denominator
    FROM t WHERE n_tasks > 1
"""

check(
    "task-dependencies-over-schedule-chaining",
    unit="multi_task_jobs",
    requires={"system.lakeflow.job_tasks": ["job_id", "task_key", "depends_on_keys"]},
    note="Conforming = multi-task job in which at least one task declares a dependency (order is enforced, not implied).",
    measure=_DEPENDS_MEASURE,
    findings="""
        WITH t AS (
          SELECT job_id, COUNT(*) AS n_tasks,
                 COUNT_IF(depends_on_keys IS NOT NULL AND size(depends_on_keys) > 0) AS n_dep
          FROM system.lakeflow.job_tasks GROUP BY job_id
        )
        SELECT 'JOB' AS object_type, CAST(job_id AS STRING) AS object_id,
               CAST(job_id AS STRING) AS object_name, NULL AS owner,
               'tasks_without_dependencies' AS metric_name, n_tasks * 1.0 AS metric_value
        FROM t WHERE n_tasks > 1 AND n_dep = 0
        ORDER BY metric_value DESC
        LIMIT 500
    """,
)

check(
    "schedule-chained-jobs",
    unit="multi_task_jobs",
    requires={"system.lakeflow.job_tasks": ["job_id", "task_key", "depends_on_keys"]},
    note="Same dependency measure, stated as the anti-pattern. Cross-job chaining via cron offsets needs a lineage join and is not yet implemented.",
    measure=_DEPENDS_MEASURE,
)

check(
    "monolithic-single-task-jobs",
    unit="jobs",
    requires={"system.lakeflow.job_tasks": ["job_id", "task_key"]},
    note="Conforming = job decomposed into more than one task, so failures are attributable and repair can restart mid-graph.",
    measure="""
        WITH t AS (SELECT job_id, COUNT(*) AS n_tasks FROM system.lakeflow.job_tasks GROUP BY job_id)
        SELECT COUNT_IF(n_tasks > 1) AS numerator, COUNT(*) AS denominator FROM t
    """,
    findings="""
        WITH t AS (SELECT job_id, COUNT(*) AS n_tasks FROM system.lakeflow.job_tasks GROUP BY job_id)
        SELECT 'JOB' AS object_type, CAST(t.job_id AS STRING) AS object_id,
               CAST(t.job_id AS STRING) AS object_name, NULL AS owner,
               'single_task_job' AS metric_name, 1.0 AS metric_value
        FROM t WHERE n_tasks = 1
        LIMIT 500
    """,
)

# ---------------------------------------------------------------------
# Python-evaluated checks (not a single SQL measure).
# ---------------------------------------------------------------------

REQUIRED_SYSTEM_SCHEMAS = [
    "access", "billing", "compute", "lakeflow", "query", "storage", "serving", "mlflow",
]


def check_system_schema_enablement(spark, params):
    """observability-from-system-tables / lineage-and-audit-via-system-tables.

    Conforming = required system schema is readable from this workspace.
    """
    enabled, findings = 0, []
    for schema in REQUIRED_SYSTEM_SCHEMAS:
        try:
            spark.sql(f"SHOW TABLES IN system.{schema}").limit(1).collect()
            enabled += 1
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            findings.append(
                {
                    "object_type": "SCHEMA",
                    "object_id": f"system.{schema}",
                    "object_name": f"system.{schema}",
                    "metric_name": "not_readable",
                    "metric_value": 1.0,
                    "detail": str(exc)[:500],
                }
            )
    return enabled, len(REQUIRED_SYSTEM_SCHEMAS), findings


PY_CHECKS = {
    "observability-from-system-tables": ("system_schemas", check_system_schema_enablement),
    "lineage-and-audit-via-system-tables": ("system_schemas", check_system_schema_enablement),
}
