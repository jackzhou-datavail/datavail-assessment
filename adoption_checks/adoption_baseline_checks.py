# Databricks notebook source
# DBTITLE 1,Overview
# MAGIC %md
# MAGIC # Databricks Platform Adoption Baseline Checks
# MAGIC
# MAGIC Automated assessment of platform adoption across **4 UI sections**:
# MAGIC 1. **Home / Workspace** — Users, compute, UC, Git, governance
# MAGIC 2. **SQL** — Warehouses, queries, dashboards, BI
# MAGIC 3. **Data Engineering** — Jobs, pipelines, streaming, ETL
# MAGIC 4. **AI/ML** — Experiments, models, serving, GenAI
# MAGIC
# MAGIC Each of the **51 checks** is scored **0** (NONE), **1** (MINIMAL), or **2** (ACTIVE). Section and overall scores are computed and written to `assessment.results.adoption_check_history`.

# COMMAND ----------

# DBTITLE 1,Setup and Configuration
import uuid
from datetime import datetime, timedelta
from pyspark.sql import functions as F, Row

# --- Run metadata ---
RUN_ID = str(uuid.uuid4())
RUN_TS = datetime.now()

# --- Lookback windows ---
DAYS_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
DAYS_90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

# --- Target table for results ---
RESULTS_TABLE = "assessment.results.adoption_check_history"

print(f"Run ID:   {RUN_ID}")
print(f"Run Time: {RUN_TS}")
print(f"30-day cutoff: {DAYS_30}")
print(f"90-day cutoff: {DAYS_90}")

# COMMAND ----------

# DBTITLE 1,Scoring Helper Functions
# --- Collector for all check results ---
results = []

def add_check(section: str, check_id: str, check_name: str, raw_value: float, score: int, detail: str = ""):
    """Register a single adoption check result."""
    label = {0: "NONE", 1: "MINIMAL", 2: "ACTIVE"}.get(score, "NONE")
    results.append(Row(
        run_id=RUN_ID,
        run_ts=RUN_TS,
        section=section,
        check_id=check_id,
        check_name=check_name,
        raw_value=float(raw_value),
        score=score,
        label=label,
        detail=detail
    ))
    icon = {"██": 2, "▓▓": 1, "░░": 0}
    block = [k for k, v in icon.items() if v == score][0]
    print(f"  [{block}] {check_id} {check_name}: {raw_value} → {label}")

def safe_query(sql: str, default=0):
    """Run a SQL query and return the first column of the first row, or default on error."""
    try:
        row = spark.sql(sql).first()
        return row[0] if row and row[0] is not None else default
    except Exception as e:
        print(f"    ⚠️ Query failed: {str(e)[:120]}")
        return default

def score_thresholds(value, minimal_threshold, active_threshold):
    """Score 0/1/2 based on two thresholds."""
    if value >= active_threshold:
        return 2
    elif value >= minimal_threshold:
        return 1
    return 0

def score_pct_threshold(value, minimal_pct, active_pct):
    """Score 0/1/2 based on percentage thresholds."""
    if value >= active_pct:
        return 2
    elif value >= minimal_pct:
        return 1
    return 0

# COMMAND ----------

# DBTITLE 1,Section 1: Home / Workspace
# MAGIC %md
# MAGIC ## Section 1: Home / Workspace — General Platform Adoption
# MAGIC Users, compute, Unity Catalog, Git, governance foundations.

# COMMAND ----------

# DBTITLE 1,Section 1 Checks (1.1 – 1.10)
SEC = "Workspace"
print(f"\n{'='*60}")
print(f"  SECTION 1: {SEC}")
print(f"{'='*60}")

# 1.1 Active users (last 30/90 days)
v = safe_query(f"""
  SELECT COUNT(DISTINCT user_identity.email)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND user_identity.email IS NOT NULL
    AND user_identity.email NOT LIKE '%databricks.com'
""")
add_check(SEC, "1.1", "Active users (30d)", v, score_thresholds(v, 1, 6))

