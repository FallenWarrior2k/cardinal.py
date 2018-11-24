import logging

from .base import Base
from .channels import OptinChannel
from .newbie import NewbieChannel, NewbieGuild, NewbieUser
from .roles import JoinRole
from .whitelist import WhitelistedChannel

logger = logging.getLogger(__name__)


def create_all(engine):
    Base.metadata.create_all(engine)
    logger.info('Created necessary database tables.')


__all__ = [
    'Base',
    'JoinRole',
    'NewbieChannel', 'NewbieGuild', 'NewbieUser',
    'OptinChannel',
    'WhitelistedChannel',
    'create_all'
]
