"""The Conformance page - a placeholder while it is redesigned.

Deliberately imports nothing from `datavail_assessment.conformance`. The
page previously lifted the scorecard out of that package's dashboard
builder, which meant any change to the conformance dashboard reached this
one too. Cutting the import makes the two independent: conformance can be
reworked freely without this dashboard moving under it.

The full three-page conformance view ships separately as the
**Conformance Assessment** dashboard, built by
`datavail_assessment.conformance.dashboard.build` and deployed by the same
bundle. Nothing was lost by blanking this page; this one links to it.

Restoring the embedded scorecard means putting back the import, a
SOURCE_PAGE index, and the dataset filter - see git history for this file.
"""

from __future__ import annotations

import os

from .. import widgets as w

PAGE_NAME = "conformance"
PAGE_TITLE = "Conformance"

# The bundle creates one dashboard per target, so this id identifies the
# DEV Conformance Assessment. Override when generating for another target:
#
#   CONFORMANCE_DASHBOARD_ID=<id> python -m datavail_assessment.dashboard.build
#
# Find it with:
#   databricks lakeview list -o json | jq -r \
#     '.[] | select(.display_name | endswith("Conformance Assessment"))
#          | "\(.dashboard_id)  \(.display_name)"'
CONFORMANCE_DASHBOARD_ID = os.environ.get(
    "CONFORMANCE_DASHBOARD_ID", "01f1bce06cec1e7b8007a4aa4976e1d2")

# Host-relative on purpose: the same JSON then works in any workspace, and
# only the id above is environment-specific.
CONFORMANCE_URL = f"/dashboardsv3/{CONFORMANCE_DASHBOARD_ID}/published"


def datasets(catalog: str, schema: str) -> list[dict]:
    """None. A text-only page runs no queries, so the dashboard should not
    carry datasets nothing reads."""
    return []


def layout() -> list[dict]:
    return [
        w.text("conformance_placeholder", [
            "# Conformance - under construction",
            "",
            "This page is being rebuilt and shows no data yet.",
            "",
            f"### [Open the Conformance Assessment dashboard]({CONFORMANCE_URL})",
            "",
            "Its three pages carry everything this one used to show, and more:",
            "",
            "- **Conformance: Scorecard** - overall score, coverage,"
            " per-category grades",
            "- **Conformance: Findings** - remediation backlog and"
            " object-level evidence",
            "- **Conformance: Coverage & Blind Spots** - what could not be"
            " measured, and why",
            "",
            "_Adoption, on the previous page, is unaffected - it is collected"
            " and scored independently._",
        ], 0, 0, 6, 10),
    ]
