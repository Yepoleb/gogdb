from pyramid.config import Configurator

from .filters import jinja as filters

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include("pyramid_jinja2")
    config.add_jinja2_renderer(".html")
    config.add_jinja2_search_path("gogdb_site:templates/", ".html")
    config.commit()
    jinja2_env = config.get_jinja2_environment(".html")
    jinja2_env.filters["yes_no"] = filters.format_yes_no
    jinja2_env.filters["os_icon"] = filters.os_icon
    jinja2_env.filters["os_icons"] = filters.os_icons
    jinja2_env.globals["iter_attr"] = filters.iter_attr
    jinja2_env.globals["comma_attr"] = filters.comma_attr

    config.include("pyramid_webassets")
    config.add_jinja2_extension(
        "webassets.ext.jinja2.AssetsExtension", ".html")
    assets_env = config.get_webassets_env()
    jinja2_env.assets_environment = assets_env

    config.include(".models")
    config.include(".routes")
    config.include(".assets")
    config.scan()
    return config.make_wsgi_app()
