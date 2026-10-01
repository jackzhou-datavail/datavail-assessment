"""Generate the Conformance Assessment AI/BI dashboard.

Emits a Lakeview dashboard JSON reading from the assessment result
tables.

    python -m datavail_assessment.conformance.dashboard.build --results-catalog assessment

Writes conformance_assessment.lvdash.json beside this file. The bundle
deploys it as the "Conformance Assessment" dashboard.

Scoring shown here is deliberately two-dimensional: every score is
paired with the coverage it was computed from. The grade describes the
score; coverage is reported beside it as its own number rather than
overriding it. Grading a real score INSUFFICIENT DATA contradicted the
score printed next to it - if a number is worth showing, it is worth
grading, and the reader judges it against the coverage.

Only a category with nothing measured at all reads NOT AVAILABLE, because
there is genuinely no score to grade.
"""

from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Grade bands for the conformance readiness score.
GOOD, FAIR = 80, 60
# A categorical bar chart renders only what fits its height and drops
# the rest silently, so the dataset is bounded and ordered instead.
# Unbounded it returned 56 rows, about 30 rendered, and WITHOUT an
# ORDER BY those 30 were an arbitrary 30 rather than the worst 30.
CHART_ROWS = 30

MIN_COVERAGE = 40  # below this, a category score is not trustworthy

GREEN, AMBER, RED, GREY = "#10B981", "#F59E0B", "#EF4444", "#94A3B8"


def latest(catalog: str, schema: str) -> str:
    return (
        f"(SELECT run_id FROM {catalog}.{schema}.assessment_run "
        f"WHERE status = 'COMPLETE' ORDER BY run_ts DESC LIMIT 1)"
    )


