from sqlalchemy import Column, String

import cardinal.db as db


class WhitelistedChannel(db.Base):
    __tablename__ = 'whitelisted_channels'

    channelid = Column(String, primary_key=True, autoincrement=False)

db.Base.metadata.create_all(db.engine)