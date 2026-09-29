"""Generate the Datavail Assessment dashboard.

One dashboard, many pages - each page answering a different question
about the workspace. Today there is one page, Adoption. Adding another
is adding a module under pages/ and one line to PAGES.

    python -m datavail_assessment.dashboard.build --results-catalog assessment

Writes datavail_assessment.lvdash.json beside this file, which the
bundle deploys as resources.dashboards.datavail_assessment. Because the
bundle owns it, edit this generator rather than the dashboard in the UI:
a UI edit makes the next `bundle deploy` fail rather than silently lose
the change, and recovering means either `bundle generate` or --force.
"""

from __future__ import annotations

import argparse
import json
import os

from .pages import adoption, conformance

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "datavail_assessment.lvdash.json")

# Page order is display order. Each module supplies datasets() and layout().
PAGES = [adoption, conformance]


def build(catalog: str, schema: str) -> dict:
    datasets, pages = [], []
    for page in PAGES:
        datasets.extend(page.datasets(catalog, schema))
        pages.append({"name": page.PAGE_NAME,
                      "displayName": page.PAGE_TITLE,
                      "layout": page.layout()})
    return {"datasets": datasets, "pages": pages,
            "uiSettings": {"theme": {"widgetHeaderAlignment": "LEFT"}}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the Datavail Assessment dashboard")
    ap.add_argument("--results-catalog",
                    default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"))
    ap.add_argument("--results-schema",
                    default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"))
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    dash = build(args.results_catalog, args.results_schema)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(dash, fh, indent=2)

    widgets = sum(len(p["layout"]) for p in dash["pages"])
    print(f"Wrote {args.out}")
    print(f"  {len(dash['pages'])} page(s): {', '.join(p['displayName'] for p in dash['pages'])}")
    print(f"  {len(dash['datasets'])} datasets, {widgets} widgets")
    return 0


if __name__ == "__main__":
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
