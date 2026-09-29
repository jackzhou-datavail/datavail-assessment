"""The 51 adoption checks, as data.

Ported from the `Adoption Baseline Checks` notebook. Each check measures
whether a capability is *used at all*, not how well - that is
`datavail_assessment.conformance`.

Every check is a scalar query returning one column. The value is scored
0 / 1 / 2 against two thresholds:

    value >= active   -> 2  ACTIVE
    value >= minimal  -> 1  MINIMAL
    otherwise         -> 0  NONE

`{DAYS_30}` and `{DAYS_90}` are substituted with ISO dates before
execution.

A few checks need more than one query or a rule that two thresholds
cannot express; those declare `combine`, a function over the named
sub-queries. See COMPOUND_CHECKS.
"""

from __future__ import annotations

SECTIONS = {
    "Workspace": {"max": 20, "weight": 0.30},
    "SQL": {"max": 24, "weight": 0.20},
    "Data Engineering": {"max": 28, "weight": 0.30},
    "AI/ML": {"max": 30, "weight": 0.20},
}

# id -> section, name, sql, minimal, active
CHECKS: dict[str, dict] = {}


def check(cid, section, name, sql, minimal, active, pct=False):
    CHECKS[cid] = {"section": section, "name": name, "sql": sql.strip(),
                   "minimal": minimal, "active": active, "pct": pct}


# --- Workspace -----------------------------------------------------

check(
    "1.1", "Workspace", "Active users (30d)",
    """
    SELECT COUNT(DISTINCT user_identity.email)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND user_identity.email IS NOT NULL
        AND user_identity.email NOT LIKE '%databricks.com'
    """,
    minimal=1.0, active=6.0,
)

check(
    "1.2", "Workspace", "Users executing code (30d)",
    """
    SELECT COUNT(DISTINCT user_identity.email)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND action_name IN ('runCommand', 'submitRun')
        AND user_identity.email IS NOT NULL
    """,
    minimal=1.0, active=4.0,
)

check(
    "1.3", "Workspace", "Notebooks created/modified (30d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND service_name = 'notebook'
        AND action_name IN ('create', 'update')
    """,
    minimal=1.0, active=11.0,
)

check(
    "1.4", "Workspace", "Git/Repos actions (30d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND service_name = 'repos'
    """,
    minimal=1.0, active=6.0,
)

check(
    "1.5", "Workspace", "All-purpose compute DBUs (30d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_start_time >= '{DAYS_30}'
        AND sku_name LIKE '%ALL_PURPOSE%'
    """,
    minimal=1.0, active=100.0,
)

check(
    "1.7", "Workspace", "Workspace files created (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'workspace'
        AND action_name IN ('create', 'import')
        AND request_params.path LIKE '%.py'
           OR request_params.path LIKE '%.sql'
           OR request_params.path LIKE '%.yaml'
           OR request_params.path LIKE '%.yml'
    """,
    minimal=1.0, active=11.0,
)

check(
    "1.8", "Workspace", "Secret/token events (30d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND service_name IN ('secrets', 'tokens')
    """,
    minimal=1.0, active=6.0,
)

check(
    "1.9", "Workspace", "Marketplace listings consumed",
    """
    SELECT COUNT(DISTINCT request_params.listing_id)
      FROM system.access.audit
      WHERE service_name = 'marketplace'
        AND action_name LIKE '%install%'
    """,
    minimal=1.0, active=2.0,
)

# --- SQL -----------------------------------------------------------

check(
    "2.1", "SQL", "SQL warehouses provisioned",
    """
    SELECT COUNT(DISTINCT warehouse_id)
      FROM system.compute.warehouses
      WHERE delete_time IS NULL
    """,
    minimal=1.0, active=2.0,
)

check(
    "2.2", "SQL", "SQL warehouse DBUs (30d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_start_time >= '{DAYS_30}'
        AND sku_name LIKE '%SQL%'
        AND usage_metadata.warehouse_id IS NOT NULL
    """,
    minimal=1.0, active=100.0,
)

check(
    "2.3", "SQL", "Total queries executed (30d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= '{DAYS_30}'
    """,
    minimal=1.0, active=500.0,
)

check(
    "2.4", "SQL", "Distinct query users (30d)",
    """
    SELECT COUNT(DISTINCT executed_by)
      FROM system.query.history
      WHERE start_time >= '{DAYS_30}'
    """,
    minimal=1.0, active=4.0,
)

check(
    "2.5", "SQL", "Lakeview dashboards created (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'dashboards'
        AND action_name = 'create'
    """,
    minimal=1.0, active=4.0,
)

