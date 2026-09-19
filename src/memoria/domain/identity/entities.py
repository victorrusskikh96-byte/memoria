"""Immutable entities and validation rules for identity assurance evidence."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from memoria.domain.identity.types import IdentityAssuranceEventKind, IdentityEvidenceKind
from memoria.domain.trust.types import IdentityAssuranceLevel

_AUTHORITY_OR_PROVIDER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_OPAQUE_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9._:|~-]{1,255}$")
_REASON_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAXIMUM_A3_LIFETIME = timedelta(hours=24)


def _validate_uuid(field: str, value: object) -> None:
    """Require a value to be a UUID for the named field."""

    if not isinstance(value, UUID):
        raise TypeError(f"{field} must be a UUID")


def _normalize_datetime(field: str, value: object) -> datetime:
    """Require an aware datetime and return its UTC-normalized value."""

    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _validate_pattern(field: str, value: object, pattern: re.Pattern[str]) -> None:
    """Require a string to match the complete field-specific pattern."""

    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{field} has an invalid format")


def _validate_printable_ascii_version(field: str, value: object) -> None:
    """Require a bounded, trimmed version string containing printable ASCII."""

    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if not 1 <= len(value) <= 64:
        raise ValueError(f"{field} must contain between 1 and 64 characters")
    if not value.isascii() or not value.isprintable():
        raise ValueError(f"{field} must contain only printable ASCII characters")
    if value != value.strip():
        raise ValueError(f"{field} must not have leading or trailing whitespace")


def _validate_event_types(
    kind: object,
    previous_level: object,
    resulting_level: object,
) -> None:
    """Require event kind and assurance levels to use their domain enumerations."""

    if not isinstance(kind, IdentityAssuranceEventKind):
        raise TypeError("kind must be an IdentityAssuranceEventKind")
    if not isinstance(previous_level, IdentityAssuranceLevel):
        raise TypeError("previous_level must be an IdentityAssuranceLevel")
    if not isinstance(resulting_level, IdentityAssuranceLevel):
        raise TypeError("resulting_level must be an IdentityAssuranceLevel")


@dataclass(frozen=True, slots=True)
class HumanSubject:
    """Represent a person through a stable identifier and creation timestamp."""

    id: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate the identifier and normalize the creation timestamp."""

        _validate_uuid("id", self.id)
        object.__setattr__(self, "created_at", _normalize_datetime("created_at", self.created_at))


@dataclass(frozen=True, slots=True)
class Account:
    """Represent an externally authenticated account without storing direct PII."""

    id: UUID
    authentication_authority: str
    external_subject_reference: str = field(repr=False)
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate account identifiers and normalize the creation timestamp."""

        _validate_uuid("id", self.id)
        _validate_pattern(
            "authentication_authority",
            self.authentication_authority,
            _AUTHORITY_OR_PROVIDER_PATTERN,
        )
        _validate_pattern(
            "external_subject_reference",
            self.external_subject_reference,
            _OPAQUE_REFERENCE_PATTERN,
        )
        object.__setattr__(self, "created_at", _normalize_datetime("created_at", self.created_at))


@dataclass(frozen=True, slots=True)
class AccountHumanSubjectBinding:
    """Associate one account with one human subject at a recorded time."""

    id: UUID
    account_id: UUID
    human_subject_id: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate all identifiers and normalize the creation timestamp."""

        _validate_uuid("id", self.id)
        _validate_uuid("account_id", self.account_id)
        _validate_uuid("human_subject_id", self.human_subject_id)
        object.__setattr__(self, "created_at", _normalize_datetime("created_at", self.created_at))


@dataclass(frozen=True, slots=True)
class IdentityEvidence:
    """Record validated evidence supporting an account-to-subject binding."""

    id: UUID
    binding_id: UUID
    kind: IdentityEvidenceKind
    provider: str
    opaque_reference: str = field(repr=False)
    observed_at: datetime
    expires_at: datetime | None
    recorded_at: datetime
    schema_version: str

    def __post_init__(self) -> None:
        """Validate evidence fields, normalize times, and enforce expiry ordering."""

        _validate_uuid("id", self.id)
        _validate_uuid("binding_id", self.binding_id)
        _validate_pattern("provider", self.provider, _AUTHORITY_OR_PROVIDER_PATTERN)
        _validate_pattern("opaque_reference", self.opaque_reference, _OPAQUE_REFERENCE_PATTERN)
        _validate_printable_ascii_version("schema_version", self.schema_version)

        observed_at = _normalize_datetime("observed_at", self.observed_at)
        recorded_at = _normalize_datetime("recorded_at", self.recorded_at)
        expires_at = None
        if self.expires_at is not None:
            expires_at = _normalize_datetime("expires_at", self.expires_at)
            if expires_at <= observed_at:
                raise ValueError("expires_at must be strictly greater than observed_at")

        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "recorded_at", recorded_at)


