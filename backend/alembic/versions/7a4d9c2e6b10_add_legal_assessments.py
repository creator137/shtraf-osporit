"""add legal assessments

Revision ID: 7a4d9c2e6b10
Revises: 5b7e2a1f4c90
Create Date: 2026-08-28 15:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7a4d9c2e6b10"
down_revision: Union[str, Sequence[str], None] = "5b7e2a1f4c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    assessment_status = postgresql.ENUM(
        "IN_PROGRESS",
        "COMPLETED",
        name="legal_assessment_status",
        create_type=False,
    )
    assessment_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "legal_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            assessment_status,
            server_default="IN_PROGRESS",
            nullable=False,
        ),
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "results",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("rules_version", sa.String(length=20), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_legal_assessments_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_assessments")),
        sa.UniqueConstraint("case_id", name=op.f("uq_legal_assessments_case_id")),
    )
def downgrade() -> None:
    op.drop_table("legal_assessments")
    postgresql.ENUM(name="legal_assessment_status").drop(
        op.get_bind(), checkfirst=True
    )
