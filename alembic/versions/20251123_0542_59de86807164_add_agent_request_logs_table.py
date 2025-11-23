"""add agent_request_logs table

Revision ID: 59de86807164
Revises:
Create Date: 2025-11-23 05:42:09.161558

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "59de86807164"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "agent_request_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("raw_command", sa.String(512), nullable=False),
        sa.Column("is_success", sa.Boolean(), nullable=False, default=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("executed_command", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table("agent_request_logs")
