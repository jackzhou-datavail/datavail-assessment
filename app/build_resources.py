"""
Build Genie Space and Dashboard via M2M credentials.
Uses SDK's api_client.do() which handles OAuth token management properly.
Saves resource IDs to /tmp/resource_ids.json for pickup by the parent process.
"""
import os, sys, json, time
from databricks.sdk import WorkspaceClient

CATALOG = os.environ.get("DEMO_CATALOG", "main")
SCHEMA  = os.environ.get("DEMO_SCHEMA", "assessment_data")
WAREHOUSE_ID = os.environ.get("DEMO_WAREHOUSE_ID", "")
FQ = f"{CATALOG}.{SCHEMA}"

def get_client():
    w = WorkspaceClient()
    host = w.config.host.rstrip("/")
    print(f"Auth type: {w.config.auth_type}, Host: {host}", flush=True)
    return host, w

def api_post(w, path, payload):
    """POST via SDK's api_client which handles M2M token refresh."""
    return w.api_client.do("POST", path, body=payload)

# ── GENIE SPACE ───────────────────────────────────────────────────────────────

GENIE_SERIALIZED = {
    "version": 2,
    "config": {
        "sample_questions": [
            {
                "id": "10000000000000000000000000000001",
                "question": ["What is the current Datavail Assessment score and which dimension is worst?"]
            },
            {
                "id": "10000000000000000000000000000002",
                "question": ["Which bronze tables have been directly modified, and what is the estimated annual cost of cascading failures?"]
            },
            {
                "id": "10000000000000000000000000000003",
                "question": ["Which ML models are serving features from tables that had direct writes in the last 30 days?"]
            },
            {
                "id": "10000000000000000000000000000004",
                "question": ["Which production pipelines have no owner tag?"]
            },
            {
                "id": "10000000000000000000000000000005",
                "question": ["How has ownership coverage improved over the past 30 days?"]
            },
            {
                "id": "10000000000000000000000000000006",
                "question": ["Show me the top 10 critical and high findings ranked by business impact."]
            }
        ]
    },
    "data_sources": {
        "tables": [
            {
                "identifier": f"{FQ}.gold_bronze_table_edits",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "downstream_gold_tables", "description": ["Comma-separated list of gold tables that depend on this bronze table via lineage."], "synonyms": ["downstream tables", "affected tables"]},
                    {"column_name": "edit_count_90d", "description": ["Number of direct DML events (INSERT/UPDATE/DELETE/MERGE/TRUNCATE) in the past 90 days."], "synonyms": ["edits", "direct writes", "DML events"]},
                    {"column_name": "estimated_rerun_cost_usd", "description": ["Annual estimated cost in USD from pipeline reruns caused by direct DML writes on this bronze table."], "synonyms": ["rerun cost", "annual cost", "cascading failure cost"]},
                    {"column_name": "severity", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "table_name", "enable_entity_matching": True, "enable_format_assistance": True}
                ]
            },
            {
                "identifier": f"{FQ}.gold_health_scores",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "dimension", "enable_entity_matching": True, "enable_format_assistance": True, "description": ["Health dimension: overall, etl_hygiene, ml_ai_governance, ownership_access, data_quality."]},
                    {"column_name": "score", "description": ["Health score 0-100. Below 60 = critical, 60-74 = needs attention, 75+ = healthy."], "synonyms": ["health score", "workspace score"]},
                    {"column_name": "score_delta_30d", "description": ["Change in score vs 30 days ago. Negative means the dimension is deteriorating."], "synonyms": ["score change", "trend", "delta"]}
                ]
            },
            {
                "identifier": f"{FQ}.gold_ownership_trend",
                "column_configs": [
                    {"column_name": "ownership_coverage_pct", "description": ["Percentage of production pipelines with owner tags. Trend goes from 58% (30 days ago) to 69% (today). Goal is 95%."], "synonyms": ["ownership", "coverage", "ownership rate"]}
                ]
            },
            {
                "identifier": f"{FQ}.gold_pipeline_health",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "failure_rate_30d", "description": ["Fraction of runs that failed in the last 30 days (0.0 to 1.0). customer_churn_etl, revenue_pipeline_v1, and ml_feature_refresh all exceed 0.40."], "synonyms": ["failure rate", "error rate"]},
                    {"column_name": "has_owner_tag", "description": ["True if the pipeline has an owner tag assigned. 31 pipelines have has_owner_tag = FALSE — these are the orphaned pipelines."], "synonyms": ["has owner", "owned", "orphaned"]},
                    {"column_name": "health_status", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "pipeline_name", "enable_entity_matching": True, "enable_format_assistance": True}
                ]
            },
            {
                "identifier": f"{FQ}.gold_remediation_backlog",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "asset_name", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "business_impact_usd", "description": ["Annual business impact in USD if this finding is not remediated."], "synonyms": ["impact", "cost", "risk"]},
                    {"column_name": "category", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "severity", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "sprint_estimate_days", "description": ["Engineering effort estimate in days to resolve this finding."], "synonyms": ["effort", "fix time"]}
                ]
            },
            {
                "identifier": f"{FQ}.raw_ws_audit_events",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "action_type", "enable_entity_matching": True, "enable_format_assistance": True, "description": ["DML operation type: INSERT, UPDATE, DELETE, MERGE, TRUNCATE."]},
                    {"column_name": "query_snippet", "exclude": True},
                    {"column_name": "table_name", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "user_email", "description": ["Engineer who ran the DML query directly on the bronze table."], "synonyms": ["user", "editor", "who"]}
                ]
            },
            {
                "identifier": f"{FQ}.raw_ws_ml_models",
                "column_configs": [
                    # sorted by column_name
                    {"column_name": "is_serving_stale_features", "description": ["TRUE if the model's serving endpoint is reading from a bronze table that received direct DML writes in the last 30 days. Exactly 2 models have this flag set."], "synonyms": ["stale features", "stale model", "data staleness"]},
                    {"column_name": "model_name", "enable_entity_matching": True, "enable_format_assistance": True},
                    {"column_name": "registered_in_uc", "description": ["True if model is registered in Unity Catalog model registry. FALSE means lineage is broken."]},
                    {"column_name": "upstream_features_table", "description": ["The table the model's training pipeline reads from for feature data."], "synonyms": ["feature table", "input table"]}
                ]
            }
        ]
    },
    "instructions": {
        "text_instructions": [
            {
                "id": "30000000000000000000000000000001",
                "content": [
                    "## PURPOSE",
                    "- Answer Datavail Assessment questions for Alex Chen (Head of Data Engineering) and their engineering team.",
                    "- This workspace has a 68/100 health score (was 71 thirty days ago). ETL Hygiene (55) is the worst dimension.",

                    "## DISAMBIGUATION",
                    "- 'Health score' means the score column in gold_health_scores WHERE report_date = CURRENT_DATE.",
                    "- 'Bronze table edits' refers to gold_bronze_table_edits — use edit_count_90d for frequency and estimated_rerun_cost_usd for cost.",
                    "- 'Stale features' means raw_ws_ml_models WHERE is_serving_stale_features = TRUE (exactly 2 models).",
                    "- 'Unowned pipelines' means gold_pipeline_health WHERE has_owner_tag = FALSE (31 total, 9 production).",
                    "- When the user asks about 'the worst table' or 'most edited table', that is raw_transactions with 47 edits.",

                    "## DATA QUALITY NOTES",
                    "- gold_health_scores has one row per (report_date, dimension). Use WHERE report_date = CURRENT_DATE for today's score.",
                    "- gold_bronze_table_edits has exactly 14 rows — one per bronze table with direct DML in 90 days.",
                    "- SUM(estimated_rerun_cost_usd) in gold_bronze_table_edits equals exactly $87,000.",
                    "- gold_ownership_trend covers 30 days; ownership_coverage_pct goes from ~58% to ~69%.",

                    "## Instructions you must follow when providing summaries",
                    "- Always state the total at-risk amount ($250K/year) when summarizing the Datavail Assessment.",
                    "- When quoting bronze table edit costs, confirm the total is $87K/year.",
                    "- Round percentages to one decimal place."
                ]
            }
        ],
        "example_question_sqls": [
            {
                "id": "20000000000000000000000000000001",
                "question": ["Which bronze tables have the most direct edits and what is the total rerun cost?"],
                "sql": [
                    f"SELECT gold_bronze_table_edits.table_name, gold_bronze_table_edits.edit_count_90d, gold_bronze_table_edits.severity, gold_bronze_table_edits.downstream_gold_tables, gold_bronze_table_edits.estimated_rerun_cost_usd FROM `{FQ}`.`gold_bronze_table_edits` ORDER BY gold_bronze_table_edits.edit_count_90d DESC"
                ],
                "usage_guidance": ["Use this for the primary bronze-edit cost analysis. The SUM of estimated_rerun_cost_usd = $87K/year."]
            },
            {
                "id": "20000000000000000000000000000002",
                "question": ["Which ML models are serving stale features and which bronze table caused the staleness?"],
                "sql": [
                    f"WITH stale_models AS (SELECT raw_ws_ml_models.model_name, raw_ws_ml_models.serving_endpoint_name, raw_ws_ml_models.upstream_features_table, raw_ws_ml_models.features_last_modified_date FROM `{FQ}`.`raw_ws_ml_models` WHERE raw_ws_ml_models.is_serving_stale_features = TRUE) SELECT stale_models.model_name, stale_models.serving_endpoint_name, stale_models.upstream_features_table, stale_models.features_last_modified_date, gold_bronze_table_edits.edit_count_90d, gold_bronze_table_edits.estimated_rerun_cost_usd FROM stale_models LEFT JOIN `{FQ}`.`gold_bronze_table_edits` ON stale_models.upstream_features_table = gold_bronze_table_edits.table_name"
                ],
                "usage_guidance": ["Cross-table join: connects ML model staleness to the bronze table edits that caused it. Returns exactly 2 models."]
            },
            {
                "id": "20000000000000000000000000000003",
                "question": ["Show the full remediation backlog ranked by severity and business impact"],
                "sql": [
                    f"SELECT gold_remediation_backlog.finding_id, gold_remediation_backlog.severity, gold_remediation_backlog.category, gold_remediation_backlog.asset_type, gold_remediation_backlog.asset_name, gold_remediation_backlog.owner_email, gold_remediation_backlog.description, gold_remediation_backlog.business_impact_usd, gold_remediation_backlog.recommended_action, gold_remediation_backlog.sprint_estimate_days FROM `{FQ}`.`gold_remediation_backlog` ORDER BY CASE gold_remediation_backlog.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, gold_remediation_backlog.business_impact_usd DESC"
                ],
                "usage_guidance": ["Sprint-planning backlog. 6 critical, 11 high, 23 medium findings. Total impact ~$250K/year."]
            }
        ]
    }
}


