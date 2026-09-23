# Databricks notebook source
"""
Datavail Assessment — Synthetic Data Generator

Simulates Unity Catalog workspace metadata (tables, pipelines, jobs, audit events,
ML assets) to power the Datavail Assessment dashboard and Genie space.

Story signals that must hold:
  - raw_transactions (bronze) has 47 direct DML writes → tallest bar in ETL chart
  - 14 total bronze tables have direct edits
  - 31 pipelines without owner tag (9 in production)
  - Overall health score: 68/100  ETL Hygiene: 55  ML/AI: 62  Ownership: 71  DQ: 78
  - 2 ML models serving stale features from ml_features_bronze
  - $87K/year estimated rerun cost from the 3 critical bronze table violations
  - Ownership coverage trend: 58% → 69% over 30 days

Tables created
  Raw (workspace metadata simulation):
    raw_ws_tables, raw_ws_pipelines, raw_ws_jobs, raw_ws_job_runs,
    raw_ws_audit_events, raw_ws_ml_experiments, raw_ws_ml_models

  Gold (dashboard + Genie reads):
    gold_health_scores, gold_bronze_table_edits, gold_pipeline_health,
    gold_ownership_trend, gold_remediation_backlog
"""

from __future__ import annotations

import decimal
import os
import random
from datetime import datetime, timedelta

from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType, DateType, DecimalType, IntegerType, LongType,
    StringType, StructField, StructType, TimestampType,
)

# ── Config ────────────────────────────────────────────────────────────────────
IN_NOTEBOOK = "dbutils" in dir()
if IN_NOTEBOOK:
    dbutils.widgets.text("catalog", "", "Catalog")
    dbutils.widgets.text("schema", "", "Schema")
    CATALOG = dbutils.widgets.get("catalog")
    SCHEMA = dbutils.widgets.get("schema")
else:
    CATALOG = os.environ.get("DEMO_CATALOG", "main")
    SCHEMA = os.environ.get("DEMO_SCHEMA", "assessment_data")

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

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

NOW = datetime.now()
NOW_STR = NOW.strftime("%Y-%m-%d")
REPORT_DATE = NOW.strftime("%Y-%m-%d")
BASELINE_DATE = (NOW - timedelta(days=30)).strftime("%Y-%m-%d")

random.seed(42)

DML_TYPES = ["INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE"]
DML_WEIGHTS = [0.45, 0.25, 0.10, 0.15, 0.05]


def _save(df: DataFrame, table: str) -> None:
    fqn = f"{CATALOG}.{SCHEMA}.{table}"
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(fqn)
    cnt = spark.table(fqn).count()
    print(f"  ✓ {table:40s}  rows={cnt:>6,}")


def _ts(days_back: int, jitter_hours: int = 0) -> str:
    """Timestamp string NOW - days_back ± jitter."""
    base = NOW - timedelta(days=days_back)
    if jitter_hours:
        base += timedelta(hours=random.randint(-jitter_hours, jitter_hours))
    return base.strftime("%Y-%m-%d %H:%M:%S")


def _date(days_back: int) -> str:
    return (NOW - timedelta(days=days_back)).strftime("%Y-%m-%d")


# ── Raw table definitions ─────────────────────────────────────────────────────
# These are the 14 bronze tables with direct DML edits (the anti-pattern)
BRONZE_EDITED = [
    # (table_name, edit_count, downstream_gold_count, downstream_gold_list, rerun_cost_usd, is_critical)
    ("raw_transactions",       47, 3, "gold_revenue_summary,gold_daily_metrics,gold_exec_kpis",        34000.00, True),
    ("ml_features_bronze",     12, 2, "gold_churn_predictions,gold_model_inputs",                      18000.00, True),
    ("customer_events_bronze",  9, 2, "gold_customer_360,gold_segment_rollup",                         14000.00, True),
    ("order_items_bronze",      6, 1, "gold_product_performance",                                       5000.00, False),
    ("payment_events_bronze",   5, 1, "gold_payment_summary",                                           4500.00, False),
    ("inventory_bronze",        4, 0, "",                                                                3800.00, False),
    ("clickstream_raw",         4, 1, "gold_funnel_analysis",                                           3200.00, False),
    ("sensor_readings_raw",     3, 0, "",                                                                2500.00, False),
    ("erp_staging_bronze",      3, 1, "gold_erp_reconciliation",                                        2200.00, False),
    ("support_tickets_raw",     2, 0, "",                                                                1800.00, False),
    ("ad_spend_bronze",         2, 0, "",                                                                1500.00, False),
    ("fulfillment_events_raw",  2, 1, "gold_fulfillment_sla",                                           1200.00, False),
    ("user_sessions_bronze",    2, 0, "",                                                                1000.00, False),
    ("pricing_overrides_raw",   1, 1, "gold_pricing_analysis",                                          1000.00, False),
]

BRONZE_CLEAN = [
    "raw_leads", "raw_accounts", "raw_contacts", "raw_opportunities",
    "raw_campaigns", "raw_emails", "raw_surveys", "raw_nps_scores",
    "raw_product_catalog", "raw_geography", "raw_employee_data", "raw_vendors",
    "raw_contracts", "raw_sla_definitions", "raw_alert_configs", "raw_feature_flags",
    "raw_cost_centers", "raw_budget_allocations", "raw_regulatory_filings",
    "raw_audit_templates", "raw_taxonomy", "raw_org_hierarchy", "raw_calendar_dim",
    "raw_currency_rates", "raw_channel_definitions", "raw_kpi_definitions",
]  # 26 clean bronze tables → total bronze = 14 + 26 = 40

