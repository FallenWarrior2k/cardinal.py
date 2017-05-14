import json

def load_config(path):
    with open(path) as data_file:
        return json.load(data_file)