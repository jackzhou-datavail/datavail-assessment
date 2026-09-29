"""Conformance assessment entry point.

Scores a workspace against the pattern library. One script, two ways to
execute it:

    # from a laptop - SQL warehouse, no cluster, no pyspark
    python -m datavail_assessment.conformance.run --profile uc-semantics --warehouse-id <id>

    # inside a workspace job - Spark on serverless
    python -m datavail_assessment.conformance.run --spark

Add --dry-run to run every check and print the result without creating
the results catalog or writing any row.
"""

from __future__ import annotations

import argparse
import os

from datavail_assessment.conformance import checks
from datavail_assessment.conformance.registry import load_registry
from datavail_assessment.core import runner
from datavail_assessment.core.paths import package_file, patterns_dir

# registry.yaml ships inside the package; patterns/ is repo data that the
# job syncs alongside it. Neither path uses __file__ directly:
# spark_python_task on serverless exec()s the entry file with no __file__
# defined, and that NameError is fatal at import time.
DEFAULT_REGISTRY = package_file("conformance", "registry.yaml")
DEFAULT_PATTERNS = patterns_dir()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run the conformance assessment")
    ap.add_argument("--spark", action="store_true",
                    help="Execute through Spark (for a workspace job) instead of a SQL warehouse")
    ap.add_argument("--profile", help="CLI profile; required unless --spark")
    ap.add_argument("--warehouse-id", help="SQL warehouse id; required unless --spark")
    ap.add_argument("--results-catalog",
                    default=os.environ.get("ASSESSMENT_RESULTS_CATALOG", "assessment"),
                    help="Dedicated catalog for output. Created if absent and always excluded "
                         "from assessment scope. Env: ASSESSMENT_RESULTS_CATALOG")
    ap.add_argument("--results-schema",
                    default=os.environ.get("ASSESSMENT_RESULTS_SCHEMA", "results"),
                    help="Schema within the results catalog. Env: ASSESSMENT_RESULTS_SCHEMA")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--patterns-dir", default=DEFAULT_PATTERNS)
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--exclude-catalog", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.results_catalog in runner.ALWAYS_EXCLUDED:
        ap.error(f"--results-catalog cannot be '{args.results_catalog}'. Use a dedicated catalog.")

    if args.spark:
        from datavail_assessment.core.spark import SparkExecutor
        executor = SparkExecutor()
        notes = "job run (spark)"
    else:
        if not args.profile or not args.warehouse_id:
            ap.error("--profile and --warehouse-id are required unless --spark is given")
        from datavail_assessment.core.warehouse import WarehouseExecutor
        executor = WarehouseExecutor(args.profile, args.warehouse_id, args.verbose)
        notes = f"run via SQL warehouse {args.warehouse_id}"

    patterns, version, checksum = load_registry(args.registry, args.patterns_dir)
    print(f"registry={version} sha={checksum[:10]} patterns={len(patterns)}")

    meta = {"registry_version": version, "registry_checksum": checksum, "notes": notes}
    meta.update(executor.context())
    return runner.execute(executor, patterns, checks, args, meta)


if __name__ == "__main__":
    # Do NOT `raise SystemExit(main())` unconditionally. spark_python_task
    # on serverless compute exec()s this file inside an IPython kernel,
    # where even SystemExit(0) is surfaced as a workload failure - the
    # collector completes, writes its results, and the task still reports
    # RUN_EXECUTION_ERROR. Return normally on success; signal only on failure.
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
