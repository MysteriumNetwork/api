"""empty message

Revision ID: cf06348b408d
Revises: 441fd5fc94a1
Create Date: 2020-03-04 04:07:42.055990

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'cf06348b408d'
down_revision = '441fd5fc94a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('monitoring_failed',
    sa.Column('provider_id', sa.String(length=42), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['node.node_key'], ),
    sa.PrimaryKeyConstraint('provider_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('monitoring_failed')
    # ### end Alembic commands ###
