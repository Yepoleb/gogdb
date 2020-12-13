import flask


def index():
    return flask.render_template("index.html")
