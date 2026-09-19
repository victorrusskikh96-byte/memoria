# Trust Kernel v1

Status: implemented first vertical slice.

## Purpose

The Trust Kernel makes one explainable authorization decision across Identity,
Consent, Ownership and Succession. It does not infer permission from a role
alone and it never silently falls back to allow.

The initial implementation covers four representative sensitive actions:

| Action | Why it is included |
|---|---|
| Add text memory | Normal creator/contributor workflow |
| Export Legacy | High-impact data portability operation |
| Activate Memorial | Succession and evidence transition |
| Create synthetic voice | High-risk biometric derivative |

## Inputs

Every request records:

- actor, subject and Legacy identifiers;
- requested action and timestamp;
- actor role and Identity assurance level;
- Legacy lifecycle state;
- Consent status and receipt reference;
- rights basis and Authority Grant reference;
- succession plan, evidence, cooling period and approval threshold where needed.

IDs reference canonical records that will be implemented in later slices. A
caller cannot replace those records with a bare boolean and still obtain a
complete audit trail.

## Decision algorithm

1. Check that subject identity and subject role agree.
2. Check that the action is permitted in the current Legacy state.
3. Check role and minimum Identity assurance.
4. Check action-specific Consent and receipt evidence.
5. Require an Authority Grant for every non-subject actor.
6. Check that the asserted rights basis is sufficient for the action.
7. For Memorial activation, require a plan, verified evidence, elapsed cooling
   period and required approvals.
8. Deny when any check fails and return every applicable reason code.
9. Allow only when no denial reason exists.

## Audit contract

The decision contains:

- immutable decision and request IDs;
- `allow` or `deny` outcome;
- ordered machine-readable reason codes;
- policy version (`trust-kernel/1.0`);
- evaluation timestamp;
- SHA-256 fingerprint of canonicalized request facts.

The fingerprint detects disagreement between the facts evaluated by the policy
and the facts sent to persistence. It is not a digital signature and does not,
by itself, prove who supplied the facts.

## Persistence contract

`authorization_decisions` is append-only:

- repository code exposes append only;
- PostgreSQL rejects `UPDATE` and `DELETE` through a trigger;
- each request ID is unique;
- the original request payload and fingerprint are stored with the outcome;
- an index supports a chronological audit view per Legacy.

Operational deletion requirements will be satisfied by retention-aware
partitioning or cryptographic erasure in a later design. Application code must
not weaken append-only history with ordinary row mutation.

## Explicit limitations

This slice does not yet authenticate HTTP callers or expose a public policy
endpoint. It does not create canonical Identity, Consent Receipt, Authority
Grant, Legacy or Succession Plan tables. Those records arrive next and will be
resolved into this request by an application service; clients will never be
trusted to assert their own assurance, consent or rights.
