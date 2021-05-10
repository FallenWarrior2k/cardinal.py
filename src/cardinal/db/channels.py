from sqlalchemy import BigInteger, Column

from .base import Base


class OptinChannel(Base):
    __tablename__ = "optin_channels"

    channel_id = Column(BigInteger, primary_key=True, autoincrement=False)
    role_id = Column(BigInteger, unique=True)
    guild_id = Column(BigInteger)  # Added to simplify querying for all items on a guild
