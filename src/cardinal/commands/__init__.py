# Please kindly ignore this craftiness

import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)


class Cog:
    def __init__(self, bot):
        self.bot = bot


def all_subclasses(cls):
    yield from cls.__subclasses__()
    yield from (g for s in cls.__subclasses__() for g in all_subclasses(s))


def setup(bot):
    imports = []
    for finder, mod_name, is_pkg in pkgutil.iter_modules(__path__):
        if is_pkg:
            continue

        try:
            imports.append(importlib.import_module('.' + mod_name, __name__))  # Ensure one borked module does not kill the whole bot
        except:
            logger.exception('Error while importing "{}.{}".'.format(__name__, mod_name))

    for cog in all_subclasses(Cog):
        logger.info('Initializing "{}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except:
            logger.exception('Error during initialization.')
        else:
            logger.info('Successfully initialized "{}".'.format(cog.__name__))

    del imports[:]  # Delete all items in list
