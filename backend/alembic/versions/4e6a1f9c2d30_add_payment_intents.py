"""add payment intents

Revision ID: 4e6a1f9c2d30
Revises: 2c8f04a9d621
Create Date: 2026-09-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "4e6a1f9c2d30"
down_revision: str | None = "2c8f04a9d621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("offer_code", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_payment_intents_case_id_cases"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_payment_intents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_intents")),
    )
    op.create_index(
        op.f("ix_payment_intents_case_id"),
        "payment_intents",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_intents_offer_code"),
        "payment_intents",
        ["offer_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_intents_user_id"),
        "payment_intents",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_intents_user_id"), table_name="payment_intents")
    op.drop_index(
        op.f("ix_payment_intents_offer_code"), table_name="payment_intents"
    )
    op.drop_index(op.f("ix_payment_intents_case_id"), table_name="payment_intents")
    op.drop_table("payment_intents")
