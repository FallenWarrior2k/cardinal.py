"""Add check constraint to ensure channel ID cannot be set on infinite mutes

Revision ID: dc0db050f230
Revises: 25d0f68d0698
Create Date: 2018-12-10 20:03:12.356521

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "dc0db050f230"
down_revision = "25d0f68d0698"
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        "channel_id_only_on_finite",
        "mute_users",
        sa.or_(sa.column("channel_id").is_(None), sa.column("muted_until").isnot(None)),
    )


def downgrade():
    op.drop_constraint("channel_id_only_on_finite", "mute_users", type_="check")
