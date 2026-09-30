# Extra Adoption Checks from the Pattern Library

Adoption and usage evidence found by reviewing every file under `patterns/` (98 files). Each item is either a **new** check, now added to [`adoption_checks.md`](adoption_checks.md), or a **duplicate** of an existing check, listed for traceability. Files that only assess implementation quality are listed at the end with the reason.

The tables follow the format of `adoption_checks.md`, with one extra column, **Source pattern(s)**. Everything in section A is new, so it has no Status column. `adoption_checks.md` itself has **Source pattern(s)** and **Implemented** (*Yes* / *Proxy* / *No*, based on `src/datavail_assessment/adoption/checks.py`) on every check. Category assignments follow [`pattern-checkmap.md`](pattern-checkmap.md).

**Adoption vs. quality rule used:** an item counts as adoption evidence if its signal answers *"is this capability being used, and how much?"*. Examples are the count or volume of objects, runs, queries or events. An item is quality-only if its signal answers *"is it used well?"*. Examples are coverage ratios of a best practice, configuration hygiene and anti-pattern instances. Capabilities that only regulated or DR-scoped workloads need (CMK, compliance security profile, DR replication) are also left out of scoring. For those, being off is not low adoption.

Items marked `*` use a `billing_origin_product` value or system table that the pattern files did not verify, or that they spell differently. Confirm these on the first run.

## At a glance

| Measure | Count |
|---------|------:|
| Pattern files reviewed | 98 |
| Files with adoption evidence | 45 |
| Quality-only files | 53 |
| New checks added to `adoption_checks.md` | 29 |
| Adoption items already covered (duplicates) | 22 |
| New check categories added | 2 |
| `init_items_mapping` items traced | 31 |
| New checks with no `init_items` counterpart | 6 |
| Checks in `adoption_checks.md` after update (51 existing + 29 new) | 80 |

| Category | New checks | Duplicates |
|----------|-----------:|-----------:|
| Home / Workspace | 7 | 4 |
| SQL | 5 | 5 |
| Data Engineering | 4 | 5 |
| AI/ML | 1 | 7 |
| Governance & Security | 8 | 0 |
| Data Sharing & Collaboration | 4 | 1 |
| **Total** | **29** | **22** |

---

## A. New checks (29), added to `adoption_checks.md`

### 1. Home / Workspace (7)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 1.11 | Billable products in use (breadth) | `system.billing.usage` (distinct `billing_origin_product` with usage) | How much of the platform is actually consumed, not just provisioned | [`platform-onboarding/platform-usage-profile.md`](../patterns/platform-onboarding/platform-usage-profile.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md) |
| 1.12 | Serverless share of compute DBUs | `system.billing.usage` (`product_features.is_serverless` / `sku_name` LIKE `%SERVERLESS%`) | Serverless compute is in use | [`platform-onboarding/serverless-first-compute.md`](../patterns/platform-onboarding/serverless-first-compute.md)<br>[`sql-analytics/serverless-sql-warehouses.md`](../patterns/sql-analytics/serverless-sql-warehouses.md) |
| 1.13 | Workspaces with active usage | `system.access.workspaces_latest` + `system.billing.usage` (distinct `workspace_id`) | The platform is used beyond a single sandbox workspace (e.g. dev / prod split) | [`platform-onboarding/environment-based-workspace-strategy.md`](../patterns/platform-onboarding/environment-based-workspace-strategy.md) |
| 1.14 | Bundle-deployed jobs and pipelines | `system.lakeflow.jobs` / `system.lakeflow.pipelines` (name has the bundle `[<target>]` prefix, `creator_id` is a service principal) | Declarative Automation Bundles (formerly DABs) / CI/CD deployment adopted | [`platform-onboarding/infrastructure-as-code-terraform-and-bundles.md`](../patterns/platform-onboarding/infrastructure-as-code-terraform-and-bundles.md)<br>[`platform-onboarding/git-backed-development-and-cicd.md`](../patterns/platform-onboarding/git-backed-development-and-cicd.md) |
| 1.15 | System tables enabled and queried | `SHOW SCHEMAS IN system` + `system.query.history` (statements referencing `system.`) | Observability built on system tables (cost, jobs, query dashboards and alerts) | [`platform-onboarding/observability-from-system-tables.md`](../patterns/platform-onboarding/observability-from-system-tables.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md) |
| 1.16 | Cost-attribution tags and budgets | `system.billing.usage` (`custom_tags` non-empty) + Budgets API / account console | FinOps controls (chargeback tags, budgets) are in use | [`platform-onboarding/cost-attribution-tagging-and-budgets.md`](../patterns/platform-onboarding/cost-attribution-tagging-and-budgets.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md)<br>[`unity-catalog-governance/tagging-strategy.md`](../patterns/unity-catalog-governance/tagging-strategy.md) |
| 1.17 | Databricks Apps deployed | `system.billing.usage` (`billing_origin_product` for Apps*) + Apps API | Data / AI applications are hosted on the platform | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) |

