# ADR-011: Canonical Identity and Assurance Evidence

Status: accepted for Stage 1.2

## Context

Memoria must distinguish authentication of an Account from evidence that the
Account represents a particular human. Collapsing both concepts into an Account
flag or a Human Subject flag would lose provenance, prevent different accounts
for one person from carrying different assurance, and allow mutable state to
replace an auditable history.

The Trust Kernel already uses `IdentityAssuranceLevel` A0-A3. Stage 1.2 defines
the canonical source from which a future Authorization Context Resolver will
obtain that fact. It does not implement an authentication protocol, public API,
or a complete identity-verification service.

## Implementation status

Stage 1.2 is in progress and is not complete. The current feature branch
implements the canonical Identity domain entities, including the immutable
IdentityEvidenceRevocation fact and runtime validation of
`IdentityEvidence.kind`. It also implements immutable Evidence Policy contract
types, policy version `identity-evidence/1.0`,
`IdentityEvidencePolicyV1.evaluate`, deterministic A1/A2/A3 selection, the
provider-kind allowlist contract, cross-provider A3, revocation filtering,
privacy-safe decisions and errors, and unit tests.

The stream-wide transition validator, terminal `REVOKED` stream enforcement,
fallback-chain validation, effective assurance resolver, application services,
repository ports and adapters, SQLAlchemy persistence, Alembic migrations,
PostgreSQL constraints, database integration tests, and HTTP API remain
unimplemented.

## Source precedence

This accepted ADR defines the architectural decision and its rationale. The
Identity Assurance domain specification defines the detailed executable
contract and must not contradict this ADR. A change to architectural semantics
is recorded in an ADR first; a behavioral clarification within the accepted
decision updates the domain specification and its tests.

## Decision

Identity assurance belongs to a specific immutable binding:

`Account <-> HumanSubject`

Assurance is not a field of either Account or HumanSubject. It is derived from
append-only Identity Assurance Events supported by minimal Identity Evidence
metadata.

The canonical entities are:

- HumanSubject;
- Account;
- AccountHumanSubjectBinding;
- IdentityEvidence;
- IdentityEvidenceRevocation;
- IdentityAssuranceEvent;
- EffectiveIdentityAssurance, which is a computed value and not mutable stored
  state.

The existing `IdentityAssuranceLevel` A0-A3 is the only assurance-level type.

## Identifier semantics

- `account_id` identifies an authentication principal.
- `human_subject_id` identifies the real represented person.
- `AuthorizationRequest.actor_id` is the HumanSubject of the acting person.
- `AuthorizationRequest.subject_id` is the HumanSubject whose Legacy is
  affected.
- `account_id` is never substituted for `actor_id`.

An authorization audit may later record Account, binding and assurance-event
provenance in addition to `actor_id`, but that audit-envelope extension is not
part of Stage 1.2.

## Cardinality and establishment

One Account is bound to at most one HumanSubject. One HumanSubject may have
multiple Accounts. Authority to manage another person's Legacy is represented
by an Authority Grant, not by an additional identity binding.

A binding is established atomically with all of the following:

- its first IdentityEvidence record;
- its first IdentityAssuranceEvent, whose kind is `ESTABLISHED` and whose
  `stream_version` is 1;
- the event-to-evidence relationship.

A committed binding without its first assurance event is an invalid state.

## Stored data boundary

Account and evidence records contain only bounded opaque provider identifiers
and the minimum metadata needed for provenance, validity and resolution.

Memoria does not store in this slice:

- passwords or password hashes;
- access or refresh tokens;
- MFA or recovery secrets;
- document images or document numbers;
- selfie or video captures;
- biometric templates;
- provider payloads;
- arbitrary metadata JSONB.

`authentication_authority` and `provider` are 1-64 character lowercase ASCII
identifiers matching `^[a-z0-9][a-z0-9._-]{0,63}$`.

`external_subject_reference` and `opaque_reference` are 1-255 character
provider identifiers matching `^[A-Za-z0-9._:|~-]{1,255}$`. Spaces, control
characters and `@` are prohibited, so an email address is not accepted as an
opaque reference. These values must be stable opaque provider identifiers and
must not contain an email address, telephone number, document number or other
directly entered PII. DTO validation does not heuristically recognize telephone
or document numbers because a numeric opaque identifier may be legitimate. The
provider adapter is responsible for converting provider-specific identity into
an allowed opaque reference.

`reason_code` is a 1-64 character lowercase ASCII slug matching
`^[a-z0-9][a-z0-9._-]{0,63}$`. `schema_version` and
`assurance_policy_version` are each 1-64 printable ASCII characters with no
leading or trailing spaces.

An IdentityEvidence record remains immutable after creation and does not gain a
mutable `revoked_at` field. Evidence withdrawal is represented by a separate
immutable IdentityEvidenceRevocation fact containing:

- `id`: UUID;
- `evidence_id`: UUID;
- `binding_id`: UUID;
- `revoked_at`: timezone-aware datetime;
- `reason_code`: safe bounded string;
- `idempotency_key`: UUID;
- `recorded_at`: timezone-aware datetime;
- `schema_version`: printable bounded string.

