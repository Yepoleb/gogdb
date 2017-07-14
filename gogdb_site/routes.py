from pyramid.path import AssetResolver

TIME_HOUR = 3600
TIME_WEEK = 604800

def includeme(config):
    config.add_route("index", "/")
    config.add_route("product_list", "/products")
    config.add_route("product_info", "/product/{product}")
    config.add_route("gogdata", "/gogdata/{slug}")
    config.add_route("robots", "/robots.txt")

    config.add_static_view(
        "static", "gogdb_site:static/", cache_max_age=TIME_HOUR)
    config.add_static_view(
        "generated", "gogdb_site:generated/", cache_max_age=TIME_WEEK)
