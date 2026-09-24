# Dashboards on Governed Datasets

**Category:** SQL & Analytics

AI/BI dashboards are built on named datasets drawn from gold tables and
metric views, published with a deliberate credential model, and shared
through the account rather than by granting everyone access to the
underlying tables.

## Why it matters

A dashboard's dataset layer is where governance and reuse either happen
or don't. Dashboards "define datasets from tables, views, or custom
queries to power your dashboard visualizations," and a dataset built
from a gold table or metric view inherits the definitions everyone else
is using. A dataset built from a pasted ad-hoc query does not — it
becomes a private fork of the business logic, and nobody discovers the
divergence until two dashboards disagree.

Publishing is the second decision that gets made by accident. A
published dashboard can be shared "with anyone registered to your
Databricks account, even if they don't have access to the workspace,"
using "shared or individual data permissions." The first mode makes the
dashboard readable by people who could not query its tables — which is
often exactly the intent for an executive dashboard, and exactly wrong
for one over restricted data. Choosing it deliberately is the whole
practice.

## What good looks like

- Datasets defined over gold tables and metric views, so the numbers
  match every other consumer's. See
  [`metric-views-as-semantic-layer.md`](metric-views-as-semantic-layer.md).
- Draft and published states used as intended: iterate on the draft with
  collaborators, publish when the content is ready for its audience.
- Credential mode chosen per dashboard and recorded — shared
  credentials for broad distribution over non-sensitive aggregates,
  individual credentials where row-level entitlements must hold.
- Scheduled refreshes and email or Slack subscriptions configured for
  the dashboards people actually rely on, so distribution is automatic
  rather than someone remembering to send a screenshot.
- Expensive widgets backed by materialized views or aggregated metric
  view materializations rather than by a large query re-run on every
  page load. See
  [`materialized-views-for-serving-layers.md`](materialized-views-for-serving-layers.md).
- Dashboards deployed as code in a bundle, so a dashboard is reviewable
  and reproducible across environments.
- Ownership assigned to a group, so a dashboard outlives its author.

## How to detect

`system.query.history` attributes queries to dashboard execution, which
makes the expensive and frequently re-run widgets visible and ranked by
total warehouse time — long-running queries repeating on a refresh
schedule are the first finding. Trace each dashboard's sources through
`system.access.table_lineage` to see whether it reads gold objects or
reaches into raw tables. The Dashboards API lists dashboards with their
datasets, publish state, and credential mode, which is where the
sharing findings come from; `system.access.audit` records publish and
permission changes.

## References

- [AI/BI Dashboards](https://docs.databricks.com/aws/en/dashboards/)
- [Databricks SQL](https://docs.databricks.com/aws/en/sql/)
- [Query history system table](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
