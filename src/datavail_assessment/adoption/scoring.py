"""Adoption scoring: ordinal per check, weighted by section.

Deliberately not `core.scoring`. Conformance asks "what share of these
objects follow the practice" and produces a percentage per item.
Adoption asks "is this capability used at all" and produces an ordinal:

    2  ACTIVE    in real use
    1  MINIMAL   present, barely used
    0  NONE      no evidence

A section's percentage is its points over its maximum (two per check),
and the overall score weights sections rather than individual checks -
a workspace can be strong in SQL and absent in ML, and the weights say
how much each matters to the overall picture.
"""

from __future__ import annotations

LABELS = {0: "NONE", 1: "MINIMAL", 2: "ACTIVE"}

# A check whose capability cannot be observed from the data available.
# Distinct from NONE: "we cannot see it" is not "they do not use it", and
# scoring it as unused would understate adoption for a reason that has
# nothing to do with the workspace.
NOT_MEASURABLE = "NOT MEASURABLE"


def score_thresholds(value: float, minimal: float, active: float) -> int:
    """Two thresholds to an ordinal. Ties score upward."""
    if value >= active:
        return 2
    if value >= minimal:
        return 1
    return 0


def grade_section(pct: float) -> str:
    if pct >= 75:
        return "STRONG"
    if pct >= 40:
        return "DEVELOPING"
    if pct >= 10:
        return "EARLY"
    return "NOT ADOPTED"


def grade_overall(pct: float) -> str:
    if pct >= 80:
        return "FULLY LEVERAGED"
    if pct >= 60:
        return "BROADLY ADOPTED"
    if pct >= 35:
        return "PARTIALLY ADOPTED"
    if pct >= 10:
        return "EARLY STAGE"
    return "NOT ADOPTED"


def roll_up(results: list[dict], sections: dict[str, dict]):
    """Per-section rollup and the weighted overall score.

    Only measurable checks count. Each contributes two points to the
    denominator, so a section where a capability could not be observed
    is scored out of what was actually looked at, and `coverage_pct`
    says how much of the section that was. Scoring an unmeasurable
    check as zero would blame the workspace for a gap in the tooling.

    `results` are rows carrying `section`, `score` and `measurable`.
    Returns (section_rows, overall_pct, overall_grade).
    """
    section_rows = []
    overall = 0.0

    for name, cfg in sections.items():
        rows = [r for r in results if r["section"] == name]
        scored = [r for r in rows if r.get("measurable", True)]
        max_points = len(scored) * 2
        points = sum(r["score"] for r in scored)
        pct = (points / max_points * 100) if max_points else 0.0
        overall += pct * cfg["weight"]
        section_rows.append({
            "section": name,
            "points": points,
            "max_points": max_points,
            "score_pct": round(pct, 1),
            "grade": grade_section(pct) if max_points else "NOT MEASURED",
            "active_count": sum(1 for r in scored if r["score"] == 2),
            "minimal_count": sum(1 for r in scored if r["score"] == 1),
            "none_count": sum(1 for r in scored if r["score"] == 0),
            "not_measurable_count": len(rows) - len(scored),
            "coverage_pct": round(100.0 * len(scored) / len(rows), 1) if rows else 0.0,
            "weight": cfg["weight"],
        })

    return section_rows, round(overall, 1), grade_overall(overall)
