# Materialized Views for Serving Layers

**Category:** SQL & Analytics

Derived tables that dashboards and BI tools read are defined as
materialized views (or streaming tables), so Databricks handles
incremental refresh — rather than as hand-written jobs that rebuild a
table on a schedule.

## Why it matters

A materialized view is a "Unity Catalog managed table that physically
stores the results of a query," refreshed automatically, on a trigger,
or on a CRON schedule. The refresh machinery is the point: the system
chooses "either incremental refresh (tracking only changed data) or
full refresh (recomputing everything), depending on query structure and
cost-effectiveness." A hand-written rebuild job always does the second
one, because implementing the first is hard enough that nobody does it
twice.

The billing model is worth knowing before choosing where to put this
work: MV refreshes run on "serverless pipelines" independent of the SQL
warehouse, so "warehouse cluster size doesn't limit compute costs —
billing scales with data volume processed, not warehouse
configuration." A refresh does not compete with interactive queries for
warehouse capacity.

The alternative extremes both fail in predictable ways. A plain view
recomputes the whole query on every dashboard load, so latency scales
with data. A scheduled CTAS rebuild is stale between runs, expensive at
volume, and silently wrong when a run fails. See
[`scheduled-snapshot-rebuilds.md`](scheduled-snapshot-rebuilds.md).

## What good looks like

- Gold-layer aggregates that dashboards read defined as materialized
  views, with a refresh cadence matched to how fresh the business
  actually needs them — not the fastest schedule that seemed harmless.
- Streaming tables used where the job is incremental ingestion or
  append-only transformation, materialized views where it is aggregation
  over a changing source.
- Refresh triggered by source changes rather than by clock where
  freshness matters and the source is bursty.
- MV definitions written so incremental refresh is achievable —
  aggregations the engine can maintain incrementally rather than
  constructs that force a full recompute every time.
- Known limitations checked before committing: no identity columns, no
  time travel queries, and underlying storage files used for
  incremental refresh may expose data — relevant when the MV sits on
  restricted source data.
- MVs deployed as code in a bundle alongside the pipelines that feed
  them, not created ad hoc in the SQL editor.

## How to detect

`system.information_schema.tables` and `views` distinguish plain views,
managed tables, and materialized views in a schema. The pattern to look
for is the mismatch: gold-layer objects that are plain views feeding
high-frequency dashboard queries (visible in `system.query.history` by
repetition and duration), or managed tables whose entire content is
replaced on a schedule — the latter shows up as a recurring job in
`system.lakeflow.jobs` whose SQL is a `CREATE OR REPLACE TABLE`.
Refresh history for MVs appears in the pipeline update timeline.

## References

- [Materialized views](https://docs.databricks.com/aws/en/sql/user/materialized-views)
- [Databricks SQL](https://docs.databricks.com/aws/en/sql/)
- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
