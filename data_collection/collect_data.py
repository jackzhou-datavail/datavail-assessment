# Databricks notebook source
"""
Datavail Assessment — REAL Data Extractor (real_data branch)

Unlike the synthetic generator on master, this script computes every raw_ws_*
and gold_* table from this workspace's actual Unity Catalog system tables
(system.access.*, system.lakeflow.*, system.mlflow.*, system.serving.*,
system.information_schema.*). Nothing here is fabricated: a metric is either
a real measurement or it is left NULL.

What is genuinely measurable in this workspace and used below:
  - Direct/ad-hoc table writes that bypass a governed job or pipeline
    (system.access.table_lineage, entity_type NULL/NOTEBOOK/DBSQL_QUERY)
  - Real pipeline/job ownership (created_by / run_as) and failure rates
    (system.lakeflow.pipelines/jobs + *_run_timeline, *_update_timeline)
  - Real table comment coverage and naming hygiene
    (system.information_schema.tables)
  - Real MLflow experiment staleness (system.mlflow.experiments_latest/runs_latest)
  - Real custom-model serving endpoints (system.serving.served_entities,
    filtered to CUSTOM_MODEL — this workspace only serves Databricks'
    built-in foundation models, so this is expected to be empty)

What is NOT measurable here and is intentionally left NULL / dropped rather
than invented (per explicit decision, not an oversight):
  - Dollar cost of any finding (estimated_rerun_cost_usd, business_impact_usd)
  - DLT data-quality expectations / hardcoded-path usage (not exposed by
    system tables without parsing pipeline source, so has_dq_expectations
    and uses_hardcoded_paths are NULL and never drive a finding)
  - Sprint sizing (sprint_estimate_days) — effort estimation is a human
    judgment call, not something this pipeline can measure
  - A 30-day history for ownership coverage — Unity Catalog only exposes
    current state, not daily snapshots, so gold_ownership_trend has exactly
    one row (today) instead of a fabricated line. ETL Hygiene is the one
    dimension with a genuine 30-day trend, because system.access.table_lineage
    and system.lakeflow.pipeline_update_timeline carry real historical
    timestamps we can roll a window over.

Tables created (same shape as the synthetic generator, so the dashboard and
Genie space work unchanged):
  Raw:  raw_ws_tables, raw_ws_pipelines, raw_ws_jobs, raw_ws_job_runs,
        raw_ws_audit_events, raw_ws_ml_experiments, raw_ws_ml_models
  Gold: gold_bronze_table_edits, gold_pipeline_health, gold_ownership_trend,
        gold_remediation_backlog, gold_health_scores
"""

from __future__ import annotations

import os

from databricks.connect import DatabricksSession

# ── Config ────────────────────────────────────────────────────────────────────
IN_NOTEBOOK = "dbutils" in dir()
if IN_NOTEBOOK:
    dbutils.widgets.text("catalog", "", "Catalog")
    dbutils.widgets.text("schema", "", "Schema")
    CATALOG = dbutils.widgets.get("catalog")
    SCHEMA = dbutils.widgets.get("schema")
else:
    CATALOG = os.environ.get("DEMO_CATALOG", "main")
    SCHEMA = os.environ.get("DEMO_SCHEMA", "assessment_data_v2")

assert CATALOG and SCHEMA, "DEMO_CATALOG and DEMO_SCHEMA must be set"

try:
    spark  # noqa: F821
except NameError:
    spark = (
        DatabricksSession.builder
        .profile(os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))
        .serverless(True)
        .getOrCreate()
    )

