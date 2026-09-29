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
