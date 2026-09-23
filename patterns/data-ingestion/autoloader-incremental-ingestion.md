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

- **File-based sources**: Auto Loader (the `cloudFiles` Structured Streaming
  source) tracks which files have already been processed by persisting file
  metadata in a scalable RocksDB key-value store inside the checkpoint
  location, so each run only reads new files. It supports both directory
  listing and (faster, more scalable) file notification discovery modes.
- **Run it inside a Lakeflow pipeline, not standalone.** Databricks'
  current guidance: *"You do not need to provide a schema or checkpoint
  location because Lakeflow pipelines automatically manage these settings
  for your pipelines."* Lakeflow pipelines are now the recommended way to
  run Auto Loader for production ingestion.
- **Managed connectors**: Lakeflow Connect provides governed, serverless
  ingestion pipelines organized by source type — database/CDC connectors
  (MySQL, PostgreSQL, SQL Server), SaaS connectors (Salesforce, HubSpot,
  Jira, Workday, and more), file connectors (Google Drive, SharePoint), and
  streaming connectors — with incremental reads built in, no custom polling
  logic required.
- **Schema evolution** is configured explicitly (`cloudFiles.schemaEvolutionMode`)
  rather than left to fail or silently drop new columns — see
  [`missing-schema-enforcement.md`](missing-schema-enforcement.md).
- New tables/pipelines default to one of these rather than a hand-rolled
  "list files, diff against a manifest table" script.

## How to detect

From this repo's real-data assessment (`data_collection/collect_data.py`):
`system.lakeflow.pipelines` and `system.lakeflow.jobs` show which
ingestion workloads exist and their `run_as` owner; `system.access.table_lineage`
with `entity_type = 'PIPELINE'` on the write side indicates a governed,
declarative ingestion path (Auto Loader inside a Lakeflow pipeline, or
Lakeflow Connect) rather than an ad-hoc script. A high ratio of
`entity_type = 'JOB'` writes with steadily increasing per-run duration as a
table grows is a signal of full-rescan ingestion rather than incremental.

## References

- [What is Auto Loader?](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/)
- [Lakeflow Connect connector concepts](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/)
