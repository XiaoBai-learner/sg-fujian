"""source connections and metadata snapshots"""
from alembic import op
import sqlalchemy as sa

revision = "0003_sources"
down_revision = "0002_materials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("database_name", sa.String(160)),
        sa.Column("endpoint_ref", sa.String(500)),
        sa.Column("last_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "metadata_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "revision"),
    )
    op.create_table(
        "metadata_tables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("schema_name", sa.String(160), nullable=False),
        sa.Column("table_name", sa.String(160), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("primary_key_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "metadata_columns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("table_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("data_type", sa.String(80), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("metadata_columns")
    op.drop_table("metadata_tables")
    op.drop_table("metadata_snapshots")
    op.drop_table("source_connections")
