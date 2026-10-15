# Implementation roadmap

## Stage 0 — development foundation (now)

- Windows audit and repeatable bootstrap;
- Python 3.13, uv, FastAPI, PostgreSQL, Alembic;
- linting, strict typing, tests, and CI;
- no production data and no generative persona.

Exit: a new workstation can run the API and all checks from documented commands.

## Stage 1 — trust kernel

### Stage 1.1 — Trust Kernel authorization decisions — implemented

- centralized, versioned and deny-by-default authorization decisions;
- canonical request IDs, reason codes and request fingerprints;
- append-only PostgreSQL authorization decision records.

### Stage 1.2 — Canonical Identity and Assurance Evidence — current, partially implemented

Completed or implemented in the current feature branch:

- approved Identity architecture and executable domain specification;
- canonical domain entities;
- immutable IdentityEvidenceRevocation domain fact;
- deterministic Evidence Policy V1;
- unit tests and privacy protections for the implemented slice.

Pending:

- stream transition validator;
- terminal `REVOKED` stream enforcement;
- fallback-chain validation;
- effective assurance resolver;
- application services and repository ports;
- SQLAlchemy persistence;
- Alembic migrations and PostgreSQL constraints;
- database integration tests;
- API layer.

### Stage 1.3 — Consent Receipts

- purpose- and scope-bound receipts;
- expiry, review and revocation behavior;
- immutable consent history.

### Stage 1.4 — Rights and Authority Grants

- resource rights and stewardship basis;
- narrow, time-bounded Authority Grants;
- explicit separation of control, permission and ownership.

### Stage 1.5 — Succession Plans and Activation Evidence

- creator-authored succession plans;
- activation evidence, cooling periods and approval thresholds;
- append-only lifecycle transition records.

### Stage 1.6 — synthetic end-to-end trust scenario

- resolve canonical Identity, Consent, Rights and Succession facts;
- produce and persist one centralized authorization decision;
- test allowed and denial paths across the complete trust context.

Exit: the first synthetic end-to-end trust scenario is tested, including denial paths.

## Stage 2 — capture and provenance

- guided memory capture;
- contributor claims and subject review;
- evidence hierarchy and conflict representation;
- encrypted object metadata and retention rules;
- exportable canonical package.

Exit: a subject can create, review, export, and delete a small legacy safely.

## Stage 3 — family experience

- invitations and relationship-scoped access;
- memorial transition workflow;
- steward and successor console;
- dispute, hold, and appeal flows;
- accessibility and recovery testing.

Exit: a multi-person synthetic family can exercise lifecycle transitions without silent authority changes.

## Stage 4 — derived intelligence

- consent-bound retrieval and summarization;
- model/version provenance on every output;
- visible uncertainty and source links;
- deterministic shutdown and rebuild of derived artifacts.

Exit: generated responses are traceable, revocable, and clearly separated from human-authored memory.

## Deferred beyond validated demand

- real-time cloned avatar;
- autonomous posting or messaging in a person's name;
- tokenization or tradeable identity rights;
- opaque proprietary export formats;
- multi-region microservice architecture.
