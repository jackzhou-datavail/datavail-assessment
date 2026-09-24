# Documented Tables and Columns

**Category:** SQL & Analytics

Every table and column intended for analytical use carries a comment
that explains what it means, maintained as code in the repo and
deployed — not typed into the UI once and forgotten.

## Why it matters

Column comments used to be a courtesy. They are now load-bearing:
"Genie uses Unity Catalog column names and descriptions to generate
responses. Clear column names and descriptions help produce
high-quality responses." An undocumented gold table is not just harder
for analysts to use — it measurably degrades the natural-language
layer built on top of it.

The same metadata drives discovery. A warehouse where `amt_2`,
`flag_c`, and `dt` are unexplained forces every new analyst through the
same rediscovery process, and each one arrives at a slightly different
interpretation. That is how two dashboards end up disagreeing about a
number that is computed identically.

Databricks' developer guidance is to treat this as source code:
maintain table and column comments in `.sql` files and deploy them via
a metadata job. The reason is drift — comments applied by hand in the
UI are lost on the next table rebuild, and nobody notices because
nothing fails.

## What good looks like

- Comments on every gold-layer table and column, written for the
  business reader: what the column means, its unit and grain, and any
  non-obvious exclusion (does revenue include tax? are cancellations
  removed?).
- Comment definitions live in `.sql` files in the repo, deployed by a
  job, so a table rebuild does not silently erase them.
- Names carry meaning before comments have to rescue them — clear
  column names are named first in the Genie guidance for a reason.
- Documentation coverage treated as a release requirement for a new
  gold table, alongside ownership and quality checks.
- Where a semantic layer exists, its agent metadata (display names,
  formats, synonyms) extends the same documentation rather than
  competing with it. See
  [`metric-views-as-semantic-layer.md`](metric-views-as-semantic-layer.md).
- Ownership recorded alongside description, so a question about a
  column has somewhere to go.

## How to detect

`system.information_schema.tables.comment` and
`system.information_schema.columns.comment` give direct coverage
metrics: the percentage of tables and of columns with a non-null,
non-trivial comment, computed per schema so gold layers can be held to
a higher bar than staging. Two refinements worth making — exclude
comments that merely restate the column name, and weight the result by
consumption using read frequency from `system.access.table_lineage` or
`system.query.history`, so a heavily queried undocumented table ranks
above a dormant one.

## References

- [Curate an effective Genie Agent](https://docs.databricks.com/aws/en/genie/best-practices)
- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
- [Unity Catalog best practices](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