SILVER_TABLES = [
    "silver_customers", "silver_orders", "silver_transactions", "silver_events",
    "silver_ml_features", "silver_churn_signals", "silver_product_perf",
    "silver_marketing_touches", "silver_support_cases", "silver_fulfillment",
    "silver_inventory_pos", "silver_pricing", "silver_channel_perf",
    "silver_campaign_metrics", "silver_user_activity", "silver_sales_pipeline",
    "silver_revenue_accrual", "silver_cost_allocation", "silver_vendor_spend",
    "silver_employee_metrics", "silver_nps_enriched", "silver_ad_attribution",
    "silver_erp_normalized", "silver_payment_enriched", "silver_segment_features",
    "silver_funnel_events", "silver_session_enriched", "silver_feature_store",
    "silver_model_features_v2", "silver_label_data",
    "silver_geo_enriched", "silver_time_series_agg", "silver_cohort_data",
    "silver_retention_signals", "silver_ltv_features", "silver_risk_scores",
    "silver_compliance_flags", "silver_data_quality_metrics", "silver_lineage_meta",
    "silver_pipeline_telemetry", "silver_job_metrics", "silver_cost_forecast",
    "silver_capacity_plan", "silver_incident_log", "silver_change_log",
    "silver_access_summary", "silver_schema_history", "silver_table_stats",
    "silver_query_patterns", "silver_usage_metrics", "silver_cluster_utilization",
    "silver_serverless_usage", "silver_warehouse_perf", "silver_photon_gains",
    "silver_storage_delta", "silver_compute_costs", "silver_team_productivity",
    "silver_sprint_metrics", "silver_pr_analytics", "silver_test_coverage",
    "silver_deploy_freq", "silver_lead_time", "silver_mttr", "silver_change_fail_rate",
    "silver_sla_compliance", "silver_error_rates", "silver_latency_p99",
    "silver_throughput", "silver_capacity_forecast", "silver_budget_vs_actual",
    "silver_forecast_accuracy", "silver_anomaly_scores", "silver_root_cause_flags",
    "silver_remediation_log", "silver_health_benchmark", "silver_peer_comparison",
    "silver_maturity_scores", "silver_improvement_velocity", "silver_kpi_tracker",
    "silver_action_items",
]  # 80 silver tables

GOLD_TABLES = [
    "gold_revenue_summary", "gold_daily_metrics", "gold_exec_kpis",
    "gold_churn_predictions", "gold_model_inputs", "gold_customer_360",
    "gold_segment_rollup", "gold_product_performance", "gold_payment_summary",
    "gold_funnel_analysis", "gold_erp_reconciliation", "gold_fulfillment_sla",
    "gold_pricing_analysis", "gold_marketing_roi", "gold_campaign_perf",
    "gold_sales_forecast", "gold_ltv_predictions", "gold_cohort_retention",
    "gold_risk_dashboard", "gold_compliance_summary", "gold_data_quality_kpis",
    "gold_platform_health", "gold_cost_efficiency", "gold_team_velocity",
    "gold_workspace_utilization", "gold_sla_adherence", "gold_anomaly_report",
    "gold_incident_summary", "gold_capacity_forecast", "gold_budget_actuals",
    "gold_strategic_kpis", "gold_exec_dashboard", "gold_investor_metrics",
    "gold_ops_runbook", "gold_alert_summary", "gold_escalation_tracker",
    "gold_remediation_status", "gold_maturity_index", "gold_benchmark_scores",
    "gold_quarterly_review",
    "gold_health_scores", "gold_bronze_table_edits", "gold_pipeline_health",
    "gold_ownership_trend", "gold_remediation_backlog",  # our health assessment tables
    "gold_churn_v2", "gold_revenue_forecast_v3", "gold_segment_v4",
    "gold_ltv_v2", "gold_attribution_v2", "gold_funnel_v2", "gold_cohort_v2",
    "gold_ml_perf_v2", "gold_feature_importance", "gold_shap_analysis",
    "gold_model_drift_scores", "gold_data_drift_metrics", "gold_bias_report",
    "gold_fairness_metrics", "gold_explainability_report", "gold_audit_trail",
    "gold_gdpr_compliance", "gold_ccpa_compliance", "gold_sox_controls",
    "gold_iso_evidence", "gold_vendor_risk", "gold_third_party_access",
    "gold_data_catalog_completeness", "gold_lineage_coverage", "gold_ownership_map",
    "gold_access_patterns", "gold_query_efficiency", "gold_compute_allocation",
    "gold_storage_tiering", "gold_cold_data_candidates", "gold_schema_evolution",
    "gold_breaking_changes", "gold_consumer_impact",
]  # 80 gold tables

ENGINEERS = [
    "alice.chen@company.com", "bob.kumar@company.com", "carlos.santos@company.com",
    "diana.patel@company.com", "erik.johansson@company.com", "fatima.ali@company.com",
    "grace.liu@company.com", "henry.brown@company.com", "irene.garcia@company.com",
    "james.wilson@company.com", "kate.murphy@company.com", "liam.zhang@company.com",
    "maya.rodriguez@company.com", "noah.kim@company.com", "olivia.taylor@company.com",
]

PIPELINE_NAMES = [
    "customer_churn_etl", "revenue_pipeline_v1", "ml_feature_refresh",
    "order_processing_daily", "inventory_sync_hourly", "customer_360_builder",
    "marketing_attribution_etl", "payment_reconciliation", "fraud_detection_pipeline",
    "sales_forecast_job", "support_ticket_enrichment", "ad_spend_ingestion",
    "erp_sync_nightly", "clickstream_processor", "session_aggregator",
    "campaign_performance_etl", "product_catalog_sync", "fulfillment_tracker",
    "nps_score_processor", "risk_scoring_pipeline", "compliance_audit_etl",
    "data_quality_monitor", "schema_drift_detector", "lineage_crawler",
    "usage_analytics_daily", "cost_allocation_etl", "capacity_planner",
    "sla_monitor_pipeline", "alert_aggregator", "incident_processor",
    "kpi_calculator_v2", "feature_store_updater", "label_generator",
    "model_retraining_trigger", "prediction_scorer_batch", "anomaly_detector",
    "root_cause_analyzer", "remediation_tracker", "health_score_calculator",
    "peer_benchmark_sync",
]

# ── 1. raw_ws_tables ─────────────────────────────────────────────────────────
print("Generating raw_ws_tables …")

edited_bronze_names = {r[0] for r in BRONZE_EDITED}
all_bronze_names = [r[0] for r in BRONZE_EDITED] + BRONZE_CLEAN  # 14 + 26 = 40

tables_rows = []
catalogs = ["main"] * 18 + ["analytics"] * 2
for i, tname in enumerate(all_bronze_names):
    cat = catalogs[i % len(catalogs)]
    has_owner = tname not in edited_bronze_names and random.random() < 0.82
    owner = random.choice(ENGINEERS) if has_owner else None
    has_comment = tname not in edited_bronze_names and random.random() < 0.75
    naming_viol = random.random() < 0.20  # 20% violation rate for bronze
    created_back = random.randint(60, 540)
    tables_rows.append((
        f"TBL-{i:05d}", tname, cat, f"{cat}_bronze", "bronze",
        owner, bool(owner), has_comment, naming_viol,
        random.randint(5000, 5000000),
        _ts(created_back), _ts(random.randint(1, 30)),
    ))