### 2. SQL (5)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 2.13 | Genie usage volume | `system.query.history` (`query_source.genie_space_id` IS NOT NULL) | Business users are asking Genie questions, not just creating spaces (extends 2.8) | [`sql-analytics/curated-genie-spaces.md`](../patterns/sql-analytics/curated-genie-spaces.md) |
| 2.14 | Dashboard-driven query volume | `system.query.history` (`query_source.dashboard_id` IS NOT NULL) | Dashboards are being viewed and refreshed, not just built (extends 2.5) | [`sql-analytics/dashboards-on-governed-datasets.md`](../patterns/sql-analytics/dashboards-on-governed-datasets.md) |
| 2.15 | Metric views defined and queried | `information_schema.tables` (`table_type` = `METRIC_VIEW`) + `system.query.history` (`statement_text` contains `MEASURE(`) | A governed semantic layer has been adopted | [`sql-analytics/metric-views-as-semantic-layer.md`](../patterns/sql-analytics/metric-views-as-semantic-layer.md) |
| 2.16 | External BI / client tools connected | `system.query.history` (distinct `client_application` outside Databricks-native sources) | Warehouses serve the wider BI estate (Tableau, Power BI, etc.) | [`sql-analytics/third-party-bi-tool-integration.md`](../patterns/sql-analytics/third-party-bi-tool-integration.md) |
| 2.17 | Cost-per-query attribution in place | `information_schema.tables` (Labs cost-per-query MV or equivalent) / `system.access.table_lineage` (tables downstream of `system.query.history`) | Warehouse cost is allocated to queries, users, dashboards and tools | [`sql-analytics/cost-per-query-attribution.md`](../patterns/sql-analytics/cost-per-query-attribution.md) |

### 3. Data Engineering (4)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 3.15 | Declared data quality rules | Pipeline event logs (expectations) + `system.information_schema.table_constraints` | Data quality is enforced in pipelines or tables | [`orchestration-reliability/pipeline-expectations-for-data-quality.md`](../patterns/orchestration-reliability/pipeline-expectations-for-data-quality.md) |
| 3.16 | Data quality monitoring enabled | `system.data_quality_monitoring.table_results` + monitor inventory | Freshness, anomaly or drift monitoring is running on tables | [`orchestration-reliability/sla-tracking-and-data-freshness.md`](../patterns/orchestration-reliability/sla-tracking-and-data-freshness.md)<br>[`platform-onboarding/observability-from-system-tables.md`](../patterns/platform-onboarding/observability-from-system-tables.md)<br>[`ml-ai-lifecycle/inference-tables-and-drift-monitoring.md`](../patterns/ml-ai-lifecycle/inference-tables-and-drift-monitoring.md) |
| 3.17 | Liquid clustering adopted | `DESCRIBE DETAIL` sampling of active tables (`clusteringColumns`) | Modern Delta table layout is in use | [`table-optimization/liquid-clustering-over-partitioning.md`](../patterns/table-optimization/liquid-clustering-over-partitioning.md) |
| 3.18 | Predictive optimization active | `system.storage.predictive_optimization_operations_history`* / metastore setting | Automated table maintenance (OPTIMIZE, VACUUM, ANALYZE) is running | [`table-optimization/predictive-optimization-autopilot.md`](../patterns/table-optimization/predictive-optimization-autopilot.md) |

### 4. AI/ML (1)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 4.16 | GenAI tracing and evaluation activity | `system.mlflow.experiments_latest` / `system.mlflow.runs_latest` (evaluation runs, traces) | GenAI apps are traced and evaluated, not just deployed | [`ml-ai-lifecycle/genai-evaluation-and-human-feedback.md`](../patterns/ml-ai-lifecycle/genai-evaluation-and-human-feedback.md)<br>[`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) |

### 5. Governance & Security (8)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 5.1 | Unity Catalog adoption vs. Hive metastore | `SHOW CATALOGS` (`hive_metastore` inventory) + `system.query.history` / `system.access.table_lineage` (activity against `hive_metastore`) | Workloads have moved to Unity Catalog | [`unity-catalog-governance/legacy-hive-metastore-usage.md`](../patterns/unity-catalog-governance/legacy-hive-metastore-usage.md) |
| 5.2 | Tags applied to data objects | `system.information_schema.catalog_tags` / `schema_tags` / `table_tags` / `column_tags` | A tagging taxonomy is used on data | [`unity-catalog-governance/tagging-strategy.md`](../patterns/unity-catalog-governance/tagging-strategy.md) |
| 5.3 | Governed tags / data classification | Tag Policies API (governed tags) + `information_schema.column_tags` (`class.*` classification tags) | Sensitive-data classification is running | [`unity-catalog-governance/automated-pii-classification.md`](../patterns/unity-catalog-governance/automated-pii-classification.md)<br>[`unity-catalog-governance/abac-governed-tags.md`](../patterns/unity-catalog-governance/abac-governed-tags.md) |
| 5.4 | Row filters and column masks | `system.information_schema.row_filters` / `column_masks` | Fine-grained access control is in use | [`unity-catalog-governance/row-filters-and-column-masks.md`](../patterns/unity-catalog-governance/row-filters-and-column-masks.md) |
| 5.5 | ABAC policies defined | `SHOW POLICIES` / Policies API (per catalog and schema) | Tag-driven access policies are adopted | [`unity-catalog-governance/abac-governed-tags.md`](../patterns/unity-catalog-governance/abac-governed-tags.md) |
| 5.6 | Service principals running workloads | `system.lakeflow.jobs.run_as` / `system.lakeflow.pipelines.run_as` (application ID vs. email) | Automation runs under non-human identities | [`platform-onboarding/service-principals-for-automation.md`](../patterns/platform-onboarding/service-principals-for-automation.md) |
| 5.7 | Audit log actively monitored | `system.query.history` (statements referencing `system.access.audit`) + `system.alert` / Alerts API | Security events are being watched | [`security-compliance/security-audit-monitoring.md`](../patterns/security-compliance/security-audit-monitoring.md) |
| 5.8 | Security Analysis Tool running | `system.lakeflow.jobs` (SAT job names) + `system.lakeflow.job_run_timeline` | Security posture is assessed regularly | [`security-compliance/security-analysis-tool-baseline.md`](../patterns/security-compliance/security-analysis-tool-baseline.md) |

