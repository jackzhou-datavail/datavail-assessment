# Lakehouse Federation for Ad-Hoc Access

**Category:** SQL & Analytics

Lakehouse Federation is used for exploratory and low-volume access to
external systems — ad-hoc reporting, BI against an operational
database, proof-of-concept work — with genuine ingestion used for
anything that needs volume, latency, or reliability.

## Why it matters

Lakehouse Federation gives "governed, read-only access to external data
through Unity Catalog foreign catalogs, with automatic query pushdown
and fine-grained access controls at the table level." That combination
is genuinely valuable: you get UC governance over a system you have not
migrated, without building a pipeline first.

Its intended use is stated plainly — federation suits "ad hoc
reporting, BI, and proof-of-concept access to operational databases"
where minimizing data movement and keeping a live connection matter
more than throughput. The boundary is equally plain: "when your source
supports both Lakehouse Federation and Lakeflow Connect, Databricks
recommends Lakeflow Connect if performance on higher data volumes and
lower latency are priorities."

The second legitimate use is migration. Catalog federation fits when
"migrating to Unity Catalog but need to incrementally phase in data
managed from a foreign catalog," or when a hybrid model is the
deliberate end state rather than an accident.

## What good looks like

- Federation reached for first when the question is "can we see this
  data at all," and re-evaluated once the answer is yes and the query
  is going to run daily.
- A documented decision per foreign catalog: exploratory, migration
  bridge, or permanent — with the permanent case justified by
  something other than nobody having built the pipeline.
- Production pipelines reading ingested tables, not foreign ones. See
  [`federated-queries-in-production-pipelines.md`](federated-queries-in-production-pipelines.md).
- Lakeflow Connect used where the source supports it and volume or
  latency matters; the Spark Data Source API where "Lakehouse
  Federation doesn't support your source, when you need write access,
  or when you need more control over query execution."
- Foreign catalogs governed like any other UC object, with table-level
  access controls set rather than inherited by default.
- Awareness that pushdown is automatic but partial — a query the engine
  cannot push down pulls data across the connection, and the source
  database feels it.

## How to detect

Foreign catalogs enumerate through `system.information_schema.catalogs`
and the Unity Catalog API, which identifies what is federated at all.
The finding is usage shape rather than existence:
`system.query.history` shows how often foreign tables are queried and
by what — scheduled or job-driven queries against a foreign catalog,
especially high-frequency or long-running ones, indicate federation
doing a pipeline's job. `system.access.table_lineage` shows which
downstream tables and dashboards depend on foreign sources, which is
also the blast radius if the external system goes down.

## References

- [Lakehouse Federation](https://docs.databricks.com/aws/en/query-federation/)
- [Query history system table](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
- [Auto Loader / Lakeflow Connect for incremental ingestion](../data-ingestion/autoloader-incremental-ingestion.md)
