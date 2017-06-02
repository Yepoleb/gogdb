import json
import os.path
import configparser

PAGE_FORMAT = "ajax/US_USD_{}.json"

def load_pages(config):
    cache_dir = config["cache"]["path"]
    game_tuples = []

    page_num = 1
    total_pages = 1
    while page_num <= total_pages:
        filename = os.path.join(cache_dir, PAGE_FORMAT).format(page_num)
        with open(filename) as cachefile:
            page_json = json.load(cachefile)

        for product in page_json["products"]:
            game_tuples.append((product["url"], product["id"]))

        total_pages = page_json["totalPages"]
        page_num += 1

    return game_tuples, total_pages

def load_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config
