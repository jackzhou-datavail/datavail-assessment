"""Mirror the cost-per-query assets from another repository.

The materialized view and its dashboard are maintained in a fork of
databrickslabs/sandbox, not here. Vendoring them would make this repo
their owner - edits would drift from upstream and nobody would know
which copy is authoritative. So they are fetched into
`resources/external/`, which .gitignore excludes.

Run before `databricks bundle deploy`. The bundle cannot do this
itself: DAB has no primitive for reading another repository, and a
dashboard resource's `file_path` must resolve inside the bundle.

Pinned to a COMMIT rather than the branch. A branch follows whatever
someone force-pushes; a commit is what we tested against. Bump REF
deliberately when picking up a change.

NOT byte-identical to upstream: both files hardcode
`main.default.dbsql_cost_per_query`, and the view is retargeted here as
the files are written. Doing it at fetch time rather than by editing
afterwards means a re-fetch cannot silently restore main.default and
leave the dashboard reading a view the job never created.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request

REPO = "jackzhou/sandbox_jz_fork"
BRANCH = "alert_source_type_fix"
# Head of BRANCH as of 2026-10-02. Bump to pick up a newer change.
REF = "b14889259882886485b1f66a5cc1230f44ee9401"
SRC_DIR = "dbsql/cost_per_query/PrPr"

# Where the materialized view should live. Upstream hardcodes
# main.default; both files are rewritten to this on the way in, so the
# job and the dashboard cannot disagree about where it is.
#
# No default on purpose. databricks.yml passes --catalog/--schema from
# bundle variables, and the one time this script defaulted to upstream's
# main.default it silently reverted a deliberate retarget - the deploy
# then shipped a DDL pointing at a catalog that does not exist here.
# A bare run has to say where the view goes.
TARGET_CATALOG = os.environ.get("ASSESSMENT_COST_CATALOG")
TARGET_SCHEMA = os.environ.get("ASSESSMENT_COST_SCHEMA")

UPSTREAM_VIEW = "main.default.dbsql_cost_per_query"
VIEW_NAME = "dbsql_cost_per_query"

# Original names kept verbatim: this is a mirror, and matching the source
# makes "is this current?" answerable by eye. Spaces and parentheses are
# awkward on a command line but fine in a path.
FILES = [
    "DBSQL Cost Per Query MV (PrPr).sql",
    "DBSQL Cost Dashboard (PrPr).lvdash.json",
]

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(HERE), "resources", "external")


def raw_url(ref: str, name: str) -> str:
    from urllib.parse import quote
    return (f"https://raw.githubusercontent.com/{REPO}/{ref}/"
            f"{quote(SRC_DIR)}/{quote(name)}")


def retarget(text: str, name: str, catalog: str, schema: str) -> str:
    """Point the view at the configured catalog and schema.

    Asserts the upstream name is present rather than substituting
    best-effort. If upstream renames the view, a silent no-op would
    create it in main.default while the dashboard read somewhere else -
    the two files have to move together or not at all.
    """
    target = f"{catalog}.{schema}.{VIEW_NAME}"
    if target == UPSTREAM_VIEW:
        return text
    n = text.count(UPSTREAM_VIEW)
    if n != 1:
        raise SystemExit(
            f"{name}: expected exactly one reference to {UPSTREAM_VIEW}, "
            f"found {n}. Upstream changed shape - check before retargeting.")
    return text.replace(UPSTREAM_VIEW, target)


def fetch(ref: str, dest: str, catalog: str, schema: str,
          verbose: bool = True) -> int:
    os.makedirs(dest, exist_ok=True)
    for name in FILES:
        url = raw_url(ref, name)
        out = os.path.join(dest, name)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                body = r.read()
        except urllib.error.HTTPError as exc:
            print(f"  {name}: HTTP {exc.code} - is REF still reachable?",
                  file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"  {name}: {exc.reason}", file=sys.stderr)
            return 1
        if not body:
            print(f"  {name}: empty response", file=sys.stderr)
            return 1
        text = retarget(body.decode("utf-8"), name, catalog, schema)
        with open(out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        if verbose:
            print(f"  {name}  ({len(body) / 1024:.1f} KB)")
    if verbose:
        print(f"  view retargeted to {catalog}.{schema}.{VIEW_NAME}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ref", default=REF,
                    help=f"commit, tag or branch (default: pinned {REF[:10]})")
    ap.add_argument("--dest", default=DEST)
    ap.add_argument("--catalog", default=TARGET_CATALOG,
                    help="catalog for the materialized view; required unless "
                         "ASSESSMENT_COST_CATALOG is set")
    ap.add_argument("--schema", default=TARGET_SCHEMA,
                    help="schema for the materialized view; required unless "
                         "ASSESSMENT_COST_SCHEMA is set")
    args = ap.parse_args(argv)

    if not args.catalog or not args.schema:
        ap.error("--catalog and --schema are required (or set "
                 "ASSESSMENT_COST_CATALOG / ASSESSMENT_COST_SCHEMA). There is "
                 "no default: falling back to upstream's main.default would "
                 "point the view at a catalog that may not exist.")

    print(f"Fetching from {REPO}@{args.ref[:10]} ({BRANCH})")
    rc = fetch(args.ref, args.dest, args.catalog, args.schema)
    if rc == 0:
        print(f"Into {args.dest}")
    return rc


if __name__ == "__main__":
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