check(
    "2.6", "SQL", "Saved queries created (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'databrickssql'
        AND action_name = 'createQuery'
    """,
    minimal=1.0, active=11.0,
)

check(
    "2.7", "SQL", "SQL alerts configured (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'databrickssql'
        AND action_name LIKE '%Alert%'
    """,
    minimal=1.0, active=3.0,
)

check(
    "2.8", "SQL", "Genie space activity (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND action_name LIKE '%Genie%'
    """,
    minimal=1.0, active=2.0,
)

check(
    "2.9", "SQL", "Distinct query statement types (30d)",
    """
    SELECT COUNT(DISTINCT statement_type)
      FROM system.query.history
      WHERE start_time >= '{DAYS_30}'
        AND statement_type IS NOT NULL
    """,
    minimal=2.0, active=3.0,
)

check(
    "2.10", "SQL", "MVs and streaming tables",
    """
    SELECT COUNT(*)
      FROM system.information_schema.tables
      WHERE table_type IN ('MATERIALIZED_VIEW', 'STREAMING_TABLE')
        AND table_catalog NOT IN ('system', 'samples')
    """,
    minimal=1.0, active=3.0,
)

check(
    "2.11", "SQL", "Federated/foreign tables",
    """
    SELECT COUNT(*)
      FROM system.information_schema.tables
      WHERE table_type = 'FOREIGN'
        AND table_catalog NOT IN ('system', 'samples')
    """,
    minimal=1.0, active=3.0,
)

check(
    "2.12", "SQL", "Dashboards actively updated (90d)",
    """
    SELECT COUNT(DISTINCT request_params.dashboard_id)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'dashboards'
        AND action_name = 'update'
    """,
    minimal=1.0, active=2.0,
)

# --- Data Engineering ----------------------------------------------

check(
    "3.1", "Data Engineering", "Jobs defined",
    """
    SELECT COUNT(DISTINCT job_id)
      FROM system.lakeflow.jobs
      WHERE delete_time IS NULL
    """,
    minimal=1.0, active=6.0,
)

check(
    "3.2", "Data Engineering", "Job runs (30d)",
    """
    SELECT COUNT(*)
      FROM system.lakeflow.job_run_timeline
      WHERE period_start_time >= '{DAYS_30}'
    """,
    minimal=1.0, active=21.0,
)

check(
    "3.4", "Data Engineering", "Multi-task jobs",
    """
    SELECT COUNT(DISTINCT job_id)
      FROM (
        SELECT job_id, COUNT(DISTINCT task_key) AS n_tasks
        FROM system.lakeflow.job_tasks
        GROUP BY job_id
        HAVING n_tasks > 1
      )
    """,
    minimal=1.0, active=3.0,
)

check(
    "3.5", "Data Engineering", "SDP pipelines created",
    """
    SELECT COUNT(DISTINCT request_params.pipeline_id)
      FROM system.access.audit
      WHERE service_name = 'deltaPipelines'
        AND action_name = 'create'
    """,
    minimal=1.0, active=2.0,
)

check(
    "3.6", "Data Engineering", "SDP pipeline updates (30d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND service_name = 'deltaPipelines'
        AND action_name = 'update'
    """,
    minimal=1.0, active=11.0,
)

check(
    "3.7", "Data Engineering", "Streaming DBUs (30d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_start_time >= '{DAYS_30}'
        AND sku_name LIKE '%STREAMING%'
    """,
    minimal=1.0, active=10.0,
)

check(
    "3.8", "Data Engineering", "Delta write ops (30d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= '{DAYS_30}'
        AND statement_type IN ('MERGE', 'UPDATE', 'DELETE')
    """,
    minimal=1.0, active=50.0,
)

check(
    "3.9", "Data Engineering", "Tables modified recently (90d)",
    """
    SELECT COUNT(*)
      FROM system.information_schema.tables
      WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        AND table_schema != 'information_schema'
        AND last_altered IS NOT NULL
        AND last_altered >= '{DAYS_90}'
    """,
    minimal=1.0, active=11.0,
)

