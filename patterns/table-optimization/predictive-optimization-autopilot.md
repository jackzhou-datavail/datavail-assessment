# Predictive Optimization for Table Maintenance

**Category:** Table Optimization

`OPTIMIZE`, `VACUUM`, and `ANALYZE` run automatically on Unity Catalog
managed tables, tuned to each table's actual write pattern, instead of
being manually scheduled (or forgotten) per table.

## Why it matters

Table maintenance is exactly the kind of task that's easy to skip: nothing
visibly breaks the day someone forgets to schedule `OPTIMIZE` on a new
table, the cost shows up gradually as small-file bloat and query slowdown,
and by the time it's noticed there's a backlog of maintenance debt across
every table that was never covered. Predictive optimization removes the
"someone has to remember" step entirely and — per Databricks — is the
recommended default for all Unity Catalog managed tables.

## What good looks like

- Predictive optimization is enabled account-wide (it's on by default for
  accounts created on/after 2024-11-11; older accounts are on a rollout
  Databricks expects to complete by August 2026 — worth confirming rather
  than assuming for any pre-existing account).
- It runs three operations automatically per table: `OPTIMIZE` (including
  incremental clustering for tables using `CLUSTER BY`/`CLUSTER BY AUTO` —
  note it does *not* run `ZORDER`, which only matters for tables still on
  the legacy Z-ORDER strategy), `VACUUM` (removing unreferenced files),
  and `ANALYZE` (refreshing the statistics the query optimizer depends on
  for good query plans).
- Teams understand its scope: it only covers Unity Catalog **managed**
  tables — external tables and tables loaded via OpenSharing aren't
  covered and still need an explicit maintenance strategy.

## How to detect

Not currently queried by `data_collection/collect_data.py`. Predictive
optimization's enablement status is an account/metastore-level setting,
not a per-table system-table field — checking it means an explicit
`SYSTEM.INFORMATION_SCHEMA` or admin-console lookup rather than something
derivable from the tables this repo currently reads. The downstream
symptom — small-file accumulation on managed tables — is covered in
[`../data-ingestion/small-file-accumulation.md`](../data-ingestion/small-file-accumulation.md).

## References

- [Predictive optimization for Unity Catalog managed tables](https://docs.databricks.com/aws/en/optimizations/predictive-optimization)
- [ANALYZE TABLE ... COMPUTE STATISTICS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-analyze-compute-statistics)
