#!/usr/bin/python3
import asyncio
import logging
import datetime
import copy
import sys

import flask

import gogdb.core.model as model
import gogdb.core.storage as storage
from gogdb.core.changelogger import Changelogger
from gogdb.updater.gogsession import GogSession
import gogdb.updater.dataextractors as dataextractors
from gogdb.updater.gen_index import index_main


logger = logging.getLogger("UpdateDB")

def scramble_number(value):
    return (value * 16205650284070698839) & 0xFFFFFFFF

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
        content = await session.fetch_store_page(current_page)
        logger.info("Downloaded store page %s", current_page)
        if content is None:
            break
        total_pages = content["totalPages"]
        page_ids = [prod["id"] for prod in content["products"]]
        qman.schedule_products(page_ids, store=True)
        ordered_ids += page_ids
        current_page += 1
    return ordered_ids


def update_prices(db, prod_id, price_by_currency_id):
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

async def prices_worker(session, qman, db):
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

        content = await session.fetch_prices(chunk, "US")
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

            update_prices(db, prod_id, price_by_currency_id)


async def product_worker(session, qman, db):
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

        v0_cont = await session.fetch_product_v0(prod_id)
        # Basic sanity check
        has_v0 = v0_cont and "id" in v0_cont
        if has_v0:
            dataextractors.extract_properties_v0(prod, v0_cont)
            prod.access = 1
            # Add referenced dlc to queue
            qman.schedule_products(prod.dlcs)

            v2_cont = await session.fetch_product_v2(prod_id)
            has_v2 = v2_cont and "_embedded" in v2_cont
            if has_v2:
                dataextractors.extract_properties_v2(prod, v2_cont)
                prod.access = 2
                # Add referenced products to queue
                qman.schedule_products(
                    prod.includes_games + prod.is_included_in +
                    prod.required_by + prod.requires)

            for system in prod.cs_systems:
                builds_cont = await session.fetch_builds(prod_id, system)
                if not builds_cont:
                    continue

                dataextractors.extract_builds(prod, builds_cont, system)

            for build in prod.builds:
                repo = db.repository.load(prod.id, build.id)
                if build.generation == 1:
                    if repo is None:
                        repo = await session.fetch_repo_v1(build.link, prod.id, build.id)
                        if repo is None:
                            continue
                        db.repository.save(repo, prod.id, build.id)
                    for depot in repo["product"]["depots"]:
                        if "manifest" not in depot:
                            continue
                        mf_filename = depot["manifest"]
                        mf_url = build.link.rsplit("/", 1)[0] + "/" + mf_filename
                        if not db.manifest_v1.has(mf_filename):
                            manifest = await session.fetch_manifest_v1(mf_filename, mf_url)
                            if manifest is None:
                                continue
                            db.manifest_v1.save(manifest, mf_filename)
                        else:
                            logger.debug(f"Not redownloading manifest v1 {mf_filename}")
                else:
                    if repo is None:
                        repo = await session.fetch_repo_v2(build.link, prod.id, build.id)
                        if repo is None:
                            continue
                        db.repository.save(repo, prod.id, build.id)
                    for depot in repo["depots"] + [repo["offlineDepot"]]:
                        mf_id = depot["manifest"]
                        if not db.manifest_v2.has(mf_id):
                            manifest = await session.fetch_manifest_v2(mf_id)
                            if manifest is None:
                                continue
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


def set_storedata(db, popularity_order, all_ids):
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
            update_prices(db, prod_id, {})


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

async def download_main(db, config):
    session = GogSession(db, config)
    qman = QueueManager()

    ids = db.ids.load()
    if ids is None:
        ids = []
    ids.sort(key=scramble_number)
    print(f"Starting downloader with {len(ids)} IDs")
    qman.schedule_products(ids)

    store_list_task = asyncio.create_task(
        store_list_worker(session, qman))
    product_tasks = [
        asyncio.create_task(product_worker(session, qman, db))
        for i in range(config.get("NUM_PRODUCT_TASKS", 1))
    ]
    prices_task = asyncio.create_task(
        prices_worker(session, qman, db))
    await wait_or_raise({store_list_task}, {*product_tasks, prices_task})
    qman.products_exhausted.set()
    await wait_or_raise({*product_tasks}, {prices_task})
    qman.prices_exhausted.set()
    await prices_task

    ids = list(qman.scheduled_products)
    db.ids.save(ids)

    logger.info("Setting popularities")
    popularity_order = store_list_task.result()
    set_storedata(db, popularity_order, ids)
    print(f"Requested {len(ids)} products")

    await session.close()
    await asyncio.sleep(0.250) # Wait for aiohttp to close connections

def main():
    config = flask.Config(".")
    config.from_envvar("GOGDB_CONFIG")
    db = storage.Storage(config["STORAGE_PATH"])

    logging.basicConfig()
    logger.setLevel(config.get("UPDATER_LOGLEVEL", logging.NOTSET))

    tasks = sys.argv[1:]
    if not tasks:
        print("Updater missing task argument: [all, download, index]")
        exit(1)
    if "all" in tasks:
        tasks = ["download", "index"]
    if "download" in tasks:
        asyncio.run(download_main(db, config))
    if "index" in tasks:
        index_main(db)

main()