check(
    "3.11", "Data Engineering", "Distinct trigger types",
    """
    SELECT COUNT(DISTINCT trigger_type)
      FROM system.lakeflow.jobs
      WHERE delete_time IS NULL
        AND trigger_type IS NOT NULL
    """,
    minimal=1.0, active=3.0,
)

check(
    "3.12", "Data Engineering", "Jobs compute DBUs (30d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_start_time >= '{DAYS_30}'
        AND (sku_name LIKE '%JOBS%' OR sku_name LIKE '%WORKFLOW%')
    """,
    minimal=1.0, active=200.0,
)

check(
    "3.13", "Data Engineering", "Auto Loader / Connect events (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND (action_name LIKE '%autoLoader%' OR action_name LIKE '%cloudFiles%'
             OR service_name = 'ingestion')
    """,
    minimal=1.0, active=5.0,
)

check(
    "3.14", "Data Engineering", "Jobs with notifications",
    """
    SELECT COUNT(DISTINCT request_params.job_id)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_90}'
        AND service_name = 'jobs'
        AND action_name IN ('create', 'resetJob', 'update')
        AND request_params.notification_settings IS NOT NULL
    """,
    minimal=1.0, active=3.0,
)

# --- AI/ML ---------------------------------------------------------

check(
    "4.1", "AI/ML", "MLflow experiments created",
    """
    SELECT COUNT(DISTINCT request_params.experiment_id)
      FROM system.access.audit
      WHERE service_name = 'mlflow'
        AND action_name = 'createExperiment'
    """,
    minimal=1.0, active=4.0,
)

check(
    "4.2", "AI/ML", "MLflow runs logged (30d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= '{DAYS_30}'
        AND service_name = 'mlflow'
        AND action_name = 'createRun'
    """,
    minimal=1.0, active=11.0,
)

check(
    "4.3", "AI/ML", "Models registered in UC",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE service_name = 'unityCatalog'
        AND action_name LIKE '%RegisteredModel%'
        AND action_name LIKE '%create%'
    """,
    minimal=1.0, active=3.0,
)

check(
    "4.4", "AI/ML", "Model versions created",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE service_name = 'unityCatalog'
        AND action_name LIKE '%ModelVersion%'
        AND action_name LIKE '%create%'
    """,
    minimal=1.0, active=4.0,
)

check(
    "4.5", "AI/ML", "Serving endpoints provisioned",
    """
    SELECT COUNT(DISTINCT endpoint_name)
      FROM system.serving.served_entities
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.6", "AI/ML", "Serving requests (30d)",
    """
    SELECT COUNT(*)
      FROM system.serving.endpoint_usage
      WHERE request_time >= '{DAYS_30}'
    """,
    minimal=1.0, active=100.0,
)

check(
    "4.7", "AI/ML", "AI Gateway endpoints active (90d)",
    """
    SELECT COUNT(DISTINCT endpoint_name)
      FROM system.ai_gateway.usage
      WHERE event_time >= '{DAYS_90}'
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.8", "AI/ML", "AI Gateway requests (30d)",
    """
    SELECT COUNT(*)
      FROM system.ai_gateway.usage
      WHERE event_time >= '{DAYS_30}'
    """,
    minimal=1.0, active=1000.0,
)

check(
    "4.9", "AI/ML", "Distinct models via Gateway (90d)",
    """
    SELECT COUNT(DISTINCT destination_model)
      FROM system.ai_gateway.usage
      WHERE event_time >= '{DAYS_90}'
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.10", "AI/ML", "Feature Store activity",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE service_name = 'featureStore'
    """,
    minimal=1.0, active=3.0,
)

check(
    "4.11", "AI/ML", "Vector search indexes created",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE service_name = 'vectorSearch'
        AND action_name LIKE '%create%'
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.12", "AI/ML", "Agent Bricks / AI function activity",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE action_name LIKE '%AgentBrick%'
         OR action_name LIKE '%agentTile%'
         OR (service_name = 'aiFunction' AND action_name LIKE '%create%')
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.13", "AI/ML", "Serving endpoints with entities",
    """
    SELECT COUNT(DISTINCT endpoint_name)
      FROM system.serving.served_entities
      WHERE entity_name IS NOT NULL
    """,
    minimal=1.0, active=2.0,
)

check(
    "4.14", "AI/ML", "AI SQL function queries (30d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= '{DAYS_30}'
        AND (LOWER(statement_text) LIKE '%ai_query%'
          OR LOWER(statement_text) LIKE '%ai_forecast%'
          OR LOWER(statement_text) LIKE '%ai_classify%'
          OR LOWER(statement_text) LIKE '%ai_extract%'
          OR LOWER(statement_text) LIKE '%ai_generate%'
          OR LOWER(statement_text) LIKE '%ai_similarity%')
    """,
    minimal=1.0, active=6.0,
)

