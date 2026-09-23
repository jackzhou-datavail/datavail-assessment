# Unclassified Sensitive Data

> ⚠️ **ANTI-PATTERN**

**Category:** Unity Catalog Governance

Tables containing PII, PHI, or other regulated data carry no governed
tags identifying them as such, so no ABAC row-filter or column-mask
policy can protect them — because policies key off tags that were never
applied.

## Why it happens

Classification is invisible work: a table with an unmasked `ssn` or
`email` column looks and behaves identically to one without, right up
until it's the subject of a compliance audit or a breach investigation.
Nobody sets out to leave sensitive data unclassified — it happens by
default whenever classification depends on someone remembering to tag a
table manually, which reliably doesn't happen at the same rate new tables
get created.

## Impact

- Sensitive columns are exposed to anyone with `SELECT` on the table,
  full stop — no row filter or column mask can apply, because ABAC
  policies are tag-conditional and there's no tag to match.
- Compliance posture becomes a guess rather than an auditable fact:
  "which tables hold regulated data" has no authoritative answer without
  someone manually re-deriving it, which is exactly the situation
  automated classification exists to prevent.
- It compounds with [`unowned-catalog-objects.md`](unowned-catalog-objects.md)
  — a table nobody clearly owns is also a table nobody's specifically
  responsible for classifying.

## How to fix

1. Enable Databricks' agentic data classification account-wide so new
   tables get scanned (typically within 24 hours) without relying on a
   human to trigger it.
2. Run a full classification scan against the *existing* table estate,
   not just tables created going forward.
3. Turn on auto-tagging so detected classifications become governed tags
   immediately usable by ABAC policies — see
   [`abac-governed-tags.md`](abac-governed-tags.md) — rather than sitting
   in a report that requires a separate manual tagging step.
4. Add custom classifiers for business-specific sensitive-data patterns
   the built-in GDPR/HIPAA/PCI DSS/GLBA/DPDPA/PIPEDA classifiers don't
   cover, and re-run a full scan after adding them.

## How to detect

Not currently queried by `data_collection/collect_data.py` (tags aren't
part of `system.information_schema.tables`). Once a tag-reading pass is
added, the concrete check is: columns whose names match common
sensitive-data patterns (`ssn`, `email`, `dob`, `phone`, `address`, etc.)
cross-referenced against `information_schema.column_tags` for a
`class.*` or equivalent classification tag — any match with no tag is a
finding.

## References

- [Data Classification](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/data-classification)
- [Core concepts for attribute-based access control (ABAC)](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/core-concepts)
