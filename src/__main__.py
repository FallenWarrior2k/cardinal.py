import logging
import json
import sys

logger = logging.getLogger(__name__)

if not len(sys.argv) > 1:
    logger.log(logging.FATAL, 'Please pass the path of the config file as the first command-line argument')
    sys.exit(1)

with open(sys.argv[1]) as config_file:
    config = json.load(config_file)

from cardinal import bot
from cardinal.commands import *

bot.run(config['token'])
