"""Persistent DDL/SQL modeling runs, draft checks and immutable adoption."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0004_modeling_runs'
down_revision='0003_sources'
branch_labels=None
depends_on=None

def upgrade():
 op.create_table('modeling_runs',
  sa.Column('id',sa.String(36),primary_key=True),sa.Column('workspace_id',sa.String(36),nullable=False),
  sa.Column('request_key',sa.String(36),nullable=False,unique=True),sa.Column('input_sha256',sa.String(64),nullable=False),
  sa.Column('status',sa.String(30),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
  sa.Column('input_json',sa.JSON(),nullable=False),sa.Column('result_json',sa.JSON()),sa.Column('validation_json',sa.JSON()),
  sa.Column('error',sa.Text()),sa.Column('created_at',sa.DateTime(timezone=True).with_variant(DATETIME(fsp=6),"mysql"),server_default=sa.func.now(),nullable=False))
 op.create_table('adopted_models',
  sa.Column('id',sa.String(36),primary_key=True),sa.Column('workspace_id',sa.String(36),nullable=False),
  sa.Column('run_id',sa.String(36),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
  sa.Column('snapshot_json',sa.JSON(),nullable=False),sa.Column('artifacts_json',sa.JSON(),nullable=False),
  sa.Column('created_at',sa.DateTime(timezone=True).with_variant(DATETIME(fsp=6),"mysql"),server_default=sa.func.now(),nullable=False))

def downgrade():
 op.drop_table('adopted_models'); op.drop_table('modeling_runs')
