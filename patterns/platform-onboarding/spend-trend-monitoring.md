# Spend Trend Monitoring

**Category:** Platform Onboarding

Consumption is tracked as a trend — month over month, per product and
per team, against a forecast — so the organization can say whether it
is on a healthy path, not just what last month's invoice was.

## Why it matters

A single month's cost says little. The same number can be a platform
growing in step with the workloads moved onto it, or one that doubled
because three idle warehouses and a forgotten serving endpoint are
compounding. What distinguishes them is shape: growth that tracks new
use cases and user counts is healthy; growth concentrated in one SKU,
one workspace, or one untagged bucket, with no matching increase in
jobs or queries, is not.

Trend monitoring is also what turns tagging and budgets
([`cost-attribution-tagging-and-budgets.md`](cost-attribution-tagging-and-budgets.md))
into decisions. Budgets alert on thresholds; trends explain why a
threshold was crossed and whether it will be crossed again next month.

## What good looks like

- A cost dashboard built on `system.billing.usage` (or the account's
  imported cost-management dashboards) showing monthly DBUs and list
  cost by `billing_origin_product`, workspace, and business-unit tag,
  with month-over-month change.
- **Unit economics** alongside totals — cost per job run, per query, per
  active user, per served request — so growth can be judged against
  output, not just in absolute terms. See
  [`../sql-analytics/cost-per-query-attribution.md`](../sql-analytics/cost-per-query-attribution.md).
- A forecast or target per team, and budgets with alert thresholds
  that fire before month end, routed to the people who own the spend.
- A regular (monthly) cost review that looks at the top movers and ends
  with named actions — a right-sizing backlog
  ([`compute-right-sizing.md`](compute-right-sizing.md)), not just a
  chart.
- Healthy-path signals: the serverless share rising as classic declines
  (if serverless is the strategy), `ALL_PURPOSE_COMPUTE` share falling,
  untagged share falling, and spend growth explained by new workloads.

## How to detect

From `system.billing.usage` joined to `system.billing.list_prices`:
monthly cost by product and workspace for the last 6–12 months, and the
month-over-month growth rate per series. Flag series with sustained
growth above the account's overall rate, sudden step changes (a new
always-on resource), and growth with no matching increase in activity
(`system.lakeflow.job_run_timeline` run counts, `system.query.history`
statement counts). Budget definitions are read from the Budgets API /
account console — their absence is the finding. The Governance Hub cost
page (beta) gives admins a consolidated view where available.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **FinOps › Spend patterns** — *primary.* Is month-over-month spend growth explained by new workloads, with the serverless share rising and all-purpose / untagged shares falling? Are unit costs tracked?
- **General › Platform usage** — *supporting;* primary pattern is [`platform-usage-profile.md`](platform-usage-profile.md).
- **AI/BI › Cost per query set up?** — *supporting;* primary pattern is [`cost-per-query-attribution.md`](../sql-analytics/cost-per-query-attribution.md).
- **Platform management › Observability tools in place?** — *supporting;* primary pattern is [`observability-from-system-tables.md`](observability-from-system-tables.md).

## References

- [Cost management tools on Databricks](https://docs.databricks.com/aws/en/admin/usage/)
- [Create and monitor budgets](https://docs.databricks.com/aws/en/admin/account-settings/budgets)
- [Monitor costs using system tables](https://docs.databricks.com/aws/en/admin/usage/system-tables)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
