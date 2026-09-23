"""
Workspace Health Assessment — Data Generation Script
Runs inside the preview app container where M2M credentials are available.
Uses SQL Statements API to create and populate all tables.
"""
import os, sys, time, random, string
from datetime import date, timedelta, datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState, ExecuteStatementRequestOnWaitTimeout

CATALOG = os.environ.get("DEMO_CATALOG", "main")
SCHEMA  = os.environ.get("DEMO_SCHEMA", "workspace_health_assessment")
WAREHOUSE_ID = os.environ.get("DEMO_WAREHOUSE_ID", "")
TODAY = date.today()

def sql(w, statement, wait=True):
    """Execute a SQL statement via the warehouse, polling until complete."""
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=statement,
        wait_timeout="50s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE
    )
    if not wait:
        return resp
    # Poll until terminal state
    sid = resp.statement_id
    state = resp.status.state if resp.status else None
    max_polls = 120  # 2 minutes max
    for _ in range(max_polls):
        if state in (StatementState.SUCCEEDED,):
            return resp
        if state in (StatementState.FAILED, StatementState.CANCELED, StatementState.CLOSED):
            err = resp.status.error if resp.status else None
            raise RuntimeError(f"SQL failed ({state}): {err.message if err else 'unknown'}\nSQL: {statement[:300]}")
        if state in (StatementState.RUNNING, StatementState.PENDING):
            time.sleep(1)
            resp = w.statement_execution.get_statement(sid)
            state = resp.status.state if resp.status else None
        else:
            break
    if state != StatementState.SUCCEEDED:
        raise RuntimeError(f"SQL timed out or in unknown state {state}\nSQL: {statement[:300]}")
    return resp

def batch_insert(w, table, rows, cols, batch_size=200):
    """Insert rows in batches via INSERT INTO ... VALUES."""
    fqn = f"`{CATALOG}`.`{SCHEMA}`.`{table}`"
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        values = ", ".join("(" + ", ".join(
            "NULL" if v is None else
            f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" if isinstance(v, (str, date)) else
            str(int(v)) if isinstance(v, bool) else
            str(v)
            for v in row
        ) + ")" for row in batch)
        sql(w, f"INSERT INTO {fqn} ({', '.join(cols)}) VALUES {values}")
        print(f"  Inserted {min(i+batch_size, len(rows))}/{len(rows)} into {table}", flush=True)

def rand_id(prefix, n=6):
    return prefix + "-" + "".join(random.choices(string.digits, k=n))

def rand_date(days_back=90):
    delta = random.randint(0, days_back)
    return TODAY - timedelta(days=delta)

def rand_email(domain="acme.com"):
    names = ["alex.chen","raj.patel","sarah.kim","mike.torres","priya.singh",
             "david.li","emma.jones","carlos.ruiz","nina.wang","tom.harris",
             "lucy.chen","sam.patel","anna.smith","ben.clark","zoe.chen"]
    return random.choice(names) + "@" + domain

# ── Bronze table anchor list ──────────────────────────────────────────────────
BRONZE_EDITED = [
    ("raw_transactions",       47, 3, 34000.00, "critical"),
    ("ml_features_bronze",     12, 2, 18000.00, "critical"),
    ("customer_events_bronze",  9, 2, 14000.00, "critical"),
    ("raw_user_sessions",       6, 1,  3500.00, "high"),
    ("raw_click_events",        5, 1,  3000.00, "high"),
    ("raw_product_catalog",     4, 1,  2500.00, "high"),
    ("raw_payments_bronze",     4, 1,  2200.00, "high"),
    ("raw_shipping_events",     3, 0,  2000.00, "high"),
    ("raw_inventory_bronze",    3, 1,  1800.00, "high"),
    ("raw_ad_impressions",      2, 0,  1600.00, "high"),
    ("raw_support_tickets",     2, 0,  1400.00, "high"),
    ("raw_search_queries",      2, 0,  1200.00, "high"),
    ("raw_device_events",       1, 0,  1000.00, "high"),
    ("raw_geo_events",          1, 0,   800.00, "high"),
]
BRONZE_EDITED_NAMES = {t[0] for t in BRONZE_EDITED}

# ── Critical pipelines ────────────────────────────────────────────────────────
CRITICAL_PIPES = {
    "customer_churn_etl":    {"owner": None, "prod": True,  "failure": 43, "hardcoded": True},
    "revenue_pipeline_v1":   {"owner": None, "prod": True,  "failure": 41, "hardcoded": True},
    "ml_feature_refresh":    {"owner": None, "prod": True,  "failure": 44, "hardcoded": False},
}

# ── Remediation findings ──────────────────────────────────────────────────────
CRITICAL_FINDINGS = [
    ("FND-000001","critical","ETL Hygiene","table","raw_transactions","alex.chen@acme.com",
     "47 direct DML writes in 90 days — bypasses all pipeline expectations",
     34000.00,"Revoke direct write permissions; route all changes through pipeline with CONSTRAINT",3),
    ("FND-000002","critical","ETL Hygiene","table","ml_features_bronze","raj.patel@acme.com",
     "12 direct DML writes — 2 serving models reading stale features",
     18000.00,"Audit model training pipeline; migrate features to silver layer",5),
    ("FND-000003","critical","ETL Hygiene","table","customer_events_bronze","sarah.kim@acme.com",
     "9 direct DML writes — downstream gold tables for executive reports affected",
     14000.00,"Revoke direct write permissions; add CONSTRAINT and pipeline expectations",3),
    ("FND-000004","critical","Ownership & Access","pipeline","customer_churn_etl",None,
     "No owner tag; 9 dependent pipelines blocked when failures occur",
     12000.00,"Assign owner tag; notify engineering lead",2),
    ("FND-000005","critical","ETL Hygiene","pipeline","revenue_pipeline_v1",None,
     "43% failure rate over 30 days; hardcoded S3 paths cause breakage on workspace migration",
     9000.00,"Remove hardcoded paths; add alerting",3),
    ("FND-000006","critical","ML/AI Governance","ml_model","churn_risk_model_v2","priya.singh@acme.com",
     "Serving endpoint reads features from bronze table with recent direct writes",
     5000.00,"Retrain on silver features; add feature lineage check to CI",5),
]