def datasets(catalog: str, schema: str, link_base: str = "",
             org_id: str = "") -> list[dict]:
    base = f"{catalog}.{schema}"
    # Absolute console links when the workspace is known, relative
    # otherwise. `?o=<workspace_id>` is what disambiguates the workspace
    # for anyone whose account has more than one; without it the link
    # can land in the wrong workspace.
    lb = link_base.rstrip("/")
    oq = f"?o={org_id}" if org_id else ""
    run = latest(catalog, schema)

    def ds(name: str, display: str, sql: str) -> dict:
        return {"name": name, "displayName": display,
                "queryLines": [l + "\n" for l in sql.strip().splitlines()]}

    return [
        ds("ds_overall", "Overall Conformance Score", f"""
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
    WHEN s.overall_score IS NULL THEN 'NOT AVAILABLE'
    WHEN s.overall_score >= {GOOD} THEN 'GOOD'
    WHEN s.overall_score >= {FAIR} THEN 'FAIR'
    ELSE 'POOR'
  END AS conformance_grade,
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
    WHEN weighted_score IS NULL THEN 'NOT AVAILABLE'
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
ORDER BY conformance_pct, severity_rank
LIMIT {CHART_ROWS}
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
  f.metric_value,
  -- Relative, so the link works in any workspace. Each object type has
  -- its own console path; anything without one gets NULL and renders as
  -- plain text rather than a link to nowhere.
  CASE
    WHEN f.object_type IN ('TABLE', 'VIEW') AND size(split(f.object_id, '[.]')) = 3
      THEN concat('{lb}/explore/data/', replace(f.object_id, '.', '/'), '{oq}')
    WHEN f.object_type = 'COLUMN' AND size(split(f.object_id, '[.]')) >= 4
      THEN concat('{lb}/explore/data/',
                  array_join(slice(split(f.object_id, '[.]'), 1, 3), '/'), '{oq}')
    WHEN f.object_type = 'JOB'        THEN concat('{lb}/jobs/', f.object_id, '{oq}')
    WHEN f.object_type = 'JOB_TASK'   THEN concat('{lb}/jobs/', split(f.object_id, ':')[0], '{oq}')
    WHEN f.object_type = 'JOB_RUN'    THEN concat('{lb}/jobs/runs/', f.object_id, '{oq}')
    WHEN f.object_type = 'EXPERIMENT' THEN concat('{lb}/ml/experiments/', f.object_id, '{oq}')
    WHEN f.object_type = 'CLUSTER'    THEN concat('{lb}/compute/clusters/', f.object_id, '{oq}')
    WHEN f.object_type = 'PIPELINE'   THEN concat('{lb}/pipelines/', f.object_id, '{oq}')
    ELSE NULL
  END AS object_url
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
    """`desc` may be empty - a tile whose title already says everything
    reads better without a subtitle restating it."""
    frame = {"showTitle": True, "title": title}
    if desc:
        frame["showDescription"] = True
        frame["description"] = desc
    else:
        frame["showDescription"] = False
    return {"widget": {"name": name, "queries": q(dataset, [field]),
                       "spec": {"version": 2, "widgetType": "counter",
                                "encodings": {"value": {"fieldName": field, "displayName": title}},
                                "frame": frame}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def bar(name, dataset, xf, yf, colorf, mappings, title, desc, x, y, w, h,
        xscale="quantitative", yscale="categorical") -> dict:
    enc = {"x": {"fieldName": xf, "scale": {"type": xscale}},
           "y": {"fieldName": yf, "scale": {"type": yscale}}}
    if colorf:
        enc["color"] = {"fieldName": colorf,
                        "scale": {"type": "categorical", "mappings": mappings}}
    fields = [xf, yf] + ([colorf] if colorf else [])
    # "group" reserves a sub-slot per colour value for EVERY category, so
    # a chart coloured by grade draws four slots per row and fills one -
    # it reads as several bars per label with gaps between them. Each
    # category here has exactly one row, so "stack" collapses to a single
    # full-thickness bar and the colour still encodes the grade.
    layout = "stack" if colorf else "group"
    return {"widget": {"name": name, "queries": q(dataset, fields),
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
                                "mark": {"layout": layout},
                                "frame": {"showTitle": True, "title": title,
                                          "showDescription": True, "description": desc}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


# Numeric columns, so tables can right-align them. Lakeview left-aligns
# every column by default, which leaves digits ragged under a header and
# makes columns of different magnitudes hard to compare down the page.
_NUMERIC = {
    "score", "coverage_pct", "conformance_pct", "weighted_score",
    "n_measured", "n_not_available", "n_not_applicable", "n_poor",
    "n_patterns", "n_error", "finding_count", "metric_value",
    "critical_gaps", "overall_score",
}

# Counts are whole numbers; percentages and scores carry one decimal.
_INTEGER = {"n_measured", "n_not_available", "n_not_applicable", "n_poor",
            "n_patterns", "n_error", "finding_count", "critical_gaps"}


def _column(field: str, label: str, order: int, link_text: str | None = None,
            visible: bool = True) -> dict:
    """Numeric cells are centred, not right-aligned.

    Lakeview centres table column HEADERS and offers no property to
    change that - alignContent is the only alignment field in the whole
    schema, and it governs cell content only. Right-aligned digits under
    a centred header read as a mistake, so the cells follow the header.
    Right alignment would scan better down a column of numbers; it is
    not available without a mismatched header.
    """
    numeric = field in _NUMERIC
    col = {"fieldName": field, "displayName": label, "title": label,
           "order": order, "visible": visible,
           "alignContent": "center" if numeric else "left"}
    if link_text:
        # This column's own value IS the URL. {{ @ }} is the only
        # template Lakeview resolves - a cross-column {{ other }} does
        # not substitute, and the cell renders as inert text instead of
        # a link. So the URL lives in the displayed column and the label
        # is a literal, rather than the URL living in a hidden column.
        col.update({"displayAs": "link", "type": "string",
                    "linkUrlTemplate": "{{ @ }}",
                    "linkTextTemplate": link_text,
                    "linkTitleTemplate": "{{ @ }}",
                    "linkOpenInNewTab": True, "highlightLinks": True,
                    "alignContent": "center"})
        return col
    if numeric:
        col["type"] = "integer" if field in _INTEGER else "float"
        col["displayAs"] = "number"
        col["numberFormat"] = "0" if field in _INTEGER else "0.0"
    else:
        col["type"] = "string"
        col["displayAs"] = "string"
    return col


def table(name, dataset, cols, title, desc, x, y, w, h, link_cols=None) -> dict:
    """`link_cols` maps a column holding a URL to the label its cells
    should show, e.g. {"object_url": "open"}."""
    link_cols = link_cols or {}
    all_cols = list(cols)
    return {"widget": {"name": name, "queries": q(dataset, [c[0] for c in all_cols]),
                       "spec": {"version": 2, "widgetType": "table",
                                "encodings": {"columns": [
                                    _column(c[0], c[1], i,
                                            link_text=link_cols.get(c[0]))
                                    for i, c in enumerate(all_cols)]},
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
                {"value": "POOR", "color": RED}, {"value": "NOT AVAILABLE", "color": GREY}]
STATUS_COLORS = [{"value": "MEASURED", "color": GREEN},
                 {"value": "NOT_AVAILABLE", "color": GREY},
                 {"value": "NOT_APPLICABLE", "color": "#64748B"},
                 {"value": "ERROR", "color": RED}]


def build(catalog: str, schema: str, link_base: str = "",
          org_id: str = "") -> dict:
    page1 = [
        text("p1_title", [
            "# Conformance Assessment",
            "",
            "**Of the things this workspace does, how well does it do them?**",
            "",
            "- **Score** - of the checks we ran, how closely the practice was followed.",
            "- **Coverage** - how many of the checks we could run at all.",
            "",
            "**Low coverage is our gap, not the workspace's.** Three outcomes per "
            "check, and the difference between the last two matters:",
            "",
            "- **Measured** - produced a number.",
            "- **Not available** - relevant here, but we could not look: no check "
            "written, no account access, a system table missing a column. This is "
            "what pulls coverage down, and saying so is the point.",
            "- **Nothing in scope** - no clusters, no shared data, no table large "
            "enough to compact. Excluded from coverage, because a practice with "
            "nothing to govern is not something we failed to measure.",
            "",
            "Every practice here comes from Databricks' own guidance, so *nothing "
            "in scope* never means the practice is irrelevant - only that this "
            "workspace has nothing it would apply to yet.",
        ], 0, 0, 6, 8),
        counter("kpi_score", "ds_overall", "overall_score", "Conformance Score",
                "Severity-weighted % across measured checks", 6, 0, 3, 5),
        counter("kpi_coverage", "ds_overall", "coverage_pct", "Measurement Coverage",
                "Severity-weighted % of all checks we could run", 9, 0, 3, 5),
        counter("kpi_grade", "ds_overall", "conformance_grade", "Overall Implementation",
                "", 0, 5, 3, 3),
        counter("kpi_critical", "ds_overall", "critical_gaps", "Critical Gaps",
                "CRITICAL-severity checks graded POOR", 3, 5, 3, 3),
        counter("kpi_measured", "ds_overall", "n_measured", "Checks Measured",
                "Checks that produced a score", 6, 5, 3, 3),
        counter("kpi_unavailable", "ds_overall", "n_not_available", "Checks Not Available",
                "Mostly practices with no check written yet; a few ran and found "
                "no data. Coverage page has the split.", 9, 5, 3, 3),
        bar("cat_score_bars", "ds_category", "score", "category", "implementation",
            GRADE_COLORS, "Implementation by Category",
            "Weighted conformance per category, coloured by grade.", 0, 8, 6, 7),
        bar("cat_coverage_bars", "ds_category", "coverage_pct", "category", None, None,
            "Measurement Coverage by Category",
            f"Severity-weighted %. Below {MIN_COVERAGE}%, read the score as "
            f"indicative.", 6, 8, 6, 7),
        table("cat_table", "ds_category",
              [("category", "Category"), ("implementation", "Implementation"),
               ("score", "Score"), ("coverage_pct", "Measurement Coverage"),
               ("n_measured", "Checks Measured"),
               ("n_not_available", "Checks Not Available"),
               ("n_not_applicable", "Nothing In Scope"),
               ("n_poor", "Poor")],
              "Category Scorecard",
              "Every category with its grade, score, and how much of it was visible.",
              0, 15, 12, 7),
    ]

    page2 = [
        text("p2_title", [
            "## Findings and Remediation",
            "",
            "Checks that produced a measurement, worst first. Grade compares the result "
            "against that check's own target and floor.",
        ], 0, 0, 12, 3),
        table("gaps_table", "ds_gaps",
              [("severity", "Severity"), ("category", "Category"), ("title", "Check"),
               ("conformance_pct", "Conformance %"), ("grade", "Grade"),
               ("coverage_detail", "Objects"), ("finding_count", "Evidence Rows"),
               ("doc_path", "Reference")],
              "Priority Remediation List",
              "Measured checks graded POOR or FAIR, ordered by severity then conformance.",
              0, 3, 12, 10),
        bar("checks_bars", "ds_checks", "conformance_pct", "title", "grade", GRADE_COLORS,
            f"{CHART_ROWS} Lowest-Scoring Checks",
            "Worst first. Bars near zero are practices not being followed at all. "
            "Every measured check is in the table above; this chart is bounded "
            "because a taller one silently drops rows.",
            0, 13, 12, 14),
        table("evidence_table", "ds_findings",
              [("severity", "Severity"), ("category", "Category"), ("pattern_id", "Check"),
               ("object_type", "Type"), ("object_name", "Object"), ("owner", "Owner"),
               ("metric_name", "Metric"), ("metric_value", "Value"),
               ("object_url", "Open")],
              "Evidence",
              "The specific objects behind each finding — the remediation worklist. "
              "Open goes straight to the table, job or experiment.",
              0, 24, 12, 10,
              link_cols={"object_url": "open"}),
    ]

    page3 = [
        text("p3_title", [
            "## Coverage and Blind Spots",
            "",
            "What this assessment could **not** see, and why. Every check without a result "
            "carries a reason: a system schema that is not enabled, a missing grant, a renamed "
            "column, or a tier needing an API this collector does not call.",
            "",
            "This page exists so the headline score is never mistaken for a complete review.",
        ], 0, 0, 12, 4),
        pie("status_pie", "ds_status", "status", "n_patterns", STATUS_COLORS,
            "Measurement Status", "How every check resolved against this workspace.",
            0, 4, 4, 7),
        bar("tier_bars", "ds_tier", "n_patterns", "check_tier", None, None,
            "Checks by Tier",
            "Why each check without a result has none.", 4, 4, 8, 7),
        table("blindspot_table", "ds_blindspots",
              [("severity", "Severity"), ("check_tier", "Tier"), ("category", "Category"),
               ("title", "Check"), ("reason", "Why Not Measured")],
              "Checks Without a Result",
              "Ranked by severity - the CRITICAL rows matter most.",
              0, 11, 12, 11),
    ]

    return {
        "datasets": datasets(catalog, schema, link_base, org_id),
        "pages": [
            {"name": "scorecard", "displayName": "Conformance: Scorecard", "layout": page1},
            {"name": "findings", "displayName": "Conformance: Findings", "layout": page2},
            {"name": "coverage", "displayName": "Conformance: Coverage & Blind Spots", "layout": page3},
        ],
        "uiSettings": {"theme": {"widgetHeaderAlignment": "LEFT"}},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-catalog", default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"))
    ap.add_argument("--results-schema", default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"))
    ap.add_argument("--out", default=os.path.join(HERE, "conformance_assessment.lvdash.json"))
    # Baked into the JSON at build time: the dashboard's own SQL has no
    # way to learn its host or workspace id. Regenerating for another
    # workspace means passing these again, or the Evidence links will
    # point at this one.
    ap.add_argument("--workspace-url",
                    default=os.environ.get("ASSESSMENT_WORKSPACE_URL",
                                           os.environ.get("DATABRICKS_HOST", "")),
                    help="e.g. https://dbc-xxxx.cloud.databricks.com. Omitted, "
                         "Evidence links are workspace-relative.")
    ap.add_argument("--org-id", default=os.environ.get("ASSESSMENT_ORG_ID", ""),
                    help="Workspace id for the ?o= parameter. Find it with: SELECT "
                         "workspace_id FROM system.compute.warehouses WHERE "
                         "warehouse_id = '<id>'")
    args = ap.parse_args()

    dash = build(args.results_catalog, args.results_schema,
                 args.workspace_url, args.org_id)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(dash, fh, indent=2)
    n_widgets = sum(len(p["layout"]) for p in dash["pages"])
    print(f"Wrote {args.out}")
    print(f"  {len(dash['datasets'])} datasets, {len(dash['pages'])} pages, {n_widgets} widgets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
