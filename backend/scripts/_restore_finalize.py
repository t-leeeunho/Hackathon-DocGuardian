"""TEMP restore finalizer: wait for the 3 group loaders, then rebuild the HNSW
vector index and re-detect conflict/duplicate edges. Deleted after the restore."""
import time
from pathlib import Path

import psycopg

ROOT = Path(r"C:\workspace\Intern-Hackathon-DocGuardian")
URL = "postgresql://docguardian:docguardian@localhost:5432/docguardian"
DEADLINE = time.time() + 120 * 60  # safety cap


def groups_done() -> bool:
    done = 0
    for k in range(3):
        p = ROOT / f"_restore_g{k}.out.log"
        if p.exists() and "GROUP DONE" in p.read_text(errors="ignore"):
            done += 1
    return done == 3


while not groups_done() and time.time() < DEADLINE:
    time.sleep(20)

# 1) rebuild the HNSW cosine index (dropped during bulk load)
with psycopg.connect(URL, autocommit=True) as c, c.cursor() as cur:
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )

# 2) re-detect duplicate/conflict edges across the whole corpus
from app.processing.conflicts import detect_conflict_edges  # noqa: E402

written = detect_conflict_edges(None)

with psycopg.connect(URL) as c, c.cursor() as cur:
    cur.execute("select count(*) from documents"); docs = cur.fetchone()[0]
    cur.execute("select count(*) from chunks"); chunks = cur.fetchone()[0]
    cur.execute("select count(*) from edges"); edges = cur.fetchone()[0]
    cur.execute("select count(distinct repo) from documents"); repos = cur.fetchone()[0]

(ROOT / "_restore_DONE.log").write_text(
    f"docs={docs} chunks={chunks} edges={edges} repos={repos} "
    f"conflict_edges_written={written}\n",
    encoding="utf-8",
)
print(f"FINALIZED docs={docs} chunks={chunks} edges={edges} repos={repos}", flush=True)
