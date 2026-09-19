from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from memoria.domain.trust import (
    AuthorityRole,
    AuthorizationRequest,
    ConsentStatus,
    IdentityAssuranceLevel,
    LegacyState,
    RightsBasis,
    SensitiveAction,
    TrustPolicy,
)
from memoria.infrastructure.database.repositories import AuthorizationDecisionRepository


@pytest.mark.asyncio
async def test_repository_rejects_a_decision_for_another_request() -> None:
    request = AuthorizationRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000101"),
        requested_at=datetime(2026, 9, 19, 12, 0, tzinfo=UTC),
        actor_id=UUID("00000000-0000-0000-0000-000000000102"),
        subject_id=UUID("00000000-0000-0000-0000-000000000102"),
        legacy_id=UUID("00000000-0000-0000-0000-000000000103"),
        action=SensitiveAction.ADD_TEXT_MEMORY,
        actor_role=AuthorityRole.SUBJECT,
        identity_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        legacy_state=LegacyState.ACTIVE,
        consent_status=ConsentStatus.GRANTED,
        consent_receipt_id=UUID("00000000-0000-0000-0000-000000000104"),
        rights_basis=RightsBasis.SUBJECT_CONTROLLED,
    )
    decision = TrustPolicy.evaluate(request)
    mismatched_decision = replace(
        decision,
        request_id=UUID("00000000-0000-0000-0000-000000000105"),
    )
    repository = AuthorizationDecisionRepository()
    unused_session = cast(AsyncSession, object())

    with pytest.raises(ValueError, match="identifiers do not match"):
        await repository.append(unused_session, request, mismatched_decision)


@pytest.mark.asyncio
async def test_repository_rejects_a_tampered_request() -> None:
    request = AuthorizationRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000201"),
        requested_at=datetime(2026, 9, 19, 12, 0, tzinfo=UTC),
        actor_id=UUID("00000000-0000-0000-0000-000000000202"),
        subject_id=UUID("00000000-0000-0000-0000-000000000202"),
        legacy_id=UUID("00000000-0000-0000-0000-000000000203"),
        action=SensitiveAction.ADD_TEXT_MEMORY,
        actor_role=AuthorityRole.SUBJECT,
        identity_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        legacy_state=LegacyState.ACTIVE,
        consent_status=ConsentStatus.GRANTED,
        consent_receipt_id=UUID("00000000-0000-0000-0000-000000000204"),
        rights_basis=RightsBasis.SUBJECT_CONTROLLED,
    )
    decision = TrustPolicy.evaluate(request)
    tampered_request = replace(request, consent_status=ConsentStatus.REVOKED)
    repository = AuthorizationDecisionRepository()
    unused_session = cast(AsyncSession, object())

    with pytest.raises(ValueError, match="fingerprint does not match"):
        await repository.append(unused_session, tampered_request, decision)