A new verification or restoration of trust creates a new IdentityEvidence
record. It never removes or reverses an earlier revocation fact.

Opaque references are pseudonymous identifiers, not anonymous data. They must
not appear in policy decisions, reason messages, exceptions, `repr` output,
ordinary application logs or analytics. They may be stored only in the
canonical Identity store and in access-restricted security audit records.

Account identity is unique by
`(authentication_authority, external_subject_reference)`. Evidence is unique
by `(provider, opaque_reference)`. A keyed digest is deferred until Memoria has
a managed secret boundary and remains future hardening.

## Evidence policy v1

The canonical policy version is `identity-evidence/1.0`. Its rules are
immutable. Any semantic rule change requires a new policy version; an existing
version must never be reinterpreted retroactively.

The versioned server-side policy recognizes these evidence kinds:

| Evidence | Supported assurance |
|---|---|
| `ACCOUNT_CHANNEL_VERIFICATION` | A1 |
| `DOCUMENT_CHECK` or `TRUSTED_VOUCH` | A2 |
| `STEP_UP_VERIFICATION` and `INDEPENDENT_CHECK` together | A3 |

The application service computes the level. A client DTO never contains a
target assurance level.

Evidence Policy determines the maximum A0-A3 level supported by evidence,
selects the supporting evidence and calculates `maximum_expires_at`. It does
not accept a prior effective level, validate an event stream, validate the A2
to A3 transition or `fallback_event_id`, or create an IdentityAssuranceEvent.
The future stream transition validator owns those checks.

The allowed `(provider, IdentityEvidenceKind)` pairs and supported evidence and
revocation schema versions are immutable rules belonging to the policy
version. Wildcard providers are prohibited. An unknown provider or unsupported
provider-kind pair does not increase assurance, but its presence alone does not
make the entire input invalid. V1 does not name any concrete external provider.

`observed_at` is the only canonical provider timestamp in v1; `issued_at` is
not part of the model.

The entire policy input is structurally invalid for a duplicate evidence ID,
duplicate revocation ID, cross-binding evidence, cross-binding revocation,
revocation of unknown evidence, unsupported `schema_version`, unknown runtime
enum or invalid temporal data. Structural invalidity fails closed and is not
reduced to ordinary A0. Unsupported providers and unsupported provider-kind
pairs are ineligible evidence, not structural invalidity.

Structural validity is checked before filtering candidates or selecting a
level, and any structural invalidity stops the computation. After that check,
an evidence item may participate in selection only when all of the following
are true:

- it belongs to the required binding;
- its `schema_version` is supported;
- its `(provider, IdentityEvidenceKind)` pair is allowed;
- `observed_at <= as_of`;
- `expires_at` is absent or `as_of < expires_at`;
- no related revocation has `revoked_at <= as_of`.

Thus future, expired and revoked evidence is ineligible. At
`as_of == expires_at`, evidence is expired. Input collection order never
affects the result.

The canonical rank of one eligible evidence item is, in order:
`expires_at=None` ahead of every finite expiry; otherwise the later
`expires_at`; then the later `observed_at`; then the lower UUID.

For A1, the policy selects the single highest-ranked
`ACCOUNT_CHANNEL_VERIFICATION` candidate.

`DOCUMENT_CHECK` and `TRUSTED_VOUCH` are alternative grounds for A2; A2 does
not require both. The policy first selects the highest-ranked candidate within
each available kind. If both kinds are available, it selects one final
supporting item by, in order: `expires_at=None` ahead of every finite expiry;
otherwise the later `expires_at`; the later `observed_at`; the earlier
declaration position in IdentityEvidenceKind; and the lower UUID.

For A3, the policy considers every cross-kind pair containing one eligible
`STEP_UP_VERIFICATION` and one eligible `INDEPENDENT_CHECK` whose `provider`
values differ. It must not merely pair the two independently highest-ranked
items. For each permissible pair, `maximum_expires_at` is the earliest of
`as_of + 24 hours` and the finite `expires_at` values of both items. The policy
selects the pair by, in order: the later `maximum_expires_at`; the canonical
rank of its `STEP_UP_VERIFICATION`; the canonical rank of its
`INDEPENDENT_CHECK`; and the lexicographically lower tuple of supporting UUIDs
after ordering them by IdentityEvidenceKind and then UUID. This exhaustive pair
selection ensures that a lower-ranked individual item can be selected when it
forms the best permissible pair.

If eligible evidence from both A3 kinds is present but no cross-provider pair
exists, A3 is not achieved. The policy continues its ordinary A2 and then A1
evaluation. `STEP_UP_VERIFICATION` and `INDEPENDENT_CHECK` do not by themselves
support A2 or A1. The absence of a permissible A3 pair is ordinary insufficient
evidence for A3, not structural invalidity, and introduces no
structural-invalid reason code.

For A1 and A2, `maximum_expires_at` is the selected supporting item's finite
expiry, or absent when that item is unbounded. Supporting evidence IDs for
every result, including a selected A3 pair, are returned in stable order by
IdentityEvidenceKind and then UUID.

