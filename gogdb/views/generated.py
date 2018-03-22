import flask

from gogdb import app


@app.route("/generated/<path:filename>")
def generated(filename):
    generated_path = app.config["ASSETS_DIRECTORY"]
    return flask.send_from_directory(generated_path, filename)
