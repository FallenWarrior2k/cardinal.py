# Please kindly ignore this craftiness

import importlib
import logging
import pkgutil

import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Cog:
    def __init__(self, bot):
        self.bot = bot


def all_subclasses(cls):
    yield from cls.__subclasses__()
    yield from (g for s in cls.__subclasses__() for g in all_subclasses(s))


def setup(bot):
    for cog in all_subclasses(Cog):
        logger.log(logging.INFO, 'Initializing "{0}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except:
            logger.log(logging.ERROR, 'Error during initialization.')
            logger.log(logging.ERROR, traceback.format_exc())
        else:
            logger.log(logging.INFO, 'Successfully initialized "{0}".'.format(cog.__name__))


imports = [importlib.import_module('.' + mod_name, __name__)
           for finder, mod_name, is_pkg in pkgutil.iter_modules(__path__) if not is_pkg]
