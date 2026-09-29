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

    `results` are rows carrying `section` and `score`. Returns
    (section_rows, overall_pct, overall_grade).
    """
    section_rows = []
    overall = 0.0

    for name, cfg in sections.items():
        rows = [r for r in results if r["section"] == name]
        points = sum(r["score"] for r in rows)
        pct = (points / cfg["max"] * 100) if cfg["max"] else 0.0
        overall += pct * cfg["weight"]
        section_rows.append({
            "section": name,
            "points": points,
            "max_points": cfg["max"],
            "score_pct": round(pct, 1),
            "grade": grade_section(pct),
            "active_count": sum(1 for r in rows if r["score"] == 2),
            "minimal_count": sum(1 for r in rows if r["score"] == 1),
            "none_count": sum(1 for r in rows if r["score"] == 0),
            "weight": cfg["weight"],
        })

    return section_rows, round(overall, 1), grade_overall(overall)
