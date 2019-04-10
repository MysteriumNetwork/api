"""empty message

Revision ID: ec97608ec2dc
Revises: f448930e4058
Create Date: 2019-04-09 13:58:06.951021

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ec97608ec2dc'
down_revision = 'f448930e4058'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('node', sa.Column('access_list', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('node', 'access_list')
    # ### end Alembic commands ###