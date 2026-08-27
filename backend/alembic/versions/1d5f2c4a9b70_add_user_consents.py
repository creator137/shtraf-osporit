"""add user consents

Revision ID: 1d5f2c4a9b70
Revises: 8c3a0b7f1e2d
Create Date: 2026-08-27 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1d5f2c4a9b70"
down_revision: Union[str, Sequence[str], None] = "8c3a0b7f1e2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_consents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_consents")),
    )
    op.create_index(
        op.f("ix_user_consents_telegram_id"),
        "user_consents",
        ["telegram_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_consents_user_id"),
        "user_consents",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_consents_user_id"), table_name="user_consents")
    op.drop_index(op.f("ix_user_consents_telegram_id"), table_name="user_consents")
    op.drop_table("user_consents")
