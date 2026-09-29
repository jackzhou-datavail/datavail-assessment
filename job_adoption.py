"""Job entry point: adoption assessment.

The code itself lives in the datavail_assessment wheel, which the job
environment installs; this file only hands control to it. Keeping it to
an import and a call matters: spark_python_task exec()s this file without
defining __file__, so anything resolving its own location here would
raise NameError before the job starts.

Arguments come from the task's `parameters` list and are read by
argparse from sys.argv, exactly as on the command line.
"""

from datavail_assessment.adoption.run import main

# Deliberately not `raise SystemExit(main())`. On serverless compute this
# file is exec()d inside an IPython kernel where even SystemExit(0) is
# reported as a workload failure - the collector completes, writes its
# results, and the task still fails. Signal only on a non-zero result.
_rc = main()
if _rc:
    raise SystemExit(_rc)
