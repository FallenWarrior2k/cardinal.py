from sqlalchemy import Column, ForeignKey, BigInteger, UnicodeText, DateTime, Interval
from sqlalchemy.orm import relationship

from .base import Base


class NewbieGuild(Base):
    __tablename__ = 'newbie_guilds'

    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    role_id = Column(BigInteger, nullable=False)
    welcome_message = Column(UnicodeText, nullable=False)
    response_message = Column(UnicodeText, nullable=False)
    timeout = Column(Interval, nullable=True)


class NewbieUser(Base):
    __tablename__ = 'newbie_users'

    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey(NewbieGuild.guild_id), primary_key=True, autoincrement=False)
    message_id = Column(BigInteger, unique=True, nullable=False)
    joined_at = Column(DateTime, nullable=False)


class NewbieChannel(Base):
    __tablename__ = 'newbie_channels'

    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey(NewbieGuild.guild_id), nullable=False)


NewbieGuild.users = relationship(NewbieUser, backref='guild', innerjoin=True, cascade='all, delete-orphan', lazy=True)  # TODO: Decide on lazy (True) or eager (False) loading
NewbieGuild.channels = relationship(NewbieChannel, backref='guild', cascade='all, delete-orphan', lazy=True)
