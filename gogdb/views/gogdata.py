import re
import requests
import json

import flask

from gogdb import app

GOGDATA_RE = re.compile(r"var gogData = (\{.*\})")


@app.route("/gogdata/<slug>")
def gogdata(slug):
    resp = requests.get("https://www.gog.com/game/" + slug,
        cookies={"gog_lc": "US_USD_en"})
    gogdata_str = GOGDATA_RE.search(resp.text).group(1)
    gogdata_dict = json.loads(gogdata_str)
    return flask.jsonify(gogdata_dict)
