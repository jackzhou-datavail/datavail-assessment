# Databricks Platform Adoption Baseline Checks

A structured checklist to determine whether a client is **actively using** each major area of the Databricks platform. These checks measure **adoption breadth and depth** — not implementation quality (which is covered separately by maturity/anti-pattern assessments).

> **2026-09-29 update:** 29 checks were added from the pattern library: 1.11–1.17, 2.13–2.17, 3.15–3.18, 4.16, plus new sections **5. Governance & Security** and **6. Data Sharing & Collaboration**. Existing check IDs are unchanged. Source patterns and the de-duplication record are in [`extra_adoption_checks.md`](extra_adoption_checks.md), and the area-to-category map is in [`pattern-checkmap.md`](pattern-checkmap.md). Every check table now has a **Source pattern(s)** column, linking the pattern files that give evidence for the check, and an **Implemented** column showing whether `src/datavail_assessment/adoption/checks.py` scores the check: *Yes* (45) means the code measures the check as written, *Proxy* (6) means it uses a stand-in query (described in the cell), and *No* (29) means it isn't coded yet. All 29 checks added on 2026-09-29 are *No*. Existing checks with no matching pattern file show —. Items marked `*` use a `billing_origin_product` value or system table that needs confirming on the first run.

---

## 1. Home / Workspace — General Platform Adoption

Evidence that the client has onboarded users, established compute governance, and is actively developing on the platform.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 1.1 | Active users (last 30/60/90 days) | `system.access.audit` | People are logging in and working | — | Yes |
| 1.2 | Distinct users executing code (notebooks, REPL) | `system.access.audit` (action = `runCommand`) | Not just logging in — actually writing and running code | — | Yes |
| 1.3 | Notebooks created/modified | `system.access.audit` (action = `create`, `update` on notebooks) | Active development happening | — | Yes |
| 1.4 | Git folder / Repos usage | `system.access.audit` (service = `repos`) | Version control adoption | [`platform-onboarding/git-backed-development-and-cicd.md`](../patterns/platform-onboarding/git-backed-development-and-cicd.md) | Yes |
| 1.5 | Clusters created and hours consumed | `system.compute.clusters` + `system.billing.usage` (SKU = `ALL_PURPOSE`) | Interactive compute is being used | — | Yes |
| 1.6 | Unity Catalog objects created (catalogs, schemas, tables) | `system.information_schema.tables` / `system.information_schema.schemata` | Data is being organized in UC | [`unity-catalog-governance/domain-catalog-organization.md`](../patterns/unity-catalog-governance/domain-catalog-organization.md) | Yes |
| 1.7 | Workspace files (non-notebook assets — .py, .sql, .yaml) | `system.access.audit` (service = `workspace`, resource = `file`) | Using modular file-based development | — | Yes |
| 1.8 | Secrets and token usage | `system.access.audit` (service = `secrets`, `tokens`) | Integrations and automation being configured | [`security-compliance/secrets-management.md`](../patterns/security-compliance/secrets-management.md) | Yes |
| 1.9 | Marketplace listings consumed | `system.access.audit` (service = `marketplace`) | Leveraging shared datasets/providers | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | Yes |
| 1.10 | Cluster policies in use | `system.compute.clusters` (policy_id IS NOT NULL) | Governance structure exists for compute | [`platform-onboarding/compute-policies-and-standard-sizing.md`](../patterns/platform-onboarding/compute-policies-and-standard-sizing.md) | Yes |
| 1.11 | Billable products in use (breadth) | `system.billing.usage` (distinct `billing_origin_product` with usage) | How much of the platform is actually consumed, not just provisioned | [`platform-onboarding/platform-usage-profile.md`](../patterns/platform-onboarding/platform-usage-profile.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md) | No |
| 1.12 | Serverless share of compute DBUs | `system.billing.usage` (`product_features.is_serverless` / `sku_name` LIKE `%SERVERLESS%`) | Serverless compute is in use | [`platform-onboarding/serverless-first-compute.md`](../patterns/platform-onboarding/serverless-first-compute.md)<br>[`sql-analytics/serverless-sql-warehouses.md`](../patterns/sql-analytics/serverless-sql-warehouses.md) | No |
| 1.13 | Workspaces with active usage | `system.access.workspaces_latest` + `system.billing.usage` (distinct `workspace_id`) | The platform is used beyond a single sandbox workspace (e.g. dev / prod split) | [`platform-onboarding/environment-based-workspace-strategy.md`](../patterns/platform-onboarding/environment-based-workspace-strategy.md) | No |
| 1.14 | Bundle-deployed jobs and pipelines | `system.lakeflow.jobs` / `system.lakeflow.pipelines` (name has the bundle `[<target>]` prefix, `creator_id` is a service principal) | Declarative Automation Bundles (formerly DABs) / CI/CD deployment adopted | [`platform-onboarding/infrastructure-as-code-terraform-and-bundles.md`](../patterns/platform-onboarding/infrastructure-as-code-terraform-and-bundles.md)<br>[`platform-onboarding/git-backed-development-and-cicd.md`](../patterns/platform-onboarding/git-backed-development-and-cicd.md) | No |
| 1.15 | System tables enabled and queried | `SHOW SCHEMAS IN system` + `system.query.history` (statements referencing `system.`) | Observability built on system tables (cost, jobs, query dashboards and alerts) | [`platform-onboarding/observability-from-system-tables.md`](../patterns/platform-onboarding/observability-from-system-tables.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md) | No |
| 1.16 | Cost-attribution tags and budgets | `system.billing.usage` (`custom_tags` non-empty) + Budgets API / account console | FinOps controls (chargeback tags, budgets) are in use | [`platform-onboarding/cost-attribution-tagging-and-budgets.md`](../patterns/platform-onboarding/cost-attribution-tagging-and-budgets.md)<br>[`platform-onboarding/spend-trend-monitoring.md`](../patterns/platform-onboarding/spend-trend-monitoring.md)<br>[`unity-catalog-governance/tagging-strategy.md`](../patterns/unity-catalog-governance/tagging-strategy.md) | No |
| 1.17 | Databricks Apps deployed | `system.billing.usage` (`billing_origin_product` for Apps*) + Apps API | Data / AI applications are hosted on the platform | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | No |

