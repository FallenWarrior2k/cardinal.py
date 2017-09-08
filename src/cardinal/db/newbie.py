from sqlalchemy import Column, ForeignKey, BigInteger, UnicodeText, DateTime, Interval
from sqlalchemy.orm import relationship

import cardinal.db as db


class Guild(db.Base):
    __tablename__ = 'newbie_guilds'

    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    role_id = Column(BigInteger, nullable=False)
    welcome_message = Column(UnicodeText, nullable=False)
    response_message = Column(UnicodeText, nullable=False)
    timeout = Column(Interval, nullable=True)


class User(db.Base):
    __tablename__ = 'newbie_users'

    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey(Guild.guild_id), primary_key=True, autoincrement=False)
    message_id = Column(BigInteger, unique=True, nullable=False)
    joined_at = Column(DateTime, nullable=False)


class Channel(db.Base):
    __tablename__ = 'newbie_channels'
    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey(Guild.guild_id), nullable=False)


Guild.users = relationship(User, backref='guild', innerjoin=True, cascade='all, delete-orphan', lazy=True)  # TODO: Decide on lazy (True) or eager (False) loading
Guild.channels = relationship(Channel, backref='guild', cascade='all, delete-orphan', lazy=True)
db.Base.metadata.create_all(db.engine)
