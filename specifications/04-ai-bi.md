# AI/BI — Dashboard + Genie

Tables and columns referenced here are defined in `01-lakeflow.md`. Gold tables power all widgets and Genie queries.

> **Talking-track-only products** — do NOT build resources for these:
> - **Genie Code**: the SQL/pipeline authoring copilot — referenced in the README, not a separate resource.
> - **Genie One**: the business-user access layer — talk track; same Genie space surfaces there once built.
> - **Lakeflow Connect**: the ingest narrative (real workspaces ingest UC system tables this way) — talk track.
> - **Unity Catalog**: the global governance layer — already in place; grants are applied during data generation.

---

## A. Genie Space

**Skill to use**: `databricks-genie` — read `SKILLS/databricks-genie-agents/SKILL.md` before implementing.

Create **`Datavail Assessment Analytics`** Genie Space.

### Tables

All in `<catalog>.<schema>` (the target catalog/schema passed at deploy time):
- `gold_bronze_table_edits` — the 14 bronze tables with direct DML, costs, downstream impact
- `gold_remediation_backlog` — all 40 findings ranked by severity
- `gold_health_scores` — daily scores per dimension (trend + current state)
- `gold_pipeline_health` — pipeline ownership, failure rates, anti-patterns
- `gold_ownership_trend` — ownership coverage % trend over 30 days
- `raw_ws_audit_events` — raw DML events on bronze tables (for drill-down by user/table/date)
- `raw_ws_ml_models` — ML models including `is_serving_stale_features` flag

### Self-sufficient room

Anyone opening the Genie room must understand the Datavail Assessment context without prior briefing.

- **Space description**: "Datavail assessment analytics for the engineering team. Overall score: 68/100. Top risk: 14 bronze tables have been directly edited in the past 90 days — bypassing pipeline expectations and causing cascading failures worth ~$87K/year. Ask about bronze table violations, pipeline ownership gaps, ML model risks, or the full remediation backlog."
- **Story-context `text_instruction`** at the TOP of instructions: describe the workspace context, what the scores mean, the baseline metrics, and the investigation flow.
- **`sample_questions`** chips + matching `example_question_sqls` walk the story arc end-to-end.

### Instructions

```
You analyze Datavail Assessment data for Alex (Head of Data Engineering) and their engineering team.

CONTEXT:
- Workspace overall health score: 68/100 (was 71 thirty days ago)
- Four dimensions: ETL Hygiene (55), ML/AI Governance (62), Ownership & Access (71), Data Quality (78)
- The workspace has accumulated anti-patterns over 18 months of growth
- $250K/year at risk from slow pipelines, broken ownership, and risky bronze table edits

BASELINES:
- Healthy bronze table: 0 direct DML writes (all changes go through pipeline)
- Healthy pipeline: has owner tag, has DQ expectations, no hardcoded paths, <10% failure rate
- Healthy ownership: 95%+ of production pipelines have owner tags
- Current ownership: 69% of production pipelines owned (target: 95%)

INVESTIGATION FLOW for "Which bronze tables have been directly modified?":
1. gold_bronze_table_edits → ORDER BY edit_count_90d DESC → raw_transactions leads with 47 edits
2. gold_bronze_table_edits → SUM(estimated_rerun_cost_usd) → ~$87K/year total
3. gold_bronze_table_edits WHERE severity = 'critical' → 3 tables feed executive gold reports
4. raw_ws_audit_events WHERE table_name = 'raw_transactions' → show who made the edits and when

INVESTIGATION FLOW for "Which ML models are serving stale features?":
1. raw_ws_ml_models WHERE is_serving_stale_features = TRUE → 2 models
2. For each model: show serving_endpoint_name, upstream_features_table, features_last_modified_date
3. Connect to gold_bronze_table_edits WHERE table_name = upstream_features_table → shows the edits that caused staleness

KEY QUERY PATTERNS:
- "What's the overall health score?" → gold_health_scores WHERE dimension = 'overall' AND report_date = CURRENT_DATE → score = 68
- "Show the remediation backlog" → gold_remediation_backlog ORDER BY severity (critical first), business_impact_usd DESC
- "How is ownership improving?" → gold_ownership_trend ORDER BY report_date → from 58% to 69% over 30 days
- "Which pipelines have no owner?" → gold_pipeline_health WHERE has_owner_tag = FALSE → 31 pipelines, 9 production
- "What is the ETL hygiene score trend?" → gold_health_scores WHERE dimension = 'etl_hygiene' ORDER BY report_date

COST CALCULATIONS:
- Annual rerun cost from bronze edits: SUM(estimated_rerun_cost_usd) from gold_bronze_table_edits ≈ $87K
- Total at-risk: $250K/year (pipelines + ownership + ML staleness combined)
```

