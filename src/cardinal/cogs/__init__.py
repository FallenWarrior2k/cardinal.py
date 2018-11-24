# Please kindly ignore this craftiness

import importlib
import logging
import pkgutil

from .basecog import BaseCog

logger = logging.getLogger(__name__)


def all_subclasses(cls):
    yield from cls.__subclasses__()
    yield from (g for s in cls.__subclasses__() for g in all_subclasses(s))


def setup(bot):
    imports = []
    for _, mod_name, is_pkg in pkgutil.iter_modules(__path__):
        if is_pkg:
            continue

        try:  # Ensure one borked module does not kill the whole bot
            imports.append(importlib.import_module('.' + mod_name, __name__))
        except Exception:
            logger.exception('Error while importing "{}.{}".'.format(__name__, mod_name))

    for cog in all_subclasses(BaseCog):
        logger.info('Initializing "{}".'.format(cog.__name__))
        try:
            bot.add_cog(cog(bot))
        except Exception:
            logger.exception('Error during initialization of "{}".'.format(cog.__name__))
        else:
            logger.info('Successfully initialized "{}".'.format(cog.__name__))
