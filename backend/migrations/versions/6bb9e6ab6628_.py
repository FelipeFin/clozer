"""empty message

Revision ID: 6bb9e6ab6628
Revises: a2341e78e660
Create Date: 2018-08-29 11:59:54.631252

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6bb9e6ab6628'
down_revision = 'a2341e78e660'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('usuario', sa.Column('cadastrado_em', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('usuario', 'cadastrado_em')
    # ### end Alembic commands ###
