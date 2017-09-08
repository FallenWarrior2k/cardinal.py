from sqlalchemy import Column, BigInteger

import cardinal.db as db


class Role(db.Base):
    __tablename__ = 'join_roles'

    role_id = Column(BigInteger, primary_key=True, autoincrement=False)


db.Base.metadata.create_all(db.engine)
