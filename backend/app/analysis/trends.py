"""Corpus and governance trends analyzer — direction D.

Pure helpers (no I/O) are independently testable offline.  All DB access is
isolated to the thin ``compute_trends`` wrapper at the bottom.

TrendsDTO contract (camelCase keys):
    series[]                list[TrendPoint]
    byRepo[]                list[RepoBreakdown]
    proposalAcceptanceRate  float
    confidenceHistogram     list[{bucket: str, count: int}]
    evidenceCoverage        float
    asOf                    ISO-8601 string (UTC)

TrendPoint keys:
    date, staleDetected, staleFixed, conflictsDetected,
    conflictsResolved, brokenLinks, qualityAvg

RepoBreakdown keys:
    repo, totalDocs, qualityAvg, brokenLinks, atRisk

Applied-action → fixed mapping (mirrors governance/metrics.py):
    staleFixed        = applied_update + applied_merge
    conflictsResolved = applied_update + applied_merge
    (duplicatesRemoved / brokenLinksResolved are not part of TrendPoint)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Confidence-histogram bucket definitions (order is significant)
# ---------------------------------------------------------------------------

# Each tuple: (display label, inclusive lower, exclusive upper).
# The LAST bucket's upper bound is inclusive (handles confidence == 1.0).
_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("0.0\u20130.2", 0.0, 0.2),  # U+2013 EN DASH
    ("0.2\u20130.4", 0.2, 0.4),
    ("0.4\u20130.6", 0.4, 0.6),
    ("0.6\u20130.8", 0.6, 0.8),
    ("0.8\u20131.0", 0.8, 1.0),
)

_TRACKED_ACTIONS = frozenset({"update", "merge", "deprecate", "link"})


# ---------------------------------------------------------------------------
# Private date helpers
# ---------------------------------------------------------------------------


def _to_date_str(iso: str | None) -> str | None:
    """Extract the YYYY-MM-DD prefix from an ISO-8601 string.

    Returns ``None`` when the input is falsy or not a string.
    """
    if not iso:
        return None
    try:
        return str(iso)[:10]
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Pure helper 1 — applied actions per calendar day
# ---------------------------------------------------------------------------


def _applied_by_day(entries: list[dict]) -> dict[str, dict]:
    """Count applied governance actions grouped by calendar day.

    Accepts **either**:
    - provenance dicts (``approvedAt``, any action = applied), or
    - proposal dicts  (``appliedAt`` + ``status == "applied"`` required).

    Returns ``{YYYY-MM-DD: {update, merge, deprecate, link, staleFixed,
    conflictsResolved}}`` where ``staleFixed = update + merge`` and
    ``conflictsResolved = update + merge`` (governance/metrics.py semantics).
    """
    raw: dict[str, dict] = {}

    for entry in entries:
        # Determine the effective timestamp for this applied event.
        approved_at = entry.get("approvedAt")
        applied_at = entry.get("appliedAt")

        if approved_at:
            # Provenance row — always represents an applied change.
            ts: str | None = approved_at
        elif applied_at and (entry.get("status") or "").lower() == "applied":
            # Proposal row that has been fully applied.
            ts = applied_at
        else:
            continue

        day = _to_date_str(ts)
        if not day:
            continue

        action = (entry.get("action") or "").lower()
        rec = raw.setdefault(day, {k: 0 for k in _TRACKED_ACTIONS})
        if action in _TRACKED_ACTIONS:
            rec[action] += 1

    result: dict[str, dict] = {}
    for day, counts in raw.items():
        fixed = counts["update"] + counts["merge"]
        result[day] = {**counts, "staleFixed": fixed, "conflictsResolved": fixed}

    return result


# ---------------------------------------------------------------------------
# Pure helper 2 — trend series
# ---------------------------------------------------------------------------


def _series(snapshots: list[dict], applied_by_day: dict[str, dict]) -> list[dict]:
    """Build one TrendPoint dict per active calendar day.

    "Active" means any day that appears in *snapshots* **or** *applied_by_day*
    (union).  For snapshot values on applied-event-only days, the most-recent
    prior snapshot is forward-filled; values default to 0 / 0.0 before the
    first snapshot.

    Rules:
    - The LAST snapshot of each day (by ``takenAt`` string — ISO 8601 sorts
      lexicographically) supplies ``staleDetected``, ``conflictsDetected``,
      ``brokenLinks``, and ``qualityAvg``.
    - ``staleFixed`` / ``conflictsResolved`` come from *applied_by_day*
      (``0`` when absent).
    - Output is sorted ascending by date string.
    """
    # 1. Find the latest snapshot per day.
    last_per_day: dict[str, dict] = {}
    for snap in snapshots:
        day = _to_date_str(snap.get("takenAt"))
        if not day:
            continue
        prev = last_per_day.get(day)
        if prev is None or (snap.get("takenAt") or "") >= (prev.get("takenAt") or ""):
            last_per_day[day] = snap

    # 2. Union of all days that warrant a data point.
    all_days = sorted(set(last_per_day.keys()) | set(applied_by_day.keys()))

    # 3. Assemble with forward-fill for detected/quality/brokenLinks.
    points: list[dict] = []
    last_snap: dict | None = None

    for day in all_days:
        snap = last_per_day.get(day)
        if snap is not None:
            last_snap = snap

        applied = applied_by_day.get(day, {})
        ctx = last_snap or {}

        points.append(
            {
                "date": day,
                "staleDetected": ctx.get("staleDetected") or 0,
                "staleFixed": applied.get("staleFixed", 0),
                "conflictsDetected": ctx.get("conflictsDetected") or 0,
                "conflictsResolved": applied.get("conflictsResolved", 0),
                "brokenLinks": ctx.get("brokenLinks") or 0,
                "qualityAvg": ctx.get("qualityAvg") or 0.0,
            }
        )

    return points


# ---------------------------------------------------------------------------
# Pure helper 3 — per-repo breakdown
# ---------------------------------------------------------------------------


def _by_repo(snapshots: list[dict]) -> list[RepoBreakdown_]:
    """Return one ``RepoBreakdown`` dict per repo using the LATEST snapshot.

    Latest = highest ``takenAt`` ISO string within each repo group.
    Snapshots missing a ``repo`` value are silently skipped.
    Output sorted ascending by repo name.
    """
    latest: dict[str, dict] = {}
    for snap in snapshots:
        repo = snap.get("repo")
        if not repo:
            continue
        prev = latest.get(repo)
        if prev is None or (snap.get("takenAt") or "") >= (prev.get("takenAt") or ""):
            latest[repo] = snap

    return [
        {
            "repo": repo,
            "totalDocs": snap.get("totalDocs") or 0,
            "qualityAvg": snap.get("qualityAvg") or 0.0,
            "brokenLinks": snap.get("brokenLinks") or 0,
            "atRisk": snap.get("atRiskCount") or 0,
        }
        for repo, snap in sorted(latest.items())
    ]


# ---------------------------------------------------------------------------
# Pure helper 4 — proposal acceptance rate
# ---------------------------------------------------------------------------


def _acceptance_rate(proposals: list[dict]) -> float:
    """Fraction of proposals whose status is ``"applied"`` or ``"approved"``.

    Returns ``0.0`` when *proposals* is empty.
    """
    if not proposals:
        return 0.0
    accepted = sum(
        1
        for p in proposals
        if (p.get("status") or "").lower() in ("applied", "approved")
    )
    return round(accepted / len(proposals), 4)


# ---------------------------------------------------------------------------
# Pure helper 5 — confidence histogram
# ---------------------------------------------------------------------------


def _confidence_histogram(proposals: list[dict]) -> list[dict]:
    """Count proposals per confidence bucket.

    Buckets span ``[0, 1]`` with half-open intervals ``[lo, hi)`` except the
    last bucket which is fully closed ``[0.8, 1.0]`` so that confidence ``1.0``
    is captured.  Boundary values (0.2, 0.4, 0.6, 0.8) belong to the UPPER
    (higher) bucket.  Proposals with ``None`` or non-numeric confidence are
    skipped.
    """
    counts = {label: 0 for label, _, _ in _BUCKETS}
    n_buckets = len(_BUCKETS)

    for p in proposals:
        raw = p.get("confidence")
        if raw is None:
            continue
        try:
            c = float(raw)
        except (TypeError, ValueError):
            continue

        for i, (label, lo, hi) in enumerate(_BUCKETS):
            # Last bucket uses closed upper bound to capture c == 1.0.
            in_bucket = (lo <= c <= hi) if i == n_buckets - 1 else (lo <= c < hi)
            if in_bucket:
                counts[label] += 1
                break

    return [{"bucket": label, "count": counts[label]} for label, _, _ in _BUCKETS]


# ---------------------------------------------------------------------------
# Pure helper 6 — evidence coverage
# ---------------------------------------------------------------------------


def _has_commit_sha(items: list[Any]) -> bool:
    """Return True when any item dict carries a non-empty commit SHA."""
    for item in items:
        if not isinstance(item, dict):
            continue
        # Support both snake_case (AgentProposal / Evidence model) and camelCase.
        sha = item.get("commit_sha") or item.get("commitSha") or ""
        if sha:
            return True
    return False


def _evidence_coverage(proposals: list[dict]) -> float:
    """Fraction of proposals with ≥1 grounded evidence item carrying a commit SHA.

    Inspects the ``evidence`` and ``citations`` sub-lists in each proposal.
    Supports two layouts:

    - *Raw proposal dict* (``AgentProposal.model_dump()``): evidence/citations
      appear at the top level.
    - *Store row* (from ``list_proposals``): evidence/citations live inside the
      ``"payload"`` sub-dict.

    Returns ``0.0`` when *proposals* is empty.
    """
    if not proposals:
        return 0.0

    grounded = 0
    for p in proposals:
        payload: dict = p.get("payload") or {}
        # Check top-level first; fall back to payload sub-dict.
        evidence = p.get("evidence") or payload.get("evidence") or []
        citations = p.get("citations") or payload.get("citations") or []
        if _has_commit_sha(evidence) or _has_commit_sha(citations):
            grounded += 1

    return round(grounded / len(proposals), 4)


# ---------------------------------------------------------------------------
# Top-level assembler (pure)
# ---------------------------------------------------------------------------

# Type alias (documentation only — plain dict at runtime).
RepoBreakdown_ = dict


def assemble_trends(
    snapshots: list[dict],
    proposals: list[dict],
    provenance: list[dict],
    now: datetime | None = None,
) -> dict:
    """Assemble a full ``TrendsDTO`` from plain Python collections.

    Parameters
    ----------
    snapshots:
        camelCase dicts from ``get_analysis_snapshots`` (oldest→newest).
    proposals:
        camelCase dicts from ``list_proposals``.
    provenance:
        camelCase dicts from ``list_provenance``.
    now:
        Override the UTC wall-clock for ``asOf`` (useful in tests).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    applied = _applied_by_day(provenance)

    return {
        "series": _series(snapshots, applied),
        "byRepo": _by_repo(snapshots),
        "proposalAcceptanceRate": _acceptance_rate(proposals),
        "confidenceHistogram": _confidence_histogram(proposals),
        "evidenceCoverage": _evidence_coverage(proposals),
        "asOf": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Thin I/O wrapper — ALL DB access lives here
# ---------------------------------------------------------------------------


def compute_trends(namespace: str | None = None) -> dict:
    """Fetch data from the store and return a ``TrendsDTO``.

    This is the only function in the module that performs I/O.  It imports
    store helpers lazily so the rest of the module (pure helpers + assembler)
    remains fully importable and testable without a live database.
    """
    # Lazy imports: keep pure module importable offline.
    from app.storage.queries import get_analysis_snapshots  # noqa: PLC0415
    from app.governance.store import list_proposals, list_provenance  # noqa: PLC0415

    snapshots = get_analysis_snapshots(namespace=namespace)
    proposals = list_proposals(namespace=namespace)
    # list_provenance() with no filters returns ALL rows (ordered approved_at DESC).
    provenance = list_provenance()

    return assemble_trends(snapshots, proposals, provenance)
