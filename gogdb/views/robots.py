import os

import flask


def robots():
    static_path = os.path.join(flask.current_app.root_path, "static")
    return flask.send_from_directory(
        static_path, "robots.txt", mimetype="text/plain")