### 6. Data Sharing & Collaboration (4)

| # | Check | Evidence Source | What It Proves | Source pattern(s) |
|---|-------|-----------------|----------------|-------------------|
| 6.1 | Shares and recipients defined (provider) | `SHOW SHARES` / `SHOW RECIPIENTS` (Shares and Recipients APIs) | Delta Sharing is set up to share data out | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) |
| 6.2 | Delta Sharing activity | `system.access.audit` (`action_name` IN `deltaSharingQueriedTable`, `deltaSharingQueriedTableChanges`) | Recipients are actually consuming shared data | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) |
| 6.3 | Shared data consumed (recipient) | UC Catalogs API (catalogs of type `DELTASHARING_CATALOG`) + `system.billing.usage` (`DATA_SHARING`*) | The organisation consumes data shared by others | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) |
| 6.4 | Clean rooms in use | Clean Rooms API + `system.billing.usage` (`billing_origin_product` for clean rooms*) | Privacy-safe multi-party collaboration is adopted | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) |

### Thresholds for new checks (29)

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 1.11 | Billable products in use (breadth) | No usage | 1–3 products in 90 days | > 3 products with usage in 30 days |
| 1.12 | Serverless share of compute DBUs | 0% serverless | > 0–25% of DBUs in 30 days | > 25% of DBUs in 30 days |
| 1.13 | Workspaces with active usage | 0 workspaces with usage | 1 workspace with usage | ≥ 2 workspaces with usage in 30 days |
| 1.14 | Bundle-deployed jobs and pipelines | 0 bundle-deployed workloads | 1–5 bundle-deployed jobs/pipelines | > 5 bundle-deployed jobs/pipelines |
| 1.15 | System tables enabled and queried | Core schemas (`billing`, `access`, `compute`, `lakeflow`) not enabled or never queried | Enabled, ad-hoc queries only | Queried on a schedule (dashboard, alert or job) in 30 days |
| 1.16 | Cost-attribution tags and budgets | No tagged usage and no budgets | Some tagged usage or ≥ 1 budget | > 50% of DBUs tagged and ≥ 1 budget |
| 1.17 | Databricks Apps deployed | 0 apps | 1 app with usage in 90 days | > 1 app with usage in 30 days |
| 2.13 | Genie usage volume | 0 Genie queries | 1–50 Genie queries in 90 days | > 50 Genie queries in 30 days |
| 2.14 | Dashboard-driven query volume | 0 dashboard queries | 1–100 in 90 days | > 100 in 30 days |
| 2.15 | Metric views defined and queried | 0 metric views | Metric views exist, not queried in 30 days | Metric views queried in 30 days |
| 2.16 | External BI / client tools connected | 0 external tools | 1 external tool | > 1 external tool in 30 days |
| 2.17 | Cost-per-query attribution in place | No allocation object | Exists, not refreshed or queried in 30 days | Refreshed and queried in 30 days |
| 3.15 | Declared data quality rules | 0 pipelines with expectations and 0 constrained tables | 1–2 pipelines or tables | > 2 pipelines or tables |
| 3.16 | Data quality monitoring enabled | 0 monitored tables | 1–5 monitored tables | > 5 monitored tables with results in 30 days |
| 3.17 | Liquid clustering adopted | 0 clustered tables | 1–5 clustered tables | > 5 clustered tables |
| 3.18 | Predictive optimization active | Disabled, no operations | Operations in 90 days on 1 catalog | Operations in 30 days across 2+ catalogs |
| 4.16 | GenAI tracing and evaluation activity | 0 evaluation runs | 1–5 evaluation runs in 90 days | > 5 evaluation runs in 30 days |
| 5.1 | Unity Catalog adoption vs. Hive metastore | Most table activity in `hive_metastore` | UC used, but `hive_metastore` read or written in 30 days | No `hive_metastore` activity in 30 days |
| 5.2 | Tags applied to data objects | 0 tagged objects | 1–20 tagged objects | > 20 tagged objects across 2+ catalogs |
| 5.3 | Governed tags / data classification | No governed tags, no classification tags | Governed tags defined or classification on 1 catalog | Classification tags on 2+ catalogs |
| 5.4 | Row filters and column masks | 0 tables | 1–5 tables protected | > 5 tables protected |
| 5.5 | ABAC policies defined | 0 policies | 1 policy | > 1 policy |
| 5.6 | Service principals running workloads | 0 jobs/pipelines as service principal | < 50% of active jobs/pipelines | ≥ 50% of jobs/pipelines active in 30 days |
| 5.7 | Audit log actively monitored | No queries on the audit log | Ad-hoc queries only in 90 days | Scheduled query, dashboard or alert on the audit log in 30 days |
| 5.8 | Security Analysis Tool running | Not installed | Installed, no successful run in 30 days | Successful run in 30 days |
| 6.1 | Shares and recipients defined (provider) | 0 shares | 1 share | > 1 share with recipients |
| 6.2 | Delta Sharing activity | 0 events | < 50 events in 90 days | > 50 events in 30 days |
| 6.3 | Shared data consumed (recipient) | 0 shared catalogs | 1 shared catalog | > 1 shared catalog |
| 6.4 | Clean rooms in use | 0 clean rooms | 1 clean room | > 1 clean room |

