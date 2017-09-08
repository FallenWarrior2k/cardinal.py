from sqlalchemy import Column, BigInteger

import cardinal.db as db


class Channel(db.Base):
    __tablename__ = 'optin_channels'

    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)
    role_id = Column(BigInteger, unique=True)


db.Base.metadata.create_all(db.engine)