# 1.2 Distinct users executing code
v = safe_query(f"""
  SELECT COUNT(DISTINCT user_identity.email)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND action_name IN ('runCommand', 'submitRun')
    AND user_identity.email IS NOT NULL
""")
add_check(SEC, "1.2", "Users executing code (30d)", v, score_thresholds(v, 1, 4))

# 1.3 Notebooks created/modified
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND service_name = 'notebook'
    AND action_name IN ('create', 'update')
""")
add_check(SEC, "1.3", "Notebooks created/modified (30d)", v, score_thresholds(v, 1, 11))

# 1.4 Git folder / Repos usage
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND service_name = 'repos'
""")
add_check(SEC, "1.4", "Git/Repos actions (30d)", v, score_thresholds(v, 1, 6))

# 1.5 Clusters created and hours consumed
v = safe_query(f"""
  SELECT COALESCE(SUM(usage_quantity), 0)
  FROM system.billing.usage
  WHERE usage_start_time >= '{DAYS_30}'
    AND sku_name LIKE '%ALL_PURPOSE%'
""")
add_check(SEC, "1.5", "All-purpose compute DBUs (30d)", v, score_thresholds(v, 1, 100))

# 1.6 Unity Catalog objects created
tables_count = safe_query("""
  SELECT COUNT(*)
  FROM system.information_schema.tables
  WHERE table_schema != 'information_schema'
    AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
""")
catalogs_count = safe_query("""
  SELECT COUNT(DISTINCT table_catalog)
  FROM system.information_schema.tables
  WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal')
""")
score_16 = 0
if tables_count > 20 and catalogs_count >= 2:
    score_16 = 2
elif tables_count >= 1:
    score_16 = 1
add_check(SEC, "1.6", "UC objects (tables/catalogs)", tables_count, score_16, f"{catalogs_count} catalogs")

# 1.7 Workspace files (non-notebook)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'workspace'
    AND action_name IN ('create', 'import')
    AND request_params.path LIKE '%.py'
       OR request_params.path LIKE '%.sql'
       OR request_params.path LIKE '%.yaml'
       OR request_params.path LIKE '%.yml'
""")
add_check(SEC, "1.7", "Workspace files created (90d)", v, score_thresholds(v, 1, 11))

# 1.8 Secrets and token usage
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND service_name IN ('secrets', 'tokens')
""")
add_check(SEC, "1.8", "Secret/token events (30d)", v, score_thresholds(v, 1, 6))

# 1.9 Marketplace listings consumed
v = safe_query(f"""
  SELECT COUNT(DISTINCT request_params.listing_id)
  FROM system.access.audit
  WHERE service_name = 'marketplace'
    AND action_name LIKE '%install%'
""")
add_check(SEC, "1.9", "Marketplace listings consumed", v, score_thresholds(v, 1, 2))

# 1.10 Cluster policies in use
total_clusters = safe_query(f"""
  SELECT COUNT(*) FROM system.compute.clusters
  WHERE change_time >= '{DAYS_90}'
""")
policy_clusters = safe_query(f"""
  SELECT COUNT(*) FROM system.compute.clusters
  WHERE change_time >= '{DAYS_90}'
    AND cluster_source = 'UI' AND policy_id IS NOT NULL
""")
pct = (policy_clusters / total_clusters * 100) if total_clusters > 0 else 0
score_110 = 0
if total_clusters > 0 and pct > 50:
    score_110 = 2
elif policy_clusters >= 1:
    score_110 = 1
add_check(SEC, "1.10", "Cluster policies in use", policy_clusters, score_110, f"{pct:.0f}% of {total_clusters} clusters")

# COMMAND ----------

