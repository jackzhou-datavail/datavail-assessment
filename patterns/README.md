# Databricks Patterns & Anti-Patterns

A reference library of Databricks platform patterns (things to do) and
anti-patterns (things to avoid), one file per pattern. Anti-patterns are
flagged with a `> ⚠️ **ANTI-PATTERN**` line immediately after the title so
they're unmistakable at a glance.

Each entry includes a **How to detect** section naming the concrete signal
— usually a `system.*` table and the columns that carry it — so the library
doubles as a source of assessment checks for a real workspace. Where a
signal isn't observable from system tables (account-level settings, Git
linkage, secrets in code), the section says so and names the API or scan
that does reach it, rather than implying a query exists.

Content is verified against current Databricks documentation (linked in
each file's References section) as of 2026-09, not written from memory
alone — see individual files for exact source quotes.

## Categories

- **[Platform Onboarding](platform-onboarding/)** — standing up and running
  the Databricks platform itself: account, workspaces, compute, IaC, cost
  - [Phased deployment planning before provisioning](platform-onboarding/phased-deployment-planning.md)
  - [Account-first identity federation](platform-onboarding/account-first-identity-federation.md)
  - [Environment-based workspace strategy](platform-onboarding/environment-based-workspace-strategy.md)
  - [Serverless-first compute](platform-onboarding/serverless-first-compute.md)
  - [Compute policies and standard sizing](platform-onboarding/compute-policies-and-standard-sizing.md)
  - [IaC: Terraform for platform, bundles for workloads](platform-onboarding/infrastructure-as-code-terraform-and-bundles.md)
  - [Git-backed development and CI/CD](platform-onboarding/git-backed-development-and-cicd.md)
  - [Service principals for automation](platform-onboarding/service-principals-for-automation.md)
  - [Cost attribution tagging and budgets](platform-onboarding/cost-attribution-tagging-and-budgets.md)
  - [Observability from system tables](platform-onboarding/observability-from-system-tables.md)
  - [Workspace sprawl](platform-onboarding/workspace-sprawl.md) — ⚠️ anti-pattern
  - [Manually configured "snowflake" workspaces](platform-onboarding/manually-configured-workspaces.md) — ⚠️ anti-pattern
  - [All-purpose compute for scheduled jobs](platform-onboarding/all-purpose-compute-for-jobs.md) — ⚠️ anti-pattern
  - [Notebooks as production code](platform-onboarding/notebooks-as-production-code.md) — ⚠️ anti-pattern
  - [Personal identities & hardcoded credentials in production](platform-onboarding/personal-identity-in-production.md) — ⚠️ anti-pattern
  - [Untagged, unmonitored spend](platform-onboarding/untagged-unmonitored-spend.md) — ⚠️ anti-pattern

- **[Orchestration & Reliability](orchestration-reliability/)** — how work is
  scheduled, how it fails, and how it recovers
  - [Task dependencies over schedule chaining](orchestration-reliability/task-dependencies-over-schedule-chaining.md)
  - [Retries and timeouts on every task](orchestration-reliability/retries-and-timeouts-on-every-task.md)
  - [Failure notifications and duration thresholds](orchestration-reliability/failure-notifications-and-duration-thresholds.md)
  - [Separate ingestion and transformation pipelines](orchestration-reliability/separate-ingestion-and-transformation-pipelines.md)
  - [Pipeline expectations for data quality](orchestration-reliability/pipeline-expectations-for-data-quality.md)
  - [Schedule-chained jobs](orchestration-reliability/schedule-chained-jobs.md) — ⚠️ anti-pattern
  - [Silent job failures](orchestration-reliability/silent-job-failures.md) — ⚠️ anti-pattern
  - [Monolithic single-task jobs](orchestration-reliability/monolithic-single-task-jobs.md) — ⚠️ anti-pattern
  - [Unbounded task execution](orchestration-reliability/unbounded-task-execution.md) — ⚠️ anti-pattern

- **[SQL & Analytics](sql-analytics/)** — warehouses, modeling for consumption,
  dashboards, Genie, and query performance
  - [Serverless SQL warehouses, sized down not up](sql-analytics/serverless-sql-warehouses.md)
  - [Medallion layering for analytics](sql-analytics/medallion-layering-for-analytics.md)
  - [Materialized views for serving layers](sql-analytics/materialized-views-for-serving-layers.md)
  - [Metric views as the semantic layer](sql-analytics/metric-views-as-semantic-layer.md)
  - [Documented tables and columns](sql-analytics/documented-tables-and-columns.md)
  - [Curated Genie spaces](sql-analytics/curated-genie-spaces.md)
  - [Dashboards on governed datasets](sql-analytics/dashboards-on-governed-datasets.md)
  - [Query performance fundamentals](sql-analytics/query-performance-fundamentals.md)
  - [Lakehouse Federation for ad-hoc access](sql-analytics/federation-for-ad-hoc-access.md)
  - [Always-on, oversized warehouses](sql-analytics/always-on-oversized-warehouses.md) — ⚠️ anti-pattern
  - [Duplicated metric definitions](sql-analytics/duplicated-metric-definitions.md) — ⚠️ anti-pattern
  - [Analytics on raw tables](sql-analytics/analytics-on-raw-tables.md) — ⚠️ anti-pattern
  - [Sprawling Genie spaces](sql-analytics/sprawling-genie-spaces.md) — ⚠️ anti-pattern
  - [Scheduled snapshot rebuilds](sql-analytics/scheduled-snapshot-rebuilds.md) — ⚠️ anti-pattern
  - [Federated queries in production pipelines](sql-analytics/federated-queries-in-production-pipelines.md) — ⚠️ anti-pattern

- **[ML & AI Lifecycle](ml-ai-lifecycle/)** — developing, governing, serving,
  and monitoring models and GenAI applications
  - [Deploy code, not models](ml-ai-lifecycle/deploy-code-not-models.md)
  - [Models in Unity Catalog](ml-ai-lifecycle/models-in-unity-catalog.md)
  - [Model aliases for deployment state](ml-ai-lifecycle/model-aliases-for-deployment-state.md)
  - [MLflow experiment tracking as the default](ml-ai-lifecycle/mlflow-experiment-tracking.md)
  - [Feature Store for consistent features](ml-ai-lifecycle/feature-store-for-consistent-features.md)
  - [Inference tables and drift monitoring](ml-ai-lifecycle/inference-tables-and-drift-monitoring.md)
  - [CI/CD for ML pipelines](ml-ai-lifecycle/cicd-for-ml-pipelines.md)
  - [Production serving endpoint configuration](ml-ai-lifecycle/production-serving-endpoint-configuration.md)
  - [Gateway governance for LLM endpoints](ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md)
  - [GenAI evaluation and human feedback](ml-ai-lifecycle/genai-evaluation-and-human-feedback.md)
  - [Legacy workspace model registry and stages](ml-ai-lifecycle/legacy-workspace-model-registry.md) — ⚠️ anti-pattern
  - [Untracked model development](ml-ai-lifecycle/untracked-model-development.md) — ⚠️ anti-pattern
  - [Training-serving skew](ml-ai-lifecycle/training-serving-skew.md) — ⚠️ anti-pattern
  - [Stale models in production](ml-ai-lifecycle/stale-models-in-production.md) — ⚠️ anti-pattern
  - [Ungoverned external LLM access](ml-ai-lifecycle/ungoverned-external-llm-access.md) — ⚠️ anti-pattern

- **[Data Ingestion](data-ingestion/)** — landing raw data into the lakehouse
  - [Auto Loader / Lakeflow Connect for incremental ingestion](data-ingestion/autoloader-incremental-ingestion.md)
  - [Idempotent ingestion via Structured Streaming checkpoints](data-ingestion/idempotent-ingestion-with-checkpoints.md)
  - [Bronze layer immutability](data-ingestion/bronze-layer-immutability.md)
  - [Change data capture (CDC) for database ingestion](data-ingestion/change-data-capture-ingestion.md)
  - [Direct writes to bronze tables](data-ingestion/direct-writes-to-bronze-tables.md) — ⚠️ anti-pattern
  - [Full-table reload instead of incremental](data-ingestion/full-reload-instead-of-incremental.md) — ⚠️ anti-pattern
  - [Missing schema enforcement / evolution handling](data-ingestion/missing-schema-enforcement.md) — ⚠️ anti-pattern
  - [Small-file accumulation at landing](data-ingestion/small-file-accumulation.md) — ⚠️ anti-pattern

- **[Unity Catalog Governance](unity-catalog-governance/)** — organizing, securing, and auditing data in UC
  - [Catalogs as the primary unit of isolation](unity-catalog-governance/domain-catalog-organization.md)
  - [Group-based access control & ownership](unity-catalog-governance/group-based-access-control.md)
  - [ABAC with governed tags](unity-catalog-governance/abac-governed-tags.md)
  - [Automated sensitive-data classification](unity-catalog-governance/automated-pii-classification.md)
  - [Lineage & audit logging via system tables](unity-catalog-governance/lineage-and-audit-via-system-tables.md)
  - [Direct grants to individual users](unity-catalog-governance/individual-user-grants.md) — ⚠️ anti-pattern
  - [Continued use of the legacy Hive metastore](unity-catalog-governance/legacy-hive-metastore-usage.md) — ⚠️ anti-pattern
  - [Unowned / never-reassigned catalog objects](unity-catalog-governance/unowned-catalog-objects.md) — ⚠️ anti-pattern
  - [Unclassified sensitive data](unity-catalog-governance/unclassified-sensitive-data.md) — ⚠️ anti-pattern

- **[Table Optimization](table-optimization/)** — Delta table layout and maintenance
  - [Liquid clustering instead of manual partitioning/Z-ORDER](table-optimization/liquid-clustering-over-partitioning.md)
  - [Predictive optimization for table maintenance](table-optimization/predictive-optimization-autopilot.md)
  - [Deletion vectors for fast UPDATE/DELETE/MERGE](table-optimization/deletion-vectors-for-fast-dml.md)
  - [Over-partitioning](table-optimization/over-partitioning.md) — ⚠️ anti-pattern
  - [Unmanaged VACUUM retention](table-optimization/unmanaged-vacuum-retention.md) — ⚠️ anti-pattern
  - [Stale or missing table statistics](table-optimization/stale-table-statistics.md) — ⚠️ anti-pattern

## File template

```markdown
# <Pattern Name>

> ⚠️ **ANTI-PATTERN**   <!-- omit this line entirely for a positive pattern -->

**Category:** <category>

<one- or two-sentence summary>

## Why it matters
## What good looks like        <!-- positive patterns -->
## Why it happens / How to fix  <!-- anti-patterns -->
## How to detect
## References
```
