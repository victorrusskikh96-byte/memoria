from enum import IntEnum, StrEnum


class IdentityAssuranceLevel(IntEnum):
    """Strength of evidence that an account represents a particular human."""

    A0_UNVERIFIED = 0
    A1_CONTACT_VERIFIED = 1
    A2_DOCUMENT_OR_TRUSTED_VOUCH = 2
    A3_HIGH_ASSURANCE = 3


class EvidenceLevel(IntEnum):
    """Truth hierarchy; higher levels carry stronger provenance."""

    GENERATED_INFERENCE = 1
    UNVERIFIED_THIRD_PARTY = 2
    VERIFIED_THIRD_PARTY = 3
    SUBJECT_APPROVED = 4
    SUBJECT_AUTHORED = 5
    CRYPTOGRAPHICALLY_ATTESTED = 6


class LegacyState(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SAFEGUARD_HOLD = "safeguard_hold"
    VERIFICATION_PENDING = "verification_pending"
    MEMORIAL = "memorial"
    DISPUTED = "disputed"
    ARCHIVED = "archived"
    EXPORTED = "exported"
    DELETED = "deleted"


class ConsentStatus(StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthorityRole(StrEnum):
    SUBJECT = "subject"
    CONTRIBUTOR = "contributor"
    STEWARD = "steward"
    SUCCESSOR = "successor"
    REVIEWER = "reviewer"
