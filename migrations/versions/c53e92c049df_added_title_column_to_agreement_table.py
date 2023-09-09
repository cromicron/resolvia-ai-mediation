"""added title column to agreement table

Revision ID: c53e92c049df
Revises: dc8e0f5c5338
Create Date: 2023-09-08 16:44:58.770732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c53e92c049df'
down_revision = 'dc8e0f5c5338'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('agreement', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agreement_title', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('agreement', schema=None) as batch_op:
        batch_op.drop_column('agreement_title')

    # ### end Alembic commands ###
