# Medallion Layering for Analytics

**Category:** SQL & Analytics

Analytical consumers — dashboards, Genie spaces, BI tools, ad-hoc SQL —
read from gold tables shaped for business questions, not from bronze or
raw landing tables, with each layer's role kept distinct.

## Why it matters

The medallion architecture exists "to incrementally and progressively
improve the structure and quality of data as it flows through each
layer" from bronze to silver to gold. The value for analytics is the
gold layer specifically: "highly refined views of the data that drive
downstream analytics, dashboards, ML, and applications," typically
aggregated and filtered, "containing semantically meaningful datasets
that map to business functions and needs."

Two rules from the layering guidance carry most of the weight:

- **Do not write to silver directly from ingestion.** Databricks warns
  this "will introduce failures due to schema changes or corrupt
  records in data sources" — bronze exists to absorb that.
- **Implement data quality checks at each layer**, not only at the end,
  so a bad record is caught where it entered rather than where it was
  noticed.

Bronze's role is to be "the single source of truth, preserving the
data's fidelity" and to enable "reprocessing and auditing by retaining
all historical data" — which is exactly why it is the wrong thing to
point a dashboard at.

## What good looks like

- Gold tables modeled for consumption: business-meaningful names,
  documented columns, the grain a stakeholder would expect, and the
  filters and aggregations already applied.
- Dashboards, Genie spaces, and BI tools granted access to gold (and
  metric views over gold), with bronze and silver access limited to the
  teams that build the pipelines.
- Bronze appended incrementally and kept immutable; reads from bronze
  configured as streaming reads where sources are append-only, "with
  batch reads reserved for small datasets."
- Silver doing the cleansing, deduplication, and normalization work, so
  gold aggregates trustworthy inputs rather than repeating the cleanup.
- Quality expectations declared at each hop, so a layer's contract is
  enforced rather than assumed.
- Layers separated by schema (or catalog) so the boundary is a
  permission, not a naming convention.

## How to detect

`system.access.table_lineage` is the direct source: trace which tables
each dashboard, Genie space, or notebook query reads, and flag
consumers whose upstream is a bronze or raw table rather than a gold
one. `system.query.history` shows which tables interactive and
dashboard queries actually hit, ranked by frequency — the top raw
tables in that list are the finding. `system.information_schema.tables`
reveals whether the layering exists structurally at all (distinct
bronze/silver/gold schemas) or is only implied by table name prefixes.

## References

- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [Best practices for reliability](https://docs.databricks.com/aws/en/lakehouse-architecture/reliability/best-practices)
- [Bronze layer immutability](../data-ingestion/bronze-layer-immutability.md)
