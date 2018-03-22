import flask_assets

from gogdb import app
from gogdb.assets.rcssmin import RCSSMin


css_all = flask_assets.Bundle(
    "css/*.css",
    filters=[RCSSMin],
    output="css/gogdb.%(version)s.css")

fonts_all = flask_assets.Bundle(
    "fonts/*.css",
    filters=[RCSSMin],
    output="css/fonts.%(version)s.css")

js_prodinfo = flask_assets.Bundle(
    "js/moment.js",
    "js/Chart.js",
    "js/chartconfig.js",
    "js/tabs.js",
    filters="rjsmin",
    output="js/product.%(version)s.js")

assets_env = flask_assets.Environment(app)
assets_env.register("css-all", css_all)
assets_env.register("fonts-all", fonts_all)
assets_env.register("js-prodinfo", js_prodinfo)

assets_env.config["RCSSMIN_KEEP_BANG_COMMENTS"] = True
assets_env.config["RJSMIN_KEEP_BANG_COMMENTS"] = True
