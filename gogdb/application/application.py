import flask

import gogdb.application.config as config
import gogdb.application.filters as filters
import gogdb.application.assets as assets
import gogdb.application.routes as routes


app = flask.Flask("gogdb")
config.configure_app(app)
filters.add_filters(app)
assets.add_assets(app)
routes.add_routes(app)
