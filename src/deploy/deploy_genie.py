# Databricks notebook source
"""
Deploy the Workspace Health Analytics Genie Space.

Idempotent: searches by title, updates if present, creates if not.
Loads the committed genie_space.json, substitutes catalog.schema at deploy time.

REQUIRES: databricks-sdk>=0.114.0 (environment_key: sdk_latest in databricks.yml).

Parameters (via base_parameters):
- catalog: Unity Catalog name
- schema:  Schema name
- warehouse_id: SQL warehouse the Genie space uses

Outputs (via dbutils.jobs.taskValues.set):
- genie_space_id: the resolved space ID
"""

# COMMAND ----------

SPACE_TITLE = "Workspace Health Analytics"
SPACE_DESCRIPTION = (
    "Workspace health analytics for the engineering team. Overall score: 68/100. "
    "Top risk: 14 bronze tables have been directly edited in the past 90 days — "
    "bypassing pipeline expectations and causing cascading failures worth ~$87K/year. "
    "Ask about bronze table violations, pipeline ownership gaps, ML model risks, "
    "or the full remediation backlog."
)

# The catalog.schema baked into the committed genie_space.json.
# Literal-replace at deploy time so the same JSON works on any catalog/schema.
SRC_QUALIFIER = "solution_builder.demo_workspace_health_assessment_report"

# COMMAND ----------

dbutils.widgets.text("catalog",      "", "Catalog")
dbutils.widgets.text("schema",       "", "Schema")
dbutils.widgets.text("warehouse_id", "", "Warehouse ID")

catalog      = dbutils.widgets.get("catalog")
schema       = dbutils.widgets.get("schema")
warehouse_id = dbutils.widgets.get("warehouse_id")

assert catalog and schema and warehouse_id, "catalog + schema + warehouse_id are required"

print(f"Deploying Genie Space: '{SPACE_TITLE}'")
print(f"  catalog.schema: {catalog}.{schema}")
print(f"  warehouse:      {warehouse_id}")

# COMMAND ----------

import json
import os
from databricks.sdk import WorkspaceClient

# Locate genie_space.json relative to the bundle root.
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
bundle_root   = os.path.dirname(os.path.dirname(os.path.dirname(notebook_path)))
config_path   = f"/Workspace{bundle_root}/src/genie/genie_space.json"
print(f"Loading: {config_path}")

with open(config_path) as f:
    serialized = f.read()

DST_QUALIFIER = f"{catalog}.{schema}"
n = serialized.count(SRC_QUALIFIER)
substituted = serialized.replace(SRC_QUALIFIER, DST_QUALIFIER)
print(f"Substituted {n} occurrences of {SRC_QUALIFIER} → {DST_QUALIFIER}")

space_payload = json.loads(substituted)
print(f"data_sources.tables: {len(space_payload['data_sources']['tables'])}")
print(f"sample_questions:    {len(space_payload['config']['sample_questions'])}")
print(f"example_sqls:        {len(space_payload['instructions']['example_question_sqls'])}")

# COMMAND ----------

w = WorkspaceClient()

# Paginate through GenieListSpacesResponse (NOT a generator — must loop on next_page_token).
existing_id = None
page_token = None
while True:
    resp = w.genie.list_spaces(page_size=200, page_token=page_token)
    for sp in (resp.spaces or []):
        if sp.title == SPACE_TITLE:
            existing_id = sp.space_id
            print(f"Found existing space: {existing_id}")
            break
    if existing_id or not getattr(resp, "next_page_token", None):
        break
    page_token = resp.next_page_token

# COMMAND ----------

if existing_id:
    print(f"Updating space {existing_id}…")
    w.genie.update_space(
        space_id=existing_id,
        warehouse_id=warehouse_id,
        serialized_space=substituted,
    )
    space_id = existing_id
else:
    print("Creating new space…")
    created = w.genie.create_space(
        warehouse_id=warehouse_id,
        title=SPACE_TITLE,
        description=SPACE_DESCRIPTION,
        serialized_space=substituted,
    )
    space_id = created.space_id

print(f"Genie space ready: {space_id}")

# COMMAND ----------

dbutils.jobs.taskValues.set(key="genie_space_id", value=space_id)
print(f"task value set: genie_space_id = {space_id}")
