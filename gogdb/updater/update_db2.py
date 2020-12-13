import asyncio
import json
import logging
import collections
import datetime
import pathlib
import dataclasses
import re
import zlib
import gzip
import copy
import os

import dateutil.parser
import aiohttp
import flask

from gogdb.core.gogtoken import GogToken
import gogdb.core.model as model
import gogdb.core.storage as storage
from gogdb.core.normalization import normalize_system
from gogdb.core.changelogger import Changelogger

CLIENT_VERSION = "1.2.17.9" # Just for their statistics
USER_AGENT = f"GOGGalaxyClient/{CLIENT_VERSION} gogdb/2.0"
REQUEST_RETRIES = 3

# Initialize logging
logging.basicConfig()
logger = logging.getLogger("UpdateDB")
session_logger = logging.getLogger("UpdateDB.session")



def scramble_number(value):
    return (value * 16205650284070698839) & 0xFFFFFFFF

# Caching constants
CACHE_NONE = 0      # Download without caching
CACHE_STORE = 1     # Download and store to disk
CACHE_LOAD = 2      # Only load from disk
CACHE_FALLBACK = 3  # Try to load, on failure fall back to store




class QueueExhausted(Exception):
    """Signals when a queue is empty and will no longer receive new elements"""
    pass

class QueueManager:
    def __init__(self):
        self.prices_queue = asyncio.Queue()
        self.scheduled_prices = set()
        # No more prices may get added after this event is set
        self.prices_exhausted = asyncio.Event()
        self.products_queue = asyncio.Queue()
        self.scheduled_products = set()
        # No more products may get added after this event is set
        self.products_exhausted = asyncio.Event()

    def schedule_product(self, prod_id, store=False):
        assert type(prod_id) is int
        if prod_id not in self.scheduled_products:
            self.scheduled_products.add(prod_id)
            self.products_queue.put_nowait(prod_id)
        if store and prod_id not in self.scheduled_prices:
            self.scheduled_prices.add(prod_id)
            self.prices_queue.put_nowait(prod_id)

    def schedule_products(self, prod_ids, store=False):
        for prod_id in prod_ids:
            self.schedule_product(prod_id, store)

    async def _get_from_queue(self, queue, exhausted_event):
        queue_task = asyncio.create_task(queue.get())
        exhausted_task = asyncio.create_task(exhausted_event.wait())
        done, pending = await asyncio.wait(
            {queue_task, exhausted_task},
            return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.exception() is not None:
                raise task.exception()
        for task in pending:
            task.cancel()
        if queue_task in done:
            return queue_task.result()
        else:
            raise QueueExhausted()

    async def get_from_products(self):
        return await self._get_from_queue(
            self.products_queue, self.products_exhausted)

    async def get_from_prices(self):
        return await self._get_from_queue(
            self.prices_queue, self.prices_exhausted)

    def products_done(self):
        self.products_queue.task_done()

    def prices_done(self):
        self.prices_queue.task_done()


async def store_list_worker(session, qman):
    current_page = 1
    total_pages = 1
    ordered_ids = []
    while current_page <= total_pages:
        content = await fetch_store_page(session, current_page)
        logger.info("Downloaded store page %s", current_page)
        if content is None:
            break
        total_pages = content["totalPages"]
        page_ids = [prod["id"] for prod in content["products"]]
        qman.schedule_products(page_ids, store=True)
        ordered_ids += page_ids
        current_page += 1
    return ordered_ids

def log_price(price_log, price_record, country):
    currency = price_record.currency
    currency_log = price_log[country][currency]
    if currency_log:
        last_price = currency_log[-1]
        if not record.same_price(last_price):
            currency_log.append(record)
    else:
        currency_log.append(record)


async def prices_worker(session, qman):
    while True:
        chunk = []
        while len(chunk) < 100:
            try:
                prod_id = await qman.get_from_prices()
            except QueueExhausted:
                logger.debug("Prices queue exhausted for products")
                break
            chunk.append(prod_id)

        if not chunk:
            break

        logger.info(f"Fetching prices for {chunk}")

        chunk_date = datetime.datetime.now(datetime.timezone.utc)

        content = await fetch_prices(session, chunk, "US")
        if not content:
            logger.error(f"Failed to fetch prices for {chunk}")

        items_by_id = {
            product_item["_embedded"]["product"]["id"]: product_item
            for product_item in content["_embedded"]["items"]
        }

        for prod_id in chunk:
            product_item = items_by_id.get(prod_id)

            if product_item:
                price_by_currency_id = {}
                for currency_item in product_item["_embedded"]["prices"]:
                    record = model.PriceRecord(
                        price_base = int(currency_item["basePrice"].split()[0]),
                        price_final = int(currency_item["finalPrice"].split()[0]),
                        currency = currency_item["currency"]["code"],
                    )
                    price_by_currency_id[("US", record.currency)] = record

            else:
                price_by_currency_id = {}

            update_prices(prod_id, price_by_currency_id)


def update_prices(prod_id, price_by_currency_id):
    price_log = db.prices.load(prod_id)
    if price_log is None:
        price_log = {"US": {"USD": []}}

    date = datetime.datetime.now(datetime.timezone.utc)

    for currency_id in [("US", "USD")]:
        record = price_by_currency_id.get(currency_id)
        if not record:
            record = model.PriceRecord(
                price_base = None,
                price_final = None,
                currency = currency_id[1]
            )
        record.date = date
        currency_log = price_log[currency_id[0]][currency_id[1]]
        if currency_log:
            last_price = currency_log[-1]
            if not record.same_price(last_price):
                currency_log.append(record)
        else:
            currency_log.append(record)

    db.prices.save(price_log, prod_id)


IMAGE_RE = re.compile(r"\w{64}")
def extract_imageid(image_url):
    if image_url is None:
        return None
    m = IMAGE_RE.search(image_url)
    if m is None:
        return None
    else:
        return m.group(0)

PRODID_RE = re.compile(r"games/(\d+)")
def extract_prodid(apiv2_url):
    m = PRODID_RE.search(apiv2_url)
    return int(m.group(1))

META_ID_RE = re.compile(r"v2/meta/.{2}/.{2}/(\w+)")
def extract_metaid(meta_url):
    m = META_ID_RE.search(meta_url)
    if m is None:
        return None
    else:
        return m.group(1)

def parse_datetime(date_str):
    if date_str is None:
        return None
    else:
        return dateutil.parser.isoparse(date_str)


async def fetch_product_v0(session, prod_id):
    return await session.get_json(
        f"api v0 {prod_id}",
        url=f"https://api.gog.com/products/{prod_id}?locale=en_US&expand=downloads,screenshots,videos,changelog",
        path=storage_path / "raw" / "prod_v0" / f"{prod_id}_v0.json",
        caching=CACHE_FALLBACK)

async def fetch_product_v2(session, prod_id):
    return await session.get_json(
        f"api v2 {prod_id}",
        url=f"https://api.gog.com/v2/games/{prod_id}?locale=en-US",
        path=storage_path / "raw" / "prod_v2" / f"{prod_id}_v2.json",
        caching=CACHE_FALLBACK)

async def fetch_builds(session, prod_id, system):
    return await session.get_json(
        f"api v0 {prod_id}",
        url=f"https://content-system.gog.com/products/{prod_id}/os/{system}/builds?generation=2",
        path=storage_path / "raw" / "builds" / f"{prod_id}_builds_{system}.json",
        caching=CACHE_FALLBACK)

async def fetch_repo_v1(session, repo_url, prod_id, build_id):
    return await session.get_json(
        f"repo v1 {repo_url}",
        url=repo_url,
        path=storage_path / f"raw/repo_v1/{prod_id}_{build_id}.json",
        caching=CACHE_FALLBACK)

async def fetch_manifest_v1(session, mf_name, manifest_url):
    return await session.get_json(
        f"manifest v1 {mf_name}",
        url=manifest_url,
        path=None,
        caching=CACHE_NONE)

async def fetch_repo_v2(session, repo_url, prod_id, build_id):
    return await session.get_json(
        f"repo v2 {repo_url}",
        url=repo_url,
        path=storage_path / f"raw/repo_v2/{prod_id}_{build_id}.json",
        caching=CACHE_FALLBACK,
        decompress=True)

async def fetch_manifest_v2(session, manifest_id):
    manifest_url = "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
        manifest_id[0:2], manifest_id[2:4], manifest_id)
    return await session.get_json(
        f"manifest v2 {manifest_id}",
        url=manifest_url,
        path=None,
        caching=CACHE_NONE,
        decompress=True)

