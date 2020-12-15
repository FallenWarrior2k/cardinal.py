from enum import Enum, auto

from discord.ext.commands.errors import BadArgument
from sqlalchemy import BigInteger, Column, Enum as EnumCol, UnicodeText

from .base import Base


class NotificationKind(Enum):
    JOIN = auto()
    LEAVE = auto()
    BAN = auto()
    UNBAN = auto()

    # Helper to be able to use the type as an annotation on commands
    @classmethod
    async def convert(cls, ctx, arg):
        try:
            return cls[arg.upper()]
        except KeyError:
            raise BadArgument

    def __str__(self):
        """Get a lowercase representation for use in user-facing text."""
        return self.name.lower()

    def __repr__(self):
        # Not technically correct, but required to support the auto-generated help
        return str(self)


class Notification(Base):
    __tablename__ = 'notifications'

    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    # Name for enum type necessary for Postgres
    kind = Column(EnumCol(NotificationKind, name="notification_kind"), primary_key=True, autoincrement=False)
    channel_id = Column(BigInteger, nullable=False)
    template = Column(UnicodeText, nullable=False)
