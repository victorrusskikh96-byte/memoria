"""Behavioral tests for identity assurance entities and their value types."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from memoria.domain.identity import (
    Account,
    AccountHumanSubjectBinding,
    EffectiveIdentityAssurance,
    HumanSubject,
    IdentityAssuranceEvent,
    IdentityAssuranceEventKind,
    IdentityAssuranceLevel,
    IdentityEvidence,
    IdentityEvidenceKind,
)

SUBJECT_ID = UUID("00000000-0000-0000-0000-000000000001")
ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000002")
BINDING_ID = UUID("00000000-0000-0000-0000-000000000003")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000004")
EVENT_ID = UUID("00000000-0000-0000-0000-000000000005")
FALLBACK_EVENT_ID = UUID("00000000-0000-0000-0000-000000000006")
IDEMPOTENCY_KEY = UUID("00000000-0000-0000-0000-000000000007")
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def make_evidence(**overrides: object) -> IdentityEvidence:
    """Build valid identity evidence with optional field overrides for tests."""

    values: dict[str, object] = {
        "id": EVIDENCE_ID,
        "binding_id": BINDING_ID,
        "kind": IdentityEvidenceKind.DOCUMENT_CHECK,
        "provider": "identity.provider-1",
        "opaque_reference": "opaque:reference|123~abc",
        "observed_at": NOW,
        "expires_at": NOW + timedelta(days=365),
        "recorded_at": NOW,
        "schema_version": "1.0",
    }
    values.update(overrides)
    return IdentityEvidence(**values)  # type: ignore[arg-type]


def make_event(**overrides: object) -> IdentityAssuranceEvent:
    """Build a valid established assurance event with optional field overrides."""

    values: dict[str, object] = {
        "id": EVENT_ID,
        "binding_id": BINDING_ID,
        "stream_version": 1,
        "kind": IdentityAssuranceEventKind.ESTABLISHED,
        "previous_level": IdentityAssuranceLevel.A0_UNVERIFIED,
        "resulting_level": IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        "effective_at": NOW,
        "expires_at": None,
        "fallback_event_id": None,
        "reason_code": "initial.verification",
        "assurance_policy_version": "policy 1.0",
        "idempotency_key": IDEMPOTENCY_KEY,
        "recorded_at": NOW,
    }
    values.update(overrides)
    return IdentityAssuranceEvent(**values)  # type: ignore[arg-type]


def make_effective_assurance(**overrides: object) -> EffectiveIdentityAssurance:
    """Build a valid effective assurance value with optional field overrides."""

    values: dict[str, object] = {
        "account_id": ACCOUNT_ID,
        "human_subject_id": SUBJECT_ID,
        "binding_id": BINDING_ID,
        "level": IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        "source_event_id": EVENT_ID,
        "valid_until": NOW + timedelta(hours=1),
        "resolved_at": NOW,
    }
    values.update(overrides)
    return EffectiveIdentityAssurance(**values)  # type: ignore[arg-type]


def test_creates_all_entities() -> None:
    """Entities retain valid identifiers, relationships, kinds, and assurance levels."""

    subject = HumanSubject(id=SUBJECT_ID, created_at=NOW)
    account = Account(
        id=ACCOUNT_ID,
        authentication_authority="accounts.example-1",
        external_subject_reference="external:subject|123~abc",
        created_at=NOW,
    )
    binding = AccountHumanSubjectBinding(
        id=BINDING_ID,
        account_id=account.id,
        human_subject_id=subject.id,
        created_at=NOW,
    )
    evidence = make_evidence(binding_id=binding.id)

    assert subject.id == SUBJECT_ID
    assert account.id == ACCOUNT_ID
    assert binding.human_subject_id == SUBJECT_ID
    assert evidence.kind is IdentityEvidenceKind.DOCUMENT_CHECK
    assert IdentityAssuranceLevel.A0_UNVERIFIED == 0


def test_entities_are_frozen() -> None:
    """Entity fields cannot be reassigned after construction."""

    subject = HumanSubject(id=SUBJECT_ID, created_at=NOW)

    with pytest.raises(FrozenInstanceError):
        subject.created_at = NOW + timedelta(seconds=1)


def test_account_repr_redacts_external_subject_reference() -> None:
    """Account repr hides its external reference while retaining safe diagnostics."""

    sensitive_value = "sensitive:account|reference"
    account = Account(
        id=ACCOUNT_ID,
        authentication_authority="accounts.example-1",
        external_subject_reference=sensitive_value,
        created_at=NOW,
    )

    representation = repr(account)

    assert "external_subject_reference" not in representation
    assert sensitive_value not in representation
    assert f"id={ACCOUNT_ID!r}" in representation
    assert "authentication_authority='accounts.example-1'" in representation
    assert f"created_at={NOW!r}" in representation


def test_identity_evidence_repr_redacts_opaque_reference() -> None:
    """Evidence repr hides its opaque reference while retaining safe diagnostics."""

    sensitive_value = "sensitive:evidence|reference"
    evidence = make_evidence(opaque_reference=sensitive_value)

    representation = repr(evidence)

    assert "opaque_reference" not in representation
    assert sensitive_value not in representation
    assert f"id={EVIDENCE_ID!r}" in representation
    assert f"binding_id={BINDING_ID!r}" in representation
    assert f"kind={IdentityEvidenceKind.DOCUMENT_CHECK!r}" in representation
    assert "provider='identity.provider-1'" in representation
    assert f"observed_at={NOW!r}" in representation
    assert f"expires_at={NOW + timedelta(days=365)!r}" in representation
    assert f"recorded_at={NOW!r}" in representation
    assert "schema_version='1.0'" in representation


@pytest.mark.parametrize(
    ("entity", "field_name"),
    [
        (
            Account(
                id=ACCOUNT_ID,
                authentication_authority="accounts.example",
                external_subject_reference="external-123",
                created_at=NOW,
            ),
            "external_subject_reference",
        ),
        (make_evidence(), "opaque_reference"),
    ],
)
def test_redacted_entities_remain_frozen_and_slotted(entity: object, field_name: str) -> None:
    """Entities with redacted fields remain frozen slotted dataclasses."""

    assert not hasattr(entity, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(entity, field_name, "replacement")


@pytest.mark.parametrize(
    ("factory", "field_name"),
    [
        (
            lambda value: Account(
                id=ACCOUNT_ID,
                authentication_authority="accounts.example",
                external_subject_reference=value,
                created_at=NOW,
            ),
            "external_subject_reference",
        ),
        (lambda value: make_evidence(opaque_reference=value), "opaque_reference"),
    ],
)
def test_redacted_reference_validation_remains_enforced(factory: object, field_name: str) -> None:
    """Redacted reference fields retain their existing validation behavior."""

    build = factory
    valid_value = "valid:reference|123"

    entity = build(valid_value)  # type: ignore[operator]
    assert getattr(entity, field_name) == valid_value

    with pytest.raises(ValueError, match=field_name):
        build("invalid reference")  # type: ignore[operator]


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda value: HumanSubject(id=SUBJECT_ID, created_at=value), "created_at"),
        (
            lambda value: Account(
                id=ACCOUNT_ID,
                authentication_authority="accounts.example",
                external_subject_reference="external-123",
                created_at=value,
            ),
            "created_at",
        ),
        (
            lambda value: AccountHumanSubjectBinding(
                id=BINDING_ID,
                account_id=ACCOUNT_ID,
                human_subject_id=SUBJECT_ID,
                created_at=value,
            ),
            "created_at",
        ),
        (lambda value: make_evidence(observed_at=value), "observed_at"),
        (
            lambda value: make_evidence(observed_at=NOW - timedelta(days=1), expires_at=value),
            "expires_at",
        ),
        (lambda value: make_evidence(recorded_at=value), "recorded_at"),
    ],
)
def test_datetimes_are_normalized_to_utc_and_reject_naive_values(
    factory: object, field: str
) -> None:
    """Aware datetimes normalize to UTC while naive values are rejected."""

    build = factory  # Keep the parametrized callable readable to mypy.
    offset_value = datetime(2026, 9, 19, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    entity = build(offset_value)  # type: ignore[operator]
    assert getattr(entity, field) == NOW
    assert getattr(entity, field).tzinfo is UTC

    with pytest.raises(ValueError, match=field):
        build(datetime(2026, 9, 19, 12, 0))  # type: ignore[operator]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: HumanSubject(id="not-a-uuid", created_at=NOW),
        lambda: Account(
            id="not-a-uuid",
            authentication_authority="accounts.example",
            external_subject_reference="external-123",
            created_at=NOW,
        ),
        lambda: AccountHumanSubjectBinding(
            id=BINDING_ID,
            account_id="not-a-uuid",
            human_subject_id=SUBJECT_ID,
            created_at=NOW,
        ),
        lambda: AccountHumanSubjectBinding(
            id=BINDING_ID,
            account_id=ACCOUNT_ID,
            human_subject_id="not-a-uuid",
            created_at=NOW,
        ),
        lambda: make_evidence(binding_id="not-a-uuid"),
    ],
)
def test_string_ids_are_rejected(factory: object) -> None:
    """String values are rejected for fields whose contract requires UUIDs."""

    build = factory
    with pytest.raises(TypeError, match="UUID"):
        build()  # type: ignore[operator]


@pytest.mark.parametrize("value", ["provider", "a", "a.b_c-9", "9" + "a" * 63])
def test_valid_provider_and_authority(value: str) -> None:
    """Provider and authority fields accept values matching their bounded syntax."""

    assert make_evidence(provider=value).provider == value
    account = Account(
        id=ACCOUNT_ID,
        authentication_authority=value,
        external_subject_reference="external-123",
        created_at=NOW,
    )
    assert account.authentication_authority == value


@pytest.mark.parametrize("value", ["", "Uppercase", "-leading", "has space", "a" * 65])
@pytest.mark.parametrize("field", ["provider", "authentication_authority"])
def test_invalid_provider_and_authority(field: str, value: str) -> None:
    """Provider and authority fields reject values outside their required syntax."""

    with pytest.raises(ValueError, match=field):
        if field == "provider":
            make_evidence(provider=value)
        else:
            Account(
                id=ACCOUNT_ID,
                authentication_authority=value,
                external_subject_reference="external-123",
                created_at=NOW,
            )


@pytest.mark.parametrize("value", ["A", "subject_1", "id:part|other~final", "a" * 255])
def test_valid_opaque_references(value: str) -> None:
    """Reference fields accept bounded values composed of permitted characters."""

    assert make_evidence(opaque_reference=value).opaque_reference == value
    account = Account(
        id=ACCOUNT_ID,
        authentication_authority="accounts.example",
        external_subject_reference=value,
        created_at=NOW,
    )
    assert account.external_subject_reference == value


@pytest.mark.parametrize("value", ["", "contains space", "contains/slash", "é", "a" * 256])
@pytest.mark.parametrize("field", ["opaque_reference", "external_subject_reference"])
def test_invalid_opaque_references(field: str, value: str) -> None:
    """Reference fields reject empty, oversized, or unsupported values."""

    with pytest.raises(ValueError, match=field):
        if field == "opaque_reference":
            make_evidence(opaque_reference=value)
        else:
            Account(
                id=ACCOUNT_ID,
                authentication_authority="accounts.example",
                external_subject_reference=value,
                created_at=NOW,
            )


@pytest.mark.parametrize(
    ("factory", "field_name"),
    [
        (lambda value: make_evidence(opaque_reference=value), "opaque_reference"),
        (
            lambda value: Account(
                id=ACCOUNT_ID,
                authentication_authority="accounts.example",
                external_subject_reference=value,
                created_at=NOW,
            ),
            "external_subject_reference",
        ),
    ],
)
def test_opaque_reference_error_does_not_disclose_value(factory: object, field_name: str) -> None:
    """Reference validation errors identify the field without exposing its value."""

    build = factory
    sensitive_value = "secret reference with spaces"

    with pytest.raises(ValueError) as error:
        build(sensitive_value)  # type: ignore[operator]

    assert field_name in str(error.value)
    assert sensitive_value not in str(error.value)


def test_evidence_expiry_must_be_strictly_after_observation() -> None:
    """Evidence expiry may be absent but must otherwise follow observation."""

    assert make_evidence(expires_at=None).expires_at is None

    for expires_at in (NOW, NOW - timedelta(microseconds=1)):
        with pytest.raises(ValueError, match="expires_at"):
            make_evidence(expires_at=expires_at)


def test_schema_version_validation() -> None:
    """Schema versions must be bounded, trimmed, and printable ASCII strings."""

    assert make_evidence(schema_version="schema 1.0").schema_version == "schema 1.0"

    for value in ("", " leading", "trailing ", "é", "line\nbreak", "a" * 65):
        with pytest.raises(ValueError, match="schema_version"):
            make_evidence(schema_version=value)


def test_enum_values() -> None:
    """Identity enums expose the stable serialized values required by the domain."""

    assert [kind.value for kind in IdentityEvidenceKind] == [
        "account_channel_verification",
        "document_check",
        "trusted_vouch",
        "independent_check",
        "step_up_verification",
    ]
    assert [kind.value for kind in IdentityAssuranceEventKind] == [
        "established",
        "upgraded",
        "refreshed",
        "downgraded",
        "revoked",
    ]


@pytest.mark.parametrize(
    "level",
    [
        IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
    ],
)
def test_established_accepts_a1_and_a2(level: IdentityAssuranceLevel) -> None:
    """ESTABLISHED accepts an initial transition from A0 to A1 or A2."""

    event = make_event(resulting_level=level)

    assert event.previous_level is IdentityAssuranceLevel.A0_UNVERIFIED
    assert event.resulting_level is level


def test_established_rejects_a3() -> None:
    """ESTABLISHED cannot create an A3 assurance level."""

    with pytest.raises(ValueError, match="ESTABLISHED"):
        make_event(
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            expires_at=NOW + timedelta(hours=1),
            fallback_event_id=FALLBACK_EVENT_ID,
        )


def test_established_requires_first_stream_version() -> None:
    """ESTABLISHED is valid only at stream version one."""

    with pytest.raises(ValueError, match="stream_version"):
        make_event(stream_version=2)


@pytest.mark.parametrize(
    "level",
    [
        IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
    ],
)
def test_upgraded_accepts_transitions_after_a0(level: IdentityAssuranceLevel) -> None:
    """UPGRADED may increase assurance directly from A0."""

    event = make_event(
        kind=IdentityAssuranceEventKind.UPGRADED,
        previous_level=IdentityAssuranceLevel.A0_UNVERIFIED,
        resulting_level=level,
    )

    assert event.resulting_level is level


def test_upgrade_to_a3_requires_a2() -> None:
    """An upgrade reaches A3 only when its previous level is A2."""

    event = make_event(
        kind=IdentityAssuranceEventKind.UPGRADED,
        previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        expires_at=NOW + timedelta(hours=1),
        fallback_event_id=FALLBACK_EVENT_ID,
    )
    assert event.resulting_level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE

    with pytest.raises(ValueError, match="previous_level A2"):
        make_event(
            kind=IdentityAssuranceEventKind.UPGRADED,
            previous_level=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            expires_at=NOW + timedelta(hours=1),
            fallback_event_id=FALLBACK_EVENT_ID,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"expires_at": None, "fallback_event_id": FALLBACK_EVENT_ID},
        {"expires_at": NOW + timedelta(hours=1), "fallback_event_id": None},
    ],
)
def test_a3_requires_expiry_and_fallback(overrides: dict[str, object]) -> None:
    """A3 assurance requires both a finite expiry and a fallback event."""

    with pytest.raises(ValueError, match="requires"):
        make_event(
            kind=IdentityAssuranceEventKind.UPGRADED,
            previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            **overrides,
        )


def test_a3_accepts_exactly_twenty_four_hours() -> None:
    """A3 assurance may remain effective for exactly twenty-four hours."""

    event = make_event(
        kind=IdentityAssuranceEventKind.UPGRADED,
        previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        expires_at=NOW + timedelta(hours=24),
        fallback_event_id=FALLBACK_EVENT_ID,
    )

    assert event.expires_at == NOW + timedelta(hours=24)


def test_a3_rejects_more_than_twenty_four_hours() -> None:
    """A3 assurance cannot remain effective for more than twenty-four hours."""

    with pytest.raises(ValueError, match="24 hours"):
        make_event(
            kind=IdentityAssuranceEventKind.UPGRADED,
            previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            expires_at=NOW + timedelta(hours=24, microseconds=1),
            fallback_event_id=FALLBACK_EVENT_ID,
        )


@pytest.mark.parametrize(
    "level",
    [
        IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
    ],
)
def test_refreshed_accepts_equal_positive_levels(level: IdentityAssuranceLevel) -> None:
    """REFRESHED preserves an existing assurance level above A0."""

    a3_fields: dict[str, object] = {}
    if level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE:
        a3_fields = {
            "expires_at": NOW + timedelta(hours=1),
            "fallback_event_id": FALLBACK_EVENT_ID,
        }
    event = make_event(
        kind=IdentityAssuranceEventKind.REFRESHED,
        previous_level=level,
        resulting_level=level,
        **a3_fields,
    )

    assert event.previous_level is event.resulting_level


@pytest.mark.parametrize(
    ("previous_level", "resulting_level"),
    [
        (IdentityAssuranceLevel.A0_UNVERIFIED, IdentityAssuranceLevel.A0_UNVERIFIED),
        (
            IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
            IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        ),
    ],
)
def test_refreshed_rejects_a0_and_level_changes(
    previous_level: IdentityAssuranceLevel,
    resulting_level: IdentityAssuranceLevel,
) -> None:
    """REFRESHED rejects A0 and any transition between different levels."""

    with pytest.raises(ValueError, match="REFRESHED"):
        make_event(
            kind=IdentityAssuranceEventKind.REFRESHED,
            previous_level=previous_level,
            resulting_level=resulting_level,
        )


@pytest.mark.parametrize(
    ("previous_level", "resulting_level"),
    [
        (
            IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        ),
        (IdentityAssuranceLevel.A1_CONTACT_VERIFIED, IdentityAssuranceLevel.A0_UNVERIFIED),
    ],
)
def test_downgraded_accepts_strict_decreases(
    previous_level: IdentityAssuranceLevel,
    resulting_level: IdentityAssuranceLevel,
) -> None:
    """DOWNGRADED accepts only a lower result, including A0."""

    event = make_event(
        kind=IdentityAssuranceEventKind.DOWNGRADED,
        previous_level=previous_level,
        resulting_level=resulting_level,
    )

    assert event.resulting_level < event.previous_level


@pytest.mark.parametrize(
    ("previous_level", "resulting_level"),
    [
        (
            IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
            IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        ),
        (
            IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
            IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        ),
    ],
)
def test_downgraded_rejects_equal_or_higher_results(
    previous_level: IdentityAssuranceLevel,
    resulting_level: IdentityAssuranceLevel,
) -> None:
    """DOWNGRADED rejects unchanged or increased assurance levels."""

    with pytest.raises(ValueError, match="DOWNGRADED"):
        make_event(
            kind=IdentityAssuranceEventKind.DOWNGRADED,
            previous_level=previous_level,
            resulting_level=resulting_level,
        )


def test_revoked_requires_a0_without_expiry_or_fallback() -> None:
    """REVOKED results in A0 and carries neither expiry nor fallback metadata."""

    event = make_event(
        kind=IdentityAssuranceEventKind.REVOKED,
        previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        resulting_level=IdentityAssuranceLevel.A0_UNVERIFIED,
    )
    assert event.expires_at is None
    assert event.fallback_event_id is None

    invalid_overrides = [
        {"resulting_level": IdentityAssuranceLevel.A1_CONTACT_VERIFIED},
        {"expires_at": NOW + timedelta(hours=1)},
        {"fallback_event_id": FALLBACK_EVENT_ID},
    ]
    for overrides in invalid_overrides:
        values: dict[str, object] = {
            "kind": IdentityAssuranceEventKind.REVOKED,
            "previous_level": IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            "resulting_level": IdentityAssuranceLevel.A0_UNVERIFIED,
        }
        values.update(overrides)
        with pytest.raises(ValueError):
            make_event(**values)


def test_fallback_is_rejected_for_non_a3_assurance() -> None:
    """Only a resulting A3 assurance level may reference a fallback event."""

    with pytest.raises(ValueError, match="only for A3"):
        make_event(fallback_event_id=FALLBACK_EVENT_ID)


def test_fallback_event_must_differ_from_event() -> None:
    """An A3 event cannot identify itself as its fallback event."""

    with pytest.raises(ValueError, match="differ"):
        make_event(
            kind=IdentityAssuranceEventKind.UPGRADED,
            previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            expires_at=NOW + timedelta(hours=1),
            fallback_event_id=EVENT_ID,
        )


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda value: make_event(effective_at=value), "effective_at"),
        (lambda value: make_event(recorded_at=value), "recorded_at"),
        (
            lambda value: make_event(
                kind=IdentityAssuranceEventKind.UPGRADED,
                previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
                resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
                expires_at=value,
                fallback_event_id=FALLBACK_EVENT_ID,
            ),
            "expires_at",
        ),
        (lambda value: make_effective_assurance(valid_until=value), "valid_until"),
        (lambda value: make_effective_assurance(resolved_at=value), "resolved_at"),
    ],
)
def test_new_entity_datetimes_reject_naive_values(factory: object, field: str) -> None:
    """New entity datetime fields reject values without timezone information."""

    build = factory
    with pytest.raises(ValueError, match=field):
        build(datetime(2026, 9, 19, 12, 0))  # type: ignore[operator]


def test_new_entity_datetimes_normalize_to_utc() -> None:
    """New entity datetime fields normalize aware values to UTC."""

    offset_time = datetime(
        2026,
        9,
        19,
        17,
        30,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )
    event = make_event(effective_at=offset_time, recorded_at=offset_time)
    effective = make_effective_assurance(valid_until=offset_time, resolved_at=offset_time)

    assert event.effective_at == NOW
    assert event.recorded_at.tzinfo is UTC
    assert effective.valid_until == NOW
    assert effective.resolved_at.tzinfo is UTC


@pytest.mark.parametrize(
    "factory",
    [
        lambda: make_event(id="not-a-uuid"),
        lambda: make_event(binding_id="not-a-uuid"),
        lambda: make_event(idempotency_key="not-a-uuid"),
        lambda: make_event(
            kind=IdentityAssuranceEventKind.UPGRADED,
            previous_level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            resulting_level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            expires_at=NOW + timedelta(hours=1),
            fallback_event_id="not-a-uuid",
        ),
        lambda: make_effective_assurance(account_id="not-a-uuid"),
        lambda: make_effective_assurance(human_subject_id="not-a-uuid"),
        lambda: make_effective_assurance(binding_id="not-a-uuid"),
        lambda: make_effective_assurance(source_event_id="not-a-uuid"),
    ],
)
def test_new_entity_string_ids_are_rejected(factory: object) -> None:
    """New entity identifier fields reject strings in place of UUID values."""

    build = factory
    with pytest.raises(TypeError, match="UUID"):
        build()  # type: ignore[operator]


@pytest.mark.parametrize("value", ["reason", "a", "reason.code_1-2", "9" + "a" * 63])
def test_reason_code_accepts_bounded_domain_codes(value: str) -> None:
    """Reason codes accept the documented lowercase bounded syntax."""

    assert make_event(reason_code=value).reason_code == value


@pytest.mark.parametrize("value", ["", "Uppercase", "-leading", "has space", "a" * 65])
def test_reason_code_rejects_invalid_values(value: str) -> None:
    """Reason codes reject values outside their documented syntax."""

    with pytest.raises(ValueError, match="reason_code"):
        make_event(reason_code=value)


@pytest.mark.parametrize("value", ["1", "policy 1.0", "v" * 64])
def test_assurance_policy_version_accepts_printable_ascii(value: str) -> None:
    """Policy versions accept bounded, trimmed, printable ASCII strings."""

    assert make_event(assurance_policy_version=value).assurance_policy_version == value


@pytest.mark.parametrize("value", ["", " leading", "trailing ", "é", "line\nbreak", "a" * 65])
def test_assurance_policy_version_rejects_invalid_values(value: str) -> None:
    """Policy versions reject empty, untrimmed, non-ASCII, or oversized values."""

    with pytest.raises(ValueError, match="assurance_policy_version"):
        make_event(assurance_policy_version=value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reason_code", "private reason"),
        ("assurance_policy_version", "private\nrevision"),
    ],
)
def test_event_validation_errors_do_not_disclose_values(field: str, value: str) -> None:
    """Event string validation errors do not disclose rejected field values."""

    with pytest.raises(ValueError) as error:
        make_event(**{field: value})

    assert value not in str(error.value)


def test_effective_identity_assurance_is_immutable() -> None:
    """Effective identity assurance is an immutable computed value."""

    assurance = make_effective_assurance()

    with pytest.raises(FrozenInstanceError):
        assurance.level = IdentityAssuranceLevel.A1_CONTACT_VERIFIED