async def fetch_store_page(session, page_num):
    return await session.get_json(
        f"store page {page_num}",
        url=f"https://www.gog.com/games/ajax/filtered?mediaType=game&page={page_num}&sort=popularity",
        path=storage_path / "raw" / "store" / f"page_{page_num}.json",
        caching=CACHE_FALLBACK)

async def fetch_prices(session, chunk, country_code):
    ids_str = ",".join(str(c) for c in chunk)
    cache_id = sum(scramble_number(c) for c in chunk)
    return await session.get_json(
        f"prices for {chunk}",
        url=f"https://api.gog.com/products/prices?ids={ids_str}&countryCode={country_code}",
        path=storage_path / "raw" / "prices" / f"prices_{chunk[0]}_{cache_id}_{country_code}.json",
        caching=CACHE_FALLBACK)


def set_properties_v0(prod, v0_cont):
    prod.id = v0_cont["id"]
    prod.access = 1

    prod.title = v0_cont["title"]
    prod.type = v0_cont["game_type"]
    prod.slug = v0_cont["slug"]

    prod.cs_systems = []
    for cs_name in ["windows", "osx", "linux"]:
        if v0_cont["content_system_compatibility"][cs_name]:
            prod.cs_systems.append(normalize_system(cs_name))

    prod.store_date = parse_datetime(v0_cont["release_date"])
    prod.is_in_development = v0_cont["in_development"]["active"]
    prod.is_pre_order = v0_cont["is_pre_order"]

    prod.image_logo = extract_imageid(v0_cont["images"]["logo"])
    prod.image_background = extract_imageid(v0_cont["images"]["background"])
    prod.image_icon = extract_imageid(v0_cont["images"]["sidebarIcon"])

    prod.link_forum = v0_cont["links"]["forum"]
    prod.link_store = v0_cont["links"]["product_card"]
    prod.link_support = v0_cont["links"]["support"]

    prod.screenshots = [x["image_id"] for x in v0_cont.get("screenshots", [])]
    prod.videos = [
        model.Video(
            video_url=v["video_url"],
            thumbnail_url=v["thumbnail_url"],
            provider=v["provider"]
        ) for v in v0_cont.get("videos", [])
    ]

    if v0_cont["dlcs"]:
        prod.dlcs = [x["id"] for x in v0_cont["dlcs"]["products"]]

    prod.changelog = v0_cont["changelog"] or None

    def parse_file(file_cont):
        return model.File(
            id = str(file_cont["id"]),
            size = file_cont["size"],
            downlink = file_cont["downlink"]
        )

    def parse_bonusdls(bonus_cont):
        return [
            model.BonusDownload(
                id = str(dl["id"]),
                name = dl["name"],
                total_size = dl["total_size"],
                bonus_type = dl["type"],
                count = dl["count"],
                files = [parse_file(dlfile) for dlfile in dl["files"]]
            ) for dl in bonus_cont
        ]
    prod.dl_bonus = parse_bonusdls(v0_cont["downloads"]["bonus_content"])

    def parse_softwaredls(software_cont):
        return [
            model.SoftwareDownload(
                id = dl["id"],
                name = dl["name"],
                total_size = dl["total_size"],
                os = normalize_system(dl["os"]),
                language = model.Language(dl["language"], dl["language_full"]),
                version = dl["version"],
                files = [parse_file(dlfile) for dlfile in dl["files"]]
            ) for dl in software_cont
        ]
    prod.dl_installer = parse_softwaredls(v0_cont["downloads"]["installers"])
    prod.dl_langpack = parse_softwaredls(v0_cont["downloads"]["language_packs"])
    prod.dl_patch = parse_softwaredls(v0_cont["downloads"]["patches"])

