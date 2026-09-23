# Unowned / Never-Reassigned Catalog Objects

> ⚠️ **ANTI-PATTERN**

**Category:** Unity Catalog Governance

A table, schema, or catalog's owner is still the individual who happened
to create it — often months or years ago, possibly someone no longer at
the company — because ownership was never deliberately reassigned to a
group.

## Why it happens

Unity Catalog makes the creator the owner automatically; that's a sensible
default for a table someone's actively iterating on, but nobody circles
back to change it once the table becomes something other people depend on.
There's no forcing function — the table keeps working fine with its
original owner right up until that person leaves, at which point
reassigning ownership requires an admin escalation instead of a routine
group-membership change.

## Impact

- When the owning individual leaves the company or changes teams, the
  object's ownership either dangles (pointing at a deactivated identity)
  or has to be forcibly reassigned by an admin under time pressure —
  exactly the wrong moment to be figuring out who should own it.
- Nobody outside the original creator has a clear, structural claim of
  responsibility for the table's quality, schema changes, or access
  requests — questions default to "whoever finds it first," not an
  accountable owner.
- It's a leading indicator, not just a standalone issue: workspaces where
  this is common tend to also show weaker patterns elsewhere (missing
  comments, no classification tags, inconsistent naming) because nobody
  was ever clearly on the hook to maintain the object.

## How to fix

1. Treat ownership reassignment as a required step when a table graduates
   from "someone's scratch work" to "other people depend on this" — not
   an optional cleanup task.
2. Run a periodic sweep: list tables/schemas/catalogs owned by individual
   users rather than groups, and route each one to its actual using team
   for a real ownership decision (reassign to a group, or confirm it's
   genuinely personal/scratch and can stay as-is or be deleted).
3. For production catalogs and schemas specifically, require group
   ownership as a matter of policy, not convention.

## How to detect

This repo's real-data assessment already computes exactly this signal:
`data_collection/collect_data.py` reads `table_owner` from
`system.information_schema.tables` (and the equivalent `run_as`/
`creator_user_name` fields from `system.lakeflow.pipelines`/`jobs`) and
flags `has_owner_tag = FALSE` where the owner isn't a resolvable real
identity at all. A workspace with a high proportion of `has_owner_tag =
FALSE` pipelines/jobs, or tables owned by individuals rather than groups,
is showing this pattern — see `gold_pipeline_health` and the
`unowned_pipeline_findings`/`unowned_job_findings` CTEs in
`gold_remediation_backlog`.

## References

- [Unity Catalog best practices](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
