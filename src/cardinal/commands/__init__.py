# Please kindly ignore this craftiness

import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Cog:

    def __init__(self, bot):
        self.bot = bot


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]


def setup(bot):
    for cog in all_subclasses(Cog):
        logger.log(logging.INFO, 'Initializing "{0}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except Exception as e:
            logger.log(logging.ERROR, 'Error during initialization.')
            logger.log(logging.ERROR, '{0}: {1}'.format(type(e).__name__, e))
        else:
            logger.log(logging.INFO, 'Successfully initialized "{0}".'.format(cog.__name__))


imports = [importlib.import_module('.' + mod_name, __name__)
           for finder, mod_name, is_pkg in pkgutil.iter_modules(__path__) if not is_pkg]