FQ = f"`{CATALOG}`.`{SCHEMA}`"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{SCHEMA}`")

# ── Exclusions ───────────────────────────────────────────────────────────────
# Never assess the tables/jobs *this project itself* creates — that would be
# circular. Add the current write target plus every schema this project has
# ever written to across earlier iterations.
PROJECT_SCOPES = [
    (CATALOG, SCHEMA),
    ("jz_test", "assessment_data"),
    ("jz_test", "assessment_data_v2"),
    ("jz_test", "assessment_data_real"),
    ("jz_test", "workspace_health_assessment"),
    ("jz_test", "demo_workspace_health_assessment_report"),
    ("solution_builder", "demo_workspace_health_assessment_report"),
]
EXCLUDE_CATALOGS_SQL = "('system','samples')"


def not_project_scope(catalog_col: str, schema_col: str) -> str:
    """SQL predicate excluding this project's own catalogs/schemas."""
    conds = " OR ".join(
        f"({catalog_col} = '{c}' AND {schema_col} = '{s}')" for c, s in PROJECT_SCOPES
    )
    return f"NOT ({conds})"


# Our own setup job / dashboard's job runs shouldn't count as "the workspace's ETL".
EXCLUDE_JOB_NAME_SQL = "name NOT RLIKE '(?i)(datavail assessment setup|workspace health setup)'"
# Materialized-view refresh pipelines are Databricks-managed housekeeping, not
# user-authored ETL — including them would swamp the real pipeline signal.
EXCLUDE_MV_PIPELINE_SQL = "name NOT RLIKE '^MV-'"


def run(sql: str) -> None:
    spark.sql(sql)


def show_count(table: str) -> None:
    n = spark.table(f"{FQ}.`{table}`").count()
    print(f"  ✓ {table:30s}  rows={n:>6,}")


# ═══════════════════════════════════════════════════════════════════════════
# RAW TABLES — direct extracts from Unity Catalog system tables
# ═══════════════════════════════════════════════════════════════════════════

print("=== raw_ws_tables (system.information_schema.tables) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_tables` COMMENT 'Real UC table inventory, excluding this project''s own schemas' AS
SELECT
  md5(concat(table_catalog, '.', table_schema, '.', table_name)) AS table_id,
  table_name,
  table_catalog AS catalog_name,
  table_schema  AS schema_name,
  CASE
    WHEN table_schema RLIKE '(?i)(^|_)(bronze|raw)(_|$)' OR table_name RLIKE '(?i)^(raw_|bronze_)' THEN 'bronze'
    WHEN table_schema RLIKE '(?i)(^|_)(silver|clean|curated)(_|$)' OR table_name RLIKE '(?i)^silver_' THEN 'silver'
    WHEN table_schema RLIKE '(?i)(^|_)(gold|mart)(_|$)' OR table_name RLIKE '(?i)^gold_' THEN 'gold'
    ELSE 'unclassified'
  END AS data_layer,
  table_owner AS owner_email,
  (table_owner IS NOT NULL AND table_owner RLIKE '@') AS has_owner_tag,
  created AS created_at,
  last_altered AS last_ddl_at,
  comment AS table_comment,
  NOT (table_name RLIKE '^[a-z][a-z0-9_]*$') AS naming_violation,
  CAST(NULL AS BIGINT) AS row_count_approx
FROM system.information_schema.tables
WHERE table_catalog NOT IN {EXCLUDE_CATALOGS_SQL}
  AND table_schema != 'information_schema'
  AND {not_project_scope('table_catalog', 'table_schema')}
