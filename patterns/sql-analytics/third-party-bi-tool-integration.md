# Third-Party BI Tools on Governed Semantics

**Category:** SQL & Analytics

External BI tools (Power BI, Tableau, Sigma, and others) are inventoried
from query history and connected to the same governed tables and metric
views as Databricks-native dashboards — using identities, warehouses,
and query patterns suited to each tool.

## Why it matters

Most organizations run at least one BI tool besides AI/BI dashboards,
and it's usually the one executives look at. Those tools often arrive
before any platform governance: connected with a personal token to
whatever warehouse was handy, pulling full extracts of silver tables,
redefining metrics in the tool's own semantic model. The result is the
[`duplicated-metric-definitions.md`](duplicated-metric-definitions.md)
problem, spread across products the platform team doesn't control.

Knowing which tools are in use is the precondition for any advice, and
it's directly observable: `system.query.history.client_application`
records the "client application that ran the statement. For example:
Databricks SQL Editor, Tableau, and Power BI," with `client_driver`
(JDBC/ODBC) alongside.

The advice then becomes tool-specific. Metric views can be consumed
externally: Power BI through the connector's **Native query** option
with the `MEASURE()` pattern in DirectQuery mode; Tableau through
**Custom SQL** with `MEASURE()` or BI compatibility mode; Sigma through a
custom-SQL dataset; other JDBC/ODBC tools through pass-through SQL.

## What good looks like

- An inventory of BI tools by query volume and cost, per warehouse.
- Each tool connects with a service principal or OAuth user identity
  — not a shared personal access token — so row filters, masks, and
  audit apply to real identities.
- Tools read gold tables and metric views
  ([`metric-views-as-semantic-layer.md`](metric-views-as-semantic-layer.md)),
  not raw or silver tables
  ([`analytics-on-raw-tables.md`](analytics-on-raw-tables.md)).
- Live/DirectQuery vs. extract chosen deliberately: frequent full
  extracts of large tables are a cost and freshness smell.
- A dedicated warehouse (or warehouses) per BI workload sized for its
  concurrency pattern, and `query_tags` set by the tool where supported,
  so cost can be attributed
  ([`cost-per-query-attribution.md`](cost-per-query-attribution.md)).

## How to detect

Group `system.query.history` by `client_application` and
`client_driver` over 30–90 days: statement counts, `total_task_duration_ms`,
`read_bytes`, and distinct `executed_by`. Then, per tool: the share of
queries hitting bronze/silver vs. gold objects (join via
`system.access.table_lineage` or parse `statement_text`); whether any
queries use `MEASURE(` (metric view adoption); whether `executed_by` is
a single human account serving a whole tool (shared credentials); and
large, repetitive `SELECT *` scans on a schedule (extract refreshes).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **AI/BI › 3rd Party tools used** — *primary.* Which external tools run queries (`system.query.history.client_application`), and are they on gold tables / metric views with proper identities?

## References

- [Query history system table reference](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
- [Use metric views with external BI tools](https://docs.databricks.com/aws/en/uc-semantics/metric-views/bi-tools)
- [Use BI compatibility mode to query metric views](https://docs.databricks.com/aws/en/partners/bi/bi-metric-view)
- [Business intelligence tools](https://docs.databricks.com/aws/en/ai-bi/tools)
