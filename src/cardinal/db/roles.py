from sqlalchemy import Column, BigInteger

from .base import Base


class JoinRole(Base):
    __tablename__ = 'join_roles'

    role_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger)  # Added to simplify querying for all items on a guild
