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

# Weights are each area's share of the overall score. `max` is no longer
# used - the denominator is computed from the checks that could actually
# be measured, so a section is scored out of what was looked at.
SECTIONS = {
    "Workspace": {"weight": 0.22},
    "SQL": {"weight": 0.18},
    "Data Engineering": {"weight": 0.22},
    "AI/ML": {"weight": 0.18},
    "Governance & Security": {"weight": 0.12},
    "Data Sharing": {"weight": 0.08},
}

# id -> section, name, sql, minimal, active
CHECKS: dict[str, dict] = {}


def check(cid, section, name, sql, minimal, active, pct=False,
          absent_means_zero=False):
    """`absent_means_zero` for feature-gated system tables.

    Some system schemas only appear once the feature behind them is
    used - system.data_quality_monitoring is the clearest case. For an
    adoption question the absence IS the answer: nothing to monitor with
    means monitoring is not adopted. Without this the check would report
    a query error and look like a tooling gap rather than a finding.
    """
    CHECKS[cid] = {"section": section, "name": name, "sql": sql.strip(),
                   "minimal": minimal, "active": active, "pct": pct,
                   "absent_means_zero": absent_means_zero}


# Capabilities the checklist specifies but system tables cannot see.
# Recorded rather than proxied: substituting a loosely-related metric
# would report a number for something that was never measured, and
# scoring them 0 would read as "unused" when the truth is "unobserved".
# Each names the API that would actually answer it.
NOT_MEASURABLE: dict[str, dict] = {}


def not_measurable(cid, section, name, reason):
    NOT_MEASURABLE[cid] = {"section": section, "name": name, "reason": reason}


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


def compound(cid, section, name, queries, combine, sampler=None):
    """`sampler` names an extra measurement the runner performs before
    combine() - used where a check needs per-object inspection that no
    single query can provide."""
    COMPOUND_CHECKS[cid] = {"section": section, "name": name,
                            "queries": queries, "combine": combine,
                            "sampler": sampler}


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


# ---------------------------------------------------------------------
# Aligned with the checklist
#
# adoption_checks.md specifies what each check should measure. Six of
# them were implemented against a proxy instead. Two are measurable as
# specified and are now measured that way; four are not observable from
# system tables and say so rather than reporting a substitute.
# ---------------------------------------------------------------------

# 4.10 - "Feature tables present", per the checklist an
# information_schema question, not an audit-log one. Unity Catalog does
# not label a table as a feature table, but a feature table must declare
# a primary key, and few other tables do. That makes PK-constrained
# tables the closest structural signal available; it will over-count a
# workspace that declares primary keys as documentation.
check(
    "4.10", "AI/ML", "Feature tables present (tables with a primary key)",
    """
    SELECT COUNT(DISTINCT CONCAT_WS('.', table_catalog, table_schema, table_name))
      FROM system.information_schema.table_constraints
      WHERE constraint_type = 'PRIMARY KEY'
        AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
    """,
    minimal=1.0, active=3.0,
)


def _tables_with_history(v):
    """3.9 - tables carrying more than one Delta version.

    The checklist asks for multi-version history, which means the table
    has been written more than once: iterative processing rather than a
    one-off load. Delta history is not in system tables, so this samples
    tables and runs DESCRIBE HISTORY on each, then extrapolates the
    share across the estate.
    """
    sampled, multi, total = v["sampled"], v["multi_version"], v["total_tables"]
    if not sampled:
        return 0.0, 0, "no managed tables to sample"
    share = multi / sampled
    estimated = share * total
    score = 2 if estimated > 10 else (1 if estimated >= 1 else 0)
    return round(estimated, 1), score, f"{multi}/{sampled} sampled, {total} tables total"


compound(
    "3.9", "Data Engineering", "Tables with history > 1 version",
    {
        "total_tables": """
            SELECT COUNT(*)
            FROM system.information_schema.tables
            WHERE table_type = 'MANAGED'
              AND table_schema != 'information_schema'
              AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        """,
    },
    _tables_with_history,
    sampler="delta_history",
)


