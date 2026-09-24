# Observability from System Tables

**Category:** Platform Onboarding

System tables are enabled across all metastores at onboarding time, and
the platform's monitoring — cost, job SLAs, query performance, data
quality — is built on them rather than on ad-hoc screenshots of the
jobs UI.

## Why it matters

"System tables are a Databricks-hosted analytical store of your
account's operational data," covering billing usage, audit logs, query
history, job runs, data lineage, and cluster events. They are the only
retrospective record of what the platform did: if a schema isn't
enabled, the history simply isn't collected, and you cannot enable it
after the fact to answer a question about last month.

Enabling them early is therefore load-bearing for everything else in
this category. Cost attribution needs `system.billing.usage`; ownership
and access review need `system.access.audit` and
`system.information_schema`; job reliability needs
`system.lakeflow.job_run_timeline`. This repo's own assessment is built
entirely on that foundation — `data_collection/collect_data.py` reads
`system.access.table_lineage`, `system.lakeflow.*`, `system.mlflow.*`,
`system.serving.*`, and `system.information_schema.tables`, and
fabricates nothing.

## What good looks like

- System tables enabled across **all** metastores, not just the one
  someone was investigating an incident in.
- Job and pipeline failures raise something: "email notifications or
  webhooks for critical job failures," with SLA tracking queried from
  `system.lakeflow.job_run_timeline` rather than watched by hand.
- Defined SLAs and alert thresholds for critical workloads, and
  runbooks documented for the operational scenarios those alerts fire
  on.
- Data quality monitors on critical production tables — "especially
  gold layer tables" — using time-series or snapshot monitoring.
- Query performance investigated with query profiles on serverless/SQL
  warehouses (stage-level execution metrics) and the Spark UI for
  classic compute.
- Model serving endpoints monitored through inference tables: request
  counts, latency, throughput.
- Third-party integration (Datadog, Prometheus, CloudWatch) where the
  organization needs one pane of glass — but the Databricks-side source
  of truth stays the system tables.
- Granularity is chosen deliberately: Databricks' own caveat is to
  "balance monitoring granularity with operational overhead and costs"
  rather than turning on everything at once.

## How to detect

`SHOW SCHEMAS IN system` lists which schemas are enabled in a given
metastore — an absent `billing`, `access`, `compute`, or `lakeflow`
schema is the finding itself. Beyond enablement, the useful check is
coverage: the share of production jobs in `system.lakeflow.jobs` with
no configured failure notification, and the share of gold-layer tables
with no entry in `system.data_quality_monitoring`. Alert definitions
and their evaluation history live in `system.alert`.

## References

- [Monitor account activity with system tables](https://docs.databricks.com/aws/en/admin/system-tables/)
- [Phase 9: Design observability strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/observability)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
