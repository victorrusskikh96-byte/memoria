from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from memoria.domain.trust.types import (
    AuthorityRole,
    ConsentStatus,
    EvidenceLevel,
    IdentityAssuranceLevel,
    LegacyState,
)

POLICY_VERSION = "trust-kernel/1.0"


class SensitiveAction(StrEnum):
    ADD_TEXT_MEMORY = "add_text_memory"
    EXPORT_LEGACY = "export_legacy"
    ACTIVATE_MEMORIAL = "activate_memorial"
    CREATE_SYNTHETIC_VOICE = "create_synthetic_voice"


class RightsBasis(StrEnum):
    SUBJECT_CONTROLLED = "subject_controlled"
    CONTRIBUTOR_OWNED = "contributor_owned"
    LICENSED = "licensed"
    STEWARDSHIP_GRANT = "stewardship_grant"
    SUCCESSION_PLAN = "succession_plan"
    UNKNOWN = "unknown"
    DISPUTED = "disputed"


class DecisionOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class DecisionReason(StrEnum):
    POLICY_SATISFIED = "policy_satisfied"
    SUBJECT_ROLE_MISMATCH = "subject_role_mismatch"
    LEGACY_STATE_FORBIDS_ACTION = "legacy_state_forbids_action"
    ROLE_FORBIDDEN = "role_forbidden"
    IDENTITY_ASSURANCE_TOO_LOW = "identity_assurance_too_low"
    CONSENT_NOT_GRANTED = "consent_not_granted"
    CONSENT_RECEIPT_MISSING = "consent_receipt_missing"
    AUTHORITY_GRANT_MISSING = "authority_grant_missing"
    RIGHTS_BASIS_INSUFFICIENT = "rights_basis_insufficient"
    SUCCESSION_PLAN_MISSING = "succession_plan_missing"
    SUCCESSION_EVIDENCE_INSUFFICIENT = "succession_evidence_insufficient"
    COOLING_PERIOD_INCOMPLETE = "cooling_period_incomplete"
    APPROVAL_THRESHOLD_NOT_MET = "approval_threshold_not_met"


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    request_id: UUID
    requested_at: datetime
    actor_id: UUID
    subject_id: UUID
    legacy_id: UUID
    action: SensitiveAction
    actor_role: AuthorityRole
    identity_assurance: IdentityAssuranceLevel
    legacy_state: LegacyState
    consent_status: ConsentStatus | None
    rights_basis: RightsBasis
    consent_receipt_id: UUID | None = None
    authority_grant_id: UUID | None = None
    succession_plan_id: UUID | None = None
    evidence_level: EvidenceLevel | None = None
    evidence_ids: tuple[UUID, ...] = ()
    cooling_period_elapsed: bool = False
    required_approvals_met: bool = False

    def __post_init__(self) -> None:
        if self.requested_at.tzinfo is None or self.requested_at.utcoffset() is None:
            raise ValueError("requested_at must be timezone-aware")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must not contain duplicates")

    def to_audit_payload(self) -> dict[str, object]:
        return {
            "request_id": str(self.request_id),
            "requested_at": self.requested_at.astimezone(UTC).isoformat(),
            "actor_id": str(self.actor_id),
            "subject_id": str(self.subject_id),
            "legacy_id": str(self.legacy_id),
            "action": self.action.value,
            "actor_role": self.actor_role.value,
            "identity_assurance": int(self.identity_assurance),
            "legacy_state": self.legacy_state.value,
            "consent_status": self.consent_status.value if self.consent_status else None,
            "rights_basis": self.rights_basis.value,
            "consent_receipt_id": (
                str(self.consent_receipt_id) if self.consent_receipt_id else None
            ),
            "authority_grant_id": (
                str(self.authority_grant_id) if self.authority_grant_id else None
            ),
            "succession_plan_id": (
                str(self.succession_plan_id) if self.succession_plan_id else None
            ),
            "evidence_level": int(self.evidence_level) if self.evidence_level else None,
            "evidence_ids": sorted(str(evidence_id) for evidence_id in self.evidence_ids),
            "cooling_period_elapsed": self.cooling_period_elapsed,
            "required_approvals_met": self.required_approvals_met,
        }

    def fingerprint(self) -> str:
        canonical_payload = json.dumps(
            self.to_audit_payload(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    decision_id: UUID
    request_id: UUID
    outcome: DecisionOutcome
    reason_codes: tuple[DecisionReason, ...]
    policy_version: str
    evaluated_at: datetime
    request_fingerprint: str

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        if not self.reason_codes:
            raise ValueError("an authorization decision must contain at least one reason")
        if self.outcome is DecisionOutcome.ALLOW and self.reason_codes != (
            DecisionReason.POLICY_SATISFIED,
        ):
            raise ValueError("an allowed decision must contain only policy_satisfied")
        if self.outcome is DecisionOutcome.DENY and DecisionReason.POLICY_SATISFIED in (
            self.reason_codes
        ):
            raise ValueError("a denied decision cannot contain policy_satisfied")


@dataclass(frozen=True, slots=True)
class _ActionRule:
    allowed_roles: frozenset[AuthorityRole]
    minimum_assurance: IdentityAssuranceLevel
    allowed_states: frozenset[LegacyState]
    allowed_rights: frozenset[RightsBasis]
    requires_consent: bool = False
    requires_succession_evidence: bool = False


_ACTION_RULES: dict[SensitiveAction, _ActionRule] = {
    SensitiveAction.ADD_TEXT_MEMORY: _ActionRule(
        allowed_roles=frozenset(
            {AuthorityRole.SUBJECT, AuthorityRole.CONTRIBUTOR, AuthorityRole.STEWARD}
        ),
        minimum_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        allowed_states=frozenset({LegacyState.DRAFT, LegacyState.ACTIVE, LegacyState.MEMORIAL}),
        allowed_rights=frozenset(
            {
                RightsBasis.SUBJECT_CONTROLLED,
                RightsBasis.CONTRIBUTOR_OWNED,
                RightsBasis.LICENSED,
                RightsBasis.STEWARDSHIP_GRANT,
            }
        ),
        requires_consent=True,
    ),
    SensitiveAction.EXPORT_LEGACY: _ActionRule(
        allowed_roles=frozenset({AuthorityRole.SUBJECT, AuthorityRole.SUCCESSOR}),
        minimum_assurance=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        allowed_states=frozenset({LegacyState.ACTIVE, LegacyState.MEMORIAL, LegacyState.ARCHIVED}),
        allowed_rights=frozenset({RightsBasis.SUBJECT_CONTROLLED, RightsBasis.STEWARDSHIP_GRANT}),
        requires_consent=True,
    ),
    SensitiveAction.ACTIVATE_MEMORIAL: _ActionRule(
        allowed_roles=frozenset({AuthorityRole.SUCCESSOR, AuthorityRole.REVIEWER}),
        minimum_assurance=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        allowed_states=frozenset({LegacyState.VERIFICATION_PENDING}),
        allowed_rights=frozenset({RightsBasis.STEWARDSHIP_GRANT, RightsBasis.SUCCESSION_PLAN}),
        requires_succession_evidence=True,
    ),
    SensitiveAction.CREATE_SYNTHETIC_VOICE: _ActionRule(
        allowed_roles=frozenset({AuthorityRole.SUBJECT}),
        minimum_assurance=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
        allowed_states=frozenset({LegacyState.ACTIVE}),
        allowed_rights=frozenset({RightsBasis.SUBJECT_CONTROLLED}),
        requires_consent=True,
    ),
}


class TrustPolicy:
    """Pure, deterministic, deny-by-default authorization policy."""

    @staticmethod
    def evaluate(
        request: AuthorizationRequest,
        *,
        decision_id: UUID | None = None,
        evaluated_at: datetime | None = None,
    ) -> AuthorizationDecision:
        rule = _ACTION_RULES[request.action]
        reasons: list[DecisionReason] = []

        actor_is_subject = request.actor_id == request.subject_id
        if actor_is_subject != (request.actor_role is AuthorityRole.SUBJECT):
            reasons.append(DecisionReason.SUBJECT_ROLE_MISMATCH)

        if request.legacy_state not in rule.allowed_states:
            reasons.append(DecisionReason.LEGACY_STATE_FORBIDS_ACTION)

        if request.actor_role not in rule.allowed_roles:
            reasons.append(DecisionReason.ROLE_FORBIDDEN)

        if request.identity_assurance < rule.minimum_assurance:
            reasons.append(DecisionReason.IDENTITY_ASSURANCE_TOO_LOW)

        if rule.requires_consent:
            if request.consent_status is not ConsentStatus.GRANTED:
                reasons.append(DecisionReason.CONSENT_NOT_GRANTED)
            if request.consent_receipt_id is None:
                reasons.append(DecisionReason.CONSENT_RECEIPT_MISSING)

        if not actor_is_subject and request.authority_grant_id is None:
            reasons.append(DecisionReason.AUTHORITY_GRANT_MISSING)

        if request.rights_basis not in rule.allowed_rights:
            reasons.append(DecisionReason.RIGHTS_BASIS_INSUFFICIENT)

        if rule.requires_succession_evidence:
            TrustPolicy._evaluate_succession(request, reasons)

        outcome = DecisionOutcome.DENY if reasons else DecisionOutcome.ALLOW
        reason_codes = tuple(reasons) or (DecisionReason.POLICY_SATISFIED,)

        return AuthorizationDecision(
            decision_id=decision_id or uuid4(),
            request_id=request.request_id,
            outcome=outcome,
            reason_codes=reason_codes,
            policy_version=POLICY_VERSION,
            evaluated_at=evaluated_at or datetime.now(UTC),
            request_fingerprint=request.fingerprint(),
        )

    @staticmethod
    def _evaluate_succession(
        request: AuthorizationRequest,
        reasons: list[DecisionReason],
    ) -> None:
        if request.succession_plan_id is None:
            reasons.append(DecisionReason.SUCCESSION_PLAN_MISSING)
        if (
            request.evidence_level is None
            or request.evidence_level < EvidenceLevel.VERIFIED_THIRD_PARTY
            or not request.evidence_ids
        ):
            reasons.append(DecisionReason.SUCCESSION_EVIDENCE_INSUFFICIENT)
        if not request.cooling_period_elapsed:
            reasons.append(DecisionReason.COOLING_PERIOD_INCOMPLETE)
        if not request.required_approvals_met:
            reasons.append(DecisionReason.APPROVAL_THRESHOLD_NOT_MET)