---

## B. Adoption evidence already covered, not added (22)

By category: Home / Workspace 4, SQL 5, Data Engineering 5, AI/ML 7, Data Sharing & Collaboration 1.

| Ref | Category | Evidence item | Existing check(s) | Source pattern(s) | Status / note |
|-----|----------|---------------|-------------------|-------------------|---------------|
| D1 | Data Engineering | Auto Loader / Lakeflow Connect ingestion pipelines | 3.13 Auto Loader / Lakeflow Connect presence, 3.5 SDP pipelines defined | [`data-ingestion/autoloader-incremental-ingestion.md`](../patterns/data-ingestion/autoloader-incremental-ingestion.md) | Duplicate. Covered. `system.lakeflow.pipelines` + `system.access.table_lineage` (`entity_type = 'PIPELINE'`) is a stronger source for 3.13 than notebook code scanning. |
| D2 | Data Engineering | Database CDC ingestion pipelines | 3.13 Auto Loader / Lakeflow Connect presence | [`data-ingestion/change-data-capture-ingestion.md`](../patterns/data-ingestion/change-data-capture-ingestion.md) | Duplicate. Covered by 3.13. System tables cannot tell CDC apart from periodic full extract. |
| D3 | Data Engineering | Structured streaming with checkpoints | 3.7 Streaming workloads | [`data-ingestion/idempotent-ingestion-with-checkpoints.md`](../patterns/data-ingestion/idempotent-ingestion-with-checkpoints.md) | Duplicate. Covered by 3.7. The checkpoint pattern itself is quality-only. |
| D4 | Data Engineering | Multi-task jobs with task dependencies | 3.4 Multi-task jobs vs. single-task | [`orchestration-reliability/task-dependencies-over-schedule-chaining.md`](../patterns/orchestration-reliability/task-dependencies-over-schedule-chaining.md) | Duplicate. Covered by 3.4. `depends_on_keys` in `system.lakeflow.job_tasks` can sharpen 3.4 later. |
| D5 | Data Engineering | Failure notifications configured | 3.14 Workflow notifications configured | [`orchestration-reliability/failure-notifications-and-duration-thresholds.md`](../patterns/orchestration-reliability/failure-notifications-and-duration-thresholds.md) | Duplicate. Covered by 3.14 (Jobs API). |
| D6 | Home / Workspace | Compute policies on clusters | 1.10 Cluster policies in use | [`platform-onboarding/compute-policies-and-standard-sizing.md`](../patterns/platform-onboarding/compute-policies-and-standard-sizing.md) | Duplicate. Covered by 1.10 (`policy_id`). |
| D7 | Home / Workspace | Git folders / version-controlled development | 1.4 Git folder / Repos usage | [`platform-onboarding/git-backed-development-and-cicd.md`](../patterns/platform-onboarding/git-backed-development-and-cicd.md) | Duplicate. Covered by 1.4. Bundle deployment is the new check 1.14. |
| D8 | Home / Workspace | Catalogs and schemas organised in UC | 1.6 Unity Catalog objects created | [`unity-catalog-governance/domain-catalog-organization.md`](../patterns/unity-catalog-governance/domain-catalog-organization.md) | Duplicate. Covered by 1.6. The naming convention itself is quality-only. |
| D9 | Home / Workspace | Secret scope usage | 1.8 Secrets and token usage | [`security-compliance/secrets-management.md`](../patterns/security-compliance/secrets-management.md) | Duplicate. Covered by 1.8 (`service_name = 'secrets'`). ACL hygiene is quality-only. |
| D10 | SQL | Warehouse types including serverless | 2.1 SQL warehouses provisioned | [`sql-analytics/serverless-sql-warehouses.md`](../patterns/sql-analytics/serverless-sql-warehouses.md) | Duplicate. Covered by 2.1. Platform-wide serverless share is the new check 1.12. |
| D11 | SQL | Genie spaces exist | 2.8 Genie spaces created | [`sql-analytics/curated-genie-spaces.md`](../patterns/sql-analytics/curated-genie-spaces.md) | Duplicate. Covered by 2.8. Usage volume is the new check 2.13. |
| D12 | SQL | Dashboards exist | 2.5 Lakeview dashboards created | [`sql-analytics/dashboards-on-governed-datasets.md`](../patterns/sql-analytics/dashboards-on-governed-datasets.md) | Duplicate. Covered by 2.5. Consumption is the new check 2.14. |
| D13 | SQL | Materialized views in serving layer | 2.10 Materialized views and streaming tables | [`sql-analytics/materialized-views-for-serving-layers.md`](../patterns/sql-analytics/materialized-views-for-serving-layers.md) | Duplicate. Covered by 2.10. |
| D14 | SQL | Lakehouse Federation foreign catalogs | 2.11 Federated / foreign tables present | [`sql-analytics/federation-for-ad-hoc-access.md`](../patterns/sql-analytics/federation-for-ad-hoc-access.md) | Duplicate. Covered by 2.11. |
| D15 | AI/ML | MLflow experiments and runs | 4.1 MLflow experiments created, 4.2 MLflow runs logged | [`ml-ai-lifecycle/mlflow-experiment-tracking.md`](../patterns/ml-ai-lifecycle/mlflow-experiment-tracking.md) | Duplicate. Covered. `system.mlflow.experiments_latest` / `runs_latest` are more direct sources than the audit log for 4.1 and 4.2. |
| D16 | AI/ML | Models and versions registered in UC | 4.3 Models registered in Unity Catalog, 4.4 Model versions created | [`ml-ai-lifecycle/models-in-unity-catalog.md`](../patterns/ml-ai-lifecycle/models-in-unity-catalog.md) | Duplicate. Covered. Alias use and legacy-registry use are quality-only. |
| D17 | AI/ML | Serving endpoints and traffic | 4.5 Serving endpoints provisioned, 4.6 Serving endpoint traffic | [`ml-ai-lifecycle/production-serving-endpoint-configuration.md`](../patterns/ml-ai-lifecycle/production-serving-endpoint-configuration.md) | Duplicate. Covered by 4.5 and 4.6. |
| D18 | AI/ML | AI Gateway endpoints, tokens, providers | 4.7 AI Gateway endpoints active, 4.8 AI Gateway request/token volume, 4.9 Distinct models/providers routed through Gateway | [`ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md`](../patterns/ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md) | Duplicate. Covered. The pattern files and `src` both use `system.ai_gateway.usage`, so the evidence source for 4.7–4.9 in `adoption_checks.md` was corrected from `system.ai.endpoint_usage`. |
| D19 | AI/ML | Feature tables / Feature Views | 4.10 Feature tables present | [`ml-ai-lifecycle/feature-store-for-consistent-features.md`](../patterns/ml-ai-lifecycle/feature-store-for-consistent-features.md) | Duplicate. Covered by 4.10. |
| D20 | AI/ML | GenAI products in use (serving, vector search, Agent Bricks) | 4.5 Serving endpoints provisioned, 4.11 Vector search indexes created, 4.12 Agent Bricks tiles defined, 1.11 (new) | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | Duplicate. Covered by the individual checks and breadth check 1.11. Apps (1.17) and evaluation (4.16) are new. |
| D21 | AI/ML | Inference tables enabled | 4.13 Inference tables logging enabled | [`ml-ai-lifecycle/inference-tables-and-drift-monitoring.md`](../patterns/ml-ai-lifecycle/inference-tables-and-drift-monitoring.md) | Duplicate. Covered by 4.13. Monitors on inference tables feed new check 3.16. |
| D22 | Data Sharing & Collaboration | Marketplace listings consumed | 1.9 Marketplace listings consumed | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | Duplicate. Already exists as 1.9 (Home / Workspace). Left in place so the IDs used in the scoring notebook don't change. |

