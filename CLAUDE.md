# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single Databricks Asset Bundle (DAB) that builds one demo: **"Datavail Assessment"** — an internal AI/BI Dashboard + Genie space that scores a (simulated) Databricks workspace's ETL hygiene, ML/AI governance, ownership, and data quality. There is no application code to build/lint/test in the traditional sense; the deliverable is Databricks-hosted resources (a dashboard, a Genie space, and UC tables) provisioned by `databricks bundle` commands.

`context/source-brief.md` holds the original user brief (source of truth for intent). `specifications/01-lakeflow.md` (data layer) and `specifications/04-ai-bi.md` (dashboard + Genie) are the detailed specs everything else was implemented from — consult these before changing table schemas, scores, or widget layouts, since they define what's "correct."

## Commands

```bash
# Validate the bundle
databricks bundle validate

# Deploy resources (dashboard) — catalog/schema have generic defaults in databricks.yml; warehouse_id is required
databricks bundle deploy \
  --var catalog=<your-catalog> \
  --var schema=<your-schema> \
  --var warehouse_id=<your-warehouse-id>

# Run the setup job: generates all 12 UC tables, then deploys/updates the Genie space
databricks bundle run datavail_assessment_setup \
  --var catalog=<your-catalog> \
  --var schema=<your-schema> \
  --var warehouse_id=<your-warehouse-id>

# Tear down (removes dashboard + job only — does NOT drop UC tables or the Genie space)
databricks bundle destroy
```

Full deploy instructions, including deploying to a different catalog/schema, are in `dab_instructions.md`.

## Architecture

**Bundle-deployed path (authoritative — this is what `databricks bundle` actually provisions):**

```
data_generation/generate_data.py  →  UC tables (raw_ws_* + gold_*)
        ↓ (job dependency)
src/deploy/deploy_genie.py        →  reads src/genie/genie_space.json, substitutes catalog.schema, creates/updates Genie space (idempotent by title lookup)

src/dashboard/dashboard.json      →  deployed directly as a bundle resource (databricks.yml → resources.dashboards)
```

`databricks.yml` wires this together: it declares the `dashboards.datavail_assessment_dashboard` resource (from the committed `src/dashboard/dashboard.json`) and the `jobs.datavail_assessment_setup` job, whose two tasks run `data_generation/generate_data.py` then `src/deploy/deploy_genie.py` in sequence. `sync.exclude` deliberately keeps `app/**` out of what gets synced to the workspace.

**`app/` is a separate, non-deployed implementation** — an earlier/alternate build using the SQL Statements API (`app/datagen.py`, different sample data than `data_generation/generate_data.py`) and raw M2M REST calls to build the dashboard/Genie space in Python (`app/build_resources.py`, builds dashboard JSON programmatically rather than from the committed `dashboard.json`). `app/start.sh` serves a static status page for a Databricks App. Because `sync.exclude` drops `app/**`, none of this runs as part of `databricks bundle deploy/run` — treat it as reference/scratch, not the source of truth. **When asked to change data generation, dashboard widgets, or Genie config, edit the bundle-deployed files (`data_generation/generate_data.py`, `src/dashboard/dashboard.json`, `src/genie/genie_space.json`), not the `app/` equivalents**, unless the user is specifically working on the `app/` preview path.

**Data model:** `data_generation/generate_data.py` creates 7 raw tables (`raw_ws_tables`, `raw_ws_pipelines`, `raw_ws_jobs`, `raw_ws_job_runs`, `raw_ws_audit_events`, `raw_ws_ml_experiments`, `raw_ws_ml_models`) simulating Unity Catalog system tables, then derives 5 gold tables (`gold_health_scores`, `gold_bronze_table_edits`, `gold_pipeline_health`, `gold_ownership_trend`, `gold_remediation_backlog`) that the dashboard and Genie space read exclusively. `raw_ws_pipelines`/job-run aggregation happens via CTAS `spark.sql`; the rest are constructed directly as DataFrames from hardcoded Python data (`BRONZE_EDITED`, `CRITICAL_PIPES`, `REMEDIATION_FINDINGS`, etc.) — there's no dbt/SDP layer.

**The story numbers are load-bearing and cross-referenced in four places** — `data_generation/generate_data.py`, `src/dashboard/dashboard.json`, `src/genie/genie_space.json`, and the specs (`specifications/01-lakeflow.md`, `04-ai-bi.md`). Key anchors that must stay consistent if edited: overall score 68 (was 71), ETL Hygiene 55, `raw_transactions` at 47 direct DML edits (3× the next-highest table), ~$87K/year total rerun cost, 31 unowned pipelines (9 in production), 2 ML models serving stale features, and a 6/11/23 critical/high/medium split in `gold_remediation_backlog`. `generate_data.py` ends with a validation block that asserts these exact values — run it after any data changes to catch drift.

**`resources.json`** records resource IDs (`genie_space_id`, `dashboard_id`) and the table list from the most recent build session — informational, not consumed by the bundle itself. `architecture.md` is a JSON spec for an architecture-diagram generation tool, not executable code.