HIGH_FINDINGS_TEMPLATES = [
    ("Ownership & Access","pipeline","No owner tag on production pipeline","Assign owner tag immediately",3),
    ("ML/AI Governance","ml_experiment","Stale experiment not run in >30 days; model may be outdated","Archive or re-run experiment",2),
    ("Ownership & Access","pipeline","Production pipeline has no owner assigned","Add owner tag via UC properties",2),
    ("ETL Hygiene","pipeline","Pipeline has no data quality expectations","Add CONSTRAINT or expectations block",3),
    ("ML/AI Governance","ml_model","Model not registered in Unity Catalog; lineage broken","Register model in UC model registry",4),
    ("Ownership & Access","pipeline","Production pipeline has no owner assigned","Add owner tag; subscribe to alerts",2),
    ("ML/AI Governance","ml_experiment","Experiment lacks description; unclear purpose","Add description and link to model",1),
    ("ETL Hygiene","pipeline","Hardcoded absolute paths in pipeline code","Replace with relative paths or UC volume references",3),
    ("Ownership & Access","table","Table has no owner tag","Assign owner via ALTER TABLE SET TAGS",1),
    ("ML/AI Governance","ml_experiment","No registered model linked to experiment","Register best run as UC model",3),
    ("ETL Hygiene","pipeline","Pipeline has no owner and no DQ expectations","Assign owner and add DQ expectations",4),
]
MEDIUM_FINDINGS_TEMPLATES = [
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("ETL Hygiene","job","Classic cluster job — serverless available","Migrate to serverless for 40% cost savings",2),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("ETL Hygiene","job","Classic cluster job — serverless available","Migrate to serverless for 40% cost savings",2),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("ETL Hygiene","job","Classic cluster job — serverless available","Migrate to serverless for 40% cost savings",2),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Bronze table missing table comment","Add table comment via ALTER TABLE",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
    ("Data Quality","table","Table name violates naming convention","Rename to follow layer_domain_entity pattern",1),
]

