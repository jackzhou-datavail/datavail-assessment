"""Result vocabulary shared by every assessment in this repo.

An assessment produces, for each item it knows about, either a
percentage or an explicit reason no measurement was possible. There is
no third option, and a missing measurement is never silently treated as
a pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

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


class Scorable(Protocol):
    """What `core.scoring` needs of an item, whatever the assessment."""

    id: str
    category: str
    severity: str
    weight: float
    applicability: str
    target_pct: float
    floor_pct: float


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

    def grade(self, item: "Scorable") -> str | None:
        if self.status != MEASURED or self.conformance_pct is None:
            return None
        if self.conformance_pct >= item.target_pct:
            return GOOD
        if self.conformance_pct >= item.floor_pct:
            return FAIR
        return POOR


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_json(obj: Any) -> str:
    return json.dumps(obj, default=str)
