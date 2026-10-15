# Identity Assurance v1

Status: architecture approved for Stage 1.2; implementation partially complete
in the current feature branch. Stage 1.2 is not complete.

## 1. Purpose

Identity Assurance v1 provides the canonical, auditable answer to this
question: with what evidence-backed confidence does a particular Account
represent a particular HumanSubject?

The slice establishes immutable identity anchors, minimal evidence metadata and
an append-only assurance-event stream. It gives a future Authorization Context
Resolver a trusted source for `identity_assurance` without allowing clients to
assert their own level.

The slice reuses the existing `IdentityAssuranceLevel` A0-A3. It is deliberately
smaller than an authentication system or KYC service.

### Source precedence

The accepted ADR records the architectural decision and its rationale. This
specification defines the detailed executable contract and cannot contradict
the ADR. Architectural semantic changes are recorded through an ADR first;
behavioral clarifications within the accepted decision update this
specification and its tests.

## 2. Module boundaries

The Identity module owns:

- canonical HumanSubject and Account identifiers;
- the Account-to-HumanSubject binding;
- minimal identity-evidence metadata;
- immutable identity-evidence revocation facts;
- assurance transition history;
- deterministic effective-assurance resolution.

The authentication boundary proves control of an Account but does not decide
which HumanSubject it represents. The Trust Kernel consumes resolved immutable
facts but does not query Identity persistence. Consent, Ownership and
Succession remain separate modules.

`AuthorizationRequest.actor_id` always identifies the acting HumanSubject.
`AuthorizationRequest.subject_id` identifies the HumanSubject whose Legacy is
affected. An Account identifier is never used in either field.

## 3. Entities and relationships

| Entity | Purpose | Minimum canonical data |
|---|---|---|
| HumanSubject | Stable identifier for a real represented person | UUID, creation time |
| Account | Authentication principal without credentials | UUID, authority, opaque external reference, creation time |
| AccountHumanSubjectBinding | Immutable assertion of which person an Account represents | UUID, Account UUID, HumanSubject UUID, creation time |
| IdentityEvidence | Minimal metadata for a trusted external verification result | UUID, binding, kind, provider, opaque reference, observed/expiry/recorded times |
| IdentityEvidenceRevocation | Immutable withdrawal of one evidence item | UUID, evidence UUID, binding UUID, revocation/recorded times, reason, idempotency key, schema version |
| IdentityAssuranceEvent | Append-only transition in one binding's assurance stream | UUID, binding, version, kind, levels, validity, fallback, policy version |
| EffectiveIdentityAssurance | Computed resolution result, not stored mutable state | Account, HumanSubject, binding, level, source event, validity, resolution time |

One Account has at most one HumanSubject binding. One HumanSubject may have
multiple Accounts. Access to another person's Legacy is represented by an
Authority Grant rather than another identity binding.

Binding establishment is one database transaction containing the binding, at
least one evidence record, the first `ESTABLISHED` event at stream version 1,
and the event-to-evidence link. A binding without that event must never be
committed.

## 4. State transitions

| Event | Required previous state | Result | May follow later |
|---|---|---|---|
| `ESTABLISHED` | No prior event; new binding | Policy-derived A1 or A2 | Upgrade, refresh, downgrade or revoke |
| `UPGRADED` | Effective lower level, including A0; A3 requires current A2 | Higher level | Upgrade, refresh, downgrade or revoke |
| `REFRESHED` | Effective positive level | Same positive level with renewed evidence or validity | Upgrade, refresh, downgrade or revoke |
| `DOWNGRADED` | Effective higher level | Lower level, including A0 | Server-side reassessment or revoke |
| `REVOKED` | Any non-revoked binding | A0 and terminal binding | Nothing in v1 |

`DOWNGRADED` to A0 means the Account-to-HumanSubject identity is still known,
but current evidence is insufficient. `REVOKED` means the binding itself is no
longer trusted. No event may be appended after revocation. Repair requires a
future correction/rebinding workflow.

Only A1 or A2 may be created by `ESTABLISHED`; A3 is never the first event.
`UPGRADED` is allowed after `DOWNGRADED` to A0. A transition to A3 is allowed
only from a currently effective A2. `REVOKED` remains terminal.

## 5. Evidence-to-level policy

| Assurance | Required evidence | Additional rule |
|---|---|---|
| A0 | No sufficient active evidence | Represents a resolved but currently unassured binding |
| A1 | `ACCOUNT_CHANNEL_VERIFICATION` | Computed only by server policy |
| A2 | `DOCUMENT_CHECK` or `TRUSTED_VOUCH` | Supporting evidence must be valid at event start |
| A3 | `STEP_UP_VERIFICATION` and `INDEPENDENT_CHECK` | Different providers; maximum evidence-policy lifetime of 24 hours |

