"""Define immutable contracts and deterministic Identity Evidence Policy V1."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

from memoria.domain.identity.entities import (
    _AUTHORITY_OR_PROVIDER_PATTERN,
    IdentityEvidence,
    IdentityEvidenceRevocation,
    _normalize_datetime,
    _validate_pattern,
    _validate_printable_ascii_version,
    _validate_uuid,
)
from memoria.domain.identity.types import IdentityEvidenceKind
from memoria.domain.trust.types import IdentityAssuranceLevel

EVIDENCE_POLICY_VERSION = "identity-evidence/1.0"


class EvidencePolicyStatus(StrEnum):
    """Classify the outcome of an evidence policy decision."""

    QUALIFIED = "qualified"
    INSUFFICIENT = "insufficient"
    INVALID = "invalid"


class EvidencePolicyReason(StrEnum):
    """Identify a documented reason for an evidence policy decision."""

    QUALIFIED = "qualified"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    DUPLICATE_EVIDENCE_ID = "duplicate_evidence_id"
    DUPLICATE_REVOCATION_ID = "duplicate_revocation_id"
    CROSS_BINDING_EVIDENCE = "cross_binding_evidence"
    CROSS_BINDING_REVOCATION = "cross_binding_revocation"
    REVOCATION_OF_UNKNOWN_EVIDENCE = "revocation_of_unknown_evidence"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNKNOWN_RUNTIME_ENUM = "unknown_runtime_enum"
    INVALID_TEMPORAL_DATA = "invalid_temporal_data"


@dataclass(frozen=True, slots=True)
class EvidenceProviderRule:
    """Allow one canonical provider to supply one evidence kind."""

    provider: str
    evidence_kind: IdentityEvidenceKind

    def __post_init__(self) -> None:
        """Validate the provider identifier and evidence kind."""

        _validate_pattern("provider", self.provider, _AUTHORITY_OR_PROVIDER_PATTERN)
        if not isinstance(self.evidence_kind, IdentityEvidenceKind):
            raise ValueError("evidence_kind must be an IdentityEvidenceKind")


@dataclass(frozen=True, slots=True)
class EvidencePolicyRulesV1:
    """Hold the immutable server-side rules for Evidence Policy V1."""

    policy_version: ClassVar[str] = EVIDENCE_POLICY_VERSION

    provider_rules: frozenset[EvidenceProviderRule]
    supported_schema_versions: frozenset[str]

    def __post_init__(self) -> None:
        """Validate the immutable provider registry and schema versions."""

        if not isinstance(self.provider_rules, frozenset):
            raise ValueError("provider_rules must be a frozenset")
        if not self.provider_rules:
            raise ValueError("provider registry configuration must not be empty")
        if not all(isinstance(rule, EvidenceProviderRule) for rule in self.provider_rules):
            raise ValueError("provider_rules must contain only EvidenceProviderRule values")

        if not isinstance(self.supported_schema_versions, frozenset):
            raise ValueError("supported_schema_versions must be a frozenset")
        if not self.supported_schema_versions:
            raise ValueError("supported schema versions configuration must not be empty")
        for schema_version in self.supported_schema_versions:
            _validate_printable_ascii_version("schema_version", schema_version)


@dataclass(frozen=True, slots=True)
class EvidencePolicyDecision:
    """Represent one immutable result produced by Evidence Policy V1."""

    status: EvidencePolicyStatus
    level: IdentityAssuranceLevel | None
    supporting_evidence_ids: tuple[UUID, ...]
    maximum_expires_at: datetime | None
    reason_codes: tuple[EvidencePolicyReason, ...]
    policy_version: str

    def __post_init__(self) -> None:
        """Validate the decision shape and normalize its optional expiry."""

        if not isinstance(self.status, EvidencePolicyStatus):
            raise ValueError("status must be an EvidencePolicyStatus")
        if self.level is not None and not isinstance(self.level, IdentityAssuranceLevel):
            raise ValueError("level must be an IdentityAssuranceLevel or None")
        if not isinstance(self.supporting_evidence_ids, tuple) or not all(
            isinstance(evidence_id, UUID) for evidence_id in self.supporting_evidence_ids
        ):
            raise ValueError("supporting_evidence_ids must contain only UUID values")
        if len(set(self.supporting_evidence_ids)) != len(self.supporting_evidence_ids):
            raise ValueError("supporting_evidence_ids must be unique")
        if not isinstance(self.reason_codes, tuple) or not all(
            isinstance(reason, EvidencePolicyReason) for reason in self.reason_codes
        ):
            raise ValueError("reason_codes must contain only EvidencePolicyReason values")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")
        if self.policy_version != EVIDENCE_POLICY_VERSION:
            raise ValueError("policy_version must identify Evidence Policy V1")

        maximum_expires_at = None
        if self.maximum_expires_at is not None:
            maximum_expires_at = _normalize_datetime("maximum_expires_at", self.maximum_expires_at)

        self._validate_status_shape(maximum_expires_at)
        object.__setattr__(self, "maximum_expires_at", maximum_expires_at)

    def _validate_status_shape(self, maximum_expires_at: datetime | None) -> None:
        """Enforce the local level and supporting-evidence invariants by status."""

        if self.status is EvidencePolicyStatus.QUALIFIED:
            if self.level not in (
                IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
                IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
                IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
            ):
                raise ValueError("QUALIFIED requires an assurance level from A1 through A3")
            if not self.supporting_evidence_ids:
                raise ValueError("QUALIFIED requires supporting evidence IDs")
        elif self.status is EvidencePolicyStatus.INSUFFICIENT:
            if self.level is not IdentityAssuranceLevel.A0_UNVERIFIED:
                raise ValueError("INSUFFICIENT requires assurance level A0")
            if self.supporting_evidence_ids:
                raise ValueError("INSUFFICIENT must not contain supporting evidence IDs")
        else:
            if self.level is not None:
                raise ValueError("INVALID requires no assurance level")
            if self.supporting_evidence_ids:
                raise ValueError("INVALID must not contain supporting evidence IDs")
            if maximum_expires_at is not None:
                raise ValueError("INVALID must not contain maximum_expires_at")


_KIND_POSITION = {kind: position for position, kind in enumerate(IdentityEvidenceKind)}
_A3_LIFETIME = timedelta(hours=24)


def _schema_version_is_supported(
    schema_version: object,
    supported_schema_versions: frozenset[str],
) -> bool:
    """Return whether a schema version is canonical and explicitly supported."""

    try:
        _validate_printable_ascii_version("schema_version", schema_version)
    except ValueError:
        return False
    return schema_version in supported_schema_versions


def _datetime_is_canonical(value: object) -> bool:
    """Return whether a value is an aware datetime already represented in UTC."""

    try:
        normalized = _normalize_datetime("temporal field", value)
    except (TypeError, ValueError, OverflowError):
        return False
    return isinstance(value, datetime) and value.tzinfo is UTC and value == normalized


def _evidence_has_invalid_temporal_data(item: IdentityEvidence) -> bool:
    """Return whether an evidence entity violates canonical temporal invariants."""

    if not _datetime_is_canonical(item.observed_at) or not _datetime_is_canonical(item.recorded_at):
        return True
    if item.expires_at is None:
        return False
    return not _datetime_is_canonical(item.expires_at) or item.expires_at <= item.observed_at


def _revocation_has_invalid_temporal_data(item: IdentityEvidenceRevocation) -> bool:
    """Return whether a revocation entity violates canonical temporal invariants."""

    return not _datetime_is_canonical(item.revoked_at) or not _datetime_is_canonical(
        item.recorded_at
    )


def _ordered_reasons(
    reasons: set[EvidencePolicyReason],
) -> tuple[EvidencePolicyReason, ...]:
    """Return unique policy reasons in their declaration order."""

    return tuple(reason for reason in EvidencePolicyReason if reason in reasons)


def _structural_reasons(
    *,
    binding_id: UUID,
    evidence: tuple[IdentityEvidence, ...],
    revocations: tuple[IdentityEvidenceRevocation, ...],
    supported_schema_versions: frozenset[str],
) -> tuple[EvidencePolicyReason, ...]:
    """Collect every structural defect without depending on collection order."""

    reasons: set[EvidencePolicyReason] = set()
    evidence_ids = [item.id for item in evidence]
    revocation_ids = [item.id for item in revocations]
    known_evidence_ids = set(evidence_ids)

    if len(known_evidence_ids) != len(evidence_ids):
        reasons.add(EvidencePolicyReason.DUPLICATE_EVIDENCE_ID)
    if len(set(revocation_ids)) != len(revocation_ids):
        reasons.add(EvidencePolicyReason.DUPLICATE_REVOCATION_ID)
    if any(item.binding_id != binding_id for item in evidence):
        reasons.add(EvidencePolicyReason.CROSS_BINDING_EVIDENCE)
    if any(item.binding_id != binding_id for item in revocations):
        reasons.add(EvidencePolicyReason.CROSS_BINDING_REVOCATION)
    if any(item.evidence_id not in known_evidence_ids for item in revocations):
        reasons.add(EvidencePolicyReason.REVOCATION_OF_UNKNOWN_EVIDENCE)
    if any(
        not _schema_version_is_supported(item.schema_version, supported_schema_versions)
        for item in evidence
    ) or any(
        not _schema_version_is_supported(item.schema_version, supported_schema_versions)
        for item in revocations
    ):
        reasons.add(EvidencePolicyReason.UNSUPPORTED_SCHEMA_VERSION)
    if any(not isinstance(item.kind, IdentityEvidenceKind) for item in evidence):
        reasons.add(EvidencePolicyReason.UNKNOWN_RUNTIME_ENUM)
    if any(_evidence_has_invalid_temporal_data(item) for item in evidence) or any(
        _revocation_has_invalid_temporal_data(item) for item in revocations
    ):
        reasons.add(EvidencePolicyReason.INVALID_TEMPORAL_DATA)

    return _ordered_reasons(reasons)


def _active_evidence(
    *,
    as_of: datetime,
    evidence: tuple[IdentityEvidence, ...],
    revocations: tuple[IdentityEvidenceRevocation, ...],
    provider_rules: frozenset[EvidenceProviderRule],
) -> tuple[IdentityEvidence, ...]:
    """Filter evidence by time, provider-kind rules, and effective revocations."""

    allowed_pairs = {(rule.provider, rule.evidence_kind) for rule in provider_rules}
    revoked_ids = {
        revocation.evidence_id for revocation in revocations if revocation.revoked_at <= as_of
    }
    return tuple(
        item
        for item in evidence
        if item.observed_at <= as_of
        and (item.expires_at is None or as_of < item.expires_at)
        and (item.provider, item.kind) in allowed_pairs
        and item.id not in revoked_ids
    )


def _candidate_rank(item: IdentityEvidence) -> tuple[bool, datetime, datetime, int]:
    """Return the documented canonical rank for one eligible evidence item."""

    return (
        item.expires_at is None,
        item.expires_at or datetime.min.replace(tzinfo=UTC),
        item.observed_at,
        -item.id.int,
    )


def _best_candidate(
    evidence: tuple[IdentityEvidence, ...],
    kind: IdentityEvidenceKind,
) -> IdentityEvidence | None:
    """Select the highest-ranked eligible item of one evidence kind."""

    candidates = (item for item in evidence if item.kind is kind)
    return max(candidates, key=_candidate_rank, default=None)


def _select_a2_candidate(evidence: tuple[IdentityEvidence, ...]) -> IdentityEvidence | None:
    """Select the canonical winner across the two alternative A2 grounds."""

    candidates = tuple(
        item
        for kind in (IdentityEvidenceKind.DOCUMENT_CHECK, IdentityEvidenceKind.TRUSTED_VOUCH)
        if (item := _best_candidate(evidence, kind)) is not None
    )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.expires_at is None,
            item.expires_at or datetime.min.replace(tzinfo=UTC),
            item.observed_at,
            -_KIND_POSITION[item.kind],
            -item.id.int,
        ),
    )


def _supporting_ids(items: tuple[IdentityEvidence, ...]) -> tuple[UUID, ...]:
    """Order supporting identifiers by evidence-kind declaration and UUID."""

    return tuple(
        item.id for item in sorted(items, key=lambda item: (_KIND_POSITION[item.kind], item.id))
    )


def _a3_expiry(
    *,
    as_of: datetime,
    step_up: IdentityEvidence,
    independent: IdentityEvidence,
) -> datetime:
    """Calculate the finite 24-hour-capped expiry for one permissible A3 pair."""

    boundaries = [as_of + _A3_LIFETIME]
    boundaries.extend(
        item.expires_at for item in (step_up, independent) if item.expires_at is not None
    )
    return min(boundaries)


def _select_a3_pair(
    *,
    as_of: datetime,
    evidence: tuple[IdentityEvidence, ...],
) -> tuple[IdentityEvidence, IdentityEvidence] | None:
    """Select the best permissible cross-provider A3 pair by canonical ranking."""

    step_ups = tuple(
        item for item in evidence if item.kind is IdentityEvidenceKind.STEP_UP_VERIFICATION
    )
    independent_checks = tuple(
        item for item in evidence if item.kind is IdentityEvidenceKind.INDEPENDENT_CHECK
    )
    pairs = tuple(
        (step_up, independent)
        for step_up in step_ups
        for independent in independent_checks
        if step_up.provider != independent.provider
    )
    if not pairs:
        return None

    def pair_rank(
        pair: tuple[IdentityEvidence, IdentityEvidence],
    ) -> tuple[
        datetime,
        tuple[bool, datetime, datetime, int],
        tuple[bool, datetime, datetime, int],
        tuple[int, ...],
    ]:
        """Return the documented canonical rank for one permissible A3 pair."""

        step_up, independent = pair
        ordered_ids = _supporting_ids(pair)
        return (
            _a3_expiry(as_of=as_of, step_up=step_up, independent=independent),
            _candidate_rank(step_up),
            _candidate_rank(independent),
            tuple(-item_id.int for item_id in ordered_ids),
        )

    return max(pairs, key=pair_rank)


@dataclass(frozen=True, slots=True)
class IdentityEvidencePolicyV1:
    """Evaluate immutable identity evidence under deterministic V1 rules."""

    rules: EvidencePolicyRulesV1

    def __post_init__(self) -> None:
        """Require the exact immutable V1 rules contract."""

        if not isinstance(self.rules, EvidencePolicyRulesV1):
            raise ValueError("rules must be an EvidencePolicyRulesV1")

    def evaluate(
        self,
        *,
        binding_id: UUID,
        as_of: datetime,
        evidence: tuple[IdentityEvidence, ...],
        revocations: tuple[IdentityEvidenceRevocation, ...],
    ) -> EvidencePolicyDecision:
        """Return the highest deterministic assurance decision supported at one instant."""

        self._validate_call(
            binding_id=binding_id,
            as_of=as_of,
            evidence=evidence,
            revocations=revocations,
        )
        normalized_as_of = _normalize_datetime("as_of", as_of)
        reasons = _structural_reasons(
            binding_id=binding_id,
            evidence=evidence,
            revocations=revocations,
            supported_schema_versions=self.rules.supported_schema_versions,
        )
        if reasons:
            return EvidencePolicyDecision(
                status=EvidencePolicyStatus.INVALID,
                level=None,
                supporting_evidence_ids=(),
                maximum_expires_at=None,
                reason_codes=reasons,
                policy_version=EVIDENCE_POLICY_VERSION,
            )

        active = _active_evidence(
            as_of=normalized_as_of,
            evidence=evidence,
            revocations=revocations,
            provider_rules=self.rules.provider_rules,
        )
        a3_pair = _select_a3_pair(as_of=normalized_as_of, evidence=active)
        if a3_pair is not None:
            step_up, independent = a3_pair
            return self._qualified(
                level=IdentityAssuranceLevel.A3_HIGH_ASSURANCE,
                supporting_evidence=a3_pair,
                maximum_expires_at=_a3_expiry(
                    as_of=normalized_as_of,
                    step_up=step_up,
                    independent=independent,
                ),
            )

        a2_candidate = _select_a2_candidate(active)
        if a2_candidate is not None:
            return self._qualified(
                level=IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
                supporting_evidence=(a2_candidate,),
                maximum_expires_at=a2_candidate.expires_at,
            )

        a1_candidate = _best_candidate(active, IdentityEvidenceKind.ACCOUNT_CHANNEL_VERIFICATION)
        if a1_candidate is not None:
            return self._qualified(
                level=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
                supporting_evidence=(a1_candidate,),
                maximum_expires_at=a1_candidate.expires_at,
            )

        return EvidencePolicyDecision(
            status=EvidencePolicyStatus.INSUFFICIENT,
            level=IdentityAssuranceLevel.A0_UNVERIFIED,
            supporting_evidence_ids=(),
            maximum_expires_at=None,
            reason_codes=(EvidencePolicyReason.INSUFFICIENT_EVIDENCE,),
            policy_version=EVIDENCE_POLICY_VERSION,
        )

    def _validate_call(
        self,
        *,
        binding_id: object,
        as_of: object,
        evidence: object,
        revocations: object,
    ) -> None:
        """Validate public call types with value-safe error messages."""

        if not isinstance(self.rules, EvidencePolicyRulesV1):
            raise ValueError("rules must be an EvidencePolicyRulesV1")
        try:
            _validate_uuid("binding_id", binding_id)
        except TypeError as error:
            raise ValueError("binding_id must be a UUID") from error
        try:
            _normalize_datetime("as_of", as_of)
        except (TypeError, ValueError) as error:
            raise ValueError("as_of must be a timezone-aware datetime") from error
        if not isinstance(evidence, tuple):
            raise ValueError("evidence must be a tuple")
        if not all(isinstance(item, IdentityEvidence) for item in evidence):
            raise ValueError("evidence must contain only IdentityEvidence values")
        if not isinstance(revocations, tuple):
            raise ValueError("revocations must be a tuple")
        if not all(isinstance(item, IdentityEvidenceRevocation) for item in revocations):
            raise ValueError("revocations must contain only IdentityEvidenceRevocation values")

    @staticmethod
    def _qualified(
        *,
        level: IdentityAssuranceLevel,
        supporting_evidence: tuple[IdentityEvidence, ...],
        maximum_expires_at: datetime | None,
    ) -> EvidencePolicyDecision:
        """Build one canonical qualified decision."""

        return EvidencePolicyDecision(
            status=EvidencePolicyStatus.QUALIFIED,
            level=level,
            supporting_evidence_ids=_supporting_ids(supporting_evidence),
            maximum_expires_at=maximum_expires_at,
            reason_codes=(EvidencePolicyReason.QUALIFIED,),
            policy_version=EVIDENCE_POLICY_VERSION,
        )
