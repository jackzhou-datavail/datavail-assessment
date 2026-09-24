# Analytics on Raw Tables

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

Dashboards, Genie spaces, and BI extracts read bronze or raw landing
tables directly, so every consumer re-implements the cleaning, joining,
and business logic that a gold layer was supposed to do once.

## Why it happens

The raw table is there and it has the data. Building a gold table
requires deciding on a grain, a definition, and an owner — three
conversations — while `SELECT` against bronze requires none. For an
urgent question that is the right trade, and the dashboard built to
answer it urgently becomes permanent.

It is also what happens when the gold layer exists but is incomplete.
An analyst needs one column that gold does not carry, so they join back
to bronze "just for that field," and the dashboard now straddles both
layers with no indication of which parts are governed.

## Impact

- Business logic fragments across consumers, which is the direct route
  to
  [`duplicated-metric-definitions.md`](duplicated-metric-definitions.md)
  — each dashboard cleans and filters slightly differently.
- Raw data is raw on purpose. Bronze "contains raw, unvalidated data"
  and preserves "the raw state of the data source in its original
  formats" — including corrupt records and pre-correction values that
  a consumer will silently include.
- Schema changes upstream break consumers directly, with no silver
  layer absorbing them. This is why Databricks warns against writing to
  silver straight from ingestion for the same reason.
- Query cost rises: bronze grows without bound and carries every
  historical row, so a dashboard scans far more than its question
  requires.
- Genie accuracy suffers badly here — raw tables tend to have cryptic
  column names and no comments, and Genie "uses Unity Catalog column
  names and descriptions to generate responses."
- Governance blurs, because giving analysts dashboard access means
  giving them bronze access, which is usually broader than intended.

## How to fix

1. Identify the consumers reading raw tables and what each actually
   needs; the overlap is the specification for the gold table that
   should exist.
2. Build that gold table with a business-meaningful grain, documented
   columns, and an owner, and repoint the consumers at it. See
   [`medallion-layering-for-analytics.md`](medallion-layering-for-analytics.md).
3. Where consumers need flexible slicing of the same measures, put a
   metric view over gold rather than a view per question.
4. Close the access path: restrict bronze and silver to the teams that
   build pipelines, so the shortcut stops being available.
5. Add data quality checks at each layer so gold is trustworthy enough
   that nobody feels a need to go around it.
6. For the one-missing-column case, extend gold rather than joining
   back — the join is a signal that gold's grain or scope is wrong.

## How to detect

`system.access.table_lineage` traces each dashboard, Genie space, and
downstream query to its source tables; consumers whose upstream is a
bronze or raw table are the finding, ranked by how many people use
them. `system.query.history` ranks raw tables by interactive and
dashboard query frequency, which shows where the pressure actually is.
Cross-check `system.information_schema.columns.comment` on those
tables — heavy analytical reads against undocumented raw tables is the
combination that most degrades both accuracy and trust.

## References

- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [Curate an effective Genie Agent](https://docs.databricks.com/aws/en/genie/best-practices)
- [Bronze layer immutability](../data-ingestion/bronze-layer-immutability.md)
