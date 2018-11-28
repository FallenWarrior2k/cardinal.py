#!/usr/bin/env python3

import json
import logging
import sys
from os import path

from sqlalchemy import create_engine

from cardinal import Bot

if __name__ == '__main__':
    config_file_path = sys.argv[1] if len(sys.argv) >= 2 else 'config.json'
    if not path.isfile(config_file_path):
        logging.fatal('Please pass a valid path to a config file as the first command-line argument'
                      ' or provide a "config.json" in the PWD.')
        sys.exit(1)

    with open(config_file_path) as config_file:
        config = json.load(config_file)
    try:
        logging.basicConfig(level=config['logging_level'].upper())
    except ValueError:
        logging.basicConfig(level=logging.INFO)
        logging.warning('"{}" is not a valid logging level. Defauted to "INFO".'
                        .format(config['logging_level']))

    logger = logging.getLogger(__name__)

    engine = create_engine(config['db']['connect_string'], **config['db']['options'])
    bot = Bot(command_prefix=config['cmd_prefix'],
              engine=engine,
              default_game=config['default_game'])

    logger.info('Loading cogs.')
    bot.load_extension('cardinal.cogs')
    logger.info('Finished loading cogs.')

    bot.run(config['token'])