### Sample Questions — story-arc walk

**Chips (all 6, in arc order):**
1. **Score** — "What is the current Datavail Assessment score and which dimension is worst?"
2. **Bronze edits** — "Which bronze tables have been directly modified, and what is the estimated annual cost of cascading failures?"
3. **ML risk** — "Which ML models are serving features from tables that had direct writes in the last 30 days?"
4. **Ownership** — "Which production pipelines have no owner tag?"
5. **Trend** — "How has ownership coverage improved over the past 30 days?"
6. **Backlog** — "Show me the top 10 critical and high findings ranked by business impact."

**Curated SQLs (3 — load-bearing cross-table joins):**
- **Bronze edits cost**: `SELECT table_name, edit_count_90d, downstream_gold_tables, estimated_rerun_cost_usd FROM gold_bronze_table_edits ORDER BY edit_count_90d DESC` + `SELECT SUM(estimated_rerun_cost_usd) as total_rerun_cost FROM gold_bronze_table_edits` — the punchline query. Cross-table pattern Genie might miss.
- **ML staleness chain**: CTE joins `raw_ws_ml_models` (where `is_serving_stale_features = TRUE`) to `gold_bronze_table_edits` on `upstream_features_table = table_name` — crosses two tables for the root-cause chain.
- **Full backlog ranked**: `SELECT severity, category, asset_name, business_impact_usd, recommended_action FROM gold_remediation_backlog ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, business_impact_usd DESC` — the ordering matters for the sprint planning view.

### Validation

- "What is the Datavail Assessment score?" → returns 68 for overall, confirms ETL Hygiene (55) is worst.
- "Which bronze tables have been directly modified?" → `raw_transactions` leads with 47 edits; total cost ≈ $87K/year.
- "Which ML models are serving stale features?" → exactly 2 models returned, with their serving endpoints and the upstream bronze table named.
- "Which production pipelines have no owner?" → 9 pipelines; `customer_churn_etl` in the list.
- "Show the remediation backlog" → 6 critical, 11 high, 23 medium; `raw_transactions` finding is first.

Add `genie_space_id` to `resources.json`.

---

## B. Dashboard

**Skill to use**: `databricks-aibi-dashboards` — read `SKILLS/databricks-aibi-dashboards/SKILL.md` before implementing. The skill owns the JSON shape and encoding rules; this spec is WHAT, not HOW.

Create **`Datavail Assessment`** dashboard. Save locally as `PROJECT/dashboard.json`. Link the Genie space from section A.

### Design principles

- **Three pages, one story**: page 1 is the executive glance (*score + dimension rings + top anti-patterns*); page 2 is the ETL deep-dive (*bronze table edits + pipeline health*); page 3 is the remediation backlog (*ranked findings for sprint planning*).
- **Score as the visual anchor**: the health score (68/100) is the first thing on page 1 — a large counter tile with its delta (−3 from 30d ago). The four dimension scores below it explain why.
- **The bronze-edit bar chart is the wow moment**: page 2 shows a horizontal bar chart of the 14 bronze tables ranked by `edit_count_90d`. `raw_transactions` at 47 stands out 3× above the next tallest bar (`ml_features_bronze` at 12). Anyone in the room can point at it without squinting.
- **Remediation backlog table on page 3**: a clean severity-ranked table — the artifact the team exports to Jira. Color-coded severity chips (critical = red, high = orange, medium = yellow).
- **Two datasets per page**: kept lean for performance and filter coherence.

