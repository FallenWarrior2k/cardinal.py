from sqlalchemy import Column, String
import cardinal as db


class Channel(db.Base):
    __tablename__ = 'optin_channels'

    channelid = Column(String, primary_key=True, autoincrement=False)
    roleid = Column(String, unique=True)

    def __repr__(self):
        return "<Channel(channelid='%s', roleid='%s')>" % (self.channelid, self.roleid)

db.Base.metadata.create_all(db.engine)