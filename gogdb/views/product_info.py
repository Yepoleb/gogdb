import copy

import flask
from sqlalchemy import orm
from arrow.arrow import Arrow

from gogdb import app, db, model


@app.route("/product_info/<int:prod_id>")
def product_info(prod_id):
    product = db.session.query(model.Product) \
        .filter_by(id=prod_id) \
        .options(
            orm.subqueryload("downloads") \
            .subqueryload("files")) \
        .one()

    pricehistory = list(product.pricehistory)
    current_price = copy.copy(pricehistory[-1])
    current_price.arrow = Arrow.utcnow()
    pricehistory.append(current_price)
    pricehistory_dict = [entry.as_dict() for entry in pricehistory]

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
        pricehistory=pricehistory_dict,
        priceframes=priceframes
    )
