import flask

from gogdb import app


@app.route("/legal")
def legal():
    return flask.render_template("legal.html")
