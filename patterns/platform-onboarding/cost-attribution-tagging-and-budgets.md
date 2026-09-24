# Cost Attribution Tagging and Budgets

**Category:** Platform Onboarding

Every compute resource and serverless workload carries custom tags for
business unit and project from day one, and account budgets with email
alerts are configured before the first large workload runs.

## Why it matters

Cost attribution is one of the few platform decisions that cannot be
applied retroactively: billing records are written with whatever tags
existed at the time, so an untagged first quarter is permanently
unattributable. Databricks' cost-optimization guidance puts "setup
tagging for cost attribution" first among its monitoring practices and
asks for "tag naming conventions" plus a minimum tag set covering
Business Units and Projects.

Custom tags "let you attribute compute usage to specific teams,
projects, or cost centers with more granularity than default tags," and
they apply across workspaces, pools, clusters, SQL warehouses, and —
through serverless usage policies — serverless notebooks, jobs,
pipelines, and model serving endpoints. The billable-usage system table
is the authoritative place those tags surface; legacy DBU usage reports
exclude serverless entirely.

Budgets are the other half. They "enable you to monitor usage across
your account" with filters for specific teams, projects, or workspaces,
and send email notifications when a threshold is crossed.

## What good looks like

- A documented tag convention (keys and allowed values) defined during
  onboarding, with a minimum set — business unit, project, environment
  — required on every resource.
- Tags applied by IaC, not by hand: compute policies and bundle
  configuration set them so a resource cannot be created untagged. For
  serverless, that means serverless usage policies.
- Budgets per team/project with alert thresholds (up to four per
  budget) routed to the people who can act on them — not only to a
  central FinOps mailbox.
- A recurring review against `system.billing.usage`: which workloads
  cost the most, which clusters are underutilized, which queries are
  expensive. Databricks frames cost management as "an ongoing process,"
  including audits and team education, not a one-time setup.
- Awareness that budgets track **list pricing** and do not account for
  credits or negotiated discounts — useful for trend and attribution,
  not for reconciling the invoice.

## How to detect

`system.billing.usage` carries a `custom_tags` map per usage record;
the share of DBUs whose records carry no business-unit or project tag
is the headline metric, and grouping untagged spend by `sku_name` and
workspace shows where to start. `system.compute.clusters` and
`system.compute.warehouses` expose per-resource tags for a
configuration-time view of the same gap. Budgets themselves are read
through the account console / Budgets API rather than SQL.
`data_collection/collect_data.py` does not currently read
`system.billing.*` — adding a tag-coverage metric there would be a
natural extension of the assessment.

## References

- [Use tags to attribute and track usage](https://docs.databricks.com/aws/en/admin/account-settings/usage-detail-tags)
- [Budgets](https://docs.databricks.com/aws/en/admin/account-settings/budgets)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
