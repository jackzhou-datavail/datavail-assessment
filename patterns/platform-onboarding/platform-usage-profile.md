# Platform Usage Profile from Billing Data

**Category:** Platform Onboarding

The first step of any assessment — and a standing view for the platform
team — is a profile of *which* Databricks products the account actually
uses and how spend splits between them, derived from
`system.billing.usage.billing_origin_product` and `sku_name`.

## Why it matters

Every other finding is weighted by this one. A workspace where 70% of
DBUs are `ALL_PURPOSE_COMPUTE` needs a different conversation from one
dominated by `SERVERLESS_SQL` or `MODEL_SERVING`, and a pattern about
Genie spaces is irrelevant if `SQL_COMPUTE` barely appears. The profile
also exposes mismatches between what a team says it runs and what it
actually pays for — scheduled ETL billed as interactive compute, a
forgotten vector index, a proof-of-concept serving endpoint still
running.

The `billing_origin_product` column "shows the Databricks product
associated with the usage record," with values such as `JOBS`,
`ALL_PURPOSE_COMPUTE`, `SQL_COMPUTE`, `SERVERLESS_SQL`,
`CLASSIC_SQL_WAREHOUSE`, `LAKEFLOW`, `MODEL_SERVING`, `AI_SEARCH`,
`GENAI_API`, `AGENT_BRICKS`, `PREDICTIVE_OPTIMIZATION`, `DATA_QUALITY`,
`DATA_SHARING`, `CLEAN_ROOMS`, `DATABRICKS_APPS`, `LAKEBASE`,
`NETWORKING`, and several serverless job and notebook variants. The
list grows as products launch, so queries should group by the column
rather than hard-code it.

## What good looks like

- A product × workspace × month breakdown of DBUs and list-price cost
  exists (a dashboard, or the imported account cost-management
  dashboard) and is reviewed regularly.
- The product mix matches the intended architecture: scheduled work on
  `JOBS` / serverless jobs rather than `ALL_PURPOSE_COMPUTE`, BI on
  `SERVERLESS_SQL` rather than classic warehouses, platform features
  (`PREDICTIVE_OPTIMIZATION`, `DATA_QUALITY`) visible where they were
  meant to be enabled.
- New product lines appearing in billing are noticed and have an owner
  — the first `MODEL_SERVING` or `AGENT_BRICKS` row is a governance
  event, not just a line item.
- `product_features` is used to split further (e.g. serverless vs.
  classic, Photon) where the headline product hides the relevant
  detail.

## How to detect

```sql
SELECT billing_origin_product, sku_name, workspace_id,
       date_trunc('month', usage_date) AS month,
       SUM(usage_quantity) AS dbus
FROM system.billing.usage
WHERE usage_date >= date_sub(current_date(), 180)
GROUP BY ALL
```

Join to `system.billing.list_prices` on `cloud`, `sku_name`, and the
price validity window (`price_start_time` / `price_end_time`) to express
it as list cost. Flag: a high `ALL_PURPOSE_COMPUTE` share (see
[`all-purpose-compute-for-jobs.md`](all-purpose-compute-for-jobs.md)),
`CLASSIC_SQL_WAREHOUSE` where serverless is available, and products
with steady spend but no identifiable owner tag
([`untagged-unmonitored-spend.md`](untagged-unmonitored-spend.md)).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **General › Platform usage** — *primary.* Which Databricks products and SKUs does the account use, and how does spend split across them? Answer from `system.billing.usage` grouped by `billing_origin_product` and `sku_name`.
- **FinOps › Spend patterns** — *supporting;* primary pattern is [`spend-trend-monitoring.md`](spend-trend-monitoring.md).

## References

- [Billable usage system table reference](https://docs.databricks.com/aws/en/admin/system-tables/billing)
- [Monitor costs using system tables](https://docs.databricks.com/aws/en/admin/usage/system-tables)
- [Cost management tools on Databricks](https://docs.databricks.com/aws/en/admin/usage/)
