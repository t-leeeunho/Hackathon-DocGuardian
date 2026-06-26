# DocGuardian AI — Hackathon Demo Plan (Win Plan)

**Challenge:** Workplace AI Innovation — *"Reimagine the future of work by applying AI &
automation to productivity, collaboration, onboarding, learning, and decision-making; projects
may enhance existing Microsoft tools."*

**Target outcome:** Win the track with a tight, live, reliable demo that judges instantly
understand and remember — and that survives the "isn't this just Copilot?" question.

---

## 0. The pitch in one breath

> "A new hire's first week is a scavenger hunt through stale, contradictory docs. **DocGuardian
> is the AI layer that makes a team's knowledge trustworthy and self-maintaining** — it answers
> with evidence instead of guessing, detects when docs are stale or contradict each other, fixes
> the *source* with a human's approval, and lives inside the Microsoft tools you already use. We
> don't just *answer* from your docs — we *govern* them."

**The hook line to open with:** *"Copilot answers from your docs. Obsidian stores them.
DocGuardian governs them."*

---

## 1. Why we fit this challenge (pillar map)

Every capability below is **already built** — the demo just makes it visible and live.

| Workplace pillar | What the judge sees | DocGuardian capability |
| --- | --- | --- |
| **Productivity** | One trusted, sourced answer instead of an afternoon of doc-hunting | evidence-backed `/chat` (sources + confidence) |
| **Onboarding** | Day-one knowledge map: fresh vs stale at a glance, auto-organized | knowledge graph + health/freshness + Insights + Librarian auto-filing |
| **Collaboration** | Team converges on one source of truth, with a human gate + audit trail | proposal → approve/reject → provenance |
| **Learning** | Sourced answers; only what you're allowed to see | evidence-or-silence; permission-aware ACL |
| **Decision-making** | "Here's the one canonical way to build Garnet" | Curator→Guardian conflict resolution |
| **Enhance MS tools** | Same verified knowledge answered from Copilot CLI/IDE | built-in MCP server |

---

## 2. Differentiation — answer the "why not just X?" question before they ask

Judges **will** ask this. Lead with it; don't get cornered by it.