silver_start = len(all_bronze_names)
for i, tname in enumerate(SILVER_TABLES):
    j = silver_start + i
    cat = "main" if i % 4 != 0 else "analytics"
    has_owner = random.random() < 0.88
    owner = random.choice(ENGINEERS) if has_owner else None
    naming_viol = random.random() < 0.38
    created_back = random.randint(30, 400)
    tables_rows.append((
        f"TBL-{j:05d}", tname, cat, f"{cat}_silver", "silver",
        owner, bool(owner), True, naming_viol,
        random.randint(10000, 20000000),
        _ts(created_back), _ts(random.randint(1, 14)),
    ))

gold_start = silver_start + len(SILVER_TABLES)
for i, tname in enumerate(GOLD_TABLES):
    j = gold_start + i
    cat = "main" if i % 5 != 0 else "analytics"
    has_owner = random.random() < 0.91
    owner = random.choice(ENGINEERS) if has_owner else None
    naming_viol = random.random() < 0.32
    created_back = random.randint(15, 300)
    tables_rows.append((
        f"TBL-{j:05d}", tname, cat, f"{cat}_gold", "gold",
        owner, bool(owner), True, naming_viol,
        random.randint(500, 5000000),
        _ts(created_back), _ts(random.randint(1, 7)),
    ))

tables_schema = StructType([
    StructField("table_id", StringType(), False),
    StructField("table_name", StringType(), False),
    StructField("catalog_name", StringType(), False),
    StructField("schema_name", StringType(), False),
    StructField("data_layer", StringType(), False),
    StructField("owner_email", StringType(), True),
    StructField("has_owner_tag", BooleanType(), False),
    StructField("has_table_comment", BooleanType(), False),
    StructField("naming_violation", BooleanType(), False),
    StructField("row_count_approx", LongType(), False),
    StructField("created_at", StringType(), False),
    StructField("last_ddl_at", StringType(), False),
])
tables_df = spark.createDataFrame(tables_rows, tables_schema).select(
    "table_id", "table_name", "catalog_name", "schema_name", "data_layer",
    "owner_email", "has_owner_tag", "has_table_comment", "naming_violation",
    "row_count_approx",
    F.to_timestamp("created_at").alias("created_at"),
    F.to_timestamp("last_ddl_at").alias("last_ddl_at"),
)
_save(tables_df, "raw_ws_tables")

# ── 2. raw_ws_pipelines ───────────────────────────────────────────────────────
print("Generating raw_ws_pipelines …")

# Critical pipelines (40%+ failure rate, named in README)
CRITICAL_PIPES = {
    "customer_churn_etl": (False, True, False, True, 0.43),    # no owner, prod, hardcoded_paths, no_dq
    "revenue_pipeline_v1": (False, True, True, False, 0.41),   # no owner, prod, hardcoded_paths
    "ml_feature_refresh": (False, True, False, True, 0.45),    # no owner, prod, no_dq
}

pipes_rows = []
no_owner_count = 0
no_owner_prod_count = 0
TOTAL_PIPES = 150
NO_OWNER_TARGET = 31
NO_OWNER_PROD_TARGET = 9

# First add all named pipelines
named_pipes = PIPELINE_NAMES[:40]  # use first 40 named ones
auto_pipes = [f"pipeline_{i:04d}" for i in range(TOTAL_PIPES - len(named_pipes))]
all_pipe_names = named_pipes + auto_pipes

schedules = ["hourly", "daily", "daily", "daily", "weekly", "manual"]

for i, pname in enumerate(all_pipe_names):
    if pname in CRITICAL_PIPES:
        no_owner, is_prod, hardcoded, no_dq, fail_rate = CRITICAL_PIPES[pname]
        has_owner_tag = not no_owner
        owner = None if no_owner else random.choice(ENGINEERS)
        if no_owner:
            no_owner_count += 1
        if no_owner and is_prod:
            no_owner_prod_count += 1
    else:
        is_prod = i < 60  # first 60 are production
        # Distribute no-owner slots: exclude critical pipes (already counted)
        remaining_no_owner = NO_OWNER_TARGET - no_owner_count - len(CRITICAL_PIPES)
        remaining_slots = TOTAL_PIPES - i - len([p for p in CRITICAL_PIPES if p not in all_pipe_names[:i]])
        need_no_owner = (remaining_no_owner > 0) and (
            (no_owner_count < NO_OWNER_TARGET) and
            (remaining_no_owner / max(1, remaining_slots) > random.random())
        )
        if need_no_owner:
            has_owner_tag = False
            owner = None
            no_owner_count += 1
            if is_prod and no_owner_prod_count < NO_OWNER_PROD_TARGET:
                no_owner_prod_count += 1
        else:
            has_owner_tag = True
            owner = random.choice(ENGINEERS)
        hardcoded = not has_owner_tag and random.random() < 0.4
        no_dq = not has_owner_tag and random.random() < 0.3
        fail_rate = round(random.uniform(0.02, 0.15), 3) if has_owner_tag else round(random.uniform(0.05, 0.25), 3)

    last_status = (
        "failed" if fail_rate > 0.35 else
        "warning" if fail_rate > 0.15 else
        "succeeded"
    )

    pipes_rows.append((
        f"PIPE-{i:06d}", pname, owner, has_owner_tag, is_prod,
        random.choice(schedules), not no_dq, not hardcoded,
        last_status, _date(random.randint(0, 7)),
        random.randint(120, 3600),
        _ts(random.randint(90, 540)),
    ))

pipes_schema = StructType([
    StructField("pipeline_id", StringType(), False),
    StructField("pipeline_name", StringType(), False),
    StructField("owner_email", StringType(), True),
    StructField("has_owner_tag", BooleanType(), False),
    StructField("is_production", BooleanType(), False),
    StructField("schedule_type", StringType(), False),
    StructField("has_dq_expectations", BooleanType(), False),
    StructField("has_clean_paths", BooleanType(), False),
    StructField("last_run_status", StringType(), False),
    StructField("last_run_date", StringType(), False),
    StructField("avg_duration_sec", IntegerType(), False),
    StructField("created_at", StringType(), False),
])
pipes_df = spark.createDataFrame(pipes_rows, pipes_schema).select(
    "pipeline_id", "pipeline_name", "owner_email", "has_owner_tag", "is_production",
    "schedule_type", "has_dq_expectations", "has_clean_paths", "last_run_status",
    F.to_date("last_run_date").alias("last_run_date"),
    "avg_duration_sec",
    F.to_timestamp("created_at").alias("created_at"),
)
_save(pipes_df, "raw_ws_pipelines")