### Theme

```
canvasBackgroundColor: #F4F6FA (light) / #0D1117 (dark)
widgetBackgroundColor: #FFFFFF (light) / #161B22 (dark)
widgetBorderColor:     same as widgetBackgroundColor
fontColor:             #1A2233 (light) / #E8ECF0 (dark)
selectionColor:        #2563EB (light) / #60A5FA (dark)
visualizationColors:   ["#1E40AF","#3B82F6","#10B981","#F59E0B","#EF4444"]
widgetHeaderAlignment: LEFT
```

5-stop palette: deep navy → medium blue → emerald → amber → red. Semantic use: navy/blue for neutral metrics, green for healthy/improving, amber for high findings, red for critical findings.

**Semantic colors (literal-hex, never `themeColorType: position N`):**
- **Critical severity** → `#EF4444` red
- **High severity** → `#F59E0B` amber
- **Medium severity** → `#3B82F6` blue
- **ETL Hygiene (worst dimension)** → `#EF4444` red
- **Healthy / improving** → `#10B981` emerald

**Dimension score color pins** (by score value, not label — derived column in dataset):
- Score < 60 → `#EF4444`
- Score 60–74 → `#F59E0B`
- Score ≥ 75 → `#10B981`

---

### Datasets (5 total)

| Name | Source | Powers |
|---|---|---|
| `ds_scores` | `gold_health_scores WHERE report_date = CURRENT_DATE` + 30d trend from same table | Score KPI tiles, dimension score bars, score trend line |
| `ds_bronze_edits` | `gold_bronze_table_edits` ORDER BY edit_count_90d DESC | Bronze table edit bar chart, cost table |
| `ds_pipeline_health` | `gold_pipeline_health` | Pipeline ownership bar, failure rate chart |
| `ds_ownership_trend` | `gold_ownership_trend` | Ownership trend line chart |
| `ds_backlog` | `gold_remediation_backlog` | Full remediation backlog table |

**No global date filter** — this is a point-in-time snapshot report. The only filter is a severity filter on `ds_backlog` (page 3). Date ranges are baked into each dataset's SQL.

---

### Page 1 — Health Score Overview

12-column grid.

| Row (y) | x | w | h | Widget |
|---|---|---|---|---|
| 0 | 0 | 12 | 3 | `page1_title` (markdown) |
| 3 | 0 | 3 | 4 | `kpi_overall_score` |
| 3 | 3 | 3 | 4 | `kpi_critical_findings` |
| 3 | 6 | 3 | 4 | `kpi_high_findings` |
| 3 | 9 | 3 | 4 | `kpi_pipelines_no_owner` |
| 7 | 0 | 8 | 7 | `dimension_score_bars` |
| 7 | 8 | 4 | 7 | `score_trend_line` |
| 14 | 0 | 12 | 6 | `top_anti_patterns_table` |

**`page1_title` — markdown widget (12-wide)**: Self-sufficient header. ~5 lines: overall score 68/100, what the score means (Needs Attention), the top risk (14 bronze tables with direct edits — $87K/year rerun cost), what to see on this page (score KPIs, dimension bars in color, trend line showing ETL Hygiene worsening). Lift from README; don't repeat verbatim.

**4 × `counter` KPI tiles** (source: `ds_scores` for score; `ds_backlog` for counts; `ds_pipeline_health` for pipeline count):
- **`kpi_overall_score`**: `68` (static from `gold_health_scores WHERE dimension = 'overall' AND report_date = CURRENT_DATE`). Value format: integer. Subtitle: "Overall health score (was 71, −30d)". Color `#F59E0B` (amber — in the "needs attention" band).
- **`kpi_critical_findings`**: `6`. Subtitle: "Critical findings". Color `#EF4444`.
- **`kpi_high_findings`**: `11`. Subtitle: "High findings". Color `#F59E0B`.
- **`kpi_pipelines_no_owner`**: `31`. Subtitle: "Pipelines without owner tag". Color `#F59E0B`.

