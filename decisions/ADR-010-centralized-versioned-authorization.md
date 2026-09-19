# ADR-010: Centralized, versioned authorization decisions

Status: accepted

## Context

Identity, Consent, Ownership and Succession checks can drift when individual
routes implement them independently. A role check alone cannot demonstrate
current consent, sufficient identity assurance, valid rights or a permitted
Legacy lifecycle state.

## Decision

All sensitive operations use a pure Trust Kernel policy. The policy evaluates a
complete immutable request, denies by default, returns machine-readable reason
codes, and records its policy version and request fingerprint.

Every resulting decision is appended to PostgreSQL. The database rejects
updates and deletes to decision rows. Public clients do not supply trusted
policy facts directly; application services will resolve them from canonical
records.

## Consequences

- authorization behavior is testable without HTTP or database infrastructure;
- denial explanations are stable enough for audit and safe user messaging;
- historical decisions remain interpretable after policy changes;
- PostgreSQL growth and retention require an explicit later partitioning plan;
- new sensitive actions must define roles, assurance, lifecycle, rights and
  evidence requirements before implementation.
