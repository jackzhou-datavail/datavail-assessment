"""The Adoption page.

Answers one question: which parts of the Databricks platform does this
workspace actually use? Not how well it uses them - that is a separate
question, and will be a separate page.

Reads what `datavail_assessment.adoption.run` writes:
  adoption_section_score   per-section rollup, plus one OVERALL row
  adoption_check_history   one row per check per run
"""

from __future__ import annotations

from ..widgets import (ADOPTION_LABEL_COLORS, ADOPTION_SECTION_COLORS,
                       bar, counter, dataset, pie, table, text)

PAGE_NAME = "adoption"
PAGE_TITLE = "Adoption"


def _latest(base: str) -> str:
    """The most recent adoption run, whichever job or laptop produced it."""
    return (f"(SELECT run_id FROM {base}.adoption_section_score "
            f"ORDER BY run_ts DESC LIMIT 1)")


def datasets(catalog: str, schema: str) -> list[dict]:
    base = f"{catalog}.{schema}"
    run = _latest(base)
    return [
        dataset("adopt_overall", "Adoption Overall", f"""
SELECT
  score_pct        AS overall_pct,
  grade            AS overall_grade,
  points,
  max_points,
  active_count,
  minimal_count,
  none_count,
  not_measurable_count,
  coverage_pct,
  run_ts
FROM {base}.adoption_section_score
WHERE run_id = {run} AND section = 'OVERALL'
"""),

        dataset("adopt_sections", "Adoption by Section", f"""
SELECT
  section,
  score_pct,
  grade,
  points,
  max_points,
  active_count,
  minimal_count,
  none_count,
  not_measurable_count,
  coverage_pct,
  weight
FROM {base}.adoption_section_score
WHERE run_id = {run} AND section <> 'OVERALL'
"""),

        dataset("adopt_checks", "Adoption Checks", f"""
SELECT
  section,
  check_id,
  check_name,
  label,
  score,
  raw_value,
  COALESCE(detail, '') AS detail,
  CASE WHEN measurable = FALSE THEN 'not observable'
       WHEN error IS NOT NULL THEN 'query failed'
       ELSE 'measured' END AS measurable
FROM {base}.adoption_check_history
WHERE run_id = {run}
ORDER BY check_id
"""),

        dataset("adopt_label_mix", "Check Mix by Section", f"""
SELECT section, label, COUNT(*) AS n_checks
FROM {base}.adoption_check_history
WHERE run_id = {run}
GROUP BY section, label
"""),

        dataset("adopt_gaps", "Unused Capabilities", f"""
SELECT
  section,
  check_id,
  check_name,
  raw_value,
  COALESCE(error, '') AS error
FROM {base}.adoption_check_history
WHERE run_id = {run} AND score = 0 AND measurable = TRUE
ORDER BY section, check_id
"""),
    ]


def layout() -> list[dict]:
    return [
        text("adopt_title", [
            "# Adoption",
            "",
            "Which parts of the Databricks platform this workspace actually uses. "
            "Each check scores **ACTIVE** (in real use), **MINIMAL** (present, "
            "barely used) or **NONE** (no evidence).",
            "",
            "This is breadth, not quality. A workspace can use a capability heavily and "
            "use it badly — that is a different question, and a different page.",
        ], 0, 0, 6, 5),
        counter("adopt_kpi_pct", "adopt_overall", "overall_pct", "Adoption Score",
                "Section percentages, weighted by section", 6, 0, 3, 5),
        counter("adopt_kpi_grade", "adopt_overall", "overall_grade", "Adoption Level",
                "NOT ADOPTED / EARLY STAGE / PARTIALLY / BROADLY / FULLY LEVERAGED",
                9, 0, 3, 5),
        counter("adopt_kpi_active", "adopt_overall", "active_count", "Capabilities Active",
                "Checks scoring 2 — in real use", 0, 5, 4, 3),
        counter("adopt_kpi_minimal", "adopt_overall", "minimal_count", "Barely Used",
                "Checks scoring 1 — present but minimal", 4, 5, 4, 3),
        counter("adopt_kpi_none", "adopt_overall", "none_count", "Unused",
                "Checks scoring 0 — no evidence of use", 8, 5, 2, 3),
        counter("adopt_kpi_coverage", "adopt_overall", "coverage_pct", "Measurable",
                "Share of the checklist observable from system tables. The score "
                "is computed over these only.", 10, 5, 2, 3),

        bar("adopt_section_bars", "adopt_sections", "score_pct", "section",
            "Adoption by Section",
            "Percentage of available points per platform area, coloured by grade.",
            0, 8, 7, 7, colorf="grade", mappings=ADOPTION_SECTION_COLORS),
        pie("adopt_mix_pie", "adopt_label_mix", "label", "n_checks",
            ADOPTION_LABEL_COLORS, "Check Mix",
            "How every check resolved across all six sections.", 7, 8, 5, 7),

        table("adopt_section_table", "adopt_sections",
              [("section", "Section"), ("grade", "Grade"), ("score_pct", "Score %"),
               ("points", "Points"), ("max_points", "Max"),
               ("active_count", "Active"), ("minimal_count", "Minimal"),
               ("none_count", "Unused"),
               ("not_measurable_count", "Not Observable"),
               ("coverage_pct", "Measurable %"), ("weight", "Weight")],
              "Section Scorecard",
              "Weight is each section's share of the overall score.",
              0, 15, 12, 6),

        table("adopt_gaps_table", "adopt_gaps",
              [("section", "Section"), ("check_id", "#"), ("check_name", "Capability"),
               ("raw_value", "Measured"), ("error", "Not Measurable Because")],
              "Unused Capabilities",
              "Every check scoring NONE — the platform surface not being used. "
              "Checks that could not be observed at all are excluded here and from "
              "the score; they appear in All Checks as 'not observable'.",
              0, 21, 12, 9),

        table("adopt_checks_table", "adopt_checks",
              [("section", "Section"), ("check_id", "#"), ("check_name", "Capability"),
               ("label", "Level"), ("raw_value", "Measured"), ("detail", "Detail"),
               ("measurable", "Status")],
              "All Checks",
              "Every check, with the value behind each score.",
              0, 30, 12, 11),
    ]
