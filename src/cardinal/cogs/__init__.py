import logging

from .basecog import BaseCog
from .channels import Channels
from .moderation import Moderation
from .newbie import Newbies
from .roles import Roles
from .whitelist import Whitelisting

logger = logging.getLogger(__name__)
cogs = (Channels, Moderation, Newbies, Roles, Whitelisting)


def setup(bot):
    for cog in cogs:
        logger.info('Initializing "{}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except Exception:
            logger.exception('Error during initialization of "{}".'.format(cog.__name__))
        else:
            logger.info('Successfully initialized "{}".'.format(cog.__name__))
