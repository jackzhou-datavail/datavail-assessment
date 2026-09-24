"""Generate the Platform Onboarding Assessment AI/BI dashboard.

Emits a Lakeview dashboard JSON reading from the assessment result
tables. Separate from the Datavail Assessment dashboard in
src/dashboard/ — different data, different resource.

    python build_dashboard.py --results-catalog assessment

Writes assessment/dashboard.lvdash.json. Deploy with deploy_dashboard.py.

Scoring shown here is deliberately two-dimensional: every score is
paired with the coverage it was computed from, and a category whose
coverage is below the floor is graded INSUFFICIENT DATA rather than
given a number that would imply more confidence than exists.
"""

from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Grade bands for the onboarding readiness score.
GOOD, FAIR = 80, 60
MIN_COVERAGE = 40  # below this, a category score is not trustworthy

GREEN, AMBER, RED, GREY = "#10B981", "#F59E0B", "#EF4444", "#94A3B8"


def latest(catalog: str, schema: str) -> str:
    return (
        f"(SELECT run_id FROM {catalog}.{schema}.assessment_run "
        f"WHERE status = 'COMPLETE' ORDER BY run_ts DESC LIMIT 1)"
    )


def datasets(catalog: str, schema: str) -> list[dict]:
    base = f"{catalog}.{schema}"
    run = latest(catalog, schema)

    def ds(name: str, display: str, sql: str) -> dict:
        return {"name": name, "displayName": display,
                "queryLines": [l + "\n" for l in sql.strip().splitlines()]}

    return [
        ds("ds_overall", "Overall Onboarding Score", f"""
SELECT
  s.overall_score,
  s.coverage_pct,
  s.confidence,
  s.critical_gaps,
  s.n_measured,
  s.n_not_available,
  s.n_not_applicable,
  s.n_patterns,
  CASE
    WHEN s.coverage_pct < {MIN_COVERAGE} THEN 'INSUFFICIENT DATA'
    WHEN s.overall_score >= {GOOD} THEN 'GOOD'
    WHEN s.overall_score >= {FAIR} THEN 'FAIR'
    ELSE 'POOR'
  END AS onboarding_grade,
  r.run_ts,
  r.lookback_days,
  r.registry_version
FROM {base}.assessment_score s
JOIN {base}.assessment_run r ON r.run_id = s.run_id
WHERE s.run_id = {run}
"""),

        ds("ds_category", "Category Readiness", f"""
SELECT
  category,
  ROUND(weighted_score, 1) AS score,
  ROUND(coverage_pct, 1)   AS coverage_pct,
  n_measured,
  n_not_available,
  n_not_applicable,
  n_poor,
  CASE
    WHEN coverage_pct < {MIN_COVERAGE} THEN 'INSUFFICIENT DATA'
    WHEN weighted_score >= {GOOD} THEN 'GOOD'
    WHEN weighted_score >= {FAIR} THEN 'FAIR'
    ELSE 'POOR'
  END AS implementation
FROM {base}.category_score
WHERE run_id = {run}
"""),

        ds("ds_checks", "Measured Checks", f"""
SELECT
  category,
  pattern_id,
  title,
  severity,
  grade,
  ROUND(conformance_pct, 1) AS conformance_pct,
  numerator,
  denominator,
  unit,
  finding_count,
  CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3 ELSE 4 END AS severity_rank
FROM {base}.v_latest_report
WHERE status = 'MEASURED'
"""),

        ds("ds_gaps", "Priority Remediation", f"""
SELECT
  severity,
  category,
  pattern_id,
  title,
  ROUND(conformance_pct, 1) AS conformance_pct,
  grade,
  CONCAT(CAST(numerator AS STRING), ' / ', CAST(denominator AS STRING), ' ', unit) AS coverage_detail,
  finding_count,
  doc_path
FROM {base}.v_latest_report
WHERE status = 'MEASURED' AND grade IN ('POOR', 'FAIR')
ORDER BY
  CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3 ELSE 4 END,
  conformance_pct
"""),

        ds("ds_findings", "Evidence", f"""
SELECT
  f.pattern_id,
  reg.category,
  reg.severity,
  f.object_type,
  f.object_name,
  f.owner,
  f.metric_name,
  f.metric_value
FROM {base}.check_finding f
JOIN {base}.pattern_registry reg
  ON reg.run_id = f.run_id AND reg.pattern_id = f.pattern_id
WHERE f.run_id = {run}
ORDER BY f.metric_value DESC NULLS LAST
"""),

        ds("ds_status", "Measurement Status", f"""
SELECT status, COUNT(*) AS n_patterns
FROM {base}.check_result
WHERE run_id = {run}
GROUP BY status
"""),

        ds("ds_blindspots", "Blind Spots", f"""
SELECT
  reg.check_tier,
  reg.severity,
  reg.category,
  res.pattern_id,
  reg.title,
  res.reason
FROM {base}.check_result res
JOIN {base}.pattern_registry reg
  ON reg.run_id = res.run_id AND reg.pattern_id = res.pattern_id
WHERE res.run_id = {run} AND res.status = 'NOT_AVAILABLE'
ORDER BY
  CASE reg.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 ELSE 3 END,
  reg.check_tier
"""),

        ds("ds_tier", "Coverage by Tier", f"""
SELECT
  reg.check_tier,
  COUNT(*) AS n_patterns,
  SUM(CASE WHEN res.status = 'MEASURED' THEN 1 ELSE 0 END) AS n_measured
FROM {base}.check_result res
JOIN {base}.pattern_registry reg
  ON reg.run_id = res.run_id AND reg.pattern_id = res.pattern_id
WHERE res.run_id = {run}
GROUP BY reg.check_tier
"""),
    ]


