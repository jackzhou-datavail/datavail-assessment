# Pattern Area → Adoption Check Category Map

Maps every area (immediate subfolder of `patterns/`) and every pattern file to a check category (a section of [`adoption_checks.md`](adoption_checks.md)). For each file it also shows whether the file gives **adoption evidence** (feeds a check) or only assesses **implementation quality**.

Reviewed 2026-09-29: 9 areas, 98 pattern files.

## Check categories

| # | Category | Status |
|---|----------|--------|
| 1 | Home / Workspace | Existing |
| 2 | SQL | Existing |
| 3 | Data Engineering | Existing |
| 4 | AI/ML | Existing |
| 5 | Governance & Security | **New.** Unity Catalog governance, security and identity had no home in sections 1–4 |
| 6 | Data Sharing & Collaboration | **New.** Delta Sharing, recipients and clean rooms fit none of sections 1–5 |

## Area mapping

| Area | Files | Check category | Adoption-evidence files | Rationale |
|------|------:|----------------|------------------------:|-----------|
| `data-ingestion` | 8 | Data Engineering | 3 | Ingestion pipelines (Auto Loader, Lakeflow Connect, CDC, streaming checkpoints) are Data Engineering workloads. |
| `data-sharing` | 2 | Data Sharing & Collaboration | 1 | Delta Sharing, recipients, clean rooms and Marketplace are cross-organisation collaboration, not SQL, DE or AI/ML usage. None of the four original sections fit, so a new **Data Sharing & Collaboration** section was added. |
| `ml-ai-lifecycle` | 16 | AI/ML | 8 | MLflow, model registry, serving, feature store, gateway and GenAI evaluation are all AI/ML. One check sourced here (Databricks Apps, 1.17) is filed under Home / Workspace because Apps are a general platform capability. |
| `orchestration-reliability` | 10 | Data Engineering | 4 | Jobs, task DAGs, retries, notifications, pipeline expectations and SLA monitoring belong to Data Engineering (Lakeflow Jobs / Declarative Pipelines). |
| `platform-onboarding` | 22 | Home / Workspace | 10 | Mixed area, so the files were reviewed individually. Most cover workspace setup, compute, CI/CD, FinOps and observability, which fit **Home / Workspace** (general platform adoption). Four identity files (account-first-identity-federation, service-principals-for-automation, personal-identity-in-production, workspace-object-permissions) map to **Governance & Security**. |
| `security-compliance` | 5 | Governance & Security | 3 | Secrets, CMK, compliance profile, SAT and audit monitoring have no home in the original four sections, so they go under a new **Governance & Security** section. Secret usage stays in existing check 1.8. |
| `sql-analytics` | 17 | SQL | 8 | Warehouses, dashboards, Genie, metric views, federation and BI tools are the SQL / AI-BI surface. The area also holds modelling and design patterns (medallion, documentation), which are quality-only. |
| `table-optimization` | 6 | Data Engineering | 2 | Delta table layout and maintenance (liquid clustering, predictive optimization, VACUUM, statistics) are part of running data pipelines, so they map to Data Engineering. |
| `unity-catalog-governance` | 12 | Governance & Security | 6 | Tags, classification, ABAC, row filters/masks, ownership, grants, lineage and Hive-metastore migration are governance. They map to the new **Governance & Security** section. Catalog organisation (domain-catalog-organization) is already measured by existing check 1.6. |

## File-level mapping

**Check category** is the category the file maps to. It differs from the area default only for the four `platform-onboarding` identity files. **Adoption checks** lists the check IDs in `adoption_checks.md` that the file provides evidence for. A dash means the file is quality-only; the reason is in [`extra_adoption_checks.md`](extra_adoption_checks.md#quality-only-pattern-files-53).

### `data-ingestion` → Data Engineering

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Auto Loader / Lakeflow Connect for Incremental Ingestion](../patterns/data-ingestion/autoloader-incremental-ingestion.md) | Pattern | Data Engineering | 3.5 (existing), 3.13 (existing) |
| [Bronze Layer Immutability (Append-Only Raw Landing)](../patterns/data-ingestion/bronze-layer-immutability.md) | Pattern | Data Engineering | — (quality) |
| [Change Data Capture (CDC) for Database Ingestion](../patterns/data-ingestion/change-data-capture-ingestion.md) | Pattern | Data Engineering | 3.13 (existing) |
| [Direct Writes to Bronze Tables](../patterns/data-ingestion/direct-writes-to-bronze-tables.md) | Anti-pattern | Data Engineering | — (quality) |
| [Full-Table Reload Instead of Incremental Ingestion](../patterns/data-ingestion/full-reload-instead-of-incremental.md) | Anti-pattern | Data Engineering | — (quality) |
| [Idempotent Ingestion via Structured Streaming Checkpoints](../patterns/data-ingestion/idempotent-ingestion-with-checkpoints.md) | Pattern | Data Engineering | 3.7 (existing) |
| [Missing Schema Enforcement / Evolution Handling](../patterns/data-ingestion/missing-schema-enforcement.md) | Anti-pattern | Data Engineering | — (quality) |
| [Small-File Accumulation at Landing](../patterns/data-ingestion/small-file-accumulation.md) | Anti-pattern | Data Engineering | — (quality; related 3.18) |

