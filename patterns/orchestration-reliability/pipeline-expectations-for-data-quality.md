# Pipeline Expectations for Data Quality

**Category:** Orchestration & Reliability

Lakeflow pipelines declare expectations on the data they produce, with
a violation policy chosen deliberately per rule — and invalid records
routed to a quarantine table rather than dropped where nobody will see
them.

## Why it matters

Expectations turn "we assume customer_id is never null" from a comment
into an enforced, measured property of the pipeline. Three violation
policies are available, and the choice between them is the actual
design decision:

- **Warn** — "records that are not valid are written to the target
  table and flagged in metrics." Nothing is lost; the metric is the
  signal.
- **Drop** — invalid rows are discarded before writing. The target
  stays clean and the rows are gone.
- **Fail** — "the pipeline update stops on the first invalid record."
  Nothing bad reaches the table, and nothing good does either.

The trap is `drop` used as a default. It produces a clean-looking
table and a silent, unbounded data loss: the row count is lower than
the source and no one can say which rows went missing or why.
Databricks' guidance is explicit about the alternative — "use a
quarantine pattern to route failed records separately rather than
silently discarding them."

Expectations at every layer is the other half. A rule on the gold table
alone tells you something broke somewhere upstream; rules at each hop
tell you where.

## What good looks like

- Expectations declared on the properties the business actually depends
  on — keys present, amounts non-negative, enums within their set, dates
  within plausible range — not on everything mechanically.
- Violation policy chosen per rule with a stated reason: `fail` for
  invariants that make downstream output meaningless, `drop` only with
  a quarantine route, `warn` for things worth watching but not worth
  stopping for.
- A **quarantine table** for rejected records, with enough context
  (source, rule violated, timestamp) to diagnose them, and someone who
  looks at it.
- Expectation metrics monitored over time, since a rule that starts
  failing is usually an upstream change rather than a one-off.
- Declarative CDC (`AUTO CDC ... INTO`) preferred over hand-written
  `MERGE`, since it handles "ordering, deduplication, out-of-order
  events, and schema evolution declaratively" — the places where
  hand-rolled merges quietly corrupt data.
- Expectations kept in the pipeline source in version control, so a
  loosened rule is visible in a diff.

## How to detect

Expectation definitions and their pass/fail metrics live in the
pipeline event log rather than in a `system.*` table, so coverage and
violation rates are read from the event log or the Pipelines API. What
system tables offer is the surrounding shape:
`system.lakeflow.pipelines` and `pipeline_update_timeline` identify
which pipelines exist and whether they are updating, and
`system.information_schema.table_constraints` shows whether declared
constraints (`NOT NULL`, `CHECK`, primary keys) exist on the tables
those pipelines write — a reasonable proxy for whether quality is
declared anywhere at all.

## References

- [Best practices for Lakeflow pipelines](https://docs.databricks.com/aws/en/ldp/best-practices)
- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [Change data capture (CDC) for database ingestion](../data-ingestion/change-data-capture-ingestion.md)
