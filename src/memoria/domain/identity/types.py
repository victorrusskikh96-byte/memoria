"""Enumerations that classify identity assurance evidence and lifecycle changes."""

from enum import StrEnum


class IdentityEvidenceKind(StrEnum):
    """Classify the mechanism represented by a piece of identity evidence."""

    ACCOUNT_CHANNEL_VERIFICATION = "account_channel_verification"
    DOCUMENT_CHECK = "document_check"
    TRUSTED_VOUCH = "trusted_vouch"
    INDEPENDENT_CHECK = "independent_check"
    STEP_UP_VERIFICATION = "step_up_verification"


class IdentityAssuranceEventKind(StrEnum):
    """Classify a change in the lifecycle of an identity assurance level."""

    ESTABLISHED = "established"
    UPGRADED = "upgraded"
    REFRESHED = "refreshed"
    DOWNGRADED = "downgraded"
    REVOKED = "revoked"
