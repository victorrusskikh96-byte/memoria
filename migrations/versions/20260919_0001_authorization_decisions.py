"""create append-only authorization decisions

Revision ID: 20260919_0001
Revises:
Create Date: 2026-09-19 00:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260919_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authorization_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legacy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('allow', 'deny')",
            name="ck_authorization_decisions_outcome",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_authorization_decisions_fingerprint_length",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_authorization_decisions_legacy_evaluated_at",
        "authorization_decisions",
        ["legacy_id", "evaluated_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION memoria_reject_authorization_decision_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'authorization decisions are append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_authorization_decisions_append_only
        BEFORE UPDATE OR DELETE ON authorization_decisions
        FOR EACH ROW
        EXECUTE FUNCTION memoria_reject_authorization_decision_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_authorization_decisions_append_only ON authorization_decisions"
    )
    op.drop_table("authorization_decisions")
    op.execute("DROP FUNCTION IF EXISTS memoria_reject_authorization_decision_mutation()")