def set_properties_v2(prod, v2_cont):
    v2_embed = v2_cont["_embedded"]
    v2_links = v2_cont["_links"]

    prod.features = [
        model.Feature(
            id=x["id"],
            name=x["name"]
        ) for x in v2_embed["features"]
    ]
    localizations_map = collections.defaultdict(lambda: model.Localization())
    for loc in v2_embed["localizations"]:
        loc_embed = loc["_embedded"]
        localization = localizations_map[loc_embed["language"]["code"]]
        localization.code = loc_embed["language"]["code"]
        localization.name = loc_embed["language"]["name"]
        if loc_embed["localizationScope"]["type"] == "text":
            localization.text = True
        elif loc_embed["localizationScope"]["type"] == "audio":
            localization.audio = True
    prod.localizations = list(localizations_map.values())
    prod.tags = [
        model.Tag(
            id=x["id"],
            level=x["level"],
            name=x["name"],
            slug=x["slug"]
        ) for x in v2_embed["tags"]
    ]
    prod.comp_systems = [
        normalize_system(support_entry["operatingSystem"]["name"])
        for support_entry in v2_embed["supportedOperatingSystems"]
    ]
    prod.is_using_dosbox = v2_cont["isUsingDosBox"]

    prod.developers = [x["name"] for x in v2_embed["developers"]]
    prod.publisher = v2_embed["publisher"]["name"]
    prod.copyright = v2_cont["copyrights"] or None

    prod.global_date = parse_datetime(v2_embed["product"].get("globalReleaseDate"))
    if "galaxyBackgroundImage" in v2_links:
        prod.image_galaxy_background = extract_imageid(v2_links["galaxyBackgroundImage"]["href"])
    prod.image_boxart = extract_imageid(v2_links["boxArtImage"]["href"])
    prod.image_icon_square = extract_imageid(v2_links["iconSquare"]["href"])

    prod.editions = [
        model.Edition(
            id=ed["id"],
            name=ed["name"],
            has_product_card=ed["hasProductCard"]
        ) for ed in v2_embed["editions"]
    ]
    prod.includes_games = [
        extract_prodid(link["href"])
        for link in v2_links.get("includesGames", [])
    ]
    prod.is_included_in = [
        extract_prodid(link["href"])
        for link in v2_links.get("isIncludedInGames", [])
    ]
    prod.required_by = [
        extract_prodid(link["href"])
        for link in v2_links.get("isRequiredByGames", [])
    ]
    prod.requires = [
        extract_prodid(link["href"])
        for link in v2_links.get("requiresGames", [])
    ]

    if v2_embed["series"]:
        prod.series = model.Series(
            id=v2_embed["series"]["id"],
            name=v2_embed["series"]["name"]
        )

    prod.description = v2_cont["description"]

