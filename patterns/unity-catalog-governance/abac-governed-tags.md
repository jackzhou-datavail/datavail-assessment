# Attribute-Based Access Control (ABAC) with Governed Tags

**Category:** Unity Catalog Governance

Row filters and column masks are applied once, as a policy attached to
governed tags at the catalog/schema level, rather than hand-written and
attached to each table individually.

## Why it matters

Per-object row filters and column masks work, but they don't scale: every
new table needs its own filter/mask wired up by hand, and nothing stops a
newly created table from silently going unprotected. ABAC inverts this —
a single policy evaluates tag-based conditions (e.g. "this column is
tagged `pii:ssn`") and applies automatically to every object, present and
future, that matches. Governed tags are the shared vocabulary this rests
on: account-level key/value pairs (like `sensitivity:confidential`) that
attach to catalogs, schemas, tables, and columns and inherit from parent
to child (column tags are the one exception — they don't inherit and must
be set directly).

## What good looks like

- A small, deliberately-governed set of tag keys/values used consistently
  account-wide (who's allowed to *apply* which tags is itself a governed
  permission), rather than free-text tags invented per team.
- ABAC policies attached at the catalog or schema level using
  `has_tag()`/`has_tag_value()` conditions, so a new table dropped into a
  tagged schema inherits the right row filters/column masks with zero
  additional configuration.
- Sensitive-data tagging is kept current automatically via Databricks'
  agentic data classification, which scans new tables (typically within
  24 hours of creation) and applies governed tags for PII/PHI and
  compliance frameworks (GDPR, HIPAA, PCI DSS, GLBA, DPDPA, PIPEDA) —
  see [`automated-pii-classification.md`](automated-pii-classification.md).

## How to detect

Tag presence/absence isn't currently queried by
`data_collection/collect_data.py` — Unity Catalog exposes governed tags
via `information_schema.catalog_tags`/`schema_tags`/`table_tags`/
`column_tags` and the `SHOW TAGS`/`DESCRIBE ... AS JSON` surface, which
would need to be added as a dedicated query pass (tags aren't part of
`system.information_schema.tables`, the table this repo currently reads).
The practical anti-pattern signal, once that's wired up, is columns with
names strongly suggesting sensitive content (`ssn`, `email`, `dob`, etc.)
that carry no classification tag at all.

## References

- [Core concepts for attribute-based access control (ABAC)](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/core-concepts)
- [Common patterns for row filtering and column masking](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/common-patterns)
- [Row filters and column masks](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/)
