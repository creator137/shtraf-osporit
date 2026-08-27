"""add document recognition

Revision ID: 5b7e2a1f4c90
Revises: 1d5f2c4a9b70
Create Date: 2026-08-27 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5b7e2a1f4c90"
down_revision: Union[str, Sequence[str], None] = "1d5f2c4a9b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recognition_status = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "RECOGNIZED",
        "FAILED",
        "VERIFIED",
        name="recognition_status",
        create_type=False,
    )
    recognition_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "document_recognitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            recognition_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_recognitions_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_recognitions")),
        sa.UniqueConstraint(
            "document_id", name=op.f("uq_document_recognitions_document_id")
        ),
    )
    op.create_index(
        op.f("ix_document_recognitions_document_id"),
        "document_recognitions",
        ["document_id"],
        unique=False,
    )
    op.create_table(
        "fine_notices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("recognition_id", sa.Integer(), nullable=True),
        sa.Column("notice_number", sa.String(length=100), nullable=True),
        sa.Column("notice_date", sa.String(length=50), nullable=True),
        sa.Column("uin", sa.String(length=64), nullable=True),
        sa.Column("fine_amount", sa.Integer(), nullable=True),
        sa.Column("article", sa.String(length=255), nullable=True),
        sa.Column("vehicle_plate", sa.String(length=32), nullable=True),
        sa.Column("violation_datetime", sa.String(length=100), nullable=True),
        sa.Column("violation_place", sa.Text(), nullable=True),
        sa.Column("issuing_authority", sa.Text(), nullable=True),
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
            name=op.f("fk_fine_notices_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recognition_id"],
            ["document_recognitions.id"],
            name=op.f("fk_fine_notices_recognition_id_document_recognitions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fine_notices")),
        sa.UniqueConstraint("case_id", name=op.f("uq_fine_notices_case_id")),
    )
    op.create_index(
        op.f("ix_fine_notices_case_id"),
        "fine_notices",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fine_notices_recognition_id"),
        "fine_notices",
        ["recognition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_fine_notices_recognition_id"), table_name="fine_notices")
    op.drop_index(op.f("ix_fine_notices_case_id"), table_name="fine_notices")
    op.drop_table("fine_notices")
    op.drop_index(
        op.f("ix_document_recognitions_document_id"),
        table_name="document_recognitions",
    )
    op.drop_table("document_recognitions")
    sa.Enum(name="recognition_status").drop(op.get_bind())
