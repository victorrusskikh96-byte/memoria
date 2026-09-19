from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from memoria.domain.trust import (
    AuthorityRole,
    AuthorizationDecision,
    AuthorizationRequest,
    ConsentStatus,
    DecisionOutcome,
    DecisionReason,
    EvidenceLevel,
    IdentityAssuranceLevel,
    LegacyState,
    RightsBasis,
    SensitiveAction,
    TrustPolicy,
)

REQUEST_ID = UUID("00000000-0000-0000-0000-000000000001")
SUBJECT_ID = UUID("00000000-0000-0000-0000-000000000002")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
LEGACY_ID = UUID("00000000-0000-0000-0000-000000000004")
CONSENT_ID = UUID("00000000-0000-0000-0000-000000000005")
AUTHORITY_ID = UUID("00000000-0000-0000-0000-000000000006")
PLAN_ID = UUID("00000000-0000-0000-0000-000000000007")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000008")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000009")
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def subject_memory_request() -> AuthorizationRequest:
    return AuthorizationRequest(
        request_id=REQUEST_ID,
        requested_at=NOW,
        actor_id=SUBJECT_ID,
        subject_id=SUBJECT_ID,
        legacy_id=LEGACY_ID,
        action=SensitiveAction.ADD_TEXT_MEMORY,
        actor_role=AuthorityRole.SUBJECT,
        identity_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        legacy_state=LegacyState.ACTIVE,
        consent_status=ConsentStatus.GRANTED,
        consent_receipt_id=CONSENT_ID,
        rights_basis=RightsBasis.SUBJECT_CONTROLLED,
    )


def evaluate(request: AuthorizationRequest) -> AuthorizationDecision:
    return TrustPolicy.evaluate(request, decision_id=DECISION_ID, evaluated_at=NOW)


def test_subject_can_add_memory_when_all_policy_inputs_are_valid() -> None:
    decision = evaluate(subject_memory_request())

    assert decision.outcome is DecisionOutcome.ALLOW
    assert decision.reason_codes == (DecisionReason.POLICY_SATISFIED,)
    assert len(decision.request_fingerprint) == 64


def test_non_subject_requires_an_explicit_authority_grant() -> None:
    request = replace(
        subject_memory_request(),
        actor_id=ACTOR_ID,
        actor_role=AuthorityRole.CONTRIBUTOR,
        rights_basis=RightsBasis.CONTRIBUTOR_OWNED,
    )

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (DecisionReason.AUTHORITY_GRANT_MISSING,)


def test_revoked_consent_fails_closed() -> None:
    request = replace(subject_memory_request(), consent_status=ConsentStatus.REVOKED)

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (DecisionReason.CONSENT_NOT_GRANTED,)


def test_actor_cannot_claim_the_subject_role_for_another_person() -> None:
    request = replace(subject_memory_request(), actor_id=ACTOR_ID)

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (
        DecisionReason.SUBJECT_ROLE_MISMATCH,
        DecisionReason.AUTHORITY_GRANT_MISSING,
    )


def test_unknown_rights_basis_fails_closed() -> None:
    request = replace(subject_memory_request(), rights_basis=RightsBasis.UNKNOWN)

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (DecisionReason.RIGHTS_BASIS_INSUFFICIENT,)


def test_synthetic_voice_requires_a3_assurance() -> None:
    request = replace(
        subject_memory_request(),
        action=SensitiveAction.CREATE_SYNTHETIC_VOICE,
        identity_assurance=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
    )

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (DecisionReason.IDENTITY_ASSURANCE_TOO_LOW,)


def test_successor_can_activate_memorial_only_with_complete_controls() -> None:
    request = AuthorizationRequest(
        request_id=REQUEST_ID,
        requested_at=NOW,
        actor_id=ACTOR_ID,
        subject_id=SUBJECT_ID,
        legacy_id=LEGACY_ID,
        action=SensitiveAction.ACTIVATE_MEMORIAL,
        actor_role=AuthorityRole.SUCCESSOR,
        identity_assurance=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        legacy_state=LegacyState.VERIFICATION_PENDING,
        consent_status=None,
        rights_basis=RightsBasis.SUCCESSION_PLAN,
        authority_grant_id=AUTHORITY_ID,
        succession_plan_id=PLAN_ID,
        evidence_level=EvidenceLevel.VERIFIED_THIRD_PARTY,
        evidence_ids=(EVIDENCE_ID,),
        cooling_period_elapsed=True,
        required_approvals_met=True,
    )

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.ALLOW
    assert decision.reason_codes == (DecisionReason.POLICY_SATISFIED,)


def test_memorial_activation_reports_every_missing_control() -> None:
    request = AuthorizationRequest(
        request_id=REQUEST_ID,
        requested_at=NOW,
        actor_id=ACTOR_ID,
        subject_id=SUBJECT_ID,
        legacy_id=LEGACY_ID,
        action=SensitiveAction.ACTIVATE_MEMORIAL,
        actor_role=AuthorityRole.SUCCESSOR,
        identity_assurance=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        legacy_state=LegacyState.VERIFICATION_PENDING,
        consent_status=None,
        rights_basis=RightsBasis.SUCCESSION_PLAN,
        authority_grant_id=AUTHORITY_ID,
    )

    decision = evaluate(request)

    assert decision.outcome is DecisionOutcome.DENY
    assert decision.reason_codes == (
        DecisionReason.SUCCESSION_PLAN_MISSING,
        DecisionReason.SUCCESSION_EVIDENCE_INSUFFICIENT,
        DecisionReason.COOLING_PERIOD_INCOMPLETE,
        DecisionReason.APPROVAL_THRESHOLD_NOT_MET,
    )


def test_fingerprint_changes_when_an_authorization_fact_changes() -> None:
    granted = subject_memory_request()
    revoked = replace(granted, consent_status=ConsentStatus.REVOKED)

    assert granted.fingerprint() == granted.fingerprint()
    assert granted.fingerprint() != revoked.fingerprint()


def test_request_rejects_a_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(subject_memory_request(), requested_at=datetime(2026, 9, 19, 12, 0))
