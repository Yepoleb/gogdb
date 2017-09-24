import math
import string
import datetime

from pyramid.view import view_config
import sqlalchemy
from sqlalchemy import orm

from .. import models

PRODUCTS_PER_PAGE = 20

ALLOWED_CHARS = set(string.ascii_lowercase + string.digits + ' ')



def normalize_search(title):
    return "".join(filter(lambda c: c in ALLOWED_CHARS, title.lower()))

def clean_dict(d):
    return dict((k, v) for k, v in d.items() if v)

def calc_pageinfo(page, num_products):
    num_pages = int(math.ceil(num_products / PRODUCTS_PER_PAGE))
    page = min(max(page, 1), num_pages)
    offset = (page - 1) * PRODUCTS_PER_PAGE
    page_info = {
        "is_first": page == 1,
        "is_last": page == num_pages,
        "page": page,
        "num_pages": num_pages,
        "from": offset,
        "to": offset + PRODUCTS_PER_PAGE,
        "prev_link": "", # Filled in later
        "next_link": ""
    }
    return page_info

@view_config(route_name="product_list", renderer="product_list.html")
def product_list(request):
    page = int(request.params.get("page", "1"))
    search = request.params.get("search", "").strip()
    search_norm = normalize_search(search)
    search_words = search_norm.split()

    if not search_words:
        # Predict page count
        num_products = request.dbsession.query(
            sqlalchemy.func.count(models.Product.id)
            ).one()[0]
        page_info = calc_pageinfo(page, num_products)

        products = request.dbsession.query(models.Product) \
            .order_by(
                (models.Product.release_date >
                sqlalchemy.sql.functions.now()).asc()) \
            .order_by(
                sqlalchemy.sql.functions.coalesce(
                    models.Product.release_date,
                    datetime.date(1, 1, 1)).desc()) \
            .offset(page_info["from"]).limit(PRODUCTS_PER_PAGE)

    else:
        query = request.dbsession.query(models.Product) \
            .order_by(
                sqlalchemy.sql.functions.char_length(models.Product.title))

        # Add a filter for each search word
        for word in search_words:
            query = query.filter(models.Product.title_norm \
                .like("%{}%".format(word)))

        products = query.all()
        page_info = calc_pageinfo(page, len(products))
        products = products[page_info["from"]:page_info["to"]]

    page_info["prev_link"] = request.route_path("product_list",
        _query=clean_dict({"page": page_info["page"] - 1, "search": search}))
    page_info["next_link"] = request.route_path("product_list",
        _query=clean_dict({"page": page_info["page"] + 1, "search": search}))

    return {"products": products, "page_info": page_info, "search": search}
