"""add_api_key_and_monitoring

Revision ID: f1c7d2e8b4a0
Revises: eab4a0bfbd5a
Create Date: 2026-10-29 20:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1c7d2e8b4a0"
down_revision: str | Sequence[str] | None = "eab4a0bfbd5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add api_key to users and ensure monitoring tables exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    user_columns = [c["name"] for c in inspector.get_columns("users")]

    # 1. Add api_key to users if not present
    if "api_key" not in user_columns:
        op.add_column("users", sa.Column("api_key", sa.String(length=64), nullable=True))
        op.create_index(op.f("ix_users_api_key"), "users", ["api_key"], unique=True)

    # JSON type with SQLite/Postgres variant
    json_type = (
        sa.JSON()
        .with_variant(sqlite.JSON(), "sqlite")
        .with_variant(postgresql.JSONB(), "postgresql")
    )

    # 2. Create mcp_confirmation_tokens table if not exists
    if "mcp_confirmation_tokens" not in existing_tables:
        op.create_table(
            "mcp_confirmation_tokens",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token", sa.String(length=64), nullable=False),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("target_id", sa.String(length=36), nullable=False),
            sa.Column("decision", sa.String(length=50), nullable=False),
            sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_mcp_confirmation_tokens_token"),
            "mcp_confirmation_tokens",
            ["token"],
            unique=True,
        )
        op.create_index(
            op.f("ix_mcp_confirmation_tokens_user_id"),
            "mcp_confirmation_tokens",
            ["user_id"],
            unique=False,
        )

    # 3. Create eval_runs table if not exists
    if "eval_runs" not in existing_tables:
        op.create_table(
            "eval_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("run_name", sa.String(length=100), nullable=False),
            sa.Column("model_version", sa.String(length=50), nullable=False),
            sa.Column("dataset_name", sa.String(length=100), nullable=False),
            sa.Column("metrics_json", json_type, nullable=False),
            sa.Column("drift_metrics_json", json_type, nullable=False),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_eval_runs_run_name"), "eval_runs", ["run_name"], unique=False)

    # 4. Create model_versions table if not exists
    if "model_versions" not in existing_tables:
        op.create_table(
            "model_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("model_type", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("parameters_json", json_type, nullable=False),
            sa.Column("benchmark_scores_json", json_type, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_model_versions_version"), "model_versions", ["version"], unique=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    user_columns = [c["name"] for c in inspector.get_columns("users")]

    if "model_versions" in existing_tables:
        op.drop_index(op.f("ix_model_versions_version"), table_name="model_versions")
        op.drop_table("model_versions")

    if "eval_runs" in existing_tables:
        op.drop_index(op.f("ix_eval_runs_run_name"), table_name="eval_runs")
        op.drop_table("eval_runs")

    if "mcp_confirmation_tokens" in existing_tables:
        op.drop_index(
            op.f("ix_mcp_confirmation_tokens_user_id"), table_name="mcp_confirmation_tokens"
        )
        op.drop_index(
            op.f("ix_mcp_confirmation_tokens_token"), table_name="mcp_confirmation_tokens"
        )
        op.drop_table("mcp_confirmation_tokens")

    if "api_key" in user_columns:
        op.drop_index(op.f("ix_users_api_key"), table_name="users")
        op.drop_column("users", "api_key")