### `data-sharing` → Data Sharing & Collaboration

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Data Copies Instead of Sharing](../patterns/data-sharing/data-copies-instead-of-sharing.md) | Anti-pattern | Data Sharing & Collaboration | — (quality; related 6.3) |
| [Governed Data Sharing with Delta Sharing / OpenSharing](../patterns/data-sharing/governed-data-sharing.md) | Pattern | Data Sharing & Collaboration | 1.9 (existing), 6.1 (new), 6.2 (new), 6.3 (new), 6.4 (new) |

### `ml-ai-lifecycle` → AI/ML

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [CI/CD for ML Pipelines](../patterns/ml-ai-lifecycle/cicd-for-ml-pipelines.md) | Pattern | AI/ML | — (quality; related 1.14) |
| [Deploy Code, Not Models](../patterns/ml-ai-lifecycle/deploy-code-not-models.md) | Pattern | AI/ML | — (quality) |
| [Feature Store for Consistent Features](../patterns/ml-ai-lifecycle/feature-store-for-consistent-features.md) | Pattern | AI/ML | 4.10 (existing) |
| [Gateway Governance for LLM Endpoints](../patterns/ml-ai-lifecycle/gateway-governance-for-llm-endpoints.md) | Pattern | AI/ML | 4.7 (existing), 4.8 (existing), 4.9 (existing) |
| [GenAI Evaluation and Human Feedback](../patterns/ml-ai-lifecycle/genai-evaluation-and-human-feedback.md) | Pattern | AI/ML | 4.16 (new) |
| [GenAI Readiness Foundations](../patterns/ml-ai-lifecycle/genai-readiness-foundations.md) | Pattern | AI/ML | 1.11 (new), 1.17 (new), 4.5 (existing), 4.11 (existing), 4.12 (existing), 4.16 (new) |
| [Inference Tables and Drift Monitoring](../patterns/ml-ai-lifecycle/inference-tables-and-drift-monitoring.md) | Pattern | AI/ML | 3.16 (new), 4.13 (existing) |
| [Legacy Workspace Model Registry and Stages](../patterns/ml-ai-lifecycle/legacy-workspace-model-registry.md) | Anti-pattern | AI/ML | — (quality; related 4.3, 4.4) |
| [MLflow Experiment Tracking as the Default](../patterns/ml-ai-lifecycle/mlflow-experiment-tracking.md) | Pattern | AI/ML | 4.1 (existing), 4.2 (existing) |
| [Model Aliases for Deployment State](../patterns/ml-ai-lifecycle/model-aliases-for-deployment-state.md) | Pattern | AI/ML | — (quality; related 4.3, 4.4) |
| [Models in Unity Catalog](../patterns/ml-ai-lifecycle/models-in-unity-catalog.md) | Pattern | AI/ML | 4.3 (existing), 4.4 (existing) |
| [Production Serving Endpoint Configuration](../patterns/ml-ai-lifecycle/production-serving-endpoint-configuration.md) | Pattern | AI/ML | 4.5 (existing), 4.6 (existing) |
| [Stale Models in Production](../patterns/ml-ai-lifecycle/stale-models-in-production.md) | Anti-pattern | AI/ML | — (quality; related 4.5, 4.6) |
| [Training-Serving Skew](../patterns/ml-ai-lifecycle/training-serving-skew.md) | Anti-pattern | AI/ML | — (quality; related 4.10) |
| [Ungoverned External LLM Access](../patterns/ml-ai-lifecycle/ungoverned-external-llm-access.md) | Anti-pattern | AI/ML | — (quality; related 4.7, 4.8, 4.9) |
| [Untracked Model Development](../patterns/ml-ai-lifecycle/untracked-model-development.md) | Anti-pattern | AI/ML | — (quality; related 4.1, 4.2) |

