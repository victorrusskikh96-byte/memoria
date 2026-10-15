"""Test immutable contracts and deterministic Identity Evidence Policy V1."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from inspect import signature
from itertools import permutations
from uuid import UUID, uuid4

import pytest

from memoria.domain.identity import (
    EVIDENCE_POLICY_VERSION,
    EvidencePolicyDecision,
    EvidencePolicyReason,
    EvidencePolicyRulesV1,
    EvidencePolicyStatus,
    EvidenceProviderRule,
    IdentityAssuranceLevel,
    IdentityEvidence,
    IdentityEvidenceKind,
    IdentityEvidencePolicyV1,
    IdentityEvidenceRevocation,
)

TEST_PROVIDER = "test-only.provider"
TEST_PROVIDER_B = "test-only.provider-b"
TEST_PROVIDER_C = "test-only.provider-c"
UNKNOWN_PROVIDER = "test-only.unknown-provider"
TEST_SCHEMA_VERSION = "test-schema 1.0"
UNSUPPORTED_SCHEMA_VERSION = "test-schema 2.0"
OPAQUE_REFERENCE = "opaque-secret-reference"
AS_OF = datetime(2030, 1, 1, 12, tzinfo=UTC)
BINDING_ID = UUID(int=1)


def make_provider_rule(**overrides: object) -> EvidenceProviderRule:
    """Build a valid test-only provider rule with selected overrides."""

    values: dict[str, object] = {
        "provider": TEST_PROVIDER,
        "evidence_kind": IdentityEvidenceKind.DOCUMENT_CHECK,
    }
    values.update(overrides)
    return EvidenceProviderRule(**values)  # type: ignore[arg-type]


def make_rules(**overrides: object) -> EvidencePolicyRulesV1:
    """Build valid V1 test rules with selected overrides."""

    values: dict[str, object] = {
        "provider_rules": frozenset({make_provider_rule()}),
        "supported_schema_versions": frozenset({TEST_SCHEMA_VERSION}),
    }
    values.update(overrides)
    return EvidencePolicyRulesV1(**values)  # type: ignore[arg-type]


def make_decision(**overrides: object) -> EvidencePolicyDecision:
    """Build a valid qualified decision with selected overrides."""

    values: dict[str, object] = {
        "status": EvidencePolicyStatus.QUALIFIED,
        "level": IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        "supporting_evidence_ids": (uuid4(),),
        "maximum_expires_at": None,
        "reason_codes": (EvidencePolicyReason.QUALIFIED,),
        "policy_version": EVIDENCE_POLICY_VERSION,
    }
    values.update(overrides)
    return EvidencePolicyDecision(**values)  # type: ignore[arg-type]


def make_evidence(**overrides: object) -> IdentityEvidence:
    """Build canonical test-only identity evidence with selected overrides."""

    values: dict[str, object] = {
        "id": UUID(int=100),
        "binding_id": BINDING_ID,
        "kind": IdentityEvidenceKind.DOCUMENT_CHECK,
        "provider": TEST_PROVIDER,
        "opaque_reference": OPAQUE_REFERENCE,
        "observed_at": AS_OF - timedelta(hours=1),
        "expires_at": AS_OF + timedelta(days=7),
        "recorded_at": AS_OF - timedelta(minutes=30),
        "schema_version": TEST_SCHEMA_VERSION,
    }
    values.update(overrides)
    return IdentityEvidence(**values)  # type: ignore[arg-type]


def make_revocation(**overrides: object) -> IdentityEvidenceRevocation:
    """Build a canonical test-only evidence revocation with selected overrides."""

    values: dict[str, object] = {
        "id": UUID(int=1000),
        "evidence_id": UUID(int=100),
        "binding_id": BINDING_ID,
        "revoked_at": AS_OF - timedelta(minutes=1),
        "reason_code": "test-revocation",
        "idempotency_key": UUID(int=2000),
        "recorded_at": AS_OF,
        "schema_version": TEST_SCHEMA_VERSION,
    }
    values.update(overrides)
    return IdentityEvidenceRevocation(**values)  # type: ignore[arg-type]


def make_policy() -> IdentityEvidencePolicyV1:
    """Build a policy whose provider registry contains only test identifiers."""

    rules = {
        EvidenceProviderRule(provider=provider, evidence_kind=kind)
        for provider in (TEST_PROVIDER, TEST_PROVIDER_B)
        for kind in IdentityEvidenceKind
    }
    rules.add(
        EvidenceProviderRule(
            provider=TEST_PROVIDER_C,
            evidence_kind=IdentityEvidenceKind.DOCUMENT_CHECK,
        )
    )
    return IdentityEvidencePolicyV1(
        rules=EvidencePolicyRulesV1(
            provider_rules=frozenset(rules),
            supported_schema_versions=frozenset({TEST_SCHEMA_VERSION}),
        )
    )


def assert_insufficient(decision: EvidencePolicyDecision) -> None:
    """Assert the complete canonical A0 decision shape."""

    assert decision == EvidencePolicyDecision(
        status=EvidencePolicyStatus.INSUFFICIENT,
        level=IdentityAssuranceLevel.A0_UNVERIFIED,
        supporting_evidence_ids=(),
        maximum_expires_at=None,
        reason_codes=(EvidencePolicyReason.INSUFFICIENT_EVIDENCE,),
        policy_version=EVIDENCE_POLICY_VERSION,
    )


def assert_qualified_for_every_evidence_order(
    *,
    evidence: tuple[IdentityEvidence, ...],
    level: IdentityAssuranceLevel,
    supporting_evidence_ids: tuple[UUID, ...],
    maximum_expires_at: datetime | None,
) -> None:
    """Assert one exact qualified decision for every evidence ordering."""

    decisions = {
        make_policy().evaluate(
            binding_id=BINDING_ID,
            as_of=AS_OF,
            evidence=ordering,
            revocations=(),
        )
        for ordering in permutations(evidence)
    }

    assert decisions == {
        EvidencePolicyDecision(
            status=EvidencePolicyStatus.QUALIFIED,
            level=level,
            supporting_evidence_ids=supporting_evidence_ids,
            maximum_expires_at=maximum_expires_at,
            reason_codes=(EvidencePolicyReason.QUALIFIED,),
            policy_version=EVIDENCE_POLICY_VERSION,
        )
    }


class SensitiveValue:
    """Expose a marker through repr to verify call errors remain value-safe."""

    def __repr__(self) -> str:
        """Return a deliberately sensitive representation."""

        return "sensitive-provider-schema-opaque-repr"


def test_evidence_policy_status_values() -> None:
    """Policy statuses expose the complete stable wire-value contract."""

    assert [(item.name, item.value) for item in EvidencePolicyStatus] == [
        ("QUALIFIED", "qualified"),
        ("INSUFFICIENT", "insufficient"),
        ("INVALID", "invalid"),
    ]


def test_evidence_policy_reason_values() -> None:
    """Policy reasons expose only the documented V1 outcome codes."""

    assert [(item.name, item.value) for item in EvidencePolicyReason] == [
        ("QUALIFIED", "qualified"),
        ("INSUFFICIENT_EVIDENCE", "insufficient_evidence"),
        ("DUPLICATE_EVIDENCE_ID", "duplicate_evidence_id"),
        ("DUPLICATE_REVOCATION_ID", "duplicate_revocation_id"),
        ("CROSS_BINDING_EVIDENCE", "cross_binding_evidence"),
        ("CROSS_BINDING_REVOCATION", "cross_binding_revocation"),
        ("REVOCATION_OF_UNKNOWN_EVIDENCE", "revocation_of_unknown_evidence"),
        ("UNSUPPORTED_SCHEMA_VERSION", "unsupported_schema_version"),
        ("UNKNOWN_RUNTIME_ENUM", "unknown_runtime_enum"),
        ("INVALID_TEMPORAL_DATA", "invalid_temporal_data"),
    ]


def test_provider_rule_accepts_canonical_test_provider() -> None:
    """A canonical test-only provider and evidence kind form a valid rule."""

    rule = make_provider_rule()

    assert rule.provider == TEST_PROVIDER
    assert rule.evidence_kind is IdentityEvidenceKind.DOCUMENT_CHECK


@pytest.mark.parametrize("provider", ["*", "test-only.*", "any/*"])
def test_provider_rule_rejects_wildcards(provider: str) -> None:
    """Provider rules reject wildcard identifiers in every common form."""

    with pytest.raises(ValueError, match="provider"):
        make_provider_rule(provider=provider)


def test_provider_rule_validates_evidence_kind_at_runtime() -> None:
    """Provider rules reject values outside IdentityEvidenceKind at runtime."""

    with pytest.raises(ValueError, match="IdentityEvidenceKind"):
        make_provider_rule(evidence_kind="document_check")


@pytest.mark.parametrize(
    "value",
    [make_provider_rule(), make_rules(), make_decision(), make_policy()],
)
def test_contract_dataclasses_are_frozen_and_slotted(value: object) -> None:
    """Every policy contract dataclass is immutable and omits an instance dictionary."""

    assert not hasattr(value, "__dict__")
    with pytest.raises((FrozenInstanceError, TypeError)):
        value.unexpected = "change"  # type: ignore[attr-defined]


def test_rules_accept_immutable_configuration() -> None:
    """V1 rules retain immutable registries and expose the class policy version."""

    rules = make_rules()

    assert rules.provider_rules == frozenset({make_provider_rule()})
    assert rules.supported_schema_versions == frozenset({TEST_SCHEMA_VERSION})
    assert rules.policy_version == EVIDENCE_POLICY_VERSION
    assert EvidencePolicyRulesV1.policy_version == EVIDENCE_POLICY_VERSION


def test_rules_reject_empty_provider_registry() -> None:
    """V1 rules reject an empty provider registry as a configuration error."""

    with pytest.raises(ValueError, match="provider registry configuration"):
        make_rules(provider_rules=frozenset())


def test_rules_reject_empty_schema_versions() -> None:
    """V1 rules reject an empty supported-schema configuration."""

    with pytest.raises(ValueError, match="schema versions configuration"):
        make_rules(supported_schema_versions=frozenset())


@pytest.mark.parametrize("schema_version", ["", " leading", "trailing ", "v\n2", "é"])
def test_rules_reject_invalid_schema_versions(schema_version: str) -> None:
    """V1 rules apply canonical version validation to every schema version."""

    with pytest.raises(ValueError, match="schema_version"):
        make_rules(supported_schema_versions=frozenset({schema_version}))


@pytest.mark.parametrize("field", ["provider_rules", "supported_schema_versions"])
def test_rules_require_frozenset_collections(field: str) -> None:
    """V1 rule collections must already use their immutable runtime types."""

    with pytest.raises(ValueError, match=field):
        make_rules(**{field: set()})


def test_qualified_decision_is_valid() -> None:
    """A qualified decision accepts A1 through A3 support and an optional expiry."""

    evidence_id = uuid4()
    decision = make_decision(
        level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        supporting_evidence_ids=(evidence_id,),
        maximum_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )

    assert decision.status is EvidencePolicyStatus.QUALIFIED
    assert decision.level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE
    assert decision.supporting_evidence_ids == (evidence_id,)


def test_insufficient_decision_is_valid() -> None:
    """An insufficient decision represents A0 without supporting evidence."""

    decision = make_decision(
        status=EvidencePolicyStatus.INSUFFICIENT,
        level=IdentityAssuranceLevel.A0_UNVERIFIED,
        supporting_evidence_ids=(),
        reason_codes=(EvidencePolicyReason.INSUFFICIENT_EVIDENCE,),
    )

    assert decision.level is IdentityAssuranceLevel.A0_UNVERIFIED
    assert decision.supporting_evidence_ids == ()


def test_invalid_decision_is_valid() -> None:
    """An invalid decision omits its level, support, and maximum expiry."""

    decision = make_decision(
        status=EvidencePolicyStatus.INVALID,
        level=None,
        supporting_evidence_ids=(),
        reason_codes=(EvidencePolicyReason.INVALID_TEMPORAL_DATA,),
    )

    assert decision.level is None
    assert decision.maximum_expires_at is None


@pytest.mark.parametrize(
    ("status", "level", "supporting_evidence_ids"),
    [
        (EvidencePolicyStatus.QUALIFIED, IdentityAssuranceLevel.A0_UNVERIFIED, (uuid4(),)),
        (EvidencePolicyStatus.QUALIFIED, None, (uuid4(),)),
        (EvidencePolicyStatus.QUALIFIED, IdentityAssuranceLevel.A1_CONTACT_VERIFIED, ()),
        (EvidencePolicyStatus.INSUFFICIENT, IdentityAssuranceLevel.A1_CONTACT_VERIFIED, ()),
        (EvidencePolicyStatus.INSUFFICIENT, IdentityAssuranceLevel.A0_UNVERIFIED, (uuid4(),)),
        (EvidencePolicyStatus.INVALID, IdentityAssuranceLevel.A0_UNVERIFIED, ()),
        (EvidencePolicyStatus.INVALID, None, (uuid4(),)),
    ],
)
def test_decision_rejects_incompatible_status_shape(
    status: EvidencePolicyStatus,
    level: IdentityAssuranceLevel | None,
    supporting_evidence_ids: tuple[UUID, ...],
) -> None:
    """Decision status controls the permitted level and supporting IDs."""

    with pytest.raises(ValueError):
        make_decision(
            status=status,
            level=level,
            supporting_evidence_ids=supporting_evidence_ids,
        )


def test_invalid_decision_rejects_maximum_expiry() -> None:
    """An invalid decision cannot carry a maximum evidence expiry."""

    with pytest.raises(ValueError, match="INVALID"):
        make_decision(
            status=EvidencePolicyStatus.INVALID,
            level=None,
            supporting_evidence_ids=(),
            maximum_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        )


def test_decision_rejects_duplicate_supporting_ids() -> None:
    """A decision rejects repeated supporting evidence UUIDs."""

    evidence_id = uuid4()
    with pytest.raises(ValueError, match="unique"):
        make_decision(supporting_evidence_ids=(evidence_id, evidence_id))


def test_decision_rejects_naive_maximum_expiry() -> None:
    """A decision rejects a maximum expiry without timezone information."""

    with pytest.raises(ValueError, match="timezone-aware"):
        make_decision(maximum_expires_at=datetime(2030, 1, 1))


def test_decision_normalizes_maximum_expiry_to_utc() -> None:
    """A decision normalizes an aware maximum expiry to UTC."""

    offset = timezone(timedelta(hours=5, minutes=30))
    expiry = datetime(2030, 1, 1, 5, 30, tzinfo=offset)

    assert make_decision(maximum_expires_at=expiry).maximum_expires_at == datetime(
        2030, 1, 1, tzinfo=UTC
    )


def test_decision_rejects_empty_reason_codes() -> None:
    """Every decision requires at least one typed reason code."""

    with pytest.raises(ValueError, match="reason_codes"):
        make_decision(reason_codes=())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "qualified"),
        ("level", 1),
        ("reason_codes", ("qualified",)),
    ],
)
def test_decision_rejects_unknown_runtime_enum_values(field: str, value: object) -> None:
    """Decision enum fields reject untyped values even when wire values match."""

    with pytest.raises(ValueError, match=field):
        make_decision(**{field: value})


def test_decision_rejects_wrong_policy_version() -> None:
    """A decision accepts only the exact Evidence Policy V1 identifier."""

    with pytest.raises(ValueError, match="policy_version"):
        make_decision(policy_version="identity-evidence/2.0")


@pytest.mark.parametrize(
    ("factory", "overrides", "sensitive_value"),
    [
        (make_provider_rule, {"provider": "secret@example.com"}, "secret@example.com"),
        (make_rules, {"supported_schema_versions": frozenset({" secret-schema"})}, "secret-schema"),
        (
            make_decision,
            {"policy_version": "opaque-provider-reference"},
            "opaque-provider-reference",
        ),
    ],
)
def test_validation_errors_do_not_expose_sensitive_values(
    factory: object,
    overrides: dict[str, object],
    sensitive_value: str,
) -> None:
    """Validation failures identify fields without echoing sensitive inputs."""

    with pytest.raises(ValueError) as error:
        factory(**overrides)  # type: ignore[operator]

    assert sensitive_value not in str(error.value)


def test_policy_retains_rules() -> None:
    """A V1 policy is created with and retains its immutable rules."""

    rules = make_rules()

    assert IdentityEvidencePolicyV1(rules=rules).rules is rules


def test_policy_rejects_non_rules_value() -> None:
    """Policy construction rejects a value outside the exact rules contract."""

    with pytest.raises(ValueError, match="rules"):
        IdentityEvidencePolicyV1(rules=SensitiveValue())  # type: ignore[arg-type]


def test_empty_evidence_is_insufficient() -> None:
    """An empty structurally valid input produces the canonical A0 decision."""

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(),
        revocations=(),
    )

    assert_insufficient(decision)


def test_a1_uses_account_channel_verification() -> None:
    """One eligible account-channel verification qualifies the binding for A1."""

    item = make_evidence(
        id=UUID(int=101),
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert decision.status is EvidencePolicyStatus.QUALIFIED
    assert decision.level is IdentityAssuranceLevel.A1_CONTACT_VERIFIED
    assert decision.supporting_evidence_ids == (item.id,)
    assert decision.maximum_expires_at == item.expires_at
    assert decision.reason_codes == (EvidencePolicyReason.QUALIFIED,)
    assert decision.policy_version == EVIDENCE_POLICY_VERSION


def test_a1_selects_by_canonical_candidate_rank() -> None:
    """A1 selection prefers an unbounded candidate before finite candidates."""

    finite = make_evidence(
        id=UUID(int=101),
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
        expires_at=AS_OF + timedelta(days=30),
    )
    unbounded = make_evidence(
        id=UUID(int=102),
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
        observed_at=AS_OF - timedelta(days=2),
        expires_at=None,
    )

    assert_qualified_for_every_evidence_order(
        evidence=(finite, unbounded),
        level=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        supporting_evidence_ids=(unbounded.id,),
        maximum_expires_at=None,
    )


@pytest.mark.parametrize(
    ("winner_id", "winner_overrides", "loser_id", "loser_overrides", "maximum_expires_at"),
    [
        pytest.param(
            UUID(int=112),
            {"expires_at": AS_OF + timedelta(days=8)},
            UUID(int=111),
            {"expires_at": AS_OF + timedelta(days=7)},
            AS_OF + timedelta(days=8),
            id="later-finite-expiry",
        ),
        pytest.param(
            UUID(int=112),
            {"observed_at": AS_OF - timedelta(minutes=30)},
            UUID(int=111),
            {"observed_at": AS_OF - timedelta(hours=1)},
            AS_OF + timedelta(days=7),
            id="later-observed-at",
        ),
        pytest.param(
            UUID(int=111),
            {},
            UUID(int=112),
            {},
            AS_OF + timedelta(days=7),
            id="lower-uuid",
        ),
    ],
)
def test_a1_remaining_candidate_rank_tie_breakers(
    winner_id: UUID,
    winner_overrides: dict[str, object],
    loser_id: UUID,
    loser_overrides: dict[str, object],
    maximum_expires_at: datetime,
) -> None:
    """A1 applies each remaining canonical candidate-rank tie-breaker."""

    winner = make_evidence(
        id=winner_id,
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
        **winner_overrides,
    )
    loser = make_evidence(
        id=loser_id,
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
        **loser_overrides,
    )

    assert_qualified_for_every_evidence_order(
        evidence=(winner, loser),
        level=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        supporting_evidence_ids=(winner.id,),
        maximum_expires_at=maximum_expires_at,
    )


def test_a2_uses_document_check() -> None:
    """One eligible document check qualifies the binding for A2."""

    item = make_evidence(kind=IdentityEvidenceKind.DOCUMENT_CHECK)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert decision.level is IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH
    assert decision.supporting_evidence_ids == (item.id,)
    assert decision.maximum_expires_at == item.expires_at


def test_a2_uses_trusted_vouch() -> None:
    """One eligible trusted vouch independently qualifies the binding for A2."""

    item = make_evidence(kind=IdentityEvidenceKind.TRUSTED_VOUCH)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert decision.level is IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH
    assert decision.supporting_evidence_ids == (item.id,)


def test_a2_selection_between_kinds_is_deterministic() -> None:
    """A2 ties prefer the earlier evidence-kind declaration before the lower UUID."""

    document = make_evidence(id=UUID(int=300), kind=IdentityEvidenceKind.DOCUMENT_CHECK)
    vouch = make_evidence(id=UUID(int=200), kind=IdentityEvidenceKind.TRUSTED_VOUCH)

    assert_qualified_for_every_evidence_order(
        evidence=(document, vouch),
        level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        supporting_evidence_ids=(document.id,),
        maximum_expires_at=document.expires_at,
    )


@pytest.mark.parametrize(
    (
        "winner_kind",
        "winner_id",
        "winner_overrides",
        "loser_kind",
        "loser_id",
        "loser_overrides",
        "maximum_expires_at",
    ),
    [
        pytest.param(
            IdentityEvidenceKind.TRUSTED_VOUCH,
            UUID(int=212),
            {"expires_at": None},
            IdentityEvidenceKind.DOCUMENT_CHECK,
            UUID(int=211),
            {"expires_at": AS_OF + timedelta(days=7)},
            None,
            id="unbounded-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.TRUSTED_VOUCH,
            UUID(int=212),
            {"expires_at": AS_OF + timedelta(days=8)},
            IdentityEvidenceKind.DOCUMENT_CHECK,
            UUID(int=211),
            {"expires_at": AS_OF + timedelta(days=7)},
            AS_OF + timedelta(days=8),
            id="later-finite-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.TRUSTED_VOUCH,
            UUID(int=212),
            {"observed_at": AS_OF - timedelta(minutes=30)},
            IdentityEvidenceKind.DOCUMENT_CHECK,
            UUID(int=211),
            {"observed_at": AS_OF - timedelta(hours=1)},
            AS_OF + timedelta(days=7),
            id="later-observed-at",
        ),
        pytest.param(
            IdentityEvidenceKind.DOCUMENT_CHECK,
            UUID(int=211),
            {},
            IdentityEvidenceKind.DOCUMENT_CHECK,
            UUID(int=212),
            {},
            AS_OF + timedelta(days=7),
            id="lower-uuid-within-kind",
        ),
    ],
)
def test_a2_remaining_candidate_rank_tie_breakers(
    winner_kind: IdentityEvidenceKind,
    winner_id: UUID,
    winner_overrides: dict[str, object],
    loser_kind: IdentityEvidenceKind,
    loser_id: UUID,
    loser_overrides: dict[str, object],
    maximum_expires_at: datetime | None,
) -> None:
    """A2 applies each remaining canonical candidate-rank tie-breaker."""

    winner = make_evidence(id=winner_id, kind=winner_kind, **winner_overrides)
    loser = make_evidence(id=loser_id, kind=loser_kind, **loser_overrides)

    assert_qualified_for_every_evidence_order(
        evidence=(winner, loser),
        level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        supporting_evidence_ids=(winner.id,),
        maximum_expires_at=maximum_expires_at,
    )


def test_a3_uses_different_providers() -> None:
    """A step-up and independent check from different providers qualify for A3."""

    step_up = make_evidence(
        id=UUID(int=401),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    independent = make_evidence(
        id=UUID(int=402),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=None,
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(step_up, independent),
        revocations=(),
    )

    assert decision.level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE
    assert decision.supporting_evidence_ids == (independent.id, step_up.id)
    assert decision.reason_codes == (EvidencePolicyReason.QUALIFIED,)


def test_a3_rejects_same_provider_pair_and_falls_through() -> None:
    """A3 evidence from one provider supplies no lower assurance by itself."""

    step_up = make_evidence(id=UUID(int=401), kind=IdentityEvidenceKind.STEP_UP_VERIFICATION)
    independent = make_evidence(id=UUID(int=402), kind=IdentityEvidenceKind.INDEPENDENT_CHECK)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(step_up, independent),
        revocations=(),
    )

    assert_insufficient(decision)


def test_unavailable_a3_falls_through_to_qualifying_a2() -> None:
    """An unavailable same-provider A3 pair falls through to qualifying A2 evidence."""

    step_up = make_evidence(
        id=UUID(int=421),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
    )
    independent = make_evidence(
        id=UUID(int=422),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER,
    )
    document = make_evidence(
        id=UUID(int=423),
        kind=IdentityEvidenceKind.DOCUMENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=AS_OF + timedelta(days=5),
    )

    assert_qualified_for_every_evidence_order(
        evidence=(step_up, independent, document),
        level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
        supporting_evidence_ids=(document.id,),
        maximum_expires_at=document.expires_at,
    )


def test_unavailable_a3_falls_through_to_qualifying_a1() -> None:
    """An unavailable same-provider A3 pair falls through to qualifying A1 evidence."""

    step_up = make_evidence(
        id=UUID(int=431),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
    )
    independent = make_evidence(
        id=UUID(int=432),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER,
    )
    account_channel = make_evidence(
        id=UUID(int=433),
        kind=IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION,
        provider=TEST_PROVIDER_B,
        expires_at=AS_OF + timedelta(days=3),
    )

    assert_qualified_for_every_evidence_order(
        evidence=(step_up, independent, account_channel),
        level=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        supporting_evidence_ids=(account_channel.id,),
        maximum_expires_at=account_channel.expires_at,
    )


def test_a3_uses_alternative_pair_when_individual_leaders_share_provider() -> None:
    """A3 exhaustive pairing can select a lower-ranked cross-provider candidate."""

    step_up = make_evidence(
        id=UUID(int=401),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    best_independent = make_evidence(
        id=UUID(int=402),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    alternative = make_evidence(
        id=UUID(int=403),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=AS_OF + timedelta(hours=4),
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(best_independent, alternative, step_up),
        revocations=(),
    )

    assert decision.level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE
    assert decision.supporting_evidence_ids == (alternative.id, step_up.id)


def test_a3_pair_maximum_expiry_precedes_candidate_ranks() -> None:
    """A3 pair selection prefers later maximum expiry before candidate ranks."""

    later_step = make_evidence(
        id=UUID(int=481),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        observed_at=AS_OF - timedelta(hours=2),
        expires_at=None,
    )
    later_independent = make_evidence(
        id=UUID(int=482),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        observed_at=AS_OF - timedelta(hours=2),
        expires_at=AS_OF + timedelta(hours=8),
    )
    earlier_step = make_evidence(
        id=UUID(int=471),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER_B,
        observed_at=AS_OF - timedelta(minutes=30),
        expires_at=None,
    )
    earlier_independent = make_evidence(
        id=UUID(int=472),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER,
        observed_at=AS_OF - timedelta(minutes=30),
        expires_at=AS_OF + timedelta(hours=4),
    )

    assert_qualified_for_every_evidence_order(
        evidence=(later_step, later_independent, earlier_step, earlier_independent),
        level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        supporting_evidence_ids=(later_independent.id, later_step.id),
        maximum_expires_at=AS_OF + timedelta(hours=8),
    )


def test_a3_step_up_rank_precedes_independent_rank() -> None:
    """A3 pair selection compares step-up rank before independent-check rank."""

    better_step = make_evidence(
        id=UUID(int=491),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    worse_independent = make_evidence(
        id=UUID(int=492),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        observed_at=AS_OF - timedelta(hours=2),
        expires_at=AS_OF + timedelta(hours=1),
    )
    worse_step = make_evidence(
        id=UUID(int=481),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER_B,
        expires_at=AS_OF + timedelta(hours=4),
    )
    better_independent = make_evidence(
        id=UUID(int=482),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER,
        observed_at=AS_OF - timedelta(minutes=30),
        expires_at=AS_OF + timedelta(hours=1),
    )

    assert_qualified_for_every_evidence_order(
        evidence=(better_step, worse_independent, worse_step, better_independent),
        level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        supporting_evidence_ids=(worse_independent.id, better_step.id),
        maximum_expires_at=AS_OF + timedelta(hours=1),
    )


@pytest.mark.parametrize(
    (
        "ranked_kind",
        "winner_id",
        "winner_overrides",
        "loser_id",
        "loser_overrides",
        "shared_id",
        "supporting_evidence_ids",
    ),
    [
        pytest.param(
            IdentityEvidenceKind.STEP_UP_VERIFICATION,
            UUID(int=512),
            {"expires_at": None},
            UUID(int=511),
            {"expires_at": AS_OF + timedelta(hours=4)},
            UUID(int=519),
            (UUID(int=519), UUID(int=512)),
            id="step-up-unbounded-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.STEP_UP_VERIFICATION,
            UUID(int=512),
            {"expires_at": AS_OF + timedelta(hours=5)},
            UUID(int=511),
            {"expires_at": AS_OF + timedelta(hours=4)},
            UUID(int=519),
            (UUID(int=519), UUID(int=512)),
            id="step-up-later-finite-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.STEP_UP_VERIFICATION,
            UUID(int=512),
            {"observed_at": AS_OF - timedelta(minutes=30)},
            UUID(int=511),
            {"observed_at": AS_OF - timedelta(hours=1)},
            UUID(int=519),
            (UUID(int=519), UUID(int=512)),
            id="step-up-later-observed-at",
        ),
        pytest.param(
            IdentityEvidenceKind.STEP_UP_VERIFICATION,
            UUID(int=511),
            {},
            UUID(int=512),
            {},
            UUID(int=519),
            (UUID(int=519), UUID(int=511)),
            id="step-up-lower-uuid",
        ),
        pytest.param(
            IdentityEvidenceKind.INDEPENDENT_CHECK,
            UUID(int=522),
            {"expires_at": None},
            UUID(int=521),
            {"expires_at": AS_OF + timedelta(hours=4)},
            UUID(int=529),
            (UUID(int=522), UUID(int=529)),
            id="independent-unbounded-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.INDEPENDENT_CHECK,
            UUID(int=522),
            {"expires_at": AS_OF + timedelta(hours=5)},
            UUID(int=521),
            {"expires_at": AS_OF + timedelta(hours=4)},
            UUID(int=529),
            (UUID(int=522), UUID(int=529)),
            id="independent-later-finite-expiry",
        ),
        pytest.param(
            IdentityEvidenceKind.INDEPENDENT_CHECK,
            UUID(int=522),
            {"observed_at": AS_OF - timedelta(minutes=30)},
            UUID(int=521),
            {"observed_at": AS_OF - timedelta(hours=1)},
            UUID(int=529),
            (UUID(int=522), UUID(int=529)),
            id="independent-later-observed-at",
        ),
        pytest.param(
            IdentityEvidenceKind.INDEPENDENT_CHECK,
            UUID(int=521),
            {},
            UUID(int=522),
            {},
            UUID(int=529),
            (UUID(int=521), UUID(int=529)),
            id="independent-lower-uuid",
        ),
    ],
)
def test_a3_candidate_ranks_break_pair_ties(
    ranked_kind: IdentityEvidenceKind,
    winner_id: UUID,
    winner_overrides: dict[str, object],
    loser_id: UUID,
    loser_overrides: dict[str, object],
    shared_id: UUID,
    supporting_evidence_ids: tuple[UUID, ...],
) -> None:
    """A3 pair ties apply the full canonical rank of each supporting kind."""

    ranked_provider = (
        TEST_PROVIDER
        if ranked_kind is IdentityEvidenceKind.STEP_UP_VERIFICATION
        else TEST_PROVIDER_B
    )
    shared_kind = (
        IdentityEvidenceKind.INDEPENDENT_CHECK
        if ranked_kind is IdentityEvidenceKind.STEP_UP_VERIFICATION
        else IdentityEvidenceKind.STEP_UP_VERIFICATION
    )
    shared_provider = TEST_PROVIDER_B if ranked_provider == TEST_PROVIDER else TEST_PROVIDER
    ranked_defaults: dict[str, object] = {
        "kind": ranked_kind,
        "provider": ranked_provider,
        "observed_at": AS_OF - timedelta(hours=1),
        "expires_at": AS_OF + timedelta(hours=4),
    }
    winner = make_evidence(id=winner_id, **(ranked_defaults | winner_overrides))
    loser = make_evidence(id=loser_id, **(ranked_defaults | loser_overrides))
    shared = make_evidence(
        id=shared_id,
        kind=shared_kind,
        provider=shared_provider,
        expires_at=AS_OF + timedelta(hours=1),
    )

    assert_qualified_for_every_evidence_order(
        evidence=(winner, loser, shared),
        level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        supporting_evidence_ids=supporting_evidence_ids,
        maximum_expires_at=AS_OF + timedelta(hours=1),
    )


def test_a3_expiry_is_capped_at_twenty_four_hours() -> None:
    """Unbounded A3 evidence receives the mandatory finite 24-hour cap."""

    step_up = make_evidence(
        id=UUID(int=401),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    independent = make_evidence(
        id=UUID(int=402),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=None,
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(step_up, independent),
        revocations=(),
    )

    assert decision.maximum_expires_at == AS_OF + timedelta(hours=24)
    assert decision.maximum_expires_at is not None
    assert decision.maximum_expires_at.tzinfo is UTC


@pytest.mark.parametrize("limiting_kind", list(IdentityEvidenceKind)[-2:])
def test_a3_expiry_is_limited_by_each_finite_evidence(
    limiting_kind: IdentityEvidenceKind,
) -> None:
    """Either A3 support item can impose the earliest finite expiry."""

    step_up_expiry = AS_OF + timedelta(hours=3) if limiting_kind.name.startswith("STEP") else None
    independent_expiry = (
        AS_OF + timedelta(hours=3) if limiting_kind.name.startswith("INDEPENDENT") else None
    )
    step_up = make_evidence(
        id=UUID(int=401),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=step_up_expiry,
    )
    independent = make_evidence(
        id=UUID(int=402),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=independent_expiry,
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(step_up, independent),
        revocations=(),
    )

    assert decision.maximum_expires_at == AS_OF + timedelta(hours=3)


def test_observed_at_equal_to_as_of_is_eligible() -> None:
    """Evidence observed exactly at the evaluation instant is available."""

    item = make_evidence(observed_at=AS_OF, recorded_at=AS_OF)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert decision.level is IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH


def test_future_observed_at_is_ignored() -> None:
    """Evidence observed after the evaluation instant is simply ineligible."""

    future = make_evidence(
        observed_at=AS_OF + timedelta(minutes=1),
        recorded_at=AS_OF + timedelta(minutes=2),
        expires_at=AS_OF + timedelta(days=1),
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(future,),
        revocations=(),
    )

    assert_insufficient(decision)


def test_expiry_equal_to_as_of_is_ineligible() -> None:
    """Evidence is expired when its expiry equals the evaluation instant."""

    expired = make_evidence(expires_at=AS_OF)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(expired,),
        revocations=(),
    )

    assert_insufficient(decision)


def test_active_revocation_excludes_evidence() -> None:
    """A revocation effective before evaluation excludes its evidence."""

    item = make_evidence()
    revocation = make_revocation(evidence_id=item.id)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(revocation,),
    )

    assert_insufficient(decision)


def test_revocation_at_as_of_is_already_effective() -> None:
    """A revocation timestamp equal to as_of already excludes the evidence."""

    item = make_evidence()
    revocation = make_revocation(evidence_id=item.id, revoked_at=AS_OF)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(revocation,),
    )

    assert_insufficient(decision)


def test_future_revocation_is_not_yet_effective() -> None:
    """A future revocation leaves its evidence eligible at the current instant."""

    item = make_evidence()
    revocation = make_revocation(
        evidence_id=item.id,
        revoked_at=AS_OF + timedelta(minutes=1),
        recorded_at=AS_OF + timedelta(minutes=2),
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(revocation,),
    )

    assert decision.level is IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH


def test_recorded_at_does_not_gate_evidence_or_revocations() -> None:
    """Future recorded_at values do not add an undocumented effective-time rule."""

    item = make_evidence(recorded_at=AS_OF + timedelta(days=5))
    future_revocation = make_revocation(
        evidence_id=item.id,
        revoked_at=AS_OF + timedelta(minutes=1),
        recorded_at=AS_OF + timedelta(days=5),
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(future_revocation,),
    )

    assert decision.level is IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH


@pytest.mark.parametrize(
    ("provider", "kind"),
    [
        (UNKNOWN_PROVIDER, IdentityEvidenceKind.DOCUMENT_CHECK),
        (TEST_PROVIDER_C, IdentityEvidenceKind.TRUSTED_VOUCH),
    ],
)
def test_unknown_or_unsupported_provider_pair_is_ignored(
    provider: str,
    kind: IdentityEvidenceKind,
) -> None:
    """Unknown providers and unsupported provider-kind pairs are ineligible only."""

    item = make_evidence(provider=provider, kind=kind)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert_insufficient(decision)


@pytest.mark.parametrize(
    "filtering_overrides",
    [
        pytest.param(
            {"expires_at": AS_OF},
            id="expired",
        ),
        pytest.param(
            {
                "observed_at": AS_OF + timedelta(hours=1),
                "expires_at": AS_OF + timedelta(hours=2),
                "recorded_at": AS_OF + timedelta(hours=1),
            },
            id="future",
        ),
        pytest.param(
            {"provider": UNKNOWN_PROVIDER},
            id="unsupported-provider",
        ),
    ],
)
def test_structural_validation_precedes_candidate_filtering(
    filtering_overrides: dict[str, object],
) -> None:
    """Structural invalidity remains visible when filtering would exclude evidence."""

    invalid = make_evidence(binding_id=UUID(int=2), **filtering_overrides)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(invalid,),
        revocations=(),
    )

    assert decision == EvidencePolicyDecision(
        status=EvidencePolicyStatus.INVALID,
        level=None,
        supporting_evidence_ids=(),
        maximum_expires_at=None,
        reason_codes=(EvidencePolicyReason.CROSS_BINDING_EVIDENCE,),
        policy_version=EVIDENCE_POLICY_VERSION,
    )


def make_structural_case(
    reason: EvidencePolicyReason,
    variant: str = "evidence",
) -> tuple[tuple[IdentityEvidence, ...], tuple[IdentityEvidenceRevocation, ...]]:
    """Build an input containing exactly one requested structural defect."""

    item = make_evidence()
    if reason is EvidencePolicyReason.DUPLICATE_EVIDENCE_ID:
        return (item, item), ()
    if reason is EvidencePolicyReason.DUPLICATE_REVOCATION_ID:
        revocation = make_revocation(evidence_id=item.id)
        return (item,), (revocation, revocation)
    if reason is EvidencePolicyReason.CROSS_BINDING_EVIDENCE:
        return (make_evidence(binding_id=UUID(int=2)),), ()
    if reason is EvidencePolicyReason.CROSS_BINDING_REVOCATION:
        return (item,), (make_revocation(evidence_id=item.id, binding_id=UUID(int=2)),)
    if reason is EvidencePolicyReason.REVOCATION_OF_UNKNOWN_EVIDENCE:
        return (item,), (make_revocation(evidence_id=UUID(int=999)),)
    if reason is EvidencePolicyReason.UNSUPPORTED_SCHEMA_VERSION:
        if variant == "revocation":
            return (item,), (
                make_revocation(
                    evidence_id=item.id,
                    schema_version=UNSUPPORTED_SCHEMA_VERSION,
                ),
            )
        return (make_evidence(schema_version=UNSUPPORTED_SCHEMA_VERSION),), ()
    if reason is EvidencePolicyReason.UNKNOWN_RUNTIME_ENUM:
        object.__setattr__(item, "kind", "document_check")
        return (item,), ()
    if reason is EvidencePolicyReason.INVALID_TEMPORAL_DATA:
        if variant == "revocation":
            revocation = make_revocation(evidence_id=item.id)
            object.__setattr__(revocation, "revoked_at", datetime(2030, 1, 1))
            return (item,), (revocation,)
        object.__setattr__(item, "expires_at", item.observed_at)
        return (item,), ()
    raise AssertionError("unsupported structural test reason")


@pytest.mark.parametrize(
    ("reason", "variant"),
    [
        (EvidencePolicyReason.DUPLICATE_EVIDENCE_ID, "evidence"),
        (EvidencePolicyReason.DUPLICATE_REVOCATION_ID, "revocation"),
        (EvidencePolicyReason.CROSS_BINDING_EVIDENCE, "evidence"),
        (EvidencePolicyReason.CROSS_BINDING_REVOCATION, "revocation"),
        (EvidencePolicyReason.REVOCATION_OF_UNKNOWN_EVIDENCE, "revocation"),
        (EvidencePolicyReason.UNSUPPORTED_SCHEMA_VERSION, "evidence"),
        (EvidencePolicyReason.UNSUPPORTED_SCHEMA_VERSION, "revocation"),
        (EvidencePolicyReason.UNKNOWN_RUNTIME_ENUM, "evidence"),
        (EvidencePolicyReason.INVALID_TEMPORAL_DATA, "evidence"),
        (EvidencePolicyReason.INVALID_TEMPORAL_DATA, "revocation"),
    ],
)
def test_each_structural_defect_returns_invalid(
    reason: EvidencePolicyReason,
    variant: str,
) -> None:
    """Every documented structural defect produces the canonical INVALID shape."""

    evidence, revocations = make_structural_case(reason, variant)

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=evidence,
        revocations=revocations,
    )

    assert decision.status is EvidencePolicyStatus.INVALID
    assert decision.level is None
    assert decision.supporting_evidence_ids == ()
    assert decision.maximum_expires_at is None
    assert decision.reason_codes == (reason,)
    assert decision.policy_version == EVIDENCE_POLICY_VERSION


def test_multiple_structural_reasons_are_complete_unique_and_stable() -> None:
    """Combined structural defects return unique reasons in enum declaration order."""

    item = make_evidence(
        binding_id=UUID(int=2),
        schema_version=UNSUPPORTED_SCHEMA_VERSION,
    )
    object.__setattr__(item, "kind", "unknown-kind")
    object.__setattr__(item, "observed_at", datetime(2030, 1, 1))
    revocation = make_revocation(
        evidence_id=UUID(int=999),
        binding_id=UUID(int=2),
        schema_version=UNSUPPORTED_SCHEMA_VERSION,
    )
    object.__setattr__(revocation, "recorded_at", datetime(2030, 1, 1))

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item, item),
        revocations=(revocation, revocation),
    )

    assert decision.reason_codes == (
        EvidencePolicyReason.DUPLICATE_EVIDENCE_ID,
        EvidencePolicyReason.DUPLICATE_REVOCATION_ID,
        EvidencePolicyReason.CROSS_BINDING_EVIDENCE,
        EvidencePolicyReason.CROSS_BINDING_REVOCATION,
        EvidencePolicyReason.REVOCATION_OF_UNKNOWN_EVIDENCE,
        EvidencePolicyReason.UNSUPPORTED_SCHEMA_VERSION,
        EvidencePolicyReason.UNKNOWN_RUNTIME_ENUM,
        EvidencePolicyReason.INVALID_TEMPORAL_DATA,
    )


def test_evidence_permutations_produce_the_same_decision() -> None:
    """Every input ordering of eligible evidence produces one identical decision."""

    items = (
        make_evidence(
            id=UUID(int=501),
            kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
            provider=TEST_PROVIDER,
        ),
        make_evidence(
            id=UUID(int=502),
            kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
            provider=TEST_PROVIDER_B,
        ),
        make_evidence(id=UUID(int=503), kind=IdentityEvidenceKind.DOCUMENT_CHECK),
    )

    decisions = {
        make_policy().evaluate(
            binding_id=BINDING_ID,
            as_of=AS_OF,
            evidence=ordering,
            revocations=(),
        )
        for ordering in permutations(items)
    }

    assert len(decisions) == 1


def test_revocation_permutations_produce_the_same_decision() -> None:
    """Every input ordering of revocations produces one identical decision."""

    first = make_evidence(id=UUID(int=601))
    second = make_evidence(id=UUID(int=602), kind=IdentityEvidenceKind.TRUSTED_VOUCH)
    revocations = (
        make_revocation(id=UUID(int=1601), evidence_id=first.id),
        make_revocation(id=UUID(int=1602), evidence_id=second.id),
    )

    decisions = {
        make_policy().evaluate(
            binding_id=BINDING_ID,
            as_of=AS_OF,
            evidence=(first, second),
            revocations=ordering,
        )
        for ordering in permutations(revocations)
    }

    assert len(decisions) == 1
    assert_insufficient(decisions.pop())


def test_evaluate_does_not_mutate_input_tuples_or_entities() -> None:
    """Evaluation leaves both tuple order and every immutable entity unchanged."""

    first = make_evidence(id=UUID(int=701))
    second = make_evidence(id=UUID(int=702), kind=IdentityEvidenceKind.TRUSTED_VOUCH)
    revocation = make_revocation(evidence_id=first.id, revoked_at=AS_OF + timedelta(days=1))
    evidence = (second, first)
    revocations = (revocation,)
    evidence_snapshot = tuple(repr(item) for item in evidence)
    revocation_snapshot = tuple(repr(item) for item in revocations)

    make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=evidence,
        revocations=revocations,
    )

    assert evidence == (second, first)
    assert revocations == (revocation,)
    assert tuple(repr(item) for item in evidence) == evidence_snapshot
    assert tuple(repr(item) for item in revocations) == revocation_snapshot


@pytest.mark.parametrize(
    "overrides",
    [
        {"binding_id": SensitiveValue()},
        {"as_of": SensitiveValue()},
        {"evidence": [make_evidence()]},
        {"evidence": (SensitiveValue(),)},
        {"revocations": [make_revocation()]},
        {"revocations": (SensitiveValue(),)},
    ],
)
def test_evaluate_call_contract_errors_are_value_safe(overrides: dict[str, object]) -> None:
    """Invalid public call types raise ValueError without rendering their values."""

    arguments: dict[str, object] = {
        "binding_id": BINDING_ID,
        "as_of": AS_OF,
        "evidence": (),
        "revocations": (),
    }
    arguments.update(overrides)

    with pytest.raises(ValueError) as error:
        make_policy().evaluate(**arguments)  # type: ignore[arg-type]

    message = str(error.value)
    assert "sensitive-provider-schema-opaque-repr" not in message
    assert OPAQUE_REFERENCE not in message
    assert TEST_PROVIDER not in message
    assert TEST_SCHEMA_VERSION not in message


def test_evaluate_revalidates_tampered_rules_without_sensitive_output() -> None:
    """Evaluation safely rejects a policy whose frozen rules field was corrupted."""

    policy = make_policy()
    object.__setattr__(policy, "rules", SensitiveValue())

    with pytest.raises(ValueError) as error:
        policy.evaluate(
            binding_id=BINDING_ID,
            as_of=AS_OF,
            evidence=(),
            revocations=(),
        )

    assert "sensitive-provider-schema-opaque-repr" not in str(error.value)


def test_decision_and_evaluation_error_do_not_expose_opaque_reference() -> None:
    """Neither successful output nor call-contract failure reveals opaque evidence data."""

    item = make_evidence(opaque_reference=OPAQUE_REFERENCE)
    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=AS_OF,
        evidence=(item,),
        revocations=(),
    )

    assert OPAQUE_REFERENCE not in repr(decision)
    with pytest.raises(ValueError) as error:
        make_policy().evaluate(
            binding_id=BINDING_ID,
            as_of=AS_OF,
            evidence=(SensitiveValue(),),  # type: ignore[arg-type]
            revocations=(),
        )
    assert OPAQUE_REFERENCE not in str(error.value)


def test_as_of_is_normalized_to_utc() -> None:
    """An aware offset as_of is normalized before calculating the A3 boundary."""

    offset_as_of = AS_OF.astimezone(timezone(timedelta(hours=5, minutes=30)))
    step_up = make_evidence(
        id=UUID(int=801),
        kind=IdentityEvidenceKind.STEP_UP_VERIFICATION,
        provider=TEST_PROVIDER,
        expires_at=None,
    )
    independent = make_evidence(
        id=UUID(int=802),
        kind=IdentityEvidenceKind.INDEPENDENT_CHECK,
        provider=TEST_PROVIDER_B,
        expires_at=None,
    )

    decision = make_policy().evaluate(
        binding_id=BINDING_ID,
        as_of=offset_as_of,
        evidence=(step_up, independent),
        revocations=(),
    )

    assert decision.maximum_expires_at == AS_OF + timedelta(hours=24)
    assert decision.maximum_expires_at is not None
    assert decision.maximum_expires_at.tzinfo is UTC


def test_evaluate_signature_excludes_prior_level_and_fallback() -> None:
    """The public signature contains only binding, instant, evidence, and revocations."""

    parameters = signature(IdentityEvidencePolicyV1.evaluate).parameters

    assert tuple(parameters) == ("self", "binding_id", "as_of", "evidence", "revocations")
    assert all(parameters[name].kind.name == "KEYWORD_ONLY" for name in tuple(parameters)[1:])
    assert "prior_effective_level" not in parameters
    assert "fallback_event_id" not in parameters