def set_builds(prod, build_cont, system):
    for build in prod.builds:
        # Mark all builds as unlisted to relist them later
        if build.os == system:
            build.listed = False

    for build_item in build_cont["items"]:
        build_id = int(build_item["build_id"])
        # Find existing build based on id and set `build` to it
        for existing_build in prod.builds:
            if existing_build.id == build_id:
                build = existing_build
                break
        else: # No existing build found
            build = model.Build()
            prod.builds.append(build)
        build.id = build_id
        build.product_id = int(build_item["product_id"])
        build.os = build_item["os"]
        build.branch = build_item["branch"]
        build.version = build_item["version_name"] or None
        build.tags = build_item["tags"]
        build.public = build_item["public"]
        build.date_published = parse_datetime(build_item["date_published"])
        build.generation = build_item["generation"]
        build.legacy_build_id = build_item.get("legacy_build_id")
        build.meta_id = extract_metaid(build_item["link"])
        build.link = build_item["link"]
        build.listed = True

    prod.builds.sort(key=lambda b: b.date_published)

async def product_worker(session, qman):
    while True:
        try:
            prod_id = await qman.get_from_products()
        except QueueExhausted:
            logger.debug("Received queue exhausted for products")
            break
        logger.info("Downloading %s", prod_id)

        timestamp = datetime.datetime.now(datetime.timezone.utc)
        prod = db.product.load(prod_id)
        if prod is None:
            prod = model.Product()
            prod.added_on = timestamp
            old_prod = None
        else:
            old_prod = copy.deepcopy(prod)

        changelog = db.changelog.load(prod_id)
        if changelog is None:
            changelog = []
        old_changelog_len = len(changelog)
        prod_changelogger = Changelogger(prod, old_prod, timestamp)

        prod.access = 0

        v0_cont = await fetch_product_v0(session, prod_id)
        # Basic sanity check
        has_v0 = v0_cont and "id" in v0_cont
        if has_v0:
            set_properties_v0(prod, v0_cont)
            prod.access = 1
            # Add referenced dlc to queue
            qman.schedule_products(prod.dlcs)

            v2_cont = await fetch_product_v2(session, prod_id)
            has_v2 = v2_cont and "_embedded" in v2_cont
            if has_v2:
                set_properties_v2(prod, v2_cont)
                prod.access = 2
                # Add referenced products to queue
                qman.schedule_products(
                    prod.includes_games + prod.is_included_in +
                    prod.required_by + prod.requires)

            for system in prod.cs_systems:
                builds_cont = await fetch_builds(session, prod_id, system)
                if not builds_cont:
                    continue

                set_builds(prod, builds_cont, system)

            for build in prod.builds:
                repo = db.repository.load(prod.id, build.id)
                if build.generation == 1:
                    if repo is None:
                        repo = await fetch_repo_v1(session, build.link, prod.id, build.id)
                        db.repository.save(repo, prod.id, build.id)
                    for depot in repo["product"]["depots"]:
                        if "manifest" not in depot:
                            continue
                        mf_filename = depot["manifest"]
                        mf_url = build.link.rsplit("/", 1)[0] + "/" + mf_filename
                        if not db.manifest_v1.has(mf_filename):
                            manifest = await fetch_manifest_v1(session, mf_filename, mf_url)
                            db.manifest_v1.save(manifest, mf_filename)
                        else:
                            logger.debug(f"Not redownloading manifest v1 {mf_filename}")
                else:
                    if repo is None:
                        repo = await fetch_repo_v2(session, build.link, prod.id, build.id)
                        db.repository.save(repo, prod.id, build.id)
                    for depot in repo["depots"] + [repo["offlineDepot"]]:
                        mf_id = depot["manifest"]
                        if not db.manifest_v2.has(mf_id):
                            manifest = await fetch_manifest_v2(session, mf_id)
                            db.manifest_v2.save(manifest, mf_id)
                        else:
                            logger.debug(f"Not redownloading manifest v2 {mf_id}")

            prod.last_updated = timestamp

            if old_prod:
                prod_changelogger.property("title")
                prod_changelogger.property("comp_systems")
                prod_changelogger.property("is_pre_order")
                prod_changelogger.property("changelog")
                prod_changelogger.downloads("bonus")
                prod_changelogger.downloads("installer")
                prod_changelogger.downloads("langpack")
                prod_changelogger.downloads("patch")
                prod_changelogger.builds()


        if prod.has_content():
            if old_prod:
                prod_changelogger.property("access")
            else:
                prod_changelogger.prod_added()
        changelog += prod_changelogger.entries

        if prod.has_content():
            db.product.save(prod, prod.id)

        if len(changelog) != old_changelog_len:
            db.changelog.save(changelog, prod.id)

        qman.products_queue.task_done()