def build_genie_space(host, w):
    """Create the Datavail Assessment Analytics Genie space."""
    print("\n=== Building Genie Space ===", flush=True)

    # Try to ensure workspace path exists (failure is non-fatal)
    workspace_path = "/Workspace/Solution Builder/genie_spaces"
    try:
        w.workspace.mkdirs(path=workspace_path)
        print(f"  Workspace path ensured: {workspace_path}", flush=True)
    except Exception as e:
        # M2M SP may not have permission to create workspace folders; use a fallback
        workspace_path = "/Workspace/Shared"
        print(f"  mkdirs failed, using: {workspace_path}", flush=True)

    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "title": "Datavail Assessment Analytics",
        "description": "Datavail assessment analytics for the engineering team. Overall score: 68/100. Top risk: 14 bronze tables have been directly edited in the past 90 days — bypassing pipeline expectations and causing cascading failures worth ~$87K/year. Ask about bronze table violations, pipeline ownership gaps, ML model risks, or the full remediation backlog.",
        "parent_path": workspace_path,
        "serialized_space": json.dumps(GENIE_SERIALIZED)
    }

    print(f"  POST /api/2.0/genie/spaces", flush=True)
    space_id = None
    try:
        resp = api_post(w, "/api/2.0/genie/spaces", payload)
        print(f"  Response: {str(resp)[:200]}", flush=True)
        if isinstance(resp, dict):
            space_id = resp.get("space_id") or resp.get("id")
    except Exception as e:
        err_str = str(e)
        if "already exists" in err_str.lower():
            print(f"  Genie space already exists, searching...", flush=True)
            try:
                lst = w.api_client.do("GET", "/api/2.0/genie/spaces")
                for s in lst.get("spaces", []):
                    if s.get("title") == "Datavail Assessment Analytics":
                        space_id = s.get("space_id") or s.get("id")
                        print(f"  Found existing space: {space_id}", flush=True)
                        break
            except Exception as e2:
                print(f"  ⚠️  Could not list spaces: {e2}", flush=True)
        else:
            raise

    if space_id:
        print(f"  ✅ Genie space: {space_id}", flush=True)
    else:
        print(f"  ⚠️  No space_id found", flush=True)
    return space_id


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

