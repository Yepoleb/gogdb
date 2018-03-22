import string
import datetime

import flask
import sqlalchemy
from sqlalchemy import orm

from gogdb import app, db, model
from gogdb.views.pagination import calc_pageinfo


PRODUCTS_PER_PAGE = 20

ALLOWED_CHARS = set(string.ascii_lowercase + string.digits + ' ')



def normalize_search(title):
    return "".join(filter(lambda c: c in ALLOWED_CHARS, title.lower()))


@app.route("/product_list")
def product_list():
    page = int(flask.request.args.get("page", "1"))
    search = flask.request.args.get("search", "").strip()
    search_norm = normalize_search(search)
    search_words = search_norm.split()

    if not search_words:
        # Predict page count
        num_products = db.session.query(
            sqlalchemy.func.count(model.Product.id)
            ).one()[0]
        page_info = calc_pageinfo(page, num_products, PRODUCTS_PER_PAGE)

        products = db.session.query(model.Product) \
            .order_by(
                (model.Product.release_date >
                sqlalchemy.sql.functions.now()).asc()) \
            .order_by(
                sqlalchemy.sql.functions.coalesce(
                    model.Product.release_date,
                    datetime.date(1, 1, 1)).desc()) \
            .offset(page_info["from"]).limit(PRODUCTS_PER_PAGE)

    else:
        query = db.session.query(model.Product) \
            .order_by(
                sqlalchemy.sql.functions.char_length(model.Product.title))

        # Add a filter for each search word
        for word in search_words:
            query = query.filter(model.Product.title_norm \
                .like("%{}%".format(word)))

        products = query.all()
        page_info = calc_pageinfo(page, len(products), PRODUCTS_PER_PAGE)
        products = products[page_info["from"]:page_info["to"]]

    if search:
        page_info["prev_link"] = flask.url_for(
            "product_list", page=page_info["page"] - 1, search=search)
        page_info["next_link"] = flask.url_for(
            "product_list", page=page_info["page"] + 1, search=search)
    else:
        page_info["prev_link"] = flask.url_for(
            "product_list", page=page_info["page"] - 1)
        page_info["next_link"] = flask.url_for(
            "product_list", page=page_info["page"] + 1)

    return flask.render_template(
        "product_list.html",
        products=products,
        page_info=page_info,
        search=search
    )
