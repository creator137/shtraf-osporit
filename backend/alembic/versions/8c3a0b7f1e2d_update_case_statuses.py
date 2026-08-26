"""update case statuses

Revision ID: 8c3a0b7f1e2d
Revises: f9fdfc704de2
Create Date: 2026-08-26 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c3a0b7f1e2d"
down_revision: Union[str, Sequence[str], None] = "f9fdfc704de2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE case_status RENAME TO case_status_old")
    case_status = sa.Enum(
        "DOCUMENT_UPLOADED",
        "IN_PROGRESS",
        "READY",
        name="case_status",
    )
    case_status.create(op.get_bind())
    op.execute(
        "ALTER TABLE cases ALTER COLUMN status DROP DEFAULT"
    )
    op.execute(
        """
        ALTER TABLE cases
        ALTER COLUMN status TYPE case_status
        USING (
            CASE status::text
                WHEN 'NEW' THEN 'DOCUMENT_UPLOADED'
                ELSE status::text
            END
        )::case_status
        """
    )
    op.execute(
        "ALTER TABLE cases ALTER COLUMN status SET DEFAULT 'DOCUMENT_UPLOADED'"
    )
    op.execute("DROP TYPE case_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE case_status RENAME TO case_status_new")
    case_status = sa.Enum(
        "NEW",
        "DOCUMENT_UPLOADED",
        name="case_status",
    )
    case_status.create(op.get_bind())
    op.execute(
        "ALTER TABLE cases ALTER COLUMN status DROP DEFAULT"
    )
    op.execute(
        """
        ALTER TABLE cases
        ALTER COLUMN status TYPE case_status
        USING (
            CASE status::text
                WHEN 'IN_PROGRESS' THEN 'DOCUMENT_UPLOADED'
                WHEN 'READY' THEN 'DOCUMENT_UPLOADED'
                ELSE status::text
            END
        )::case_status
        """
    )
    op.execute(
        "ALTER TABLE cases ALTER COLUMN status SET DEFAULT 'NEW'"
    )
    op.execute("DROP TYPE case_status_new")