# DBTITLE 1,Section 2: SQL
# MAGIC %md
# MAGIC ## Section 2: SQL — Analytics & BI Adoption
# MAGIC Warehouses, queries, dashboards, alerts, Genie, and advanced SQL features.

# COMMAND ----------

# DBTITLE 1,Section 2 Checks (2.1 – 2.12)
SEC = "SQL"
print(f"\n{'='*60}")
print(f"  SECTION 2: {SEC}")
print(f"{'='*60}")

# 2.1 SQL warehouses provisioned
v = safe_query("""
  SELECT COUNT(DISTINCT warehouse_id)
  FROM system.compute.warehouses
  WHERE delete_time IS NULL
""")
add_check(SEC, "2.1", "SQL warehouses provisioned", v, score_thresholds(v, 1, 2))

# 2.2 SQL warehouse active hours (DBU)
v = safe_query(f"""
  SELECT COALESCE(SUM(usage_quantity), 0)
  FROM system.billing.usage
  WHERE usage_start_time >= '{DAYS_30}'
    AND sku_name LIKE '%SQL%'
    AND usage_metadata.warehouse_id IS NOT NULL
""")
add_check(SEC, "2.2", "SQL warehouse DBUs (30d)", v, score_thresholds(v, 1, 100))

# 2.3 Total queries executed (30d)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.query.history
  WHERE start_time >= '{DAYS_30}'
""")
add_check(SEC, "2.3", "Total queries executed (30d)", v, score_thresholds(v, 1, 500))

# 2.4 Distinct users running queries
v = safe_query(f"""
  SELECT COUNT(DISTINCT executed_by)
  FROM system.query.history
  WHERE start_time >= '{DAYS_30}'
""")
add_check(SEC, "2.4", "Distinct query users (30d)", v, score_thresholds(v, 1, 4))

# 2.5 Lakeview dashboards created
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'dashboards'
    AND action_name = 'create'
""")
add_check(SEC, "2.5", "Lakeview dashboards created (90d)", v, score_thresholds(v, 1, 4))

# 2.6 Saved queries
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'databrickssql'
    AND action_name = 'createQuery'
""")
add_check(SEC, "2.6", "Saved queries created (90d)", v, score_thresholds(v, 1, 11))

# 2.7 Alerts configured
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'databrickssql'
    AND action_name LIKE '%Alert%'
""")
add_check(SEC, "2.7", "SQL alerts configured (90d)", v, score_thresholds(v, 1, 3))

# 2.8 Genie spaces created
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND action_name LIKE '%Genie%'
""")
add_check(SEC, "2.8", "Genie space activity (90d)", v, score_thresholds(v, 1, 2))

# 2.9 Query type distribution
v = safe_query(f"""
  SELECT COUNT(DISTINCT statement_type)
  FROM system.query.history
  WHERE start_time >= '{DAYS_30}'
    AND statement_type IS NOT NULL
""")
add_check(SEC, "2.9", "Distinct query statement types (30d)", v, score_thresholds(v, 2, 3))

# 2.10 Materialized views and streaming tables
mv_count = safe_query("""
  SELECT COUNT(*)
  FROM system.information_schema.tables
  WHERE table_type IN ('MATERIALIZED_VIEW', 'STREAMING_TABLE')
    AND table_catalog NOT IN ('system', 'samples')
""")
add_check(SEC, "2.10", "MVs and streaming tables", mv_count, score_thresholds(mv_count, 1, 3))

# 2.11 Federated / foreign tables
v = safe_query("""
  SELECT COUNT(*)
  FROM system.information_schema.tables
  WHERE table_type = 'FOREIGN'
    AND table_catalog NOT IN ('system', 'samples')
""")
add_check(SEC, "2.11", "Federated/foreign tables", v, score_thresholds(v, 1, 3))

# 2.12 Parameterized dashboards (proxy: filter widget usage in audit)
v = safe_query(f"""
  SELECT COUNT(DISTINCT request_params.dashboard_id)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'dashboards'
    AND action_name = 'update'