---

## 2. SQL — Analytics & BI Adoption

Evidence that the client is leveraging SQL warehouses, building dashboards, and serving analytics to business users.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 2.1 | SQL warehouses provisioned (count, types) | `system.compute.warehouses` | SQL compute layer exists | [`sql-analytics/serverless-sql-warehouses.md`](../patterns/sql-analytics/serverless-sql-warehouses.md) | Yes |
| 2.2 | SQL warehouse active hours | `system.billing.usage` (SKU LIKE `%SQL%`) | Warehouses are actually being used | — | Yes |
| 2.3 | Total queries executed (last 30/60/90 days) | `system.query.history` | Query workload volume | — | Yes |
| 2.4 | Distinct users running queries | `system.query.history` (distinct `executed_by`) | Breadth of SQL user adoption | — | Yes |
| 2.5 | Lakeview dashboards created | `system.access.audit` (service = `dashboards`) | BI layer being built | [`sql-analytics/dashboards-on-governed-datasets.md`](../patterns/sql-analytics/dashboards-on-governed-datasets.md) | Yes |
| 2.6 | Saved queries (count and recency) | `system.access.audit` (action on saved queries) | Queries are being preserved, not ad-hoc only | — | Yes |
| 2.7 | Alerts configured | `system.access.audit` (service = `sql/alerts`) | Proactive monitoring on data | — | Yes |
| 2.8 | Genie spaces created | `system.access.audit` (service = `aibi`) | Natural-language analytics adopted | [`sql-analytics/curated-genie-spaces.md`](../patterns/sql-analytics/curated-genie-spaces.md) | Yes |
| 2.9 | Query types distribution (SELECT, MERGE, CREATE, etc.) | `system.query.history` (statement_type) | Mix of read vs. write activity | — | Yes |
| 2.10 | Materialized views and streaming tables in SQL | `information_schema.tables` (table_type) | Advanced SQL features adopted | [`sql-analytics/materialized-views-for-serving-layers.md`](../patterns/sql-analytics/materialized-views-for-serving-layers.md) | Yes |
| 2.11 | Federated / foreign tables present | `information_schema.tables` (table_type = `FOREIGN`) | Lakehouse Federation in use | [`sql-analytics/federation-for-ad-hoc-access.md`](../patterns/sql-analytics/federation-for-ad-hoc-access.md) | Yes |
| 2.12 | Parameterized queries / filters in dashboards | Dashboard dataset inspection | Interactive BI, not static reports | — | Proxy: dashboards updated in 90d, not parameterized dashboards |
| 2.13 | Genie usage volume | `system.query.history` (`query_source.genie_space_id` IS NOT NULL) | Business users are asking Genie questions, not just creating spaces (extends 2.8) | [`sql-analytics/curated-genie-spaces.md`](../patterns/sql-analytics/curated-genie-spaces.md) | No |
| 2.14 | Dashboard-driven query volume | `system.query.history` (`query_source.dashboard_id` IS NOT NULL) | Dashboards are being viewed and refreshed, not just built (extends 2.5) | [`sql-analytics/dashboards-on-governed-datasets.md`](../patterns/sql-analytics/dashboards-on-governed-datasets.md) | No |
| 2.15 | Metric views defined and queried | `information_schema.tables` (`table_type` = `METRIC_VIEW`) + `system.query.history` (`statement_text` contains `MEASURE(`) | A governed semantic layer has been adopted | [`sql-analytics/metric-views-as-semantic-layer.md`](../patterns/sql-analytics/metric-views-as-semantic-layer.md) | No |
| 2.16 | External BI / client tools connected | `system.query.history` (distinct `client_application` outside Databricks-native sources) | Warehouses serve the wider BI estate (Tableau, Power BI, etc.) | [`sql-analytics/third-party-bi-tool-integration.md`](../patterns/sql-analytics/third-party-bi-tool-integration.md) | No |
| 2.17 | Cost-per-query attribution in place | `information_schema.tables` (Labs cost-per-query MV or equivalent) / `system.access.table_lineage` (tables downstream of `system.query.history`) | Warehouse cost is allocated to queries, users, dashboards and tools | [`sql-analytics/cost-per-query-attribution.md`](../patterns/sql-analytics/cost-per-query-attribution.md) | No |

---

## 3. Data Engineering — ETL & Orchestration Adoption

