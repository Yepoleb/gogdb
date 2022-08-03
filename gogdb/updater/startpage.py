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


class StartpageProcessor:
    wants = {"product", "changelog", "prices"}

    def __init__(self, db):
        self.summaries = []
        self.db = db

    async def prepare(self, num_ids):
        pass

    async def process(self, data):
        prod = data.product
        if prod is None:
            return

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
        changelog = data.changelog
        if changelog is not None:
            for cl_entry in reversed(changelog):
                if cl_entry.category == "build" and cl_entry.action == "add":
                    last_build = cl_entry.timestamp
                    break

        on_sale = False
        discount = 0
        prices = data.prices
        if prices is not None and prices["US"]["USD"]:
            cur_price = prices["US"]["USD"][-1]
            if cur_price.price_base is not None:
                discount = cur_price.discount

        if discount is None:
            discount = 0
        on_sale_sort_val = 0 if discount > 0 else 1  # on sale should sort first

        self.summaries.append(ProductSummary(
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

    async def finish(self):
        games = [p for p in self.summaries if p.type == "game"]
        list_added = sorted(games, key=lambda p: p.added_on, reverse=True)[:NUM_SUMMARY]
        list_trending = sorted(self.summaries, key=lambda p: p.rank_trending)[:NUM_SUMMARY]
        list_builds = sorted(games, key=lambda p: p.last_build, reverse=True)[:NUM_SUMMARY]
        list_sale = sorted(games, key=lambda p: (p.on_sale, p.rank_bestselling))[:NUM_SUMMARY]
        startpage_obj = model.StartpageLists(
            added = [p.index_prod for p in list_added],
            trending = [p.index_prod for p in list_trending],
            builds = [p.index_prod for p in list_builds],
            sale = [p.index_prod for p in list_sale]
        )
        await self.db.startpage.save(startpage_obj)
