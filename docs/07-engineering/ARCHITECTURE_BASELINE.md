# Architecture baseline

## Decision

Memoria starts as a typed modular monolith: one FastAPI deployment, one
PostgreSQL canonical store, explicit domain boundaries, and asynchronous jobs
added only when a real workflow needs them.

## Why this shape

The product's main risk is not request throughput. It is making authority,
consent, provenance, and succession rules correct and explainable. A modular
monolith keeps transactions and audit trails coherent while avoiding the
operational cost and distributed failure modes of premature microservices.

## Initial boundaries

| Module | Owns | Must not own |
|---|---|---|
| Identity | human/account binding, assurance evidence | consent decisions |
| Consent | purpose-scoped grants and revocations | identity verification |
| Ownership | stewardship and asset authority | ownership of a human identity |
| Succession | transition evidence and successor powers | silent account takeover |
| Legacy | canonical record and immutable snapshots | derived AI state |
| Audit | append-only security and authority events | mutable business state |

The four trust modules form one policy system. No privileged action is allowed
from a role alone; it must be evaluated against identity assurance, current
consent, asset authority, lifecycle state, and evidence.

## Data and derived systems

PostgreSQL is the source of truth for identities, policy events, snapshots,
and audit metadata. Object storage will later hold encrypted media. Search
indexes, embeddings, summaries, and generative representations are derived
artifacts: they are rebuildable, versioned, revocable, and never authoritative.

## First vertical slice

The first functional slice is deliberately narrow:

1. create a synthetic subject and canonical Legacy;
2. record an identity assurance event;
3. issue a purpose-scoped consent receipt;
4. append one provenance-bearing memory item;
5. produce an immutable snapshot;
6. verify that a revocation blocks derived use without rewriting history.

The code currently supplies the runtime, database boundary, health checks, and
trust enums. The next implementation step is the authorization decision record
and the first database migration.