""")
show_count("raw_ws_tables")

print("\n=== raw_ws_pipelines (system.lakeflow.pipelines + pipeline_update_timeline) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_pipelines` COMMENT 'Real DLT/Lakeflow pipelines, excluding MV-refresh housekeeping pipelines' AS
WITH latest_pipelines AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.pipelines
  WHERE delete_time IS NULL
),
runs_30d AS (
  SELECT pipeline_id,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN result_state IN ('FAILED', 'CANCELED') THEN 1 ELSE 0 END) AS failed_runs,
    MAX(period_start_time) AS last_run_time,
    AVG(CAST(period_end_time AS DOUBLE) - CAST(period_start_time AS DOUBLE)) AS avg_duration
  FROM system.lakeflow.pipeline_update_timeline
  WHERE period_start_time >= CURRENT_DATE() - INTERVAL 30 DAYS
  GROUP BY pipeline_id
)
SELECT
  p.pipeline_id,
  p.name AS pipeline_name,
  p.run_as AS owner_email,
  (p.run_as IS NOT NULL AND p.run_as RLIKE '@') AS has_owner_tag,
  NOT (p.name RLIKE '(?i)(test|tutorial|demo|dev[_-])') AS is_production,
  'unknown' AS schedule_type,
  CAST(NULL AS BOOLEAN) AS has_dq_expectations,
  CAST(NULL AS BOOLEAN) AS uses_hardcoded_paths,
  CASE WHEN COALESCE(r.failed_runs, 0) > 0 THEN 'failed'
       WHEN COALESCE(r.total_runs, 0) > 0 THEN 'succeeded'
       ELSE 'unknown' END AS last_run_status,
  CAST(r.last_run_time AS DATE) AS last_run_date,
  CAST(r.avg_duration AS INT) AS avg_duration_sec,
  ROUND(COALESCE(r.failed_runs, 0) / NULLIF(r.total_runs, 0), 3) AS failure_rate_30d,
  COALESCE(p.create_time, p.change_time) AS created_at
FROM latest_pipelines p
LEFT JOIN runs_30d r ON p.pipeline_id = r.pipeline_id
WHERE p.rn = 1 AND {EXCLUDE_MV_PIPELINE_SQL}
""")
show_count("raw_ws_pipelines")

print("\n=== raw_ws_jobs (system.lakeflow.jobs) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_jobs` COMMENT 'Real Databricks Jobs, excluding this bundle''s own setup job' AS
WITH latest_jobs AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
)
SELECT
  job_id,
  name AS job_name,
  COALESCE(creator_user_name, creator_id) AS owner_email,
  (creator_user_name IS NOT NULL AND creator_user_name RLIKE '@') AS has_owner_tag,
  trigger.schedule.quartz_cron_expression AS schedule_cron,
  'unknown' AS cluster_type,
  COALESCE(create_time, change_time) AS created_at
FROM latest_jobs
WHERE rn = 1 AND {EXCLUDE_JOB_NAME_SQL}
""")
show_count("raw_ws_jobs")

print("\n=== raw_ws_job_runs (system.lakeflow.job_run_timeline) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_job_runs` COMMENT 'Real job run history, 90 days' AS
SELECT
  rt.run_id,
  rt.job_id,
  CAST(NULL AS STRING) AS pipeline_id,
  rt.period_start_time AS start_time,
  rt.period_end_time AS end_time,
  LOWER(COALESCE(rt.result_state, 'unknown')) AS status,
  CAST(rt.run_duration_seconds AS INT) AS duration_sec,
  LOWER(COALESCE(rt.trigger_type, 'unknown')) AS triggered_by
FROM system.lakeflow.job_run_timeline rt
JOIN {FQ}.`raw_ws_jobs` j ON rt.job_id = j.job_id
WHERE rt.period_start_time >= CURRENT_DATE() - INTERVAL 90 DAYS
""")
show_count("raw_ws_job_runs")

