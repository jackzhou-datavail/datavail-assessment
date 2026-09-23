# Over-Partitioning

> ⚠️ **ANTI-PATTERN**

**Category:** Table Optimization

A table is partitioned by a high-cardinality or overly granular column —
a common offender is a daily or hourly timestamp column like
`_partition_date` — resulting in far more, far smaller partitions and
files than the data volume actually justifies.

## Why it happens

Partitioning by a date column feels like the obvious, safe default: it
matches how people think about the data ("give me last Tuesday's rows"),
and it's the pattern most tutorials teach. What isn't obvious up front is
the file-count math: a modest daily-partitioned table quickly produces
thousands of partitions, each holding a sliver of data, well under
Databricks' recommended 1 GB-per-partition floor.

## Impact

- Every file, however small, carries its own storage metadata overhead;
  a table partitioned into many tiny slices multiplies that overhead
  across the whole table, which is exactly the small-file problem — see
  [`../data-ingestion/small-file-accumulation.md`](../data-ingestion/small-file-accumulation.md)
  — except caused by the layout choice itself rather than the write
  pattern.
- Databricks' own guidance: most tables under 100 TB don't need
  partitioning at all, because Delta Lake already clusters by ingestion
  time by default. Tables under 1 TB specifically shouldn't be
  partitioned, full stop.
- An ineffective partitioning strategy chosen early is expensive to
  undo — Databricks notes it "might negatively affect query performance
  and require a full rewrite of data to fix," which is precisely the
  rigidity liquid clustering was built to avoid.

## How to fix

1. For any table under 1 TB, remove partitioning entirely and let Delta
   Lake's default ingestion-time clustering (or liquid clustering) handle
   layout.
2. For tables between 1–100 TB, use liquid clustering (`CLUSTER BY`)
   instead of partitioning — see
   [`liquid-clustering-over-partitioning.md`](liquid-clustering-over-partitioning.md).
3. If partitioning is genuinely justified (a small, stable set of
   low-cardinality values every query filters on, at real scale), size
   partitions to at least ~1 GB each — that usually means partitioning by
   month or region, not by day or hour.
4. Where an existing table is already over-partitioned, plan the rewrite
   rather than letting the layout choice fossilize further — it only gets
   more expensive to fix as the table grows.

## How to detect

Partition column and partition count/size aren't part of
`system.information_schema.tables` (the table `data_collection/collect_data.py`
currently reads) — confirming this needs `DESCRIBE DETAIL <table>`
(`numFiles`, `sizeInBytes`, and `partitionColumns`) per table. The
practical signal is a table whose average file size sits well below the
~1 GB-per-partition guidance, paired with a date/timestamp-looking
partition column name.

## References

- [When to partition tables on Databricks](https://docs.databricks.com/aws/en/tables/partitions)
- [Use liquid clustering for tables](https://docs.databricks.com/aws/en/tables/clustering)
