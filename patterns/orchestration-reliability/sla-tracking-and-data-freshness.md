# SLA Tracking and Data Freshness

**Category:** Orchestration & Reliability

Critical data products have explicit service levels — when the data
must be ready, how complete it must be — and those are measured
continuously from job history and table freshness, with a record of
how often the SLA was met.

## Why it matters

A job succeeding is not the same as a consumer being served. The job
can succeed at 11:40 for a dashboard read at 9:00; it can succeed with
zero rows because an upstream extract was empty. The business
experiences both as a broken SLA, and neither shows up as a failure.

Notifications and duration thresholds
([`failure-notifications-and-duration-thresholds.md`](failure-notifications-and-duration-thresholds.md))
catch an individual run going wrong. SLA tracking answers the
aggregate question — *how reliable is this data product over time* —
which is what capacity planning, prioritization, and trust conversations
need.

## What good looks like

- A short list of SLA-bearing data products (usually gold tables behind
  executive dashboards, regulatory reports, or ML features), each with
  an owner, a ready-by time, and a freshness/completeness expectation.
- **Pipeline-side SLA** measured from `system.lakeflow.job_run_timeline`:
  end time vs. the deadline, per run, rolled up into an attainment
  percentage per month.
- **Table-side SLA** measured independently of the pipeline via
  Unity Catalog anomaly detection, which checks **freshness** ("if a
  commit is unusually late, the table is marked as stale") and
  **completeness** (rows committed in the last 24 hours below the
  expected range). It's enabled per schema and writes to
  `system.data_quality_monitoring.table_results`, with alerts available.
- Duration thresholds and streaming-backlog thresholds set on the jobs
  behind each SLA, so lateness is noticed during the run.
- An SLA dashboard that consumers can see — shared reliability numbers
  build more trust than reassurances.

## How to detect

`system.lakeflow.job_run_timeline` (`job_id`, `period_start_time`,
`period_end_time`, `result_state`) gives completion time per run;
compare against a documented deadline to compute attainment. Check
whether anomaly detection is enabled for schemas containing gold /
SLA-bearing tables — no rows for those tables in
`system.data_quality_monitoring.table_results` is the finding. Jobs
without duration health rules are visible through the Jobs API
(`health.rules`), not system tables. The absence of any documented SLA
is a conversation finding, and the most common one.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Platform management › SLA tracking** — *primary.* Do critical data products have documented SLAs, measured from `system.lakeflow.job_run_timeline` and table freshness / completeness monitoring?

## References

- [Anomaly detection](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-quality-monitoring/anomaly-detection/)
- [Data quality monitoring results system table](https://docs.databricks.com/aws/en/admin/system-tables/data-quality-monitoring)
- [Add notifications on a job](https://docs.databricks.com/aws/en/jobs/notifications)
- [Phase 9: Design observability strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/observability)
