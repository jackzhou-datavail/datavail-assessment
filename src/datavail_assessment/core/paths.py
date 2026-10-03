"""Locating files that ship with the package, and repo data beside it.

Deliberately avoids `__file__` on the entry script. `spark_python_task`
on serverless compute exec()s the file it is given without defining
`__file__`, so any module-level `os.path.abspath(__file__)` in that file
raises NameError before the job starts. Resolving through an imported
module is safe, because imported modules always have `__file__`.
"""

from __future__ import annotations

import os

import datavail_assessment

PACKAGE_ROOT = os.path.dirname(os.path.abspath(datavail_assessment.__file__))


def package_file(*parts: str) -> str:
    """Absolute path to a data file shipped inside the package."""
    return os.path.join(PACKAGE_ROOT, *parts)


def patterns_dir() -> str:
    """Absolute path to the pattern library.

    The library is repo data, not package data: it is prose that people
    edit, and the registry reads titles from it at load time. Resolution
    order:

      1. ASSESSMENT_PATTERNS_DIR, if set - how a job points at the
         directory the bundle synced
      2. patterns/ beside an installed package (src layout: the repo
         root is two levels above the package)
      3. patterns/ under the current working directory
    """
    env = os.environ.get("ASSESSMENT_PATTERNS_DIR")
    if env:
        return env

    # src/<package>/  ->  repo root is two directories up
    repo_root = os.path.dirname(os.path.dirname(PACKAGE_ROOT))
    candidate = os.path.join(repo_root, "patterns")
    if os.path.isdir(candidate):
        return candidate

    return os.path.join(os.getcwd(), "patterns")


def external_dir() -> str:
    """Absolute path to resources/external.

    Mirrored assets from another repository, fetched by
    scripts/fetch_external.py and excluded by .gitignore. Same
    resolution order and the same reasoning as patterns_dir(): repo
    data, not package data, so it cannot be found relative to the
    installed package alone.

      1. ASSESSMENT_EXTERNAL_DIR, if set
      2. resources/external beside an installed package
      3. resources/external under the current working directory
    """
    env = os.environ.get("ASSESSMENT_EXTERNAL_DIR")
    if env:
        return env

    repo_root = os.path.dirname(os.path.dirname(PACKAGE_ROOT))
    candidate = os.path.join(repo_root, "resources", "external")
    if os.path.isdir(candidate):
        return candidate

    return os.path.join(os.getcwd(), "resources", "external")
