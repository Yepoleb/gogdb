import copy

import flask
from sqlalchemy import orm
from arrow.arrow import Arrow

from gogdb import app, db, model


@app.route("/product/<int:prod_id>")
def product_info(prod_id):
    product = db.session.query(model.Product) \
        .filter_by(id=prod_id) \
        .options(
            orm.subqueryload("downloads") \
            .subqueryload("files")) \
        .one_or_none()

    if product is None:
        flask.abort(404)

    pricehistory = list(product.pricehistory)
    history_chart = {"labels": [], "values": [], "max": 0}
    if pricehistory:
        current_price = copy.copy(pricehistory[-1])
        current_price.arrow = Arrow.utcnow()
        pricehistory.append(current_price)
        last_price = None
        for entry in pricehistory:
            if entry.price_final is not None:
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(str(entry.price_final))
                history_chart["max"] = max(
                    history_chart["max"], entry.price_final)
            elif last_price is not None:
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(str(last_price))
                history_chart["labels"].append(entry.date.isoformat())
                history_chart["values"].append(None)
            last_price = entry.price_final
    history_chart["max"] = float(history_chart["max"])

    priceframes = []
    for start, end in zip(pricehistory[:-1], pricehistory[1:]):
        frame = {
            "start": start.arrow,
            "end": end.arrow,
            "discount": start.discount,
            "price_final": start.price_final,
            "price_base": start.price_base
        }
        priceframes.append(frame)

    return flask.render_template(
        "product_info.html",
        product=product,
        pricehistory=history_chart,
        priceframes=priceframes
    )
