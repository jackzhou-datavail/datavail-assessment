# Query Performance Fundamentals

**Category:** SQL & Analytics

Query tuning starts from the query profile and the platform's built-in
accelerations — Photon, disk cache, result cache, data skipping,
adaptive query execution — before anyone reaches for bigger compute.

## Why it matters

Most slow queries on Databricks are slow for one of a small number of
reasons, and the query profile names which one. Databricks' guidance is
to "use the query profile feature to troubleshoot performance
bottlenecks," and the profile is also where the two clearest sizing
signals live: disk spill (size up) and scan volume disproportionate to
the filter (a layout or statistics problem, not a compute problem).

Reaching for a larger warehouse first is tempting because it sometimes
works, and it always costs. The accelerations below are free in the
sense that they are already paid for — Photon "provides fast query
performance at low cost," and the disk cache requires no code change at
all, unlike Spark caching "which demands manual implementation."

## What good looks like

- **Photon** enabled for SQL and analytical workloads; it is on by
  default on serverless SQL warehouses and serverless jobs.
- **Disk cache** relied on for repeat reads of remote Parquet data —
  Databricks "recommends using automatic disk caching," and
  cache-accelerated worker instance types are "automatically configured
  optimally" for it. **Query result cache** serves deterministic
  repeat queries outright.
- Native Spark and SQL functions preferred over Python or Scala UDFs
  wherever a built-in exists — UDFs are the most common avoidable
  bottleneck in otherwise well-written SQL.
- Data skipping working for you: statistics collected, `ANALYZE TABLE`
  run where plans need it, and liquid clustering rather than manual
  partitioning. See
  [`../table-optimization/liquid-clustering-over-partitioning.md`](../table-optimization/liquid-clustering-over-partitioning.md)
  and
  [`../table-optimization/stale-table-statistics.md`](../table-optimization/stale-table-statistics.md).
- Small files compacted (`OPTIMIZE`, auto-compaction, optimized writes)
  so scans aren't dominated by file overhead.
- **Adaptive query execution left enabled**, and range join
  optimization applied where a range predicate dominates a join.
- The whole execution chain considered, "including BI tools and
  connectors" — a fast query rendered by a tool that pulls a million
  rows is not a fast dashboard.
- Performance tested in development against production-representative
  data, with caches prewarmed, rather than discovered under load.

## How to detect

`system.query.history` is the starting point: rank statements by total
duration and by frequency × duration to find both the slow queries and
the cheap-looking ones that run constantly. The columns that matter
for triage are execution time, bytes and rows scanned, and queue time —
a high scan-to-result ratio points at layout or statistics, sustained
queue time points at warehouse concurrency, and spill points at size.
Per-statement query profiles give the detailed plan.
`system.compute.warehouses` supplies the configuration those queries
ran against.

## References

- [Best practices for performance efficiency](https://docs.databricks.com/aws/en/lakehouse-architecture/performance-efficiency/best-practices)
- [Optimize performance with caching (disk cache)](https://docs.databricks.com/aws/en/optimizations/disk-cache)
- [Query history system table](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
