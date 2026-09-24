# Metric Views as the Semantic Layer

**Category:** SQL & Analytics

Business metrics are defined once as Unity Catalog metric views and
consumed from there by dashboards, alerts, Genie agents, and external
BI tools — instead of being re-expressed in each tool's own modeling
layer.

## Why it matters

Metric views let you "define metrics once and query them at runtime" by
separating the measure definition from the fields used to group and
filter it. The problem they solve is structural: traditional views
"lock in aggregations and groupings at creation time," so every new
slice of an existing metric becomes a new view, and the definitions
drift apart as they multiply.

The payoff is the one executives notice: "every user across the
organization reports the same value for the same KPI." A metric view
defines, say, revenue per active customer once; the engine then handles
computing it correctly when grouped by region, by month, or by both. See
[`duplicated-metric-definitions.md`](duplicated-metric-definitions.md)
for the failure this prevents.

Because metric views are Unity Catalog objects, the definition is also
governed: you "control access, enable collaborative editing, and manage
the metric view lifecycle" with the same mechanisms as tables.

## What good looks like

- Metric views modeling the shapes the warehouse already has: star
  schemas (fact joined to dimensions), snowflake schemas (multi-level
  dimension joins), and one-to-many relationships.
- **Composability** used deliberately — complex measures built by
  referencing other measures "rather than rewriting their logic, which
  improves consistency, auditability, and maintenance."
- Window measures for time-series work (moving averages, running
  totals, period-over-period) rather than each dashboard reimplementing
  them.
- Materialization chosen per usage: "an unaggregated materialization as
  a fallback, and aggregated materializations for your known
  high-traffic queries" — the right fit when an expensive join backs a
  dashboard of known widgets.
- Every consumption channel pointed at the metric view: SQL editors and
  notebooks, dashboards and alerts, Genie agents, and external BI tools
  (Power BI, Tableau, Sigma).
- **Agent metadata** filled in — display names, format specifications,
  and synonyms — which "improves LLM accuracy by providing business
  context," making the semantic layer the thing that makes Genie
  reliable rather than a separate effort.
- Metric views deployed as code and reviewed like code, since a change
  moves every number that depends on them.

## How to detect

Metric views are Unity Catalog objects, so they enumerate through
`system.information_schema` alongside tables and views; the first check
is simply whether any exist in the schemas that back reporting. The
more telling signal is in `system.query.history`: repeated,
near-identical aggregate expressions issued by different dashboards or
BI tools against the same fact tables indicate the metric is being
redefined per consumer. Dashboard and Genie definitions name their
sources directly — consumers reading base tables rather than metric
views is the concrete finding.

## References

- [Unity Catalog metric views](https://docs.databricks.com/aws/en/uc-semantics/metric-views/)
- [Advanced techniques for metric views](https://docs.databricks.com/aws/en/business-semantics/metric-views/advanced-techniques)
- [Choose a materialization type for metric views](https://docs.databricks.com/aws/en/business-semantics/metric-views/choose-materialization-type)
