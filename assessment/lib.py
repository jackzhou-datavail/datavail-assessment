"""Shared plumbing for the platform assessment collector.

Registry loading, preflight capability probing, result modelling, and
scoring. Deliberately dependency-light: PyYAML is used when present,
otherwise a small parser handles the flow-mapping style registry.yaml is
written in, so the registry can be validated off-cluster.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# --- statuses ---------------------------------------------------------

MEASURED = "MEASURED"
NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
ERROR = "ERROR"

GOOD, FAIR, POOR = "GOOD", "FAIR", "POOR"

# Why a whole tier cannot be measured by a SQL-only collector. These
# strings land in check_result.reason and are the user-facing
# explanation for "no data available".
TIER_REASONS = {
    "TABLE_DETAIL": (
        "Requires DESCRIBE DETAIL per table (file counts, partition columns, "
        "clustering). Not exposed by system tables; needs a per-object scan pass."
    ),
    "WORKSPACE_API": (
        "Requires a workspace API (Genie, Dashboards, Workspace/Git, or SHOW GRANTS). "
        "Not exposed by system tables."
    ),
    "ACCOUNT_API": (
        "Requires the Account API or account console (workspace inventory, admin "
        "roles, identity federation, budgets). Not exposed by system tables."
    ),
    "REPO_SCAN": (
        "Requires scanning source control or exported notebook sources."
    ),
    "MANUAL": (
        "Design judgment. Requires review of documented decisions, not a query."
    ),
    "SYSTEM_TABLE": (
        "Measurable from system tables, but no collector check is implemented yet."
    ),
}


@dataclass
class Pattern:
    """One registry entry, joined to its markdown document."""

    id: str
    category: str
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


@dataclass
class Outcome:
    """Result of running (or declining to run) one check."""

    pattern_id: str
    status: str
    conformance_pct: float | None = None
    numerator: int | None = None
    denominator: int | None = None
    unit: str | None = None
    reason: str | None = None
    evidence_query: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)

    def grade(self, pattern: Pattern) -> str | None:
        if self.status != MEASURED or self.conformance_pct is None:
            return None
        if self.conformance_pct >= pattern.target_pct:
            return GOOD
        if self.conformance_pct >= pattern.floor_pct:
            return FAIR
        return POOR


# --- registry ---------------------------------------------------------

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
    for rec in raw["patterns"]:
        category = rec["cat"]
        doc_rel = os.path.join(category, f"{rec['id']}.md")
        doc_abs = os.path.join(patterns_dir, doc_rel)
        title, is_anti = rec["id"], False
        if os.path.exists(doc_abs):
            body = open(doc_abs, encoding="utf-8").read()
            first = body.splitlines()[0] if body else ""
            title = first.lstrip("# ").strip() or rec["id"]
            is_anti = "ANTI-PATTERN" in body
        patterns.append(
            Pattern(
                id=rec["id"],
                category=category,
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
    return patterns, str(raw.get("version", "unknown")), checksum


# --- preflight --------------------------------------------------------


class Capability:
    """Probes which system tables and columns this run can actually read.

    Every check declares the objects it needs. Anything missing — because
    the schema is not enabled, the runner lacks grants, or the column was
    renamed — turns into NOT_AVAILABLE with a precise reason, rather than
    a stack trace or, worse, a silently optimistic score.
    """

    def __init__(self, spark):
        self._spark = spark
        self._cache: dict[str, set[str] | None] = {}

    def columns(self, fqn: str) -> set[str] | None:
        """Lowercased column names for `fqn`, or None if unreadable."""
        if fqn not in self._cache:
            try:
                cols = {f.name.lower() for f in self._spark.table(fqn).schema.fields}
                self._cache[fqn] = cols
            except Exception:
                self._cache[fqn] = None
        return self._cache[fqn]

    def missing(self, requires: dict[str, list[str]]) -> str | None:
        """Return a human reason if anything required is unavailable."""
        for fqn, needed in requires.items():
            cols = self.columns(fqn)
            if cols is None:
                return (
                    f"`{fqn}` is not readable from this workspace — the system schema "
                    f"may not be enabled, or the runner lacks SELECT on it."
                )
            absent = [c for c in needed if c.lower() not in cols]
            if absent:
                return (
                    f"`{fqn}` is readable but lacks expected column(s): "
                    f"{', '.join(absent)}. The system table schema has likely changed; "
                    f"the check needs updating."
                )
        return None


# --- scoring ----------------------------------------------------------


def applicable(pattern: Pattern, facts: dict[str, bool]) -> bool:
    """Whether a pattern is in scope given what exists in the workspace."""
    rule = pattern.applicability
    if rule == "ALWAYS":
        return True
    return bool(facts.get(rule, False))


def score(patterns: list[Pattern], outcomes: dict[str, Outcome], facts: dict[str, bool]):
    """Compute per-category and overall scores.

    Scores are the weighted mean conformance over MEASURED checks only.
    Coverage is measured weight over applicable weight, so a high score
    on thin evidence is always visible as such.
    """
    by_cat: dict[str, dict[str, float]] = {}
    tot_app = tot_meas = tot_weighted = 0.0
    n = {MEASURED: 0, NOT_AVAILABLE: 0, NOT_APPLICABLE: 0, ERROR: 0}
    critical_gaps = 0

    for p in patterns:
        out = outcomes.get(p.id)
        cat = by_cat.setdefault(
            p.category,
            {"w_app": 0.0, "w_meas": 0.0, "weighted": 0.0,
             MEASURED: 0.0, NOT_AVAILABLE: 0.0, NOT_APPLICABLE: 0.0, ERROR: 0.0, "poor": 0.0},
        )
        if not applicable(p, facts):
            cat[NOT_APPLICABLE] += 1
            n[NOT_APPLICABLE] += 1
            continue
        cat["w_app"] += p.weight
        tot_app += p.weight
        if out is None or out.status != MEASURED:
            status = out.status if out else NOT_AVAILABLE
            cat[status] += 1
            n[status] += 1
            continue
        cat[MEASURED] += 1
        n[MEASURED] += 1
        cat["w_meas"] += p.weight
        cat["weighted"] += p.weight * (out.conformance_pct or 0.0)
        tot_meas += p.weight
        tot_weighted += p.weight * (out.conformance_pct or 0.0)
        if out.grade(p) == POOR:
            cat["poor"] += 1
            if p.severity == "CRITICAL":
                critical_gaps += 1

    cats = []
    for name, c in sorted(by_cat.items()):
        cats.append(
            {
                "category": name,
                "weighted_score": round(c["weighted"] / c["w_meas"], 2) if c["w_meas"] else None,
                "coverage_pct": round(100.0 * c["w_meas"] / c["w_app"], 2) if c["w_app"] else 0.0,
                "weight_applicable": c["w_app"],
                "weight_measured": c["w_meas"],
                "n_measured": int(c[MEASURED]),
                "n_not_available": int(c[NOT_AVAILABLE]),
                "n_not_applicable": int(c[NOT_APPLICABLE]),
                "n_error": int(c[ERROR]),
                "n_poor": int(c["poor"]),
            }
        )

    coverage = round(100.0 * tot_meas / tot_app, 2) if tot_app else 0.0
    confidence = "HIGH" if coverage >= 70 else "MEDIUM" if coverage >= 40 else "LOW"
    overall = {
        "overall_score": round(tot_weighted / tot_meas, 2) if tot_meas else None,
        "coverage_pct": coverage,
        "confidence": confidence,
        "weight_applicable": tot_app,
        "weight_measured": tot_meas,
        "n_patterns": len(patterns),
        "n_measured": n[MEASURED],
        "n_not_available": n[NOT_AVAILABLE],
        "n_not_applicable": n[NOT_APPLICABLE],
        "n_error": n[ERROR],
        "critical_gaps": critical_gaps,
    }
    return cats, overall


def split_sql(ddl: str) -> list[str]:
    """Split a DDL script on statement boundaries, quote-aware.

    A naive split on ';' breaks on semicolons inside COMMENT strings,
    which the result schema uses throughout. Line comments are stripped
    in the same pass, because they too can contain semicolons.
    """
    statements, buf, in_str = [], [], False
    i, n = 0, len(ddl)
    while i < n:
        ch = ddl[i]
        if in_str:
            # '' inside a string is an escaped quote, not a terminator.
            if ch == "'" and i + 1 < n and ddl[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            if ch == "'":
                in_str = False
            buf.append(ch)
        elif ch == "'":
            in_str = True
            buf.append(ch)
        elif ch == "-" and i + 1 < n and ddl[i + 1] == "-":
            # Skip to end of line, preserving the newline.
            j = ddl.find("\n", i)
            i = n if j == -1 else j
            continue
        elif ch == ";":
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    statements.append("".join(buf))

    return [s.strip() for s in statements if s.strip()]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_json(obj: Any) -> str:
    return json.dumps(obj, default=str)
