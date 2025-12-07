"""create api_usage_logs table

Revision ID: 2a3b4c5d6e7f
Revises: 1d98858db855
Create Date: 2025-11-27 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2a3b4c5d6e7f"
down_revision = "1d98858db855"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "api_usage_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("request_log_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Create index on created_at for efficient date-range queries
    op.create_index("ix_api_usage_logs_created_at", "api_usage_logs", ["created_at"])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_api_usage_logs_created_at", table_name="api_usage_logs")
    op.drop_table("api_usage_logs")
