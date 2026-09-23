# Liquid Clustering Instead of Manual Partitioning / Z-ORDER

**Category:** Table Optimization

New tables use `CLUSTER BY` (liquid clustering) as their data-layout
strategy, rather than a manually chosen partition column, `OPTIMIZE ...
ZORDER BY`, or no layout strategy at all.

## Why it matters

Databricks' current guidance opens with the recommendation flatly stated:
*"Databricks recommends liquid clustering for all managed tables."* Liquid
clustering replaces both table partitioning and `ZORDER` as the default
data-layout technique. The reason it displaced both: partitioning and
Z-ORDER are effective right up until access patterns change or the wrong
column was chosen up front, at which point fixing it means a full data
rewrite. Liquid clustering keys can be changed with `ALTER TABLE ...
CLUSTER BY` at any time, with no immediate rewrite required — new writes
and future `OPTIMIZE` runs pick up the new keys incrementally.

## What good looks like

- New tables are created with `CLUSTER BY (col1, col2, ...)` from the
  start, chosen based on actual filter/join columns.
- `CLUSTER BY AUTO` (Databricks Runtime 15.4 LTS+) is used where query
  patterns aren't known in advance or may shift — predictive optimization
  then selects and adjusts clustering keys based on observed workloads,
  only reclustering when the cost is justified.
- Clustering keys are revisited with `ALTER TABLE ... CLUSTER BY` when
  access patterns genuinely change, instead of living with a stale choice
  because changing it used to mean a full rewrite.
- Partitioning is reserved for the narrow case it's still good at: a
  small number of low-cardinality values that essentially every query
  filters on and that never change (Databricks still recommends trying
  liquid clustering first even above 100 TB).

## How to detect

Not currently queried by `data_collection/collect_data.py` — clustering
configuration lives in `DESCRIBE TABLE EXTENDED` / `information_schema.tables`'s
clustering columns, not in the subset of `system.information_schema.tables`
fields this repo currently reads. The practical anti-pattern to look for
is covered in [`over-partitioning.md`](over-partitioning.md): tables under
1 TB with a manually chosen partition column and no clustering keys are
the clearest sign this pattern wasn't adopted.

## References

- [When to partition tables on Databricks](https://docs.databricks.com/aws/en/tables/partitions)
- [Use liquid clustering for tables](https://docs.databricks.com/aws/en/tables/clustering)
- [Debunking 8 data layout myths (Databricks Blog)](https://www.databricks.com/blog/debunking-8-data-layout-myths-why-liquid-clustering-outperforms-partitioning)
