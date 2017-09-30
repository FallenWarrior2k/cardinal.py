from sqlalchemy import Column, BigInteger

from .. import db


class Role(db.Base):
    __tablename__ = 'join_roles'

    role_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger)  # Added to simplify querying for all items on a guild
