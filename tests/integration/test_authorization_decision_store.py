import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

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
from memoria.infrastructure.database.session import async_session_factory

if os.getenv("MEMORIA_RUN_INTEGRATION_TESTS") != "1":
    pytest.skip(
        "set MEMORIA_RUN_INTEGRATION_TESTS=1 to run database integration tests",
        allow_module_level=True,
    )

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="module")
async def test_database_rejects_authorization_decision_updates() -> None:
    subject_id = uuid4()
    request = AuthorizationRequest(
        request_id=uuid4(),
        requested_at=datetime.now(UTC),
        actor_id=subject_id,
        subject_id=subject_id,
        legacy_id=uuid4(),
        action=SensitiveAction.ADD_TEXT_MEMORY,
        actor_role=AuthorityRole.SUBJECT,
        identity_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        legacy_state=LegacyState.ACTIVE,
        consent_status=ConsentStatus.GRANTED,
        consent_receipt_id=uuid4(),
        rights_basis=RightsBasis.SUBJECT_CONTROLLED,
    )
    decision = TrustPolicy.evaluate(request)
    repository = AuthorizationDecisionRepository()

    async with async_session_factory() as session:
        record = await repository.append(session, request, decision)
        record.outcome = "deny"

        with pytest.raises(DBAPIError, match="append-only"):
            await session.flush()

        await session.rollback()


@pytest.mark.asyncio(loop_scope="module")
async def test_database_rejects_authorization_decision_deletes() -> None:
    subject_id = uuid4()
    request = AuthorizationRequest(
        request_id=uuid4(),
        requested_at=datetime.now(UTC),
        actor_id=subject_id,
        subject_id=subject_id,
        legacy_id=uuid4(),
        action=SensitiveAction.ADD_TEXT_MEMORY,
        actor_role=AuthorityRole.SUBJECT,
        identity_assurance=IdentityAssuranceLevel.A1_CONTACT_VERIFIED,
        legacy_state=LegacyState.ACTIVE,
        consent_status=ConsentStatus.GRANTED,
        consent_receipt_id=uuid4(),
        rights_basis=RightsBasis.SUBJECT_CONTROLLED,
    )
    decision = TrustPolicy.evaluate(request)
    repository = AuthorizationDecisionRepository()

    async with async_session_factory() as session:
        record = await repository.append(session, request, decision)
        await session.delete(record)

        with pytest.raises(DBAPIError, match="append-only"):
            await session.flush()

        await session.rollback()