""")
add_check(SEC, "2.12", "Dashboards actively updated (90d)", v, score_thresholds(v, 1, 2))

# COMMAND ----------

# DBTITLE 1,Section 3: Data Engineering
# MAGIC %md
# MAGIC ## Section 3: Data Engineering — ETL & Orchestration Adoption
# MAGIC Jobs, SDP pipelines, streaming, Delta writes, scheduling, and alerting.

# COMMAND ----------

# DBTITLE 1,Section 3 Checks (3.1 – 3.14)
SEC = "Data Engineering"
print(f"\n{'='*60}")
print(f"  SECTION 3: {SEC}")
print(f"{'='*60}")

# 3.1 Jobs defined
v = safe_query("""
  SELECT COUNT(DISTINCT job_id)
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
""")
add_check(SEC, "3.1", "Jobs defined", v, score_thresholds(v, 1, 6))

# 3.2 Jobs actively running (30d)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.lakeflow.job_run_timeline
  WHERE period_start_time >= '{DAYS_30}'
""")
add_check(SEC, "3.2", "Job runs (30d)", v, score_thresholds(v, 1, 21))

# 3.3 Job run success/failure volume
success = safe_query(f"""
  SELECT COUNT(*)
  FROM system.lakeflow.job_run_timeline
  WHERE period_start_time >= '{DAYS_30}'
    AND result_state = 'SUCCESS'
""")
failed = safe_query(f"""
  SELECT COUNT(*)
  FROM system.lakeflow.job_run_timeline
  WHERE period_start_time >= '{DAYS_30}'
    AND result_state IN ('FAILED', 'TIMEDOUT')
""")
total_runs = success + failed
add_check(SEC, "3.3", "Completed runs (30d)", total_runs, score_thresholds(total_runs, 1, 50), f"{success} success, {failed} failed")

# 3.4 Multi-task jobs
v = safe_query("""
  SELECT COUNT(DISTINCT job_id)
  FROM (
    SELECT job_id, COUNT(DISTINCT task_key) AS n_tasks
    FROM system.lakeflow.job_tasks
    GROUP BY job_id
    HAVING n_tasks > 1
  )
""")
add_check(SEC, "3.4", "Multi-task jobs", v, score_thresholds(v, 1, 3))

# 3.5 SDP pipelines defined
v = safe_query(f"""
  SELECT COUNT(DISTINCT request_params.pipeline_id)
  FROM system.access.audit
  WHERE service_name = 'deltaPipelines'
    AND action_name = 'create'
""")
add_check(SEC, "3.5", "SDP pipelines created", v, score_thresholds(v, 1, 2))

# 3.6 SDP pipeline update frequency
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND service_name = 'deltaPipelines'
    AND action_name = 'update'
""")
add_check(SEC, "3.6", "SDP pipeline updates (30d)", v, score_thresholds(v, 1, 11))

# 3.7 Streaming workloads
v = safe_query(f"""
  SELECT COALESCE(SUM(usage_quantity), 0)
  FROM system.billing.usage
  WHERE usage_start_time >= '{DAYS_30}'
    AND sku_name LIKE '%STREAMING%'
""")
add_check(SEC, "3.7", "Streaming DBUs (30d)", v, score_thresholds(v, 1, 10))

# 3.8 Delta table write operations (MERGE, UPDATE, DELETE)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.query.history
  WHERE start_time >= '{DAYS_30}'
    AND statement_type IN ('MERGE', 'UPDATE', 'DELETE')
""")
add_check(SEC, "3.8", "Delta write ops (30d)", v, score_thresholds(v, 1, 50))

# 3.9 Tables with history > 1 version (proxy: tables modified recently)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.information_schema.tables
  WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal')
    AND table_schema != 'information_schema'
    AND last_altered IS NOT NULL
    AND last_altered >= '{DAYS_90}'
