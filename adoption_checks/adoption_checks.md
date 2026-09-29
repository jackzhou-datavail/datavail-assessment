# Databricks Platform Adoption Baseline Checks

A structured checklist to determine whether a client is **actively using** each major area of the Databricks platform. These checks measure **adoption breadth and depth** — not implementation quality (which is covered separately by maturity/anti-pattern assessments).

---

## 1. Home / Workspace — General Platform Adoption

Evidence that the client has onboarded users, established compute governance, and is actively developing on the platform.

| # | Check | Evidence Source | What It Proves |
|---|-------|-----------------|----------------|
| 1.1 | Active users (last 30/60/90 days) | `system.access.audit` | People are logging in and working |
| 1.2 | Distinct users executing code (notebooks, REPL) | `system.access.audit` (action = `runCommand`) | Not just logging in — actually writing and running code |
| 1.3 | Notebooks created/modified | `system.access.audit` (action = `create`, `update` on notebooks) | Active development happening |
| 1.4 | Git folder / Repos usage | `system.access.audit` (service = `repos`) | Version control adoption |
| 1.5 | Clusters created and hours consumed | `system.compute.clusters` + `system.billing.usage` (SKU = `ALL_PURPOSE`) | Interactive compute is being used |
| 1.6 | Unity Catalog objects created (catalogs, schemas, tables) | `system.information_schema.tables` / `system.information_schema.schemata` | Data is being organized in UC |
| 1.7 | Workspace files (non-notebook assets — .py, .sql, .yaml) | `system.access.audit` (service = `workspace`, resource = `file`) | Using modular file-based development |
| 1.8 | Secrets and token usage | `system.access.audit` (service = `secrets`, `tokens`) | Integrations and automation being configured |
| 1.9 | Marketplace listings consumed | `system.access.audit` (service = `marketplace`) | Leveraging shared datasets/providers |
| 1.10 | Cluster policies in use | `system.compute.clusters` (policy_id IS NOT NULL) | Governance structure exists for compute |

---

## 2. SQL — Analytics & BI Adoption

Evidence that the client is leveraging SQL warehouses, building dashboards, and serving analytics to business users.

| # | Check | Evidence Source | What It Proves |
|---|-------|-----------------|----------------|
| 2.1 | SQL warehouses provisioned (count, types) | `system.compute.warehouses` | SQL compute layer exists |
| 2.2 | SQL warehouse active hours | `system.billing.usage` (SKU LIKE `%SQL%`) | Warehouses are actually being used |
| 2.3 | Total queries executed (last 30/60/90 days) | `system.query.history` | Query workload volume |
| 2.4 | Distinct users running queries | `system.query.history` (distinct `executed_by`) | Breadth of SQL user adoption |
| 2.5 | Lakeview dashboards created | `system.access.audit` (service = `dashboards`) | BI layer being built |
| 2.6 | Saved queries (count and recency) | `system.access.audit` (action on saved queries) | Queries are being preserved, not ad-hoc only |
| 2.7 | Alerts configured | `system.access.audit` (service = `sql/alerts`) | Proactive monitoring on data |
| 2.8 | Genie spaces created | `system.access.audit` (service = `aibi`) | Natural-language analytics adopted |
| 2.9 | Query types distribution (SELECT, MERGE, CREATE, etc.) | `system.query.history` (statement_type) | Mix of read vs. write activity |
| 2.10 | Materialized views and streaming tables in SQL | `information_schema.tables` (table_type) | Advanced SQL features adopted |
| 2.11 | Federated / foreign tables present | `information_schema.tables` (table_type = `FOREIGN`) | Lakehouse Federation in use |
| 2.12 | Parameterized queries / filters in dashboards | Dashboard dataset inspection | Interactive BI, not static reports |

---

## 3. Data Engineering — ETL & Orchestration Adoption

Evidence that the client is building and running data pipelines, orchestrating workloads, and processing data at scale.

| # | Check | Evidence Source | What It Proves |
|---|-------|-----------------|----------------|
| 3.1 | Jobs defined (total count) | `system.lakeflow.jobs` | Orchestration layer exists |
| 3.2 | Jobs actively running (last 30 days) | `system.lakeflow.job_run_timeline` | Jobs aren't just defined — they execute |
| 3.3 | Job run success/failure volume | `system.lakeflow.job_run_timeline` (result_state) | Workloads running at scale |
| 3.4 | Multi-task jobs vs. single-task | `system.lakeflow.job_tasks` | DAG-based orchestration adopted |
| 3.5 | SDP pipelines defined (count) | `system.access.audit` (service = `deltaPipelines`) | Declarative pipeline layer exists |
| 3.6 | SDP pipeline update frequency | Pipeline event logs | Pipelines actively refreshing data |
| 3.7 | Streaming workloads (structured streaming) | `system.billing.usage` (SKU contains streaming) or `system.query.history` | Real-time ingestion happening |
| 3.8 | Delta table write operations (MERGE, UPDATE, DELETE) | `system.query.history` (statement_type IN MERGE, UPDATE, DELETE) | Active data transformation, not just reads |
| 3.9 | Tables with history > 1 version | `information_schema.tables` + DESCRIBE HISTORY sampling | Data is being iteratively processed |
| 3.10 | Scheduled jobs (cron-based) vs. manual triggers | Job configurations | Automation vs. manual execution |
| 3.11 | Task types used (notebook, Python, SQL, JAR, pipeline) | `system.lakeflow.job_tasks` (task_type) | Breadth of engineering workload types |
| 3.12 | Compute usage by Jobs SKU | `system.billing.usage` (SKU = `JOBS`, `JOBS_SERVERLESS`) | Engineering compute consumption |
| 3.13 | Auto Loader / Lakeflow Connect presence | Audit logs or notebook code patterns | Managed ingestion adopted |
| 3.14 | Workflow notifications configured | Job settings (email/webhook on failure) | Operational alerting in place |

