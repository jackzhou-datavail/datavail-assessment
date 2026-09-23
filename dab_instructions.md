# DAB Deploy Instructions — Workspace Health Assessment

## Prerequisites

- Databricks CLI installed and authenticated (`databricks auth login` or a configured profile)
- A Unity Catalog catalog and schema you own or have `CREATE`/`USE SCHEMA` privileges on (the schema will be created if it doesn't exist)
- A SQL Warehouse ID available in your workspace

## 2-Command Deploy

### Step 1 — Deploy resources

```bash
databricks bundle deploy \
  --var catalog=<your-catalog> \
  --var schema=<your-schema> \
  --var warehouse_id=<your-warehouse-id>
```

This creates / updates:
- **AI/BI Dashboard** — "Workspace Health Assessment" (from `src/dashboard/dashboard.json`)

### Step 2 — Run setup job

```bash
databricks bundle run workspace_health_setup \
  --var catalog=<your-catalog> \
  --var schema=<your-schema> \
  --var warehouse_id=<your-warehouse-id>
```

The setup job runs two tasks in sequence:
1. **`generate_data`** — generates synthetic workspace metadata into the UC tables (12 tables: 7 raw + 5 gold)
2. **`deploy_genie`** — creates / updates the "Workspace Health Analytics" Genie space

## Deploy to a Different Catalog / Schema

Override any variable at deploy time:

```bash
databricks bundle deploy \
  --var catalog=my_catalog \
  --var schema=my_schema \
  --var warehouse_id=<my_warehouse_id>

databricks bundle run workspace_health_setup \
  --var catalog=my_catalog \
  --var schema=my_schema \
  --var warehouse_id=<my_warehouse_id>
```

The dashboard queries and Genie space SQL will be rebound to the new catalog.schema automatically.

## Validate Before Deploy

```bash
databricks bundle validate
```

## Tear Down

```bash
databricks bundle destroy
```

This removes the dashboard and setup job. **Does NOT delete the UC tables or Genie space** (those are deployed by the setup job tasks, not declared as bundle resources).

## File Map

| File | Purpose |
|------|---------|
| `databricks.yml` | Bundle definition — variables, dashboard, setup job |
| `src/dashboard/dashboard.json` | Static dashboard JSON (3 pages) |
| `src/genie/genie_space.json` | Genie space serialized config (7 tables, 6 sample Qs, 3 curated SQLs) |
| `src/deploy/deploy_genie.py` | Notebook task — creates/updates Genie space idempotently |
| `data_generation/generate_data.py` | Notebook task — generates all 12 UC tables |

## Already-Deployed Resources (pre-built)

`resources.json` records the resource IDs from the most recent build session (genie space, dashboard, table list) — informational only, not consumed by the bundle. For a fresh deployment the setup job will create new IDs in the target workspace.
