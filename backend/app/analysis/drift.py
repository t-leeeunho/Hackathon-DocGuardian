"""Staleness & drift analysis (pure, deterministic — C-pillar of Insights).

``analyze_drift`` computes a risk score in [0, 1] by blending:
- document age (days since last commit),
- staleness (reuses ``DocSignals.is_stale`` semantics from governance/health),
- importance (high-importance + stale → extra risk),
- presence of conflict / duplicate edges.

All functions are **pure**: they take plain data and return plain data.
No DB access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.governance.health import DocSignals
from app.analysis.signals import DocAnalysisSignals

# ---------------------------------------------------------------------------
# Age helper
# ---------------------------------------------------------------------------


def doc_age_days(
    commit_date: datetime | None,
    now: datetime | None = None,
) -> int:
    """Return the age of the document in whole days, or 0 if *commit_date* is None.

    Both *commit_date* and *now* are treated as UTC when timezone-naïve.
    """
    if commit_date is None:
        return 0
    if now is None:
        now = datetime.now(timezone.utc)

    # Normalise to UTC if naïve
    if commit_date.tzinfo is None:
        commit_date = commit_date.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    return max(0, (now - commit_date).days)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DocDrift:
    """Drift / decay signals for one document."""

    age_days: int
    is_stale: bool
    risk_score: float  # [0..1]
    risk_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

# Thresholds for age-based risk labels
_AGING_DAYS = 180
_OLD_DAYS = 365


def analyze_drift(
    sig: DocAnalysisSignals,
    importance: float,
    now: datetime | None = None,
) -> DocDrift:
    """Compute drift risk for *sig*.

    Risk score formula (all terms capped so the total stays in [0, 1]):

    | Component                        | Weight |
    |----------------------------------|--------|
    | age (normalised, cap 1 yr)       |  0.25  |
    | staleness flag                   |  0.25  |
    | importance                       |  0.20  |
    | stale × importance (interaction) |  0.15  |
    | conflict edge                    |  0.10  |
    | duplicate edge                   |  0.05  |

    ``is_stale`` reuses ``DocSignals`` semantics:
    - no ``last_verified_sha`` → always stale (never reviewed).
    - ``last_verified_sha != commit_sha`` → stale since last commit.
    """
    health_sig = DocSignals(
        has_conflict_edge=sig.has_conflict_edge,
        has_duplicate_edge=sig.has_duplicate_edge,
        is_deprecated=sig.is_deprecated,
        current_commit_sha=sig.commit_sha,
        last_verified_sha=sig.last_verified_sha,
    )
    is_stale = health_sig.is_stale

    age = doc_age_days(sig.commit_date, now)
    age_norm = min(age / float(_OLD_DAYS), 1.0)
    stale_f = 1.0 if is_stale else 0.0

    base = 0.25 * age_norm + 0.25 * stale_f + 0.20 * importance
    interaction = 0.15 * stale_f * importance
    edge_pen = 0.10 * (1.0 if sig.has_conflict_edge else 0.0) + 0.05 * (
        1.0 if sig.has_duplicate_edge else 0.0
    )

    risk_score = round(min(1.0, max(0.0, base + interaction + edge_pen)), 3)

    reasons: list[str] = []
    if age > _OLD_DAYS:
        reasons.append(f"old: {age} days since last commit")
    elif age > _AGING_DAYS:
        reasons.append(f"aging: {age} days since last commit")
    if is_stale:
        reasons.append("unverified since last commit")
    if is_stale and importance > 0.6:
        reasons.append("high-importance doc is unverified")
    if sig.has_conflict_edge:
        reasons.append("has conflict edge")
    if sig.has_duplicate_edge:
        reasons.append("has duplicate edge")

    return DocDrift(
        age_days=age,
        is_stale=is_stale,
        risk_score=risk_score,
        risk_reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_at_risk(
    items: list[tuple[str, DocDrift]],
) -> list[tuple[str, DocDrift]]:
    """Return *items* sorted by ``risk_score`` descending (highest risk first)."""
    return sorted(items, key=lambda x: x[1].risk_score, reverse=True)
