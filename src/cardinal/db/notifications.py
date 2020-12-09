from enum import Enum, auto

from sqlalchemy import BigInteger, Column, Enum as EnumCol, UnicodeText

from .base import Base


class NotificationKind(Enum):
    JOIN = auto()
    LEAVE = auto()
    BAN = auto()
    UNBAN = auto()


class Notification(Base):
    __tablename__ = 'notifications'

    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    # Name for enum type necessary for Postgres
    kind = Column(EnumCol(NotificationKind, name="notification_kind"), primary_key=True, autoincrement=False)
    channel_id = Column(BigInteger, nullable=False)
    template = Column(UnicodeText, nullable=False)