print(f"  → no_owner_count={no_owner_count}, no_owner_prod_count={no_owner_prod_count}")

# ── 3. raw_ws_jobs ────────────────────────────────────────────────────────────
print("Generating raw_ws_jobs …")

job_names = [f"job_{i:04d}" for i in range(80)]
job_names[:10] = [
    "daily_etl_orchestrator", "nightly_ml_training", "weekly_report_gen",
    "feature_store_refresh", "model_scoring_batch", "data_quality_check",
    "archive_old_data", "cost_allocation_run", "compliance_export", "backup_metadata",
]
jobs_rows = []
for i, jname in enumerate(job_names):
    has_owner = random.random() < 0.82
    owner = random.choice(ENGINEERS) if has_owner else None
    cluster_type = "classic" if random.random() < 0.35 else "serverless"
    jobs_rows.append((
        f"JOB-{i:06d}", jname, owner, has_owner, cluster_type,
        _ts(random.randint(60, 540)),
    ))

jobs_df = spark.createDataFrame(
    jobs_rows,
    "job_id string, job_name string, owner_email string, has_owner_tag boolean, cluster_type string, created_at string",
).select(
    "job_id", "job_name", "owner_email", "has_owner_tag", "cluster_type",
    F.to_timestamp("created_at").alias("created_at"),
)
_save(jobs_df, "raw_ws_jobs")

# ── 4. raw_ws_job_runs ────────────────────────────────────────────────────────
print("Generating raw_ws_job_runs …")

# ~500 runs over 90 days. Critical pipelines have 40%+ failure rates.
CRITICAL_PIPE_IDS = {
    pname: f"PIPE-{i:06d}"
    for i, pname in enumerate(all_pipe_names[:40])
    if pname in CRITICAL_PIPES
}

runs_rows = []
run_id = 0
# Generate runs for each pipeline — more runs for critical ones
for i, pname in enumerate(all_pipe_names):
    pipe_id = f"PIPE-{i:06d}"
    n_runs = random.randint(5, 12)
    is_critical = pname in CRITICAL_PIPES
    fail_rate = CRITICAL_PIPES[pname][4] if is_critical else random.uniform(0.02, 0.2)

    for r in range(n_runs):
        days_back = random.randint(0, 89)
        duration = random.randint(60, 7200)
        rand_val = random.random()
        status = (
            "failed" if rand_val < fail_rate else
            "cancelled" if rand_val < fail_rate + 0.08 else
            "succeeded"
        )
        trigger = random.choice(["schedule", "schedule", "schedule", "manual", "api"])
        runs_rows.append((
            f"RUN-{run_id:08d}", pipe_id, _ts(days_back, jitter_hours=12),
            _ts(days_back, jitter_hours=12),  # end_time approximate
            status, duration, trigger,
        ))
        run_id += 1
        if run_id >= 520:
            break
    if run_id >= 520:
        break

runs_df = spark.createDataFrame(
    runs_rows,
    "run_id string, pipeline_id string, start_time string, end_time string, "
    "status string, duration_sec int, triggered_by string",
).select(
    "run_id", "pipeline_id",
    F.to_timestamp("start_time").alias("start_time"),
    F.to_timestamp("end_time").alias("end_time"),
    "status", "duration_sec", "triggered_by",
)
_save(runs_df, "raw_ws_job_runs")

# ── 5. raw_ws_audit_events ────────────────────────────────────────────────────
print("Generating raw_ws_audit_events …")

# Distribution per table: (table_name, edit_count)
AUDIT_DIST = [(r[0], r[1]) for r in BRONZE_EDITED]

QUERY_SNIPPETS = {
    "INSERT": "INSERT INTO {table} SELECT * FROM staging_temp WHERE ...",
    "UPDATE": "UPDATE {table} SET status = 'processed', updated_at = NOW() WHERE ...",
    "DELETE": "DELETE FROM {table} WHERE created_at < DATEADD(day, -90, NOW())",
    "MERGE":  "MERGE INTO {table} t USING source s ON t.id = s.id WHEN MATCHED THEN ...",
    "TRUNCATE": "TRUNCATE TABLE {table}",
}

audit_rows = []
evt_id = 0
for tname, count in AUDIT_DIST:
    for _ in range(count):
        days_back = random.randint(0, 89)
        action = random.choices(DML_TYPES, weights=DML_WEIGHTS)[0]
        user = random.choice(ENGINEERS)
        snippet = QUERY_SNIPPETS[action].format(table=tname)[:120]
        audit_rows.append((
            f"EVT-{evt_id:08d}",
            _ts(days_back, jitter_hours=8),
            user, action, tname, "bronze",
            random.randint(1000, 5000000),
            snippet,
        ))
        evt_id += 1

audit_df = spark.createDataFrame(
    audit_rows,
    "event_id string, event_time string, user_email string, action_type string, "
    "table_name string, data_layer string, bytes_affected long, query_snippet string",
).select(
    "event_id",
    F.to_timestamp("event_time").alias("event_time"),
    "user_email", "action_type", "table_name", "data_layer",
    "bytes_affected", "query_snippet",
)
_save(audit_df, "raw_ws_audit_events")

# ── 6. raw_ws_ml_experiments ──────────────────────────────────────────────────
print("Generating raw_ws_ml_experiments …")