A3 is permitted as an assurance event only from an effective A2 state. It has
an explicit `fallback_event_id` referring to an effective A2 event from the
same binding. These are stream transition invariants rather than Evidence
Policy inputs.

A1 and A2 may omit `expires_at`. When their supporting evidence has a finite
expiry, the assurance event cannot outlive that evidence. A1 and A2 have no
fallback. Evidence Policy does not read, validate or produce fallback data;
the mandatory A3 fallback is checked only by the stream transition validator.

## Event stream

The event kinds are:

- `ESTABLISHED`;
- `UPGRADED`;
- `REFRESHED`;
- `DOWNGRADED`;
- `REVOKED`.

The stream obeys these invariants:

- `stream_version` starts at 1 and is unique and continuous per binding;
- append uses `expected_stream_version` for optimistic concurrency;
- `previous_level` equals the effective level immediately before append;
- `ESTABLISHED` is only the first event and may establish only A1 or A2;
- A3 is never created by the first event;
- `UPGRADED` raises the level;
- `UPGRADED` is allowed after `DOWNGRADED` to A0;
- transition to A3 is allowed only from a currently effective A2;
- `REFRESHED` retains the same positive level;
- `DOWNGRADED` lowers the level, including to A0;
- `REVOKED` sets A0 and is terminal in Identity Assurance v1;
- every positive event has supporting evidence;
- A1 and A2 do not have fallback;
- the mandatory A3 fallback refers only to an earlier effective A2 event in the
  same binding;
- cross-binding evidence is prohibited;
- `idempotency_key` is globally unique.

No assurance events may follow `REVOKED`. Recovery from an erroneous revocation
or incorrect binding requires a future correction/rebinding workflow.
`DOWNGRADED` to A0 does not revoke the binding and may be followed by a trusted
server-side reassessment.

## Time and resolution rules

All datetimes are timezone-aware and canonically represented in UTC.
`effective_at` is assigned by the application service through an injected
clock. The provider's `observed_at` is the only canonical provider timestamp in
v1 and records provenance; it does not start an assurance event. PostgreSQL
assigns `recorded_at`. Client backdating is prohibited. At the boundary,
`as_of >= expires_at` means expired and `as_of >= revoked_at` means the related
evidence is revoked.

Resolution fails closed before TrustPolicy when the Account or binding is
absent, the binding is revoked, the event stream is missing or invalid, an enum
is unknown, or the fallback chain is damaged. These conditions are not reduced
to ordinary A0 because no trustworthy acting HumanSubject can be established.

An expired A3 event follows its explicit valid fallback. A1 and A2 have no
fallback and resolve to A0 when expired. A0 from expiry or downgrade remains a
resolved identity and may therefore be supplied to TrustPolicy.

## Persistence protection

The following proposed v1 tables are required to be immutable and append-only:

- `account_human_subject_bindings`;
- `identity_evidence`;
- `identity_assurance_events`;
- `identity_assurance_event_evidence`.

Repository APIs expose no update or delete operation. PostgreSQL rejects
`UPDATE`, `DELETE`, and `TRUNCATE`; `TRUNCATE` uses a separate statement-level
trigger. Foreign keys use `ON DELETE RESTRICT`.

IdentityEvidenceRevocation is a canonical immutable domain fact. Its eventual
persistence representation must be append-only and protected from `UPDATE` and
`DELETE`, but the concrete physical table or event-store representation has not
been selected. Its absence from the proposed table list is intentional and
defers that choice to the persistence design stage. No physical representation,
migration, or database constraint for this fact is approved here.

Identity Assurance persistence has not started. Its concrete persistence
design, migrations, and database constraints remain future work.

Separating runtime and migration database roles is recorded as future
hardening, not implemented in Stage 1.2.

## Trust Kernel boundary

The future Authorization Context Resolver will authenticate an Account through
a separate boundary, resolve its canonical binding and effective assurance,
and construct the immutable AuthorizationRequest. TrustPolicy remains pure and
deterministic and performs no identity database access.

## Deferred work

The current Stage 1.2 work has not yet implemented the stream transition
validator, terminal `REVOKED` enforcement, fallback-chain validation, effective
assurance resolver, application services, repository ports or adapters,
SQLAlchemy persistence, Alembic migrations, PostgreSQL constraints, database
integration tests, or HTTP API.

Stage 1.2 also does not implement:

- an authentication protocol;
- raw KYC or document storage;
- biometrics;
- subject duplicate detection or merge;
- binding correction or rebinding;
- Consent, Ownership or Succession;
- the Authorization Context Resolver;
- an expanded authorization audit envelope;
- separate runtime and migration database roles;
- retention or cryptographic erasure.

## Consequences

- Assurance remains attributable to evidence and changes without rewriting
  history.
- Multiple Accounts for one HumanSubject can carry independent assurance.
- Binding revocation is deliberately conservative and irreversible within v1;
  an evidence revocation fact is also immutable, while later verification
  creates new evidence.
- Higher-assurance expiry is deterministic and cannot depend on a background
  worker.
- Correction, deletion and retention require later explicit designs rather
  than mutation of the v1 history.
