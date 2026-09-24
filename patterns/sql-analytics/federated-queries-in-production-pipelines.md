# Federated Queries in Production Pipelines

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

Scheduled pipelines, dashboards, and high-volume reporting read through
Lakehouse Federation foreign catalogs instead of ingested tables — so
production analytics depend on an operational database's availability
and capacity.

## Why it happens

Federation works immediately and looks like it removed the need for a
pipeline. A proof of concept queries the source system through a
foreign catalog, the numbers are right, and the PoC ships. Nothing
prompts a second look, because building ingestion afterwards means
doing work that appears already done.

The absence of a boundary is the real cause: there is no point at which
a federated query announces that it has become production. The
exploratory query, the dashboard built on it, and the nightly job that
grew out of that dashboard all use the same mechanism.

## Impact

- Databricks' own boundary is explicit: "when your source supports both
  Lakehouse Federation and Lakeflow Connect, Databricks recommends
  Lakeflow Connect if performance on higher data volumes and lower
  latency are priorities." Production pipelines are the case that
  guidance is about.
- **Load lands on the operational database.** Analytical scans compete
  with the transactional workload that system exists to serve — the
  original reason for separating OLTP from analytics.
- Partial pushdown makes this unpredictable. Pushdown is automatic but
  not total; a query the engine cannot push down pulls data across the
  connection, so performance varies with query shape in ways nobody
  modeled.
- Availability couples: an outage, a maintenance window, or a
  credential rotation on the source takes out the dashboards and
  pipelines built on it, often with an error that points at Databricks
  rather than at the source.
- No history. Federated access is read-only and live, so there is no
  snapshot to reprocess, audit, or time-travel — everything the bronze
  layer would have preserved is unavailable.
- Source schema changes propagate instantly to every consumer, with no
  layer in between to absorb them.

## How to fix

1. Decide per foreign catalog whether it is exploratory, a migration
   bridge, or permanent — and treat anything scheduled as the signal
   that it is no longer exploratory. See
   [`federation-for-ad-hoc-access.md`](federation-for-ad-hoc-access.md).
2. Ingest the sources that production depends on with Lakeflow Connect
   or Auto Loader, landing them in bronze and building the layers
   forward from there.
3. Where federation is genuinely the right answer but volume is the
   problem, consider the Spark Data Source API, recommended "when
   Lakehouse Federation doesn't support your source, when you need
   write access, or when you need more control over query execution."
4. Repoint pipelines and dashboards at the ingested tables, and keep
   the foreign catalog for ad-hoc investigation.
5. For catalog federation used as a migration bridge, set an end date —
   a hybrid model is fine as a deliberate end state and poor as an
   indefinite default.

## How to detect

Enumerate foreign catalogs through
`system.information_schema.catalogs` and the Unity Catalog API, then
look at how they are used: `system.query.history` reveals query
frequency, duration, and whether the caller is interactive or a
scheduled job — recurring job-driven queries against foreign tables are
the finding. `system.access.table_lineage` maps which downstream
tables, dashboards, and Genie spaces depend on foreign sources, giving
both the remediation list and the blast radius of a source outage.

## References

- [Lakehouse Federation](https://docs.databricks.com/aws/en/query-federation/)
- [Auto Loader / Lakeflow Connect for incremental ingestion](../data-ingestion/autoloader-incremental-ingestion.md)
- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
