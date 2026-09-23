# Continued Use of the Legacy Hive Metastore

> ⚠️ **ANTI-PATTERN**

**Category:** Unity Catalog Governance

New tables and workloads are still being created in the per-workspace
Hive metastore (`hive_metastore` catalog) instead of Unity Catalog, or
existing Hive metastore tables were never migrated.

## Why it happens

Hive metastore predates Unity Catalog and was the only option for years,
so older workspaces accumulated real production workloads on it before UC
existed. Migration is genuinely a project — Databricks recommends deep
clones for managed Delta tables — so it competes for priority against
whatever's currently on fire, and workspaces where it never became
urgent enough just keep adding new tables to the path of least
resistance: the metastore that's already there.

## Impact

Databricks is explicit: Hive metastore tables "do not benefit from the
full set of security and governance features provided by Unity Catalog,
such as built-in auditing, lineage, and access control." Concretely:

- No built-in lineage — none of the automatic table/column lineage this
  library relies on for [`lineage-and-audit-via-system-tables.md`](lineage-and-audit-via-system-tables.md)
  exists for Hive metastore objects.
- Access control is workspace-local (Hive metastore groups), not
  account-level — the same group-based governance strategy in
  [`group-based-access-control.md`](group-based-access-control.md) doesn't
  extend to it.
- No `DENY` statements, no `ANY FILE`/`ANONYMOUS FUNCTION` protections,
  and the hosted metastore has connection limits that can cause failures
  under load that UC doesn't have.
- Every table left in Hive metastore is a blind spot in any
  workspace-wide governance or assessment effort built on UC system
  tables — including this repo's own `data_collection/collect_data.py`,
  which reads `system.information_schema.tables` and therefore doesn't
  see Hive metastore objects at all.

## How to fix

1. Inventory what's still in `hive_metastore` and identify genuinely
   active tables vs. abandoned ones.
2. Migrate managed Delta tables via `CREATE TABLE ... CLONE` (deep
   clones are required from Hive metastore to UC); for a large or urgent
   estate, Hive metastore federation can create a mirrored foreign
   catalog in UC as an interim step during gradual migration.
3. After migration, explicitly disable direct Hive metastore access
   rather than leaving it reachable "just in case."

## How to detect

Not visible from `system.information_schema.tables` at all — that's the
point above. The signal is the presence and size of `hive_metastore` in
`SHOW CATALOGS`, and whether any pipelines/jobs still write there. Worth
treating an active `hive_metastore` catalog as a standing finding in its
own right whenever one shows up in an assessment.

## References

- [Work with the legacy Hive metastore alongside Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/hive-metastore)
- [Upgrade Hive tables and views to Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/migrate)
