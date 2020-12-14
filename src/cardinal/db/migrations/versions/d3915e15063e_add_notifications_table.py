"""Add notifications table

Revision ID: d3915e15063e
Revises: 52d93745fa71
Create Date: 2020-12-13 14:51:46.447103

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3915e15063e'
down_revision = '52d93745fa71'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('notifications',
    sa.Column('guild_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('kind', sa.Enum('JOIN', 'LEAVE', 'BAN', 'UNBAN', name='notification_kind'), autoincrement=False, nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('template', sa.UnicodeText(), nullable=False),
    sa.PrimaryKeyConstraint('guild_id', 'kind', name=op.f('pk_notifications'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('notifications')
    # ### end Alembic commands ###
