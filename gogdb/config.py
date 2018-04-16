import os

from gogdb import app


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["JINJA_LSTRIP_BLOCKS"] = False
app.config["JINJA_TRIM_BLOCKS"] = False

app.config["ASSETS_DIRECTORY"] = os.path.join(app.root_path, "generated")
app.config["ASSETS_URL"] = "/generated"
app.config["ASSETS_DEBUG"] = False
app.config["ASSETS_AUTO_BUILD"] = False
app.config["ASSETS_URL_EXPIRE"] = False
app.config["ASSETS_VERSIONS"] = "hash"
app.config["ASSETS_MANIFEST"] = "file:" + os.path.join(app.root_path, "generated", "webassets-manifest")
app.config["ASSETS_CACHE"] = False
app.config["ASSETS_LOAD_PATH"] = [os.path.join(app.root_path, "static")]

app.config.from_envvar("GOGDB_CONFIG")

app.jinja_env.lstrip_blocks = app.config["JINJA_LSTRIP_BLOCKS"]
app.jinja_env.trim_blocks = app.config["JINJA_TRIM_BLOCKS"]

if app.debug:
    try:
        import flask_debugtoolbar
        app.config["SECRET_KEY"] = os.urandom(24)
        toolbar = flask_debugtoolbar.DebugToolbarExtension(app)
    except ImportError:
        pass
