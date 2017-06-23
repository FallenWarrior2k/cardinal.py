import json
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if len(sys.argv) <= 1:
    logger.log(logging.FATAL, 'Please pass the path of the config file as the first command-line argument')
    sys.exit(1)

with open(sys.argv[1]) as config_file:
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
