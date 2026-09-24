# Separate Ingestion and Transformation Pipelines

**Category:** Orchestration & Reliability

Ingestion and transformation live in distinct pipelines, so each can be
scheduled, scaled, failed, and repaired on its own terms instead of
sharing one fate.

## Why it matters

Databricks' pipeline guidance is to "separate ingestion and
transformation into distinct pipelines to enable independent
scheduling and troubleshooting." The reasoning is that the two have
genuinely different characteristics and the difference compounds.

Ingestion is driven by the source: it runs when data arrives, it fails
for reasons outside your control (a credential expired, an API is
down), and its correct response to a bad source is usually to stop and
wait. Transformation is driven by your own logic: it runs when
upstream data is ready, it fails because of a code change, and its
correct response is to be fixed and re-run.

Combine them and every failure has the same blast radius. A transient
source outage at 3am takes down the transformation logic that had
nothing to do with it; a bug in a gold aggregate forces a re-run that
re-ingests data unnecessarily. You also lose the ability to scale them
differently, which matters because ingestion is often small and
frequent while transformation is large and periodic.

## What good looks like

- One pipeline landing raw data into bronze, another moving bronze
  through silver to gold, connected by the table rather than by shared
  code.
- Dataset types chosen per job: "streaming tables are the right choice
  for data ingestion and low-latency streaming transformations," while
  materialized views suit "complex transformations and analytical
  queries" and temporary views organise intermediate logic without
  storage cost.
- Medallion layering used as the organising principle — bronze for raw
  ingestion, silver for transformation, gold for analytics — with the
  layer boundaries as the natural pipeline boundaries. See
  [`../sql-analytics/medallion-layering-for-analytics.md`](../sql-analytics/medallion-layering-for-analytics.md).
- Independent schedules: ingestion triggered by arrival, transformation
  triggered by ingestion completing or on its own cadence.
- Incremental refresh preserved where it applies, since for
  materialized views "incremental refresh is significantly cheaper than
  rerunning the query from scratch on each pipeline trigger."
- Liquid clustering (`CLUSTER BY AUTO`) rather than static partitioning
  for the layout of what these pipelines write.
- Both pipelines deployed from bundles with per-environment targets, so
  dev, staging, and production differ only in configuration.

## How to detect

`system.lakeflow.pipelines` lists pipelines and
`system.access.table_lineage` shows what each reads and writes. The
signal is a single pipeline whose write targets span bronze *and* gold
— it is doing both jobs. Corroborate with
`system.lakeflow.pipeline_update_timeline`: a pipeline with a long
update duration and a high failure rate relative to its peers is
typically one that has absorbed both responsibilities, since it fails
for both sets of reasons.

## References

- [Best practices for Lakeflow pipelines](https://docs.databricks.com/aws/en/ldp/best-practices)
- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [Auto Loader / Lakeflow Connect for incremental ingestion](../data-ingestion/autoloader-incremental-ingestion.md)
