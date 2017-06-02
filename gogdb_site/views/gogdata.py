from pyramid.view import view_config

import re
import requests
import json

GOGDATA_RE = re.compile(r"var gogData = (\{.*\})")

@view_config(route_name="gogdata", renderer="json")
def gogdata_view(request):
    slug = request.matchdict["slug"]
    resp = requests.get("https://www.gog.com/game/" + slug,
        cookies={"gog_lc": "US_USD_en"})
    gogdata_str = GOGDATA_RE.search(resp.text).group(1)
    gogdata = json.loads(gogdata_str)
    return gogdata
