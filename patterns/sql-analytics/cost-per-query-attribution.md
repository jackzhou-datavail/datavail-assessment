# Cost per Query Attribution

**Category:** SQL & Analytics

SQL warehouse cost is allocated down to individual queries — and from
there to users, dashboards, tools, and query tags — so the expensive
workloads on a shared warehouse can be identified and acted on.

## Why it matters

Billing records warehouse cost per warehouse, not per query. On a shared
warehouse serving dozens of dashboards and hundreds of analysts, that
leaves the most useful questions unanswerable: which dashboard costs the
most to refresh, which team's ad-hoc exploration dominates the bill,
whether a BI extract running every 15 minutes is worth what it costs.
Without an answer, the only lever is the warehouse's size — which
punishes every user for the behavior of a few.

The data to allocate cost already exists. `system.query.history` records
per-statement `total_task_duration_ms` ("the combined time it took to
run the query across all cores"), the `compute` struct identifying the
warehouse, `executed_by`, `client_application`, `query_source`
(dashboards, jobs, notebooks, Genie), and `query_tags`. Billing gives
the warehouse's cost per hour. Apportioning each hour's cost by each
query's share of task time is the standard approach, and Databricks
Labs publishes a reference implementation as a materialized view
(Private Preview-era sample in `databrickslabs/sandbox`,
`dbsql/cost_per_query`).

## What good looks like

- A cost-per-query table or materialized view refreshed daily, built on
  `system.query.history` + `system.billing.usage` +
  `system.billing.list_prices`.
- Rollups by `query_source` (dashboard / Genie space / job), by user,
  by `client_application`, and by `query_tags` — with `query_tags` set
  by the organization's BI and job tooling so business context travels
  with the query.
- The top-N expensive queries and dashboards reviewed alongside
  [`query-performance-fundamentals.md`](query-performance-fundamentals.md)
  — the expensive query is usually the one worth tuning first.
- Idle time acknowledged: warehouse cost not covered by any query
  (running but idle) reported separately, feeding auto-stop decisions in
  [`serverless-sql-warehouses.md`](serverless-sql-warehouses.md).
- Results feed showback to the teams generating the load
  ([`../platform-onboarding/spend-trend-monitoring.md`](../platform-onboarding/spend-trend-monitoring.md)).

## How to detect

Check whether an allocation exists: a table or materialized view
derived from `system.query.history` joined to `system.billing.usage`
(search `system.access.table_lineage` for downstream tables of
`system.query.history`, or the Labs MV name in
`system.information_schema.tables`). If none exists, the finding is
simply that warehouse cost can't be attributed below the warehouse. A
quick proxy for the assessment itself: sum `total_task_duration_ms` by
`executed_by`, `client_application`, and `query_source` over 30 days per
warehouse — the distribution is usually heavily skewed.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **AI/BI › Cost per query set up?** — *primary.* Is warehouse cost allocated to queries, users, dashboards and tools (e.g. the Labs cost-per-query MV)?

## References

- [Query history system table reference](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
- [Billable usage system table reference](https://docs.databricks.com/aws/en/admin/system-tables/billing)
- [DBSQL Cost Per Query MV (Databricks Labs sandbox)](https://github.com/databrickslabs/sandbox/blob/main/dbsql/cost_per_query/PrPr/DBSQL%20Cost%20Per%20Query%20MV%20(PrPr).sql)
