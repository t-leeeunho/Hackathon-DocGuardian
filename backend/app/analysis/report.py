"""Aggregator for DocGuardian Insights — per-doc and corpus-level reports.

Pure mappers convert analyzer dataclasses to camelCase dicts; thin IO wrappers
orchestrate DB reads + analyzers without leaking I/O into the pure layer.

Public API
----------
Pure (no I/O, offline-testable)::

    _quality_to_dto(q: DocQuality) -> dict        # snake → camelCase
    _links_to_dto(l: DocLinks)     -> dict        # snake → camelCase
    _drift_to_dto(d: DocDrift)     -> dict        # snake → camelCase

    assemble_doc_analysis(doc_id, quality, links, drift, centrality,
                          llm=None) -> dict       # DocAnalysis DTO

    assemble_report(rows, repo_filter=None,
                    now=None, top_n=5) -> dict    # AnalysisReport DTO

    report_to_snapshot_row(report, repo=None,
                           **extra_counts) -> dict  # snapshot-table row

IO wrappers (require live DB)::

    compute_doc_analysis(doc_id, namespace=None, llm_notes=None) -> dict
    compute_report(namespace=None)                                 -> dict

DTO shapes
----------
DocAnalysis::
    {docId, quality:{qualityScore, readability, gradeLevel,
     completenessScore, structureScore, wordCount, placeholderCount, issues},
     links:{brokenInternal, brokenLinkCount, externalCount, orphan, deadEnd},
     drift:{ageDays, isStale, riskScore, riskReasons},
     centrality, llm}

AnalysisReport::
    {repoFilter, totalDocs, qualityAvg, brokenLinksDetected,
     orphanCount, atRiskCount,
     worstQuality: DocRef[], mostAtRisk: DocRef[], topCentral: DocRef[],
     asOf}

DocRef::
    {docId, score, reasons}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.analysis.drift import DocDrift
from app.analysis.links import DocLinks
from app.analysis.quality import DocQuality

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: At-risk threshold for drift risk_score.
#:
#: A document is counted as "at risk" when its ``drift.risk_score >= 0.5``.
#: 0.5 is the midpoint of the [0, 1] scale; values at or above it indicate
#: *at least moderate* risk (e.g. unverified since last commit, aging doc, or
#: a doc carrying a conflict/duplicate edge).  Callers can inspect the raw
#: ``riskScore`` for finer-grained bucketing.
AT_RISK_THRESHOLD: float = 0.5

#: Maximum number of quality ``issues`` to surface per DocRef in worstQuality.
_MAX_QUALITY_REASONS: int = 3


# ---------------------------------------------------------------------------
# Pure mappers — snake_case dataclass → camelCase dict
# ---------------------------------------------------------------------------


def _quality_to_dto(q: DocQuality) -> dict:
    """Map a :class:`~app.analysis.quality.DocQuality` to a camelCase dict.

    Field mapping:
    ``quality_score``      → ``qualityScore``
    ``readability``        → ``readability``       (no change)
    ``grade_level``        → ``gradeLevel``
    ``completeness_score`` → ``completenessScore``
    ``structure_score``    → ``structureScore``
    ``word_count``         → ``wordCount``
    ``placeholder_count``  → ``placeholderCount``
    ``issues``             → ``issues``            (no change)
    """
    return {
        "qualityScore": q.quality_score,
        "readability": q.readability,
        "gradeLevel": q.grade_level,
        "completenessScore": q.completeness_score,
        "structureScore": q.structure_score,
        "wordCount": q.word_count,
        "placeholderCount": q.placeholder_count,
        "issues": list(q.issues),
    }


def _links_to_dto(lnk: DocLinks) -> dict:
    """Map a :class:`~app.analysis.links.DocLinks` to a camelCase dict.

    Field mapping:
    ``broken_internal``  → ``brokenInternal``
    ``broken_link_count``→ ``brokenLinkCount``
    ``external_count``   → ``externalCount``
    ``orphan``           → ``orphan``     (no change)
    ``dead_end``         → ``deadEnd``
    """
    return {
        "brokenInternal": list(lnk.broken_internal),
        "brokenLinkCount": lnk.broken_link_count,
        "externalCount": lnk.external_count,
        "orphan": lnk.orphan,
        "deadEnd": lnk.dead_end,
    }


def _drift_to_dto(d: DocDrift) -> dict:
    """Map a :class:`~app.analysis.drift.DocDrift` to a camelCase dict.

    Field mapping:
    ``age_days``     → ``ageDays``
    ``is_stale``     → ``isStale``
    ``risk_score``   → ``riskScore``
    ``risk_reasons`` → ``riskReasons``
    """
    return {
        "ageDays": d.age_days,
        "isStale": d.is_stale,
        "riskScore": d.risk_score,
        "riskReasons": list(d.risk_reasons),
    }


# ---------------------------------------------------------------------------
# Pure assembler — single-document DocAnalysis DTO
# ---------------------------------------------------------------------------


def assemble_doc_analysis(
    doc_id: str,
    quality: DocQuality,
    links: DocLinks,
    drift: DocDrift,
    centrality: float,
    llm: Any = None,
) -> dict:
    """Assemble a ``DocAnalysis`` camelCase dict from per-doc analyzer outputs.

    Parameters
    ----------
    doc_id:
        Unique document identifier (e.g. ``"vscode/docs/build.md"``).
    quality:
        Result of :func:`~app.analysis.quality.analyze_quality`.
    links:
        Result of :func:`~app.analysis.links.analyze_links`.
    drift:
        Result of :func:`~app.analysis.drift.analyze_drift`.
    centrality:
        Normalised PageRank score from
        :func:`~app.analysis.graph_structure.centrality_for` (range ``[0, 1]``).
    llm:
        Optional LLM-layer notes dict (e.g. ``LlmQualityNotes``).
        ``None`` when the LLM layer was not invoked (the default).
    """
    return {
        "docId": doc_id,
        "quality": _quality_to_dto(quality),
        "links": _links_to_dto(links),
        "drift": _drift_to_dto(drift),
        "centrality": centrality,
        "llm": llm,
    }


# ---------------------------------------------------------------------------
# Pure assembler — corpus-level AnalysisReport DTO
# ---------------------------------------------------------------------------


def assemble_report(
    rows: list[dict],
    repo_filter: str | None = None,
    now: datetime | None = None,
    top_n: int = 5,
) -> dict:
    """Assemble a corpus-wide ``AnalysisReport`` camelCase dict.

    Parameters
    ----------
    rows:
        Per-document analysis rows.  Each row is a plain dict with keys::

            {
                "docId":      str,
                "quality":    DocQuality,
                "links":      DocLinks,
                "drift":      DocDrift,
                "centrality": float,
            }

    repo_filter:
        Namespace / repo filter that was applied when gathering *rows*
        (or ``None`` for a full-corpus report).  Passed through to
        ``repoFilter`` in the output.
    now:
        UTC datetime for the ``asOf`` timestamp.  Defaults to
        ``datetime.now(timezone.utc)`` when ``None``.
    top_n:
        Maximum number of entries in ``worstQuality``, ``mostAtRisk``, and
        ``topCentral``.  Fewer entries are returned when the corpus is
        smaller than *top_n*.

    At-risk definition
    ------------------
    A document is counted as "at risk" when its
    ``drift.risk_score >= AT_RISK_THRESHOLD`` (0.5).  Scores at or above
    this midpoint indicate at least moderate risk — the doc is either
    unverified since its last commit, significantly aged, or carries a
    conflict/duplicate edge.

    qualityAvg
    ----------
    Mean of all ``quality.quality_score`` values, rounded to 3 decimal
    places.  Returns ``0.0`` for an empty corpus.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    total = len(rows)

    if total == 0:
        return {
            "repoFilter": repo_filter,
            "totalDocs": 0,
            "qualityAvg": 0.0,
            "brokenLinksDetected": 0,
            "orphanCount": 0,
            "atRiskCount": 0,
            "worstQuality": [],
            "mostAtRisk": [],
            "topCentral": [],
            "asOf": now.isoformat(),
        }

    # --- Aggregate scalars -----------------------------------------------
    quality_avg = round(
        sum(r["quality"].quality_score for r in rows) / total, 3
    )
    broken_links_detected = sum(r["links"].broken_link_count for r in rows)
    orphan_count = sum(1 for r in rows if r["links"].orphan)
    at_risk_count = sum(
        1 for r in rows if r["drift"].risk_score >= AT_RISK_THRESHOLD
    )

    # --- worstQuality: top_n lowest qualityScore (ascending) --------------
    sorted_by_quality = sorted(rows, key=lambda r: r["quality"].quality_score)
    worst_quality: list[dict] = [
        {
            "docId": r["docId"],
            "score": r["quality"].quality_score,
            # First few issues give the reviewer quick context
            "reasons": r["quality"].issues[:_MAX_QUALITY_REASONS],
        }
        for r in sorted_by_quality[:top_n]
    ]

    # --- mostAtRisk: top_n highest riskScore (descending) -----------------
    sorted_by_risk = sorted(
        rows, key=lambda r: r["drift"].risk_score, reverse=True
    )
    most_at_risk: list[dict] = [
        {
            "docId": r["docId"],
            "score": r["drift"].risk_score,
            "reasons": list(r["drift"].risk_reasons),
        }
        for r in sorted_by_risk[:top_n]
    ]

    # --- topCentral: top_n highest centrality (descending) ----------------
    sorted_by_centrality = sorted(
        rows, key=lambda r: r["centrality"], reverse=True
    )
    top_central: list[dict] = [
        {
            "docId": r["docId"],
            "score": r["centrality"],
            "reasons": [],
        }
        for r in sorted_by_centrality[:top_n]
    ]

    return {
        "repoFilter": repo_filter,
        "totalDocs": total,
        "qualityAvg": quality_avg,
        "brokenLinksDetected": broken_links_detected,
        "orphanCount": orphan_count,
        "atRiskCount": at_risk_count,
        "worstQuality": worst_quality,
        "mostAtRisk": most_at_risk,
        "topCentral": top_central,
        "asOf": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------------


def report_to_snapshot_row(
    report: dict,
    repo: str | None = None,
    **extra_counts: Any,
) -> dict:
    """Convert an ``AnalysisReport`` dict to a snapshot-table row shape.

    The analysis layer does not track conflict, duplicate, or stale *detected*
    counts directly (those come from ingestion events or the caller).  Pass
    them via ``extra_counts``; they default to ``None`` when absent.

    Parameters
    ----------
    report:
        The dict produced by :func:`assemble_report` or
        :func:`compute_report`.
    repo:
        Repository / namespace override.  When ``None``, falls back to
        ``report["repoFilter"]``.
    **extra_counts:
        Optional counts supplied by the caller:
        ``staleDetected``, ``conflictsDetected``, ``duplicatesDetected``.
        Any key absent from *extra_counts* is stored as ``None``.

    Returns a flat dict suitable for insertion into the
    ``analysis_snapshots`` table (``snapshotId`` is assigned by the DB
    and is therefore **not** included here).
    """
    effective_repo = repo if repo is not None else report.get("repoFilter")
    return {
        "repo": effective_repo,
        "totalDocs": report.get("totalDocs", 0),
        "qualityAvg": report.get("qualityAvg", 0.0),
        "brokenLinks": report.get("brokenLinksDetected", 0),
        "orphanCount": report.get("orphanCount", 0),
        "atRiskCount": report.get("atRiskCount", 0),
        "staleDetected": extra_counts.get("staleDetected"),
        "conflictsDetected": extra_counts.get("conflictsDetected"),
        "duplicatesDetected": extra_counts.get("duplicatesDetected"),
        "payload": report,
    }


# ---------------------------------------------------------------------------
# IO wrappers — ALL DB access lives here; pure helpers stay offline-safe
# ---------------------------------------------------------------------------


def compute_doc_analysis(
    doc_id: str,
    namespace: str | None = None,
    llm_notes: Any = None,
) -> dict:
    """Gather signals from the DB, run all analyzers, return a ``DocAnalysis`` dict.

    This is the only I/O entry-point for per-document analysis.

    Parameters
    ----------
    doc_id:
        The document to analyse.
    namespace:
        Optional repo namespace passed to :func:`gather_corpus_signals`
        to restrict PageRank to the same namespace.
    llm_notes:
        Pre-computed LLM notes dict to embed in the result (or ``None``
        to omit the LLM layer entirely).
    """
    # Lazy imports keep the pure helpers importable without a live DB.
    from app.analysis.drift import analyze_drift  # noqa: PLC0415
    from app.analysis.graph_structure import centrality_for, pagerank  # noqa: PLC0415
    from app.analysis.links import analyze_links  # noqa: PLC0415
    from app.analysis.quality import analyze_quality  # noqa: PLC0415
    from app.analysis.signals import gather_corpus_signals, gather_doc_signals  # noqa: PLC0415

    corpus = gather_corpus_signals(namespace)
    sig = gather_doc_signals(doc_id)

    # PageRank over the corpus (references edges only).
    ref_edges = [(f, t) for f, t, typ in corpus.edges if typ == "references"]
    ranks = pagerank(ref_edges, corpus.doc_ids)
    centrality = centrality_for(doc_id, ranks)

    quality = analyze_quality(sig)
    links = analyze_links(sig, corpus)
    drift = analyze_drift(sig, importance=centrality)

    return assemble_doc_analysis(
        doc_id, quality, links, drift, centrality, llm=llm_notes
    )


def compute_report(namespace: str | None = None) -> dict:
    """Gather corpus signals + analyse every document; return an ``AnalysisReport``.

    PageRank is computed once over the full (namespace-filtered) corpus.
    Per-doc signal gathering is parallelism-friendly but kept sequential here
    for simplicity — each call is a single indexed DB query.

    Individual documents that cannot be fetched (e.g. a doc deleted between
    the corpus listing and the per-doc query) are silently skipped so one bad
    document does not abort the entire corpus report.

    Parameters
    ----------
    namespace:
        Optional repo filter; restricts to documents whose ``doc_id`` starts
        with ``"{namespace}/"``.
    """
    # Lazy imports — keep the pure layer importable offline.
    from app.analysis.drift import analyze_drift  # noqa: PLC0415
    from app.analysis.graph_structure import centrality_for, pagerank  # noqa: PLC0415
    from app.analysis.links import analyze_links  # noqa: PLC0415
    from app.analysis.quality import analyze_quality  # noqa: PLC0415
    from app.analysis.signals import gather_corpus_signals, gather_doc_signals  # noqa: PLC0415

    corpus = gather_corpus_signals(namespace)

    if not corpus.doc_ids:
        return assemble_report([], repo_filter=namespace)

    # Compute PageRank once over all reference edges in the (filtered) corpus.
    ref_edges = [(f, t) for f, t, typ in corpus.edges if typ == "references"]
    ranks = pagerank(ref_edges, corpus.doc_ids)

    rows: list[dict] = []
    for doc_id in corpus.doc_ids:
        try:
            sig = gather_doc_signals(doc_id)
        except Exception:  # noqa: BLE001
            # Doc may have been deleted between the corpus listing and now.
            continue

        centrality = centrality_for(doc_id, ranks)
        quality = analyze_quality(sig)
        links = analyze_links(sig, corpus)
        drift = analyze_drift(sig, importance=centrality)

        rows.append(
            {
                "docId": doc_id,
                "quality": quality,
                "links": links,
                "drift": drift,
                "centrality": centrality,
            }
        )

    return assemble_report(rows, repo_filter=namespace)
