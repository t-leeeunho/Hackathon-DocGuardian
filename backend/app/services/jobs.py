"""In-memory job registry for background ingestion (README §8B job queue).

Tracks the lifecycle of an async document ingest so the client can poll
``GET /jobs/{jobId}`` (and/or listen on ``WS /stream``) instead of blocking on the
slow embed + summarize + conflict-detect pipeline. Single-process and thread-safe;
good enough for the hackathon. Completed jobs are kept briefly for status reads.
"""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any, Optional

# status: queued -> processing -> succeeded | failed
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_MAX_JOBS = 200


def create_job(doc_id: str) -> dict[str, Any]:
    job_id = "job_" + secrets.token_hex(8)
    job = {
        "jobId": job_id,
        "docId": doc_id,
        "status": "queued",
        "result": None,
        "error": None,
        "createdAt": time.time(),
        "updatedAt": time.time(),
    }
    with _lock:
        _jobs[job_id] = job
        # Evict oldest finished jobs if we grow too large.
        if len(_jobs) > _MAX_JOBS:
            for jid in sorted(_jobs, key=lambda k: _jobs[k]["updatedAt"])[: len(_jobs) - _MAX_JOBS]:
                if _jobs[jid]["status"] in ("succeeded", "failed"):
                    _jobs.pop(jid, None)
    return dict(job)


def set_status(
    job_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = status
        if result is not None:
            job["result"] = result
            # The Librarian may re-file the doc, so the real id is only known once
            # the ingest finishes — keep the job's docId in sync with the result
            # (accept either the camelCase DTO or the raw snake_case result).
            doc_id = result.get("docId") or result.get("doc_id")
            if doc_id:
                job["docId"] = doc_id
        if error is not None:
            job["error"] = error
        job["updatedAt"] = time.time()


def set_progress(job_id: str, **fields: Any) -> None:
    """Merge arbitrary progress fields (e.g. imported count, message) into a job."""
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(fields)
        job["updatedAt"] = time.time()


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
