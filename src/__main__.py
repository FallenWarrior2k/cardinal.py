import importlib
import json
import logging
import sys
from os import path

from sqlalchemy import create_engine

logging.basicConfig(level=logging.WARNING)

if len(sys.argv) <= 2 and not path.isfile('config.json'):
    logging.fatal('Please pass the path of the config file as the first command-line argument or provide a "config.json" in the PWD.')
    sys.exit(1)

config_file_path = sys.argv[1] if len(sys.argv) >= 2 else 'config.json'
if not path.isfile(config_file_path):
    logging.fatal('Config file not found. Please make sure the provided path is correct.')
    sys.exit(1)

with open(config_file_path) as config_file:
    config = json.load(config_file)

root_logger = logging.getLogger()
try:
    root_logger.setLevel(config['logging_level'].upper())
except:
    root_logger.setLevel(logging.INFO)
    logging.error('"{}" is not a valid logging level. Defauted to "INFO".'.format(config['logging_level']))

logger = logging.getLogger(__name__)
logger.info('Loaded config file. Logging level set to "{}".'.format(logging.getLevelName(root_logger.getEffectiveLevel())))

cardinal = importlib.import_module('cardinal')
engine = create_engine(config['db']['connect_string'], **config['db']['options'])
bot = cardinal.Bot(command_prefix=config['cmd_prefix'], description='cardinal.py', default_game=config['default_game'], engine=engine)

try:
    logger.info('Loading cogs.')
    bot.load_extension('cardinal.cogs')
    logger.info('Finished loading cogs.')
except:
    logger.exception('An error occured while loading the cogs.')

bot.run(config['token'])
del cardinal