### `orchestration-reliability` → Data Engineering

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Failure Notifications and Duration Thresholds](../patterns/orchestration-reliability/failure-notifications-and-duration-thresholds.md) | Pattern | Data Engineering | 3.14 (existing) |
| [Monolithic Single-Task Jobs](../patterns/orchestration-reliability/monolithic-single-task-jobs.md) | Anti-pattern | Data Engineering | — (quality; related 3.4) |
| [Pipeline Expectations for Data Quality](../patterns/orchestration-reliability/pipeline-expectations-for-data-quality.md) | Pattern | Data Engineering | 3.15 (new) |
| [Retries and Timeouts on Every Task](../patterns/orchestration-reliability/retries-and-timeouts-on-every-task.md) | Pattern | Data Engineering | — (quality) |
| [Schedule-Chained Jobs](../patterns/orchestration-reliability/schedule-chained-jobs.md) | Anti-pattern | Data Engineering | — (quality) |
| [Separate Ingestion and Transformation Pipelines](../patterns/orchestration-reliability/separate-ingestion-and-transformation-pipelines.md) | Pattern | Data Engineering | — (quality) |
| [Silent Job Failures](../patterns/orchestration-reliability/silent-job-failures.md) | Anti-pattern | Data Engineering | — (quality; related 3.14) |
| [SLA Tracking and Data Freshness](../patterns/orchestration-reliability/sla-tracking-and-data-freshness.md) | Pattern | Data Engineering | 3.16 (new) |
| [Task Dependencies Over Schedule Chaining](../patterns/orchestration-reliability/task-dependencies-over-schedule-chaining.md) | Pattern | Data Engineering | 3.4 (existing) |
| [Unbounded Task Execution](../patterns/orchestration-reliability/unbounded-task-execution.md) | Anti-pattern | Data Engineering | — (quality) |

### `platform-onboarding` → Home / Workspace

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Account-First Identity Federation](../patterns/platform-onboarding/account-first-identity-federation.md) | Pattern | Governance & Security | — (quality; related 5.6) |
| [All-Purpose Compute for Scheduled Jobs](../patterns/platform-onboarding/all-purpose-compute-for-jobs.md) | Anti-pattern | Home / Workspace | — (quality) |
| [Compute Policies and Standard Sizing](../patterns/platform-onboarding/compute-policies-and-standard-sizing.md) | Pattern | Home / Workspace | 1.10 (existing) |
| [Compute Right-Sizing from Utilization Data](../patterns/platform-onboarding/compute-right-sizing.md) | Pattern | Home / Workspace | — (quality) |
| [Cost Attribution Tagging and Budgets](../patterns/platform-onboarding/cost-attribution-tagging-and-budgets.md) | Pattern | Home / Workspace | 1.16 (new) |
| [Disaster Recovery Strategy with Tested RPO/RTO](../patterns/platform-onboarding/disaster-recovery-strategy.md) | Pattern | Home / Workspace | — (quality) |
| [Environment-Based Workspace Strategy](../patterns/platform-onboarding/environment-based-workspace-strategy.md) | Pattern | Home / Workspace | 1.13 (new) |
| [Git-Backed Development and CI/CD](../patterns/platform-onboarding/git-backed-development-and-cicd.md) | Pattern | Home / Workspace | 1.4 (existing), 1.14 (new) |
| [Infrastructure as Code: Terraform for Platform, Bundles for Workloads](../patterns/platform-onboarding/infrastructure-as-code-terraform-and-bundles.md) | Pattern | Home / Workspace | 1.14 (new) |
| [Manually Configured "Snowflake" Workspaces](../patterns/platform-onboarding/manually-configured-workspaces.md) | Anti-pattern | Home / Workspace | — (quality; related 1.14) |
| [Misconfigured Classic Compute](../patterns/platform-onboarding/misconfigured-classic-compute.md) | Anti-pattern | Home / Workspace | — (quality) |
| [Notebooks as Production Code](../patterns/platform-onboarding/notebooks-as-production-code.md) | Anti-pattern | Home / Workspace | — (quality; related 1.4) |
| [Observability from System Tables](../patterns/platform-onboarding/observability-from-system-tables.md) | Pattern | Home / Workspace | 1.15 (new), 3.16 (new) |
| [Personal Identities and Hardcoded Credentials in Production](../patterns/platform-onboarding/personal-identity-in-production.md) | Anti-pattern | Governance & Security | — (quality; related 5.6) |
| [Phased Deployment Planning Before Provisioning](../patterns/platform-onboarding/phased-deployment-planning.md) | Pattern | Home / Workspace | — (quality) |
| [Platform Usage Profile from Billing Data](../patterns/platform-onboarding/platform-usage-profile.md) | Pattern | Home / Workspace | 1.11 (new) |
| [Serverless-First Compute](../patterns/platform-onboarding/serverless-first-compute.md) | Pattern | Home / Workspace | 1.12 (new) |
| [Service Principals for Automation](../patterns/platform-onboarding/service-principals-for-automation.md) | Pattern | Governance & Security | 5.6 (new) |
| [Spend Trend Monitoring](../patterns/platform-onboarding/spend-trend-monitoring.md) | Pattern | Home / Workspace | 1.11 (new), 1.15 (new), 1.16 (new) |
| [Untagged, Unmonitored Spend](../patterns/platform-onboarding/untagged-unmonitored-spend.md) | Anti-pattern | Home / Workspace | — (quality; related 1.16) |
| [Group-Based Permissions on Workspace Resources](../patterns/platform-onboarding/workspace-object-permissions.md) | Pattern | Governance & Security | — (quality) |
| [Workspace Sprawl](../patterns/platform-onboarding/workspace-sprawl.md) | Anti-pattern | Home / Workspace | — (quality; related 1.13) |