def main():
    print("Initializing Databricks client with M2M credentials...", flush=True)
    w = WorkspaceClient()
    print(f"Auth type: {w.config.auth_type}, Host: {w.config.host}", flush=True)

    # Create schema (M2M SP becomes owner, giving it full permissions)
    try:
        w.schemas.delete(full_name=f"{CATALOG}.{SCHEMA}", force=True)
        print("Existing schema deleted", flush=True)
    except Exception:
        pass
    try:
        w.schemas.create(catalog_name=CATALOG, name=SCHEMA,
                         comment="Workspace Health Assessment demo")
        print("Schema created by M2M SP (owner)", flush=True)
    except Exception as e:
        if "already exists" in str(e).lower():
            print("Schema already exists", flush=True)
        else:
            raise

    fq = f"`{CATALOG}`.`{SCHEMA}`"

    # ── DROP EXISTING TABLES ──────────────────────────────────────────────────
    print("\n=== Dropping existing tables ===", flush=True)
    tables = [
        "raw_ws_tables", "raw_ws_pipelines", "raw_ws_jobs", "raw_ws_job_runs",
        "raw_ws_audit_events", "raw_ws_ml_experiments", "raw_ws_ml_models",
        "gold_health_scores", "gold_bronze_table_edits", "gold_pipeline_health",
        "gold_ownership_trend", "gold_remediation_backlog"
    ]
    for t in tables:
        sql(w, f"DROP TABLE IF EXISTS {fq}.`{t}`")
    print("Tables dropped.", flush=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # RAW TABLES
    # ═══════════════════════════════════════════════════════════════════════════

    # ── raw_ws_tables ─────────────────────────────────────────────────────────
    print("\n=== Creating raw_ws_tables ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_tables` (
        table_id STRING COMMENT 'Primary key: TBL-NNNNNN',
        table_name STRING COMMENT 'Table name',
        catalog_name STRING COMMENT 'Catalog',
        schema_name STRING COMMENT 'Schema name ending in _bronze/_silver/_gold',
        data_layer STRING COMMENT 'bronze/silver/gold',
        owner_email STRING COMMENT 'Owner email; nullable for orphaned tables',
        has_owner_tag BOOLEAN COMMENT 'True if owner tag set',
        created_at TIMESTAMP COMMENT 'Creation timestamp',
        last_ddl_at TIMESTAMP COMMENT 'Last schema change',
        table_comment STRING COMMENT 'Table description; nullable',
        naming_violation BOOLEAN COMMENT 'True if name violates layer_domain_entity convention',
        row_count_approx BIGINT COMMENT 'Approximate row count'
    ) USING DELTA COMMENT 'Simulated workspace table metadata'""")

    random.seed(42)
    # Build 200 tables: 40 bronze, 80 silver, 80 gold
    BRONZE_NAMES = list(BRONZE_EDITED_NAMES) + [
        "raw_email_events", "raw_api_calls", "raw_sensor_readings", "raw_weather_data",
        "raw_partner_feeds", "raw_loyalty_events", "raw_returns_bronze", "raw_pricing_bronze",
        "raw_contracts_bronze", "raw_hr_events_bronze", "raw_notifications_bronze",
        "raw_feedback_bronze", "raw_survey_bronze", "raw_audit_log_bronze",
        "raw_order_items_bronze", "raw_cart_events", "raw_wish_list_events",
        "raw_referral_events", "raw_push_notifications", "raw_error_logs",
        "raw_batch_jobs_bronze", "raw_sync_events", "raw_crm_events", "raw_iot_telemetry",
        "raw_warehouse_ops",
    ]
    BRONZE_NAMES = BRONZE_NAMES[:40]

    SILVER_NAMES = [
        "silver_customer_profile", "silver_transaction_summary", "silver_product_catalog",
        "silver_user_sessions", "silver_click_funnel", "silver_payment_summary",
        "silver_shipping_status", "silver_inventory_status", "silver_ad_performance",
        "silver_support_resolution", "silver_search_ranking", "silver_device_fingerprint",
        "silver_geo_enriched", "silver_email_engagement", "silver_api_metrics",
        "silver_sensor_clean", "silver_weather_enriched", "silver_partner_normalized",
        "silver_loyalty_summary", "silver_return_analysis", "silver_price_history",
        "silver_contract_status", "silver_hr_attendance", "silver_notification_status",
        "silver_feedback_sentiment", "silver_survey_results", "silver_audit_clean",
        "silver_order_fulfilment", "silver_cart_abandonment", "silver_wish_conversion",
        "silver_referral_attribution", "silver_push_ctr", "silver_error_classification",
        "silver_batch_performance", "silver_sync_health", "silver_crm_health_score",
        "silver_iot_aggregated", "silver_warehouse_efficiency", "silver_churn_signals",
        "silver_revenue_daily", "silver_feature_store_v1", "silver_feature_store_v2",
        "silver_model_inputs", "silver_experiment_runs", "silver_ab_test_results",
        "silver_cohort_analysis", "silver_ltv_signals", "silver_nps_signals",
        "silver_attribution_model", "silver_marketing_mix", "silver_media_spend",
        "silver_channel_perf", "silver_brand_sentiment", "silver_competitor_monitor",
        "silver_supply_forecast", "silver_demand_signals", "silver_ops_kpis",
        "silver_sla_compliance", "silver_incident_response", "silver_change_log",
        "silver_capacity_plan", "silver_cost_allocation", "silver_infra_metrics",
        "silver_security_events", "silver_access_patterns", "silver_compliance_log",
        "silver_data_catalog_meta", "silver_lineage_clean", "silver_quality_scores",
        "silver_governance_summary", "silver_ownership_clean", "silver_schema_health",
        "silver_pipeline_meta", "silver_job_performance", "silver_workspace_usage",
        "silver_compute_utilization", "silver_storage_usage", "silver_network_traffic",
        "silver_api_latency", "silver_query_performance",
    ][:80]

    GOLD_NAMES = [
        "gold_revenue_summary", "gold_customer_360", "gold_product_performance",
        "gold_executive_kpis", "gold_churn_risk_scores", "gold_ltv_model_output",
        "gold_attribution_report", "gold_marketing_roi", "gold_ops_dashboard",
        "gold_sla_report", "gold_compliance_status", "gold_security_posture",
        "gold_data_quality_report", "gold_lineage_report", "gold_ownership_report",
        "gold_pipeline_health_report", "gold_ml_model_registry", "gold_experiment_catalog",
        "gold_feature_importance", "gold_model_drift_report", "gold_forecast_accuracy",
        "gold_ab_test_outcomes", "gold_cohort_retention", "gold_nps_trend",
        "gold_brand_health", "gold_competitor_landscape", "gold_supply_chain_health",
        "gold_demand_forecast", "gold_workforce_analytics", "gold_cost_efficiency",
        "gold_infrastructure_health", "gold_security_incidents", "gold_audit_trail",
        "gold_governance_posture", "gold_capacity_report", "gold_spend_analysis",
        "gold_channel_attribution", "gold_media_efficiency", "gold_content_performance",
        "gold_customer_journey", "gold_funnel_conversion", "gold_engagement_score",
        "gold_satisfaction_index", "gold_support_quality", "gold_incident_heatmap",
        "gold_change_impact", "gold_technical_debt", "gold_platform_maturity",
        "gold_data_mesh_health", "gold_catalog_completeness", "gold_schema_evolution",
        "gold_query_patterns", "gold_cost_attribution", "gold_utilization_report",
        "gold_cloud_spend", "gold_team_velocity", "gold_sprint_outcomes",
        "gold_okr_progress", "gold_roadmap_health", "gold_dependency_graph",
        "gold_release_quality", "gold_test_coverage", "gold_deployment_frequency",
        "gold_lead_time", "gold_mttr", "gold_change_failure_rate",
        "gold_availability_sla", "gold_performance_baseline", "gold_anomaly_log",
        "gold_prediction_accuracy", "gold_model_performance", "gold_data_freshness",
        "gold_pipeline_reliability", "gold_ownership_health", "gold_access_patterns",
        "gold_workspace_score", "gold_governance_score", "gold_quality_index",
        "gold_etl_health", "gold_ml_governance",
    ][:80]

    NAMING_VIOLATIONS = {
        "raw_user_sessions", "raw_click_events", "silver_customer_profile",
        "silver_transaction_summary", "gold_revenue_summary", "gold_executive_kpis",
        "raw_api_calls", "raw_sensor_readings", "silver_churn_signals",
        "gold_customer_360", "silver_revenue_daily", "gold_product_performance"
    }

    table_rows = []
    for i, tname in enumerate(BRONZE_NAMES):
        cat = "main" if random.random() < 0.9 else "analytics"
        has_owner = tname not in {"raw_email_events","raw_api_calls","raw_sensor_readings",
                                    "raw_weather_data","raw_partner_feeds"}
        owner = rand_email() if has_owner else None
        created = TODAY - timedelta(days=random.randint(30, 540))
        has_comment = tname not in BRONZE_EDITED_NAMES or random.random() < 0.4
        table_rows.append((
            rand_id("TBL", 6), tname, cat, tname.replace("raw_","") + "_bronze" if "_bronze" not in tname else tname.replace("raw_",""),
            "bronze", owner, has_owner, str(created) + " 00:00:00",
            str(created + timedelta(days=random.randint(0,30))) + " 00:00:00",
            None if not has_comment else f"Bronze landing zone for {tname.replace('raw_','').replace('_',' ')}",
            tname in NAMING_VIOLATIONS, random.randint(100000, 50000000)
        ))

    for tname in SILVER_NAMES:
        cat = "main" if random.random() < 0.9 else "analytics"
        has_owner = random.random() < 0.82
        owner = rand_email() if has_owner else None
        created = TODAY - timedelta(days=random.randint(10, 400))
        table_rows.append((
            rand_id("TBL", 6), tname, cat, tname.replace("silver_","") + "_silver",
            "silver", owner, has_owner, str(created) + " 00:00:00",
            str(created + timedelta(days=random.randint(0,20))) + " 00:00:00",
            f"Curated {tname.replace('silver_','').replace('_',' ')} data" if random.random() < 0.75 else None,
            tname in NAMING_VIOLATIONS, random.randint(10000, 5000000)
        ))

    for tname in GOLD_NAMES:
        cat = "main" if random.random() < 0.9 else "analytics"
        has_owner = random.random() < 0.88
        owner = rand_email() if has_owner else None
        created = TODAY - timedelta(days=random.randint(5, 300))
        table_rows.append((
            rand_id("TBL", 6), tname, cat, tname.replace("gold_","") + "_gold",
            "gold", owner, has_owner, str(created) + " 00:00:00",
            str(created + timedelta(days=random.randint(0,10))) + " 00:00:00",
            f"Gold layer {tname.replace('gold_','').replace('_',' ')}" if random.random() < 0.85 else None,
            tname in NAMING_VIOLATIONS, random.randint(1000, 500000)
        ))

    cols = ["table_id","table_name","catalog_name","schema_name","data_layer",
            "owner_email","has_owner_tag","created_at","last_ddl_at",
            "table_comment","naming_violation","row_count_approx"]
    batch_insert(w, "raw_ws_tables", table_rows, cols)
    print(f"  raw_ws_tables: {len(table_rows)} rows", flush=True)

    # ── raw_ws_pipelines ──────────────────────────────────────────────────────
    print("\n=== Creating raw_ws_pipelines ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_pipelines` (
        pipeline_id STRING, pipeline_name STRING, owner_email STRING,
        has_owner_tag BOOLEAN, is_production BOOLEAN,
        schedule_type STRING, has_dq_expectations BOOLEAN,
        uses_hardcoded_paths BOOLEAN, last_run_status STRING,
        last_run_date DATE, avg_duration_sec INT, created_at TIMESTAMP
    ) USING DELTA COMMENT 'Simulated pipeline metadata'""")

    schedules = ["hourly","daily","weekly","manual"]
    statuses  = ["succeeded","failed","warning"]
    pipe_rows = []
    unowned_count = 0
    prod_unowned_count = 0

    # Critical pipelines first
    for pname, pinfo in CRITICAL_PIPES.items():
        pipe_rows.append((
            rand_id("PIPE"), pname, pinfo["owner"], pinfo["owner"] is not None,
            True, "daily", False, pinfo["hardcoded"],
            "failed", str(TODAY - timedelta(days=random.randint(0,3))),
            random.randint(600, 3600), str(TODAY - timedelta(days=random.randint(60,400))) + " 00:00:00"
        ))
        unowned_count += 1
        prod_unowned_count += 1

    # Fill remaining pipelines to reach 150 total (31 unowned, 9 production unowned)
    pipe_names_pool = [
        "revenue_daily_rollup", "customer_360_refresh", "product_catalog_sync",
        "user_session_etl", "click_funnel_pipeline", "payment_reconciliation",
        "shipping_status_update", "inventory_sync", "ad_attribution_pipeline",
        "support_ticket_etl", "search_index_refresh", "device_fingerprint_etl",
        "geo_enrichment_pipeline", "email_engagement_etl", "api_metrics_pipeline",
        "sensor_data_cleanup", "weather_enrichment", "partner_data_normalize",
        "loyalty_points_calc", "returns_processing", "pricing_update_pipeline",
        "contract_status_sync", "hr_attendance_etl", "notification_delivery_etl",
        "feedback_sentiment_pipeline", "survey_results_etl", "audit_log_clean",
        "order_fulfilment_etl", "cart_abandonment_track", "wish_list_conversion",
        "referral_attribution_pipeline", "push_notification_etl", "error_log_classifier",
        "batch_job_monitor", "crm_sync_pipeline", "iot_aggregation_pipeline",
        "warehouse_efficiency_calc", "churn_signal_pipeline", "ltv_calculation_etl",
        "ab_test_results_etl", "cohort_retention_calc", "nps_trend_pipeline",
        "brand_sentiment_etl", "competitor_monitor_pipeline", "supply_forecast_etl",
        "demand_signal_pipeline", "ops_kpi_pipeline", "sla_compliance_etl",
        "incident_response_etl", "change_log_pipeline", "capacity_planning_etl",
        "cost_allocation_pipeline", "infra_metrics_etl", "security_events_pipeline",
        "access_patterns_etl", "compliance_log_pipeline", "data_catalog_refresh",
        "lineage_scan_pipeline", "quality_score_pipeline", "governance_summary_etl",
        "ownership_audit_pipeline", "schema_health_pipeline", "job_perf_etl",
        "workspace_usage_etl", "compute_utilization_etl", "storage_usage_etl",
        "network_traffic_etl", "api_latency_etl", "query_perf_etl",
        "model_drift_monitor", "feature_importance_calc", "forecast_accuracy_etl",
        "ab_outcomes_pipeline", "journey_analytics_etl", "engagement_score_calc",
        "satisfaction_index_etl", "support_quality_etl", "incident_heatmap_etl",
        "change_impact_pipeline", "tech_debt_scan", "platform_maturity_calc",
        "mesh_health_pipeline", "catalog_completeness_etl", "schema_evolution_track",
        "query_pattern_analysis", "cost_attribution_etl", "utilization_report_pipeline",
        "cloud_spend_pipeline", "team_velocity_etl", "sprint_outcomes_pipeline",
        "okr_progress_etl", "roadmap_health_calc", "dependency_graph_etl",
        "release_quality_pipeline", "test_coverage_etl", "deployment_freq_pipeline",
        "lead_time_calc", "mttr_pipeline", "change_failure_rate_etl",
        "availability_sla_pipeline", "perf_baseline_etl", "anomaly_detection_pipeline",
        "prediction_accuracy_etl", "data_freshness_monitor", "pipeline_reliability_etl",
        "ownership_health_pipeline", "access_audit_pipeline", "workspace_score_pipeline",
        "governance_score_pipeline", "quality_index_pipeline", "etl_health_monitor",
        "ml_governance_pipeline", "feature_refresh_v2", "churn_model_retrain",
        "revenue_forecast_etl", "customer_segmentation_pipeline", "product_rec_pipeline",
        "search_ranking_etl", "recommendation_refresh", "personalization_pipeline",
        "fraud_detection_etl", "risk_scoring_pipeline", "compliance_check_pipeline",
        "data_masking_pipeline", "pii_scan_pipeline", "lineage_enrichment_pipeline",
        "catalog_tagging_pipeline", "schema_migration_etl", "delta_upgrade_pipeline",
        "partition_optimize_pipeline", "vacuum_schedule_pipeline", "compaction_pipeline",
        "checkpoint_cleanup_pipeline", "metrics_export_pipeline", "alert_routing_pipeline",
        "incident_triage_pipeline", "escalation_routing_pipeline", "oncall_handoff_pipeline",
        "runbook_sync_pipeline", "docs_refresh_pipeline", "wiki_sync_pipeline",
        "jira_sync_pipeline", "github_metrics_pipeline",
    ]
    random.shuffle(pipe_names_pool)

    # Need 31 unowned total, 9 production + unowned
    needed_unowned = 31 - unowned_count  # 28 more
    needed_prod_unowned = 9 - prod_unowned_count  # 6 more prod+unowned
    prod_unowned_added = 0
    non_prod_unowned_added = 0

    for i, pname in enumerate(pipe_names_pool[:147]):
        is_prod = (i < 57)  # first 57 are production (60 total - 3 critical = 57)
        has_owner = True

        if prod_unowned_added < needed_prod_unowned and is_prod:
            has_owner = False
            prod_unowned_added += 1
        elif (non_prod_unowned_added + prod_unowned_added) < needed_unowned and not is_prod:
            has_owner = False
            non_prod_unowned_added += 1

        owner = rand_email() if has_owner else None
        has_dq = random.random() < 0.95
        has_hardcoded = random.random() < 0.08
        status = random.choices(statuses, weights=[72,18,10])[0]
        pipe_rows.append((
            rand_id("PIPE"), pname, owner, has_owner, is_prod,
            random.choice(schedules), has_dq, has_hardcoded,
            status, str(TODAY - timedelta(days=random.randint(0,7))),
            random.randint(60, 3600), str(TODAY - timedelta(days=random.randint(30,540))) + " 00:00:00"
        ))

    cols = ["pipeline_id","pipeline_name","owner_email","has_owner_tag","is_production",
            "schedule_type","has_dq_expectations","uses_hardcoded_paths",
            "last_run_status","last_run_date","avg_duration_sec","created_at"]
    batch_insert(w, "raw_ws_pipelines", pipe_rows, cols)
    actual_no_owner = sum(1 for r in pipe_rows if not r[3])
    actual_prod_no_owner = sum(1 for r in pipe_rows if r[4] and not r[3])
    print(f"  raw_ws_pipelines: {len(pipe_rows)} rows (unowned={actual_no_owner}, prod+unowned={actual_prod_no_owner})", flush=True)

    # Build a lookup of pipeline IDs for the job runs table
    pipe_id_map = {r[1]: r[0] for r in pipe_rows}

    # ── raw_ws_jobs ───────────────────────────────────────────────────────────
    print("\n=== Creating raw_ws_jobs ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_jobs` (
        job_id STRING, job_name STRING, owner_email STRING,
        has_owner_tag BOOLEAN, schedule_cron STRING,
        cluster_type STRING, created_at TIMESTAMP
    ) USING DELTA COMMENT 'Simulated job metadata'""")

    job_rows = []
    for i in range(80):
        has_owner = random.random() > 0.18
        owner = rand_email() if has_owner else None
        cluster = "serverless" if random.random() > 0.35 else "classic"
        cron = f"0 {random.randint(0,23)} * * *" if random.random() > 0.2 else None
        job_rows.append((
            rand_id("JOB"), f"job_{i+1:03d}_{random.choice(['etl','refresh','sync','load','export'])}",
            owner, has_owner, cron, cluster,
            str(TODAY - timedelta(days=random.randint(5,400))) + " 00:00:00"
        ))
    cols = ["job_id","job_name","owner_email","has_owner_tag","schedule_cron","cluster_type","created_at"]
    batch_insert(w, "raw_ws_jobs", job_rows, cols)
    print(f"  raw_ws_jobs: {len(job_rows)} rows", flush=True)

    # ── raw_ws_job_runs ───────────────────────────────────────────────────────
    print("\n=== Creating raw_ws_job_runs ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_job_runs` (
        run_id STRING, job_id STRING, pipeline_id STRING,
        start_time TIMESTAMP, end_time TIMESTAMP,
        status STRING, duration_sec INT, triggered_by STRING
    ) USING DELTA COMMENT 'Simulated job run history'""")

    run_rows = []
    triggers = ["schedule","manual","api"]
    statuses3 = ["succeeded","failed","cancelled"]

    # Critical pipelines with 40%+ failure rates
    for pname, pinfo in CRITICAL_PIPES.items():
        pipe_id = pipe_id_map.get(pname, rand_id("PIPE"))
        job_id = rand_id("JOB")
        for _ in range(25):
            start = TODAY - timedelta(days=random.randint(0,90), hours=random.randint(0,23))
            dur = random.randint(300, 3600)
            status = "failed" if random.random() < 0.42 else "succeeded"
            run_rows.append((
                rand_id("RUN", 8), job_id, pipe_id,
                str(start), str(start + timedelta(seconds=dur)),
                status, dur, random.choice(triggers)
            ))

    # Remaining runs for other pipelines
    for _ in range(425):
        pipe_name = random.choice(list(pipe_id_map.keys()))
        pipe_id = pipe_id_map[pipe_name]
        job_id = random.choice(job_rows)[0] if random.random() < 0.7 else rand_id("JOB")
        start = TODAY - timedelta(days=random.randint(0,90), hours=random.randint(0,23))
        dur = random.randint(30, 3600)
        status = random.choices(statuses3, weights=[72,18,10])[0]
        run_rows.append((
            rand_id("RUN", 8), job_id,
            pipe_id if random.random() < 0.6 else None,
            str(start), str(start + timedelta(seconds=dur)),
            status, dur, random.choice(triggers)
        ))

    cols = ["run_id","job_id","pipeline_id","start_time","end_time","status","duration_sec","triggered_by"]
    batch_insert(w, "raw_ws_job_runs", run_rows, cols)
    print(f"  raw_ws_job_runs: {len(run_rows)} rows", flush=True)

    # ── raw_ws_audit_events ───────────────────────────────────────────────────
    print("\n=== Creating raw_ws_audit_events ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_audit_events` (
        event_id STRING, event_time TIMESTAMP, user_email STRING,
        action_type STRING, table_id STRING, table_name STRING,
        data_layer STRING, bytes_affected BIGINT, query_snippet STRING
    ) USING DELTA COMMENT 'DML audit events on bronze tables'""")

    dml_types = ["INSERT","UPDATE","DELETE","MERGE","TRUNCATE"]
    audit_rows = []
    table_id_map = {r[1]: r[0] for r in table_rows}

    for tname, edit_count, _, _, _ in BRONZE_EDITED:
        tid = table_id_map.get(tname, rand_id("TBL"))
        # Weight for raw_transactions: mostly INSERT and UPDATE
        weights = [30,12,5,5,0] if tname == "raw_transactions" else [4,3,2,2,1]
        for _ in range(edit_count):
            action = random.choices(dml_types, weights=weights)[0]
            evt_time = TODAY - timedelta(days=random.randint(0,90), hours=random.randint(0,23), minutes=random.randint(0,59))
            snippets = {
                "INSERT": f"INSERT INTO {tname} SELECT * FROM staging.{tname}_staging WHERE date = ",
                "UPDATE": f"UPDATE {tname} SET status = 'processed' WHERE id IN (SELECT id FROM tmp_",
                "DELETE": f"DELETE FROM {tname} WHERE event_date < '2024-01-01' AND status =",
                "MERGE": f"MERGE INTO {tname} USING staging.{tname}_new ON {tname}.id = staging.{tname}_new",
                "TRUNCATE": f"TRUNCATE TABLE {tname}",
            }
            audit_rows.append((
                rand_id("EVT", 8), str(evt_time), rand_email(),
                action, tid, tname, "bronze",
                random.randint(1000, 10000000),
                snippets[action][:120]
            ))

    cols = ["event_id","event_time","user_email","action_type","table_id","table_name",
            "data_layer","bytes_affected","query_snippet"]
    batch_insert(w, "raw_ws_audit_events", audit_rows, cols)
    print(f"  raw_ws_audit_events: {len(audit_rows)} rows", flush=True)

    # ── raw_ws_ml_experiments ─────────────────────────────────────────────────
    print("\n=== Creating raw_ws_ml_experiments ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_ml_experiments` (
        experiment_id STRING, experiment_name STRING, owner_email STRING,
        workspace_path STRING, last_run_date DATE, is_stale BOOLEAN,
        has_registered_model BOOLEAN, has_description BOOLEAN, created_at TIMESTAMP
    ) USING DELTA COMMENT 'ML experiment metadata'""")

    exp_names = [
        "churn_prediction_v1","churn_prediction_v2","ltv_model_exp","fraud_detection_v1",
        "recommendation_v1","recommendation_v2","demand_forecast_v1","price_optimization",
        "customer_segmentation","anomaly_detection_v1","anomaly_detection_v2","nps_prediction",
        "engagement_scoring","attribution_model_v1","attribution_model_v2","supply_chain_opt",
        "inventory_forecast","staffing_model","risk_scoring_v1","risk_scoring_v2",
        "click_prediction","conversion_model","search_ranking_ml","content_rec_model",
        "email_send_time","push_timing_model","personalization_v1","personalization_v2",
        "feature_selection_exp","hyperparameter_study","baseline_model","benchmark_exp",
        "transfer_learning_test","fine_tuning_llm","embedding_quality_test",
        "data_augmentation_exp","synthetic_data_eval","model_compression_test",
        "quantization_study","distillation_exp","ensemble_v1","stacking_model",
        "feature_engineering_v1","feature_engineering_v2","outlier_detection",
        "time_series_v1","time_series_v2","causal_inference_exp","uplift_model",
        "survival_analysis","clustering_exp_v1","clustering_exp_v2",
        "dimension_reduction","neural_net_v1","transformer_exp","gnn_experiment",
        "zero_shot_classification","few_shot_eval","prompt_tuning_v1","prompt_tuning_v2",
    ][:60]

    exp_rows = []
    for i, ename in enumerate(exp_names):
        has_owner = random.random() > 0.25
        owner = rand_email() if has_owner else None
        last_run = TODAY - timedelta(days=random.randint(1, 120))
        is_stale = last_run < TODAY - timedelta(days=30)
        has_model = random.random() > 0.4
        has_desc = random.random() > 0.35
        exp_rows.append((
            rand_id("EXP"), ename, owner,
            f"/Users/{owner or 'unknown'}/{ename}",
            str(last_run), is_stale, has_model, has_desc,
            str(TODAY - timedelta(days=random.randint(10,400))) + " 00:00:00"
        ))

    cols = ["experiment_id","experiment_name","owner_email","workspace_path","last_run_date",
            "is_stale","has_registered_model","has_description","created_at"]
    batch_insert(w, "raw_ws_ml_experiments", exp_rows, cols)
    print(f"  raw_ws_ml_experiments: {len(exp_rows)} rows", flush=True)

    # ── raw_ws_ml_models ──────────────────────────────────────────────────────
    print("\n=== Creating raw_ws_ml_models ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`raw_ws_ml_models` (
        model_id STRING, model_name STRING, serving_endpoint_name STRING,
        upstream_features_table STRING, features_table_layer STRING,
        last_training_date DATE, features_last_modified_date DATE,
        is_serving_stale_features BOOLEAN, owner_email STRING,
        registered_in_uc BOOLEAN
    ) USING DELTA COMMENT 'ML model registry metadata'""")

    model_data = [
        # 2 stale-feature models
        ("churn_risk_model_v2",    "churn_risk_endpoint_v2",     "ml_features_bronze",     "bronze", 15, 5,  True),
        ("revenue_forecast_model", "revenue_forecast_endpoint",  "ml_features_bronze",     "bronze", 20, 8,  True),
        # Well-governed models
        ("ltv_model_v3",           "ltv_scoring_endpoint",       "silver_feature_store_v1","silver", 5,  30, False),
        ("fraud_detector_v2",      "fraud_detection_endpoint",   "silver_feature_store_v2","silver", 3,  25, False),
        ("recommendation_v3",      "rec_engine_endpoint",        "silver_model_inputs",    "silver", 7,  20, False),
        ("nps_predictor_v1",       "nps_prediction_endpoint",    "gold_customer_360",      "gold",   10, 15, False),
        ("churn_model_v1",         None,                         "silver_churn_signals",   "silver", 45, 90, False),
        ("demand_forecast_v2",     "demand_endpoint",            "silver_demand_signals",  "silver", 8,  40, False),
        ("segmentation_model_v1",  None,                         "silver_customer_profile","silver", 30, 60, False),
        ("attribution_model_v2",   "attribution_endpoint",       "silver_attribution_model","silver",12, 35, False),
        ("anomaly_detector_v1",    "anomaly_endpoint",           "gold_security_posture",  "gold",   6,  20, False),
        ("price_optimizer_v1",     None,                         "silver_price_history",   "silver", 25, 50, False),
        ("engagement_scorer_v2",   "engagement_endpoint",        "silver_engagement_score","silver", 4,  18, False),
        ("risk_scorer_v1",         None,                         "silver_feature_store_v1","silver", 60, 120,False),
        ("content_rec_v1",         "content_rec_endpoint",       "gold_content_performance","gold",  9,  28, False),
        ("email_timing_v1",        "email_endpoint",             "silver_email_engagement","silver", 11, 33, False),
        ("push_timing_v2",         "push_endpoint",              "silver_push_ctr",        "silver", 7,  22, False),
        ("conversion_model_v1",    None,                         "silver_cart_abandonment","silver", 35, 70, False),
        ("search_ranker_v2",       "search_ranking_endpoint",    "silver_search_ranking",  "silver", 5,  15, False),
        ("inventory_forecast_v1",  None,                         "silver_inventory_status","silver", 20, 45, False),
        ("supply_chain_v1",        "supply_endpoint",            "silver_supply_forecast", "silver", 14, 38, False),
        ("staffing_model_v1",      None,                         "silver_hr_attendance",   "silver", 28, 55, False),
        ("clustering_model_v2",    None,                         "silver_customer_profile","silver", 40, 80, False),
        ("uplift_model_v1",        "uplift_endpoint",            "silver_ab_test_results", "silver", 18, 42, False),
        ("survival_model_v1",      None,                         "silver_ltv_signals",     "silver", 50, 100,False),
        ("time_series_v2",         "forecast_endpoint",          "silver_revenue_daily",   "silver", 8,  25, False),
        ("causal_v1",              None,                         "silver_attribution_model","silver", 22, 48, False),
        ("few_shot_classifier",    "classifier_endpoint",        "gold_catalog_completeness","gold", 6, 20, False),
        ("embedding_model_v1",     "embedding_endpoint",         "silver_feature_store_v1","silver",3,  12, False),
        ("distillation_v1",        None,                         "silver_model_inputs",    "silver", 45, 90, False),
    ][:30]

    model_rows = []
    for row in model_data:
        mname, endpoint, feat_table, feat_layer, train_days_ago, feat_days_ago, stale = row
        registered = random.random() > 0.27
        model_rows.append((
            rand_id("MDL"), mname, endpoint, feat_table, feat_layer,
            str(TODAY - timedelta(days=train_days_ago)),
            str(TODAY - timedelta(days=feat_days_ago)),
            stale, rand_email(), registered
        ))

    cols = ["model_id","model_name","serving_endpoint_name","upstream_features_table",
            "features_table_layer","last_training_date","features_last_modified_date",
            "is_serving_stale_features","owner_email","registered_in_uc"]
    batch_insert(w, "raw_ws_ml_models", model_rows, cols)
    print(f"  raw_ws_ml_models: {len(model_rows)} rows", flush=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # GOLD TABLES
    # ═══════════════════════════════════════════════════════════════════════════

    # ── gold_health_scores ────────────────────────────────────────────────────
    print("\n=== Creating gold_health_scores ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`gold_health_scores` (
        report_date DATE, dimension STRING, score INT,
        score_delta_30d INT, critical_count INT, high_count INT, medium_count INT
    ) USING DELTA COMMENT 'Daily health scores per dimension'""")

    # Target scores TODAY: overall=68, etl_hygiene=55, ml_ai_governance=62, ownership_access=71, data_quality=78
    # 30 days ago: overall=71, etl=60, ml=60, ownership=63, quality=77
    dim_config = {
        "overall":          {"today": 68, "baseline": 71, "trend": "down",     "crit": 6,  "high": 11, "med": 23},
        "etl_hygiene":      {"today": 55, "baseline": 60, "trend": "down",     "crit": 3,  "high": 4,  "med": 8},
        "ml_ai_governance": {"today": 62, "baseline": 60, "trend": "up",       "crit": 1,  "high": 3,  "med": 7},
        "ownership_access": {"today": 71, "baseline": 63, "trend": "up",       "crit": 1,  "high": 2,  "med": 5},
        "data_quality":     {"today": 78, "baseline": 77, "trend": "up",       "crit": 1,  "high": 2,  "med": 3},
    }

    score_rows = []
    for dim, cfg in dim_config.items():
        for d in range(30, -1, -1):
            rdate = TODAY - timedelta(days=d)
            frac = d / 30.0
            if d == 0:
                # Today's score must be exact — no jitter
                score = cfg["today"]
            elif cfg["trend"] == "down":
                score = round(cfg["today"] + frac * (cfg["baseline"] - cfg["today"]) + random.randint(-1,1))
            else:
                score = round(cfg["baseline"] + (1-frac) * (cfg["today"] - cfg["baseline"]) + random.randint(-1,1))
            score = max(0, min(100, score))
            score_rows.append((str(rdate), dim, score, cfg["today"] - cfg["baseline"] if d == 0 else random.randint(-2,2),
                                cfg["crit"], cfg["high"], cfg["med"]))

    cols = ["report_date","dimension","score","score_delta_30d","critical_count","high_count","medium_count"]
    batch_insert(w, "gold_health_scores", score_rows, cols)
    print(f"  gold_health_scores: {len(score_rows)} rows", flush=True)

    # ── gold_bronze_table_edits ───────────────────────────────────────────────
    print("\n=== Creating gold_bronze_table_edits ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`gold_bronze_table_edits` (
        table_name STRING, catalog_schema STRING,
        edit_count_90d INT, last_editor_email STRING,
        last_edit_date DATE, last_action_type STRING,
        downstream_gold_table_count INT, downstream_gold_tables STRING,
        estimated_rerun_cost_usd DECIMAL(10,2), severity STRING
    ) USING DELTA COMMENT '14 bronze tables with direct DML — the ETL hygiene finding'""")

    gold_downstream = {
        "raw_transactions":       (3, "gold_revenue_summary,gold_executive_kpis,gold_customer_360"),
        "ml_features_bronze":     (2, "gold_ml_model_registry,gold_feature_importance"),
        "customer_events_bronze": (2, "gold_executive_kpis,gold_customer_360"),
        "raw_user_sessions":      (1, "gold_customer_journey"),
        "raw_click_events":       (1, "gold_funnel_conversion"),
        "raw_product_catalog":    (1, "gold_product_performance"),
        "raw_payments_bronze":    (1, "gold_revenue_summary"),
        "raw_shipping_events":    (0, ""),
        "raw_inventory_bronze":   (1, "gold_ops_dashboard"),
        "raw_ad_impressions":     (0, ""),
        "raw_support_tickets":    (0, ""),
        "raw_search_queries":     (0, ""),
        "raw_device_events":      (0, ""),
        "raw_geo_events":         (0, ""),
    }

    edit_rows = []
    for tname, edit_count, ds_count, cost, sev in BRONZE_EDITED:
        ds_cnt, ds_tables = gold_downstream.get(tname, (0, ""))
        last_edit = TODAY - timedelta(days=random.randint(0, 10))
        action = random.choice(["INSERT","UPDATE","MERGE"])
        edit_rows.append((
            tname, f"{CATALOG}.{SCHEMA}",
            edit_count, rand_email(), str(last_edit), action,
            ds_cnt, ds_tables if ds_tables else None,
            cost, sev
        ))

    cols = ["table_name","catalog_schema","edit_count_90d","last_editor_email",
            "last_edit_date","last_action_type","downstream_gold_table_count",
            "downstream_gold_tables","estimated_rerun_cost_usd","severity"]
    batch_insert(w, "gold_bronze_table_edits", edit_rows, cols)
    total_cost = sum(r[8] for r in edit_rows)
    print(f"  gold_bronze_table_edits: {len(edit_rows)} rows, total_cost=${total_cost:,.0f}", flush=True)

    # ── gold_pipeline_health ──────────────────────────────────────────────────
    print("\n=== Creating gold_pipeline_health ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`gold_pipeline_health` AS
        SELECT
            p.pipeline_id, p.pipeline_name, p.owner_email, p.has_owner_tag,
            p.is_production, p.has_dq_expectations, p.uses_hardcoded_paths,
            COALESCE(r.failure_rate_30d, 0.0) AS failure_rate_30d,
            p.avg_duration_sec,
            CAST(
                (CASE WHEN NOT p.has_owner_tag THEN 1 ELSE 0 END +
                 CASE WHEN NOT p.has_dq_expectations THEN 1 ELSE 0 END +
                 CASE WHEN p.uses_hardcoded_paths THEN 1 ELSE 0 END)
            AS INT) AS anti_pattern_count,
            CASE
                WHEN COALESCE(r.failure_rate_30d, 0.0) > 0.35 OR
                     (NOT p.has_owner_tag AND p.is_production) THEN 'critical'
                WHEN COALESCE(r.failure_rate_30d, 0.0) > 0.15 OR
                     NOT p.has_dq_expectations THEN 'warning'
                ELSE 'healthy'
            END AS health_status
        FROM `{CATALOG}`.`{SCHEMA}`.`raw_ws_pipelines` p
        LEFT JOIN (
            SELECT pipeline_id,
                   CAST(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS DOUBLE) /
                   NULLIF(COUNT(*), 0) AS failure_rate_30d
            FROM `{CATALOG}`.`{SCHEMA}`.`raw_ws_job_runs`
            WHERE pipeline_id IS NOT NULL
              AND start_time >= CURRENT_TIMESTAMP - INTERVAL 30 DAYS
            GROUP BY pipeline_id
        ) r ON p.pipeline_id = r.pipeline_id
    """)
    print("  gold_pipeline_health: CTAS complete", flush=True)

    # ── gold_ownership_trend ──────────────────────────────────────────────────
    print("\n=== Creating gold_ownership_trend ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`gold_ownership_trend` (
        report_date DATE, total_production_pipelines INT,
        owned_production_pipelines INT, ownership_coverage_pct DECIMAL(5,2),
        goal_pct DECIMAL(5,2)
    ) USING DELTA COMMENT 'Daily ownership coverage trend'""")

    # 58% -> 69% over 30 days with slight noise
    trend_rows = []
    for d in range(30, -1, -1):
        rdate = TODAY - timedelta(days=d)
        frac = (30 - d) / 30.0
        coverage = 58.0 + frac * 11.0 + random.uniform(-0.5, 0.5)
        coverage = round(max(55, min(72, coverage)), 2)
        total = 60
        owned = round(total * coverage / 100)
        trend_rows.append((str(rdate), total, owned, coverage, 95.00))

    cols = ["report_date","total_production_pipelines","owned_production_pipelines",
            "ownership_coverage_pct","goal_pct"]
    batch_insert(w, "gold_ownership_trend", trend_rows, cols)
    print(f"  gold_ownership_trend: {len(trend_rows)} rows", flush=True)

    # ── gold_remediation_backlog ──────────────────────────────────────────────
    print("\n=== Creating gold_remediation_backlog ===", flush=True)
    sql(w, f"""CREATE TABLE {fq}.`gold_remediation_backlog` (
        finding_id STRING, severity STRING, category STRING,
        asset_type STRING, asset_name STRING, owner_email STRING,
        description STRING, business_impact_usd DECIMAL(10,2),
        recommended_action STRING, detected_at DATE, sprint_estimate_days INT
    ) USING DELTA COMMENT 'Ranked remediation backlog — 6 critical, 11 high, 23 medium'""")

    backlog_rows = []
    # 6 critical — insert detected_at between recommended_action (idx 8) and sprint_estimate_days (idx 9)
    for row in CRITICAL_FINDINGS:
        detected = str(TODAY - timedelta(days=random.randint(1, 30)))
        backlog_rows.append(row[:9] + (detected,) + row[9:])

    # 11 high
    pipe_names_for_findings = [r[1] for r in pipe_rows if not r[3]]  # unowned
    exp_names_for_findings  = [r[1] for r in exp_rows  if r[5]]      # stale
    model_names_for_findings = [r[1] for r in model_rows if not r[9]] # not registered
    random.shuffle(pipe_names_for_findings)
    random.shuffle(exp_names_for_findings)
    random.shuffle(model_names_for_findings)

    HIGH_ASSET_NAMES = (
        pipe_names_for_findings[:7] +
        exp_names_for_findings[:3] +
        model_names_for_findings[:1]
    )

    for i, (cat, atype, desc, action, effort) in enumerate(HIGH_FINDINGS_TEMPLATES[:11]):
        asset = HIGH_ASSET_NAMES[i] if i < len(HIGH_ASSET_NAMES) else f"asset_{i}"
        impact = round(random.uniform(3000, 8000), 2)
        owner = rand_email() if random.random() > 0.4 else None
        backlog_rows.append((
            f"FND-{1000+i:06d}", "high", cat, atype, asset, owner,
            desc, impact, action, str(TODAY - timedelta(days=random.randint(1,30))), effort
        ))

    # 23 medium
    table_names_for_med = [r[1] for r in table_rows if r[10]] + \
                           [r[1] for r in table_rows if r[4]=="bronze" and r[9] is None]
    random.shuffle(table_names_for_med)
    job_names_for_med = [r[1] for r in job_rows if r[5] == "classic"]

    med_assets = table_names_for_med[:20] + job_names_for_med[:3]
    random.shuffle(med_assets)

    for i, (cat, atype, desc, action, effort) in enumerate(MEDIUM_FINDINGS_TEMPLATES[:23]):
        asset = med_assets[i] if i < len(med_assets) else f"table_{i}"
        impact = round(random.uniform(500, 3000), 2)
        owner = rand_email() if random.random() > 0.3 else None
        backlog_rows.append((
            f"FND-{2000+i:06d}", "medium", cat, atype, asset, owner,
            desc, impact, action, str(TODAY - timedelta(days=random.randint(1,60))), effort
        ))

    cols = ["finding_id","severity","category","asset_type","asset_name","owner_email",
            "description","business_impact_usd","recommended_action","detected_at","sprint_estimate_days"]
    batch_insert(w, "gold_remediation_backlog", backlog_rows, cols)
    crit = sum(1 for r in backlog_rows if r[1] == "critical")
    high = sum(1 for r in backlog_rows if r[1] == "high")
    med  = sum(1 for r in backlog_rows if r[1] == "medium")
    print(f"  gold_remediation_backlog: {len(backlog_rows)} rows (crit={crit}, high={high}, med={med})", flush=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n=== Running validation queries ===", flush=True)
    checks = [
        (f"SELECT COUNT(*) as n FROM {fq}.`gold_bronze_table_edits`", "gold_bronze_table_edits rows", 14),
        (f"SELECT edit_count_90d FROM {fq}.`gold_bronze_table_edits` WHERE table_name = 'raw_transactions'", "raw_transactions edit_count", 47),
        (f"SELECT CAST(SUM(estimated_rerun_cost_usd) AS BIGINT) FROM {fq}.`gold_bronze_table_edits`", "total rerun cost (USD)", None),
        (f"SELECT COUNT(*) FROM {fq}.`gold_remediation_backlog` WHERE severity = 'critical'", "critical findings", 6),
        (f"SELECT COUNT(*) FROM {fq}.`gold_remediation_backlog` WHERE severity = 'high'", "high findings", 11),
        (f"SELECT COUNT(*) FROM {fq}.`gold_remediation_backlog` WHERE severity = 'medium'", "medium findings", 23),
        (f"SELECT score FROM {fq}.`gold_health_scores` WHERE report_date = CURRENT_DATE AND dimension = 'overall'", "overall score", 68),
        (f"SELECT score FROM {fq}.`gold_health_scores` WHERE report_date = CURRENT_DATE AND dimension = 'etl_hygiene'", "etl_hygiene score", 55),
        (f"SELECT COUNT(*) FROM {fq}.`raw_ws_ml_models` WHERE is_serving_stale_features = TRUE", "stale feature models", 2),
        (f"SELECT COUNT(*) FROM {fq}.`raw_ws_pipelines` WHERE has_owner_tag = FALSE", "pipelines without owner", 31),
        (f"SELECT COUNT(*) FROM {fq}.`raw_ws_pipelines` WHERE has_owner_tag = FALSE AND is_production = TRUE", "prod pipelines without owner", 9),
    ]

    all_passed = True
    for stmt, label, expected in checks:
        try:
            r = sql(w, stmt)
            val = None
            if r.result and r.result.data_array:
                val = r.result.data_array[0][0]
                val = int(val) if val is not None else None
            status = "✓" if (expected is None or val == expected) else "✗"
            if expected is not None and val != expected:
                all_passed = False
            print(f"  {status} {label}: {val} (expected: {expected or 'any'})", flush=True)
        except Exception as e:
            print(f"  ✗ {label}: ERROR — {e}", flush=True)
            all_passed = False

    print(f"\n{'✅ All checks passed!' if all_passed else '⚠️  Some checks failed — review above'}", flush=True)
    print("\n=== Data generation complete ===", flush=True)
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
