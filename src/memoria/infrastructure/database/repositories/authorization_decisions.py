from sqlalchemy.ext.asyncio import AsyncSession

from memoria.domain.trust import AuthorizationDecision, AuthorizationRequest
from memoria.infrastructure.database.models import AuthorizationDecisionRecord


class AuthorizationDecisionRepository:
    """Append Trust Kernel decisions; mutation is intentionally not exposed."""

    async def append(
        self,
        session: AsyncSession,
        request: AuthorizationRequest,
        decision: AuthorizationDecision,
    ) -> AuthorizationDecisionRecord:
        if decision.request_id != request.request_id:
            raise ValueError("decision and request identifiers do not match")
        if decision.request_fingerprint != request.fingerprint():
            raise ValueError("decision fingerprint does not match the request")

        record = AuthorizationDecisionRecord(
            id=decision.decision_id,
            request_id=request.request_id,
            legacy_id=request.legacy_id,
            actor_id=request.actor_id,
            subject_id=request.subject_id,
            action=request.action.value,
            outcome=decision.outcome.value,
            reason_codes=[reason.value for reason in decision.reason_codes],
            policy_version=decision.policy_version,
            request_fingerprint=decision.request_fingerprint,
            request_payload=request.to_audit_payload(),
            evaluated_at=decision.evaluated_at,
        )
        session.add(record)
        await session.flush()
        return record
