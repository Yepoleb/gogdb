import copy

from pyramid.view import view_config
from sqlalchemy import orm
from arrow.arrow import Arrow

from .. import models



@view_config(route_name="product_info", renderer="product_info.html")
def product_info(request):
    prod_id = request.matchdict["product"]
    product = request.dbsession.query(models.Product).filter_by(id=prod_id).\
        options(orm.subqueryload("downloads").subqueryload("files")).one()

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

    return {"product": product, "pricehistory": pricehistory_dict,
        "priceframes": priceframes}
