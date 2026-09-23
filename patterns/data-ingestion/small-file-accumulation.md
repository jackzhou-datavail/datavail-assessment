# Small-File Accumulation at Landing

> ⚠️ **ANTI-PATTERN**

**Category:** Data Ingestion

Streaming or frequent micro-batch ingestion writes many small files to a
table instead of periodically compacting them into fewer, larger ones, and
nothing in the pipeline ever cleans that up.

## Why it happens

Each streaming micro-batch (or each small frequent batch job) naturally
writes its own set of files — that's correct and unavoidable at write time.
The problem isn't the write path, it's the absence of any subsequent
compaction step, which is easy to omit entirely since ingestion "works"
without it; the cost only shows up later, in read performance, and doesn't
have an obvious single cause to point at.

## Impact

Small files hurt reads two ways: they cause excessive I/O overhead (many
small reads instead of few large ones), and they bloat the Delta
transaction log with metadata for every file, which slows query planning
before a single row is even scanned. The effect compounds — a bronze table
fed by frequent micro-batches for months can accumulate enough small files
that every downstream query, including ones that never touch most of the
historical data, pays a fixed tax just to plan.

## How to fix

1. Enable **Predictive Optimization** on Unity Catalog managed tables —
   Databricks then runs `OPTIMIZE` automatically on the workspace's behalf.
   This is the recommended default for all UC managed tables.
2. Where predictive optimization isn't in play, enable **Auto Compaction**
   (`delta.autoOptimize.autoCompact`), which merges small files into
   ~128 MB files as a post-write step — smaller than a full `OPTIMIZE` run
   (which targets ~1 GB files) but requiring no separate maintenance job.
3. For tables that need explicit control, schedule periodic `OPTIMIZE`
   runs sized to actual write frequency — a table receiving continuous
   micro-batches needs it far more often than one refreshed nightly.

## How to detect

Not directly exposed by the system tables this repo's assessment queries
today (`system.information_schema.tables` doesn't report file counts).
`DESCRIBE DETAIL <table>` gives `numFiles` and `sizeInBytes` per table —
dividing them yields average file size, and a bronze table averaging well
under ~100 MB per file, fed by a `PIPELINE`/`JOB` entity in
`system.access.table_lineage` on a frequent schedule, is the pattern to
look for. Not currently wired into `data_collection/collect_data.py`
(would need a per-table `DESCRIBE DETAIL` pass, which doesn't scale to
every table in a workspace the way the other queries do) — a candidate for
a future, opt-in deeper scan rather than the standard run.

## References

- [Optimize data file layout](https://docs.databricks.com/aws/en/delta/optimize)
- [Control data file size](https://docs.databricks.com/aws/en/tables/tune-file-size)
