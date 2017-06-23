# Please kindly ignore this craftiness

import glob
import importlib
import logging
from os.path import dirname, basename, isfile, isdir

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


nodes = glob.glob(dirname(__file__) + '/*')
modules = (basename(f)[:-3] for f in nodes if isfile(f) and basename(f).endswith('.py') and not basename(f).startswith('__'))
packages = (basename(f) for f in nodes if isdir(f) and isfile(f + '/__init__.py'))

imports = {}

for _module in modules:
    imports[_module] = importlib.import_module('.' + _module, __name__)

for package in packages:
    imports[package] = importlib.import_module('.' + package, __name__)