# --- widget builders --------------------------------------------------

def text(name: str, lines: list[str], x, y, w, h) -> dict:
    return {"widget": {"name": name,
                       "multilineTextboxSpec": {"lines": [l + "\n" for l in lines]}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def q(dataset: str, fields: list[str]) -> list[dict]:
    return [{"name": "main_query",
             "query": {"datasetName": dataset,
                       "fields": [{"name": f, "expression": f"`{f}`"} for f in fields],
                       "disaggregated": True}}]


def counter(name, dataset, field, title, desc, x, y, w=3, h=4) -> dict:
    return {"widget": {"name": name, "queries": q(dataset, [field]),
                       "spec": {"version": 2, "widgetType": "counter",
                                "encodings": {"value": {"fieldName": field, "displayName": title}},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def bar(name, dataset, xf, yf, colorf, mappings, title, desc, x, y, w, h,
        xscale="quantitative", yscale="categorical") -> dict:
    enc = {"x": {"fieldName": xf, "scale": {"type": xscale}},
           "y": {"fieldName": yf, "scale": {"type": yscale}}}
    if colorf:
        enc["color"] = {"fieldName": colorf,
                        "scale": {"type": "categorical", "mappings": mappings}}
    fields = [xf, yf] + ([colorf] if colorf else [])
    return {"widget": {"name": name, "queries": q(dataset, fields),
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
                                "mark": {"layout": "group"},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def table(name, dataset, cols, title, desc, x, y, w, h) -> dict:
    return {"widget": {"name": name, "queries": q(dataset, [c[0] for c in cols]),
                       "spec": {"version": 2, "widgetType": "table",
                                "encodings": {"columns": [
                                    {"fieldName": c[0], "displayName": c[1]} for c in cols]},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def pie(name, dataset, colorf, anglef, mappings, title, desc, x, y, w, h) -> dict:
    return {"widget": {"name": name, "queries": q(dataset, [colorf, anglef]),
                       "spec": {"version": 3, "widgetType": "pie",
                                "encodings": {
                                    "angle": {"fieldName": anglef, "scale": {"type": "quantitative"}},
                                    "color": {"fieldName": colorf,
                                              "scale": {"type": "categorical", "mappings": mappings}}},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


GRADE_COLORS = [{"value": "GOOD", "color": GREEN}, {"value": "FAIR", "color": AMBER},
                {"value": "POOR", "color": RED}, {"value": "INSUFFICIENT DATA", "color": GREY}]
STATUS_COLORS = [{"value": "MEASURED", "color": GREEN},
                 {"value": "NOT_AVAILABLE", "color": GREY},
                 {"value": "NOT_APPLICABLE", "color": "#64748B"},
                 {"value": "ERROR", "color": RED}]


def build(catalog: str, schema: str) -> dict:
    page1 = [
        text("p1_title", [
            "# Platform Onboarding Assessment",
            "",
            "How closely this workspace follows documented Databricks practice, measured from "
            "Unity Catalog system tables against the pattern library.",
            "",
            "**Read the score with the coverage.** Only checks that could actually be measured "
            "contribute to a score. A category measured on thin evidence is graded "
            "*INSUFFICIENT DATA* rather than given a misleading number.",
        ], 0, 0, 6, 5),
        counter("kpi_score", "ds_overall", "overall_score", "Onboarding Score",
                "Weighted mean conformance across measured checks (0-100)", 6, 0, 3, 5),
        counter("kpi_coverage", "ds_overall", "coverage_pct", "Measurement Coverage",
                "Share of applicable weight that could be measured", 9, 0, 3, 5),
        counter("kpi_grade", "ds_overall", "onboarding_grade", "Overall Implementation",
                f"GOOD >= {GOOD}, FAIR >= {FAIR}, else POOR", 0, 5, 3, 3),
        counter("kpi_critical", "ds_overall", "critical_gaps", "Critical Gaps",
                "CRITICAL-severity checks graded POOR", 3, 5, 3, 3),
        counter("kpi_measured", "ds_overall", "n_measured", "Checks Measured",
                "Patterns that produced a percentage", 6, 5, 3, 3),
        counter("kpi_unavailable", "ds_overall", "n_not_available", "Not Measurable",
                "Patterns with no obtainable data this run", 9, 5, 3, 3),
        bar("cat_score_bars", "ds_category", "score", "category", "implementation",
            GRADE_COLORS, "Implementation by Category",
            "Weighted conformance per category, coloured by grade.", 0, 8, 6, 7),
        bar("cat_coverage_bars", "ds_category", "coverage_pct", "category", None, None,
            "Measurement Coverage by Category",
            f"Share of each category actually measured. Below {MIN_COVERAGE}% the score is not "
            "trustworthy and the grade reads INSUFFICIENT DATA.", 6, 8, 6, 7),
        table("cat_table", "ds_category",
              [("category", "Category"), ("implementation", "Implementation"),
               ("score", "Score"), ("coverage_pct", "Coverage %"),
               ("n_measured", "Measured"), ("n_not_available", "Not Available"),
               ("n_poor", "Poor")],
              "Category Scorecard",
              "Every category with its grade, score, and how much of it was visible.",
              0, 15, 12, 7),
    ]

    page2 = [
        text("p2_title", [
            "## Findings and Remediation",
            "",
            "Checks that produced a measurement, worst first. Severity is the pattern's rank in "
            "the registry; grade compares the measured conformance against that pattern's own "
            "target and floor.",
        ], 0, 0, 12, 3),
        table("gaps_table", "ds_gaps",
              [("severity", "Severity"), ("category", "Category"), ("title", "Pattern"),
               ("conformance_pct", "Conformance %"), ("grade", "Grade"),
               ("coverage_detail", "Objects"), ("finding_count", "Evidence Rows"),
               ("doc_path", "Pattern Doc")],
              "Priority Remediation List",
              "Measured checks graded POOR or FAIR, ordered by severity then conformance.",
              0, 3, 12, 10),
        bar("checks_bars", "ds_checks", "conformance_pct", "title", "grade", GRADE_COLORS,
            "Conformance by Pattern",
            "All measured checks. Bars near zero are the practices not being followed at all.",
            0, 13, 12, 11),
        table("evidence_table", "ds_findings",
              [("severity", "Severity"), ("category", "Category"), ("pattern_id", "Pattern"),
               ("object_type", "Type"), ("object_name", "Object"), ("owner", "Owner"),
               ("metric_name", "Metric"), ("metric_value", "Value")],
              "Evidence",
              "The specific objects behind each finding — the remediation worklist.",
              0, 24, 12, 10),
    ]

    page3 = [
        text("p3_title", [
            "## Coverage and Blind Spots",
            "",
            "What this assessment could **not** see, and why. Every unmeasured pattern carries a "
            "reason: a system schema that is not enabled, a missing grant, a renamed column, or a "
            "check tier that needs an API this collector does not call.",
            "",
            "This page exists so the headline score is never mistaken for a complete review.",
        ], 0, 0, 12, 4),
        pie("status_pie", "ds_status", "status", "n_patterns", STATUS_COLORS,
            "Measurement Status", "How the pattern library resolved against this workspace.",
            0, 4, 4, 7),
        bar("tier_bars", "ds_tier", "n_patterns", "check_tier", None, None,
            "Patterns by Check Tier",
            "SYSTEM_TABLE is implemented. WORKSPACE_API, ACCOUNT_API, TABLE_DETAIL and MANUAL "
            "tiers need collectors that do not exist yet.", 4, 4, 8, 7),
        table("blindspot_table", "ds_blindspots",
              [("severity", "Severity"), ("check_tier", "Tier"), ("category", "Category"),
               ("title", "Pattern"), ("reason", "Why Not Measured")],
              "Unmeasured Patterns",
              "Ranked by severity — the CRITICAL rows are the most important things this "
              "assessment cannot currently tell you.",
              0, 11, 12, 11),
    ]

    return {
        "datasets": datasets(catalog, schema),
        "pages": [
            {"name": "scorecard", "displayName": "Onboarding Scorecard", "layout": page1},
            {"name": "findings", "displayName": "Findings", "layout": page2},
            {"name": "coverage", "displayName": "Coverage & Blind Spots", "layout": page3},
        ],
        "uiSettings": {"theme": {"widgetHeaderAlignment": "LEFT"}},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-catalog", default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"))
    ap.add_argument("--results-schema", default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"))
    ap.add_argument("--out", default=os.path.join(HERE, "dashboard.lvdash.json"))
    args = ap.parse_args()

    dash = build(args.results_catalog, args.results_schema)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(dash, fh, indent=2)
    n_widgets = sum(len(p["layout"]) for p in dash["pages"])
    print(f"Wrote {args.out}")
    print(f"  {len(dash['datasets'])} datasets, {len(dash['pages'])} pages, {n_widgets} widgets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
