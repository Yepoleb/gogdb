import datetime
import itertools
import asyncio

from dataclasses import dataclass

import gogdb.core.model as model



NUM_SUMMARY = 10
FIRST_DATE = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

@dataclass
class ProductSummary:
    index_prod: model.StartpageProduct
    type: str
    added_on: datetime.datetime
    rank_trending: int
    rank_bestselling: int
    last_build: datetime.datetime
    on_sale: bool


async def startpage_worker(db, ids, worker_num):
    worker_results = []
    while ids:
        prod_id = ids.pop()
        prod = await db.product.load(prod_id)
        if prod is None:
            continue

        added_on = prod.added_on
        if added_on is None:
            added_on = FIRST_DATE
        rank_trending = prod.rank_trending
        if rank_trending is None:
            rank_trending = 100000  # some high number
        rank_bestselling = prod.rank_bestselling
        if rank_bestselling is None:
            rank_bestselling = 1000000

        last_build = FIRST_DATE
        changelog = await db.changelog.load(prod_id)
        if changelog is not None:
            for cl_entry in reversed(changelog):
                if cl_entry.category == "build" and cl_entry.action == "add":
                    last_build = cl_entry.timestamp
                    break

        on_sale = False
        discount = 0
        prices = await db.prices.load(prod_id)
        if prices is not None and prices["US"]["USD"]:
            cur_price = prices["US"]["USD"][-1]
            if cur_price.price_base is not None:
                discount = cur_price.discount

        if discount is None:
            discount = 0
        on_sale_sort_val = 0 if discount > 0 else 1  # on sale should sort first

        worker_results.append(ProductSummary(
            index_prod = model.StartpageProduct(
                id = prod.id,
                title = prod.title,
                image_logo = prod.image_logo,
                discount = discount
            ),
            type = prod.type,
            added_on = added_on,
            rank_trending = rank_trending,
            rank_bestselling = rank_bestselling,
            last_build = last_build,
            on_sale = on_sale_sort_val
        ))

    return worker_results

async def startpage_main(db):
    ids = await db.ids.load()
    print(f"Starting startpage generator with {len(ids)} IDs")
    worker_tasks = [
        asyncio.create_task(startpage_worker(db, ids, worker_num))
        for worker_num in range(8)
    ]
    worker_results = await asyncio.gather(*worker_tasks, return_exceptions=False)

    product_summary = list(itertools.chain.from_iterable(worker_results))

    games = [p for p in product_summary if p.type == "game"]
    list_added = sorted(games, key=lambda p: p.added_on, reverse=True)[:NUM_SUMMARY]
    list_trending = sorted(product_summary, key=lambda p: p.rank_trending)[:NUM_SUMMARY]
    list_builds = sorted(games, key=lambda p: p.last_build, reverse=True)[:NUM_SUMMARY]
    list_sale = sorted(games, key=lambda p: (p.on_sale, p.rank_bestselling))[:NUM_SUMMARY]
    startpage_obj = model.StartpageLists(
        added = [p.index_prod for p in list_added],
        trending = [p.index_prod for p in list_trending],
        builds = [p.index_prod for p in list_builds],
        sale = [p.index_prod for p in list_sale]
    )
    await db.startpage.save(startpage_obj)