""")
add_check(SEC, "3.9", "Tables modified recently (90d)", v, score_thresholds(v, 1, 11))

# 3.10 Scheduled jobs (cron) vs. manual
# Note: schedule lives inside trigger.schedule struct, not as a top-level column
scheduled = safe_query("""
  SELECT COUNT(DISTINCT job_id)
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
    AND trigger.schedule IS NOT NULL
""")
total_jobs = safe_query("""
  SELECT COUNT(DISTINCT job_id)
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
""")
pct_sched = (scheduled / total_jobs * 100) if total_jobs > 0 else 0
score_310 = 0
if pct_sched > 50:
    score_310 = 2
elif scheduled >= 1:
    score_310 = 1
add_check(SEC, "3.10", "Scheduled jobs", scheduled, score_310, f"{pct_sched:.0f}% of {total_jobs} jobs")

# 3.11 Trigger types used (proxy for workload diversity)
# Note: job_tasks has no task_type column; use trigger_type from jobs instead
v = safe_query("""
  SELECT COUNT(DISTINCT trigger_type)
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
    AND trigger_type IS NOT NULL
""")
add_check(SEC, "3.11", "Distinct trigger types", v, score_thresholds(v, 1, 3))

# 3.12 Jobs SKU compute usage
v = safe_query(f"""
  SELECT COALESCE(SUM(usage_quantity), 0)
  FROM system.billing.usage
  WHERE usage_start_time >= '{DAYS_30}'
    AND (sku_name LIKE '%JOBS%' OR sku_name LIKE '%WORKFLOW%')
""")
add_check(SEC, "3.12", "Jobs compute DBUs (30d)", v, score_thresholds(v, 1, 200))

# 3.13 Auto Loader / Lakeflow Connect presence
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND (action_name LIKE '%autoLoader%' OR action_name LIKE '%cloudFiles%'
         OR service_name = 'ingestion')
""")
add_check(SEC, "3.13", "Auto Loader / Connect events (90d)", v, score_thresholds(v, 1, 5))

# 3.14 Workflow notifications configured
v = safe_query(f"""
  SELECT COUNT(DISTINCT request_params.job_id)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_90}'
    AND service_name = 'jobs'
    AND action_name IN ('create', 'resetJob', 'update')
    AND request_params.notification_settings IS NOT NULL
""")
add_check(SEC, "3.14", "Jobs with notifications", v, score_thresholds(v, 1, 3))

# COMMAND ----------

RESULTS_TABLE

# COMMAND ----------

# DBTITLE 1,Section 4: AI/ML
# MAGIC %md
# MAGIC ## Section 4: AI/ML — Machine Learning & GenAI Adoption
# MAGIC Experiments, models, serving endpoints, AI Gateway, vector search, and GPU compute.

# COMMAND ----------

# DBTITLE 1,Section 4 Checks (4.1 – 4.15)
SEC = "AI/ML"
print(f"\n{'='*60}")
print(f"  SECTION 4: {SEC}")
print(f"{'='*60}")

# 4.1 MLflow experiments created
v = safe_query(f"""
  SELECT COUNT(DISTINCT request_params.experiment_id)
  FROM system.access.audit
  WHERE service_name = 'mlflow'
    AND action_name = 'createExperiment'
""")
add_check(SEC, "4.1", "MLflow experiments created", v, score_thresholds(v, 1, 4))

# 4.2 MLflow runs logged (30d)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE event_date >= '{DAYS_30}'
    AND service_name = 'mlflow'
    AND action_name = 'createRun'
""")
add_check(SEC, "4.2", "MLflow runs logged (30d)", v, score_thresholds(v, 1, 11))

# 4.3 Models registered in Unity Catalog
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE service_name = 'unityCatalog'
    AND action_name LIKE '%RegisteredModel%'
    AND action_name LIKE '%create%'
""")
add_check(SEC, "4.3", "Models registered in UC", v, score_thresholds(v, 1, 3))