The canonical v1 policy version is `identity-evidence/1.0`. Its rules are
immutable. A semantic rule change requires a new policy version; an existing
version is never reinterpreted retroactively. The application service derives
the level from trusted evidence; public or provider-facing client DTOs do not
accept a target level.

Evidence Policy has exactly these responsibilities:

- determine the maximum A0-A3 level supported by evidence;
- select the supporting evidence;
- calculate `maximum_expires_at`.

It does not accept `prior_effective_level`, validate the event stream, validate
the A2 to A3 transition or `fallback_event_id`, or create an
IdentityAssuranceEvent. A3 may become an assurance event only from an effective
A2 state and with an explicit fallback to an effective A2 event from the same
binding. The future stream transition validator, not Evidence Policy, owns
those requirements.

The allowed `(provider, IdentityEvidenceKind)` pairs and supported evidence and
revocation `schema_version` values are immutable server-side rules within the
policy version. Wildcard providers are prohibited. An unknown provider or an
unsupported provider-kind pair cannot increase assurance, but its presence
alone does not make the whole input invalid. V1 does not define concrete
external provider names.

`observed_at` is the only canonical provider timestamp in v1. There is no
`issued_at`.

The complete Evidence Policy input is structurally invalid if it contains:

- a duplicate evidence ID;
- a duplicate revocation ID;
- evidence from another binding;
- a revocation from another binding;
- a revocation referring to unknown evidence;
- an unsupported evidence or revocation `schema_version`;
- an unknown runtime enum;
- invalid temporal data.

Structural invalidity fails closed and is not ordinary A0. Expired, revoked or
not-yet-available evidence and unsupported provider pairs are ineligible for
assurance but do not by themselves invalidate the complete input.

Structural validity is checked before candidate filtering or level selection;
any structural invalidity stops the computation. After that check, evidence
may participate only if it simultaneously:

- belongs to the required binding;
- has a supported `schema_version`;
- has an allowed `(provider, IdentityEvidenceKind)` pair;
- has `observed_at <= as_of`;
- has no `expires_at` or has `as_of < expires_at`;
- has no related revocation with `revoked_at <= as_of`.

At `as_of == expires_at`, evidence is expired. The input collection order
cannot affect the result.

The canonical rank of one eligible evidence item is:

1. `expires_at=None` ahead of every finite expiry, otherwise the later
   `expires_at`;
2. the later `observed_at`;
3. the lower UUID.

For A1, select the single highest-ranked `ACCOUNT_CHANNEL_VERIFICATION`
candidate.

`DOCUMENT_CHECK` and `TRUSTED_VOUCH` are alternative grounds for A2; both are
not required. First select the highest-ranked candidate within each available
kind. If both kinds are available, select one final supporting item by:

1. `expires_at=None` ahead of every finite expiry, otherwise the later
   `expires_at`;
2. the later `observed_at`;
3. the earlier declaration position in IdentityEvidenceKind;
4. the lower UUID.

For A3, consider every cross-kind pair containing one eligible
`STEP_UP_VERIFICATION` and one eligible `INDEPENDENT_CHECK` with different
`provider` values. Do not merely pair the two independently highest-ranked
items. For each permissible pair, `maximum_expires_at` is the earliest of
`as_of + 24 hours` and the finite `expires_at` values of both items. Select the
pair by:

1. the later `maximum_expires_at`;
2. the canonical rank of its `STEP_UP_VERIFICATION` evidence;
3. the canonical rank of its `INDEPENDENT_CHECK` evidence;
4. the lexicographically lower tuple of supporting UUIDs after ordering them by
   IdentityEvidenceKind and then UUID.

This exhaustive comparison allows a lower-ranked individual item to win when
it forms the best permissible pair. If eligible evidence from both A3 kinds is
present but no cross-provider pair exists, A3 is not achieved and the policy
continues its ordinary A2 and then A1 evaluation. `STEP_UP_VERIFICATION` and
`INDEPENDENT_CHECK` alone do not support A2 or A1. No permissible A3 pair is
ordinary insufficient evidence for A3, not structural invalidity, and no new
structural-invalid reason code is introduced.

For A1 and A2, `maximum_expires_at` is the selected supporting item's finite
expiry, or absent when that item is unbounded. Supporting evidence IDs for
every result, including A3, are returned in stable order by
IdentityEvidenceKind and then UUID.

## 6. Effective assurance algorithm

Resolution accepts an Account and timezone-aware `as_of` instant.