---

## 4. AI/ML — Machine Learning & GenAI Adoption

Evidence that the client is training models, serving predictions, and leveraging generative AI capabilities.

| # | Check | Evidence Source | What It Proves |
|---|-------|-----------------|----------------|
| 4.1 | MLflow experiments created | `system.access.audit` (service = `mlflow`) | Experiment tracking is happening |
| 4.2 | MLflow runs logged (last 30/60/90 days) | `system.access.audit` (action = `createRun`) | Models are actively being trained |
| 4.3 | Models registered in Unity Catalog | `system.access.audit` (service = `unityCatalog`, action on registered models) | Model governance in place |
| 4.4 | Model versions created | UC model version metadata | Model iteration is happening |
| 4.5 | Serving endpoints provisioned | `system.serving.served_entities` | Models being served for inference |
| 4.6 | Serving endpoint traffic (request volume) | `system.serving.endpoint_usage` | Endpoints receiving actual traffic |
| 4.7 | AI Gateway endpoints active | `system.ai.endpoint_usage` | Governed LLM access is being used |
| 4.8 | AI Gateway request/token volume | `system.ai.endpoint_usage` (total_requests, total_tokens) | GenAI workloads at scale |
| 4.9 | Distinct models/providers routed through Gateway | `system.ai.endpoint_usage` (distinct endpoint_name, model) | Breadth of GenAI model usage |
| 4.10 | Feature tables present | `information_schema.tables` (table with feature-store metadata) | Feature engineering formalized |
| 4.11 | Vector search indexes created | `system.access.audit` (service = `vectorSearch`) | RAG / semantic search adopted |
| 4.12 | Agent Bricks tiles defined | Tile inventory | Document processing / extraction automated |
| 4.13 | Inference tables logging enabled | Serving endpoint configuration | Production predictions are logged |
| 4.14 | AI functions used in SQL (ai_query, ai_forecast, etc.) | `system.query.history` (statement text contains `ai_`) | SQL-native AI adoption |
| 4.15 | GPU cluster / ML compute usage | `system.billing.usage` (SKU contains `GPU` or `ML`) | Dedicated ML compute being consumed |

---

## Summary

| UI Section | Checks | Primary System Tables |
|------------|--------|-----------------------|
| Home / Workspace | 10 | `system.access.audit`, `system.compute.clusters`, `system.billing.usage` |
| SQL | 12 | `system.query.history`, `system.compute.warehouses`, `system.billing.usage` |
| Data Engineering | 14 | `system.lakeflow.jobs`, `system.lakeflow.job_run_timeline`, `system.query.history` |
| AI/ML | 15 | `system.ai.endpoint_usage`, `system.serving.*`, `system.access.audit` |
| **Total** | **51** | |

---

## Scoring Framework

### Per-Check Scoring

Each of the 51 checks is scored on a **0–2 scale** based on evidence found:

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

---

### Section-Level Rollup

For each section, compute an **adoption score** as a percentage of the maximum possible:

```
Section Score = (Sum of check scores) / (Number of checks × 2) × 100
```

| Section | Max Points | Formula |
|---------|------------|---------|
| Home / Workspace | 20 | `sum(1.1–1.10) / 20 × 100` |
| SQL | 24 | `sum(2.1–2.12) / 24 × 100` |
| Data Engineering | 28 | `sum(3.1–3.14) / 28 × 100` |
| AI/ML | 30 | `sum(4.1–4.15) / 30 × 100` |

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
| Home / Workspace | 30% | Foundation — must be adopted before anything else works |
| SQL | 20% | Analytics layer — often the entry point for business users |
| Data Engineering | 30% | Core value — production pipelines and orchestration |
| AI/ML | 20% | Advanced — typically adopted after data platform is stable |

```
Overall Score = (Workspace Score × 0.30)
             + (SQL Score × 0.20)
             + (Data Engineering Score × 0.30)
             + (AI/ML Score × 0.20)
```

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
             1.1  1.2  1.3  1.4  1.5  1.6  1.7  1.8  1.9  1.10
Workspace   [ ██ ][ ██ ][ ▓▓ ][ ░░ ][ ██ ][ ██ ][ ▓▓ ][ ░░ ][ ░░ ][ ██ ]

             2.1  2.2  2.3  2.4  2.5  2.6  2.7  2.8  2.9  2.10 2.11 2.12
SQL         [ ██ ][ ██ ][ ██ ][ ▓▓ ][ ▓▓ ][ ░░ ][ ░░ ][ ░░ ][ ██ ][ ░░ ][ ░░ ][ ▓▓ ]

             3.1  3.2  3.3  ...  3.14
Data Eng    [ ██ ][ ██ ][ ██ ]  ...  [ ▓▓ ]

             4.1  4.2  4.3  ...  4.15
AI/ML       [ ░░ ][ ░░ ][ ░░ ]  ...  [ ░░ ]

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
  section       STRING      COMMENT 'UI section: Workspace | SQL | Data Engineering | AI/ML',
  check_id      STRING      COMMENT 'Check number (e.g., 1.1, 2.5, 4.12)',
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
6. **Combined View**: Overlay adoption scores ("Are they using it?") with the 78-pattern maturity scores ("Are they using it well?") for a complete platform health picture.
