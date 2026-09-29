# Fine-Grained Access with Row Filters and Column Masks

**Category:** Unity Catalog Governance

Sensitive rows and columns are protected in the table itself with Unity
Catalog row filters and column masks, so every consumer — SQL, notebooks,
BI tools, Genie — sees the same restricted result, rather than relying
on a zoo of per-audience copies or views.

## Why it matters

Without fine-grained controls, the usual workaround is to materialize a
filtered copy of a table per audience (`sales_emea`, `sales_us`,
`customers_masked`). Each copy is another pipeline, another place the
logic can diverge, and another object whose grants must be kept right.
Row filters and column masks move that logic onto the table: "the filter
is a SQL user-defined function (UDF) that evaluates each row at query
time," and a mask is a UDF that returns the original or a masked value.

There are two ways to apply them, and the choice is the real assessment
question. Databricks "recommends ABAC policies when you need consistent
row filtering and column masking across many tables" — see
[`abac-governed-tags.md`](abac-governed-tags.md). Manually attaching a
function per table with `ALTER TABLE ... SET ROW FILTER` / `ALTER COLUMN
... SET MASK` is fine for a handful of special cases but does not scale
and leaves new tables unprotected by default.

## What good looks like

- Row filters and masks are used for genuinely shared tables with
  mixed-sensitivity audiences, instead of audience-specific copies.
- ABAC policies drive the common cases (tag-matched PII columns,
  region-based row filtering); per-table functions are the documented
  exception.
- Filter/mask functions live in a governed schema, are owned by a
  group, and are simple: "Use simple UDFs. Functions with fewer
  expressions perform better," and "prefer SQL to Python UDFs."
- Group membership (`is_account_group_member()`) drives the logic — not
  hard-coded user emails inside the function.
- Known limits are designed around: filters and masks can't be applied
  to a view, time travel isn't supported on tables with them, and
  clients need a recent runtime (12.2 LTS+ in general; 15.4 LTS+ on
  dedicated access mode).

## How to detect

`system.information_schema.column_masks` (`catalog_name`, `schema_name`,
`table_name`, `column_name`, `mask_catalog`, `mask_schema`, `mask_name`)
and `system.information_schema.row_filters` list per-table assignments;
ABAC policies are listed per securable through the policies API /
`SHOW POLICIES`. Useful findings:

- Tables with sensitive-classified columns (column tags from data
  classification) that have neither a mask nor a covering ABAC policy.
- Many near-duplicate tables or views whose names encode an audience or
  region — a sign copies are standing in for row filters.
- Filter/mask functions containing literal email addresses
  (`system.information_schema.routines.routine_definition`).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Governance and Unity Catalog › Access controls (row filters, column masks)** — *primary.* Are sensitive rows and columns protected with row filters / column masks (preferably via ABAC) instead of audience-specific copies?
- **Governance and Unity Catalog › ABAC policies used** — *supporting;* primary pattern is [`abac-governed-tags.md`](abac-governed-tags.md).
- **Compliance/regulatory alignment › PII handling** — *supporting;* primary pattern is [`automated-pii-classification.md`](automated-pii-classification.md).

## References

- [Row filters and column masks](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/)
- [Manually apply row filters and column masks](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/manually-apply)
- [COLUMN_MASKS information schema](https://docs.databricks.com/aws/en/sql/language-manual/information-schema/column_masks)
