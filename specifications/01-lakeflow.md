# Lakeflow — Data Generation + Gold Table Chain

> **Simple-demo contract.** One self-contained data-generation script produces all layers: raw workspace-metadata simulation tables and gold tables the dashboard + Genie read. **No SDP** — all transformations run as inline SQL in the generation script. Lineage visible in Catalog Explorer. Talking track: *"in production, these tables come directly from Unity Catalog system tables — `system.access.audit`, `system.lakeflow.job_run_timeline`, `system.lineage.table_lineage` — via Lakeflow Connect. Here the data-gen does the equivalent layering inline."*

---

## Shared Context

**Catalog / Schema**: `<catalog>.<schema>` (the target catalog/schema passed at deploy time)

**Story anchor — the single biggest signal in the data:**
- `raw_transactions` (a bronze table) has **47 direct DML writes** in 90 days — the tallest bar on the ETL Hygiene chart and the one Genie leads with.
- 14 total bronze tables have direct edits — these are the critical finding.
- 3 of those bronze tables feed gold tables that power weekly executive reports (the $87K/year rerun cost finding).

**Health scores (must match dashboard KPI tiles exactly):**

| Dimension | Score |
|---|---|
| Overall | 68 |
| ETL Hygiene | 55 |
| ML/AI Governance | 62 |
| Ownership & Access | 71 |
| Data Quality | 78 |

**Time anchors**: `REPORT_DATE = NOW` (rolling). Audit history covers `NOW − 90 days` → `NOW`. Ownership coverage trend covers `NOW − 30 days` → `NOW`. `BASELINE_DATE = NOW − 30 days` used for score delta comparisons (overall was 71 at baseline).

---

## A. Data Generation Script

**Skill**: `databricks-synthetic-data-gen` — read `SKILLS/databricks-synthetic-data-gen/SKILL.md` first.

**Runtime**: pre-provisioned databricks-connect venv. Do NOT create a new venv.

One idempotent Python script. All tables written to `<catalog>.<schema>`. Script is structured in three sections:

1. **Raw tables** — workspace metadata simulation (tables, pipelines, jobs, job runs, audit events, ML assets)
2. **Intermediate aggregations** — pre-compute derived signals needed for gold (inline `spark.sql`)
3. **Gold tables** — the final tables the dashboard and Genie read (inline `spark.sql` CTAS)

---

## B. Raw Tables (source simulation)

### `raw_ws_tables` — ~200 rows

Simulates `system.unity_catalog.tables` + custom property tags.

| Column | Type | Notes |
|---|---|---|
| `table_id` | STRING PK | `TBL-NNNNNN` |
| `table_name` | STRING | e.g. `raw_transactions`, `silver_customer_events`, `gold_revenue_summary` |
| `catalog_name` | STRING | `main` (90%) or `analytics` (10%) |
| `schema_name` | STRING | ends in `_bronze`, `_silver`, or `_gold` matching `data_layer` |
| `data_layer` | STRING | `bronze` / `silver` / `gold` — 40 bronze, 80 silver, 80 gold |
| `owner_email` | STRING | nullable for 22% of rows (these are the orphaned tables) |
| `has_owner_tag` | BOOLEAN | TRUE if `owner_email` non-null AND a UC tag `owner` is set |
| `created_at` | TIMESTAMP | spread across 18 months |
| `last_ddl_at` | TIMESTAMP | last schema change |
| `table_comment` | STRING | nullable — 40% of bronze tables lack a comment (naming governance finding) |
| `naming_violation` | BOOLEAN | TRUE if table name doesn't follow `{layer}_{domain}_{entity}` convention; ~35% of all tables |
| `row_count_approx` | BIGINT | synthetic order-of-magnitude count |