Evidence that the client is building and running data pipelines, orchestrating workloads, and processing data at scale.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 3.1 | Jobs defined (total count) | `system.lakeflow.jobs` | Orchestration layer exists | — | Yes |
| 3.2 | Jobs actively running (last 30 days) | `system.lakeflow.job_run_timeline` | Jobs aren't just defined — they execute | — | Yes |
| 3.3 | Job run success/failure volume | `system.lakeflow.job_run_timeline` (result_state) | Workloads running at scale | — | Yes |
| 3.4 | Multi-task jobs vs. single-task | `system.lakeflow.job_tasks` | DAG-based orchestration adopted | [`orchestration-reliability/task-dependencies-over-schedule-chaining.md`](../patterns/orchestration-reliability/task-dependencies-over-schedule-chaining.md) | Yes |
| 3.5 | SDP pipelines defined (count) | `system.access.audit` (service = `deltaPipelines`) | Declarative pipeline layer exists | [`data-ingestion/autoloader-incremental-ingestion.md`](../patterns/data-ingestion/autoloader-incremental-ingestion.md) | Yes |
| 3.6 | SDP pipeline update frequency | Pipeline event logs | Pipelines actively refreshing data | — | Yes |
| 3.7 | Streaming workloads (structured streaming) | `system.billing.usage` (SKU contains streaming) or `system.query.history` | Real-time ingestion happening | [`data-ingestion/idempotent-ingestion-with-checkpoints.md`](../patterns/data-ingestion/idempotent-ingestion-with-checkpoints.md) | Yes |
| 3.8 | Delta table write operations (MERGE, UPDATE, DELETE) | `system.query.history` (statement_type IN MERGE, UPDATE, DELETE) | Active data transformation, not just reads | — | Yes |
| 3.9 | Tables with history > 1 version | `information_schema.tables` + DESCRIBE HISTORY sampling | Data is being iteratively processed | — | Proxy: tables altered in 90d, not tables with > 1 version |
| 3.10 | Scheduled jobs (cron-based) vs. manual triggers | Job configurations | Automation vs. manual execution | — | Yes |
| 3.11 | Task types used (notebook, Python, SQL, JAR, pipeline) | `system.lakeflow.job_tasks` (task_type) | Breadth of engineering workload types | — | Proxy: distinct job trigger types, not task types |
| 3.12 | Compute usage by Jobs SKU | `system.billing.usage` (SKU = `JOBS`, `JOBS_SERVERLESS`) | Engineering compute consumption | — | Yes |
| 3.13 | Auto Loader / Lakeflow Connect presence | Audit logs or notebook code patterns | Managed ingestion adopted | [`data-ingestion/autoloader-incremental-ingestion.md`](../patterns/data-ingestion/autoloader-incremental-ingestion.md)<br>[`data-ingestion/change-data-capture-ingestion.md`](../patterns/data-ingestion/change-data-capture-ingestion.md) | Yes |
| 3.14 | Workflow notifications configured | Job settings (email/webhook on failure) | Operational alerting in place | [`orchestration-reliability/failure-notifications-and-duration-thresholds.md`](../patterns/orchestration-reliability/failure-notifications-and-duration-thresholds.md) | Yes |
| 3.15 | Declared data quality rules | Pipeline event logs (expectations) + `system.information_schema.table_constraints` | Data quality is enforced in pipelines or tables | [`orchestration-reliability/pipeline-expectations-for-data-quality.md`](../patterns/orchestration-reliability/pipeline-expectations-for-data-quality.md) | No |
| 3.16 | Data quality monitoring enabled | `system.data_quality_monitoring.table_results` + monitor inventory | Freshness, anomaly or drift monitoring is running on tables | [`orchestration-reliability/sla-tracking-and-data-freshness.md`](../patterns/orchestration-reliability/sla-tracking-and-data-freshness.md)<br>[`platform-onboarding/observability-from-system-tables.md`](../patterns/platform-onboarding/observability-from-system-tables.md)<br>[`ml-ai-lifecycle/inference-tables-and-drift-monitoring.md`](../patterns/ml-ai-lifecycle/inference-tables-and-drift-monitoring.md) | No |
| 3.17 | Liquid clustering adopted | `DESCRIBE DETAIL` sampling of active tables (`clusteringColumns`) | Modern Delta table layout is in use | [`table-optimization/liquid-clustering-over-partitioning.md`](../patterns/table-optimization/liquid-clustering-over-partitioning.md) | No |
| 3.18 | Predictive optimization active | `system.storage.predictive_optimization_operations_history`* / metastore setting | Automated table maintenance (OPTIMIZE, VACUUM, ANALYZE) is running | [`table-optimization/predictive-optimization-autopilot.md`](../patterns/table-optimization/predictive-optimization-autopilot.md) | No |

---

## 4. AI/ML — Machine Learning & GenAI Adoption