# 4.4 Model versions created
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE service_name = 'unityCatalog'
    AND action_name LIKE '%ModelVersion%'
    AND action_name LIKE '%create%'
""")
add_check(SEC, "4.4", "Model versions created", v, score_thresholds(v, 1, 4))

# 4.5 Serving endpoints provisioned
v = safe_query("""
  SELECT COUNT(DISTINCT endpoint_name)
  FROM system.serving.served_entities
""")
add_check(SEC, "4.5", "Serving endpoints provisioned", v, score_thresholds(v, 1, 2))

# 4.6 Serving endpoint traffic (30d)
v = safe_query(f"""
  SELECT COALESCE(SUM(request_count), 0)
  FROM system.serving.endpoint_usage
  WHERE served_at >= '{DAYS_30}'
""")
add_check(SEC, "4.6", "Serving requests (30d)", v, score_thresholds(v, 1, 100))

# 4.7 AI Gateway endpoints active
v = safe_query(f"""
  SELECT COUNT(DISTINCT endpoint_name)
  FROM system.ai.endpoint_usage
  WHERE served_at >= '{DAYS_90}'
""")
add_check(SEC, "4.7", "AI Gateway endpoints active (90d)", v, score_thresholds(v, 1, 2))

# 4.8 AI Gateway request/token volume (30d)
reqs = safe_query(f"""
  SELECT COALESCE(SUM(request_count), 0)
  FROM system.ai.endpoint_usage
  WHERE served_at >= '{DAYS_30}'
""")
add_check(SEC, "4.8", "AI Gateway requests (30d)", reqs, score_thresholds(reqs, 1, 1000))

# 4.9 Distinct models/providers via Gateway
v = safe_query(f"""
  SELECT COUNT(DISTINCT served_model_name)
  FROM system.ai.endpoint_usage
  WHERE served_at >= '{DAYS_90}'
""")
add_check(SEC, "4.9", "Distinct models via Gateway (90d)", v, score_thresholds(v, 1, 2))

# 4.10 Feature tables present
v = safe_query("""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE service_name = 'featureStore'
""")
add_check(SEC, "4.10", "Feature Store activity", v, score_thresholds(v, 1, 3))

# 4.11 Vector search indexes created
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE service_name = 'vectorSearch'
    AND action_name LIKE '%create%'
""")
add_check(SEC, "4.11", "Vector search indexes created", v, score_thresholds(v, 1, 2))

# 4.12 Agent Bricks tiles defined
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.access.audit
  WHERE action_name LIKE '%AgentBrick%'
     OR action_name LIKE '%agentTile%'
     OR (service_name = 'aiFunction' AND action_name LIKE '%create%')
""")
add_check(SEC, "4.12", "Agent Bricks / AI function activity", v, score_thresholds(v, 1, 2))

# 4.13 Inference tables logging enabled
v = safe_query("""
  SELECT COUNT(DISTINCT endpoint_name)
  FROM system.serving.served_entities
  WHERE entity_name IS NOT NULL
""")
# Proxy: endpoints with entities are likely logging
add_check(SEC, "4.13", "Serving endpoints with entities", v, score_thresholds(v, 1, 2))

# 4.14 AI functions in SQL (ai_query, ai_forecast, etc.)
v = safe_query(f"""
  SELECT COUNT(*)
  FROM system.query.history
  WHERE start_time >= '{DAYS_30}'
    AND (LOWER(statement_text) LIKE '%ai_query%'
      OR LOWER(statement_text) LIKE '%ai_forecast%'
      OR LOWER(statement_text) LIKE '%ai_classify%'
      OR LOWER(statement_text) LIKE '%ai_extract%'
      OR LOWER(statement_text) LIKE '%ai_generate%'
      OR LOWER(statement_text) LIKE '%ai_similarity%')