| "Why not just…" | What they do | What DocGuardian adds |
| --- | --- | --- |
| **Copilot / ChatGPT / doc-RAG** | **Read-time**: retrieve + synthesize an answer; will blend two conflicting docs and sound confident | **Write-time governance**: conflict is a first-class signal; repairs the **source**; evidence-or-silence (chunkId + commitSha + confidence); human approval + rollback |
| **Obsidian / Notion / Confluence** | Store + author **verbatim**; graph = **manual** links; dumb time-based "stale?" nudges; humans keep it tidy | **Automatic** detection of stale/duplicate/**conflicting** content vs source-of-truth; AI proposes the fix; the **Librarian rewrites every dropped doc into a canonical, agent-retrievable form and re-files it** for you |
| **Data observability** (Monte Carlo, Great Expectations) | Quality for **structured** data/pipelines | Quality + observability for **unstructured knowledge** — broken-link/orphan detection, PageRank centrality, staleness/drift risk, quality scoring: the data nobody governs |
| **Doc linters** (Vale) | **Style** checks | **Truth & conflict** checks against code signals |

**The sentence that wins the argument:**
> "RAG patches the *answer* at read time — the bad doc is still there, poisoning the next person
> and the next query. DocGuardian fixes the *data at the source*, so the whole team **and every
> Copilot query** gets the corrected version. We're not competing with Copilot — we're the trust
> layer underneath it. In fact, we feed it."

**"Isn't this already in production?"** The pieces exist (RAG, staleness reminders, data
observability for *structured* data) — but **no mainstream tool closes the loop** for knowledge:
detect-against-code-signals → evidence-backed proposal → human approve → provenance/rollback →
metrics, as a governed knowledge graph. That integrated loop with evidence discipline is the
novelty — and it's demoable in 5 minutes.

---

## 3. The hero scenario (one story, start to finish)

**Persona:** *Maya*, a new engineer onboarding to the team. *Sam*, the team lead who owns the docs.

**The arc:** Maya needs to build Garnet from source. Two docs disagree — the canonical `build.md`
targets **.NET 8**, while a stale `build-legacy.md` still says **.NET 6**. A generic copilot would
confidently give her the wrong one. DocGuardian catches the conflict, proposes one canonical doc
with evidence, Sam approves, the change is logged and reversible, the dashboard moves — and the same
verified answer is now available right inside Copilot.

Keep the **entire demo on this single thread.** No tangents.

---

## 4. The live demo script (≈5 minutes)

> Format per beat — **Say** (verbatim narration) · **Do** (on-screen action) · **Proves** (pillar).
> Run the backend with `CHAT_PROVIDER=fake` so the hero answer/proposal is **deterministic and
> offline** (see §7). Pre-stage everything in §7 before you walk on.

### Beat 0 — Hook (0:00–0:30)
- **Say:** *"Raise your hand if your team's docs are 100% up to date. Right — nobody. A new hire's
  first week is a scavenger hunt through stale, contradictory docs. Copilot answers from those
  docs. Obsidian stores them. DocGuardian **governs** them."*
- **Do:** Title screen → the DocGuardian knowledge graph already loaded.
- **Proves:** Framing + differentiation up front.

### Beat 1 — Ask, and get evidence not a guess (0:30–1:15)
- **Say:** *"Maya's first question: how do I build Garnet from source? Watch — DocGuardian answers
  with its sources and a confidence score. If it can't ground an answer, it says 'needs human
  review' instead of bluffing. That's evidence-or-silence."*
- **Do:** Type in chat: **"How do I build Garnet from source?"** → answer renders (`dotnet build
  -c Release`, **.NET 8**) with **citation chips** (`build.md` + `README.md`, with commit SHAs) and a
  **0.82 confidence** badge. Click a citation chip → it highlights the source node in the graph
  ("show your work").
- **Proves:** Productivity, Learning, Trust.

### Beat 2 — The knowledge map: fresh vs stale (1:15–2:00)
- **Say:** *"This is the whole team's knowledge as a living map. Green is fresh, red is stale,
  locked means you don't have access. A new hire sees the shape of the system on day one — no
  human had to draw these links; we derived them from the docs and the commits."*
- **Do:** Pan the graph; hover the **red/stale** node **`build-legacy.md`** (tooltip: stale .NET 6
  guide, old commit). Open the **Insights drawer** on it → low quality (0.34), 2 broken links,
  orphan, high staleness risk. Point out a **locked** node (`install-old.md`, permission-aware) and
  a **`duplicate-of`** pair (`install.md` ⟷ `install-old.md`).
- **Proves:** Onboarding, Observability, Trust (permissions).

### Beat 3 — The conflict + the contrast vs RAG (2:00–3:00) ← the money moment
- **Say:** *"Here's the trap. Two docs describe building Garnet — but one targets **.NET 8**, the
  stale one still says **.NET 6**. A normal copilot would just pick one and sound confident — and
  Maya wastes her afternoon. DocGuardian flags the contradiction as a first-class problem."*
- **Do:** Click the **`conflicts-with` edge** (weight 0.88) between **`build.md`** and
  **`build-legacy.md`** → side panel shows both snippets with the divergent SDK versions highlighted.
- **Say (contrast beat):** *"This is the difference. They patch the answer; we fix the source."*
- **Do:** Click **"Propose fix"** → the Curator drafts **one canonical 'Building Garnet'** doc
  (merges into `build.md`, supersedes the legacy page); the Guardian reviews it and attaches
  **evidence (the .NET 6 quote + commit) + a 0.79 confidence score + a recommendation** — here it
  flags that `build-legacy.md` has inbound links, so it routes to **human review** rather than
  auto-approving.
- **Proves:** Data quality, Decision-making — and nails the differentiation live.

### Beat 4 — Human in the loop: approve, with audit + rollback (3:00–3:50)
- **Say:** *"Nothing changes without a human. Sam, the doc owner, reviews a before/after diff —
  with the evidence right there — and approves. The moment he does, we write an immutable
  provenance record: what changed, who approved it, which agent proposed it, why, the sources, and
  the previous version. And it's reversible."*
- **Do:** Open the **diff (Monaco)**; click **Approve** → toast confirms; open the **Provenance
  panel** showing the new audit entry. Briefly hover **Rollback** to show it exists.
- **Proves:** Collaboration, Trust, Governance.

### Beat 5 — The dashboard moves (3:50–4:20)
- **Say:** *"And the scoreboard updates live: one conflict resolved, one stale doc on the mend,
  duplicates down, broken links fixed. This is knowledge health you can actually manage."*
- **Do:** Show the **metrics strip + Insights trends** updating (conflicts resolved ↑, stale ↓,
  broken links ↓, quality ↑) — auto-refreshed over the WebSocket right after the approval. The
  **Insights drawer** charts the same trend over time, with PageRank centrality ranking the
  most-relied-on docs.
- **Proves:** Observability, Decision-making, measurable impact.

### Beat 6 — The Microsoft tie-in finale (4:20–5:00)
- **Say:** *"Last thing. This isn't a walled garden. The same verified knowledge is available right
  where engineers already work — Copilot. Watch me ask the exact same question from the Copilot
  CLI, and get the **governed** answer, not a guess."*
- **Do:** Switch to a terminal → ask the same "how do I build Garnet from source?" question through
  the **MCP server / Copilot CLI** → same canonical, sourced answer.
- **Say (close):** *"Copilot answers. Obsidian stores. DocGuardian governs — and makes every
  Copilot answer trustworthy. That's how teams onboard faster and decide with confidence."*
- **Proves:** Enhance MS tools — the bonus the challenge explicitly asks for.

---

## 5. Timing cheat-sheet

| Beat | Time | One-word anchor |
| --- | --- | --- |
| 0 Hook | 0:30 | govern |
| 1 Evidence answer | 0:45 | trust |
| 2 Knowledge map | 0:45 | onboarding |
| 3 Conflict + contrast + propose | 1:00 | **differentiation** |
| 4 Approve + provenance | 0:50 | governance |
| 5 Metrics move | 0:30 | impact |
| 6 Copilot/MCP finale | 0:40 | Microsoft |
| **Total** | **~5:00** | |

---

## 6. Judging-criteria alignment (talking points)

| Likely criterion | Our strongest proof point |
| --- | --- |
| **Challenge alignment** | Hits all 5 workplace pillars + the explicit "enhance Microsoft tools" bonus (Copilot/MCP) |
| **Innovation** | "Govern, don't just answer": write-time documentation governance with evidence discipline — a loop no mainstream tool closes |
| **Technical execution** | Full pipeline live: ingestion → Librarian rewrite → pgvector retrieval → 2-agent LangGraph → governance (approve/provenance/rollback) → Insights/metrics → MCP; **413 backend tests**; runs offline |
| **Impact / business value** | Onboarding friction removed; one trusted answer; conflicts resolved on a live scoreboard |
| **Demo polish** | One clean story, 5 minutes, deterministic & offline, with a fallback recording |
| **Trust / responsibility** | Evidence-or-silence, permission-aware, human-in-the-loop, auditable + reversible |

---

## 7. Reliability & setup — do NOT skip (this is how demos are actually won)

**Your most reliable path is Presenter Mode.** The frontend ships a one-click **guided auto-pilot
demo** (the "Run guided demo" button in the header): it drives the *real* app handlers through the
scripted Garnet story above over **offline fixtures** — no Azure, no DB, no network — with on-screen
teleprompter captions + presenter cues. Transport controls: **Space** play/pause, **←/→** prev/next,
**R** restart, **C** captions, **Esc** exit. Rehearse on this; it cannot flake on Wi-Fi.

**For the live (backend-connected) path, run fully offline + deterministic** so nothing depends on
Azure or conference Wi-Fi:

```powershell
# Backend
cd backend
docker compose up -d                       # Postgres + pgvector — auto-seeds the demo corpus
$env:CHAT_PROVIDER = "fake"                 # deterministic agents, no Azure/network
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # API + Swagger at /docs
# Optional (larger OSS backdrop): python -m scripts.run_ingest --all
#   then: python -m scripts.load_vectors --all && python -m scripts.detect_conflicts --all

# Frontend
cd ../frontend
npm install
npm run build && npm run preview            # or: npm run dev  (http://localhost:5173)
```

> **Live + offline now aligned:** the auto-seed (`backend/docker/init/01-seed.sql`, regenerated by
> `backend/scripts/gen_seed.py`) plants the **same Garnet .NET 8 vs .NET 6 build conflict** (plus an
> ONNX Runtime duplicate) that Presenter Mode shows — with real embeddings, so live `/graph` +
> `/chat` and the offline fixtures tell one story. Health is derived live (build-legacy.md → red,
> install.md → yellow, install-old.md → gray); both build docs read red since both are conflict
> endpoints.

**Pre-flight checklist (run 30 min before):**
- [ ] **Presenter Mode runs clean end-to-end** (offline fixtures) — this is the primary path.
- [ ] DB up; demo corpus auto-seeded; conflict/duplicate/stale edges present (live path).
- [ ] `CHAT_PROVIDER=fake` set; hero `/chat` + `/propose` return the expected deterministic result.
- [ ] Frontend governance panels are **wired live** (Metrics, Proposal approve/reject, Provenance);
      until fully live, the UI falls back to demo fixtures (acceptable backup, but aim for live).
- [ ] Copilot CLI MCP server registered and answering (see `docs/mcp.md`).
- [ ] Browser zoom ↑, font size ↑, dark/light chosen for projector contrast.
- [ ] **Fallback screen recording** of the full 5-minute run saved locally.
- [ ] Reset path ready (restart container to re-seed / reset proposals; or just restart Presenter Mode).

**Golden rule:** if anything is flaky live, narrate over the **recording** — never debug on stage.

---

## 8. Roles during the live demo

- **Driver** (screen + clicks): rehearsed click-path only; never improvise navigation.
- **Narrator** (talks): owns the verbatim lines in §4 and the §2 objection answers.
- **Q&A lead**: fields judge questions using §2 + §9; redirects to the recording if needed.
- (Solo presenter: driver = narrator; rehearse until the click-path is muscle memory.)

---

## 9. Q&A prep — rehearsed answers

- **"Isn't this just Copilot/RAG?"** → "RAG answers at read time and will blend two conflicting
  docs. We govern at write time — detect the conflict, fix the source with evidence, human
  approval, provenance, rollback. We make Copilot's answers trustworthy; we even feed Copilot via MCP."
- **"Isn't this Confluence/Notion with AI?"** → "Those store what you type and rely on humans to
  keep docs fresh and organized. We *automatically* detect stale/duplicate/conflicting content
  against commits and propose the fix — and our **Librarian rewrites every dropped doc into a
  canonical, agent-retrievable form and re-files it** for you. The AI is the guardian *and* the
  librarian, not the human."
- **"How do you avoid the AI hallucinating a bad edit?"** → "Evidence-or-silence: no answer or
  proposal without grounded chunkIds + commit SHAs + a confidence score. Below threshold → 'needs
  human review'. And a human approves every governed write, with full rollback."
- **"Does it scale beyond engineering docs?"** → "The pipeline is content-agnostic — any
  markdown/wiki knowledge base. We demo on Microsoft OSS docs because they have real, naturally
  occurring conflicts."
- **"What's actually built vs. mocked?"** → "Ingestion, retrieval, both agents, governance,
  provenance, metrics, the verification sandbox, and the MCP server are real and tested. Auth
  principals are mocked; everything else runs."
- **"What's the business impact?"** → "Faster onboarding, fewer wrong-instruction incidents, and a
  measurable knowledge-health score leadership can track."

---

## 10. Optional high-wow stretch (only if rock-solid on the core)

- **Verification-as-trust:** run the proposed test command in the **real Docker sandbox** live →
  green "verified to run" badge on the proposal. Dramatic, but adds live risk — only if rehearsed.
- **Pillar-framed dashboard:** headline **knowledge-health / trust score** + trend sparkline mapped
  to the four pillars.
- **Permission flip:** toggle to a non-privileged principal and show the restricted node's content
  is **omitted** from the answer.

---

## Appendix A — The demo corpus (as built — reproducible detections)

The hero story runs on the **offline fixtures** in `frontend/src/lib/fixtures.ts` (what Presenter
Mode drives) — backed by the live auto-seed in `backend/docker/init/01-seed.sql`. These guarantee
the detections fire on stage; a larger OSS corpus (garnet / playwright / onnxruntime / vscode) is
the credible backdrop.

| Doc (fixtures) | Content | Expected detection | Used in |
| --- | --- | --- | --- |
| `garnet/docs/build.md` | Canonical build: **.NET 8**, `dotnet build -c Release` | `conflicts-with` (0.88) | Beat 1/3 (hero) |
| `garnet/docs/build-legacy.md` | Stale build page: **.NET 6**, old commit | **stale** → health red; orphan; 2 broken links; Curator merges → canonical | Beat 2/3 (hero) |
| `onnxruntime/docs/install.md` / `install-old.md` | near-identical install pages | `duplicate-of` (0.94) + `deprecated-by` | Beat 2/5 |
| `onnxruntime/docs/install-old.md` | restricted / no-access | **locked** (gray) node; omitted for non-privileged user | Beat 2 / stretch |

> **Live seed:** `01-seed.sql` (regenerated by `backend/scripts/gen_seed.py`) seeds this exact
> Garnet corpus with real 384-dim embeddings, so the live backend matches the fixtures. Re-run the
> generator whenever the demo corpus changes — don't hand-edit the SQL.

**Optional live beat — the Librarian:** drop a messy doc into the intake area (or `POST /documents`)
and show DocGuardian **rewrite it into an agent-friendly doc and re-file it** under an AI-chosen
category, preserving the original (`GET /original/{docId}`). This is the auto-organizing angle no
Obsidian/Notion has.

**Keep fixtures isolated, labeled, and non-sensitive — no real secrets.**

---

## Appendix B — One-screen narrative (memorize this)

1. Docs go stale and contradict each other → new hires suffer, decisions get made on bad info.
2. Copilot/RAG just *answers* over those broken docs — and hides the contradiction.
3. DocGuardian *governs* the docs: detect → evidence-backed propose → human approve → provenance → metrics.
4. The Librarian even *rewrites + re-files* every dropped doc so the library stays agent-ready.
5. Same verified knowledge, inside Copilot (MCP).
6. **Copilot answers. Obsidian stores. DocGuardian governs.**
