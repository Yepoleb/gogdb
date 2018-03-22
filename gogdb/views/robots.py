import os

import flask

from gogdb import app


@app.route("/robots.txt")
def robots():
    static_path = os.path.join(app.root_path, "static")
    return flask.send_from_directory(
        static_path, "robots.txt", mimetype="text/plain")
