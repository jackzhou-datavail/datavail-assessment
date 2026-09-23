# Direct Grants to Individual Users

> ⚠️ **ANTI-PATTERN**

**Category:** Unity Catalog Governance

Privileges are granted directly to named individuals' accounts —
`alice@company.com`, `bob@company.com` — instead of to identity-provider
groups, and objects stay owned by whoever happened to create them.

## Why it happens

It's the fastest path to unblocking someone right now: a teammate needs
access to a table today, and granting it to them by name takes thirty
seconds, while setting up (or finding) the right group takes longer. Done
once, it's harmless. Done as the default pattern across a growing team, it
compounds silently — nobody notices the permission graph getting
unmanageable until an offboarding or an audit forces someone to actually
look at it.

## Impact

- Every personnel change — a new hire, a team move, an offboarding —
  becomes a manual grant-by-grant review instead of a group-membership
  change. Databricks' own guidance is blunt about the outcome: individual
  grants "create an unmanageable permission graph after the first few
  months."
- Objects created by an individual and never reassigned stay owned by
  that person's account. If they leave, ownership either dangles or has
  to be recovered through an admin escalation instead of a routine
  process.
- There's no single place to answer "who can see this table" — the
  answer is scattered across however many individual grants accumulated
  over time, rather than a short list of group names.

## How to fix

1. Stand up groups in the identity provider (Entra ID, Okta, etc.) that
   mirror how access decisions are actually made — by team, by role, by
   data domain — and sync them into Databricks.
2. Reassign ownership of shared/production catalogs, schemas, and tables
   from individual creators to the appropriate group.
3. Replace existing individual grants with equivalent group grants, then
   revoke the individual ones — don't just add groups on top and leave
   the old direct grants in place.
4. Treat "grant this to a named user" as an exception that requires a
   reason, not the default path.

## How to detect

`system.information_schema.tables.table_owner` gives current ownership —
a workspace where most tables are owned by individual user emails rather
than groups or service principals is showing this pattern structurally.
Confirming it for *grants* (as opposed to ownership) needs `SHOW GRANTS`
scans across objects, since system tables don't currently expose the
grant graph the way they expose ownership — `data_collection/collect_data.py`
covers the ownership signal today but not a full grants audit.

## References

- [Unity Catalog best practices](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
