# Full-Table Reload Instead of Incremental Ingestion

> ⚠️ **ANTI-PATTERN**

**Category:** Data Ingestion

Every run of the ingestion job truncates (or overwrites) the target table
and reloads the entire source from scratch, rather than processing only
what's new or changed since the last run.

## Why it happens

It's the simplest thing to write first — `df.write.mode("overwrite")` needs
no state tracking, no watermark, no checkpoint, and it's trivially correct
the day you write it. It keeps working right up until the source grows past
the point where a full scan fits in the job's time/cost budget, at which
point it's load-bearing production code that's expensive to change.

## Impact

Databricks' own guidance is blunt about this: *"Full reloads — where the
entire source dataset is re-read and rewritten on every run — are simple to
implement but scale poorly."* Organizations that migrated from full reloads
to incremental streaming have reported cost reductions of 50% or more even
as data volumes grew tenfold, since incremental patterns keep processing
cost roughly constant regardless of total table size.

- Run time and compute cost scale with total source size, not with how much
  actually changed — a job that took 5 minutes at launch can take hours a
  year later, on the same schedule.
- Upstream systems (databases, SaaS APIs) take the load of a full extract
  every run, which can throttle or degrade the source for other consumers.
- A failed or slow full reload leaves the target table either stale or
  briefly empty/inconsistent for any reader mid-refresh, unless it's
  carefully double-buffered.
- It hides the actual rate of change in the source, since "what changed
  today" is never computed or observable anywhere.

## How to fix

1. Switch to Auto Loader (file sources) or Lakeflow Connect (database/SaaS
   sources) for incremental, checkpoint-tracked ingestion — see
   [`autoloader-incremental-ingestion.md`](autoloader-incremental-ingestion.md).
2. Where a true incremental source isn't available, add a watermark column
   (an updated-at timestamp or monotonic ID) and filter the extract to rows
   newer than the last successful run.
3. If a periodic full reconciliation is genuinely needed (some sources
   don't reliably expose deletes), keep it — but make it an explicit,
   separate, infrequent job, not the only ingestion path.

## How to detect

Not directly observable from Unity Catalog system tables alone (they don't
expose *how* a write was constructed). The practical signal is indirect:
in `system.lakeflow.job_run_timeline` / `pipeline_update_timeline`, an
ingestion job/pipeline whose `run_duration_seconds` grows roughly linearly
with the target table's row count over time, on a workload with no
incremental watermark visible in its configuration, is a strong hint. Worth
a manual code-review pass on any ingestion job that predates the team's
adoption of Auto Loader / Lakeflow Connect.

## References

- [Data Pipeline Best Practices (Databricks Blog)](https://www.databricks.com/blog/data-pipeline-best-practices)
- [What is Auto Loader?](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/)
