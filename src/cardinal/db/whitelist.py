from sqlalchemy import Column, BigInteger

import cardinal.db as db


class WhitelistedChannel(db.Base):
    __tablename__ = 'whitelisted_channels'

    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)


db.Base.metadata.create_all(db.engine)
