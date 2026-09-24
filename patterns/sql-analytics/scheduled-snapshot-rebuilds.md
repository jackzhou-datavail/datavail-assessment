# Scheduled Snapshot Rebuilds

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

Derived reporting tables are maintained by a scheduled job that runs
`CREATE OR REPLACE TABLE` over the full source every night, rather than
by a materialized view or streaming table that refreshes incrementally.

## Why it happens

It is the pattern every SQL developer already knows, and it is
genuinely simple: one query, one schedule, one table. Incremental
maintenance — tracking what changed, handling late-arriving records,
merging correctly — is hard enough to implement by hand that a full
rebuild is the rational choice for a person writing it themselves.

The job also starts out cheap. A full rebuild over six months of data
finishes in two minutes, so nobody designs for the version that runs
over three years of data and takes forty. The cost grows smoothly
enough that no single day looks like the day to fix it.

## Impact

- Cost scales with total history rather than with change. Every night
  the job reprocesses years of rows to incorporate one day's worth, and
  that ratio only worsens.
- Data is stale by up to a full cycle. A dashboard reading a
  nightly-rebuilt table is answering yesterday's question, which is
  sometimes fine and is rarely stated anywhere.
- A failed run leaves either the previous day's data or, worse, a
  partially replaced table — and `CREATE OR REPLACE` discards the old
  version, so recovery means re-running rather than rolling back.
- Refresh competes with interactive queries when it runs on a shared
  warehouse, so the nightly rebuild is also why the morning dashboards
  are slow.
- The rebuild query and the table's definition drift apart, because the
  definition lives in a job rather than with the table.
- It is the analytics-layer instance of the same mistake as
  [`../data-ingestion/full-reload-instead-of-incremental.md`](../data-ingestion/full-reload-instead-of-incremental.md).

## How to fix

1. Redefine the table as a **materialized view**. The engine then picks
   "either incremental refresh (tracking only changed data) or full
   refresh (recomputing everything), depending on query structure and
   cost-effectiveness" — the incremental case you were not going to
   implement by hand.
2. Use a **streaming table** where the work is append-only ingestion or
   transformation rather than aggregation over a mutable source.
3. Set refresh to match real freshness needs — ad-hoc, on-trigger when
   source data changes, or a CRON schedule — rather than inheriting the
   old job's timing by default.
4. Write the definition so incremental refresh is achievable; some
   constructs force a full recompute every time, which puts you back
   where you started with extra indirection.
5. Note that MV refreshes run on serverless pipelines independent of
   the SQL warehouse, so refresh stops competing with interactive
   queries for warehouse capacity.
6. Check the limitations first — no identity columns, no time travel
   queries, and incremental-refresh storage files may expose underlying
   data. See
   [`materialized-views-for-serving-layers.md`](materialized-views-for-serving-layers.md).

## How to detect

Look for recurring jobs in `system.lakeflow.jobs` and
`system.lakeflow.job_run_timeline` whose SQL is a full `CREATE OR
REPLACE TABLE` or `INSERT OVERWRITE` against a reporting table —
`system.query.history` surfaces those statements with their duration
and scanned volume. Two corroborating signals: run duration growing
steadily over months for the same job, and a table in
`system.information_schema.tables` that is a managed table where the
schema's other reporting objects are materialized views.

## References

- [Materialized views](https://docs.databricks.com/aws/en/sql/user/materialized-views)
- [Databricks SQL](https://docs.databricks.com/aws/en/sql/)
- [Best practices for performance efficiency](https://docs.databricks.com/aws/en/lakehouse-architecture/performance-efficiency/best-practices)
