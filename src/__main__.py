import json
import sys

if not len(sys.argv) > 1:
    print('Please pass the path of the config file as the first command-line argument')
    sys.exit(1)

with open(sys.argv[1]) as config_file:
    config = json.load(config_file)


import cardinal
