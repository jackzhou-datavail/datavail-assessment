# Group-Based Access Control & Ownership

**Category:** Unity Catalog Governance

Privileges and object ownership are assigned to identity-provider-managed
groups (or service principals for automated workloads), not to individual
users — including for objects an individual originally created.

## Why it matters

Databricks' guidance is direct: *"Avoid direct grants to users whenever
possible"* and *"Always assign ownership of production catalogs and
schemas to groups, not individual users."* The creator of an object is its
first owner by default — the practice this pattern requires is that
creators **reassign** ownership to the appropriate group once an object is
meant for shared/production use. Individual-grant permission graphs are
manageable for the first few objects and unmanageable a few months later:
every offboarding becomes a hunt for orphaned grants, and every new
teammate needs a fresh round of manual grants instead of a group
membership change.

## What good looks like

- Groups are defined and managed in the identity provider (Entra ID,
  Okta, etc.) and synced into Databricks — not created ad hoc inside
  Databricks itself.
- Production catalogs/schemas/tables are owned by a group; when the group
  owns a view or metric view, members can edit its definition while their
  actual data access still follows what the group is separately granted.
- Automated workloads (jobs, pipelines) run as — and where relevant, are
  owned by — a service principal, not a named individual's identity, so
  the pipeline keeps working after that person changes teams.
- The Principle of Least Privilege applies at every level of the
  hierarchy: `USE CATALOG`/`USE SCHEMA` only for principals that need that
  specific data, `MODIFY` on production tables reserved for the owning
  service principal, `CREATE EXTERNAL LOCATION` limited to admins.

## How to detect

`system.information_schema.tables.table_owner` and the equivalent for
pipelines/jobs (`run_as`/`created_by` in `system.lakeflow.pipelines`/`jobs`)
show whether an object's owner is a real individual user email or a
group/service-principal identity. `data_collection/collect_data.py`
already treats "owner looks like a real user email" as a *positive* signal
(`has_owner_tag`) for the simpler question of "is anyone accountable at
all" — distinguishing individual-user ownership from group/service-principal
ownership specifically would need `SHOW GRANTS`/`DESCRIBE ... AS JSON`
tooling beyond what system tables expose directly, since system tables
don't label a given email as belonging to a "group" vs. a person.

## References

- [Unity Catalog best practices](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
- [Manage privileges in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/)