@dataclass(frozen=True, slots=True)
class IdentityAssuranceEvent:
    """Record one locally valid change to a binding's identity assurance level."""

    id: UUID
    binding_id: UUID
    stream_version: int
    kind: IdentityAssuranceEventKind
    previous_level: IdentityAssuranceLevel
    resulting_level: IdentityAssuranceLevel
    effective_at: datetime
    expires_at: datetime | None
    fallback_event_id: UUID | None
    reason_code: str
    assurance_policy_version: str
    idempotency_key: UUID
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Validate event fields, normalize times, and enforce local transition rules."""

        _validate_uuid("id", self.id)
        _validate_uuid("binding_id", self.binding_id)
        _validate_uuid("idempotency_key", self.idempotency_key)
        if self.fallback_event_id is not None:
            _validate_uuid("fallback_event_id", self.fallback_event_id)
        if not isinstance(self.stream_version, int) or isinstance(self.stream_version, bool):
            raise TypeError("stream_version must be an integer")
        if self.stream_version < 1:
            raise ValueError("stream_version must be at least 1")
        _validate_event_types(self.kind, self.previous_level, self.resulting_level)
        _validate_pattern("reason_code", self.reason_code, _REASON_CODE_PATTERN)
        _validate_printable_ascii_version("assurance_policy_version", self.assurance_policy_version)

        effective_at = _normalize_datetime("effective_at", self.effective_at)
        recorded_at = _normalize_datetime("recorded_at", self.recorded_at)
        expires_at = None
        if self.expires_at is not None:
            expires_at = _normalize_datetime("expires_at", self.expires_at)
            if expires_at <= effective_at:
                raise ValueError("expires_at must be strictly greater than effective_at")

        if self.fallback_event_id == self.id:
            raise ValueError("fallback_event_id must differ from id")

        self._validate_assurance_window(effective_at, expires_at)
        self._validate_transition(expires_at)

        object.__setattr__(self, "effective_at", effective_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "recorded_at", recorded_at)

    def _validate_assurance_window(
        self, effective_at: datetime, expires_at: datetime | None
    ) -> None:
        """Enforce expiry and fallback invariants for the resulting assurance level."""

        if self.resulting_level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE:
            if expires_at is None:
                raise ValueError("A3 assurance requires expires_at")
            if self.fallback_event_id is None:
                raise ValueError("A3 assurance requires fallback_event_id")
            if expires_at - effective_at > _MAXIMUM_A3_LIFETIME:
                raise ValueError("A3 assurance lifetime must not exceed 24 hours")
        elif self.fallback_event_id is not None:
            raise ValueError("fallback_event_id is permitted only for A3 assurance")

    def _validate_transition(self, expires_at: datetime | None) -> None:
        """Enforce invariants belonging to the event's local transition kind."""

        if self.kind is IdentityAssuranceEventKind.ESTABLISHED:
            if self.stream_version != 1:
                raise ValueError("ESTABLISHED requires stream_version 1")
            if self.previous_level is not IdentityAssuranceLevel.A0_UNVERIFIED:
                raise ValueError("ESTABLISHED requires previous_level A0")
            if self.resulting_level not in (
                IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
                IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH,
            ):
                raise ValueError("ESTABLISHED must result in A1 or A2")
        elif self.kind is IdentityAssuranceEventKind.UPGRADED:
            if self.resulting_level <= self.previous_level:
                raise ValueError("UPGRADED must increase the assurance level")
            if (
                self.resulting_level is IdentityAssuranceLevel.A3_HIGH_ASSURANCE
                and self.previous_level is not IdentityAssuranceLevel.A2_DOCUMENT_OR_TRUSTED_VOUCH
            ):
                raise ValueError("an upgrade to A3 requires previous_level A2")
        elif self.kind is IdentityAssuranceEventKind.REFRESHED:
            if self.previous_level != self.resulting_level:
                raise ValueError("REFRESHED requires equal assurance levels")
            if self.resulting_level is IdentityAssuranceLevel.A0_UNVERIFIED:
                raise ValueError("REFRESHED requires an assurance level above A0")
        elif self.kind is IdentityAssuranceEventKind.DOWNGRADED:
            if self.resulting_level >= self.previous_level:
                raise ValueError("DOWNGRADED must decrease the assurance level")
        elif self.kind is IdentityAssuranceEventKind.REVOKED:
            if self.resulting_level is not IdentityAssuranceLevel.A0_UNVERIFIED:
                raise ValueError("REVOKED must result in A0")
            if expires_at is not None:
                raise ValueError("REVOKED must not have expires_at")
            if self.fallback_event_id is not None:
                raise ValueError("REVOKED must not have fallback_event_id")


@dataclass(frozen=True, slots=True)
class EffectiveIdentityAssurance:
    """Represent the immutable assurance value resolved for an account binding."""

    account_id: UUID
    human_subject_id: UUID
    binding_id: UUID
    level: IdentityAssuranceLevel
    source_event_id: UUID
    valid_until: datetime | None
    resolved_at: datetime

    def __post_init__(self) -> None:
        """Validate identifiers and normalize the optional validity and resolution times."""

        _validate_uuid("account_id", self.account_id)
        _validate_uuid("human_subject_id", self.human_subject_id)
        _validate_uuid("binding_id", self.binding_id)
        _validate_uuid("source_event_id", self.source_event_id)
        if not isinstance(self.level, IdentityAssuranceLevel):
            raise TypeError("level must be an IdentityAssuranceLevel")

        valid_until = None
        if self.valid_until is not None:
            valid_until = _normalize_datetime("valid_until", self.valid_until)
        object.__setattr__(self, "valid_until", valid_until)
        object.__setattr__(
            self,
            "resolved_at",
            _normalize_datetime("resolved_at", self.resolved_at),
        )
