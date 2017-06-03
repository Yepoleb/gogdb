from pyramid.view import view_config


@view_config(route_name="index", renderer="index.html")
def index(request):
    return {}