**`dimension_score_bars` — `bar` horizontal "Health score by dimension"** (8-wide). Source: `ds_scores`. y = `dimension` (5 rows), x = `score`. Color by a derived `score_band` column (`critical` / `warning` / `healthy`) with literal-hex pins: critical → `#EF4444`, warning → `#F59E0B`, healthy → `#10B981`. Sorted by score ASC so ETL Hygiene (55) is at the top as the worst. Max x-axis = 100 (score scale). Frame description: *"ETL Hygiene is the only dimension in the red. Ownership & Access shows the most improvement (+8 pts over 30 days)."*

**`score_trend_line` — `line` "ETL Hygiene score trend (30 days)"** (4-wide). Source: `ds_scores` (30d history for ETL Hygiene only). x = `report_date` (temporal), y = `score`. Line color `#EF4444`. Shows a slight downward trend (from 60 to 55) with a horizontal goal line at 80. Frame description: *"ETL Hygiene is the only dimension trending down — driven by recent bronze table edits."*

**`top_anti_patterns_table` — `table` "Top anti-patterns by impact"** (12-wide). Source: `ds_backlog WHERE severity = 'critical'`. Columns: `severity` (chip — color-coded), `category`, `asset_name`, `description`, `business_impact_usd` (USD format), `recommended_action`. Sorted by `business_impact_usd` DESC. Max 6 rows (the critical findings only). Frame description: *"The six most urgent findings. Each row is a Jira ticket waiting to happen."*

---

### Page 2 — ETL Hygiene Deep-Dive

| Row (y) | x | w | h | Widget |
|---|---|---|---|---|
| 0 | 0 | 12 | 3 | `page2_title` (markdown) |
| 3 | 0 | 8 | 7 | `bronze_edits_bar` |
| 3 | 8 | 4 | 7 | `bronze_edit_cost_table` |
| 10 | 0 | 12 | 1 | `sec_pipeline_health` (markdown) |
| 11 | 0 | 6 | 6 | `pipeline_failure_bar` |
| 11 | 6 | 6 | 6 | `pipeline_ownership_bar` |
| 17 | 0 | 12 | 6 | `ownership_trend_line` |

**`page2_title` — markdown (12-wide)**: Page frame for the ETL deep-dive. What's on this page: bronze table DML violations ranked by frequency, pipeline failure rates, ownership coverage trend. The key number to point at: `raw_transactions` at 47 edits, standing out 3× above the next-tallest bar.

**`bronze_edits_bar` — `bar` horizontal "Direct DML writes on bronze tables (90 days)"** (8-wide). Source: `ds_bronze_edits`. y = `table_name`, x = `edit_count_90d`. Color by `severity` with literal-hex pins: `critical` → `#EF4444`, `high` → `#F59E0B`. Sorted by `edit_count_90d` DESC. All 14 rows shown. Frame description: *"`raw_transactions` at 47 edits is 3× the next-worst table. Every bar here represents a pipeline expectation bypass."* This is the **wow moment** of the demo — the gap between `raw_transactions` (47) and everything else is unmissable.

**`bronze_edit_cost_table` — `table` "Bronze edit cost & downstream impact"** (4-wide). Source: `ds_bronze_edits` WHERE `severity = 'critical'`. Columns: `table_name`, `edit_count_90d` (Edits), `downstream_gold_table_count` (Affected gold tables), `estimated_rerun_cost_usd` (Annual cost, USD format). Footer row: SUM of `estimated_rerun_cost_usd` ≈ $87K. Frame description: *"The 3 critical bronze tables drive ~$87K/year in rerun costs."*

**`sec_pipeline_health` — markdown section heading (12-wide, h=1)**: `## Pipeline health & ownership`

