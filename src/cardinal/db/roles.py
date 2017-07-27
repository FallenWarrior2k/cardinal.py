from sqlalchemy import Column, String

import cardinal.db as db


class Role(db.Base):
    __tablename__ = 'join_roles'

    roleid = Column(String, primary_key=True, autoincrement=False)


db.Base.metadata.create_all(db.engine)