def set_storedata(popularity_order, all_ids):
    popularity_by_id = {
        prod_id: rank_0_based + 1
        for rank_0_based, prod_id in enumerate(reversed(popularity_order))
    }
    for prod_id in all_ids:
        prod = db.product.load(prod_id)
        if not prod:
            continue
        prod.sale_rank = popularity_by_id.get(prod_id, 0)
        db.product.save(prod, prod_id)
        if prod.sale_rank == 0:
            # The product is not for sale, so we need to set its price to unavailable now
            update_prices(prod_id, {})


async def wait_or_raise(waiting, raising):
    """Return if at least one of the waiting awaitables finishes,
       but also monitors raising for exceptions."""
    remaining_tasks = waiting | raising
    while True:
        done, pending = await asyncio.wait(
            remaining_tasks, return_when=asyncio.FIRST_COMPLETED)
        for done_task in done:
            if done_task.exception() is not None:
                raise done_task.exception()
        done_waiting = set()
        for done_task in done:
            if done_task in waiting:
                done_waiting.add(done_task)
            else:
                remaining_tasks.remove(done_task)
        if done_waiting:
            return done_waiting

async def main():
    #logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("aiohttp.client").setLevel(logging.DEBUG)

    config = flask.Config()
    config.from_envvar("GOGDB_CONFIG")
    # Initialize db
    global storage_path, db
    storage_path = pathlib.Path(config["STORAGE_PATH"])
    db = storage.Storage(config["STORAGE_PATH"])

    session = GogSession()
    qman = QueueManager()

    ids = db.ids.load()
    ids.sort(key=scramble_number)
    assert ids
    qman.schedule_products(ids)

    store_list_task = asyncio.create_task(
        store_list_worker(session, qman))
    product_task = asyncio.create_task(
        product_worker(session, qman))
    prices_task = asyncio.create_task(
        prices_worker(session, qman))
    await wait_or_raise({store_list_task}, {product_task, prices_task})
    qman.products_exhausted.set()
    await wait_or_raise({product_task}, {prices_task})
    qman.prices_exhausted.set()
    await prices_task

    ids = list(qman.scheduled_products)
    db.ids.save(ids)

    logger.info("Setting popularities")
    popularity_order = store_list_task.result()
    set_storedata(popularity_order, ids)

    await session.close()
    await asyncio.sleep(0.250) # Wait for aiohttp to close connections

asyncio.run(main())
