import os

import flask


def favicon():
    static_path = os.path.join(flask.current_app.root_path, "static")
    return flask.send_from_directory(
        static_path, "img/favicon.ico", mimetype="image/vnd.microsoft.icon")