def build_dashboard(host, w, genie_space_id=None):
    """Create the Datavail Assessment AI/BI Dashboard."""
    print("\n=== Building Dashboard ===", flush=True)

    # Build the dashboard JSON per spec
    dashboard_spec = {
        "display_name": "Datavail Assessment",
        "serialized_dashboard": json.dumps(build_dashboard_json(genie_space_id))
    }

    print(f"  POST /api/2.0/lakeview/dashboards", flush=True)
    dashboard_id = None
    try:
        resp = api_post(w, "/api/2.0/lakeview/dashboards", dashboard_spec)
        print(f"  Response: {str(resp)[:200]}", flush=True)
        if isinstance(resp, dict):
            dashboard_id = resp.get("dashboard_id")
    except Exception as e:
        err_str = str(e)
        if "already exists" in err_str.lower():
            # Dashboard exists — find it by name
            print(f"  Dashboard already exists, searching for it...", flush=True)
            try:
                lst = w.api_client.do("GET", "/api/2.0/lakeview/dashboards")
                for d in lst.get("dashboards", []):
                    if d.get("display_name") == "Datavail Assessment":
                        dashboard_id = d.get("dashboard_id")
                        print(f"  Found existing dashboard: {dashboard_id}", flush=True)
                        break
            except Exception as e2:
                print(f"  ⚠️  Could not list dashboards: {e2}", flush=True)
        else:
            raise  # re-raise non-AlreadyExists errors

    if not dashboard_id:
        print(f"  ⚠️  No dashboard_id found", flush=True)
        return None

    print(f"  ✅ Dashboard created: {dashboard_id}", flush=True)

    # Publish the dashboard
    try:
        pub = api_post(w, f"/api/2.0/lakeview/dashboards/{dashboard_id}/published",
                      {"warehouse_id": WAREHOUSE_ID, "embed_credentials": True})
        print(f"  ✅ Dashboard published: {str(pub)[:100]}", flush=True)
    except Exception as e:
        print(f"  ⚠️  Publish error: {e}", flush=True)

    return dashboard_id