**Key constraints:**
- Exactly 40 tables with `data_layer = 'bronze'`
- Exactly 14 of those 40 bronze tables have `has_direct_dml_edits = TRUE` (added in gold join)
- `raw_transactions` must be one of the 14 edited bronze tables (it's the worst offender)
- 3 bronze tables feed gold executive report tables — these must be among the 14 edited ones (the $87K/year rerun cost story)

### `raw_ws_pipelines` — ~150 rows

Simulates `system.lakeflow.pipelines`.

| Column | Type | Notes |
|---|---|---|
| `pipeline_id` | STRING PK | `PIPE-NNNNNN` |
| `pipeline_name` | STRING | descriptive name e.g. `customer_churn_etl`, `revenue_daily_rollup` |
| `owner_email` | STRING | nullable for 31 rows |
| `has_owner_tag` | BOOLEAN | FALSE for those 31 rows |
| `is_production` | BOOLEAN | TRUE for 60 pipelines; 9 of the 31 un-owned ones are production |
| `schedule_type` | STRING | `hourly` / `daily` / `weekly` / `manual` |
| `has_dq_expectations` | BOOLEAN | FALSE for 8 pipelines (anti-pattern finding) |
| `uses_hardcoded_paths` | BOOLEAN | TRUE for 12 pipelines (anti-pattern finding) |
| `last_run_status` | STRING | `succeeded` / `failed` / `warning` |
| `last_run_date` | DATE | within past 30 days |
| `avg_duration_sec` | INT | 60–3600 |
| `created_at` | TIMESTAMP | |

**Anchor pipeline**: `customer_churn_etl` — no owner tag, production, has hardcoded paths. This is the one named in the README.

### `raw_ws_jobs` — ~80 rows

| Column | Type | Notes |
|---|---|---|
| `job_id` | STRING PK | `JOB-NNNNNN` |
| `job_name` | STRING | |
| `owner_email` | STRING | nullable for 18% |
| `has_owner_tag` | BOOLEAN | |
| `schedule_cron` | STRING | nullable (some are manual) |
| `cluster_type` | STRING | `serverless` / `classic` — 35% still use classic (serverless migration opportunity) |
| `created_at` | TIMESTAMP | |

### `raw_ws_job_runs` — ~500 rows

| Column | Type | Notes |
|---|---|---|
| `run_id` | STRING PK | `RUN-NNNNNNNN` |
| `job_id` | STRING FK | |
| `pipeline_id` | STRING FK | nullable — only pipeline-backed jobs have this |
| `start_time` | TIMESTAMP | past 90 days |
| `end_time` | TIMESTAMP | |
| `status` | STRING | `succeeded` / `failed` / `cancelled` |
| `duration_sec` | INT | |
| `triggered_by` | STRING | `schedule` / `manual` / `api` |

**Distribution**: ~72% succeeded, ~18% failed, ~10% cancelled. The 3 critical pipelines (`customer_churn_etl`, `revenue_pipeline_v1`, `ml_feature_refresh`) have **40%+ failure rates** — visible in the pipeline health chart.

### `raw_ws_audit_events` — ~600 rows

Simulates `system.access.audit` filtered to DML events on bronze tables.

| Column | Type | Notes |
|---|---|---|
| `event_id` | STRING PK | `EVT-NNNNNNNN` |
| `event_time` | TIMESTAMP | past 90 days |
| `user_email` | STRING | the engineer who ran the query |
| `action_type` | STRING | `INSERT` / `UPDATE` / `DELETE` / `MERGE` / `TRUNCATE` |
| `table_id` | STRING FK → `raw_ws_tables` | |
| `table_name` | STRING | denormalized for query speed |
| `data_layer` | STRING | `bronze` for all rows in this table (only bronze DML events) |
| `bytes_affected` | BIGINT | rough estimate |
| `query_snippet` | STRING | first 120 chars of the DML statement (sanitized — no actual data) |

**Key distribution:**
- `raw_transactions`: 47 events (the anchor) — mix of `INSERT` (30), `UPDATE` (12), `MERGE` (5)
- `ml_features_bronze`: 12 events (connects to the ML finding)
- `customer_events_bronze`: 9 events
- 11 other bronze tables: 1–6 events each
- Total across 14 tables: ~300 bronze DML events

Events spread across `NOW − 90 days` → `NOW`. No seasonal pattern needed — the story is about cumulative count, not a spike.

### `raw_ws_ml_experiments` — ~60 rows

| Column | Type | Notes |
|---|---|---|
| `experiment_id` | STRING PK | `EXP-NNNNNN` |
| `experiment_name` | STRING | |
| `owner_email` | STRING | nullable for 25% |
| `workspace_path` | STRING | `/Users/...` path |
| `last_run_date` | DATE | |
| `is_stale` | BOOLEAN | TRUE if `last_run_date < NOW − 30 days`; ~40% stale |
| `has_registered_model` | BOOLEAN | |
| `has_description` | BOOLEAN | FALSE for 35% (governance gap) |
| `created_at` | TIMESTAMP | |

### `raw_ws_ml_models` — ~30 rows

| Column | Type | Notes |
|---|---|---|
| `model_id` | STRING PK | `MDL-NNNNNN` |
| `model_name` | STRING | |
| `serving_endpoint_name` | STRING | nullable — 12 models have no serving endpoint (unused) |
| `upstream_features_table` | STRING | the table the model's training pipeline reads |
| `features_table_layer` | STRING | `bronze` / `silver` / `gold` — 2 models read from bronze directly (the risky ones) |
| `last_training_date` | DATE | |
| `features_last_modified_date` | DATE | last direct DML on `upstream_features_table` |
| `is_serving_stale_features` | BOOLEAN | TRUE if `features_table_layer = 'bronze'` AND `features_last_modified_date` within 30 days |
| `owner_email` | STRING | |
| `registered_in_uc` | BOOLEAN | FALSE for 8 models (governance gap) |

**Anchor models**: 2 models have `is_serving_stale_features = TRUE` — they read from `ml_features_bronze` which had 12 direct DML writes. These are the "2 models serving stale features" in the story.

---

## C. Gold Tables (dashboard + Genie reads)

All derived via inline `spark.sql` CTAS. Every column has a COMMENT.

### `gold_health_scores` — ~120 rows (4 dimensions × 30 days)

One row per `(report_date, dimension)`. Used for the score trend cards.

| Column | Type |
|---|---|
| `report_date` | DATE |
| `dimension` | STRING — `overall` / `etl_hygiene` / `ml_ai_governance` / `ownership_access` / `data_quality` |
| `score` | INT — 0–100 |
| `score_delta_30d` | INT — score change vs 30 days ago |
| `critical_count` | INT |
| `high_count` | INT |
| `medium_count` | INT |

**Score values on `REPORT_DATE` (today):**

| Dimension | Score | delta_30d |
|---|---|---|
| `overall` | 68 | -3 |
| `etl_hygiene` | 55 | -5 |
| `ml_ai_governance` | 62 | +2 |
| `ownership_access` | 71 | +8 |
| `data_quality` | 78 | +1 |

The ownership_access dimension shows clear improvement (+8 over 30 days) — the team has been cleaning it up sprint over sprint.

### `gold_bronze_table_edits` — 14 rows

One row per bronze table with direct DML. The load-bearing table for the ETL Hygiene deep-dive.

| Column | Type | Notes |
|---|---|---|
| `table_name` | STRING | |
| `catalog_schema` | STRING | `catalog.schema` |
| `edit_count_90d` | INT | total DML events in 90 days |
| `last_editor_email` | STRING | user who made the most recent edit |
| `last_edit_date` | DATE | |
| `last_action_type` | STRING | last DML operation type |
| `downstream_gold_table_count` | INT | how many gold tables depend on this via lineage |
| `downstream_gold_tables` | STRING | comma-separated list of affected gold tables |
| `estimated_rerun_cost_usd` | DECIMAL(10,2) | annual estimate based on failure rate × avg job duration × compute cost |
| `severity` | STRING | `critical` if `edit_count_90d > 20` OR feeds executive gold; `high` otherwise |

**Anchor rows (must match exactly):**

| table_name | edit_count_90d | downstream_gold_table_count | estimated_rerun_cost_usd | severity |
|---|---|---|---|---|
| `raw_transactions` | 47 | 3 | 34000.00 | `critical` |
| `ml_features_bronze` | 12 | 2 | 18000.00 | `critical` |
| `customer_events_bronze` | 9 | 2 | 14000.00 | `critical` |
| other 11 tables | 1–6 each | 0–1 | 1000–5000 | `high` |

Total `SUM(estimated_rerun_cost_usd)` ≈ $87,000 — this is the number Genie quotes.

### `gold_pipeline_health` — ~150 rows (one per pipeline)

Joins `raw_ws_pipelines` + job run aggregates.

| Column | Type |
|---|---|
| `pipeline_id` | STRING |
| `pipeline_name` | STRING |
| `owner_email` | STRING (nullable) |
| `has_owner_tag` | BOOLEAN |
| `is_production` | BOOLEAN |
| `has_dq_expectations` | BOOLEAN |
| `uses_hardcoded_paths` | BOOLEAN |
| `failure_rate_30d` | DECIMAL(5,2) — % of runs that failed |
| `avg_duration_sec` | INT |
| `anti_pattern_count` | INT — count of `has_no_owner + no_dq + hardcoded_paths` |
| `health_status` | STRING — `healthy` / `warning` / `critical` |

Critical pipelines (failure_rate > 40%): `customer_churn_etl`, `revenue_pipeline_v1`, `ml_feature_refresh`.

### `gold_ownership_trend` — ~30 rows (one per day)

Powers the "Ownership coverage" trend chart.

| Column | Type | Notes |
|---|---|---|
| `report_date` | DATE | past 30 days |
| `total_production_pipelines` | INT | ~60 |
| `owned_production_pipelines` | INT | started at 35 (58%), now 41 (69%) |
| `ownership_coverage_pct` | DECIMAL(5,2) | |
| `goal_pct` | DECIMAL(5,2) | 95.00 (constant) |

Coverage trends from ~58% on `NOW − 30d` to ~69% on `NOW`. Linear improvement with slight noise.

### `gold_remediation_backlog` — ~40 rows

The ranked findings table. This is what the team takes into sprint planning.

| Column | Type | Notes |
|---|---|---|
| `finding_id` | STRING PK | `FND-NNNNNN` |
| `severity` | STRING | `critical` / `high` / `medium` |
| `category` | STRING | `ETL Hygiene` / `ML/AI Governance` / `Ownership & Access` / `Data Quality` |
| `asset_type` | STRING | `table` / `pipeline` / `job` / `ml_model` / `ml_experiment` |
| `asset_name` | STRING | the specific violating asset |
| `owner_email` | STRING (nullable) | current owner if assigned |
| `description` | STRING | human-readable finding description |
| `business_impact_usd` | DECIMAL(10,2) | annual estimate |
| `recommended_action` | STRING | one-sentence fix |
| `detected_at` | DATE | when this was first detected |
| `sprint_estimate_days` | INT | rough fix effort |

**Distribution**: 6 critical, 11 high, 23 medium.

**Critical findings (must exist verbatim in data):**

| asset_name | category | description | business_impact_usd | recommended_action |
|---|---|---|---|---|
| `raw_transactions` | ETL Hygiene | 47 direct DML writes in 90 days — bypasses all pipeline expectations | 34000.00 | Revoke direct write permissions; route all changes through pipeline with CONSTRAINT |
| `ml_features_bronze` | ETL Hygiene | 12 direct DML writes — 2 serving models reading stale features | 18000.00 | Audit model training pipeline; migrate features to silver layer |
| `customer_events_bronze` | ETL Hygiene | 9 direct DML writes — downstream gold tables for executive reports affected | 14000.00 | Revoke direct write permissions; add CONSTRAINT and pipeline expectations |
| `customer_churn_etl` | Ownership & Access | No owner tag; 9 dependent pipelines blocked | 12000.00 | Assign owner tag; notify engineering lead |
| `revenue_pipeline_v1` | ETL Hygiene | 43% failure rate over 30 days; hardcoded S3 paths | 9000.00 | Remove hardcoded paths; add alerting |
| `churn_risk_model_v2` | ML/AI Governance | Serving endpoint reads features from bronze table with recent direct writes | 5000.00 | Retrain on silver features; add feature lineage check to CI |

**High findings**: mix of missing owner tags (7 pipelines), stale ML experiments (11), un-registered models (3).

**Medium findings**: naming violations (12 tables), missing table comments (8 bronze tables), classic compute jobs (3).

---

## D. Data Shaping Rules

- **Visibility rule**: `raw_transactions`'s 47-edit bar must stand out clearly above the second-tallest bar (`ml_features_bronze` at 12). The gap (47 vs 12) ensures the anchor is visible at a glance.
- **Ownership trend**: deliberately shows improvement (58% → 69%) so the chart reads as "we're getting better but not done" — motivating, not alarming.
- **Score timeline**: ETL Hygiene is the only score trending *down* slightly (−5 over 30d) while others improve — this is the dimension that needs attention.
- **No seasonal distribution needed** — this is cumulative count data, not time-series events. Spread audit events evenly over 90 days with mild random jitter.

---

## E. Validation

Run these as `execute_sql` checks after data generation:

**Load-bearing (gate the story):**
- `gold_bronze_table_edits` has exactly 14 rows; `raw_transactions` row has `edit_count_90d = 47`.
- `SUM(estimated_rerun_cost_usd)` from `gold_bronze_table_edits` ≈ $87,000 (±$5K).
- `gold_remediation_backlog` counts: 6 critical, 11 high, 23 medium.
- `gold_health_scores WHERE report_date = CURRENT_DATE AND dimension = 'overall'` → `score = 68`.
- `gold_health_scores WHERE report_date = CURRENT_DATE AND dimension = 'etl_hygiene'` → `score = 55`.
- `gold_ownership_trend WHERE report_date = CURRENT_DATE` → `ownership_coverage_pct` between 68 and 71.
- `raw_ws_ml_models WHERE is_serving_stale_features = TRUE` → exactly 2 rows.
- `raw_ws_pipelines WHERE has_owner_tag = FALSE` → exactly 31 rows; of those, `WHERE is_production = TRUE` → exactly 9 rows.

**Smoke checks:**
- All tables non-empty; `gold_health_scores` has one row per day × 5 dimensions = ~150 rows.
- `gold_ownership_trend` has ~30 rows, coverage increasing from ~58% to ~69%.
- `gold_pipeline_health` has same row count as `raw_ws_pipelines` (~150).
- No nulls in any `finding_id`, `severity`, `asset_name` in `gold_remediation_backlog`.
