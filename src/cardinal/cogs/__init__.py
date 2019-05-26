import logging

from .anilist import Anilist
from .channels import Channels
from .moderation import Moderation
from .mute import Mute
from .newbie import Newbies
from .roles import Roles
from .stop import Stop
from .whitelist import Whitelisting

logger = logging.getLogger(__name__)
cogs = (Anilist, Channels, Moderation, Mute, Newbies, Roles, Stop, Whitelisting)


def setup(bot):
    for cog in cogs:
        logger.info('Initializing "{}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except Exception:
            logger.exception('Error during initialization of "{}".'.format(cog.__name__))
            raise  # Propagate to prevent starting an incomplete bot
        else:
            logger.info('Successfully initialized "{}".'.format(cog.__name__))