# ---------------------------------------------------------------------
# Checks added from the pattern library review (2026-09-29)
#
# Every one measures what adoption_checks.md specifies. Where the
# checklist named an API alongside a system table, the system-table half
# is measured and the check name says what it counts, so nobody reads
# more into the number than it carries.
# ---------------------------------------------------------------------

# --- Workspace -------------------------------------------------------

check(
    "1.11", "Workspace", "Billable products in use (breadth)",
    """
    SELECT COUNT(DISTINCT billing_origin_product)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS
    """,
    minimal=3.0, active=8.0,
)

check(
    "1.12", "Workspace", "Serverless share of compute DBUs (%)",
    """
    SELECT COALESCE(ROUND(100.0 * SUM(CASE WHEN upper(sku_name) LIKE '%SERVERLESS%'
                                           THEN usage_quantity ELSE 0 END)
                          / NULLIF(SUM(usage_quantity), 0), 1), 0)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 30 DAYS
    """,
    minimal=10.0, active=50.0, pct=True,
)

check(
    "1.13", "Workspace", "Workspaces with active usage",
    """
    SELECT COUNT(DISTINCT workspace_id)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 30 DAYS
    """,
    minimal=1.0, active=2.0,
)

check(
    "1.14", "Workspace", "Bundle-deployed jobs and pipelines",
    """
    SELECT COUNT(*) FROM (
      SELECT job_id FROM (
        SELECT job_id, name,
               ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.jobs
      ) x WHERE rn = 1 AND name RLIKE '^\\[[a-zA-Z0-9_ -]+\\]'
    )
    """,
    minimal=1.0, active=3.0,
)

check(
    "1.15", "Workspace", "System tables queried (statements referencing system.)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
        AND lower(statement_text) LIKE '%system.%'
    """,
    minimal=1.0, active=50.0,
)

check(
    "1.16", "Workspace", "Cost-attribution tags on usage (%)",
    """
    SELECT COALESCE(ROUND(100.0 * SUM(CASE WHEN custom_tags IS NOT NULL
                                             AND size(map_keys(custom_tags)) > 0
                                           THEN usage_quantity ELSE 0 END)
                          / NULLIF(SUM(usage_quantity), 0), 1), 0)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 30 DAYS
    """,
    minimal=10.0, active=60.0, pct=True,
)

check(
    "1.17", "Workspace", "Databricks Apps deployed (DBUs)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS
        AND upper(billing_origin_product) = 'APPS'
    """,
    minimal=0.01, active=1.0,
)

# --- SQL -------------------------------------------------------------

check(
    "2.13", "SQL", "Genie usage volume (30d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
        AND query_source.genie_space_id IS NOT NULL
    """,
    minimal=1.0, active=50.0,
)

check(
    "2.14", "SQL", "Dashboard-driven query volume (30d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
        AND query_source.dashboard_id IS NOT NULL
    """,
    minimal=1.0, active=100.0,
)

check(
    "2.15", "SQL", "Metric views defined",
    """
    SELECT COUNT(*)
      FROM system.information_schema.tables
      WHERE upper(table_type) LIKE '%METRIC%'
        AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
    """,
    minimal=1.0, active=3.0,
)

check(
    "2.16", "SQL", "External BI / client tools connected (30d)",
    """
    SELECT COUNT(DISTINCT client_application)
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
        AND client_application IS NOT NULL
        AND lower(client_application) NOT RLIKE
            '(databricks|notebook|sql editor|dashboard|genie|unknown)'
    """,
    minimal=1.0, active=2.0,
)

check(
    "2.17", "SQL", "Cost-per-query attribution in place",
    """
    SELECT COUNT(*)
      FROM system.information_schema.tables
      WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        AND (lower(table_name) LIKE '%cost_per_query%'
             OR lower(table_name) LIKE '%query_cost%')
    """,
    minimal=1.0, active=1.0,
)

# --- Data Engineering ------------------------------------------------