check(
    "4.15", "AI/ML", "GPU/ML compute DBUs (30d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_start_time >= '{DAYS_30}'
        AND (sku_name LIKE '%GPU%' OR sku_name LIKE '%ML%')
    """,
    minimal=1.0, active=50.0,
)


# ---------------------------------------------------------------------
# Compound checks
#
# Four checks cannot be expressed as one query plus two thresholds. Each
# declares its sub-queries and a `combine` that returns (value, score,
# detail), preserving the notebook's original rules exactly.
# ---------------------------------------------------------------------

COMPOUND_CHECKS: dict[str, dict] = {}


def compound(cid, section, name, queries, combine):
    COMPOUND_CHECKS[cid] = {"section": section, "name": name,
                            "queries": queries, "combine": combine}


def _uc_objects(v):
    """1.6 - breadth matters as well as volume: many tables spread over
    at least two catalogs is ACTIVE; anything at all is MINIMAL."""
    tables, catalogs = v["tables"], v["catalogs"]
    score = 2 if (tables > 20 and catalogs >= 2) else (1 if tables >= 1 else 0)
    return tables, score, f"{catalogs} catalogs"


def _cluster_policies(v):
    """1.10 - share of recent UI-created clusters made under a policy."""
    total, governed = v["total"], v["governed"]
    pct = (governed / total * 100) if total else 0.0
    score = 2 if (total > 0 and pct > 50) else (1 if governed >= 1 else 0)
    return governed, score, f"{pct:.0f}% of {total} clusters"


def _completed_runs(v):
    """3.3 - total completed job runs, successes and failures together."""
    success, failed = v["success"], v["failed"]
    total = success + failed
    score = 2 if total >= 50 else (1 if total >= 1 else 0)
    return total, score, f"{success} success, {failed} failed"


def _scheduled_jobs(v):
    """3.10 - share of live jobs carrying a schedule trigger."""
    total, scheduled = v["total"], v["scheduled"]
    pct = (scheduled / total * 100) if total else 0.0
    score = 2 if pct > 50 else (1 if scheduled >= 1 else 0)
    return scheduled, score, f"{pct:.0f}% of {total} jobs"


compound(
    "1.6", "Workspace", "UC objects (tables/catalogs)",
    {
        "tables": """
            SELECT COUNT(*)
            FROM system.information_schema.tables
            WHERE table_schema != 'information_schema'
              AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        """,
        "catalogs": """
            SELECT COUNT(DISTINCT table_catalog)
            FROM system.information_schema.tables
            WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        """,
    },
    _uc_objects,
)

compound(
    "1.10", "Workspace", "Cluster policies in use",
    {
        "total": """
            SELECT COUNT(*) FROM system.compute.clusters
            WHERE change_time >= '{DAYS_90}'
        """,
        "governed": """
            SELECT COUNT(*) FROM system.compute.clusters
            WHERE change_time >= '{DAYS_90}'
              AND cluster_source = 'UI' AND policy_id IS NOT NULL
        """,
    },
    _cluster_policies,
)

compound(
    "3.3", "Data Engineering", "Completed runs (30d)",
    {
        "success": """
            SELECT COUNT(*)
            FROM system.lakeflow.job_run_timeline
            WHERE period_start_time >= '{DAYS_30}'
              AND result_state = 'SUCCESS'
        """,
        "failed": """
            SELECT COUNT(*)
            FROM system.lakeflow.job_run_timeline
            WHERE period_start_time >= '{DAYS_30}'
              AND result_state IN ('FAILED', 'TIMEDOUT')
        """,
    },
    _completed_runs,
)

compound(
    "3.10", "Data Engineering", "Scheduled jobs",
    {
        "scheduled": """
            SELECT COUNT(DISTINCT job_id)
            FROM system.lakeflow.jobs
            WHERE delete_time IS NULL
              AND trigger.schedule IS NOT NULL
        """,
        "total": """
            SELECT COUNT(DISTINCT job_id)
            FROM system.lakeflow.jobs
            WHERE delete_time IS NULL
        """,
    },
    _scheduled_jobs,
)