print("\n=== raw_ws_audit_events (real direct/ad-hoc writes, system.access.table_lineage) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_audit_events` COMMENT 'Real writes NOT triggered by a governed job or pipeline (entity_type NULL/NOTEBOOK/DBSQL_QUERY), 90 days' AS
SELECT
  md5(concat(COALESCE(l.entity_run_id, ''), l.target_table_full_name, CAST(l.event_time AS STRING))) AS event_id,
  l.event_time,
  l.created_by AS user_email,
  'DIRECT_WRITE' AS action_type,
  md5(l.target_table_full_name) AS table_id,
  l.target_table_name AS table_name,
  COALESCE(t.data_layer, 'unclassified') AS data_layer,
  CAST(NULL AS BIGINT) AS bytes_affected,
  CONCAT('Write via ', COALESCE(l.entity_type, 'ad-hoc query'), ' — not a governed job or pipeline run') AS query_snippet
FROM system.access.table_lineage l
LEFT JOIN {FQ}.`raw_ws_tables` t
  ON t.catalog_name = l.target_table_catalog AND t.schema_name = l.target_table_schema AND t.table_name = l.target_table_name
WHERE l.target_table_full_name IS NOT NULL
  AND (l.entity_type IS NULL OR l.entity_type IN ('NOTEBOOK', 'DBSQL_QUERY'))
  AND l.event_time >= CURRENT_DATE() - INTERVAL 90 DAYS
  AND l.target_table_catalog NOT IN {EXCLUDE_CATALOGS_SQL}
  AND {not_project_scope('l.target_table_catalog', 'l.target_table_schema')}
""")
show_count("raw_ws_audit_events")

print("\n=== raw_ws_ml_experiments (system.mlflow.experiments_latest + runs_latest) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_ml_experiments` COMMENT 'Real MLflow experiments' AS
WITH last_runs AS (
  SELECT experiment_id, MAX(start_time) AS last_run_time
  FROM system.mlflow.runs_latest
  WHERE delete_time IS NULL
  GROUP BY experiment_id
)
SELECT
  e.experiment_id,
  e.name AS experiment_name,
  regexp_extract(e.name, '^/Users/([^/]+)/', 1) AS owner_email,
  e.name AS workspace_path,
  CAST(COALESCE(lr.last_run_time, e.create_time) AS DATE) AS last_run_date,
  COALESCE(lr.last_run_time, e.create_time) < CURRENT_DATE() - INTERVAL 30 DAYS AS is_stale,
  CAST(NULL AS BOOLEAN) AS has_registered_model,
  CAST(NULL AS BOOLEAN) AS has_description,
  e.create_time AS created_at
FROM system.mlflow.experiments_latest e
LEFT JOIN last_runs lr ON e.experiment_id = lr.experiment_id
WHERE e.delete_time IS NULL
""")
show_count("raw_ws_ml_experiments")

print("\n=== raw_ws_ml_models (system.serving.served_entities, CUSTOM_MODEL only) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`raw_ws_ml_models` COMMENT 'Real custom-model serving endpoints (excludes Databricks built-in foundation models)' AS
SELECT
  se.served_entity_id AS model_id,
  se.entity_name AS model_name,
  se.endpoint_name AS serving_endpoint_name,
  CAST(NULL AS STRING) AS upstream_features_table,
  CAST(NULL AS STRING) AS features_table_layer,
  CAST(NULL AS DATE) AS last_training_date,
  CAST(NULL AS DATE) AS features_last_modified_date,
  CAST(false AS BOOLEAN) AS is_serving_stale_features,
  se.created_by AS owner_email,
  CAST(true AS BOOLEAN) AS registered_in_uc
FROM system.serving.served_entities se
WHERE se.entity_type = 'CUSTOM_MODEL'
""")
show_count("raw_ws_ml_models")

# ═══════════════════════════════════════════════════════════════════════════
# GOLD TABLES — derived real metrics (dashboard + Genie read these)
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== gold_bronze_table_edits (real direct-write frequency + real downstream lineage) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`gold_bronze_table_edits`
COMMENT 'Tables with real direct/ad-hoc writes outside governed jobs/pipelines. estimated_rerun_cost_usd is NULL: no real cost signal exists.'
AS
WITH edits AS (
  SELECT
    table_name,
    COUNT(*) AS edit_count_90d,
    MAX_BY(user_email, event_time) AS last_editor_email,
    MAX(event_time) AS last_edit_time,
    'DIRECT_WRITE' AS last_action_type
  FROM {FQ}.`raw_ws_audit_events`
  GROUP BY table_name
),
downstream AS (
  SELECT
    source_table_name AS table_name,
    COUNT(DISTINCT target_table_full_name) AS downstream_table_count,
    CONCAT_WS(',', COLLECT_SET(target_table_name)) AS downstream_tables
  FROM system.access.table_lineage
  WHERE source_table_full_name IS NOT NULL AND target_table_full_name IS NOT NULL
    AND event_time >= CURRENT_DATE() - INTERVAL 90 DAYS
    AND source_table_catalog NOT IN {EXCLUDE_CATALOGS_SQL}
    AND {not_project_scope('source_table_catalog', 'source_table_schema')}
  GROUP BY source_table_name
)
SELECT
  e.table_name,
  CAST(NULL AS STRING) AS catalog_schema,
  e.edit_count_90d,
  e.last_editor_email,
  CAST(e.last_edit_time AS DATE) AS last_edit_date,
  e.last_action_type,
  COALESCE(d.downstream_table_count, 0) AS downstream_gold_table_count,
  d.downstream_tables AS downstream_gold_tables,
  CAST(NULL AS DECIMAL(10,2)) AS estimated_rerun_cost_usd,
  CASE WHEN e.edit_count_90d > 5 OR COALESCE(d.downstream_table_count, 0) > 0 THEN 'critical' ELSE 'high' END AS severity
FROM edits e
LEFT JOIN downstream d ON e.table_name = d.table_name
ORDER BY e.edit_count_90d DESC
""")
show_count("gold_bronze_table_edits")

