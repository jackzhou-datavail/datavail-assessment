# Lineage & Audit Logging via System Tables

**Category:** Unity Catalog Governance

Data lineage and access-audit history are treated as queryable, always-on
governance data — read directly from Unity Catalog's system tables —
rather than something reconstructed by hand when an incident forces the
question.

## Why it matters

When Unity Catalog is enabled, it automatically tracks lineage — "which
queries and files populate a table, which jobs and notebooks transform it,
and which dashboards consume the results" — at both table and column
level, with zero extra configuration required from the team. Paired with
`system.access.audit` (who did what, when, from where), this turns "what
changed and why does this number look wrong" from a Slack archaeology
exercise into a query. This repo's own real-data assessment tooling is
built entirely on this: `data_collection/collect_data.py` derives its
flagship "direct/ad-hoc write" finding from `system.access.table_lineage`
alone.

## What good looks like

- Lineage is treated as a first-class artifact when debugging a bad
  number or scoping the blast radius of a schema change — not just a
  "nice to have" panel in the UI nobody opens.
- Anyone with legitimate need can query `system.access.table_lineage`
  and `system.access.column_lineage` directly, rather than lineage
  knowledge living only in the heads of whoever built the pipeline.
- Audit log retention and export policy is a deliberate decision, not a
  default left unexamined — system-table audit logs expire after 90 days
  by default, so anything needed for longer-term compliance is exported
  or archived elsewhere.

## Known limitations (don't assume lineage is complete)

- Column-level lineage isn't captured through path references
  (`delta."s3://bucket/path"`) or through UDFs that obscure the
  input→output column mapping — those show up as table-level lineage
  only.
- History before 2024-09-01 isn't available, and lineage isn't preserved
  across object renames.
- RDDs, global temp views, and `system.information_schema` itself aren't
  tracked.

## How to detect

This *is* the detection mechanism for several other patterns in this
library, not something to detect itself — see
[`direct-writes-to-bronze-tables.md`](../data-ingestion/direct-writes-to-bronze-tables.md)
for the concrete query. The one thing worth checking about lineage
*itself*: workspaces where `system.access.table_lineage` returns
suspiciously little for known-active tables are workspaces relying on one
of the limitations above (path-based reads, UDF-obscured transforms) more
heavily than they realize.

## References

- [Lineage in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage)
- [Audit log system table reference](https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/audit-logs)
