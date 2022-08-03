#!/usr/bin/python3
import asyncio
import logging
import datetime
import copy
import sys
import decimal

import flask

import gogdb.core.model as model
import gogdb.core.storage as storage
from gogdb.core.changelogger import Changelogger
from gogdb.updater.gogsession import GogSession
import gogdb.updater.dataextractors as dataextractors
from gogdb.updater.indexdb import index_main
from gogdb.updater.startpage import startpage_main


logger = logging.getLogger("UpdateDB")

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def scramble_number(value):
    return (value * 16205650284070698839) & 0xFFFFFFFF

class QueueExhausted(Exception):
    """Signals when a queue is empty and will no longer receive new elements"""
    pass

class QueueManager:
    def __init__(self):
        self.products_queue = asyncio.Queue()
        self.scheduled_products = set()
        # No more products may get added after this event is set
        self.products_exhausted = asyncio.Event()

    def schedule_product(self, prod_id):
        assert type(prod_id) is int
        if prod_id not in self.scheduled_products:
            self.scheduled_products.add(prod_id)
            self.products_queue.put_nowait(prod_id)

    def schedule_products(self, prod_ids):
        for prod_id in prod_ids:
            self.schedule_product(prod_id)

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

    def products_done(self):
        self.products_queue.task_done()


@model.defaultdataclass
class CatalogEntry:
    id: int
    price_base: decimal.Decimal
    price_final: decimal.Decimal
    rating: int
    state: str
    position: int  # This will be filled out by default
    pos_bestselling: int = 0 # This is only set after manually merging both results
    pos_trending: int = 0 # See above

async def get_catalog(session, params):
    current_page = 1
    total_pages = 1
    position = 0
    collected_products = []
    while current_page <= total_pages:
        page = await session.fetch_catalog(params, current_page)
        logger.info("Downloaded store page %s", current_page)
        total_pages = page["pages"]
        for cat_prod in page["products"]:
            cat_entry = CatalogEntry()
            cat_entry.id = int(cat_prod["id"])
            if cat_prod["price"] is not None:
                cat_entry.price_base = decimal.Decimal(cat_prod["price"]["baseMoney"]["amount"])
                cat_entry.price_final = decimal.Decimal(cat_prod["price"]["finalMoney"]["amount"])
            cat_entry.rating = cat_prod["reviewsRating"]
            cat_entry.state = cat_prod["productState"]
            cat_entry.position = position
            position += 1
            collected_products.append(cat_entry)
        current_page += 1
    return collected_products

async def catalog_worker(session, qman, db):
    default_params = {
        "order": "asc:title",
        "productType": "in:game,pack,dlc,extras",
        "countryCode": "US",
        "locale": "en-US",
        "currencyCode": "USD"
    }
    bestselling_params = default_params.copy()
    bestselling_params["order"] = "desc:bestselling"
    trending_params = default_params.copy()
    trending_params["order"] = "desc:trending"

    # Do a first pass sorted by title because bestselling moves around too much
    title_res = await get_catalog(session, default_params)
    catalog_ids = [cat_entry.id for cat_entry in title_res]
    qman.schedule_products(catalog_ids)

    bestselling_res = await get_catalog(session, bestselling_params)
    trending_res = await get_catalog(session, trending_params)
    bestselling_by_id = {cat_entry.id: cat_entry for cat_entry in bestselling_res}
    trending_by_id = {cat_entry.id: cat_entry for cat_entry in trending_res}
    merged_res = title_res
    for cat_entry in merged_res:
        bestselling_entry = bestselling_by_id.get(cat_entry.id)
        if bestselling_entry:
            cat_entry.pos_bestselling = bestselling_entry.position
        trending_entry = trending_by_id.get(cat_entry.id)
        if trending_entry:
            cat_entry.pos_trending = trending_entry.position

    now = datetime.datetime.now(datetime.timezone.utc)
    all_ids = qman.scheduled_products.copy()
    title_by_id = {cat_entry.id: cat_entry for cat_entry in title_res}
    for prod_id in all_ids:
        # Work on the bestselling entries because that is already dictionary indexed
        cat_entry = title_by_id.get(prod_id)
        if cat_entry is not None:
            await update_price(
                db,
                prod_id = prod_id,
                country = "US",
                currency = "USD",
                price_base = cat_entry.price_base,
                price_final = cat_entry.price_final,
                now = now
            )
        else:
            await update_price(
                db,
                prod_id = prod_id,
                country = "US",
                currency = "USD",
                price_base = None,
                price_final = None,
                now = now
            )
    return merged_res

async def update_price(db, prod_id, country, currency, price_base, price_final, now):
    price_log = await db.prices.load(prod_id)
    if price_log is None:
        price_log = {"US": {"USD": []}}
    currency_log = price_log["US"]["USD"]

    record = model.PriceRecord(
        currency = currency,
        date = now
    )
    record.price_base_decimal = price_base
    record.price_final_decimal = price_final

    if currency_log:
        last_price = currency_log[-1]
        # Rollback means the last not-for-sale entry is invalid because the old price
        # came back within a short time
        is_rollback = (
            len(currency_log) >= 2
            and record.same_price(currency_log[-2])
            and last_price.price_base is None
            and (record.date - last_price.date) < datetime.timedelta(hours=4)
        )
        if is_rollback:
            # Remove the last not-for-sale entry
            logger.warning(f"Price rollback for {prod_id}")
            currency_log.pop()
        elif not record.same_price(last_price):
            currency_log.append(record)
    elif record.price_base is not None:
        currency_log.append(record)

    # Only save if it has entries
    if price_log["US"]["USD"]:
        await db.prices.save(price_log, prod_id)


