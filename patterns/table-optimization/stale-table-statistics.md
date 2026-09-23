# Stale or Missing Table Statistics

> ⚠️ **ANTI-PATTERN**

**Category:** Table Optimization

`ANALYZE TABLE ... COMPUTE STATISTICS` has never been run (or hasn't been
run since the table changed substantially), so the query optimizer is
planning joins and aggregations against statistics that no longer reflect
reality — or don't exist at all.

## Why it happens

Statistics collection is invisible infrastructure: a query still returns
correct results with stale or missing statistics, just a potentially much
worse execution plan, so there's no error to notice. It's exactly the kind
of maintenance task that gets skipped when it's manual, for the same
reason `OPTIMIZE`/`VACUUM` get skipped — see
[`unmanaged-vacuum-retention.md`](unmanaged-vacuum-retention.md).

## Impact

- The query optimizer uses table/column statistics to choose join
  strategies, join order, and whether to broadcast a table — without
  current statistics, it's guessing, and a plan that made sense when the
  table was 10 GB can be badly wrong at 500 GB.
- The failure mode is silent and gradual: query latency creeps up as data
  grows and the optimizer's picture of the table diverges further from
  reality, with no single event to point at as the cause.
- It compounds with other layout issues on this list — a table that's
  also over-partitioned or full of small files gives the optimizer a
  double handicap: bad statistics *and* a bad physical layout to plan
  around.

## How to fix

1. Enable predictive optimization — it runs `ANALYZE` automatically on
   Unity Catalog managed tables alongside `OPTIMIZE` and `VACUUM`, which
   is Databricks' recommended default and removes this as a manual task
   entirely.
2. Where predictive optimization isn't available (non-UC-managed tables,
   older accounts still on rollout), schedule `ANALYZE TABLE <table>
   COMPUTE STATISTICS FOR ALL COLUMNS` to run after any batch job that
   substantially changes a table's size or distribution.
3. Prioritize tables that are frequently joined or aggregated over — the
   cost of stale statistics scales with how central a table is to the
   query workload, not with its size alone.

## How to detect

Not currently queried by `data_collection/collect_data.py` — statistics
freshness isn't part of `system.information_schema.tables`. Confirming
this needs `DESCRIBE TABLE EXTENDED <table>` or `DESCRIBE DETAIL`, and
comparing the last-analyzed timestamp against how much the table has
actually changed since (row count, `last_altered` from
`system.information_schema.tables`, which this repo already reads).

## References

- [ANALYZE TABLE ... COMPUTE STATISTICS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-analyze-compute-statistics)
- [Predictive optimization for Unity Catalog managed tables](https://docs.databricks.com/aws/en/optimizations/predictive-optimization)