**`pipeline_failure_bar` — `bar` vertical "Pipeline failure rate (30 days)"** (6-wide). Source: `ds_pipeline_health WHERE failure_rate_30d > 0`. y = `failure_rate_30d` (%), x = `pipeline_name`. Color by `health_status`: `critical` → `#EF4444`, `warning` → `#F59E0B`, `healthy` → `#10B981`. Show top 15 by failure rate. Frame description: *"Three pipelines fail >40% of runs — the team is manually re-triggering them every week."*

**`pipeline_ownership_bar` — `bar` stacked horizontal "Production pipelines by ownership"** (6-wide). Source: `ds_pipeline_health WHERE is_production = TRUE`. One aggregated bar showing owned vs un-owned count. `color = has_owner_tag` pinned: TRUE → `#10B981`, FALSE → `#EF4444`. Also show a small horizontal goal line at 95% owned. Frame description: *"31 of 60 production pipelines have no owner tag. When things break, nobody knows who to call."*

**`ownership_trend_line` — `line` "Ownership coverage — 30-day trend"** (12-wide). Source: `ds_ownership_trend`. x = `report_date`, y = `ownership_coverage_pct` (actual line, blue `#3B82F6`) + `goal_pct` (dashed, `#10B981`). Annotate `report_date = CURRENT_DATE − 30d` with label "Sprint 42 starts". Frame description: *"58% → 69% — the team is gaining ~0.37 pts/day. At this rate, 95% ownership is 70 days out."*

---

### Page 3 — Remediation Backlog

| Row (y) | x | w | h | Widget |
|---|---|---|---|---|
| 0 | 0 | 12 | 3 | `page3_title` (markdown) |
| 3 | 0 | 4 | 4 | `backlog_kpi_critical` |
| 3 | 4 | 4 | 4 | `backlog_kpi_high` |
| 3 | 8 | 4 | 4 | `backlog_kpi_medium` |
| 7 | 0 | 12 | 10 | `backlog_full_table` |

**`page3_title` — markdown (12-wide)**: Page frame. This is the sprint planning artifact. 40 total findings (6 critical, 11 high, 23 medium). Total business impact at risk: ~$250K/year. Use the severity filter (left panel) to focus on what fits in the next sprint.

**3 × `counter` KPI tiles**:
- **`backlog_kpi_critical`**: `6`. Subtitle: "Critical — address this sprint". Color `#EF4444`.
- **`backlog_kpi_high`**: `11`. Subtitle: "High — address next 2 sprints". Color `#F59E0B`.
- **`backlog_kpi_medium`**: `23`. Subtitle: "Medium — address this quarter". Color `#3B82F6`.

**`backlog_full_table` — `table` "Full remediation backlog"** (12-wide). Source: `ds_backlog`. Columns: `severity` (chip, color-coded), `category`, `asset_type`, `asset_name`, `owner_email` (Owner — blank cell if null, visually obvious), `description`, `business_impact_usd` (Impact, USD format, DESC sort default), `recommended_action` (wrap), `sprint_estimate_days` (Effort). All 40 rows. Default sort: severity rank (critical first), then `business_impact_usd` DESC. Frame description: *"Export to CSV and paste into Jira. Sort by Effort (sprint_estimate_days) to find quick wins."*

**Global filter (left panel)**: `severity` multi-select (Critical / High / Medium) applied to `ds_backlog` only. Default: all selected.

### Validation

Open the published dashboard and confirm:
- Page 1: Score tiles read 68 / 6 / 11 / 31. Dimension bars: ETL Hygiene is shortest (leftmost when sorted ASC) and red.
- Page 2: `raw_transactions` bar at 47 is clearly the tallest; next bar is `ml_features_bronze` at 12. Bronze edit cost table footer shows ~$87K. Ownership trend rises from ~58% to ~69%.
- Page 3: Backlog table shows 6 critical rows first; `raw_transactions` finding has `$34,000` in Impact column.
- Global severity filter on page 3 narrows the table correctly.

Add `dashboard_id` to `resources.json`.
