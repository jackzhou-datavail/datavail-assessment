"""Weighted scoring, and the coverage that qualifies it.

Scores are the weighted mean over MEASURED items only. Coverage is
measured weight over applicable weight, so a high score computed from
thin evidence is always visible as such rather than mistaken for a
clean bill of health.
"""

from __future__ import annotations

from .model import ERROR, MEASURED, NOT_APPLICABLE, NOT_AVAILABLE, POOR, Outcome, Scorable

def applicable(item: Scorable, facts: dict[str, bool]) -> bool:
    """Whether a pattern is in scope given what exists in the workspace."""
    rule = item.applicability
    if rule == "ALWAYS":
        return True
    return bool(facts.get(rule, False))


def score(items: list[Scorable], outcomes: dict[str, Outcome], facts: dict[str, bool]):
    """Compute per-category and overall scores.

    Scores are the weighted mean conformance over MEASURED checks only.
    Coverage is measured weight over applicable weight, so a high score
    on thin evidence is always visible as such.
    """
    by_cat: dict[str, dict[str, float]] = {}
    tot_app = tot_meas = tot_weighted = 0.0
    n = {MEASURED: 0, NOT_AVAILABLE: 0, NOT_APPLICABLE: 0, ERROR: 0}
    critical_gaps = 0

    for p in items:
        out = outcomes.get(p.id)
        cat = by_cat.setdefault(
            p.category,
            {"w_app": 0.0, "w_meas": 0.0, "weighted": 0.0,
             MEASURED: 0.0, NOT_AVAILABLE: 0.0, NOT_APPLICABLE: 0.0, ERROR: 0.0, "poor": 0.0},
        )
        if not applicable(p, facts):
            cat[NOT_APPLICABLE] += 1
            n[NOT_APPLICABLE] += 1
            continue
        cat["w_app"] += p.weight
        tot_app += p.weight
        if out is None or out.status != MEASURED:
            status = out.status if out else NOT_AVAILABLE
            cat[status] += 1
            n[status] += 1
            continue
        cat[MEASURED] += 1
        n[MEASURED] += 1
        cat["w_meas"] += p.weight
        cat["weighted"] += p.weight * (out.conformance_pct or 0.0)
        tot_meas += p.weight
        tot_weighted += p.weight * (out.conformance_pct or 0.0)
        if out.grade(p) == POOR:
            cat["poor"] += 1
            if p.severity == "CRITICAL":
                critical_gaps += 1

    cats = []
    for name, c in sorted(by_cat.items()):
        cats.append(
            {
                "category": name,
                "weighted_score": round(c["weighted"] / c["w_meas"], 2) if c["w_meas"] else None,
                "coverage_pct": round(100.0 * c["w_meas"] / c["w_app"], 2) if c["w_app"] else 0.0,
                "weight_applicable": c["w_app"],
                "weight_measured": c["w_meas"],
                "n_measured": int(c[MEASURED]),
                "n_not_available": int(c[NOT_AVAILABLE]),
                "n_not_applicable": int(c[NOT_APPLICABLE]),
                "n_error": int(c[ERROR]),
                "n_poor": int(c["poor"]),
            }
        )

    coverage = round(100.0 * tot_meas / tot_app, 2) if tot_app else 0.0
    confidence = "HIGH" if coverage >= 70 else "MEDIUM" if coverage >= 40 else "LOW"
    overall = {
        "overall_score": round(tot_weighted / tot_meas, 2) if tot_meas else None,
        "coverage_pct": coverage,
        "confidence": confidence,
        "weight_applicable": tot_app,
        "weight_measured": tot_meas,
        "n_patterns": len(items),
        "n_measured": n[MEASURED],
        "n_not_available": n[NOT_AVAILABLE],
        "n_not_applicable": n[NOT_APPLICABLE],
        "n_error": n[ERROR],
        "critical_gaps": critical_gaps,
    }
    return cats, overall