1. Resolve the Account and its unique binding.
2. Require an event stream beginning with `ESTABLISHED` at version 1.
3. Validate continuous versions, transition invariants and terminal state.
4. Select the latest event effective at `as_of`.
5. If it is `REVOKED`, fail closed before TrustPolicy.
6. If it is not expired, return its resulting level and provenance.
7. If an A3 event is expired, resolve its required explicit fallback chain.
8. If an A1 or A2 event is expired, return effective A0.
9. If a required or referenced fallback is invalid, fail closed.

The result includes Account, HumanSubject and binding IDs, effective level,
source event, validity boundary and resolution time. It is immutable and does
not become a mutable current-level database row.

An absent Account or binding does not produce A0: the acting HumanSubject cannot
be established, so resolution stops before TrustPolicy. The same applies to a
revoked binding or corrupted stream.

## 7. Fallback behavior

Evidence Policy does not accept, produce or validate fallback information. A1
and A2 have no fallback. A3 requires an explicit fallback, which is validated
only by the future stream transition validator rather than by Evidence Policy.

An A3 fallback:

- refers only to an earlier event in the same binding;
- must be effective and unexpired at resolution time;
- cannot cross a revocation;
- must not form a cycle;
- is required for A3 and points to a valid A2 event.

At `as_of >= expires_at`, an A3 event is expired. The resolver follows its
fallback and validates that event using the same rules. An expired A1 or A2
event resolves directly to A0. An A3 fallback that is missing, cross-binding,
cyclic or structurally invalid is corrupted state and fails closed. A valid
fallback event that has itself expired is evaluated recursively and may
ultimately resolve to A0.

## 8. Failure posture

Resolution fails closed before TrustPolicy for:

- missing Account;
- missing binding;
- binding without events;
- revoked binding;
- unknown enum value;
- missing, duplicate or discontinuous stream version;
- invalid transition or terminal-state violation;
- corrupted fallback chain;
- cross-binding evidence or fallback;
- structurally invalid evidence-policy input;
- inconsistent level or evidence policy result.

These cases are observability and integrity incidents, not normal A0
authorization requests. A0 reaches TrustPolicy only when the actor binding is
reliably known but its effective assurance is insufficient because of expiry or
downgrade.

## 9. Persistence contract

This section defines a target contract; Identity Assurance persistence has not
been implemented. PostgreSQL is the canonical store. The proposed tables are:

- `human_subjects`;
- `accounts`;
- `account_human_subject_bindings`;
- `identity_evidence`;
- `identity_assurance_events`;
- `identity_assurance_event_evidence`.

Canonical IDs are UUIDs. Account uniqueness is
`(authentication_authority, external_subject_reference)`. Evidence uniqueness
is `(provider, opaque_reference)`. Binding enforces at most one HumanSubject per
Account. Stream versions are unique per binding and `idempotency_key` is
globally unique.

Assurance append uses `expected_stream_version`. Versions start at 1 and remain
continuous. `previous_level` must equal the effective level immediately before
append. Positive events require supporting evidence, and the database must
prevent cross-binding event/evidence relationships.

The following are immutable and append-only in v1:

- `account_human_subject_bindings`;
- `identity_evidence`;
- `identity_assurance_events`;
- `identity_assurance_event_evidence`.

Repositories expose only append and read operations. PostgreSQL rejects
`UPDATE` and `DELETE` with row-level triggers and rejects `TRUNCATE` with a
separate statement-level trigger. Foreign keys use `ON DELETE RESTRICT`.
Separate runtime and migration roles are future hardening.

IdentityEvidenceRevocation is a canonical immutable domain fact. Its physical
persistence representation must be append-only and protected from `UPDATE` and
`DELETE`. A concrete table or event-store representation has not been selected;
its absence from the proposed table list is a deliberate deferral to the
persistence design stage. No physical representation is approved by this
specification. The persistence design, migrations, and database constraints
for Identity Assurance remain future work.

## 10. Time and privacy contract

Every datetime is timezone-aware and canonically represented in UTC.
`effective_at` is supplied by the application service using an injected clock.
PostgreSQL assigns `recorded_at`. Provider `observed_at` is the only canonical
provider timestamp in v1; `issued_at` is not stored. `observed_at` records
evidence provenance and never starts or backdates an assurance event.
Client-provided backdating is prohibited.

IdentityEvidence is immutable and never receives a mutable `revoked_at` field.
Withdrawal is recorded as a separate immutable IdentityEvidenceRevocation with
these fields:

- `id`: UUID;
- `evidence_id`: UUID;
- `binding_id`: UUID;
- `revoked_at`: timezone-aware datetime;
- `reason_code`: safe bounded string;
- `idempotency_key`: UUID;
- `recorded_at`: timezone-aware datetime;
- `schema_version`: printable bounded string.

