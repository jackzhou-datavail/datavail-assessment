# Untagged, Unmonitored Spend

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Compute runs without custom tags and no budgets or alerts are
configured, so consumption is only discovered when the cloud invoice
arrives — and cannot be attributed to the team or project that caused
it.

## Why it happens

Tagging has no immediate payoff and no immediate failure. Nothing
breaks when a cluster is created untagged, so tagging discipline never
forms during the pilot phase — and the pilot phase is precisely when
the conventions would have been cheap to establish. Budgets are skipped
for the same reason: while spend is small, an alert threshold feels
like ceremony.

The trap is that billing history is written once. Usage records carry
whatever tags existed at the time, so tagging introduced in month six
does nothing for months one through five. By the time anyone asks "who
is spending this," the answer for the period in question is permanently
unavailable.

## Impact

- Spend cannot be attributed. Without tags, `system.billing.usage`
  shows what was consumed but not by whom or for what — so cost
  conversations become opinion rather than data.
- No early warning. Budgets exist to send "email notifications when the
  monthly budget is reached"; without them, a runaway cluster or a
  mis-sized warehouse runs until someone happens to look.
- Serverless is the blind spot that bites hardest: legacy DBU usage
  reports exclude serverless usage entirely, so teams relying on those
  reports are reading an increasingly incomplete picture as serverless
  adoption grows.
- Cost optimization work has nowhere to start — you cannot identify
  "expensive queries, underutilized clusters" per team without the
  dimension to group by.
- Chargeback and showback to business units become impossible, which
  in most organizations means cost accountability stays with the
  platform team regardless of who generated the spend.

## How to fix

1. Define the tag convention now — keys, allowed values, and a required
   minimum set covering business unit and project. Retrofitting the
   convention is cheap; retrofitting the history is impossible.
2. Apply tags through automation rather than instructions: compute
   policies and bundle configuration for classic compute, serverless
   usage policies for serverless notebooks, jobs, pipelines, and
   serving endpoints. See
   [`cost-attribution-tagging-and-budgets.md`](cost-attribution-tagging-and-budgets.md).
3. Create budgets per team or project with alert thresholds (up to four
   each), routed to the people who can act, not only to a central
   mailbox.
4. Treat `system.billing.usage` as the authoritative source — not the
   legacy DBU reports — and build a recurring cost review on it.
5. Attack the largest untagged bucket first; it is usually one or two
   always-on clusters or warehouses, not a long tail.

## How to detect

`system.billing.usage.custom_tags` is the direct measure: compute the
share of DBUs whose records carry no business-unit or project tag, then
group the untagged remainder by `sku_name` and workspace to find where
it comes from. `system.compute.clusters` and
`system.compute.warehouses` give the configuration-time view of which
resources lack tags. Budget definitions are read through the account
console / Budgets API rather than SQL — the finding is simply their
absence. `data_collection/collect_data.py` does not read
`system.billing.*` today.

## References

- [Use tags to attribute and track usage](https://docs.databricks.com/aws/en/admin/account-settings/usage-detail-tags)
- [Budgets](https://docs.databricks.com/aws/en/admin/account-settings/budgets)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
