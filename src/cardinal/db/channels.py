from sqlalchemy import Column, String

import cardinal.db as db


class Channel(db.Base):
    __tablename__ = 'optin_channels'

    channelid = Column(String, primary_key=True, autoincrement=False)
    roleid = Column(String, unique=True)