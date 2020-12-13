import copy
import datetime
import itertools

import flask

import gogdb.core.model as model
from gogdb.application.datasources import get_storagedb, get_indexdb
from gogdb.core.normalization import decompress_systems


class MockProduct:
    image_logo = None
    sale_rank = 0
    title = "Unknown"
    type = "unknown"
    comp_systems = []

    def __init__(self, product_id):
        self.id = product_id


def product_info(prod_id):
    storagedb = get_storagedb()
    product = storagedb.product.load(prod_id)

    if product is None:
        flask.abort(404)

    pricehistory = storagedb.prices.load(prod_id)
    changelog = storagedb.changelog.load(prod_id)
    if pricehistory:
        cur_history = pricehistory["US"]["USD"]
    else:
        cur_history = []

    history_chart = {"labels": [], "values": [], "max": 0}
    if cur_history:
        current_price = copy.copy(cur_history[-1])
        current_price.date = datetime.datetime.now(datetime.timezone.utc)
        cur_history.append(current_price)
        last_price = None
        for entry in cur_history:
            if entry.price_final is not None:
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(str(entry.price_final_decimal))
                history_chart["max"] = max(
                    history_chart["max"], entry.price_final_decimal)
            elif last_price is not None:
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(str(last_price))
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(None)
            last_price = entry.price_final_decimal
    history_chart["max"] = float(history_chart["max"])

    priceframes = []
    for start, end in zip(cur_history[:-1], cur_history[1:]):
        frame = {
            "start": start.date,
            "end": end.date,
            "discount": start.discount,
            "price_final": start.price_final_decimal,
            "price_base": start.price_base_decimal
        }
        priceframes.append(frame)

    # Prefetch referenced products
    referenced_ids = {
        "editions": [edition.id for edition in product.editions],
        "includes_games": product.includes_games,
        "is_included_in": product.is_included_in,
        "required_by": product.required_by,
        "requires": product.requires,
        "dlcs": product.dlcs
    }
    all_references = set(itertools.chain.from_iterable(referenced_ids.values()))
    all_products = {}
    if all_references:
        cur = get_indexdb().cursor()
        placeholders = ", ".join(itertools.repeat("?", len(all_references)))
        cur.execute(
            "SELECT * FROM products WHERE product_id IN ({})".format(placeholders),
            tuple(all_references)
        )
        for prod_res in cur:
            idx_prod = model.IndexProduct(
                id = prod_res["product_id"],
                title = prod_res["title"],
                image_logo = prod_res["image_logo"],
                type = prod_res["product_type"],
                comp_systems = decompress_systems(prod_res["comp_systems"]),
                sale_rank = prod_res["sale_rank"],
                search_title = prod_res["search_title"]
            )
            all_products[idx_prod.id] = idx_prod
    referenced_products = {
        key: [all_products.get(ref_id, MockProduct(ref_id)) for ref_id in ref_ids]
        for key, ref_ids in referenced_ids.items()
    }

    return flask.render_template(
        "product_info.html",
        product=product,
        referenced_products=referenced_products,
        pricehistory=history_chart,
        priceframes=priceframes,
        changelog=changelog
    )
