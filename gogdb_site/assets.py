import webassets
from .filters.rcssmin import RCSSMin

css_all = webassets.Bundle(
    "css/*.css",
    filters=[RCSSMin],
    output="css/gogdb.%(version)s.css")

fonts_all = webassets.Bundle(
    "fonts/*.css",
    filters=["cssrewrite", RCSSMin],
    output="css/fonts.%(version)s.css")

js_prodinfo = webassets.Bundle(
    "js/moment.js",
    "js/Chart.js",
    "js/chartconfig.js",
    filters="rjsmin",
    output="js/product.%(version)s.js")

def includeme(config):
    config.add_webasset("css-all", css_all)
    config.add_webasset("fonts-all", fonts_all)
    config.add_webasset("js-prodinfo", js_prodinfo)