---

## C. Traceability to `init_items` / `init_items_mapping` (31 items)

Each assessment item in `init_items_mapping` is traced to its primary pattern file and to the adoption outcome. "Quality only" items stay in the maturity assessment and are not scored for adoption.

Outcomes: Feeds one or more new checks 17, Covered by existing checks only 4, Quality only 7, Not scored (requirement-driven) 3.

| init_items area | Assessment item | Primary pattern file | Adoption outcome |
|-----------------|-----------------|----------------------|------------------|
| General | Platform usage | [`platform-onboarding/platform-usage-profile.md`](../patterns/platform-onboarding/platform-usage-profile.md) | **1.11** (new) |
| Governance and Unity Catalog | Identity/group management on resources | [`platform-onboarding/workspace-object-permissions.md`](../patterns/platform-onboarding/workspace-object-permissions.md) | Quality only (ACL hygiene); related adoption signal 5.6 |
| Governance and Unity Catalog | Use of tagging | [`unity-catalog-governance/tagging-strategy.md`](../patterns/unity-catalog-governance/tagging-strategy.md) | **5.2** (new), **1.16** (new) |
| Governance and Unity Catalog | ABAC policies used | [`unity-catalog-governance/abac-governed-tags.md`](../patterns/unity-catalog-governance/abac-governed-tags.md) | **5.5** (new) |
| Governance and Unity Catalog | Policies for compute | [`platform-onboarding/compute-policies-and-standard-sizing.md`](../patterns/platform-onboarding/compute-policies-and-standard-sizing.md) | 1.10 (existing) |
| Governance and Unity Catalog | Access controls (row filters, column masks) | [`unity-catalog-governance/row-filters-and-column-masks.md`](../patterns/unity-catalog-governance/row-filters-and-column-masks.md) | **5.4** (new) |
| Workspace design | How workspaces are split for environments | [`platform-onboarding/environment-based-workspace-strategy.md`](../patterns/platform-onboarding/environment-based-workspace-strategy.md) | **1.13** (new); split quality stays in maturity assessment |
| Workspace design | Layering (medallion) pattern used | [`sql-analytics/medallion-layering-for-analytics.md`](../patterns/sql-analytics/medallion-layering-for-analytics.md) | Quality only |
| CI/CD / Development Lifecycle | Use of DABs | [`platform-onboarding/infrastructure-as-code-terraform-and-bundles.md`](../patterns/platform-onboarding/infrastructure-as-code-terraform-and-bundles.md) | **1.14** (new); 1.4 (existing) |
| Security and Identity | SSO and identity management | [`platform-onboarding/account-first-identity-federation.md`](../patterns/platform-onboarding/account-first-identity-federation.md) | Quality only (Account API config); related 5.6, 5.8 |
| Security and Identity | Secrets | [`security-compliance/secrets-management.md`](../patterns/security-compliance/secrets-management.md) | 1.8 (existing) |
| Security and Identity | CMEK | [`security-compliance/customer-managed-keys.md`](../patterns/security-compliance/customer-managed-keys.md) | Not scored (requirement-driven) |
| Security and Identity | Audit logging | [`security-compliance/security-audit-monitoring.md`](../patterns/security-compliance/security-audit-monitoring.md) | **5.7** (new) |
| FinOps | Compute right sizing | [`platform-onboarding/compute-right-sizing.md`](../patterns/platform-onboarding/compute-right-sizing.md) | Quality only; related 1.12 |
| FinOps | Compute configuration (Classic) | [`platform-onboarding/misconfigured-classic-compute.md`](../patterns/platform-onboarding/misconfigured-classic-compute.md) | Quality only |
| FinOps | Cost visibility (tagging for chargeback) | [`platform-onboarding/cost-attribution-tagging-and-budgets.md`](../patterns/platform-onboarding/cost-attribution-tagging-and-budgets.md) | **1.16** (new) |
| FinOps | Spend patterns | [`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md) | Quality only (trend health); inputs 1.11, 1.16 |
| AI/BI | Warehouse right sizing/SKU | [`sql-analytics/serverless-sql-warehouses.md`](../patterns/sql-analytics/serverless-sql-warehouses.md) | 2.1 (existing); 1.12 (new) |
| AI/BI | Cost per query set up? | [`sql-analytics/cost-per-query-attribution.md`](../patterns/sql-analytics/cost-per-query-attribution.md) | **2.17** (new) |
| AI/BI | Metric centralization | [`sql-analytics/metric-views-as-semantic-layer.md`](../patterns/sql-analytics/metric-views-as-semantic-layer.md) | **2.15** (new); 2.14 (new, supporting) |
| AI/BI | 3rd Party tools used | [`sql-analytics/third-party-bi-tool-integration.md`](../patterns/sql-analytics/third-party-bi-tool-integration.md) | **2.16** (new) |
| AI/ML | Use of MLFlow experiments, model registry in UC | [`ml-ai-lifecycle/models-in-unity-catalog.md`](../patterns/ml-ai-lifecycle/models-in-unity-catalog.md) | 4.1–4.4 (existing) |
| AI/ML | Feature management | [`ml-ai-lifecycle/feature-store-for-consistent-features.md`](../patterns/ml-ai-lifecycle/feature-store-for-consistent-features.md) | 4.10 (existing) |
| AI/ML | Gen AI readiness | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | **4.16**, **1.17** (new); 4.7–4.12 (existing) |
| Platform management | Observability tools in place? | [`platform-onboarding/observability-from-system-tables.md`](../patterns/platform-onboarding/observability-from-system-tables.md) | **1.15** (new) |
| Platform management | SLA tracking | [`orchestration-reliability/sla-tracking-and-data-freshness.md`](../patterns/orchestration-reliability/sla-tracking-and-data-freshness.md) | **3.16** (new) |
| Platform management | Disaster recovery | [`platform-onboarding/disaster-recovery-strategy.md`](../patterns/platform-onboarding/disaster-recovery-strategy.md) | Not scored (requirement-driven) |
| Data sharing and collaboration | Use of external/internal sharing | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | **6.1–6.3** (new); 1.9 (existing) |
| Compliance/regulatory alignment | Requirements for regulatory framework(s)? | [`security-compliance/compliance-security-profile.md`](../patterns/security-compliance/compliance-security-profile.md) | Not scored (requirement-driven) |
| Compliance/regulatory alignment | Data retention policies | [`unity-catalog-governance/data-retention-policies.md`](../patterns/unity-catalog-governance/data-retention-policies.md) | Quality only |
| Compliance/regulatory alignment | PII handling | [`unity-catalog-governance/automated-pii-classification.md`](../patterns/unity-catalog-governance/automated-pii-classification.md) | **5.3** (new) |

New checks with no `init_items` counterpart, found only in the pattern library (6): 2.13, 3.15, 3.17, 3.18, 5.1, 6.4.

---

## Quality-only pattern files (53)

These files were reviewed and left out of the adoption checks because they assess *how well* a capability is implemented. Where a related adoption check exists, it is named.

| Pattern file | Reason |
|--------------|--------|
| [`data-ingestion/bronze-layer-immutability.md`](../patterns/data-ingestion/bronze-layer-immutability.md) | Whether bronze stays append-only is write discipline (quality). |
| [`data-ingestion/direct-writes-to-bronze-tables.md`](../patterns/data-ingestion/direct-writes-to-bronze-tables.md) | Anti-pattern: ad-hoc writes (quality). |
| [`data-ingestion/full-reload-instead-of-incremental.md`](../patterns/data-ingestion/full-reload-instead-of-incremental.md) | Anti-pattern: ingestion efficiency (quality). |
| [`data-ingestion/missing-schema-enforcement.md`](../patterns/data-ingestion/missing-schema-enforcement.md) | Anti-pattern: schema handling in code (quality). |
| [`data-ingestion/small-file-accumulation.md`](../patterns/data-ingestion/small-file-accumulation.md) | Anti-pattern: file layout (quality). Its remedy feeds 3.18. |
| [`data-sharing/data-copies-instead-of-sharing.md`](../patterns/data-sharing/data-copies-instead-of-sharing.md) | Anti-pattern: export copies (quality). Contributes context to 6.3. |
| [`ml-ai-lifecycle/cicd-for-ml-pipelines.md`](../patterns/ml-ai-lifecycle/cicd-for-ml-pipelines.md) | Mostly quality; its bundle-deployment signal feeds 1.14. |
| [`ml-ai-lifecycle/deploy-code-not-models.md`](../patterns/ml-ai-lifecycle/deploy-code-not-models.md) | Promotion practice (quality). |
| [`ml-ai-lifecycle/legacy-workspace-model-registry.md`](../patterns/ml-ai-lifecycle/legacy-workspace-model-registry.md) | Anti-pattern: migration gap (quality); UC registration is covered by 4.3. |
| [`ml-ai-lifecycle/model-aliases-for-deployment-state.md`](../patterns/ml-ai-lifecycle/model-aliases-for-deployment-state.md) | Deployment practice (quality). |
| [`ml-ai-lifecycle/stale-models-in-production.md`](../patterns/ml-ai-lifecycle/stale-models-in-production.md) | Anti-pattern: retraining cadence (quality). |
| [`ml-ai-lifecycle/training-serving-skew.md`](../patterns/ml-ai-lifecycle/training-serving-skew.md) | Anti-pattern: feature consistency (quality). |
| [`ml-ai-lifecycle/ungoverned-external-llm-access.md`](../patterns/ml-ai-lifecycle/ungoverned-external-llm-access.md) | Anti-pattern: traffic outside the gateway can't be seen in system tables (quality). |
| [`ml-ai-lifecycle/untracked-model-development.md`](../patterns/ml-ai-lifecycle/untracked-model-development.md) | Anti-pattern: logging completeness (quality). Its inverse is 4.1 and 4.2. |
| [`orchestration-reliability/monolithic-single-task-jobs.md`](../patterns/orchestration-reliability/monolithic-single-task-jobs.md) | Anti-pattern (quality). Inverse of 3.4. |
| [`orchestration-reliability/retries-and-timeouts-on-every-task.md`](../patterns/orchestration-reliability/retries-and-timeouts-on-every-task.md) | Job configuration hygiene (quality). |
| [`orchestration-reliability/schedule-chained-jobs.md`](../patterns/orchestration-reliability/schedule-chained-jobs.md) | Anti-pattern: orchestration design (quality). |
| [`orchestration-reliability/separate-ingestion-and-transformation-pipelines.md`](../patterns/orchestration-reliability/separate-ingestion-and-transformation-pipelines.md) | Pipeline decomposition (quality). |
| [`orchestration-reliability/silent-job-failures.md`](../patterns/orchestration-reliability/silent-job-failures.md) | Anti-pattern: reliability (quality). Related to 3.14. |
| [`orchestration-reliability/unbounded-task-execution.md`](../patterns/orchestration-reliability/unbounded-task-execution.md) | Anti-pattern: missing timeouts (quality). |
| [`platform-onboarding/account-first-identity-federation.md`](../patterns/platform-onboarding/account-first-identity-federation.md) | SCIM/SSO configuration posture (quality). Related adoption signal: 5.6. |
| [`platform-onboarding/all-purpose-compute-for-jobs.md`](../patterns/platform-onboarding/all-purpose-compute-for-jobs.md) | Anti-pattern: compute type choice (quality). |
| [`platform-onboarding/compute-right-sizing.md`](../patterns/platform-onboarding/compute-right-sizing.md) | Utilisation vs. size (quality). |
| [`platform-onboarding/disaster-recovery-strategy.md`](../patterns/platform-onboarding/disaster-recovery-strategy.md) | Driven by requirements; having no DR is not low adoption. Kept out of scoring. |
| [`platform-onboarding/manually-configured-workspaces.md`](../patterns/platform-onboarding/manually-configured-workspaces.md) | Anti-pattern (quality). Inverse of 1.14. |
| [`platform-onboarding/misconfigured-classic-compute.md`](../patterns/platform-onboarding/misconfigured-classic-compute.md) | Anti-pattern: cluster settings (quality). |
| [`platform-onboarding/notebooks-as-production-code.md`](../patterns/platform-onboarding/notebooks-as-production-code.md) | Anti-pattern (quality). Inverse of 1.4 and 1.14. |
| [`platform-onboarding/personal-identity-in-production.md`](../patterns/platform-onboarding/personal-identity-in-production.md) | Anti-pattern: human-owned production workloads (quality). Its inverse feeds 5.6. |
| [`platform-onboarding/phased-deployment-planning.md`](../patterns/platform-onboarding/phased-deployment-planning.md) | Process and documentation (not observable). |
| [`platform-onboarding/untagged-unmonitored-spend.md`](../patterns/platform-onboarding/untagged-unmonitored-spend.md) | Anti-pattern (quality). Inverse of 1.16. |
| [`platform-onboarding/workspace-object-permissions.md`](../patterns/platform-onboarding/workspace-object-permissions.md) | ACL hygiene (quality). |
| [`platform-onboarding/workspace-sprawl.md`](../patterns/platform-onboarding/workspace-sprawl.md) | Anti-pattern (quality). Context for 1.13. |
| [`security-compliance/compliance-security-profile.md`](../patterns/security-compliance/compliance-security-profile.md) | Driven by requirements (regulated workloads only); leaving it off is not low adoption. |
| [`security-compliance/customer-managed-keys.md`](../patterns/security-compliance/customer-managed-keys.md) | Driven by requirements; leaving it off is not low adoption. |
| [`sql-analytics/always-on-oversized-warehouses.md`](../patterns/sql-analytics/always-on-oversized-warehouses.md) | Anti-pattern: warehouse sizing (quality). |
| [`sql-analytics/analytics-on-raw-tables.md`](../patterns/sql-analytics/analytics-on-raw-tables.md) | Anti-pattern: consumer layer choice (quality). |
| [`sql-analytics/documented-tables-and-columns.md`](../patterns/sql-analytics/documented-tables-and-columns.md) | Comment coverage (quality). |
| [`sql-analytics/duplicated-metric-definitions.md`](../patterns/sql-analytics/duplicated-metric-definitions.md) | Anti-pattern (quality). Inverse of 2.15. |
| [`sql-analytics/federated-queries-in-production-pipelines.md`](../patterns/sql-analytics/federated-queries-in-production-pipelines.md) | Anti-pattern: federation misuse (quality). Foreign tables are already 2.11. |
| [`sql-analytics/medallion-layering-for-analytics.md`](../patterns/sql-analytics/medallion-layering-for-analytics.md) | Layering design (quality). Init item *Layering (medallion) pattern used* stays a quality assessment. |
| [`sql-analytics/query-performance-fundamentals.md`](../patterns/sql-analytics/query-performance-fundamentals.md) | Performance (quality). |
| [`sql-analytics/scheduled-snapshot-rebuilds.md`](../patterns/sql-analytics/scheduled-snapshot-rebuilds.md) | Anti-pattern: rebuild vs. MV (quality). |
| [`sql-analytics/sprawling-genie-spaces.md`](../patterns/sql-analytics/sprawling-genie-spaces.md) | Anti-pattern: Genie scope (quality). Usage volume feeds 2.13. |
| [`table-optimization/deletion-vectors-for-fast-dml.md`](../patterns/table-optimization/deletion-vectors-for-fast-dml.md) | On by default for new tables, so it does not tell clients apart. Per-table property only. |
| [`table-optimization/over-partitioning.md`](../patterns/table-optimization/over-partitioning.md) | Anti-pattern: layout (quality). Its inverse feeds 3.17. |
| [`table-optimization/stale-table-statistics.md`](../patterns/table-optimization/stale-table-statistics.md) | Anti-pattern: maintenance (quality). Its remedy feeds 3.18. |
| [`table-optimization/unmanaged-vacuum-retention.md`](../patterns/table-optimization/unmanaged-vacuum-retention.md) | Anti-pattern: maintenance (quality). Its remedy feeds 3.18. |
| [`unity-catalog-governance/data-retention-policies.md`](../patterns/unity-catalog-governance/data-retention-policies.md) | Retention schedule compliance (quality / requirement-driven). |
| [`unity-catalog-governance/group-based-access-control.md`](../patterns/unity-catalog-governance/group-based-access-control.md) | Ownership and grants to groups (quality). |
| [`unity-catalog-governance/individual-user-grants.md`](../patterns/unity-catalog-governance/individual-user-grants.md) | Anti-pattern: grants to users (quality). |
| [`unity-catalog-governance/lineage-and-audit-via-system-tables.md`](../patterns/unity-catalog-governance/lineage-and-audit-via-system-tables.md) | Lineage is captured automatically, so it is a detection mechanism, not adoption. Audit usage is 5.7. |
| [`unity-catalog-governance/unclassified-sensitive-data.md`](../patterns/unity-catalog-governance/unclassified-sensitive-data.md) | Anti-pattern: coverage gap (quality). Its inverse feeds 5.3. |
| [`unity-catalog-governance/unowned-catalog-objects.md`](../patterns/unity-catalog-governance/unowned-catalog-objects.md) | Anti-pattern: ownership (quality). |
