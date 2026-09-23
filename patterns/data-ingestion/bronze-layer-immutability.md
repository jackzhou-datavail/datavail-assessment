# Bronze Layer Immutability (Append-Only Raw Landing)

**Category:** Data Ingestion

Bronze/raw tables are written by exactly one ingestion path, in append-only
fashion, and are never the target of ad-hoc `UPDATE`, `DELETE`, or manual
`MERGE` statements.

## Why it matters

Bronze is meant to be a faithful, replayable copy of what the source
actually sent — the thing you fall back to when a downstream transformation
turns out to be wrong. The moment something other than the ingestion
pipeline can write to it, that guarantee is gone: `CONSTRAINT`s and
expectations defined on the pipeline stop being enforced, replays from
bronze stop being trustworthy, and every table downstream of the mutated
one inherits a discrepancy nobody can explain from lineage alone.

## What good looks like

- Write access to bronze schemas is granted only to the service
  principal/pipeline identity that owns ingestion — not to individual
  engineers' interactive identities.
- Corrections to bad source data happen by re-ingesting or backfilling
  through the same pipeline, not by hand-editing the bronze table.
- If a table genuinely needs point-in-time correction (e.g. GDPR deletes),
  that's an explicit, audited, documented exception — not routine practice.

## How to detect

This is the flagship signal `data_collection/collect_data.py` computes on
the `real_data` branch: `system.access.table_lineage` rows where
`target_table_full_name` matches a bronze-layer table and `entity_type` is
`NULL`, `NOTEBOOK`, or `DBSQL_QUERY` (i.e. the write did *not* come from a
governed `JOB` or `PIPELINE` run). See `gold_bronze_table_edits` and the
`direct_write_findings` CTE in `gold_remediation_backlog` for the exact
query. A table with a nonzero count there is a live instance of this
anti-pattern — see
[`direct-writes-to-bronze-tables.md`](direct-writes-to-bronze-tables.md).

## References

- <https://docs.databricks.com/lakehouse/medallion.html>
