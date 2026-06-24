---
name: contract-sync
description: >-
  Keep DocGuardian's data contracts in sync across layers by changing a Pydantic
  model (backend/app/models) and its mirrored TypeScript interface
  (frontend/src/lib/types.ts) together. USE WHEN the user adds or changes a data
  contract (RawDocument, DocChunk, GraphEdge, AgentProposal, ChatAnswer,
  DocumentRecord, ProvenanceEntry, GraphDTO, MetricsDTO, etc.) and wants backend +
  frontend types to match. DIRECTOR-LEVEL change — contracts are otherwise frozen.
---

# Contract Sync (Pydantic ⇄ TypeScript)

The data contracts in `README.md` §8A are the frozen interface between the five
layers and the four engineers. This skill makes a contract change in **one place**
and mirrors it everywhere so the camelCase JSON shape stays identical.

## When to use

- The `director` is adding or evolving a data contract.
- A field's name/type/optionality must change across backend and frontend together.

## When NOT to use

- For ordinary feature work inside an engineer's owned slice — those consume the
  contracts but never change them. Route contract changes through the `director`.

## Procedure

### 1. Locate the canonical schema

Find the contract's JSON example in `README.md` §8A. The README field names
(camelCase: `docId`, `commitSha`, `headingPath`, `riskLevel`) are authoritative.

### 2. Update the Pydantic v2 model

In `backend/app/models/`, define/edit the model so its serialized JSON is camelCase
and it accepts both snake_case and camelCase input:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class DocChunk(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    chunk_id: str
    doc_id: str
    heading_path: list[str]
    token_count: int
    # ... match every field from the README example
```

### 3. Mirror the TypeScript interface

In `frontend/src/lib/types.ts`, write the matching interface with identical
camelCase keys and equivalent types (`str→string`, `int|float→number`,
`list[X]→X[]`, `Optional[X]→X | null`, nested models → nested interfaces):

```ts
export interface DocChunk {
  chunkId: string;
  docId: string;
  headingPath: string[];
  tokenCount: number;
  // ... identical shape to the Pydantic model
}
```

### 4. Update fixtures and verify

- Update any sample fixtures (`backend/app/fixtures/`, `frontend/src/lib/fixtures.ts`)
  that instantiate the changed contract.
- Verify both sides: `cd backend && pytest -q` (the model validates the README
  example) and `cd frontend && npx tsc --noEmit`.
- Announce the change to the affected engineers/agents.

## Rules

- **Names match exactly** — a mismatch silently breaks serialization between layers.
- Prefer additive, backward-compatible changes mid-build; coordinate breaking
  changes through the `director`.
- Never edit only one side.
