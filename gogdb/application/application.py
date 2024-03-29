import quart

import gogdb.application.config as config
import gogdb.application.filters as filters
import gogdb.application.routes as routes
import gogdb.application.datasources as datasources


app = quart.Quart("gogdb", static_folder=None)
config.configure_app(app)
filters.add_filters(app)
routes.add_routes(app)
datasources.add_teardown(app)
