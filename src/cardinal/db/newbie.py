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

    guildid = Column(String, ForeignKey(Guild.guildid), primary_key=True, autoincrement=False)
    userid = Column(String, primary_key=True, autoincrement=False)
    joined_at = Column(DateTime, nullable=False)


Guild.users = relationship(User, backref='guild', innerjoin=True, cascade='all, delete-orphan', lazy=True)  # TODO: Decide on lazy (True) or eager (False) loading
db.Base.metadata.create_all(db.engine)
