"""add stage 4 legal analysis

Revision ID: 2c8f04a9d621
Revises: 7a4d9c2e6b10
Create Date: 2026-09-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "2c8f04a9d621"
down_revision: str | None = "7a4d9c2e6b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    legal_analysis_status = postgresql.ENUM(
        "PENDING_CONFIRMATION",
        "CONFIRMED",
        "DOCUMENTS_GENERATED",
        "FAILED",
        name="legal_analysis_status",
        create_type=False,
    )
    generated_document_type = postgresql.ENUM(
        "COMPLAINT",
        "EVIDENCE_PETITION",
        name="generated_document_type",
        create_type=False,
    )
    generated_document_format = postgresql.ENUM(
        "DOCX",
        "PDF",
        name="generated_document_format",
        create_type=False,
    )
    legal_analysis_status.create(op.get_bind(), checkfirst=True)
    generated_document_type.create(op.get_bind(), checkfirst=True)
    generated_document_format.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "legal_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            legal_analysis_status,
            server_default="PENDING_CONFIRMATION",
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "input_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "grounds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "missing_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_legal_analyses_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_analyses")),
        sa.UniqueConstraint("case_id", name=op.f("uq_legal_analyses_case_id")),
    )
    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("legal_analysis_id", sa.Integer(), nullable=True),
        sa.Column("document_type", generated_document_type, nullable=False),
        sa.Column("file_format", generated_document_format, nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_generated_documents_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["legal_analysis_id"],
            ["legal_analyses.id"],
            name=op.f("fk_generated_documents_legal_analysis_id_legal_analyses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_documents")),
    )
    op.create_index(
        op.f("ix_generated_documents_case_id"),
        "generated_documents",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_legal_analysis_id"),
        "generated_documents",
        ["legal_analysis_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_generated_documents_legal_analysis_id"),
        table_name="generated_documents",
    )
    op.drop_index(op.f("ix_generated_documents_case_id"), table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_table("legal_analyses")
    postgresql.ENUM(name="generated_document_format").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="generated_document_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="legal_analysis_status").drop(op.get_bind(), checkfirst=True)