### `security-compliance` → Governance & Security

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Compliance Security Profile for Regulated Workloads](../patterns/security-compliance/compliance-security-profile.md) | Pattern | Governance & Security | — (quality) |
| [Customer-Managed Keys for Encryption](../patterns/security-compliance/customer-managed-keys.md) | Pattern | Governance & Security | — (quality) |
| [Secrets Managed in Secret Scopes or Unity Catalog](../patterns/security-compliance/secrets-management.md) | Pattern | Governance & Security | 1.8 (existing) |
| [Security Posture Baseline with the Security Analysis Tool](../patterns/security-compliance/security-analysis-tool-baseline.md) | Pattern | Governance & Security | 5.8 (new) |
| [Security Audit Log Monitoring and Alerting](../patterns/security-compliance/security-audit-monitoring.md) | Pattern | Governance & Security | 5.7 (new) |

### `sql-analytics` → SQL

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Always-On, Oversized Warehouses](../patterns/sql-analytics/always-on-oversized-warehouses.md) | Anti-pattern | SQL | — (quality; related 2.1) |
| [Analytics on Raw Tables](../patterns/sql-analytics/analytics-on-raw-tables.md) | Anti-pattern | SQL | — (quality) |
| [Cost per Query Attribution](../patterns/sql-analytics/cost-per-query-attribution.md) | Pattern | SQL | 2.17 (new) |
| [Curated Genie Spaces](../patterns/sql-analytics/curated-genie-spaces.md) | Pattern | SQL | 2.8 (existing), 2.13 (new) |
| [Dashboards on Governed Datasets](../patterns/sql-analytics/dashboards-on-governed-datasets.md) | Pattern | SQL | 2.5 (existing), 2.14 (new) |
| [Documented Tables and Columns](../patterns/sql-analytics/documented-tables-and-columns.md) | Pattern | SQL | — (quality) |
| [Duplicated Metric Definitions](../patterns/sql-analytics/duplicated-metric-definitions.md) | Anti-pattern | SQL | — (quality; related 2.15) |
| [Federated Queries in Production Pipelines](../patterns/sql-analytics/federated-queries-in-production-pipelines.md) | Anti-pattern | SQL | — (quality; related 2.11) |
| [Lakehouse Federation for Ad-Hoc Access](../patterns/sql-analytics/federation-for-ad-hoc-access.md) | Pattern | SQL | 2.11 (existing) |
| [Materialized Views for Serving Layers](../patterns/sql-analytics/materialized-views-for-serving-layers.md) | Pattern | SQL | 2.10 (existing) |
| [Medallion Layering for Analytics](../patterns/sql-analytics/medallion-layering-for-analytics.md) | Pattern | SQL | — (quality) |
| [Metric Views as the Semantic Layer](../patterns/sql-analytics/metric-views-as-semantic-layer.md) | Pattern | SQL | 2.15 (new) |
| [Query Performance Fundamentals](../patterns/sql-analytics/query-performance-fundamentals.md) | Pattern | SQL | — (quality) |
| [Scheduled Snapshot Rebuilds](../patterns/sql-analytics/scheduled-snapshot-rebuilds.md) | Anti-pattern | SQL | — (quality) |
| [Serverless SQL Warehouses, Sized Down Not Up](../patterns/sql-analytics/serverless-sql-warehouses.md) | Pattern | SQL | 1.12 (new), 2.1 (existing) |
| [Sprawling Genie Spaces](../patterns/sql-analytics/sprawling-genie-spaces.md) | Anti-pattern | SQL | — (quality; related 2.13) |
| [Third-Party BI Tools on Governed Semantics](../patterns/sql-analytics/third-party-bi-tool-integration.md) | Pattern | SQL | 2.16 (new) |

