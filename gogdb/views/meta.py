import requests
import zlib
import json

import flask

from gogdb import app


@app.route("/meta/<meta_id>")
def meta(meta_id):
    url = "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
        meta_id[0:2], meta_id[2:4], meta_id)
    resp = requests.get(url)
    json_text = zlib.decompress(resp.content, 15).decode("utf-8")
    return flask.jsonify(json.loads(json_text))
