# Auto Loader / Lakeflow Connect for Incremental Ingestion

**Category:** Data Ingestion

New files or source-system changes are picked up incrementally and
automatically as they arrive, instead of the ingestion job rescanning the
entire source on every run.

## Why it matters

Rescanning a full source (a cloud storage bucket, a database table, a SaaS
API) on every run gets slower and more expensive as the source grows, and it
puts unnecessary load on upstream systems. Incremental ingestion keeps run
time roughly constant regardless of how much historical data has
accumulated, and it's the only practical approach once a source reaches any
real scale.

## What good looks like

- **File-based sources**: Auto Loader (`cloudFiles` format) tracks which
  files have already been processed via a scalable file-notification or
  directory-listing backend, so each run only reads new files.
- **Managed connectors**: Lakeflow Connect ingests directly from databases
  and SaaS applications (Salesforce, Workday, SQL Server, etc.) with
  built-in incremental/CDC support, no custom polling logic required.
- **Schema evolution** is configured explicitly (`cloudFiles.schemaEvolutionMode`)
  rather than left to fail or silently drop new columns.
- New tables/pipelines default to one of these rather than a hand-rolled
  "list files, diff against a manifest table" script.

## How to detect

From this repo's real-data assessment (`data_collection/collect_data.py`):
`system.lakeflow.pipelines` and `system.lakeflow.jobs` show which
ingestion workloads exist and their `run_as` owner; `system.access.table_lineage`
with `entity_type = 'PIPELINE'` on the write side indicates a governed,
declarative ingestion path (Auto Loader inside DLT/Lakeflow Declarative
Pipelines, or Lakeflow Connect) rather than an ad-hoc script. A high ratio
of `entity_type = 'JOB'` writes with steadily increasing per-run duration as
a table grows is a signal of full-rescan ingestion rather than incremental.

## References

- <https://docs.databricks.com/ingestion/auto-loader/index.html>
- <https://docs.databricks.com/ingestion/lakeflow-connect/index.html>
