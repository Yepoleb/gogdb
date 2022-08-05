import string
import datetime

import quart

import gogdb.core.model as model
from gogdb.views.pagination import calc_pageinfo
from gogdb.core.normalization import normalize_search, decompress_systems
from gogdb.application.datasources import get_indexdb_cursor


PRODUCTS_PER_PAGE = 20


async def product_list():
    page = int(quart.request.args.get("page", "1"))
    search = quart.request.args.get("search", "").strip()
    # Filter illegal characters and resulting empty strings
    search_words = list(filter(None, (normalize_search(word) for word in search.split())))

    cur = await get_indexdb_cursor()
    if len(search) == 10 and search.isdecimal():
        return quart.redirect(quart.url_for("product_info", prod_id=search), 303)

    elif search_words:
        query_filters = []
        # Add a filter for each search word
        for word in search_words:
            # Should not be injectable because words are filtered
            word_cond = "search_title LIKE '%{}%'".format(word)
            query_filters.append(word_cond)
        filter_string = "WHERE " + " AND ".join(query_filters)
        order_string = "sale_rank DESC, LENGTH(title) ASC"
    else:
        filter_string = ""
        order_string = "sale_rank DESC"

    await cur.execute("SELECT COUNT(*) FROM products {};".format(filter_string))
    num_products = (await cur.fetchone())[0]
    page_info = calc_pageinfo(page, num_products, PRODUCTS_PER_PAGE)

    await cur.execute(
        "SELECT * FROM products {} ORDER BY {} LIMIT ? OFFSET ?;".format(filter_string, order_string),
        (PRODUCTS_PER_PAGE, page_info["from"])
    )
    products = []
    async for prod_res in cur:
        idx_prod = model.IndexProduct(
            id = prod_res["product_id"],
            title = prod_res["title"],
            image_logo = prod_res["image_logo"],
            type = prod_res["product_type"],
            comp_systems = decompress_systems(prod_res["comp_systems"]),
            sale_rank = prod_res["sale_rank"],
            search_title = prod_res["search_title"]
        )
        products.append(idx_prod)

    if search:
        page_info["prev_link"] = quart.url_for(
            "product_list", page=page_info["page"] - 1, search=search)
        page_info["next_link"] = quart.url_for(
            "product_list", page=page_info["page"] + 1, search=search)
    else:
        page_info["prev_link"] = quart.url_for(
            "product_list", page=page_info["page"] - 1)
        page_info["next_link"] = quart.url_for(
            "product_list", page=page_info["page"] + 1)

    return await quart.render_template(
        "product_list.html",
        products=products,
        page_info=page_info,
        search=search
    )
