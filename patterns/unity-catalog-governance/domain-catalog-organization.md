# Catalogs as the Primary Unit of Isolation

**Category:** Unity Catalog Governance

Catalogs are organized around environment, team, or business domain (e.g.
`prod_finance`, `dev_marketing`) rather than being an afterthought, with
projects and medallion layers organized at the schema level *within* each
catalog.

## Why it matters

Databricks' own Unity Catalog best-practices guidance calls "using catalogs
as your primary unit of isolation" the single most important architectural
decision to get right, because privileges, workspace bindings, and
isolation boundaries are all inherited down the three-level namespace
(`catalog.schema.table`) from the catalog down. A catalog structure that
tracks how the organization actually thinks about environments and domains
makes access control legible; one that doesn't means every new grant is a
judgment call made from scratch.

## What good looks like

- One catalog per environment/team/business-unit combination (e.g.
  `prod_finance`, `staging_hr_sensitive`), or a hybrid of the two as the
  organization scales — Databricks' guidance is explicitly to "start with
  environment-based catalogs... and evolve toward domain-driven patterns."
- Medallion layers (bronze/silver/gold) organized as schemas *within* a
  domain catalog, or as schemas within a shared lakehouse catalog — either
  way, a consistent, documented convention rather than one invented per
  project.
- Workspace-to-catalog bindings restrict which workspaces can even see a
  given catalog, so environment separation (dev/staging/prod) is enforced
  structurally, not just by naming convention.

## How to detect

`system.information_schema.tables` (queried by
`data_collection/collect_data.py`) gives the actual catalog/schema/table
inventory of a workspace — a proliferation of ad-hoc, inconsistently-named
catalogs with no discernible env/domain pattern, or medallion-layer
sprawl across catalogs rather than within them, is the practical signal
that no organizing convention was ever agreed on.

## References

- [Unity Catalog best practices](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
