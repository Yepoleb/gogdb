import flask


def generated(filename):
    generated_path = flask.current_app.config["ASSETS_DIRECTORY"]
    return flask.send_from_directory(generated_path, filename)
