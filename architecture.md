```json
[
  {
    "name": "Workspace Health Assessment",
    "story": "Unity Catalog system tables ingested via Lakeflow Connect → declarative medallion pipeline → governed lakehouse → AI/BI Dashboard (68/100 health score) + Genie Agent for NL workspace analysis → Genie One for engineering managers.",
    "columns": [
      "sources",
      "pipeline",
      "lakehouse",
      "consumption",
      "entry"
    ],
    "nodes": [
      {
        "id": "dashboard",
        "type": "ai-bi-dashboard",
        "col": "consumption",
        "row": 1,
        "desc": "68/100 health score · ETL Hygiene · Ownership · Backlog"
      },
      {
        "id": "data",
        "type": "lakeflow-genie-block",
        "col": "pipeline",
        "params": {
          "bronze_desc": "Raw system table snapshots",
          "silver_desc": "Cleaned · joined · normalized",
          "gold_desc": "health_scores · bronze_edits · pipeline_health · remediation_backlog"
        },
        "ai_reasoning": "lakeflow-genie-block is preferred — covers ingest + SDP + Genie Code in one block; gold_desc names the 4 gold tables the dashboard and Genie Agent consume"
      },
      {
        "id": "db-platform",
        "type": "db-platform",
        "pin": {
          "at": "top-left",
          "to": "platform-box"
        }
      },
      {
        "id": "genie",
        "type": "genie",
        "col": "consumption",
        "row": 2,
        "desc": "Ask: bronze edits · stale ML models · orphaned pipelines"
      },
      {
        "id": "genie-one",
        "type": "genie-one",
        "col": "entry",
        "rot": 90,
        "ai_reasoning": "rotated 90° into a slim final lane; persona pill is built in — no separate user node needed; edges auto-arrow to dashboard and genie"
      },
      {
        "id": "governance",
        "type": "governance-block",
        "pin": {
          "at": "top-right",
          "to": "platform-box"
        },
        "ai_reasoning": "governance-block spans everything — Unity Catalog is the common semantic layer: lineage, audit logs, table properties, ownership tags, ML registry. No per-tile edges — pinned position implies it governs all tiles beneath it."
      },
      {
        "id": "lakehouse",
        "type": "sql-lakehouse",
        "col": "lakehouse"
      },
      {
        "id": "note-ingest",
        "type": "note",
        "text": "In production: UC system tables arrive via Lakeflow Connect — system.access.audit, system.lakeflow.job_run_timeline, system.lineage.table_lineage. No custom pipelines.",
        "below": "data",
        "gap": 20
      },
      {
        "id": "note-managers",
        "type": "note",
        "text": "Engineering managers access the report and export findings to Jira via Genie One — no Databricks engineering seat required.",
        "below": "genie-one",
        "gap": 20
      },
      {
        "id": "note-risk",
        "type": "note",
        "text": "$250K/year at risk — 14 bronze tables with direct writes, 31 orphaned pipelines, 2 ML models on stale features.",
        "below": "lakehouse",
        "gap": 20
      },
      {
        "id": "platform-box",
        "type": "box",
        "wraps": [
          "src-audit",
          "src-jobs",
          "src-lineage",
          "src-ml",
          "data",
          "lakehouse",
          "dashboard",
          "genie",
          "genie-one"
        ]
      },
      {
        "id": "src-audit",
        "type": "source",
        "col": "sources",
        "row": 1,
        "label": "system.access.audit",
        "icon": "file:vendor/databricks",
        "desc": "DML events on bronze tables",
        "ai_reasoning": "UC system table — the audit log that surfaces direct edits to bronze layer; icon is the Databricks mark because these are Databricks-native system tables"
      },
      {
        "id": "src-jobs",
        "type": "source",
        "col": "sources",
        "row": 2,
        "label": "job_run_timeline",
        "icon": "file:vendor/databricks",
        "desc": "Pipeline run history · failure analysis"
      },
      {
        "id": "src-lineage",
        "type": "source",
        "col": "sources",
        "row": 3,
        "label": "table_lineage",
        "icon": "file:vendor/databricks",
        "desc": "Gold table dependency graph"
      },
      {
        "id": "src-ml",
        "type": "source",
        "col": "sources",
        "row": 4,
        "label": "mlflow.runs",
        "icon": "file:vendor/databricks",
        "desc": "ML experiment + model registry metadata"
      }
    ],
    "edges": [
      {
        "id": "e1",
        "from": "src-audit",
        "to": "data@in-lakeflow-connect",
        "flow": true
      },
      {
        "id": "e2",
        "from": "src-jobs",
        "to": "data@in-lakeflow-connect",
        "flow": true
      },
      {
        "id": "e3",
        "from": "src-lineage",
        "to": "data@in-lakeflow-connect",
        "flow": true
      },
      {
        "id": "e4",
        "from": "src-ml",
        "to": "data@in-lakeflow-connect",
        "flow": true
      },
      {
        "id": "e5",
        "from": "data",
        "to": "lakehouse",
        "flow": true
      },
      {
        "id": "e6",
        "from": "lakehouse",
        "to": "dashboard",
        "flow": true
      },
      {
        "id": "e7",
        "from": "lakehouse",
        "to": "genie",
        "flow": true
      },
      {
        "id": "e8",
        "from": "genie-one",
        "to": "dashboard",
        "ai_reasoning": "Genie One fronts the consumption tiles; auto-arrow (no flow/arrow fields)"
      },
      {
        "id": "e9",
        "from": "genie-one",
        "to": "genie"
      }
    ]
  }
]
```