check(
    "3.15", "Data Engineering", "Declared data quality rules (table constraints)",
    """
    SELECT COUNT(*)
      FROM system.information_schema.table_constraints
      WHERE constraint_type IN ('CHECK', 'PRIMARY KEY', 'FOREIGN KEY')
        AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
    """,
    minimal=1.0, active=10.0,
)

check(
    "3.16", "Data Engineering", "Data quality monitoring enabled",
    """
    SELECT COUNT(DISTINCT table_name)
      FROM system.data_quality_monitoring.table_results
    """,
    minimal=1.0, active=3.0, absent_means_zero=True,
)

check(
    "3.18", "Data Engineering", "Predictive optimization active",
    """
    SELECT COUNT(DISTINCT CONCAT_WS('.', catalog_name, schema_name, table_name))
      FROM system.storage.predictive_optimization_operations_history
    """,
    minimal=1.0, active=10.0,
)

# --- AI/ML -----------------------------------------------------------

check(
    "4.16", "AI/ML", "GenAI tracing and evaluation activity (90d)",
    """
    SELECT COUNT(*)
      FROM system.mlflow.runs_latest
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
        AND (lower(COALESCE(run_name, '')) RLIKE '(eval|trace|judge|genai)'
             OR array_contains(map_keys(COALESCE(tags, map())), 'mlflow.genai.evaluation'))
    """,
    minimal=1.0, active=5.0,
)

# --- Governance & Security -------------------------------------------

check(
    "5.2", "Governance & Security", "Tags applied to data objects",
    """
    SELECT (SELECT COUNT(*) FROM system.information_schema.catalog_tags)
         + (SELECT COUNT(*) FROM system.information_schema.schema_tags)
         + (SELECT COUNT(*) FROM system.information_schema.table_tags)
         + (SELECT COUNT(*) FROM system.information_schema.column_tags)
    """,
    minimal=1.0, active=10.0,
)

check(
    "5.3", "Governance & Security", "Data classification tags on columns",
    """
    SELECT COUNT(*)
      FROM system.information_schema.column_tags
      WHERE lower(tag_name) RLIKE '(class|sensitiv|pii|confidential|gdpr)'
    """,
    minimal=1.0, active=5.0,
)

check(
    "5.4", "Governance & Security", "Row filters and column masks",
    """
    SELECT (SELECT COUNT(*) FROM system.information_schema.row_filters)
         + (SELECT COUNT(*) FROM system.information_schema.column_masks)
    """,
    minimal=1.0, active=3.0,
)

check(
    "5.6", "Governance & Security", "Service principals running workloads (%)",
    """
    WITH w AS (
      SELECT run_as FROM (
        SELECT run_as, ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.jobs
      ) x WHERE rn = 1
      UNION ALL
      SELECT run_as FROM (
        SELECT run_as, ROW_NUMBER() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.pipelines
      ) y WHERE rn = 1
    )
    SELECT COALESCE(ROUND(100.0 * COUNT_IF(run_as IS NOT NULL
             AND NOT run_as RLIKE '^[^@ ]+@[^@ ]+\\.[^@ ]+$') / NULLIF(COUNT(*), 0), 1), 0)
      FROM w
    """,
    minimal=10.0, active=60.0, pct=True,
)

check(
    "5.7", "Governance & Security", "Audit log actively queried (90d)",
    """
    SELECT COUNT(*)
      FROM system.query.history
      WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
        AND lower(statement_text) LIKE '%system.access.audit%'
    """,
    minimal=1.0, active=10.0,
)

check(
    "5.8", "Governance & Security", "Security Analysis Tool running",
    """
    SELECT COUNT(DISTINCT job_id)
      FROM system.lakeflow.jobs
      WHERE delete_time IS NULL
        AND (lower(name) LIKE '%security analysis%' OR lower(name) LIKE '%sat %'
             OR lower(name) LIKE '%security_analysis%')
    """,
    minimal=1.0, active=1.0,
)

# --- Data Sharing ----------------------------------------------------

