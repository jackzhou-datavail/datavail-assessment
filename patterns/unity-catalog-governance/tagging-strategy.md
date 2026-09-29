# A Single Tagging Strategy Across Data and Compute

**Category:** Unity Catalog Governance

Tags are used deliberately for four jobs — cost attribution, access
control, classification, and discovery — from one documented taxonomy,
with the important keys enforced as governed tags and applied by
automation, rather than free-text labels invented per team.

## Why it matters

"Use of tagging" usually turns out to be several unrelated practices
that happen to share a word. Compute tags drive chargeback; Unity
Catalog tags drive ABAC, classification, and search. When each grows up
separately, the same concept gets three spellings (`CostCenter`,
`cost_center`, `cc`), tag keys are case-sensitive so `Sales` and
`sales` are "two distinct tags," and none of them can be relied on —
ABAC policies miss objects, cost reports have an "unknown" bucket, and
search returns half the answers.

Governed tags solve the consistency problem: they are "account-level
tags with built-in rules for consistency and control," each with a tag
policy and a fixed set of allowed values, and only principals with the
`ASSIGN` permission can apply them. Databricks also ships system tags —
`class.*` from data classification, `system.certification_status` for
certified/deprecated assets.

## What good looks like

- **One taxonomy document** covering both families:
  - Compute / serverless tags for cost (business unit, project,
    environment) — see
    [`../platform-onboarding/cost-attribution-tagging-and-budgets.md`](../platform-onboarding/cost-attribution-tagging-and-budgets.md).
  - UC governed tags for sensitivity, domain, data owner, and
    certification on catalogs, schemas, tables, and columns.
- The keys that drive policy (sensitivity, domain) are **governed
  tags**, with `ASSIGN` limited to data stewards; free-form tags are
  allowed only for low-stakes discovery metadata.
- Tags applied by automation — IaC, bundles, compute and serverless
  usage policies, and automated classification
  ([`automated-pii-classification.md`](automated-pii-classification.md)) —
  not by hand.
- Tags set high in the hierarchy (catalog/schema) where they inherit,
  and on columns directly where needed (column tags don't inherit).
- Tags consumed: ABAC policies reference them
  ([`abac-governed-tags.md`](abac-governed-tags.md)), cost reports group
  by them, and certified tables are marked so analysts can find them.
- No sensitive information in tag values — Databricks warns explicitly
  against it.

## How to detect

Data side: `system.information_schema.catalog_tags`, `schema_tags`,
`table_tags`, `column_tags`, and `volume_tags` — measure coverage (share
of production tables with a domain/sensitivity tag), and look for
near-duplicate keys differing only in case or spelling. Governed tag
definitions and their policies come from the Tag Policies API. Compute
side: `custom_tags` coverage in `system.billing.usage` and `tags` on
`system.compute.clusters` / `warehouses`. Findings: low coverage,
inconsistent keys, sensitivity expressed as ungoverned tags, and tags
nobody consumes (no ABAC policy or cost report references them).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Governance and Unity Catalog › Use of tagging** — *primary.* Is there one tag taxonomy, are policy-driving keys governed tags, what is tag coverage on data objects and on compute spend, and are tags actually consumed?
- **Governance and Unity Catalog › ABAC policies used** — *supporting;* primary pattern is [`abac-governed-tags.md`](abac-governed-tags.md).
- **FinOps › Cost visibility (tagging for chargeback)** — *supporting;* primary pattern is [`cost-attribution-tagging-and-budgets.md`](../platform-onboarding/cost-attribution-tagging-and-budgets.md).

## References

- [Governed tags](https://docs.databricks.com/aws/en/admin/governed-tags/)
- [Apply tags to Unity Catalog securable objects](https://docs.databricks.com/aws/en/database-objects/tags)
- [Use tags to attribute and track usage](https://docs.databricks.com/aws/en/admin/account-settings/usage-detail-tags)
