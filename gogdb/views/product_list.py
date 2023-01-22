import secrets

import quart

import gogdb.core.model as model
from gogdb.views.pagination import calc_pageinfo
from gogdb.core.normalization import normalize_search, decompress_systems
from gogdb.application.datasources import get_indexdb_cursor


PRODUCTS_PER_PAGE = 20

_allowed_system_params = {'w', 'o', 'l'}
_script_nonce = secrets.token_urlsafe(16)
_csp_header = (
    "default-src 'self'; "
    "img-src 'self' images.gog-statics.com; "
    f"script-src 'self' 'nonce-{_script_nonce}';"
)


async def product_list():
    page = int(quart.request.args.get("page", "1"))
    hide_dlcs = quart.request.args.get("hide-dlcs", "") == "y"
    systems = {s for s in quart.request.args.getlist("systems") if s in _allowed_system_params}
    search = quart.request.args.get("search", "").strip()
    # Filter illegal characters and resulting empty strings
    search_words = list(filter(None, (normalize_search(word) for word in search.split())))

    cur = await get_indexdb_cursor()
    if len(search) == 10 and search.isdecimal():
        return quart.redirect(quart.url_for("product_info", prod_id=search), 303)

    filter_clauses = []
    order_clauses = ["sale_rank ASC"]

    if search_words:
        # Add a filter for each search word
        for word in search_words:
            # Should not be injectable because words are filtered
            filter_clauses.append("search_title LIKE '%{}%'".format(word))
        order_clauses.append("LENGTH(title) ASC")

    if hide_dlcs:
        filter_clauses.append("product_type != 'dlc'")

    if systems:
        filter_clauses.append(
            "(comp_systems LIKE '%"
            + "%' OR comp_systems LIKE '%".join(systems)
            + "%')"
        )

    filter_string = "WHERE " + " AND ".join(filter_clauses) if filter_clauses else ""
    order_string = "ORDER BY " + ", ".join(order_clauses) if order_clauses else ""

    await cur.execute("SELECT COUNT(*) FROM products {};".format(filter_string))
    num_products = (await cur.fetchone())[0]
    page_info = calc_pageinfo(page, num_products, PRODUCTS_PER_PAGE)

    await cur.execute(
        f"SELECT * FROM products {filter_string} {order_string} LIMIT ? OFFSET ?;",
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
    await cur.close()

    query_params = quart.request.args.to_dict(False)
    page_info["prev_link"] = quart.url_for(
        "product_list", **(query_params | {"page": page_info["page"] - 1}))
    page_info["next_link"] = quart.url_for(
        "product_list", **(query_params | {"page": page_info["page"] + 1}))

    filter_config = {
        "form_action": quart.url_for("product_list"),
        "value": {
            "search": search,
            "hide-dlcs": hide_dlcs,
            "systems": systems,
        }
    }

    response = await quart.make_response(await quart.render_template(
        "product_list.html",
        products=products,
        page_info=page_info,
        script_nonce=_script_nonce,
        filter_config=filter_config,
    ))
    response.headers["Content-Security-Policy"] = _csp_header
    return response