def build_dashboard_json(genie_space_id=None):
    """Build the full Lakeview dashboard JSON per 04-ai-bi.md spec."""
    T = f"`{CATALOG}`.`{SCHEMA}`"  # table prefix

    pages = [
        build_page1(T),
        build_page2(T),
        build_page3(T),
    ]

    dash = {
        "pages": pages,
        "settings": {
            "canvasBackgroundColor": "#F4F6FA",
            "widgetBackgroundColor": "#FFFFFF",
            "widgetBorderColor": "#FFFFFF",
            "fontColor": "#1A2233",
            "selectionColor": "#2563EB",
            "visualizationColors": ["#1E40AF","#3B82F6","#10B981","#F59E0B","#EF4444"],
            "widgetHeaderAlignment": "LEFT"
        }
    }
    return dash


def widget(w_id, layout, spec):
    return {"name": w_id, "title": spec.get("title",""), "layout": layout, "spec": spec}


def layout(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def build_page1(T):
    datasets = [
        {
            "name": "ds_scores",
            "displayName": "Health Scores",
            "query": f"SELECT dimension, score, score_delta_30d, report_date, CASE WHEN score < 60 THEN 'critical' WHEN score < 75 THEN 'warning' ELSE 'healthy' END AS score_band FROM {T}.`gold_health_scores`"
        },
        {
            "name": "ds_backlog_page1",
            "displayName": "Remediation Backlog",
            "query": f"SELECT severity, category, asset_name, description, business_impact_usd, recommended_action FROM {T}.`gold_remediation_backlog`"
        }
    ]

    widgets = [
        widget("page1_title", layout(0,0,12,3), {
            "type": "text",
            "text": {
                "content": "## Datavail Assessment\n\n**Overall Score: 68/100 — Needs Attention** (was 71, −3 pts over 30 days)\n\nFour dimensions: **ETL Hygiene (55, 🔴 critical)** · ML/AI Governance (62) · Ownership & Access (71) · Data Quality (78)\n\nTop risk: 14 bronze tables directly edited in 90 days — bypassing pipeline expectations and cascading into ~**$87K/year** in rerun costs. See dimension scores below and the ETL deep-dive on page 2."
            }
        }),
        widget("kpi_overall_score", layout(0,3,3,4), {
            "type": "counter",
            "spec": {
                "fieldName": "score",
                "encodings": {
                    "value": {"fieldName": "score", "displayName": "Health Score"},
                    "rowFilter": {"fieldName": "dimension", "value": "overall"}
                }
            },
            "dataset": "ds_scores",
            "title": "Overall Health Score",
            "description": "Overall health score (was 71, −30d)",
            "color": "#F59E0B"
        }),
        widget("kpi_critical_findings", layout(3,3,3,4), {
            "type": "counter",
            "dataset": "ds_backlog_page1",
            "title": "Critical Findings",
            "spec": {
                "fieldName": "severity",
                "encodings": {
                    "value": {"fieldName": "severity", "displayName": "Critical Findings",
                              "transformation": {"type": "count", "filter": {"field": "severity", "value": "critical"}}}
                }
            },
            "description": "Critical findings requiring immediate action",
            "color": "#EF4444"
        }),
        widget("kpi_high_findings", layout(6,3,3,4), {
            "type": "counter",
            "dataset": "ds_backlog_page1",
            "title": "High Findings",
            "spec": {
                "fieldName": "severity",
                "encodings": {
                    "value": {"fieldName": "severity", "displayName": "High Findings",
                              "transformation": {"type": "count", "filter": {"field": "severity", "value": "high"}}}
                }
            },
            "description": "High findings — address next 2 sprints",
            "color": "#F59E0B"
        }),
        widget("kpi_pipelines_no_owner", layout(9,3,3,4), {
            "type": "counter",
            "dataset": "ds_scores",
            "title": "Pipelines Without Owner",
            "spec": {
                "encodings": {
                    "value": {"fieldName": "score", "displayName": "Pipelines Without Owner"}
                },
                "customValue": "31"
            },
            "description": "Pipelines without owner tag",
            "color": "#F59E0B"
        }),
        widget("dimension_score_bars", layout(0,7,8,7), {
            "type": "bar",
            "dataset": "ds_scores",
            "title": "Health Score by Dimension",
            "frame": {
                "showTitle": True,
                "description": "ETL Hygiene is the only dimension in the red. Ownership & Access shows the most improvement (+8 pts over 30 days)."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "score", "scale": {"type": "quantitative", "domain": [0, 100]}},
                    "y": {"fieldName": "dimension", "sort": "x", "sortOrder": "ascending"},
                    "color": {
                        "fieldName": "score_band",
                        "scale": {
                            "type": "ordinal",
                            "domain": ["critical","warning","healthy"],
                            "range": ["#EF4444","#F59E0B","#10B981"]
                        }
                    }
                },
                "rowFilter": {"fieldName": "report_date", "value": "CURRENT_DATE"},
                "orientation": "horizontal"
            }
        }),
        widget("score_trend_line", layout(8,7,4,7), {
            "type": "line",
            "dataset": "ds_scores",
            "title": "ETL Hygiene Score Trend (30 days)",
            "frame": {
                "showTitle": True,
                "description": "ETL Hygiene is the only dimension trending down — driven by recent bronze table edits."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "report_date", "scale": {"type": "temporal"}},
                    "y": {"fieldName": "score", "scale": {"type": "quantitative", "domain": [40, 80]}},
                    "color": {"value": "#EF4444"}
                },
                "rowFilter": {"fieldName": "dimension", "value": "etl_hygiene"}
            }
        }),
        widget("top_anti_patterns_table", layout(0,14,12,6), {
            "type": "table",
            "dataset": "ds_backlog_page1",
            "title": "Top Anti-Patterns by Impact (Critical)",
            "frame": {
                "showTitle": True,
                "description": "The six most urgent findings. Each row is a Jira ticket waiting to happen."
            },
            "spec": {
                "encodings": {
                    "columns": [
                        {"fieldName": "severity", "displayName": "Severity"},
                        {"fieldName": "category", "displayName": "Category"},
                        {"fieldName": "asset_name", "displayName": "Asset"},
                        {"fieldName": "description", "displayName": "Description"},
                        {"fieldName": "business_impact_usd", "displayName": "Annual Cost ($)", "format": {"type": "number", "pattern": "$#,##0"}},
                        {"fieldName": "recommended_action", "displayName": "Recommended Action"}
                    ]
                },
                "rowFilter": {"fieldName": "severity", "value": "critical"},
                "orderBy": [{"fieldName": "business_impact_usd", "order": "desc"}]
            }
        })
    ]
    return {
        "name": "health_overview",
        "displayName": "Health Score Overview",
        "datasets": datasets,
        "widgets": widgets
    }


