import os

import flask

from gogdb import app


@app.route("/favicon.ico")
def favicon():
    static_path = os.path.join(app.root_path, "static")
    return flask.send_from_directory(
        static_path, "img/favicon.ico", mimetype="image/vnd.microsoft.icon")