### `table-optimization` → Data Engineering

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Deletion Vectors for Fast UPDATE / DELETE / MERGE](../patterns/table-optimization/deletion-vectors-for-fast-dml.md) | Pattern | Data Engineering | — (quality) |
| [Liquid Clustering Instead of Manual Partitioning / Z-ORDER](../patterns/table-optimization/liquid-clustering-over-partitioning.md) | Pattern | Data Engineering | 3.17 (new) |
| [Over-Partitioning](../patterns/table-optimization/over-partitioning.md) | Anti-pattern | Data Engineering | — (quality; related 3.17) |
| [Predictive Optimization for Table Maintenance](../patterns/table-optimization/predictive-optimization-autopilot.md) | Pattern | Data Engineering | 3.18 (new) |
| [Stale or Missing Table Statistics](../patterns/table-optimization/stale-table-statistics.md) | Anti-pattern | Data Engineering | — (quality; related 3.18) |
| [Unmanaged VACUUM Retention](../patterns/table-optimization/unmanaged-vacuum-retention.md) | Anti-pattern | Data Engineering | — (quality; related 3.18) |

### `unity-catalog-governance` → Governance & Security

| Pattern file | Type | Check category | Adoption checks |
|--------------|------|----------------|-----------------|
| [Attribute-Based Access Control (ABAC) with Governed Tags](../patterns/unity-catalog-governance/abac-governed-tags.md) | Pattern | Governance & Security | 5.3 (new), 5.5 (new) |
| [Automated Sensitive-Data Classification](../patterns/unity-catalog-governance/automated-pii-classification.md) | Pattern | Governance & Security | 5.3 (new) |
| [Explicit Data Retention Policies](../patterns/unity-catalog-governance/data-retention-policies.md) | Pattern | Governance & Security | — (quality) |
| [Catalogs as the Primary Unit of Isolation](../patterns/unity-catalog-governance/domain-catalog-organization.md) | Pattern | Governance & Security | 1.6 (existing) |
| [Group-Based Access Control & Ownership](../patterns/unity-catalog-governance/group-based-access-control.md) | Pattern | Governance & Security | — (quality) |
| [Direct Grants to Individual Users](../patterns/unity-catalog-governance/individual-user-grants.md) | Anti-pattern | Governance & Security | — (quality) |
| [Continued Use of the Legacy Hive Metastore](../patterns/unity-catalog-governance/legacy-hive-metastore-usage.md) | Anti-pattern | Governance & Security | 5.1 (new) |
| [Lineage & Audit Logging via System Tables](../patterns/unity-catalog-governance/lineage-and-audit-via-system-tables.md) | Pattern | Governance & Security | — (quality; related 5.7) |
| [Fine-Grained Access with Row Filters and Column Masks](../patterns/unity-catalog-governance/row-filters-and-column-masks.md) | Pattern | Governance & Security | 5.4 (new) |
| [A Single Tagging Strategy Across Data and Compute](../patterns/unity-catalog-governance/tagging-strategy.md) | Pattern | Governance & Security | 1.16 (new), 5.2 (new) |
| [Unclassified Sensitive Data](../patterns/unity-catalog-governance/unclassified-sensitive-data.md) | Anti-pattern | Governance & Security | — (quality; related 5.3) |
| [Unowned / Never-Reassigned Catalog Objects](../patterns/unity-catalog-governance/unowned-catalog-objects.md) | Anti-pattern | Governance & Security | — (quality) |
