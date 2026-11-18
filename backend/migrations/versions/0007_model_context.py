"""Keep handwritten workflow context on its model, outside the upload library."""
from alembic import op
import sqlalchemy as sa

revision = '0007_model_context'
down_revision = '0006_workbench'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('ontology_models', sa.Column('business_context', sa.Text))

def downgrade():
    op.drop_column('ontology_models', 'business_context')
