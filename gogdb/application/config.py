import os


async def add_security_headers(response):
    if "Content-Security-Policy" not in response.headers:
        response.headers["Content-Security-Policy"] = \
            "default-src 'self'; img-src 'self' images.gog.com;"
    return response

def configure_app(app):
    app.config["JINJA_LSTRIP_BLOCKS"] = False
    app.config["JINJA_TRIM_BLOCKS"] = False

    app.config.from_envvar("GOGDB_CONFIG")

    app.jinja_env.lstrip_blocks = app.config["JINJA_LSTRIP_BLOCKS"]
    app.jinja_env.trim_blocks = app.config["JINJA_TRIM_BLOCKS"]

    app.after_request(add_security_headers)
