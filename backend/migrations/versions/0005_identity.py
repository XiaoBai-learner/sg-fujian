"""password accounts, login sessions and persistent login throttling"""
from alembic import op
import sqlalchemy as sa

revision = "0005_identity"
down_revision = "0004_modeling_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("username", sa.String(64)))
    op.add_column("users", sa.Column("password_hash", sa.String(255)))
    op.add_column("users", sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_index("uq_users_username", "users", ["username"], unique=True)
    op.create_table("login_sessions",
                    sa.Column("token_hash", sa.String(64), primary_key=True),
                    sa.Column("user_id", sa.String(36), nullable=False),
                    sa.Column("csrf_token", sa.String(64), nullable=False),
                    sa.Column("expires_at", sa.DateTime, nullable=False))
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])
    op.create_table("login_throttles",
                    sa.Column("key", sa.String(64), primary_key=True),
                    sa.Column("attempts", sa.Integer, nullable=False),
                    sa.Column("expires_at", sa.DateTime, nullable=False))


def downgrade():
    op.drop_table("login_throttles")
    op.drop_table("login_sessions")
    op.drop_index("uq_users_username", table_name="users")
    op.drop_column("users", "active")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
