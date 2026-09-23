# Datavail Assessment Report

> **Audience.** Internal engineering teams — data engineers, ML engineers, and platform leads — who need a scored, evidence-based view of their Databricks workspace to prioritize remediation. Not customer-facing.

## The Story

| | |
|---|---|
| **Company** | Mid-size enterprise data platform team (generic — rebrand to the client's name) |
| **Hero** | Alex Chen, Head of Data Engineering |
| **Problem** | After 18 months of rapid platform growth, the workspace has accumulated anti-patterns: bronze tables being edited directly, pipelines with no owners, inconsistent naming, undocumented lineage, and ML experiments with no governance. Three critical ETL pipelines fail weekly. |
| **Catalyst** | A routine Q3 audit flags $250K/year in lost productivity: reruns from bad data writes, unowned pipelines blocking new hires, and two ML models serving stale features because their upstream tables were silently mutated. |
| **Investigation** | Alex opens the Datavail Assessment dashboard — an overall score (68/100), broken down by four dimensions: ETL Hygiene, ML/AI Governance, Ownership & Access, and Data Quality. Each dimension has a leaderboard of the worst offenders ranked by severity. |
| **Root cause** | Direct edits to bronze-layer tables are the single biggest risk: 14 bronze tables have been modified by ad-hoc SQL in the past 90 days, bypassing all pipeline expectations and corrupting three downstream gold tables. |
| **Resolution** | The report generates a prioritized remediation backlog: 6 critical issues (bronze edits, orphaned pipelines), 11 high issues (missing ownership tags, stale ML experiments), and 23 medium issues (naming violations, lineage gaps). The team loads the backlog into their sprint planning tool. |
| **Impact** | $250K/year recovered: pipeline reruns down 70%, two ML models retrained on clean features, and onboarding time for new engineers cut from 3 weeks to 4 days. |

---

## Overview

Alex opens the Datavail Assessment on Monday morning. The top card reads **68/100 — Needs Attention**. The score is broken into four color-coded rings: ETL Hygiene (55), ML/AI Governance (62), Ownership & Access (71), Data Quality (78).

Drilling into ETL Hygiene, the dashboard shows 14 bronze tables with direct SQL modifications in the past 90 days — a clear anti-pattern in a medallion architecture. Three of those tables feed gold-layer assets that power weekly executive reports. The most-edited bronze table (`raw_transactions`) has been touched 47 times directly, bypassing every `CONSTRAINT` and pipeline expectation.

Alex asks Genie: *"Which bronze tables have been directly modified and what downstream gold tables do they affect?"* Genie walks the Unity Catalog lineage graph, surfaces the three affected gold tables, and calculates the compounded rerun cost: **$87K/year** in wasted compute from cascading failures.

The Ownership & Access tab reveals 31 pipelines with no owner tag — 9 of them actively running in production. When Alex's newest engineer asked "who owns the customer churn pipeline?", the answer was no one on record.

The report closes with the **Remediation Backlog** view — a severity-ranked table of every finding, with the category, the violating asset, the business impact estimate, and a suggested fix. The team exports it to Jira in one click (via Genie One / Lakeflow Connect integration).

**Duration:** 6–8 minutes for a full walkthrough.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Overall Datavail Assessment score | 68 / 100 |
| Bronze tables with direct edits (90 days) | 14 |
| Most-edited bronze table | `raw_transactions` — 47 direct writes |
| Pipelines with no owner tag | 31 (9 in production) |
| Weekly ETL pipeline failures | 3 critical pipelines |
| Stale ML model features (from mutated upstreams) | 2 models in serving |
| Annualized cost at risk | $250,000 |
| Estimated savings from remediation | $250K / year |
| Critical findings in backlog | 6 |
| High findings | 11 |
| Medium findings | 23 |

---

## Demo Walkthrough

**Frame:** Monday morning. The Q3 platform audit is in two days. Alex opens the internal health report.

### Act 1 — Read the score (1 min)

**Open the Datavail Assessment dashboard.**

Top card: **68/100 — Needs Attention** with a delta vs 30 days ago (was 71). Four dimension rings below — ETL Hygiene is the only one in red (55). The "Critical Issues" banner lists 6 findings with red severity chips. 

> *"This is **AI/BI Dashboards** — the same governed BI layer your business teams use, now turned inward. The data behind every tile comes from Unity Catalog system tables — job run history, lineage graphs, table property metadata, access audit logs — ingested via **Lakeflow Connect** connectors and processed through a declarative pipeline."*

---

### Act 2 — Drill into ETL Hygiene (2 min)

**Navigate to the ETL Hygiene tab.**

The tab shows a ranked list of anti-patterns. Top finding: **14 bronze tables with direct DML writes** (not via pipeline). Below: 8 pipelines without data quality expectations. Below: 12 pipeline tasks with hardcoded absolute paths.

Click a bronze table row — a drawer shows the modification history: which user, which query type, timestamp, and the downstream gold tables affected via lineage.

> *"Direct edits to bronze tables are the most common anti-pattern in medallion architectures. This view surfaces them from Unity Catalog audit logs — every `INSERT`, `UPDATE`, `DELETE`, `MERGE` on any table tagged `layer=bronze` or living in a `*_bronze` schema. The fix is immediate: revoke direct write permissions and route all changes through the pipeline."*

---

### Act 3 — Ask Genie (1–2 min)

**Open the Genie space attached to the dashboard.**

**Alex types:** `Which bronze tables have been directly modified and what is the estimated rerun cost?`

Genie traces the lineage: bronze edits → affected silver tables → cascading gold failures → computes rerun cost from job run durations × failure frequency. Answer: **$87K/year** for the top 3 tables alone.

**Alex types:** `Which ML models are serving features from tables that had direct writes in the last 30 days?`

Genie returns 2 model names, their serving endpoint, the upstream table, and the date of last direct write — surfaces the silent data corruption risk that the ML team didn't know existed.

> *"This is **AI/BI Genie** — natural language over Unity Catalog system tables. Alex didn't write a single JOIN. The lineage graph, the audit logs, and the model registry are all queryable in plain English. **Unity Catalog** is the common semantic layer; every agent and dashboard reads the same lineage, same permissions, same metadata."*

---

### Act 4 — Review the Remediation Backlog (1 min)

**Navigate to the Remediation Backlog tab.**

A severity-ranked table: Critical (6 rows, red) → High (11) → Medium (23). Each row: finding category, asset name, last modified, owner (blank if orphaned), business impact estimate, recommended action.

**Critical examples:**
- `raw_transactions` — 47 direct DML writes — $34K/year rerun cost — **Revoke write perms, add CONSTRAINT**
- `ml_features_bronze` — 12 direct writes — 2 models serving stale data — **Audit model training pipeline**
- Pipeline `customer_churn_etl` — no owner — blocking 3 dependent pipelines — **Assign owner tag**

> *"The backlog is designed to go straight into sprint planning. Export to CSV or route to Jira via **Genie One** — the same analyst who just asked questions in Genie can assign tickets to the right engineers without leaving the platform."*

---

### Act 5 — Zoom out: governance posture (30s)

**Navigate to Ownership & Access tab.**

Show the "Ownership coverage" trend chart: 30 days ago 58% of production pipelines had owner tags; today 69% after last sprint's cleanup. The goal line is at 95%.

> *"This is how the team tracks improvement sprint over sprint. The score isn't a one-time audit — it's a living metric, recalculated nightly from Unity Catalog system tables. Engineering leads can make it a team OKR: '95% ownership coverage by Q4.' **Databricks One** surfaces the same report to engineering managers without them needing a Databricks seat."*

---

## Products Showcased

| Product | Mode | What it does in this demo |
|---------|------|---------------------------|
| **Synthetic Data Generation** | Build | Generates realistic workspace metadata: ~200 tables (bronze/silver/gold), ~150 pipelines, ~80 jobs, ~500 job run records (with failures), ~300 audit log events (direct DML on bronze), ~60 ML experiments, ~30 model endpoints. Produces the governed `health_*` gold tables the dashboard and Genie consume. |
| **Lakeflow Connect** | Talk track | "In production, workspace telemetry arrives from Unity Catalog system tables — `system.access.audit`, `system.lakeflow.job_run_timeline`, `system.lineage.table_lineage` — via Lakeflow Connect. No custom pipelines, no cron jobs." |
| **AI/BI Dashboard** | Build | The 68/100 health score at a glance — four dimension rings, anti-pattern leaderboards, drill-through drawers, remediation backlog table. |
| **AI/BI Genie** | Build | Answers engineering questions in plain English: "which bronze tables were directly modified?", "what models serve stale features?", "which pipelines have no owner?" — all from Unity Catalog metadata. |
| **Unity Catalog** | Talk track | The common layer the report is built on — lineage, audit logs, table properties, ownership tags, ML registry. Every finding traces back to a UC-governed asset. |
| **Genie Code** | Talk track | The copilot Alex used to build the custom dashboard SQL and the Genie space instructions — referenced but not provisioned per-demo. |
| **Genie One** | Talk track | Where engineering managers and platform leads access the same report and export findings to Jira without a Databricks engineering seat. |