exp_domains = [
    "churn_prediction", "revenue_forecast", "lead_scoring", "fraud_detection",
    "product_recommendation", "demand_forecast", "customer_segmentation",
    "price_optimization", "sentiment_analysis", "anomaly_detection",
    "ltv_prediction", "next_best_action",
]
exps_rows = []
for i in range(60):
    domain = exp_domains[i % len(exp_domains)]
    version = (i // len(exp_domains)) + 1
    name = f"{domain}_v{version}"
    has_owner = random.random() < 0.75
    owner = random.choice(ENGINEERS) if has_owner else None
    days_since_run = random.randint(0, 90)
    is_stale = days_since_run > 30
    has_model = random.random() < 0.55
    has_desc = random.random() < 0.65
    user_slug = owner.split("@")[0].replace(".", "_") if owner else "service_account"
    exps_rows.append((
        f"EXP-{i:06d}", name, owner,
        f"/Users/{user_slug}/ml/{name}",
        _date(days_since_run), is_stale, has_model, has_desc,
        _ts(random.randint(90, 540)),
    ))

exps_df = spark.createDataFrame(
    exps_rows,
    "experiment_id string, experiment_name string, owner_email string, "
    "workspace_path string, last_run_date string, is_stale boolean, "
    "has_registered_model boolean, has_description boolean, created_at string",
).select(
    "experiment_id", "experiment_name", "owner_email", "workspace_path",
    F.to_date("last_run_date").alias("last_run_date"),
    "is_stale", "has_registered_model", "has_description",
    F.to_timestamp("created_at").alias("created_at"),
)
_save(exps_df, "raw_ws_ml_experiments")

# ── 7. raw_ws_ml_models ───────────────────────────────────────────────────────
print("Generating raw_ws_ml_models …")

model_names = [
    "churn_classifier_v2", "revenue_forecaster", "lead_scorer", "fraud_detector_v3",
    "product_recommender", "demand_planner", "customer_segmenter", "price_optimizer",
    "sentiment_classifier", "anomaly_detector", "ltv_estimator", "nba_agent",
    "retention_predictor", "upsell_scorer", "campaign_response", "risk_rater",
    "approval_classifier", "document_extractor", "entity_tagger", "intent_classifier",
    "next_action_predictor", "engagement_scorer", "health_index_model",
    "feature_importance_tracker", "drift_detector", "bias_monitor",
    "quality_gate_model", "sla_predictor", "capacity_forecaster", "cost_estimator",
]

# First 2 models are the "stale features" ones — read from ml_features_bronze
STALE_MODELS = [("churn_classifier_v2", "ml_features_bronze"), ("retention_predictor", "ml_features_bronze")]

models_rows = []
for i, mname in enumerate(model_names):
    if i < len(STALE_MODELS):
        _, features_table = STALE_MODELS[i]
        features_layer = "bronze"
        # ml_features_bronze had 12 edits; last edit was recent
        features_last_modified = _date(random.randint(5, 25))
        is_stale_features = True
        serving_endpoint = f"{mname.replace('_', '-')}-endpoint"
    else:
        features_table = random.choice(SILVER_TABLES[:20])
        features_layer = "silver"
        features_last_modified = _date(random.randint(30, 120))
        is_stale_features = False
        serving_endpoint = f"{mname.replace('_', '-')}-endpoint" if random.random() < 0.6 else None

    owner = random.choice(ENGINEERS)
    last_train = _date(random.randint(1, 45))
    registered_in_uc = random.random() < 0.73
    models_rows.append((
        f"MDL-{i:06d}", mname, serving_endpoint, features_table, features_layer,
        last_train, features_last_modified, is_stale_features, owner, registered_in_uc,
    ))

models_df = spark.createDataFrame(
    models_rows,
    "model_id string, model_name string, serving_endpoint_name string, "
    "upstream_features_table string, features_table_layer string, "
    "last_training_date string, features_last_modified_date string, "
    "is_serving_stale_features boolean, owner_email string, registered_in_uc boolean",
).select(
    "model_id", "model_name", "serving_endpoint_name",
    "upstream_features_table", "features_table_layer",
    F.to_date("last_training_date").alias("last_training_date"),
    F.to_date("features_last_modified_date").alias("features_last_modified_date"),
    "is_serving_stale_features", "owner_email", "registered_in_uc",
)
_save(models_df, "raw_ws_ml_models")

# ── Gold tables ───────────────────────────────────────────────────────────────
print("\nBuilding gold tables …")

# ── gold_bronze_table_edits (derived from BRONZE_EDITED + raw_ws_audit_events) ─
print("Building gold_bronze_table_edits …")

# Build gold_bronze_table_edits directly from Python (all data pre-defined in BRONZE_EDITED).
bronze_edit_rows = []
for tname, edit_count, dl_count, dl_tables, rerun_cost, is_critical in BRONZE_EDITED:
    # Find the most recent event for this table
    last_editor = random.choice(ENGINEERS)
    last_edit_days = random.randint(1, 30)
    last_action = random.choices(DML_TYPES[:4], weights=[0.4, 0.3, 0.1, 0.2])[0]
    severity = "critical" if is_critical else "high"
    bronze_edit_rows.append((
        tname, f"main.main_bronze",
        edit_count, last_editor, _date(last_edit_days), last_action,
        dl_count, dl_tables, decimal.Decimal(str(rerun_cost)), severity,
    ))

bronze_edits_df = spark.createDataFrame(
    bronze_edit_rows,
    StructType([
        StructField("table_name", StringType(), False),
        StructField("catalog_schema", StringType(), False),
        StructField("edit_count_90d", IntegerType(), False),
        StructField("last_editor_email", StringType(), False),
        StructField("last_edit_date", StringType(), False),
        StructField("last_action_type", StringType(), False),
        StructField("downstream_gold_table_count", IntegerType(), False),
        StructField("downstream_gold_tables", StringType(), False),
        StructField("estimated_rerun_cost_usd", DecimalType(10, 2), False),
        StructField("severity", StringType(), False),
    ])
).select(
    "table_name", "catalog_schema", "edit_count_90d", "last_editor_email",
    F.to_date("last_edit_date").alias("last_edit_date"),
    "last_action_type", "downstream_gold_table_count", "downstream_gold_tables",
    "estimated_rerun_cost_usd", "severity",
)
_save(bronze_edits_df, "gold_bronze_table_edits")

# ── gold_pipeline_health ──────────────────────────────────────────────────────
print("Building gold_pipeline_health …")

spark.sql(f"""
    CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.gold_pipeline_health
    COMMENT 'Pipeline health: ownership, DQ coverage, failure rates, anti-pattern count. One row per pipeline. Drives the ETL Hygiene deep-dive page.'
    AS
    SELECT
      p.pipeline_id,
      p.pipeline_name,
      p.owner_email,
      p.has_owner_tag,
      p.is_production,
      p.has_dq_expectations,
      NOT p.has_clean_paths AS uses_hardcoded_paths,
      COALESCE(ROUND(failed_runs * 1.0 / NULLIF(total_runs, 0), 3), 0.0) AS failure_rate_30d,
      p.avg_duration_sec,
      (CASE WHEN NOT p.has_owner_tag THEN 1 ELSE 0 END +
       CASE WHEN NOT p.has_dq_expectations THEN 1 ELSE 0 END +
       CASE WHEN NOT p.has_clean_paths THEN 1 ELSE 0 END) AS anti_pattern_count,
      CASE
        WHEN COALESCE(failed_runs * 1.0 / NULLIF(total_runs, 0), 0) > 0.35 THEN 'critical'
        WHEN COALESCE(failed_runs * 1.0 / NULLIF(total_runs, 0), 0) > 0.15
          OR NOT p.has_owner_tag THEN 'warning'
        ELSE 'healthy'
      END AS health_status
    FROM {CATALOG}.{SCHEMA}.raw_ws_pipelines p
    LEFT JOIN (
      SELECT pipeline_id,
             COUNT(*) AS total_runs,
             SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_runs
      FROM {CATALOG}.{SCHEMA}.raw_ws_job_runs
      GROUP BY pipeline_id
    ) r ON p.pipeline_id = r.pipeline_id
""")

# ── gold_health_scores (synthetic scores, not derived from raw) ───────────────
print("Building gold_health_scores …")

# Scores over 30 days. Target today's values and interpolate backward.
SCORE_TARGETS_TODAY = {
    "overall": (68, -3),
    "etl_hygiene": (55, -5),
    "ml_ai_governance": (62, 2),
    "ownership_access": (71, 8),
    "data_quality": (78, 1),
}

score_rows = []
for dim, (score_today, delta_30d) in SCORE_TARGETS_TODAY.items():
    score_30d_ago = score_today - delta_30d
    for day_back in range(30, -1, -1):
        progress = 1.0 - (day_back / 30.0)
        score = round(score_30d_ago + (score_today - score_30d_ago) * progress + random.uniform(-0.8, 0.8))
        score = max(40, min(100, score))
        report_dt = (NOW - timedelta(days=day_back)).strftime("%Y-%m-%d")
        # Critical/high/medium counts roughly inverse to score
        crit = max(0, round(8 - (score - 50) * 0.08 + random.uniform(-0.5, 0.5)))
        high = max(0, round(15 - (score - 50) * 0.10 + random.uniform(-1, 1)))
        med = max(0, round(30 - (score - 50) * 0.15 + random.uniform(-2, 2)))
        if dim == "overall":
            crit = max(0, round(6 + (68 - score) * 0.2 + random.uniform(-0.3, 0.3)))
            high = max(0, round(11 + (68 - score) * 0.3 + random.uniform(-0.5, 0.5)))
            med = max(0, round(23 + (68 - score) * 0.4 + random.uniform(-1, 1)))
        score_rows.append((report_dt, dim, score, delta_30d, crit, high, med))

scores_df = spark.createDataFrame(
    score_rows,
    "report_date string, dimension string, score int, score_delta_30d int, "
    "critical_count int, high_count int, medium_count int",
).select(
    F.to_date("report_date").alias("report_date"),
    "dimension", "score", "score_delta_30d", "critical_count", "high_count", "medium_count",
)
_save(scores_df, "gold_health_scores")

# ── gold_ownership_trend ──────────────────────────────────────────────────────
print("Building gold_ownership_trend …")

# 30-day trend: starts at ~58%, trends to ~69%
trend_rows = []
for day_back in range(30, -1, -1):
    progress = 1.0 - (day_back / 30.0)
    coverage = round(58.0 + (69.0 - 58.0) * progress + random.uniform(-0.5, 0.5), 2)
    owned = round(60 * coverage / 100)
    report_dt = (NOW - timedelta(days=day_back)).strftime("%Y-%m-%d")
    trend_rows.append((report_dt, 60, owned, coverage, 95.0))

trend_df = spark.createDataFrame(
    trend_rows,
    "report_date string, total_production_pipelines int, owned_production_pipelines int, "
    "ownership_coverage_pct double, goal_pct double",
).select(
    F.to_date("report_date").alias("report_date"),
    "total_production_pipelines", "owned_production_pipelines",
    "ownership_coverage_pct", "goal_pct",
)
_save(trend_df, "gold_ownership_trend")

# ── gold_remediation_backlog ──────────────────────────────────────────────────
print("Building gold_remediation_backlog …")

REMEDIATION_FINDINGS = [
    # Critical findings (6 total)
    ("FND-000001", "critical", "ETL Hygiene", "table", "raw_transactions",
     None, "47 direct DML writes in 90 days — bypasses all pipeline expectations and constraints",
     34000.00, "Revoke direct write permissions; route all changes through pipeline with CONSTRAINT", 3),
    ("FND-000002", "critical", "ETL Hygiene", "table", "ml_features_bronze",
     None, "12 direct DML writes — 2 serving models reading stale features (churn_classifier_v2, retention_predictor)",
     18000.00, "Audit model training pipeline; migrate features to silver layer before next retraining", 5),
    ("FND-000003", "critical", "ETL Hygiene", "table", "customer_events_bronze",
     None, "9 direct DML writes — downstream gold tables for executive weekly reports affected",
     14000.00, "Revoke direct write permissions; add NOT NULL CONSTRAINT and DQ expectations", 3),
    ("FND-000004", "critical", "Ownership & Access", "pipeline", "customer_churn_etl",
     None, "No owner tag; 9 dependent pipelines and 2 ML models blocked when this fails",
     12000.00, "Assign owner tag; notify engineering lead; add runbook link to pipeline config", 1),
    ("FND-000005", "critical", "ETL Hygiene", "pipeline", "revenue_pipeline_v1",
     None, "43% failure rate over 30 days; hardcoded S3 paths break on workspace migration",
     9000.00, "Replace hardcoded paths with UC volume references; add alerting on failure", 4),
    ("FND-000006", "critical", "ML/AI Governance", "ml_model", "churn_classifier_v2",
     "alice.chen@company.com",
     "Serving endpoint reads features from ml_features_bronze — a bronze table with 12 recent direct writes",
     5000.00, "Retrain on silver_ml_features; add feature lineage check to CI/CD pipeline", 5),

    # High findings (11 total)
    ("FND-000007", "high", "Ownership & Access", "pipeline", "ml_feature_refresh",
     None, "No owner tag; 45% failure rate — ML retraining jobs fail silently when this pipeline breaks",
     4500.00, "Assign owner tag; add failure alert to oncall rotation", 1),
    ("FND-000008", "high", "Ownership & Access", "pipeline", "revenue_pipeline_v1",
     None, "No owner tag on a production pipeline processing $3M+ weekly revenue data",
     4000.00, "Assign owner from revenue engineering team; document in runbook", 1),
    ("FND-000009", "high", "ML/AI Governance", "ml_model", "retention_predictor",
     "bob.kumar@company.com",
     "Model serves from ml_features_bronze with recent direct writes — feature drift undetected",
     3800.00, "Retrain on clean silver features; add feature store validation gate", 5),
    ("FND-000010", "high", "ML/AI Governance", "ml_experiment", "churn_prediction_v2",
     None, "No owner and no description — experiment cannot be reproduced or audited",
     3200.00, "Assign owner; add MLflow description with training data ref and evaluation results", 1),
    ("FND-000011", "high", "ETL Hygiene", "table", "order_items_bronze",
     "carlos.santos@company.com",
     "6 direct DML writes in 90 days — feeds gold_product_performance, a KPI source",
     5000.00, "Remove direct write access; add pipeline expectation on row count", 3),
    ("FND-000012", "high", "ETL Hygiene", "table", "payment_events_bronze",
     None, "5 direct DML writes — payment reconciliation data mutated outside pipeline",
     4500.00, "Revoke write permissions; enforce data contract on schema", 3),
    ("FND-000013", "high", "Ownership & Access", "pipeline", "marketing_attribution_etl",
     None, "No owner; pipeline has been running for 14 months with no documented owner",
     2800.00, "Audit pipeline history; assign owner from marketing analytics team", 1),
    ("FND-000014", "high", "ML/AI Governance", "ml_model", "fraud_detector_v3",
     "diana.patel@company.com",
     "Model not registered in Unity Catalog — no lineage tracking or version control",
     2500.00, "Register model in UC; link to experiment and training dataset", 2),
    ("FND-000015", "high", "Ownership & Access", "pipeline", "payment_reconciliation",
     None, "No owner tag on critical financial reconciliation pipeline",
     2200.00, "Assign owner from finance engineering team; add to SOX control inventory", 1),
    ("FND-000016", "high", "ETL Hygiene", "pipeline", "erp_sync_nightly",
     "erik.johansson@company.com",
     "Uses hardcoded credential path and S3 bucket — will fail on workspace migration",
     2000.00, "Migrate credentials to Databricks secrets; use UC external location", 3),
    ("FND-000017", "high", "Ownership & Access", "pipeline", "fraud_detection_pipeline",
     None, "No owner; fraud detection system has no designated incident responder",
     1800.00, "Assign owner from security engineering; add to incident response runbook", 1),

    # Medium findings (23 total)
    ("FND-000018", "medium", "ETL Hygiene", "table", "inventory_bronze",
     "fatima.ali@company.com", "4 direct DML writes — inventory staging data mutated ad-hoc",
     3800.00, "Revoke direct write; add pipeline ownership tag", 2),
    ("FND-000019", "medium", "ETL Hygiene", "table", "clickstream_raw",
     "grace.liu@company.com", "4 direct DML writes — clickstream events mutated post-ingestion",
     3200.00, "Enforce immutable ingest pattern; add APPEND-only constraint", 2),
    ("FND-000020", "medium", "ETL Hygiene", "table", "sensor_readings_raw",
     None, "3 direct DML writes on IoT sensor data — breaks time-series continuity",
     2500.00, "Switch to append-only ingest; fix at-source instead of post-ingest", 2),
    ("FND-000021", "medium", "Data Quality", "table", "raw_ws_tables",
     None, "35% of tables have naming violations (not following {layer}_{domain}_{entity} convention)",
     2000.00, "Run automated rename proposal script; plan migration over Q3", 5),
    ("FND-000022", "medium", "Data Quality", "table", "silver_tables_batch",
     None, "38% of silver tables have naming violations — inconsistent domain prefixes",
     1800.00, "Adopt and enforce naming standard in CI/CD schema linting step", 5),
    ("FND-000023", "medium", "ML/AI Governance", "ml_experiment", "revenue_forecast_v2",
     "henry.brown@company.com", "Experiment stale for 45 days — model may be outdated vs current data distribution",
     1600.00, "Schedule retraining run or archive if no longer in use", 2),
    ("FND-000024", "medium", "ML/AI Governance", "ml_experiment", "lead_scoring_v1",
     None, "Experiment has no description — training data, features, and evaluation not documented",
     1500.00, "Add MLflow run tags: dataset_version, feature_list, evaluation_metric", 1),
    ("FND-000025", "medium", "ETL Hygiene", "table", "erp_staging_bronze",
     "irene.garcia@company.com", "3 direct DML writes on ERP staging data",
     2200.00, "Revoke write access; add data contract validation in ingestion pipeline", 2),
    ("FND-000026", "medium", "Ownership & Access", "pipeline", "clickstream_processor",
     None, "No owner tag; high-volume pipeline with no incident responder",
     1500.00, "Assign owner from web analytics team", 1),
    ("FND-000027", "medium", "Ownership & Access", "pipeline", "session_aggregator",
     None, "No owner tag; runs daily but no team tracks failures",
     1400.00, "Assign owner; add failure notification to team Slack channel", 1),
    ("FND-000028", "medium", "Data Quality", "pipeline", "data_quality_monitor",
     "james.wilson@company.com", "8 pipelines lack data quality expectations — no row count or freshness checks",
     1200.00, "Add minimum row count expectation and max-age freshness check to each pipeline", 3),
    ("FND-000029", "medium", "ETL Hygiene", "table", "support_tickets_raw",
     None, "2 direct DML writes on support ticket data — ticket history modified post-close",
     1800.00, "Enforce immutable event log pattern; investigate who made changes and why", 1),
    ("FND-000030", "medium", "ETL Hygiene", "table", "ad_spend_bronze",
     "kate.murphy@company.com", "2 direct DML writes on advertising spend data",
     1500.00, "Revert ad spend data to last-known-good snapshot; add pipeline constraint", 2),
    ("FND-000031", "medium", "ML/AI Governance", "ml_model", "product_recommender",
     "liam.zhang@company.com", "Model not registered in Unity Catalog — no governance trail",
     1200.00, "Register in UC model registry with experiment link and training data ref", 2),
    ("FND-000032", "medium", "Ownership & Access", "job", "daily_etl_orchestrator",
     None, "Job uses classic compute — 3x higher cost vs serverless equivalent",
     1000.00, "Migrate to serverless compute; estimated 65% cost reduction", 3),
    ("FND-000033", "medium", "Ownership & Access", "pipeline", "schema_drift_detector",
     None, "No owner tag; schema drift detection has no responder when alerts fire",
     900.00, "Assign owner from data platform team; link alert to runbook", 1),
    ("FND-000034", "medium", "Data Quality", "table", "gold_revenue_summary",
     "maya.rodriguez@company.com",
     "Gold table fed by a bronze table with 47 direct writes — downstream quality at risk",
     800.00, "Add freshness monitor on gold_revenue_summary; alert on anomalous row count delta", 1),
    ("FND-000035", "medium", "ETL Hygiene", "table", "fulfillment_events_raw",
     "noah.kim@company.com", "2 direct DML writes on fulfillment events",
     1200.00, "Add NOT NULL constraint on event_id; enforce append-only pattern", 2),
    ("FND-000036", "medium", "ETL Hygiene", "table", "user_sessions_bronze",
     None, "2 direct DML writes on user session data — session replay data affected",
     1000.00, "Revoke write permissions; sessions are immutable by definition", 1),
    ("FND-000037", "medium", "ML/AI Governance", "ml_experiment", "customer_segmentation_v1",
     "olivia.taylor@company.com", "Experiment stale for 38 days",
     900.00, "Retrain on current customer feature set or archive", 2),
    ("FND-000038", "medium", "Ownership & Access", "pipeline", "lineage_crawler",
     None, "No owner tag; lineage metadata is out of date when this fails",
     800.00, "Assign owner from data governance team", 1),
    ("FND-000039", "medium", "Data Quality", "table", "pricing_overrides_raw",
     "alice.chen@company.com", "1 direct DML write on pricing data — override applied outside approval workflow",
     1000.00, "Implement approval workflow for pricing overrides; add audit log", 3),
    ("FND-000040", "medium", "Ownership & Access", "pipeline", "cost_allocation_etl",
     None, "No owner tag on cost allocation pipeline used for chargeback reporting",
     700.00, "Assign owner from FinOps team; add to monthly chargeback review checklist", 1),
]

REMEDIATION_FINDINGS = [
    row[:7] + (decimal.Decimal(str(row[7])),) + row[8:]
    for row in REMEDIATION_FINDINGS
]

backlog_df = spark.createDataFrame(
    REMEDIATION_FINDINGS,
    StructType([
        StructField("finding_id", StringType(), False),
        StructField("severity", StringType(), False),
        StructField("category", StringType(), False),
        StructField("asset_type", StringType(), False),
        StructField("asset_name", StringType(), False),
        StructField("owner_email", StringType(), True),
        StructField("description", StringType(), False),
        StructField("business_impact_usd", DecimalType(10, 2), False),
        StructField("recommended_action", StringType(), False),
        StructField("sprint_estimate_days", IntegerType(), False),
    ])
)
# Add detected_at (all findings detected in the past 90 days, critical ones more recent)
backlog_df = backlog_df.withColumn(
    "detected_at",
    F.to_date(F.expr(
        "CASE severity "
        "WHEN 'critical' THEN date_sub(current_date(), int(rand(42) * 14)) "
        "WHEN 'high'     THEN date_sub(current_date(), int(rand(43) * 30)) "
        "ELSE                 date_sub(current_date(), int(rand(44) * 60)) "
        "END"
    ))
)
_save(backlog_df, "gold_remediation_backlog")

# ── Constraints (for Catalog Explorer lineage) ────────────────────────────────
print("\nApplying constraints …")
for table, col in [
    ("raw_ws_tables", "table_id"),
    ("raw_ws_pipelines", "pipeline_id"),
    ("raw_ws_jobs", "job_id"),
    ("raw_ws_audit_events", "event_id"),
    ("raw_ws_ml_experiments", "experiment_id"),
    ("raw_ws_ml_models", "model_id"),
    ("gold_bronze_table_edits", "table_name"),
    ("gold_remediation_backlog", "finding_id"),
]:
    try:
        spark.sql(f"ALTER TABLE {CATALOG}.{SCHEMA}.{table} ALTER COLUMN {col} SET NOT NULL")
        spark.sql(
            f"ALTER TABLE {CATALOG}.{SCHEMA}.{table} ADD CONSTRAINT {table}_pk PRIMARY KEY ({col}) NOT ENFORCED RELY"
        )
    except Exception as e:
        print(f"  (constraint skip for {table}.{col}: {e})")

# ── Validation ────────────────────────────────────────────────────────────────
print("\n── Validation ──────────────────────────────────────────────────────────")
checks = [
    (f"SELECT edit_count_90d FROM {CATALOG}.{SCHEMA}.gold_bronze_table_edits WHERE table_name = 'raw_transactions'",
     "raw_transactions edit_count = 47"),
    (f"SELECT COUNT(*) AS n FROM {CATALOG}.{SCHEMA}.gold_bronze_table_edits",
     "gold_bronze_table_edits has 14 rows"),
    (f"SELECT ROUND(SUM(CAST(estimated_rerun_cost_usd AS DOUBLE)), 0) FROM {CATALOG}.{SCHEMA}.gold_bronze_table_edits",
     "total rerun cost ≈ $87K"),
    (f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.gold_remediation_backlog WHERE severity = 'critical'",
     "6 critical findings"),
    (f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.gold_remediation_backlog WHERE severity = 'high'",
     "11 high findings"),
    (f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.gold_remediation_backlog WHERE severity = 'medium'",
     "23 medium findings"),
    (f"SELECT score FROM {CATALOG}.{SCHEMA}.gold_health_scores WHERE dimension = 'overall' AND report_date = current_date()",
     "overall score = 68"),
    (f"SELECT score FROM {CATALOG}.{SCHEMA}.gold_health_scores WHERE dimension = 'etl_hygiene' AND report_date = current_date()",
     "ETL Hygiene score = 55"),
    (f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.raw_ws_ml_models WHERE is_serving_stale_features = TRUE",
     "2 models serving stale features"),
    (f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.raw_ws_pipelines WHERE has_owner_tag = FALSE",
     "31 pipelines without owner tag"),
]
for sql, label in checks:
    try:
        result = spark.sql(sql).collect()[0][0]
        print(f"  ✓ {label}: {result}")
    except Exception as e:
        print(f"  ✗ {label}: {e}")

print(f"\n✅ Done. All tables in {CATALOG}.{SCHEMA}")
print("Next: build the Genie space and dashboard (04-ai-bi.md)")

import json as _json  # noqa: E402
if IN_NOTEBOOK:
    dbutils.notebook.exit(_json.dumps({"status": "success", "catalog": CATALOG, "schema": SCHEMA}))
