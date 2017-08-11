from sqlalchemy import Column, String

import cardinal.db as db


class Channel(db.Base):
    __tablename__ = 'optin_channels'

    channel_id = Column(String, primary_key=True, autoincrement=False)
    role_id = Column(String, unique=True)


db.Base.metadata.create_all(db.engine)