print("\n=== gold_pipeline_health ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`gold_pipeline_health`
COMMENT 'Real pipeline ownership + 30-day failure rate. anti_pattern_count only counts unowned (DQ-expectations/hardcoded-paths are not measurable here).'
AS
SELECT
  pipeline_id,
  pipeline_name,
  owner_email,
  has_owner_tag,
  is_production,
  has_dq_expectations,
  uses_hardcoded_paths,
  COALESCE(failure_rate_30d, 0.0) AS failure_rate_30d,
  avg_duration_sec,
  CAST(CASE WHEN NOT has_owner_tag THEN 1 ELSE 0 END AS INT) AS anti_pattern_count,
  CASE
    WHEN COALESCE(failure_rate_30d, 0.0) > 0.35 OR (NOT has_owner_tag AND is_production) THEN 'critical'
    WHEN COALESCE(failure_rate_30d, 0.0) > 0.15 THEN 'warning'
    ELSE 'healthy'
  END AS health_status
FROM {FQ}.`raw_ws_pipelines`
""")
show_count("gold_pipeline_health")

print("\n=== gold_ownership_trend (single real current-state row — no fabricated history) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`gold_ownership_trend`
COMMENT 'Real current ownership coverage across pipelines + jobs. Unity Catalog exposes current state only, not daily history, so this is ONE row (today), not a 30-day series.'
AS
SELECT
  CURRENT_DATE() AS report_date,
  COUNT(*) AS total_production_pipelines,
  SUM(CASE WHEN has_owner_tag THEN 1 ELSE 0 END) AS owned_production_pipelines,
  ROUND(100.0 * SUM(CASE WHEN has_owner_tag THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS ownership_coverage_pct,
  CAST(95.0 AS DOUBLE) AS goal_pct
FROM {FQ}.`raw_ws_pipelines`
WHERE is_production = TRUE
""")
show_count("gold_ownership_trend")

