# Direct Writes to Bronze Tables

> ⚠️ **ANTI-PATTERN**

**Category:** Data Ingestion

An engineer (or a script, notebook, or ad-hoc SQL query) writes directly to
a bronze/raw table with `INSERT`, `UPDATE`, `DELETE`, or `MERGE`, instead of
routing the change through the governed ingestion pipeline that owns that
table.

## Why it happens

Usually a well-intentioned shortcut under time pressure: a bad row needs
fixing before a demo, a one-off backfill seems faster to do by hand than to
route through the pipeline, or someone doesn't realize a table is
pipeline-owned because there's no tagging/documentation saying so. It
compounds because the first direct edit doesn't visibly break anything, so
it looks safe to do again.

## Impact

- Any `CONSTRAINT`s or Lakeflow Declarative Pipelines expectations (the
  data-quality mechanism formerly shipped as Delta Live Tables/DLT) defined
  on the ingestion pipeline are bypassed for that write — bad data can get
  in with nothing flagging it.
- The table is no longer a faithful replay of the source; if the pipeline
  is ever re-run from scratch (a common recovery step), the manual edit is
  silently lost.
- Every downstream table that reads from the mutated bronze table now
  carries an undocumented discrepancy. Root-causing a bad number in an
  executive dashboard three layers downstream becomes a manual lineage
  hunt instead of a pipeline re-run.

## How to fix

1. Revoke `MODIFY` on bronze schemas for interactive users; grant it only
   to the pipeline's service principal. On Databricks Runtime 18.1+, prefer
   the fine-grained `INSERT`/`UPDATE`/`DELETE` privileges over `MODIFY` — they're
   least-privilege alternatives that can be granted/revoked independently,
   so a one-off legitimate need (e.g. an audited correction) can be scoped
   without handing out full write access.
2. Route the specific need that motivated the direct edit through a proper
   path — a backfill run of the pipeline, a correction pipeline, or (for
   genuinely one-off legal/compliance deletes) an audited exception process.
3. Add `CONSTRAINT`s / Lakeflow Declarative Pipelines expectations on the
   bronze table if it doesn't have them, so future attempts fail loudly
   instead of silently landing. Expectations support three violation
   policies — `warn` (default), `drop`, and `fail` — and their pass/fail
   metrics are queryable from the pipeline event log.

## How to detect

`system.access.table_lineage` rows where `target_table_full_name` matches
a bronze-layer table and `entity_type` is `NULL`, `NOTEBOOK`, or
`DBSQL_QUERY` — i.e. the write didn't come from a `JOB` or `PIPELINE` run.
This repo's `real_data` branch computes exactly this in
`data_collection/collect_data.py` → `gold_bronze_table_edits` /
`gold_remediation_backlog`'s `direct_write_findings` CTE, ranking tables by
`edit_count_90d` and joining to real downstream-table lineage to show blast
radius.

## References

- [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [Manage privileges in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/)
- [Fine-grained DML privileges](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/fine-grained-dml-privileges)
- [Manage data quality with pipeline expectations](https://docs.databricks.com/aws/en/ldp/expectations)
