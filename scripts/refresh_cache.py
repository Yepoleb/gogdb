import json
import requests
import os
import os.path
import sys
import logging
from concurrent import futures

from requests_futures.sessions import FuturesSession

import gog_shared

GAMES_AJAX = "https://www.gog.com/games/ajax/filtered?mediaType=game&page={}&sort=bestselling"
GOG_API = "https://api.gog.com/products/{}?expand=downloads,description"
THREAD_NUM = 4



logger = logging.getLogger("RefreshCache")
logging.basicConfig(level=logging.INFO)

if len(sys.argv) != 2:
    print("Usage: {} <config.ini>".format(sys.argv[0]))
    exit(1)

config = gog_shared.load_config(sys.argv[1])
cachedir = config["cache"]["path"]


os.makedirs(os.path.join(cachedir, "ajax"), exist_ok=True)
os.makedirs(os.path.join(cachedir, "game"), exist_ok=True)
os.makedirs(os.path.join(cachedir, "api"), exist_ok=True)

session = requests.Session()
session.cookies["gog_lc"] = "US_USD_en"
session.headers["User-Agent"] = "gogdb/0.1 (/u/Yepoleb)"


logger.info("Downloading catalog pages")
game_tuples = []
page_num = 1
total_pages = 1
while page_num <= total_pages:
    logger.debug("Page %s/%s", page_num, total_pages)
    page_resp = session.get(GAMES_AJAX.format(page_num))
    page_json = page_resp.json()
    filepath = os.path.join(cachedir, "ajax/US_USD_{}.json".format(page_num))
    with open(filepath, "w") as cachefile:
        json.dump(page_json, cachefile, indent=2, sort_keys=True)

    for product in page_json["products"]:
        game_tuples.append((product["url"], product["id"]))

    total_pages = page_json["totalPages"]
    page_num += 1


f_session = FuturesSession(
    executor=futures.ThreadPoolExecutor(max_workers=THREAD_NUM),
    session=session)
prop_map = {}

logger.info("Queueing requests")
for url, prod_id in game_tuples:
    if not url:
        logger.warning("Product %s has no game page", prod_id)
        continue

    dest = os.path.join(cachedir, url.lstrip('/'))
    future = f_session.get("https://www.gog.com" + url)
    prop_map[future] = (url, dest)


for _, prod_id in game_tuples:
    future = f_session.get(GOG_API.format(prod_id))
    dest = os.path.join(cachedir, "api/{}.json".format(prod_id))
    prop_map[future] = (prod_id, dest)


logger.info("Downloading files")
num_requests = len(prop_map)
for num_resp, future in enumerate(futures.as_completed(prop_map)):
    game, dest = prop_map[future]
    response = future.result()
    logger.debug("%s/%s %s", num_resp, num_requests, game)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("Request for %s failed: %s", game, response.status_code)
        continue
    with open(dest, "w") as cachefile:
        cachefile.write(response.text)

    # Fix memory leak
    future._result = None

logger.info("Done")