""")
add_check(SEC, "4.14", "AI SQL function queries (30d)", v, score_thresholds(v, 1, 6))

# 4.15 GPU / ML compute usage
v = safe_query(f"""
  SELECT COALESCE(SUM(usage_quantity), 0)
  FROM system.billing.usage
  WHERE usage_start_time >= '{DAYS_30}'
    AND (sku_name LIKE '%GPU%' OR sku_name LIKE '%ML%')
""")
add_check(SEC, "4.15", "GPU/ML compute DBUs (30d)", v, score_thresholds(v, 1, 50))

# COMMAND ----------

# DBTITLE 1,Scoring Rollup
# MAGIC %md
# MAGIC ## Scoring Rollup & Results
# MAGIC Section scores, overall weighted adoption score, grade bands, and heatmap.

# COMMAND ----------

# DBTITLE 1,Compute Section & Overall Scores
from pyspark.sql import DataFrame
import math

# --- Build results DataFrame ---
results_df = spark.createDataFrame(results)

# --- Section rollup ---
section_config = {
    "Workspace":        {"max": 20, "weight": 0.30},
    "SQL":              {"max": 24, "weight": 0.20},
    "Data Engineering": {"max": 28, "weight": 0.30},
    "AI/ML":            {"max": 30, "weight": 0.20},
}

def grade_section(pct):
    if pct >= 75: return "STRONG"
    if pct >= 40: return "DEVELOPING"
    if pct >= 10: return "EARLY"
    return "NOT ADOPTED"

def grade_overall(pct):
    if pct >= 80: return "FULLY LEVERAGED"
    if pct >= 60: return "BROADLY ADOPTED"
    if pct >= 35: return "PARTIALLY ADOPTED"
    if pct >= 10: return "EARLY STAGE"
    return "NOT ADOPTED"

print(f"\n{'='*60}")
print("  ADOPTION SCORECARD")
print(f"{'='*60}\n")

overall_score = 0.0
section_results = []

for sec_name, cfg in section_config.items():
    sec_checks = [r for r in results if r.section == sec_name]
    points = sum(r.score for r in sec_checks)
    pct = (points / cfg["max"]) * 100 if cfg["max"] > 0 else 0
    grade = grade_section(pct)
    overall_score += pct * cfg["weight"]

    active = sum(1 for r in sec_checks if r.score == 2)
    minimal = sum(1 for r in sec_checks if r.score == 1)
    none = sum(1 for r in sec_checks if r.score == 0)

    section_results.append(Row(
        section=sec_name,
        points=points,
        max_points=cfg["max"],
        score_pct=round(pct, 1),
        grade=grade,
        active_count=active,
        minimal_count=minimal,
        none_count=none,
        weight=cfg["weight"]
    ))

    bar_len = int(pct / 2)
    bar = "█" * bar_len + "░" * (50 - bar_len)
    print(f"  {sec_name:<20s} [{bar}] {pct:5.1f}%  {grade}")
    print(f"  {'':20s}  ██={active}  ▓▓={minimal}  ░░={none}  ({points}/{cfg['max']} pts)")
    print()

overall_grade = grade_overall(overall_score)
print(f"  {'='*60}")
print(f"  OVERALL ADOPTION SCORE:  {overall_score:.1f}%  —  {overall_grade}")
print(f"  {'='*60}")

# Display section summary table
section_df = spark.createDataFrame(section_results)
display(section_df.select("section", "score_pct", "grade", "active_count", "minimal_count", "none_count", "points", "max_points"))

# COMMAND ----------

# DBTITLE 1,Heatmap Visualization
# --- Heatmap display ---
print("\n  ADOPTION HEATMAP")
print(f"  {'='*60}\n")

for sec_name in section_config.keys():
    sec_checks = sorted([r for r in results if r.section == sec_name], key=lambda r: r.check_id)
    blocks = []
    ids = []
    for r in sec_checks:
        icon = {2: "██", 1: "▓▓", 0: "░░"}.get(r.score, "░░")
        blocks.append(f"[{icon}]")
        ids.append(f" {r.check_id.split('.')[-1]:>2s} ")

    label = f"  {sec_name:<18s}"
    print(f"  {'':18s} {''.join(ids)}")
    print(f"{label} {''.join(blocks)}")
    print()

print(f"  Legend:  ██ = ACTIVE (2)    ▓▓ = MINIMAL (1)    ░░ = NONE (0)")

# COMMAND ----------

# DBTITLE 1,Detailed Check Results
# --- Display all 51 checks ---
display(
    results_df
    .select("section", "check_id", "check_name", "raw_value", "label", "detail")
    .orderBy("check_id")
)

# COMMAND ----------

# DBTITLE 1,Write Results to Delta
# --- Create target table if not exists ---
spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
    run_id        STRING      COMMENT 'Unique run identifier',
    run_ts        TIMESTAMP   COMMENT 'When the adoption check ran',
    section       STRING      COMMENT 'UI section: Workspace | SQL | Data Engineering | AI/ML',
    check_id      STRING      COMMENT 'Check number (e.g., 1.1, 2.5, 4.12)',
    check_name    STRING      COMMENT 'Human-readable check name',
    raw_value     DOUBLE      COMMENT 'Measured numeric value',
    score         INT         COMMENT '0 = NONE, 1 = MINIMAL, 2 = ACTIVE',
    label         STRING      COMMENT 'NONE | MINIMAL | ACTIVE',
    detail        STRING      COMMENT 'Optional: supporting evidence or breakdown'
  )
  USING DELTA
  COMMENT 'Per-check adoption scores, one row per check per run. Enables trending over time.'
""")

