#!/usr/bin/env python3

import json
import logging
import sys
from os import path

from cardinal.container import RootContainer
from cardinal.cogs import load_cogs

if __name__ == "__main__":
    config_file_path = sys.argv[1] if len(sys.argv) >= 2 else "config.json"
    if not path.isfile(config_file_path):
        logging.fatal(
            "Please pass a valid path to a config file as the first command-line argument"
            ' or provide a "config.json" in the PWD.'
        )
        sys.exit(1)

    with open(config_file_path) as config_file:
        config = json.load(config_file)

    log_level = config.get("log_level") or config.get("logging_level") or "INFO"
    try:
        logging.basicConfig(level=log_level.upper())
    except ValueError:
        logging.basicConfig(level=logging.INFO)
        logging.warning(
            '"{}" is not a valid logging level. Defauted to "INFO".'.format(log_level)
        )

    logger = logging.getLogger(__name__)
    root = RootContainer(config=config)

    logger.info("Loading cogs.")
    load_cogs(root)
    logger.info("Finished loading cogs.")

    root.run_bot()
