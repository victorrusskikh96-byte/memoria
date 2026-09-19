# Identity Assurance v1

Status: architecture approved for Stage 1.2; implementation pending.

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

## 2. Module boundaries

The Identity module owns:

- canonical HumanSubject and Account identifiers;
- the Account-to-HumanSubject binding;
- minimal identity-evidence metadata;
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
| A3 | `STEP_UP_VERIFICATION` and `INDEPENDENT_CHECK` | Only from active A2; maximum 24 hours; explicit A2 fallback |

The policy is versioned. The application service derives the level from trusted
evidence; public or provider-facing client DTOs do not accept a target level.

A3 always has `expires_at`, cannot outlive either supporting evidence item, and
references an effective A2 event from the same binding. A1 and A2 may be
unbounded, but when supporting evidence expires the event cannot extend beyond
that expiry.

## 6. Effective assurance algorithm

Resolution accepts an Account and timezone-aware `as_of` instant.

1. Resolve the Account and its unique binding.
2. Require an event stream beginning with `ESTABLISHED` at version 1.
3. Validate continuous versions, transition invariants and terminal state.
4. Select the latest event effective at `as_of`.
5. If it is `REVOKED`, fail closed before TrustPolicy.
6. If it is not expired, return its resulting level and provenance.
7. If expired, resolve its explicit fallback chain when one is permitted.
8. If no fallback is defined and none is required, return effective A0.
9. If a required or referenced fallback is invalid, fail closed.

The result includes Account, HumanSubject and binding IDs, effective level,
source event, validity boundary and resolution time. It is immutable and does
not become a mutable current-level database row.

An absent Account or binding does not produce A0: the acting HumanSubject cannot
be established, so resolution stops before TrustPolicy. The same applies to a
revoked binding or corrupted stream.

## 7. Fallback behavior

Fallback is explicit rather than an implicit search for the highest historical
level. A fallback:

- refers only to an earlier event in the same binding;
- must be effective and unexpired at resolution time;
- cannot cross a revocation;
- must not form a cycle;
- is required for A3 and points to a valid A2 event.

At `as_of >= expires_at`, the event is expired. The resolver follows the
fallback and validates that event using the same rules. An otherwise valid
event with no defined or required fallback resolves to A0. A required or
referenced fallback that is missing, cross-binding, cyclic or structurally
invalid is corrupted state and fails closed. A valid fallback event that has
itself expired is evaluated recursively and may ultimately resolve to A0.

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
- inconsistent level or evidence policy result.

These cases are observability and integrity incidents, not normal A0
authorization requests. A0 reaches TrustPolicy only when the actor binding is
reliably known but its effective assurance is insufficient because of expiry or
downgrade.

## 9. Persistence contract

PostgreSQL is the canonical store. The proposed tables are:

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

## 10. Time and privacy contract

Every datetime is timezone-aware and canonically represented in UTC.
`effective_at` is supplied by the application service using an injected clock.
PostgreSQL assigns `recorded_at`. Provider `observed_at` is evidence provenance
and never backdates assurance. Client-provided backdating is prohibited.

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
not appear in ordinary application logs, error messages or analytics. They may
be stored only in the canonical Identity store and in access-restricted
security audit records. A keyed digest remains future hardening after a managed
secret boundary exists.

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

## 13. Implementation readiness criteria

Implementation may be considered complete only when:

- all canonical entities use UUIDs and validated UTC-aware datetimes;
- binding establishment is atomic and cannot leave an eventless binding;
- the v1 evidence policy is deterministic, versioned and server-controlled;
- every transition and stream invariant is enforced by domain code and
  appropriate PostgreSQL constraints;
- A3 enforces its A2 origin, evidence combination, fallback and 24-hour limit;
- expiry and fallback resolve deterministically without a background job;
- revocation is terminal and downgrade-to-A0 remains reassessable;
- repository APIs expose no mutation of immutable history;
- PostgreSQL rejects update, delete and truncate on append-only tables;
- unit tests cover policy, transitions, time boundaries and corrupted streams;
- integration tests cover atomic establishment, concurrency, constraints and
  database mutation protection;
- TrustPolicy remains pure and no public identity endpoint is added.
