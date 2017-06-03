from pyramid.path import AssetResolver

TIME_HOUR = 3600
TIME_WEEK = 604800

def includeme(config):
    config.add_route("product_list", "/products")
    config.add_route("product_info", "/product/{product}")
    config.add_route("gogdata", "/gogdata/{slug}")

    assets_env = config.get_webassets_env()
    asset_resolv = AssetResolver()
    config.add_static_view(
        "static", "gogdb_site:static/", cache_max_age=TIME_HOUR)
    assets_env.append_path(
        asset_resolv.resolve("gogdb_site:static/").abspath(), "static")
    config.add_static_view(
        "generated", assets_env.directory, cache_max_age=TIME_WEEK)
