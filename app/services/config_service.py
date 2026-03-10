import json


def load_scoring_weights():

    with open("config.json") as f:
        config = json.load(f)

    return config["scoring_weights"]
