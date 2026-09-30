"""The pattern registry: scoring metadata for the pattern library.

Pattern-specific, so it lives here rather than in core. Titles and
anti-pattern flags are read from the markdown at load time, so the
registry can never drift from the documents it scores.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any

# Pattern areas (the patterns/ subdirectories) roll up to the same six
# reporting categories the adoption assessment uses, so a reader compares
# like with like across the two dashboards. Derived from
# adoption_checks/pattern-checkmap.md; the names match
# adoption.checks.SECTIONS exactly.
AREA_TO_CATEGORY = {
    "data-ingestion":            "Data Engineering",
    "data-sharing":              "Data Sharing",
    "ml-ai-lifecycle":           "AI/ML",
    "orchestration-reliability": "Data Engineering",
    "platform-onboarding":       "Workspace",
    "security-compliance":       "Governance & Security",
    "sql-analytics":             "SQL",
    "table-optimization":        "Data Engineering",
    "unity-catalog-governance":  "Governance & Security",
}

# platform-onboarding is the one mixed area. These four are identity and
# access patterns, so they report under governance rather than workspace
# setup - the only file-level exceptions in the checkmap.
_GOVERNANCE_OVERRIDES = {
    "account-first-identity-federation",
    "service-principals-for-automation",
    "personal-identity-in-production",
    "workspace-object-permissions",
}


def report_category(pattern_id: str, area: str) -> str:
    """The reporting category for a pattern. Falls back to the area so an
    area added to patterns/ but not to the map is visible rather than
    silently folded into something else."""
    if pattern_id in _GOVERNANCE_OVERRIDES:
        return "Governance & Security"
    return AREA_TO_CATEGORY.get(area, area)


@dataclass
class Pattern:
    """One registry entry, joined to its markdown document."""

    id: str
    area: str          # patterns/ subdirectory; resolves the markdown path
    category: str      # reporting category, shared with adoption
    severity: str
    tier: str
    implemented: bool
    target_pct: float
    floor_pct: float
    applicability: str
    root_cause: str
    weight: float
    title: str = ""
    is_anti_pattern: bool = False
    doc_path: str = ""


_FLOW = re.compile(r"^\s*-\s*\{(?P<body>.+)\}\s*$")
_SCALAR = re.compile(r"^\s*(?P<key>[A-Za-z_]+)\s*:\s*(?P<val>.+?)\s*$")


def _parse_registry_text(text: str) -> dict[str, Any]:
    """Minimal parser for registry.yaml's restricted subset of YAML."""
    out: dict[str, Any] = {"patterns": [], "severity_weights": {}, "confidence_thresholds": {}}
    section = None
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "-", "\t")):
            section = line.split(":", 1)[0].strip()
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if section == "version" and rest:
                out["version"] = rest.strip('"')
            continue
        flow = _FLOW.match(line)
        if flow:
            rec: dict[str, Any] = {}
            for part in flow.group("body").split(","):
                if ":" not in part:
                    continue
                k, v = part.split(":", 1)
                rec[k.strip()] = v.strip()
            out["patterns"].append(rec)
            continue
        scalar = _SCALAR.match(line)
        if scalar and section in ("severity_weights", "confidence_thresholds"):
            out[section][scalar.group("key")] = float(scalar.group("val"))
    return out


def _load_yaml(path: str) -> dict[str, Any]:
    text = open(path, encoding="utf-8").read()
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        return _parse_registry_text(text)


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "yes", "1")


def load_registry(registry_path: str, patterns_dir: str) -> tuple[list[Pattern], str, str]:
    """Return (patterns, version, checksum).

    Title and anti-pattern flag are read from the markdown so the
    registry can never drift from the documents it scores.
    """
    raw = _load_yaml(registry_path)
    weights = {k: float(v) for k, v in raw.get("severity_weights", {}).items()}
    checksum = hashlib.sha256(
        open(registry_path, "rb").read()
    ).hexdigest()

    patterns: list[Pattern] = []
    missing: list[str] = []
    for rec in raw["patterns"]:
        area = rec["cat"]
        doc_rel = os.path.join(area, f"{rec['id']}.md")
        doc_abs = os.path.join(patterns_dir, doc_rel)
        title, is_anti = rec["id"], False
        if not os.path.exists(doc_abs):
            missing.append(f"{rec['id']} (expected {doc_rel.replace(os.sep, '/')})")
        else:
            body = open(doc_abs, encoding="utf-8").read()
            first = body.splitlines()[0] if body else ""
            title = first.lstrip("# ").strip() or rec["id"]
            is_anti = "ANTI-PATTERN" in body
        patterns.append(
            Pattern(
                id=rec["id"],
                area=area,
                category=report_category(rec["id"], area),
                severity=rec["sev"],
                tier=rec["tier"],
                implemented=_as_bool(rec["impl"]),
                target_pct=float(rec["target"]),
                floor_pct=float(rec["floor"]),
                applicability=rec["applies"],
                root_cause=rec["cause"],
                weight=weights.get(rec["sev"], 1.0),
                title=title,
                is_anti_pattern=is_anti,
                doc_path=f"patterns/{doc_rel.replace(os.sep, '/')}",
            )
        )

    # A registry id IS the markdown filename stem, so a missing document
    # means the two have drifted. Without this the entry would load with
    # its id as the title and a dead doc_path - a typo that scores
    # normally and shows up only as an odd-looking row on the dashboard.
    #
    # Only raise when SOME documents resolved: none resolving means
    # patterns_dir is wrong or was not synced, which is a different
    # problem and already obvious from every title being an id.
    if missing and len(missing) < len(patterns):
        raise ValueError(
            "%d registry %s no pattern document: %s"
            % (len(missing), "entry has" if len(missing) == 1 else "entries have",
               "; ".join(missing)))

    return patterns, str(raw.get("version", "unknown")), checksum
