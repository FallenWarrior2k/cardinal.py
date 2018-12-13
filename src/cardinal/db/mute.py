from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, or_
from sqlalchemy.orm import relationship

from .base import Base


class MuteGuild(Base):
    __tablename__ = 'mute_guilds'

    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    role_id = Column(BigInteger, unique=True, nullable=False)


class MuteUser(Base):
    __tablename__ = 'mute_users'

    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger,
                      ForeignKey(MuteGuild.guild_id),
                      primary_key=True,
                      autoincrement=False)
    muted_until = Column(DateTime, index=True, nullable=True)
    channel_id = Column(BigInteger, nullable=True)

    __table_args__ = (
        CheckConstraint(
            or_(channel_id.is_(None), muted_until.isnot(None)),
            name='channel_id_only_on_finite'
        ),
    )


MuteGuild.mutes = relationship(MuteUser,
                               backref='guild',
                               innerjoin=True,
                               cascade='all, delete-orphan',
                               lazy=True)
