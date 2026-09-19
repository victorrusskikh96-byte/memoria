from memoria.domain.trust import EvidenceLevel, IdentityAssuranceLevel, LegacyState


def test_assurance_order_is_monotonic() -> None:
    assert IdentityAssuranceLevel.A3_HIGH_ASSURANCE > IdentityAssuranceLevel.A0_UNVERIFIED


def test_subject_authored_evidence_outranks_generated_inference() -> None:
    assert EvidenceLevel.SUBJECT_AUTHORED > EvidenceLevel.GENERATED_INFERENCE


def test_disputed_is_an_explicit_legacy_state() -> None:
    assert LegacyState.DISPUTED.value == "disputed"
