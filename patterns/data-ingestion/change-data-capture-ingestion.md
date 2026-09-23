# Change Data Capture (CDC) for Database Ingestion

**Category:** Data Ingestion

Changes in a source database (inserts, updates, deletes) are captured and
applied to the lakehouse as a stream of changes, instead of periodically
re-extracting the entire table.

## Why it matters

Transactional databases are query-serving systems, not batch-export
systems — repeatedly running full extracts against one to feed a lakehouse
competes with the production workload it's actually there to serve. CDC
streams only what changed, so downstream tables stay in near-real-time sync
without that load, and — unlike a periodic full extract — it captures
deletes, which a plain incremental "changed since last run" query typically
misses entirely.

## What good looks like

- Source databases with native CDC (SQL Server, MySQL, PostgreSQL, and
  others) are ingested through Lakeflow Connect's managed database
  connectors, which handle CDC configuration and apply changes
  incrementally without custom pipeline code.
- Applying captured changes uses Lakeflow Declarative Pipelines' `AUTO CDC`
  API, which processes a CDC feed (from a source database or from a Delta
  table's own Change Data Feed) directly into a target table, including
  out-of-order-event handling.
- When a source can't produce a true CDC feed, `AUTO CDC FROM SNAPSHOT`
  compares consecutive full snapshots and synthesizes a change feed —
  still landing as an idempotent, incremental apply rather than a blind
  overwrite — and can maintain SCD Type 1 or Type 2 history.
- The team has a considered choice here, not a default: native CDC feed
  when the source offers one, snapshot-diffing when it doesn't, rather than
  reaching for `truncate + full reload` as the fallback either way (see
  [`full-reload-instead-of-incremental.md`](full-reload-instead-of-incremental.md)).

## How to detect

`system.lakeflow.pipelines` with `pipeline_type` indicating an ingestion
pipeline, joined to `system.access.table_lineage` where the *source* side
is an external database rather than another lakehouse table, is the
closest real signal available. Whether it's specifically CDC vs. periodic
full extract isn't distinguishable from system tables alone — same caveat
as [`full-reload-instead-of-incremental.md`](full-reload-instead-of-incremental.md);
worth a manual check of the connector/pipeline configuration for any
database-sourced ingestion pipeline.

## References

- [Change data capture and snapshots](https://docs.databricks.com/aws/en/data-engineering/what-is-cdc)
- [Lakeflow Connect connector concepts](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/)
- [The AUTO CDC APIs: simplify change data capture with pipelines](https://learn.microsoft.com/en-us/azure/databricks/ldp/cdc)
