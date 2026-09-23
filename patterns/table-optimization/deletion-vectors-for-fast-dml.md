# Deletion Vectors for Fast UPDATE / DELETE / MERGE

**Category:** Table Optimization

Row-level `UPDATE`, `DELETE`, and `MERGE` operations mark affected rows in
lightweight metadata instead of rewriting the entire Parquet file that
contains them, deferring the physical rewrite to a scheduled compaction
step.

## Why it matters

Without deletion vectors, modifying even a single row means rewriting the
whole file it lives in — on a table with large files, a `DELETE` that
logically touches a handful of rows can mean rewriting gigabytes of
unrelated data. Deletion vectors make the change nearly instantaneous by
marking rows as deleted in metadata and applying that metadata at read
time to resolve the current table state; the expensive physical rewrite
happens later, in bulk, on a schedule the table owner controls rather than
inline with every DML statement.

## What good looks like

- Deletion vectors are enabled on tables that see meaningful UPDATE/DELETE/MERGE
  volume, especially ones with large files where per-row rewrites would be
  expensive.
- `REORG TABLE ... APPLY (PURGE)` runs on a real schedule to rewrite files
  containing soft-deleted rows and reclaim storage — not left indefinitely,
  since file compaction alone doesn't guarantee resolving deletion-vector
  entries.
- `VACUUM` runs after `PURGE` to actually remove the old file versions
  from cloud storage. For tables with deletion vectors, predictive
  optimization already sequences this correctly (`PURGE` before
  `VACUUM`) — see
  [`predictive-optimization-autopilot.md`](predictive-optimization-autopilot.md).
- Teams that need firm compliance deletion guarantees (e.g. GDPR
  "right to erasure") understand that a `DELETE` alone is a soft-delete
  until purged, and schedule `PURGE` accordingly rather than assuming the
  row is physically gone the moment `DELETE` returns.

## How to detect

Not currently queried by `data_collection/collect_data.py` — deletion
vector enablement is a table property, not something exposed in
`system.information_schema.tables`. Checking it means `DESCRIBE TABLE
EXTENDED` or `SHOW TBLPROPERTIES` per table (`delta.enableDeletionVectors`).

## References

- [Deletion vectors in Databricks](https://docs.databricks.com/aws/en/tables/features/deletion-vectors)
- [Remove unused data files with vacuum](https://docs.databricks.com/aws/en/tables/operations/vacuum)
