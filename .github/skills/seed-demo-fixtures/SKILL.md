---
name: seed-demo-fixtures
description: >-
  Generate planted documentation fixtures — obvious stale, duplicate, and
  conflicting docs — so the DocGuardian demo reliably triggers detection, proposal,
  and approval flows. USE WHEN the user wants to "seed demo data", "create demo
  fixtures", "plant a conflict", "make the demo reproducible", or prepare the
  end-to-end walkthrough. Produces controlled examples plus an expected-outcome note.
---

# Seed Demo Fixtures (planted stale / duplicate / conflict)

A hackathon demo must be reproducible. Live corpora are noisy, so this skill plants
a few **obvious, controlled** problems that exercise the full pipeline:
detect → propose → evidence/confidence → approve → provenance → metrics.

## When to use

- Preparing or rehearsing the 9-step demo (`README.md` §11).
- You need a guaranteed duplicate/conflict the agents will catch on stage.

## When NOT to use

- For production behavior — these are demo-only fixtures; keep them clearly labeled
  and outside the authoritative corpus.

## What to plant

Create fixtures under a clearly named demo folder (e.g. `data/_demo/`), each a small
markdown doc with real-looking build/test instructions.

### 1. A duplicate pair (triggers `duplicate-of`, score ≥ 0.92)

Two docs describing the **same** workflow in near-identical words (e.g. two
"Running the tests" pages). Expectation: retrieval flags a `duplicate-of` edge and
the Curator proposes `merge` or `link`.

### 2. A conflict pair (triggers `conflicts-with`, score ≥ 0.85 + divergent commands)

Two docs that are highly similar **but give different commands** for the same task,
e.g. one says:

```
Run `yarn` then `yarn watch`.
```

and the other says:

```
Run `npm ci` then `npm run watch`.
```

Expectation: conflict detected; Curator drafts a merged canonical version; Guardian
judges with evidence + confidence; human approves via the diff panel.

### 3. A stale doc (triggers stale / health = red)

A doc whose `lastVerifiedSha` differs from `currentCommitSha` (or references an old
command/version). Expectation: node colored red, surfaced in metrics "stale detected".

## Output

For each planted fixture, also write an **expected-outcome** note (a comment or a
sibling `expected.md`) capturing: which detection should fire, the proposed action,
the rough confidence band, and the metric it should move. This makes the demo
verifiable and lets checks confirm the flow still works.

## Safety

- Keep planted fixtures isolated and labeled; never mix them into the real ingested
  corpus used for genuine validation.
- Use realistic but non-sensitive content; no secrets or credentials in fixtures.