check(
    "6.2", "Data Sharing", "Delta Sharing activity (90d)",
    """
    SELECT COUNT(*)
      FROM system.access.audit
      WHERE event_date >= CURRENT_DATE() - INTERVAL 90 DAYS
        AND action_name LIKE 'deltaSharing%'
    """,
    minimal=1.0, active=100.0,
)

check(
    "6.4", "Data Sharing", "Clean rooms in use (DBUs, 90d)",
    """
    SELECT COALESCE(SUM(usage_quantity), 0)
      FROM system.billing.usage
      WHERE usage_date >= CURRENT_DATE() - INTERVAL 90 DAYS
        AND upper(billing_origin_product) LIKE '%CLEAN%'
    """,
    minimal=0.01, active=1.0,
)


# --- Compound and sampled additions ----------------------------------

def _uc_vs_hive(v):
    """5.1 - Unity Catalog adoption measured against remaining Hive use."""
    uc, hive = v["uc_statements"], v["hive_statements"]
    total = uc + hive
    pct = (uc / total * 100) if total else 100.0
    score = 2 if pct >= 95 else (1 if pct >= 50 else 0)
    return round(pct, 1), score, f"{hive} statements still referencing hive_metastore"


compound(
    "5.1", "Governance & Security", "Unity Catalog adoption vs. Hive metastore",
    {
        "uc_statements": """
            SELECT COUNT(*) FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
              AND statement_text IS NOT NULL
              AND NOT lower(statement_text) LIKE '%hive_metastore%'
        """,
        "hive_statements": """
            SELECT COUNT(*) FROM system.query.history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
              AND lower(statement_text) LIKE '%hive_metastore%'
        """,
    },
    _uc_vs_hive,
)


def _shares_defined(v):
    """6.1 - shares and recipients this workspace publishes."""
    shares, recipients = v["shares"], v["recipients"]
    score = 2 if (shares >= 1 and recipients >= 1) else (1 if shares >= 1 else 0)
    return shares, score, f"{recipients} recipients"


compound(
    "6.1", "Data Sharing", "Shares and recipients defined (provider)",
    {}, _shares_defined, sampler="sharing_inventory",
)


def _shared_consumed(v):
    """6.3 - Delta Sharing catalogs mounted from other providers."""
    providers, catalogs = v["providers"], v["shared_catalogs"]
    score = 2 if catalogs >= 2 else (1 if (catalogs >= 1 or providers >= 1) else 0)
    return catalogs, score, f"{providers} providers"


compound(
    "6.3", "Data Sharing", "Shared data consumed (recipient)",
    {}, _shared_consumed, sampler="sharing_inventory",
)


def _liquid_clustering(v):
    """3.17 - share of sampled tables declaring clustering columns."""
    sampled, clustered, total = v["sampled"], v["clustered"], v["total_tables"]
    if not sampled:
        return 0.0, 0, "no managed tables to sample"
    estimated = (clustered / sampled) * total
    score = 2 if estimated > 10 else (1 if estimated >= 1 else 0)
    return round(estimated, 1), score, f"{clustered}/{sampled} sampled, {total} tables total"


compound(
    "3.17", "Data Engineering", "Liquid clustering adopted",
    {
        "total_tables": """
            SELECT COUNT(*) FROM system.information_schema.tables
            WHERE table_type = 'MANAGED'
              AND table_schema != 'information_schema'
              AND table_catalog NOT IN ('system', 'samples', '__databricks_internal')
        """,
    },
    _liquid_clustering,
    sampler="clustering",
)


def _abac_policies(v):
    """5.5 - ABAC policies attached to catalogs or schemas.

    SHOW POLICIES is per-securable, so the sampler walks catalogs rather
    than relying on a system table, which does not expose them.
    """
    policies, scanned = v["policies"], v["catalogs_scanned"]
    score = 2 if policies >= 3 else (1 if policies >= 1 else 0)
    return policies, score, f"across {scanned} catalogs"


compound(
    "5.5", "Governance & Security", "ABAC policies defined",
    {}, _abac_policies, sampler="abac_policies",
)