# --- Append this run's results ---
results_df.write.mode("append").saveAsTable(RESULTS_TABLE)

print(f"\n✅ {len(results)} check results written to {RESULTS_TABLE}")
print(f"   Run ID: {RUN_ID}")

# COMMAND ----------

# DBTITLE 1,Trend Comparison (Optional)
# --- Compare with previous run (if exists) ---
try:
    prev_run = spark.sql(f"""
      SELECT run_id, run_ts
      FROM {RESULTS_TABLE}
      WHERE run_id != '{RUN_ID}'
      GROUP BY run_id, run_ts
      ORDER BY run_ts DESC
      LIMIT 1
    """).first()

    if prev_run:
        print(f"\n  TREND vs. PREVIOUS RUN ({prev_run.run_ts.strftime('%Y-%m-%d %H:%M')})")
        print(f"  {'='*60}\n")

        comparison = spark.sql(f"""
          SELECT
            c.check_id,
            c.check_name,
            c.section,
            p.label AS prev_label,
            c.label AS curr_label,
            c.score - p.score AS delta,
            CASE
              WHEN c.score > p.score THEN '⬆️ IMPROVED'
              WHEN c.score < p.score THEN '⬇️ REGRESSED'
              ELSE '↔️ UNCHANGED'
            END AS trend
          FROM {RESULTS_TABLE} c
          JOIN {RESULTS_TABLE} p
            ON c.check_id = p.check_id
          WHERE c.run_id = '{RUN_ID}'
            AND p.run_id = '{prev_run.run_id}'
          ORDER BY delta DESC, c.check_id
        """)

        improved = comparison.filter("delta > 0").count()
        regressed = comparison.filter("delta < 0").count()
        unchanged = comparison.filter("delta = 0").count()

        print(f"  ⬆️ Improved:  {improved}")
        print(f"  ⬇️ Regressed: {regressed}")
        print(f"  ↔️ Unchanged: {unchanged}\n")

        display(comparison.filter("delta != 0"))
    else:
        print("\n  ℹ️ First run — no previous data for trend comparison.")
except Exception as e:
    print(f"\n  ℹ️ Trend comparison skipped: {str(e)[:120]}")