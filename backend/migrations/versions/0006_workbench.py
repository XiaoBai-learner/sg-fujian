"""Named ontology models and editable encrypted metadata connections."""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = '0006_workbench'
down_revision = '0005_identity'
branch_labels = None
depends_on = None

def upgrade():
    for column in [sa.Column('host', sa.String(255)), sa.Column('port', sa.Integer),
                   sa.Column('username', sa.String(160)), sa.Column('password_ciphertext', sa.Text),
                   sa.Column('databases_json', sa.JSON)]:
        op.add_column('source_connections', column)
    op.add_column('modeling_runs', sa.Column('model_id', sa.String(36)))
    op.create_index('ix_modeling_runs_model_id', 'modeling_runs', ['model_id'])
    op.create_table('ontology_models', sa.Column('id',sa.String(36),primary_key=True),
                    sa.Column('workspace_id',sa.String(36),nullable=False), sa.Column('name',sa.String(160),nullable=False),
                    sa.Column('group_name',sa.String(160),nullable=False), sa.Column('current_run_id',sa.String(36)),
                    sa.Column('adopted_id',sa.String(36)), sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_ontology_models_workspace_id','ontology_models',['workspace_id'])
    connection=op.get_bind()
    for run in connection.execute(sa.text('SELECT id,workspace_id,created_at FROM modeling_runs')).mappings().all():
        model_id=str(uuid4())
        adopted=connection.execute(sa.text('SELECT id FROM adopted_models WHERE run_id=:run ORDER BY created_at DESC LIMIT 1'),{'run':run['id']}).scalar()
        connection.execute(sa.text('INSERT INTO ontology_models (id,workspace_id,name,group_name,current_run_id,adopted_id,created_at) VALUES (:id,:workspace,:name,:group,:run,:adopted,:created)'),
                           {'id':model_id,'workspace':run['workspace_id'],'name':'已有模型 '+run['id'][:8],'group':'未分组','run':run['id'],'adopted':adopted,'created':run['created_at']})
        connection.execute(sa.text('UPDATE modeling_runs SET model_id=:model WHERE id=:run'),{'model':model_id,'run':run['id']})
    op.create_table('trace_attachments',sa.Column('id',sa.String(36),primary_key=True),
                    sa.Column('workspace_id',sa.String(36),nullable=False),sa.Column('content_uri',sa.Text,nullable=False),
                    sa.Column('content_type',sa.String(40),nullable=False),sa.Column('size_bytes',sa.Integer,nullable=False))

def downgrade():
    op.drop_table('trace_attachments')
    op.drop_table('ontology_models')
    op.drop_index('ix_modeling_runs_model_id',table_name='modeling_runs')
    op.drop_column('modeling_runs','model_id')
    for field in ['databases_json','password_ciphertext','username','port','host']:
        op.drop_column('source_connections',field)