A new verification or restoration of trust creates a new IdentityEvidence. It
does not delete, update or reverse the revocation fact.

`authentication_authority` and `provider` are 1-64 character lowercase ASCII
identifiers matching `^[a-z0-9][a-z0-9._-]{0,63}$`.

`external_subject_reference` and `opaque_reference` are 1-255 character values
matching `^[A-Za-z0-9._:|~-]{1,255}$`. Spaces, control characters and `@` are
prohibited, so an email address is not accepted as an opaque reference. Each
value must be a stable opaque provider identifier and must not contain an email
address, telephone number, document number or other directly entered PII. DTOs
do not heuristically recognize telephone or document numbers because a numeric
opaque identifier may be legitimate. The provider adapter is responsible for
converting provider-specific identity into an allowed opaque reference.

`reason_code` is a 1-64 character lowercase ASCII slug matching
`^[a-z0-9][a-z0-9._-]{0,63}$`. `schema_version` and
`assurance_policy_version` are each 1-64 printable ASCII characters with no
leading or trailing spaces.

Opaque references are pseudonymous identifiers, not anonymous data. They must
not appear in policy decisions, reason messages, exceptions, `repr` output,
ordinary application logs or analytics. They may be stored only in the
canonical Identity store and in access-restricted security audit records. A
keyed digest remains future hardening after a managed secret boundary exists.

The identity store does not contain passwords, password hashes, tokens, MFA or
recovery secrets, raw documents, document numbers, selfie/video, biometric
templates, provider payloads or arbitrary metadata JSONB.

## 11. Future Authorization Context Resolver integration

The future resolver will:

1. receive an authenticated Account from a separate authentication boundary;
2. resolve its canonical Account-to-HumanSubject binding;
3. calculate effective assurance at the request time;
4. use the binding's HumanSubject as `AuthorizationRequest.actor_id`;
5. resolve the represented HumanSubject as `AuthorizationRequest.subject_id`;
6. resolve Consent, Authority, Legacy and Succession facts from their modules;
7. construct one immutable request for the pure TrustPolicy.

Unbound, revoked or corrupted identities stop before policy evaluation. A later
audit-envelope extension may persist Account, binding and source-event IDs, but
neither the resolver nor that extension is implemented in Stage 1.2.

## 12. Explicit non-goals

Identity Assurance v1 does not implement:

- an authentication protocol;
- HTTP endpoints;
- raw KYC or document storage;
- biometrics;
- subject duplicate detection or merge;
- binding correction or rebinding;
- Consent;
- Ownership;
- Succession;
- AuthorizationContextResolver;
- authorization audit-envelope expansion;
- separate runtime and migration database roles;
- retention or cryptographic erasure.

## 13. Current implementation status

Implemented in the current feature branch:

- canonical Identity domain entities;
- the immutable IdentityEvidenceRevocation domain fact;
- runtime validation of `IdentityEvidence.kind`;
- immutable Evidence Policy contract types;
- policy version `identity-evidence/1.0`;
- `IdentityEvidencePolicyV1.evaluate`;
- deterministic A1, A2, and A3 evidence selection;
- the provider-kind allowlist contract and cross-provider A3;
- revocation filtering;
- privacy-safe policy decisions and errors;
- unit tests for the implemented entities and Evidence Policy behavior.

Still pending:

- a stream-wide transition validator;
- terminal `REVOKED` stream enforcement;
- fallback-chain validation;
- the effective assurance resolver;
- application services;
- repository ports and adapters;
- SQLAlchemy persistence;
- Alembic migrations;
- PostgreSQL constraints;
- database integration tests;
- the HTTP API.

## 14. Implementation completion criteria

Implementation may be considered complete only when:

- all canonical entities use UUIDs and validated UTC-aware datetimes;
- binding establishment is atomic and cannot leave an eventless binding;
- the v1 evidence policy is deterministic, versioned and server-controlled;
- evidence revocation is an immutable fact rather than a mutable evidence
  field;
- every transition and stream invariant is enforced by domain code and
  appropriate PostgreSQL constraints;
- Evidence Policy enforces the A3 evidence combination, distinct providers and
  24-hour `maximum_expires_at`;
- the stream transition validator enforces the A3 effective-A2 origin and
  mandatory explicit fallback;
- expiry and fallback resolve deterministically without a background job;
- binding revocation is terminal and downgrade-to-A0 remains reassessable;
- repository APIs expose no mutation of immutable history;
- PostgreSQL rejects update, delete and truncate on append-only tables;
- unit tests cover policy, transitions, time boundaries and corrupted streams;
- integration tests cover atomic establishment, concurrency, constraints and
  database mutation protection;
- TrustPolicy remains pure and no public identity endpoint is added.
