from sqlalchemy import Column, BigInteger, ForeignKey
from cardinal import Base, engine

class Channel(Base):
    __tablename__ = 'channels'

    channelid = Column(BigInteger, primary_key=True, autoincrement=False)
    roleid = Column(BigInteger, unique=True)

    def __repr__(self):
        return "<Channel(channelid='%s', roleid='%s')>" % (self.channelid, self.roleid)

Base.metadata.create_all(engine)