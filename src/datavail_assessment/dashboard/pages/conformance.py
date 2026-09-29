"""The Conformance page.

Answers the question the Adoption page deliberately does not: of the
things this workspace does, how well does it do them? Adoption measures
breadth; conformance measures quality, and its findings are the evidence
behind a score.

The page is lifted wholesale from the standalone conformance dashboard
rather than rewritten - same datasets, same widgets, same layout - so
the two cannot drift apart. That dashboard's builder stays the single
definition; this module selects one of its pages and re-labels it.

Reads what `datavail_assessment.conformance.run` writes: the six result
tables and the v_latest_report view.
"""

from __future__ import annotations

from datavail_assessment.conformance.dashboard import build as source

# Which page of the standalone dashboard to surface here.
#   0  Onboarding Scorecard   - score, coverage, per-category grades
#   1  Findings               - remediation list and object-level evidence
#   2  Coverage & Blind Spots - what could not be measured, and why
SOURCE_PAGE = 0

PAGE_NAME = "conformance"
PAGE_TITLE = "Conformance"


def _page(catalog: str = "c", schema: str = "s") -> dict:
    """The source page. Widget layout carries no catalog or schema, so
    placeholders are fine when only the layout is wanted."""
    return source.build(catalog, schema)["pages"][SOURCE_PAGE]


def datasets(catalog: str, schema: str) -> list[dict]:
    """Only the datasets this page actually references.

    The source dashboard defines datasets for all three of its pages;
    carrying the unused ones over would make the combined dashboard run
    queries nothing displays.
    """
    built = source.build(catalog, schema)
    page = built["pages"][SOURCE_PAGE]
    used = {q["query"]["datasetName"]
            for w in page["layout"]
            for q in w["widget"].get("queries", [])}
    return [ds for ds in built["datasets"] if ds["name"] in used]


def layout() -> list[dict]:
    return _page()["layout"]
