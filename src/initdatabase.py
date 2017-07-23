import importlib
import json
import logging
import pkgutil
import sys
from os import path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if len(sys.argv) <= 2 and not path.isfile('config.json'):
    logger.log(logging.FATAL,
               'Please pass the path of the config file as the first command-line argument or provide a "config.json" in the PWD.')
    sys.exit(1)

config_file_path = sys.argv[1] if len(sys.argv) >= 2 else 'config.json'
if not path.isfile(config_file_path):
    logger.log(logging.FATAL, 'Config file not found. Please make sure the provided path is correct.')
    sys.exit(1)

with open(config_file_path) as config_file:
    config = json.load(config_file)

import cardinal.db as db

package = db
modules = [importlib.import_module('.' + mod_name, package.__name__)
           for finder, mod_name, is_pkg in pkgutil.iter_modules(package.__path__) if not is_pkg]

db.Base.metadata.create_all(db.engine)