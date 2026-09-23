# Automated Sensitive-Data Classification

**Category:** Unity Catalog Governance

Sensitive columns (PII, PHI, and other regulated data) are identified and
tagged automatically and continuously, rather than relying on whoever
built a table to remember to flag it.

## Why it matters

Manual classification decays: the person who knew a column held customer
SSNs moves teams, a new table gets added without anyone thinking to review
it, and six months later nobody can say with confidence which tables in
the workspace actually hold regulated data. Databricks' Data Classification
feature addresses this with an agentic system — described as using "an
agentic AI system to automatically classify and tag any tables in Unity
Catalog" — that scans new tables (typically within 24 hours of creation)
and keeps classification current without waiting for a manual audit.

## What good looks like

- Data classification is enabled account-wide rather than run as an
  occasional one-off scan.
- Detected classifications are auto-tagged as governed tags (e.g.
  `class.email_address`), making them immediately usable by ABAC row
  filter/column mask policies — see
  [`abac-governed-tags.md`](abac-governed-tags.md) — instead of sitting in
  a report nobody acts on.
- Built-in classifiers cover named compliance frameworks (GDPR, HIPAA,
  PCI DSS, GLBA, DPDPA, PIPEDA); custom classifiers extend detection to
  business-specific sensitive-data patterns the built-in ones don't cover.
- A full manual re-scan is triggered after adding a new custom
  classifier, so existing tables get evaluated against it too, not just
  tables created going forward.

## How to detect

Not currently queried by `data_collection/collect_data.py` — classification
tags live in Unity Catalog's tag surface
(`information_schema.column_tags`, `SHOW TAGS`), not in
`system.information_schema.tables`. Once wired up, the practical
anti-pattern is the same as for ABAC generally: columns whose names imply
sensitive content but that carry no `class.*` tag, especially in schemas
that also show a high proportion of tables with `has_owner_tag = FALSE` —
low ownership accountability and missing classification tend to go
together.

## References

- [Data Classification](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/data-classification)
- [ABAC row filtering and column masking, governed tags, and data classification are GA (Databricks Blog)](https://www.databricks.com/blog/abac-row-filtering-and-column-masking-policies-governed-tags-and-data-classification-are-now)