Evidence that the client is training models, serving predictions, and leveraging generative AI capabilities.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 4.1 | MLflow experiments created | `system.access.audit` (service = `mlflow`) | Experiment tracking is happening | [`ml-ai-lifecycle/mlflow-experiment-tracking.md`](../patterns/ml-ai-lifecycle/mlflow-experiment-tracking.md) | Yes |
| 4.2 | MLflow runs logged (last 30/60/90 days) | `system.access.audit` (action = `createRun`) | Models are actively being trained | [`ml-ai-lifecycle/mlflow-experiment-tracking.md`](../patterns/ml-ai-lifecycle/mlflow-experiment-tracking.md) | Yes |
| 4.3 | Models registered in Unity Catalog | `system.access.audit` (service = `unityCatalog`, action on registered models) | Model governance in place | [`ml-ai-lifecycle/models-in-unity-catalog.md`](../patterns/ml-ai-lifecycle/models-in-unity-catalog.md) | Yes |
| 4.4 | Model versions created | UC model version metadata | Model iteration is happening | [`ml-ai-lifecycle/models-in-unity-catalog.md`](../patterns/ml-ai-lifecycle/models-in-unity-catalog.md) | Yes |
| 4.5 | Serving endpoints provisioned | `system.serving.served_entities` | Models being served for inference | [`ml-ai-lifecycle/production-serving-endpoint-configuration.md`](../patterns/ml-ai-lifecycle/production-serving-endpoint-configuration.md)<br>[`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | Yes |
| 4.6 | Serving endpoint traffic (request volume) | `system.serving.endpoint_usage` | Endpoints receiving actual traffic | [`ml-ai-lifecycle/production-serving-endpoint-configuration.md`](../patterns/ml-ai-lifecycle/production-serving-endpoint-configuration.md) | Yes |
| 4.7 | AI Gateway endpoints active | `system.ai_gateway.usage` | Governed LLM access is being used | [`ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md`](../patterns/ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md) | Yes |
| 4.8 | AI Gateway request/token volume | `system.ai_gateway.usage` (requests, tokens) | GenAI workloads at scale | [`ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md`](../patterns/ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md) | Yes |
| 4.9 | Distinct models/providers routed through Gateway | `system.ai_gateway.usage` (distinct `endpoint_name`, `destination_model`) | Breadth of GenAI model usage | [`ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md`](../patterns/ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md) | Yes |
| 4.10 | Feature tables present | `information_schema.tables` (table with feature-store metadata) | Feature engineering formalized | [`ml-ai-lifecycle/feature-store-for-consistent-features.md`](../patterns/ml-ai-lifecycle/feature-store-for-consistent-features.md) | Proxy: `featureStore` audit events, not feature tables present |
| 4.11 | Vector search indexes created | `system.access.audit` (service = `vectorSearch`) | RAG / semantic search adopted | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | Yes |
| 4.12 | Agent Bricks tiles defined | Tile inventory | Document processing / extraction automated | [`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | Proxy: Agent Bricks / AI function audit events, not tiles defined |
| 4.13 | Inference tables logging enabled | Serving endpoint configuration | Production predictions are logged | [`ml-ai-lifecycle/inference-tables-and-drift-monitoring.md`](../patterns/ml-ai-lifecycle/inference-tables-and-drift-monitoring.md) | Proxy: endpoints with served entities, not inference tables enabled |
| 4.14 | AI functions used in SQL (ai_query, ai_forecast, etc.) | `system.query.history` (statement text contains `ai_`) | SQL-native AI adoption | — | Yes |
| 4.15 | GPU cluster / ML compute usage | `system.billing.usage` (SKU contains `GPU` or `ML`) | Dedicated ML compute being consumed | — | Yes |
| 4.16 | GenAI tracing and evaluation activity | `system.mlflow.experiments_latest` / `system.mlflow.runs_latest` (evaluation runs, traces) | GenAI apps are traced and evaluated, not just deployed | [`ml-ai-lifecycle/genai-evaluation-and-human-feedback.md`](../patterns/ml-ai-lifecycle/genai-evaluation-and-human-feedback.md)<br>[`ml-ai-lifecycle/genai-readiness-foundations.md`](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | No |

---

## 5. Governance & Security — Unity Catalog Governance & Security Adoption

Evidence that the client has moved to Unity Catalog and uses its governance and security features: tags, classification, fine-grained access, non-human identities, and audit monitoring.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 5.1 | Unity Catalog adoption vs. Hive metastore | `SHOW CATALOGS` (`hive_metastore` inventory) + `system.query.history` / `system.access.table_lineage` (activity against `hive_metastore`) | Workloads have moved to Unity Catalog | [`unity-catalog-governance/legacy-hive-metastore-usage.md`](../patterns/unity-catalog-governance/legacy-hive-metastore-usage.md) | No |
| 5.2 | Tags applied to data objects | `system.information_schema.catalog_tags` / `schema_tags` / `table_tags` / `column_tags` | A tagging taxonomy is used on data | [`unity-catalog-governance/tagging-strategy.md`](../patterns/unity-catalog-governance/tagging-strategy.md) | No |
| 5.3 | Governed tags / data classification | Tag Policies API (governed tags) + `information_schema.column_tags` (`class.*` classification tags) | Sensitive-data classification is running | [`unity-catalog-governance/automated-pii-classification.md`](../patterns/unity-catalog-governance/automated-pii-classification.md)<br>[`unity-catalog-governance/abac-governed-tags.md`](../patterns/unity-catalog-governance/abac-governed-tags.md) | No |
| 5.4 | Row filters and column masks | `system.information_schema.row_filters` / `column_masks` | Fine-grained access control is in use | [`unity-catalog-governance/row-filters-and-column-masks.md`](../patterns/unity-catalog-governance/row-filters-and-column-masks.md) | No |
| 5.5 | ABAC policies defined | `SHOW POLICIES` / Policies API (per catalog and schema) | Tag-driven access policies are adopted | [`unity-catalog-governance/abac-governed-tags.md`](../patterns/unity-catalog-governance/abac-governed-tags.md) | No |
| 5.6 | Service principals running workloads | `system.lakeflow.jobs.run_as` / `system.lakeflow.pipelines.run_as` (application ID vs. email) | Automation runs under non-human identities | [`platform-onboarding/service-principals-for-automation.md`](../patterns/platform-onboarding/service-principals-for-automation.md) | No |
| 5.7 | Audit log actively monitored | `system.query.history` (statements referencing `system.access.audit`) + `system.alert` / Alerts API | Security events are being watched | [`security-compliance/security-audit-monitoring.md`](../patterns/security-compliance/security-audit-monitoring.md) | No |
| 5.8 | Security Analysis Tool running | `system.lakeflow.jobs` (SAT job names) + `system.lakeflow.job_run_timeline` | Security posture is assessed regularly | [`security-compliance/security-analysis-tool-baseline.md`](../patterns/security-compliance/security-analysis-tool-baseline.md) | No |

---

## 6. Data Sharing & Collaboration — Delta Sharing & Clean Rooms Adoption

Evidence that the client shares data in place with other teams or organisations, or consumes data shared with them. Marketplace consumption is already measured by check 1.9.

| # | Check | Evidence Source | What It Proves | Source pattern(s) | Implemented |
|---|-------|-----------------|----------------|-------------------|--------|
| 6.1 | Shares and recipients defined (provider) | `SHOW SHARES` / `SHOW RECIPIENTS` (Shares and Recipients APIs) | Delta Sharing is set up to share data out | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | No |
| 6.2 | Delta Sharing activity | `system.access.audit` (`action_name` IN `deltaSharingQueriedTable`, `deltaSharingQueriedTableChanges`) | Recipients are actually consuming shared data | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | No |
| 6.3 | Shared data consumed (recipient) | UC Catalogs API (catalogs of type `DELTASHARING_CATALOG`) + `system.billing.usage` (`DATA_SHARING`*) | The organisation consumes data shared by others | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | No |
| 6.4 | Clean rooms in use | Clean Rooms API + `system.billing.usage` (`billing_origin_product` for clean rooms*) | Privacy-safe multi-party collaboration is adopted | [`data-sharing/governed-data-sharing.md`](../patterns/data-sharing/governed-data-sharing.md) | No |

---

## Summary

| UI Section | Checks | Primary System Tables |
|------------|--------|-----------------------|
| Home / Workspace | 17 | `system.access.audit`, `system.compute.clusters`, `system.billing.usage`, `system.lakeflow.jobs` |
| SQL | 17 | `system.query.history`, `system.compute.warehouses`, `system.billing.usage` |
| Data Engineering | 18 | `system.lakeflow.jobs`, `system.lakeflow.job_run_timeline`, `system.query.history`, `system.data_quality_monitoring` |
| AI/ML | 16 | `system.ai_gateway.usage`, `system.serving.*`, `system.mlflow.*`, `system.access.audit` |
| Governance & Security | 8 | `system.information_schema.*` (tags, row filters, column masks), `system.lakeflow.jobs`, `system.query.history` |
| Data Sharing & Collaboration | 4 | `system.access.audit`, `system.billing.usage`, Shares / Recipients / Clean Rooms APIs |
| **Total** | **80** | |

---

## Scoring Framework

### Per-Check Scoring

Each of the 80 checks is scored on a **0–2 scale** based on evidence found:

| Score | Label | Definition |
|-------|-------|------------|
| 2 | **ACTIVE** | Clear, sustained evidence of adoption. Meets or exceeds the "Active" threshold. |
| 1 | **MINIMAL** | Some evidence exists but volume is low, sporadic, or concentrated in a single user/team. |
| 0 | **NONE** | No evidence found. The capability is unused. |

### Suggested Thresholds Per Check

#### Section 1: Home / Workspace

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 1.1 | Active users | 0 users in 90 days | 1–5 users in 90 days | > 5 users in 30 days |
| 1.2 | Users executing code | 0 | 1–3 users | > 3 users in 30 days |
| 1.3 | Notebooks created/modified | 0 in 90 days | 1–10 notebooks | > 10 notebooks in 30 days |
| 1.4 | Git folder / Repos usage | No repo events | < 5 repo actions in 90 days | > 5 repo actions in 30 days |
| 1.5 | Clusters created and hours | 0 clusters | < 100 cluster-hours in 90 days | > 100 cluster-hours in 30 days |
| 1.6 | UC objects created | 0 tables/schemas | 1–20 tables across 1 catalog | > 20 tables across 2+ catalogs |
| 1.7 | Workspace files | 0 non-notebook files | 1–10 files | > 10 .py/.sql/.yaml files |
| 1.8 | Secrets and token usage | 0 secret/token events | < 5 events in 90 days | > 5 events in 30 days |
| 1.9 | Marketplace consumed | 0 listings | 1 listing | > 1 listing |
| 1.10 | Cluster policies in use | 0 policies | 1 policy, < 50% clusters use it | > 1 policy, > 50% clusters governed |
| 1.11 | Billable products in use (breadth) | No usage | 1–3 products in 90 days | > 3 products with usage in 30 days |
| 1.12 | Serverless share of compute DBUs | 0% serverless | > 0–25% of DBUs in 30 days | > 25% of DBUs in 30 days |
| 1.13 | Workspaces with active usage | 0 workspaces with usage | 1 workspace with usage | ≥ 2 workspaces with usage in 30 days |
| 1.14 | Bundle-deployed jobs and pipelines | 0 bundle-deployed workloads | 1–5 bundle-deployed jobs/pipelines | > 5 bundle-deployed jobs/pipelines |
| 1.15 | System tables enabled and queried | Core schemas (`billing`, `access`, `compute`, `lakeflow`) not enabled or never queried | Enabled, ad-hoc queries only | Queried on a schedule (dashboard, alert or job) in 30 days |
| 1.16 | Cost-attribution tags and budgets | No tagged usage and no budgets | Some tagged usage or ≥ 1 budget | > 50% of DBUs tagged and ≥ 1 budget |
| 1.17 | Databricks Apps deployed | 0 apps | 1 app with usage in 90 days | > 1 app with usage in 30 days |

#### Section 2: SQL

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 2.1 | SQL warehouses provisioned | 0 | 1 warehouse | > 1 warehouse (or 1 serverless) |
| 2.2 | Warehouse active hours | 0 DBU | < 100 DBU in 90 days | > 100 DBU in 30 days |
| 2.3 | Total queries executed | 0 | 1–500 queries in 90 days | > 500 queries in 30 days |
| 2.4 | Distinct query users | 0 | 1–3 users | > 3 users in 30 days |
| 2.5 | Lakeview dashboards | 0 | 1–3 dashboards | > 3 dashboards |
| 2.6 | Saved queries | 0 | 1–10 queries | > 10 saved queries |
| 2.7 | Alerts configured | 0 | 1–2 alerts | > 2 alerts |
| 2.8 | Genie spaces created | 0 | 1 space | > 1 space |
| 2.9 | Query type distribution | Only SELECT | SELECT + 1 other type | 3+ distinct statement types |
| 2.10 | MVs and streaming tables | 0 | 1–2 MVs or streaming tables | > 2 MVs or streaming tables |
| 2.11 | Federated / foreign tables | 0 | 1–2 foreign tables | > 2 foreign tables |
| 2.12 | Parameterized dashboards | 0 | 1 dashboard with filters | > 1 dashboard with parameters |
| 2.13 | Genie usage volume | 0 Genie queries | 1–50 Genie queries in 90 days | > 50 Genie queries in 30 days |
| 2.14 | Dashboard-driven query volume | 0 dashboard queries | 1–100 in 90 days | > 100 in 30 days |
| 2.15 | Metric views defined and queried | 0 metric views | Metric views exist, not queried in 30 days | Metric views queried in 30 days |
| 2.16 | External BI / client tools connected | 0 external tools | 1 external tool | > 1 external tool in 30 days |
| 2.17 | Cost-per-query attribution in place | No allocation object | Exists, not refreshed or queried in 30 days | Refreshed and queried in 30 days |

#### Section 3: Data Engineering

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 3.1 | Jobs defined | 0 | 1–5 jobs | > 5 jobs |
| 3.2 | Jobs actively running | 0 runs in 30 days | 1–20 runs in 30 days | > 20 runs in 30 days |
| 3.3 | Run success/failure volume | 0 | < 50 completed runs in 90 days | > 50 completed runs in 30 days |
| 3.4 | Multi-task jobs | 0 | 1–2 multi-task jobs | > 2 multi-task jobs |
| 3.5 | SDP pipelines defined | 0 | 1 pipeline | > 1 pipeline |
| 3.6 | SDP update frequency | 0 updates | < 10 updates in 90 days | > 10 updates in 30 days |
| 3.7 | Streaming workloads | 0 | Any streaming DBU in 90 days | Sustained streaming over 30 days |
| 3.8 | Delta write operations | 0 | 1–50 MERGE/UPDATE/DELETE in 90 days | > 50 in 30 days |
| 3.9 | Tables with history > 1 ver. | 0 | 1–10 tables | > 10 tables with multi-version history |
| 3.10 | Scheduled vs. manual | 0 scheduled | < 50% of jobs scheduled | > 50% of jobs on a cron schedule |
| 3.11 | Task types used | 0 | 1–2 task types | 3+ distinct task types |
| 3.12 | Jobs SKU compute usage | 0 DBU | < 200 DBU in 90 days | > 200 DBU in 30 days |
| 3.13 | Auto Loader / Connect | No evidence | Evidence in 1 notebook/pipeline | Multiple ingestion sources |
| 3.14 | Notifications configured | 0 | < 50% of jobs have notifications | > 50% of jobs have notifications |
| 3.15 | Declared data quality rules | 0 pipelines with expectations and 0 constrained tables | 1–2 pipelines or tables | > 2 pipelines or tables |
| 3.16 | Data quality monitoring enabled | 0 monitored tables | 1–5 monitored tables | > 5 monitored tables with results in 30 days |
| 3.17 | Liquid clustering adopted | 0 clustered tables | 1–5 clustered tables | > 5 clustered tables |
| 3.18 | Predictive optimization active | Disabled, no operations | Operations in 90 days on 1 catalog | Operations in 30 days across 2+ catalogs |

#### Section 4: AI/ML

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 4.1 | MLflow experiments | 0 | 1–3 experiments | > 3 experiments |
| 4.2 | MLflow runs logged | 0 in 90 days | 1–10 runs in 90 days | > 10 runs in 30 days |
| 4.3 | Models registered in UC | 0 | 1–2 models | > 2 registered models |
| 4.4 | Model versions created | 0 | 1–3 versions total | > 3 versions (iterating) |
| 4.5 | Serving endpoints provisioned | 0 | 1 endpoint | > 1 endpoint |
| 4.6 | Serving endpoint traffic | 0 requests | < 100 requests in 90 days | > 100 requests in 30 days |
| 4.7 | AI Gateway endpoints active | 0 | 1 endpoint | > 1 endpoint |
| 4.8 | Gateway request/token volume | 0 | < 1,000 requests in 90 days | > 1,000 requests in 30 days |
| 4.9 | Distinct models via Gateway | 0 | 1 model/provider | > 1 model/provider |
| 4.10 | Feature tables present | 0 | 1–2 feature tables | > 2 feature tables |
| 4.11 | Vector search indexes | 0 | 1 index | > 1 index |
| 4.12 | Agent Bricks tiles | 0 | 1 tile | > 1 tile |
| 4.13 | Inference tables enabled | 0 | 1 endpoint with logging | > 1 endpoint with logging |
| 4.14 | AI functions in SQL | 0 queries | 1–5 queries with ai_ functions | > 5 queries in 30 days |
| 4.15 | GPU / ML compute usage | 0 DBU | < 50 GPU DBU in 90 days | > 50 GPU DBU in 30 days |
| 4.16 | GenAI tracing and evaluation activity | 0 evaluation runs | 1–5 evaluation runs in 90 days | > 5 evaluation runs in 30 days |

#### Section 5: Governance & Security

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 5.1 | Unity Catalog adoption vs. Hive metastore | Most table activity in `hive_metastore` | UC used, but `hive_metastore` read or written in 30 days | No `hive_metastore` activity in 30 days |
| 5.2 | Tags applied to data objects | 0 tagged objects | 1–20 tagged objects | > 20 tagged objects across 2+ catalogs |
| 5.3 | Governed tags / data classification | No governed tags, no classification tags | Governed tags defined or classification on 1 catalog | Classification tags on 2+ catalogs |
| 5.4 | Row filters and column masks | 0 tables | 1–5 tables protected | > 5 tables protected |
| 5.5 | ABAC policies defined | 0 policies | 1 policy | > 1 policy |
| 5.6 | Service principals running workloads | 0 jobs/pipelines as service principal | < 50% of active jobs/pipelines | ≥ 50% of jobs/pipelines active in 30 days |
| 5.7 | Audit log actively monitored | No queries on the audit log | Ad-hoc queries only in 90 days | Scheduled query, dashboard or alert on the audit log in 30 days |
| 5.8 | Security Analysis Tool running | Not installed | Installed, no successful run in 30 days | Successful run in 30 days |

#### Section 6: Data Sharing & Collaboration

| # | Check | NONE (0) | MINIMAL (1) | ACTIVE (2) |
|---|-------|----------|-------------|------------|
| 6.1 | Shares and recipients defined (provider) | 0 shares | 1 share | > 1 share with recipients |
| 6.2 | Delta Sharing activity | 0 events | < 50 events in 90 days | > 50 events in 30 days |
| 6.3 | Shared data consumed (recipient) | 0 shared catalogs | 1 shared catalog | > 1 shared catalog |
| 6.4 | Clean rooms in use | 0 clean rooms | 1 clean room | > 1 clean room |

---

### Section-Level Rollup

For each section, compute an **adoption score** as a percentage of the maximum possible:

```
Section Score = (Sum of check scores) / (Number of checks × 2) × 100
```

| Section | Max Points | Formula |
|---------|------------|---------|
| Home / Workspace | 34 | `sum(1.1–1.17) / 34 × 100` |
| SQL | 34 | `sum(2.1–2.17) / 34 × 100` |
| Data Engineering | 36 | `sum(3.1–3.18) / 36 × 100` |
| AI/ML | 32 | `sum(4.1–4.16) / 32 × 100` |
| Governance & Security | 16 | `sum(5.1–5.8) / 16 × 100` |
| Data Sharing & Collaboration | 8 | `sum(6.1–6.4) / 8 × 100` |

**Section Grade Bands:**

| Grade | Score Range | Interpretation |
|-------|------------|----------------|
| **STRONG** | 75–100% | The client is actively leveraging this area of the platform |
| **DEVELOPING** | 40–74% | Partial adoption — some capabilities used, significant gaps remain |
| **EARLY** | 10–39% | Initial exploration only — most capabilities untouched |
| **NOT ADOPTED** | 0–9% | No meaningful evidence of use |

---

### Overall Adoption Score

The overall score is a **weighted average** across sections, reflecting the typical progression of platform adoption (workspace and data engineering are foundational; SQL and AI/ML build on top):

| Section | Weight | Rationale |
|---------|--------|-----------|
| Home / Workspace | 25% | Foundation — must be adopted before anything else works |
| SQL | 15% | Analytics layer — often the entry point for business users |
| Data Engineering | 25% | Core value — production pipelines and orchestration |
| AI/ML | 15% | Advanced — typically adopted after data platform is stable |
| Governance & Security | 15% | Control layer — Unity Catalog governance and security features in use |
| Data Sharing & Collaboration | 5% | Situational — relevant only where data is exchanged across teams or organisations |

```
Overall Score = (Workspace Score × 0.25)
             + (SQL Score × 0.15)
             + (Data Engineering Score × 0.25)
             + (AI/ML Score × 0.15)
             + (Governance & Security Score × 0.15)
             + (Data Sharing & Collaboration Score × 0.05)
```

> Weights were rebalanced when sections 5 and 6 were added (previously 30 / 20 / 30 / 20 across sections 1–4). If a client has no data-sharing use case, you can mark section 6 N/A and spread its 5% proportionally across the other sections.

**Overall Grade Bands:**

| Grade | Score Range | Client Posture |
|-------|------------|----------------|
| **FULLY LEVERAGED** | 80–100% | Platform is a core part of the client's data stack |
| **BROADLY ADOPTED** | 60–79% | Strong adoption with room to expand into underused areas |
| **PARTIALLY ADOPTED** | 35–59% | Meaningful use in some areas, but significant platform value is untapped |
| **EARLY STAGE** | 10–34% | Proof-of-concept or single-team usage — not yet scaled |
| **NOT ADOPTED** | 0–9% | Essentially no platform utilization |

---

### Adoption Heatmap

Visualize results as a heatmap grid — each check is a cell, color-coded by score:

```
             1.1  1.2  1.3  ...  1.17
Workspace   [ ██ ][ ██ ][ ▓▓ ]  ...  [ ░░ ]

             2.1  2.2  2.3  ...  2.17
SQL         [ ██ ][ ██ ][ ██ ]  ...  [ ▓▓ ]

             3.1  3.2  3.3  ...  3.18
Data Eng    [ ██ ][ ██ ][ ██ ]  ...  [ ▓▓ ]

             4.1  4.2  4.3  ...  4.16
AI/ML       [ ░░ ][ ░░ ][ ░░ ]  ...  [ ░░ ]

             5.1  5.2  5.3  ...  5.8
Gov & Sec   [ ██ ][ ▓▓ ][ ░░ ]  ...  [ ░░ ]

             6.1  6.2  6.3  6.4
Sharing     [ ░░ ][ ░░ ][ ▓▓ ][ ░░ ]

Legend:  ██ = ACTIVE (2)    ▓▓ = MINIMAL (1)    ░░ = NONE (0)
```

---

### Trending Over Time

Run the assessment on a recurring schedule (monthly or quarterly) and track:

| Metric | Purpose |
|--------|---------|
| Overall score delta (MoM / QoQ) | Is the client adopting more of the platform over time? |
| Section score delta | Which areas are growing vs. stalling? |
| Checks that flipped NONE → MINIMAL or MINIMAL → ACTIVE | Newly adopted capabilities |
| Checks that regressed (ACTIVE → MINIMAL or MINIMAL → NONE) | Capabilities falling out of use |
| Number of NONE checks remaining | Shrinking backlog of untouched features |

Store each run's per-check scores in a Delta table for historical comparison:

```sql
CREATE TABLE IF NOT EXISTS assessment.results.adoption_check_history (
  run_id        STRING      COMMENT 'Unique run identifier',
  run_ts        TIMESTAMP   COMMENT 'When the adoption check ran',
  section       STRING      COMMENT 'UI section: Workspace | SQL | Data Engineering | AI/ML | Governance & Security | Data Sharing & Collaboration',
  check_id      STRING      COMMENT 'Check number (e.g., 1.1, 2.5, 4.12, 5.3)',
  check_name    STRING      COMMENT 'Human-readable check name',
  raw_value     DOUBLE      COMMENT 'Measured numeric value (e.g., count of users, DBU hours)',
  score         INT         COMMENT '0 = NONE, 1 = MINIMAL, 2 = ACTIVE',
  label         STRING      COMMENT 'NONE | MINIMAL | ACTIVE',
  detail        STRING      COMMENT 'Optional: supporting evidence or breakdown'
)
USING DELTA
COMMENT 'Per-check adoption scores, one row per check per run. Enables trending over time.'
```

---

## How to Use This Checklist

1. **Adoption vs. Quality**: These checks answer *"Is anyone using this?"* and *"How much?"* — a usage thermometer. Pair with maturity/anti-pattern assessments (e.g., the 78-pattern assessment framework) for implementation quality.
2. **Scoring**: Each check is scored 0 (NONE), 1 (MINIMAL), or 2 (ACTIVE) against the thresholds above.
3. **Rollup**: Section scores and an overall weighted score produce grades from NOT ADOPTED to FULLY LEVERAGED.
4. **Trending**: Run periodically (monthly/quarterly) and store results in `adoption_check_history` to track adoption growth.
5. **Client Conversations**: Use the heatmap and section grades to pinpoint underutilized areas and recommend targeted enablement.
6. **Traceability**: Each check added from the pattern library links back to its source pattern file(s) in [`extra_adoption_checks.md`](extra_adoption_checks.md). [`pattern-checkmap.md`](pattern-checkmap.md) maps every pattern area and file to a section here.
7. **Combined View**: Overlay adoption scores ("Are they using it?") with the 78-pattern maturity scores ("Are they using it well?") for a complete platform health picture.