async def product_worker(session, qman, db, worker_number):
    while True:
        try:
            prod_id = await qman.get_from_products()
        except QueueExhausted:
            logger.debug("Received queue exhausted for products")
            break
        logger.info(f"Worker {worker_number} Downloading {prod_id}")

        timestamp = datetime.datetime.now(datetime.timezone.utc)
        prod = await db.product.load(prod_id)
        if prod is None:
            prod = model.Product()
            prod.added_on = timestamp
            old_prod = None
        else:
            old_prod = copy.deepcopy(prod)

        changelog = await db.changelog.load(prod_id)
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
                repo = await db.repository.load(prod.id, build.id)
                if build.generation == 1:
                    if repo is None:
                        repo = await session.fetch_repo_v1(build.link, prod.id, build.id)
                        if repo is None:
                            continue
                        await db.repository.save(repo, prod.id, build.id)
                    for depot in repo["product"]["depots"]:
                        if "manifest" not in depot:
                            continue
                        mf_id = depot["manifest"].split(".")[0]
                        mf_url = build.link.rsplit("/", 1)[0] + "/" + depot["manifest"]
                        if not await db.manifest_v1.has(mf_id):
                            manifest = await session.fetch_manifest_v1(mf_id, mf_url)
                            if manifest is None:
                                continue
                            await db.manifest_v1.save(manifest, mf_id)
                        else:
                            logger.debug(f"Not redownloading manifest v1 {mf_id}")
                else:
                    if repo is None:
                        repo = await session.fetch_repo_v2(build.link, prod.id, build.id)
                        if repo is None:
                            continue
                        await db.repository.save(repo, prod.id, build.id)
                    for depot in repo["depots"] + [repo["offlineDepot"]]:
                        mf_id = depot["manifest"]
                        if not await db.manifest_v2.has(mf_id):
                            manifest = await session.fetch_manifest_v2(mf_id)
                            if manifest is None:
                                continue
                            await db.manifest_v2.save(manifest, mf_id)
                        else:
                            logger.debug(f"Not redownloading manifest v2 {mf_id}")

            prod.last_updated = timestamp

            if old_prod:
                prod_changelogger.property("title")
                prod_changelogger.property("comp_systems")
                # deprecated, needs to be replaced with store_state
                #prod_changelogger.property("is_pre_order")
                # Disabled because it can't be detected reliably
                #prod_changelogger.property("changelog")
                prod_changelogger.downloads("bonus")
                prod_changelogger.downloads("installer")
                prod_changelogger.downloads("langpack")
                prod_changelogger.downloads("patch")
                prod_changelogger.builds()


        if prod.has_content():
            if old_prod:
                # Disabled because it can't be detected reliably
                #prod_changelogger.property("access")
                pass
            else:
                prod_changelogger.prod_added()
        changelog += prod_changelogger.entries

        if prod.has_content():
            await db.product.save(prod, prod.id)

        if len(changelog) != old_changelog_len:
            await db.changelog.save(changelog, prod.id)

        qman.products_queue.task_done()
    logger.info(f"Worker {worker_number} done")


async def set_storedata(db, catalog_res, all_ids):
    num_entries = len(catalog_res)
    catalog_by_id = {cat_entry.id: cat_entry for cat_entry in catalog_res}
    for prod_id in all_ids:
        prod = await db.product.load(prod_id)
        if not prod:
            continue
        cat_entry = catalog_by_id.get(prod_id)
        if cat_entry:
            prod.user_rating = cat_entry.rating
            prod.store_state = cat_entry.state
            prod.rank_bestselling = cat_entry.pos_bestselling
            prod.rank_trending = cat_entry.pos_trending
        else:
            prod.user_rating = None
            prod.store_state = None
            prod.rank_bestselling = None
            prod.rank_trending = None
        await db.product.save(prod, prod_id)


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
    await session.load_token()
    qman = QueueManager()

    ids = await db.ids.load()
    if ids is None:
        ids = []
    ids.sort(key=scramble_number)
    eprint(f"Starting downloader with {len(ids)} IDs")
    qman.schedule_products(ids)

    catalog_task = asyncio.create_task(catalog_worker(session, qman, db))
    num_product_tasks = config.get("NUM_PRODUCT_TASKS", 1)
    logger.info(f"Creating {num_product_tasks} product workers")
    product_tasks = [
        asyncio.create_task(product_worker(session, qman, db, i))
        for i in range(num_product_tasks)
    ]
    await wait_or_raise({catalog_task}, {*product_tasks})
    qman.products_exhausted.set()
    await asyncio.gather(*product_tasks, return_exceptions=False)

    ids = list(qman.scheduled_products)
    await db.ids.save(ids)

    logger.info("Setting catalog data")
    catalog_results = catalog_task.result()
    await set_storedata(db, catalog_results, ids)
    eprint(f"Requested {len(ids)} products")

    await session.close()
    await asyncio.sleep(0.250) # Wait for aiohttp to close connections

def main():
    config = flask.Config(".")
    config.from_envvar("GOGDB_CONFIG")
    db = storage.Storage(config["STORAGE_PATH"])

    logging.basicConfig()
    logger.setLevel(config.get("UPDATER_LOGLEVEL", logging.NOTSET))
    logging.getLogger("UpdateDB.session").setLevel(config.get("SESSION_LOGLEVEL", logging.NOTSET))

    tasks = sys.argv[1:]
    if not tasks:
        eprint("Updater missing task argument: [all, download, index, startpage]")
        exit(1)
    if "all" in tasks:
        tasks = ["download", "index", "startpage"]
    if "download" in tasks:
        asyncio.run(download_main(db, config))
    if "index" in tasks:
        asyncio.run(index_main(db))
    if "startpage" in tasks:
        asyncio.run(startpage_main(db))

main()
