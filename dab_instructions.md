# DAB Deploy Instructions — Workspace Health Assessment

## Prerequisites

- Databricks CLI installed and authenticated (`databricks auth login` or a configured profile)
- Catalog `solution_builder` and schema `demo_workspace_health_assessment_report` accessible
- SQL Warehouse `5c7c72ebf856f7c4` available (or substitute your own)

## 2-Command Deploy

### Step 1 — Deploy resources

```bash
databricks bundle deploy \
  --var catalog=solution_builder \
  --var schema=demo_workspace_health_assessment_report \
  --var warehouse_id=5c7c72ebf856f7c4
```

This creates / updates:
- **AI/BI Dashboard** — "Workspace Health Assessment" (from `src/dashboard/dashboard.json`)

### Step 2 — Run setup job

```bash
databricks bundle run workspace_health_setup \
  --var catalog=solution_builder \
  --var schema=demo_workspace_health_assessment_report \
  --var warehouse_id=5c7c72ebf856f7c4
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

These IDs are in `resources.json` and were created during the initial build session:

| Resource | ID |
|----------|----|
| Genie Space | `01f1b6a557d9128f9b7e715d762bb8aa` |
| Dashboard | `01f1b6a50efd1433bee40e0168ce0f0f` |

For a fresh deployment the setup job will create new IDs in the target workspace.
