"""The Conformance pages, lifted from the standalone conformance dashboard.

Two pages - the scorecard and the findings - selected from the builder in
`datavail_assessment.conformance.dashboard`. That builder stays the single
definition of what a conformance page looks like; this module chooses
which of its pages to surface and relabels them. Rebuilding the same
widgets by hand would guarantee the two drift apart.

Its third page, Coverage & Blind Spots, is deliberately left out. It
explains why checks could not run - missing collectors, sources the
platform does not expose - which is a conversation about the assessment
rather than about the workspace, and it stays on the standalone
dashboard.

This replaces the placeholder that stood here while conformance was
reworked. The placeholder existed to decouple the two dashboards during
that work; now that conformance has settled, sharing one definition is
worth more than the independence.
"""

from __future__ import annotations

from datavail_assessment.conformance.dashboard import build as source


class _Page:
    """One page of the source dashboard, presented as a page module.

    `dashboard.build` iterates PAGES and asks each entry for PAGE_NAME,
    PAGE_TITLE, datasets() and layout(). A module can only supply one of
    each, so two pages from one source need two objects, not two modules.
    """

    def __init__(self, index: int, name: str, title: str):
        self.index = index
        self.PAGE_NAME = name
        self.PAGE_TITLE = title

    def datasets(self, catalog: str, schema: str,
                 link_base: str = "", org_id: str = "") -> list[dict]:
        """Only the datasets this page references.

        The source builds datasets for all three of its pages; carrying
        the unused ones would make the combined dashboard run queries
        nothing displays.
        """
        built = source.build(catalog, schema, link_base, org_id)
        page = built["pages"][self.index]
        used = {q["query"]["datasetName"]
                for w in page["layout"]
                for q in w["widget"].get("queries", [])}
        return [ds for ds in built["datasets"] if ds["name"] in used]

    def layout(self) -> list[dict]:
        """Widget layout carries no catalog or schema, so placeholders are
        fine - only datasets() needs the real ones."""
        return source.build("c", "s")["pages"][self.index]["layout"]


# Index into the source dashboard's pages: 0 scorecard, 1 findings,
# 2 coverage (not surfaced here).
SCORECARD = _Page(0, "conformance_scorecard", "Conformance: Scorecard")
FINDINGS = _Page(1, "conformance_findings", "Conformance: Findings")