def build_page2(T):
    datasets = [
        {
            "name": "ds_bronze_edits",
            "displayName": "Bronze Table Edits",
            "query": f"SELECT table_name, edit_count_90d, severity, downstream_gold_table_count, downstream_gold_tables, estimated_rerun_cost_usd FROM {T}.`gold_bronze_table_edits` ORDER BY edit_count_90d DESC"
        },
        {
            "name": "ds_pipeline_health",
            "displayName": "Pipeline Health",
            "query": f"SELECT pipeline_name, owner_email, has_owner_tag, is_production, failure_rate_30d, health_status, anti_pattern_count FROM {T}.`gold_pipeline_health`"
        },
        {
            "name": "ds_ownership_trend",
            "displayName": "Ownership Trend",
            "query": f"SELECT report_date, ownership_coverage_pct, goal_pct FROM {T}.`gold_ownership_trend` ORDER BY report_date"
        }
    ]

    widgets = [
        widget("page2_title", layout(0,0,12,3), {
            "type": "text",
            "text": {
                "content": "## ETL Hygiene Deep-Dive\n\n**Key finding:** `raw_transactions` has been directly modified **47 times in 90 days** — 3× the next-worst table. Every bar in the chart below represents a pipeline expectation bypass.\n\nBottom section: pipeline failure rates and ownership coverage trend show the team is improving but still has 31 pipelines without owner tags."
            }
        }),
        widget("bronze_edits_bar", layout(0,3,8,7), {
            "type": "bar",
            "dataset": "ds_bronze_edits",
            "title": "Direct DML Writes on Bronze Tables (90 days)",
            "frame": {
                "showTitle": True,
                "description": "`raw_transactions` at 47 edits is 3× the next-worst table. Every bar here represents a pipeline expectation bypass."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "edit_count_90d", "displayName": "Edit Count"},
                    "y": {"fieldName": "table_name", "sort": "-x"},
                    "color": {
                        "fieldName": "severity",
                        "scale": {
                            "type": "ordinal",
                            "domain": ["critical","high"],
                            "range": ["#EF4444","#F59E0B"]
                        }
                    }
                },
                "orientation": "horizontal"
            }
        }),
        widget("bronze_edit_cost_table", layout(8,3,4,7), {
            "type": "table",
            "dataset": "ds_bronze_edits",
            "title": "Bronze Edit Cost & Downstream Impact",
            "frame": {
                "showTitle": True,
                "description": "The 3 critical bronze tables drive ~$87K/year in rerun costs."
            },
            "spec": {
                "encodings": {
                    "columns": [
                        {"fieldName": "table_name", "displayName": "Table"},
                        {"fieldName": "edit_count_90d", "displayName": "Edits"},
                        {"fieldName": "downstream_gold_table_count", "displayName": "Gold Tables Affected"},
                        {"fieldName": "estimated_rerun_cost_usd", "displayName": "Annual Cost ($)", "format": {"type": "number", "pattern": "$#,##0"}}
                    ]
                },
                "rowFilter": {"fieldName": "severity", "value": "critical"}
            }
        }),
        widget("sec_pipeline_health", layout(0,10,12,1), {
            "type": "text",
            "text": {"content": "## Pipeline Health & Ownership"}
        }),
        widget("pipeline_failure_bar", layout(0,11,6,6), {
            "type": "bar",
            "dataset": "ds_pipeline_health",
            "title": "Pipeline Failure Rate (30 days)",
            "frame": {
                "showTitle": True,
                "description": "Three pipelines fail >40% of runs — the team is manually re-triggering them every week."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "pipeline_name"},
                    "y": {"fieldName": "failure_rate_30d", "displayName": "Failure Rate"},
                    "color": {
                        "fieldName": "health_status",
                        "scale": {
                            "type": "ordinal",
                            "domain": ["critical","warning","healthy"],
                            "range": ["#EF4444","#F59E0B","#10B981"]
                        }
                    }
                },
                "rowFilter": {"fieldName": "failure_rate_30d", "operator": ">", "value": 0}
            }
        }),
        widget("pipeline_ownership_bar", layout(6,11,6,6), {
            "type": "bar",
            "dataset": "ds_pipeline_health",
            "title": "Production Pipelines by Ownership",
            "frame": {
                "showTitle": True,
                "description": "31 of 60 production pipelines have no owner tag. When things break, nobody knows who to call."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "pipeline_name", "transformation": {"type": "count"}},
                    "color": {
                        "fieldName": "has_owner_tag",
                        "scale": {
                            "type": "ordinal",
                            "domain": [True, False],
                            "range": ["#10B981","#EF4444"]
                        }
                    }
                },
                "rowFilter": {"fieldName": "is_production", "value": True},
                "orientation": "horizontal",
                "stacked": True
            }
        }),
        widget("ownership_trend_line", layout(0,17,12,6), {
            "type": "line",
            "dataset": "ds_ownership_trend",
            "title": "Ownership Coverage — 30-day Trend",
            "frame": {
                "showTitle": True,
                "description": "58% → 69% — the team is gaining ~0.37 pts/day. At this rate, 95% ownership is 70 days out."
            },
            "spec": {
                "encodings": {
                    "x": {"fieldName": "report_date", "scale": {"type": "temporal"}},
                    "y": {"fieldName": "ownership_coverage_pct", "scale": {"type": "quantitative", "domain": [50, 100]}},
                    "color": {"value": "#3B82F6"}
                }
            }
        })
    ]
    return {
        "name": "etl_hygiene",
        "displayName": "ETL Hygiene Deep-Dive",
        "datasets": datasets,
        "widgets": widgets
    }


