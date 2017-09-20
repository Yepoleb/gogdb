from pyramid.view import view_config
from pyramid.response import Response

ROBOTS_FILE = \
"""\
User-agent: *
Disallow: /gogdata/
Disallow: /legal
"""

@view_config(route_name="robots")
def robots_view(request):
    return Response(content_type="text/plain", body=ROBOTS_FILE)
