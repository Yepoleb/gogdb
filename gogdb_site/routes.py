from pyramid.path import AssetResolver

TIME_HOUR = 3600
TIME_WEEK = 604800

def includeme(config):
    config.add_route("product_list", "/products")
    config.add_route("product_info", "/product/{product}")
    config.add_route("gogdata", "/gogdata/{slug}")

    config.add_static_view("static", "gogdb_site:static/", cache_max_age=3600)
    config.add_static_view(
        "generated", "gogdb_site:generated/", cache_max_age=604800)

    assets_env = config.get_webassets_env()
    asset_resolv = AssetResolver()
    assets_env.append_path(
        asset_resolv.resolve("gogdb_site:static/").abspath(), "static")
