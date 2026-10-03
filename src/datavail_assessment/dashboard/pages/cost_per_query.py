"""The Cost per Query page, mirrored from another repository.

Unlike every other page here, this one is not generated. It is lifted
verbatim from a dashboard maintained in a fork of
databrickslabs/sandbox, fetched into resources/external by
scripts/fetch_external.py. Its datasets and widgets are returned as
they are found.

Embedded rather than ported on purpose. Porting 24 widgets and 12
parameters into Python would make this page ours to maintain, and the
whole reason it lives in another repository is that it is not. The cost
is that the builder cannot restyle it - it will not match the alignment
and wording conventions the conformance pages follow.

Reads the dbsql_cost_per_query materialized view that the
cost_per_query_mv job creates. Which catalog and schema that is comes
from scripts/fetch_external.py, which retargets BOTH this dashboard and
the DDL as it mirrors them - so they cannot disagree. Without the view
the page renders errors rather than appearing empty, so run the job
before pointing anyone at the page.

The page carries 12 parameters - warehouse, date range, top-N, a
discount rate - so it behaves like a tool you drive, where the other
pages are read-only. Lakeview scopes parameter widgets to their page,
so this does not leak into Adoption or Conformance.
"""

from __future__ import annotations

import json
import os

from datavail_assessment.core.paths import external_dir

PAGE_NAME = "cost_per_query"
PAGE_TITLE = "Cost per Query"

SOURCE_FILE = "DBSQL Cost Dashboard (PrPr).lvdash.json"


def _source() -> dict:
    path = os.path.join(external_dir(), SOURCE_FILE)
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} is missing. It is gitignored because it mirrors another "
            "repository - run `python scripts/fetch_external.py` first.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _page(src: dict) -> dict:
    """The one page the source dashboard defines."""
    pages = src.get("pages") or []
    if len(pages) != 1:
        raise SystemExit(
            f"{SOURCE_FILE} has {len(pages)} pages; this module assumes one. "
            "The mirrored dashboard changed shape - pick a page explicitly.")
    return pages[0]


def datasets(catalog: str, schema: str,
             link_base: str = "", org_id: str = "") -> list[dict]:
    """Every dataset the source defines, verbatim.

    catalog and schema are ignored: this page reads the cost MV, not the
    assessment results, so it has nothing to parameterise. The arguments
    exist to satisfy the page protocol.
    """
    return list(_source().get("datasets") or [])


def layout() -> list[dict]:
    return list(_page(_source()).get("layout") or [])
