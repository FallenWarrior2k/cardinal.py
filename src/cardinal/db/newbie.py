from sqlalchemy import Column, ForeignKey, String, UnicodeText, DateTime, Interval
from sqlalchemy.orm import relationship

import cardinal.db as db


class Guild(db.Base):
    __tablename__ = 'newbie_guilds'

    guildid = Column(String, primary_key=True, autoincrement=False)
    roleid = Column(String, nullable=False)
    welcome_message = Column(UnicodeText, nullable=False)
    response_message = Column(UnicodeText, nullable=False)
    timeout = Column(Interval, nullable=True)


class User(db.Base):
    __tablename__ = 'newbie_users'

    userid = Column(String, primary_key=True, autoincrement=False)
    guildid = Column(String, ForeignKey(Guild.guildid), primary_key=True, autoincrement=False)
    messageid = Column(String, unique=True, nullable=False)
    joined_at = Column(DateTime, nullable=False)


class Channel(db.Base):
    __tablename__ = 'newbie_channels'
    channelid = Column(String, primary_key=True, autoincrement=False)
    guildid = Column(String, ForeignKey(Guild.guildid), nullable=False)


Guild.users = relationship(User, backref='guild', innerjoin=True, cascade='all, delete-orphan', lazy=True)  # TODO: Decide on lazy (True) or eager (False) loading
Guild.channels = relationship(Channel, backref='guild', cascade='all, delete-orphan', lazy=True)
db.Base.metadata.create_all(db.engine)