print("\n=== gold_remediation_backlog (real findings only — no invented $ impact or effort sizing) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`gold_remediation_backlog`
COMMENT 'Real findings only. business_impact_usd and sprint_estimate_days are NULL: neither is measurable from system tables.'
AS
WITH direct_write_findings AS (
  SELECT
    table_name AS asset_name,
    'table' AS asset_type,
    'ETL Hygiene' AS category,
    severity,
    CONCAT(CAST(edit_count_90d AS STRING), ' direct/ad-hoc write(s) in 90 days — bypasses governed jobs/pipelines',
           CASE WHEN downstream_gold_table_count > 0
                THEN CONCAT('; ', CAST(downstream_gold_table_count AS STRING), ' downstream table(s) depend on it')
                ELSE '' END) AS description,
    last_editor_email AS owner_email,
    CONCAT('Route writes through a governed job/pipeline; revoke ad-hoc write access if unintended') AS recommended_action,
    last_edit_date AS detected_at
  FROM {FQ}.`gold_bronze_table_edits`
),
pipeline_failure_findings AS (
  SELECT
    pipeline_name AS asset_name,
    'pipeline' AS asset_type,
    'ETL Hygiene' AS category,
    CASE WHEN failure_rate_30d > 0.35 THEN 'critical' ELSE 'high' END AS severity,
    CONCAT(CAST(ROUND(failure_rate_30d * 100) AS STRING), '% failure rate over 30 days') AS description,
    owner_email,
    'Investigate recent failures; add alerting on repeated failure' AS recommended_action,
    last_run_date AS detected_at
  FROM {FQ}.`raw_ws_pipelines`
  WHERE failure_rate_30d > 0.15
),
unowned_pipeline_findings AS (
  SELECT
    pipeline_name AS asset_name,
    'pipeline' AS asset_type,
    'Ownership & Access' AS category,
    CASE WHEN is_production THEN 'critical' ELSE 'high' END AS severity,
    CONCAT('No identifiable owner (run_as = ', COALESCE(owner_email, 'unknown'), ')',
           CASE WHEN is_production THEN ' — runs in production' ELSE '' END) AS description,
    owner_email,
    'Assign a real owner (run_as identity) to this pipeline' AS recommended_action,
    CAST(created_at AS DATE) AS detected_at
  FROM {FQ}.`raw_ws_pipelines`
  WHERE NOT has_owner_tag
),
unowned_job_findings AS (
  SELECT
    job_name AS asset_name,
    'job' AS asset_type,
    'Ownership & Access' AS category,
    'medium' AS severity,
    CONCAT('No identifiable creator (creator = ', COALESCE(owner_email, 'unknown'), ')') AS description,
    owner_email,
    'Assign a real creator/owner to this job' AS recommended_action,
    CAST(created_at AS DATE) AS detected_at
  FROM {FQ}.`raw_ws_jobs`
  WHERE NOT has_owner_tag
),
stale_experiment_findings AS (
  SELECT
    experiment_name AS asset_name,
    'ml_experiment' AS asset_type,
    'ML/AI Governance' AS category,
    'medium' AS severity,
    CONCAT('No runs in the last 30+ days (last run ', CAST(last_run_date AS STRING), ')') AS description,
    owner_email,
    'Archive if abandoned, or re-run and document current status' AS recommended_action,
    last_run_date AS detected_at
  FROM {FQ}.`raw_ws_ml_experiments`
  WHERE is_stale
),
missing_comment_findings AS (
  SELECT
    table_name AS asset_name,
    'table' AS asset_type,
    'Data Quality' AS category,
    'medium' AS severity,
    'Table has no comment describing its contents/purpose' AS description,
    owner_email,
    'Add a table comment via ALTER TABLE ... SET COMMENT' AS recommended_action,
    CAST(created_at AS DATE) AS detected_at
  FROM {FQ}.`raw_ws_tables`
  WHERE table_comment IS NULL
),
naming_violation_findings AS (
  SELECT
    table_name AS asset_name,
    'table' AS asset_type,
    'Data Quality' AS category,
    'medium' AS severity,
    'Table name does not follow lowercase snake_case naming convention' AS description,
    owner_email,
    'Rename to lowercase snake_case, or document the exception' AS recommended_action,
    CAST(created_at AS DATE) AS detected_at
  FROM {FQ}.`raw_ws_tables`
  WHERE naming_violation
),
unioned AS (
  SELECT * FROM direct_write_findings
  UNION ALL SELECT * FROM pipeline_failure_findings
  UNION ALL SELECT * FROM unowned_pipeline_findings
  UNION ALL SELECT * FROM unowned_job_findings
  UNION ALL SELECT * FROM stale_experiment_findings
  UNION ALL SELECT * FROM missing_comment_findings
  UNION ALL SELECT * FROM naming_violation_findings
)
SELECT
  CONCAT('FND-', LPAD(CAST(ROW_NUMBER() OVER (ORDER BY severity, category, asset_name) AS STRING), 6, '0')) AS finding_id,
  severity,
  category,
  asset_type,
  asset_name,
  owner_email,
  description,
  CAST(NULL AS DECIMAL(10,2)) AS business_impact_usd,
  recommended_action,
  COALESCE(detected_at, CURRENT_DATE()) AS detected_at,
  CAST(NULL AS INT) AS sprint_estimate_days
FROM unioned
""")
show_count("gold_remediation_backlog")

print("\n=== gold_health_scores (real scores; ETL Hygiene has a genuine 30-day rolling trend) ===")
run(f"""
CREATE OR REPLACE TABLE {FQ}.`gold_health_scores`
COMMENT 'Real scores from measured signals. Only ETL Hygiene has real day-by-day history (rolled from timestamped lineage + run events); the other three dimensions are current-state snapshots and appear as a single row for today. score_delta_30d is NULL where no historical comparison is possible.'
AS
WITH date_spine AS (
  SELECT explode(sequence(CURRENT_DATE() - INTERVAL 29 DAYS, CURRENT_DATE(), INTERVAL 1 DAY)) AS report_date
),
lineage_events AS (
  SELECT event_time,
         (entity_type IS NULL OR entity_type IN ('NOTEBOOK', 'DBSQL_QUERY')) AS is_adhoc
  FROM system.access.table_lineage
  WHERE target_table_full_name IS NOT NULL
    AND event_time >= CURRENT_DATE() - INTERVAL 59 DAYS
    AND target_table_catalog NOT IN {EXCLUDE_CATALOGS_SQL}
    AND {not_project_scope('target_table_catalog', 'target_table_schema')}
),
pipeline_runs AS (
  SELECT rt.period_start_time AS event_time,
         (rt.result_state IN ('FAILED', 'CANCELED')) AS is_failed
  FROM system.lakeflow.pipeline_update_timeline rt
  WHERE rt.period_start_time >= CURRENT_DATE() - INTERVAL 59 DAYS
),
-- Rolling 30-day window ending on each date_spine day, computed from real events.
etl_daily AS (
  SELECT
    d.report_date,
    SUM(CASE WHEN l.event_time BETWEEN d.report_date - INTERVAL 29 DAYS AND d.report_date THEN 1 ELSE 0 END) AS total_writes,
    SUM(CASE WHEN l.event_time BETWEEN d.report_date - INTERVAL 29 DAYS AND d.report_date AND l.is_adhoc THEN 1 ELSE 0 END) AS adhoc_writes
  FROM date_spine d
  LEFT JOIN lineage_events l ON true
  GROUP BY d.report_date
),
etl_daily_runs AS (
  SELECT
    d.report_date,
    SUM(CASE WHEN r.event_time BETWEEN d.report_date - INTERVAL 29 DAYS AND d.report_date THEN 1 ELSE 0 END) AS total_runs,
    SUM(CASE WHEN r.event_time BETWEEN d.report_date - INTERVAL 29 DAYS AND d.report_date AND r.is_failed THEN 1 ELSE 0 END) AS failed_runs
  FROM date_spine d
  LEFT JOIN pipeline_runs r ON true
  GROUP BY d.report_date
),
etl_scores AS (
  SELECT
    w.report_date,
    ROUND(100 * (1 - COALESCE(w.adhoc_writes / NULLIF(w.total_writes, 0), 0))
              * (1 - LEAST(COALESCE(r.failed_runs / NULLIF(r.total_runs, 0), 0), 1))) AS score
  FROM etl_daily w
  JOIN etl_daily_runs r ON w.report_date = r.report_date
),
-- Current-state (non-time-series) dimensions, computed once for "today".
ownership_now AS (
  SELECT ROUND(100.0 * AVG(CASE WHEN has_owner_tag THEN 1.0 ELSE 0.0 END)) AS score
  FROM (
    SELECT has_owner_tag FROM {FQ}.`raw_ws_pipelines`
    UNION ALL
    SELECT has_owner_tag FROM {FQ}.`raw_ws_jobs`
  )
),
ml_now AS (
  SELECT CASE WHEN COUNT(*) = 0 THEN 100
              ELSE ROUND(100.0 * SUM(CASE WHEN NOT is_stale THEN 1 ELSE 0 END) / COUNT(*))
         END AS score
  FROM {FQ}.`raw_ws_ml_experiments`
),
dq_now AS (
  SELECT ROUND(100.0 * AVG(
           (CASE WHEN table_comment IS NOT NULL THEN 1.0 ELSE 0.0 END +
            CASE WHEN NOT naming_violation THEN 1.0 ELSE 0.0 END) / 2.0
         )) AS score
  FROM {FQ}.`raw_ws_tables`
),
backlog_counts AS (
  SELECT
    CASE category
      WHEN 'ETL Hygiene' THEN 'etl_hygiene'
      WHEN 'Ownership & Access' THEN 'ownership_access'
      WHEN 'ML/AI Governance' THEN 'ml_ai_governance'
      WHEN 'Data Quality' THEN 'data_quality'
    END AS dimension,
    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical_count,
    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) AS high_count,
    SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) AS medium_count
  FROM {FQ}.`gold_remediation_backlog`
  GROUP BY category
)
SELECT
  e.report_date,
  'etl_hygiene' AS dimension,
  e.score,
  e.score - LAG(e.score, 30) OVER (ORDER BY e.report_date) AS score_delta_30d,
  COALESCE(bc.critical_count, 0) AS critical_count,
  COALESCE(bc.high_count, 0) AS high_count,
  COALESCE(bc.medium_count, 0) AS medium_count
