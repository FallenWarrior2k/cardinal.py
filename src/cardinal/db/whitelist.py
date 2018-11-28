from sqlalchemy import BigInteger, Column

from .base import Base


class WhitelistedChannel(Base):
    __tablename__ = 'whitelisted_channels'

    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger)  # Added to simplify querying for all items in a guild
