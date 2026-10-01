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

    Three outcomes, deliberately not two:

    MEASURED        produced a number; counts in both numerator and
                    denominator.
    NOT_AVAILABLE   relevant here, but we could not look - no collector,
                    no account access, a system table missing a column.
                    Denominator only, which is what drags coverage down
                    and is the honest signal.
    NOT_APPLICABLE  nothing in scope to judge - the workspace does not
                    share data, has no clusters, has no table large
                    enough for compaction to matter. Excluded from both,
                    because a pattern with nothing to apply to is not a
                    gap in our measurement.

    Every pattern in the library came from Databricks' own guidance, so
    NOT_APPLICABLE never means the practice is irrelevant - only that
    this workspace currently has nothing it would govern.
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
        status = out.status if out else NOT_AVAILABLE

        # NOT_APPLICABLE leaves the denominator entirely, however it was
        # reached - whether the registry's `applies` rule ruled the
        # pattern out up front, or the check ran and found nothing in
        # scope. Both mean the same thing: there is nothing here that
        # could be right or wrong, so there is nothing we failed to see.
        #
        # This is NOT the same as a credential or capability limit. A
        # pattern we cannot look at - no account access, no collector
        # written, a system table missing a column - is NOT_AVAILABLE and
        # stays in the denominator, because the practice is relevant and
        # we simply did not measure it. Coverage exists to report exactly
        # that gap, so hiding it would defeat the number.
        if not applicable(p, facts) or status == NOT_APPLICABLE:
            cat[NOT_APPLICABLE] += 1
            n[NOT_APPLICABLE] += 1
            continue
        cat["w_app"] += p.weight
        tot_app += p.weight
        if out is None or out.status != MEASURED:
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