FROM etl_scores e
LEFT JOIN backlog_counts bc ON bc.dimension = 'etl_hygiene'

UNION ALL

SELECT CURRENT_DATE(), 'ownership_access', o.score, CAST(NULL AS INT),
       COALESCE(bc.critical_count, 0), COALESCE(bc.high_count, 0), COALESCE(bc.medium_count, 0)
FROM ownership_now o LEFT JOIN backlog_counts bc ON bc.dimension = 'ownership_access'

UNION ALL

SELECT CURRENT_DATE(), 'ml_ai_governance', m.score, CAST(NULL AS INT),
       COALESCE(bc.critical_count, 0), COALESCE(bc.high_count, 0), COALESCE(bc.medium_count, 0)
FROM ml_now m LEFT JOIN backlog_counts bc ON bc.dimension = 'ml_ai_governance'

UNION ALL

SELECT CURRENT_DATE(), 'data_quality', q.score, CAST(NULL AS INT),
       COALESCE(bc.critical_count, 0), COALESCE(bc.high_count, 0), COALESCE(bc.medium_count, 0)
FROM dq_now q LEFT JOIN backlog_counts bc ON bc.dimension = 'data_quality'
""")

print("\n=== gold_health_scores: adding 'overall' as the average of today's 4 dimensions ===")
run(f"""
INSERT INTO {FQ}.`gold_health_scores`
SELECT
  CURRENT_DATE() AS report_date,
  'overall' AS dimension,
  ROUND(AVG(score)) AS score,
  CAST(NULL AS INT) AS score_delta_30d,
  SUM(critical_count) AS critical_count,
  SUM(high_count) AS high_count,
  SUM(medium_count) AS medium_count
FROM {FQ}.`gold_health_scores`
WHERE report_date = CURRENT_DATE()
""")
show_count("gold_health_scores")

print("\n=== Data generation complete ===")

import json as _json  # noqa: E402
if IN_NOTEBOOK:
    dbutils.notebook.exit(_json.dumps({"status": "success", "catalog": CATALOG, "schema": SCHEMA}))
