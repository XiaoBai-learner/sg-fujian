"""material and material revision tables"""
from alembic import op
import sqlalchemy as sa

revision = "0002_materials"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("source_ref", sa.String(255)),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "material_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("material_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_uri", sa.String(500), nullable=False),
        sa.Column("parse_status", sa.String(30), nullable=False),
        sa.Column("parsed_uri", sa.String(500)),
        sa.Column("parse_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("material_id", "revision"),
    )


def downgrade() -> None:
    op.drop_table("material_revisions")
    op.drop_table("materials")
