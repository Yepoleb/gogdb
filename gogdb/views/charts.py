import flask

from gogdb.application.datasources import get_storagedb


def charts(prod_id):
    storagedb = get_storagedb()

    charts_path = storagedb.path_charts()
    filename = f"{prod_id}.svg.gz"
    response = flask.send_from_directory(charts_path, filename, mimetype="image/svg+xml")
    response.headers["Content-Encoding"] = "gzip"
    return response
