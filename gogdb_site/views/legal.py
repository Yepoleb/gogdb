from pyramid.view import view_config


@view_config(route_name="legal", renderer="legal.html")
def legal(request):
    return {}