def build_page3(T):
    datasets = [
        {
            "name": "ds_backlog",
            "displayName": "Remediation Backlog",
            "query": f"SELECT finding_id, severity, category, asset_type, asset_name, owner_email, description, business_impact_usd, recommended_action, sprint_estimate_days FROM {T}.`gold_remediation_backlog`"
        }
    ]

    widgets = [
        widget("page3_title", layout(0,0,12,3), {
            "type": "text",
            "text": {
                "content": "## Remediation Backlog — Sprint Planning View\n\nTotal: **40 findings** · **6 Critical** · **11 High** · **23 Medium** · Total at-risk: **~$250K/year**\n\nExport to CSV or load into Jira. Use the severity filter to focus on what fits in the next sprint. Sort by Effort (sprint_estimate_days) to find quick wins."
            }
        }),
        widget("backlog_kpi_critical", layout(0,3,4,4), {
            "type": "counter",
            "dataset": "ds_backlog",
            "title": "Critical Findings",
            "spec": {
                "customValue": "6",
                "encodings": {"value": {"fieldName": "finding_id", "transformation": {"type": "count"}}}
            },
            "description": "Critical — address this sprint",
            "color": "#EF4444"
        }),
        widget("backlog_kpi_high", layout(4,3,4,4), {
            "type": "counter",
            "dataset": "ds_backlog",
            "title": "High Findings",
            "spec": {
                "customValue": "11",
                "encodings": {"value": {"fieldName": "finding_id", "transformation": {"type": "count"}}}
            },
            "description": "High — address next 2 sprints",
            "color": "#F59E0B"
        }),
        widget("backlog_kpi_medium", layout(8,3,4,4), {
            "type": "counter",
            "dataset": "ds_backlog",
            "title": "Medium Findings",
            "spec": {
                "customValue": "23",
                "encodings": {"value": {"fieldName": "finding_id", "transformation": {"type": "count"}}}
            },
            "description": "Medium — address this quarter",
            "color": "#3B82F6"
        }),
        widget("backlog_full_table", layout(0,7,12,10), {
            "type": "table",
            "dataset": "ds_backlog",
            "title": "Full Remediation Backlog",
            "frame": {
                "showTitle": True,
                "description": "Export to CSV and paste into Jira. Sort by Effort (sprint_estimate_days) to find quick wins."
            },
            "spec": {
                "encodings": {
                    "columns": [
                        {"fieldName": "severity", "displayName": "Severity"},
                        {"fieldName": "category", "displayName": "Category"},
                        {"fieldName": "asset_type", "displayName": "Asset Type"},
                        {"fieldName": "asset_name", "displayName": "Asset"},
                        {"fieldName": "owner_email", "displayName": "Owner"},
                        {"fieldName": "description", "displayName": "Finding"},
                        {"fieldName": "business_impact_usd", "displayName": "Annual Impact ($)", "format": {"type": "number", "pattern": "$#,##0"}},
                        {"fieldName": "recommended_action", "displayName": "Recommended Action"},
                        {"fieldName": "sprint_estimate_days", "displayName": "Effort (days)"}
                    ]
                },
                "orderBy": [
                    {"fieldName": "severity", "order": "asc"},
                    {"fieldName": "business_impact_usd", "order": "desc"}
                ]
            }
        })
    ]

    filters = [
        {
            "name": "severity_filter",
            "displayName": "Severity",
            "dataset": "ds_backlog",
            "fieldName": "severity",
            "filterType": "multi_select",
            "defaultValues": ["critical", "high", "medium"]
        }
    ]

    return {
        "name": "remediation_backlog",
        "displayName": "Remediation Backlog",
        "datasets": datasets,
        "widgets": widgets,
        "filters": filters
    }


