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

Opaque references are pseudonymous identifiers, not anonymous data. They must
not appear in ordinary application logs, error messages or analytics. They may
be stored only in the canonical Identity store and in access-restricted
security audit records.

Account identity is unique by
`(authentication_authority, external_subject_reference)`. Evidence is unique
by `(provider, opaque_reference)`. A keyed digest is deferred until Memoria has
a managed secret boundary and remains future hardening.

## Evidence policy v1

The versioned server-side policy recognizes these evidence kinds:

| Evidence | Supported assurance |
|---|---|
| `ACCOUNT_CHANNEL_VERIFICATION` | A1 |
| `DOCUMENT_CHECK` or `TRUSTED_VOUCH` | A2 |
| `STEP_UP_VERIFICATION` and `INDEPENDENT_CHECK` together | A3 |

The application service computes the level. A client DTO never contains a
target assurance level.

A3 is permitted only from an effective A2 state. It always has `expires_at`,
has a maximum v1 lifetime of 24 hours, cannot outlive any supporting evidence,
and has an explicit `fallback_event_id` referring to an effective A2 event from
the same binding.

A1 and A2 may omit `expires_at`. When their supporting evidence has a finite
expiry, the assurance event cannot outlive that evidence.

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
- fallback refers only to an earlier event in the same binding;
- cross-binding evidence is prohibited;
- `idempotency_key` is globally unique.

No assurance events may follow `REVOKED`. Recovery from an erroneous revocation
or incorrect binding requires a future correction/rebinding workflow.
`DOWNGRADED` to A0 does not revoke the binding and may be followed by a trusted
server-side reassessment.

## Time and resolution rules

All datetimes are timezone-aware and canonically represented in UTC.
`effective_at` is assigned by the application service through an injected
clock. The provider's `observed_at` records provenance but does not start
assurance. PostgreSQL assigns `recorded_at`. Client backdating is prohibited.
At the boundary, `as_of >= expires_at` means expired.

Resolution fails closed before TrustPolicy when the Account or binding is
absent, the binding is revoked, the event stream is missing or invalid, an enum
is unknown, or the fallback chain is damaged. These conditions are not reduced
to ordinary A0 because no trustworthy acting HumanSubject can be established.

An expired event follows its explicit valid fallback. If there is no permitted
fallback, the effective level is A0. A0 from expiry or downgrade remains a
resolved identity and may therefore be supplied to TrustPolicy.

## Persistence protection

These v1 tables are immutable and append-only:

- `account_human_subject_bindings`;
- `identity_evidence`;
- `identity_assurance_events`;
- `identity_assurance_event_evidence`.

Repository APIs expose no update or delete operation. PostgreSQL rejects
`UPDATE`, `DELETE`, and `TRUNCATE`; `TRUNCATE` uses a separate statement-level
trigger. Foreign keys use `ON DELETE RESTRICT`.

Separating runtime and migration database roles is recorded as future
hardening, not implemented in Stage 1.2.

## Trust Kernel boundary

The future Authorization Context Resolver will authenticate an Account through
a separate boundary, resolve its canonical binding and effective assurance,
and construct the immutable AuthorizationRequest. TrustPolicy remains pure and
deterministic and performs no identity database access.

## Deferred work

Stage 1.2 does not implement:

- an authentication protocol or HTTP endpoints;
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
- Revocation is deliberately conservative and irreversible within v1.
- Higher-assurance expiry is deterministic and cannot depend on a background
  worker.
- Correction, deletion and retention require later explicit designs rather
  than mutation of the v1 history.
