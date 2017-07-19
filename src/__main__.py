import json
import logging
from os import path
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if len(sys.argv) <= 2 and not path.isfile('config.json'):
    logger.log(logging.FATAL, 'Please pass the path of the config file as the first command-line argument or provide a "config.json" in the PWD.')
    sys.exit(1)

config_file_path = sys.argv[1] if len(sys.argv) >= 2 else 'config.json'
if not path.isfile(config_file_path):
    logger.log(logging.FATAl, 'Config file not found. Please make sure the provided path is correct.')
    sys.exit(1)

with open(config_file_path) as config_file:
    config = json.load(config_file)

from cardinal import bot

try:
    logger.log(logging.INFO, 'Loading commands.')
    bot.load_extension('cardinal.commands')
    logger.log(logging.INFO, 'Loaded all commands.')
except Exception as e:
    logger.log(logging.ERROR, 'Failed to load commands.')
    logger.log(logging.ERROR, '{0}: {1}'.format(type(e).__name__, e))

bot.run(config['token'])