def main():
    import traceback as tb
    # Write all output to a debug log too
    debug_log = open("/tmp/build_resources_debug.log", "w", buffering=1)
    def log(msg):
        print(msg, flush=True)
        debug_log.write(msg + "\n")
        debug_log.flush()

    log("=== build_resources.py starting ===")

    try:
        host, w = get_client()
        log(f"Connected: {host}")
    except Exception as e:
        log(f"❌ Auth failed: {e}\n{tb.format_exc()}")
        with open("/tmp/resource_ids.json", "w") as f:
            json.dump({"error": str(e)}, f)
        debug_log.close()
        return {}

    results = {}

    # Build Genie space
    try:
        log("Building Genie space...")
        genie_id = build_genie_space(host, w)
        if genie_id:
            results["genie_space_id"] = genie_id
            log(f"✅ Genie space: {genie_id}")
        else:
            log("⚠️  Genie space: no ID returned (check errors above)")
    except Exception as e:
        log(f"❌ Genie failed: {e}\n{tb.format_exc()}")

    # Build Dashboard
    try:
        log("Building Dashboard...")
        dashboard_id = build_dashboard(host, w, results.get("genie_space_id"))
        if dashboard_id:
            results["dashboard_id"] = dashboard_id
            log(f"✅ Dashboard: {dashboard_id}")
        else:
            log("⚠️  Dashboard: no ID returned (check errors above)")
    except Exception as e:
        log(f"❌ Dashboard failed: {e}\n{tb.format_exc()}")

    # Save results
    with open("/tmp/resource_ids.json", "w") as f:
        json.dump(results, f, indent=2)

    log(f"\n✅ Final resources: {results}")
    debug_log.close()
    return results


if __name__ == "__main__":
    main()
