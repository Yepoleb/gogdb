from pyramid.config import Configurator

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)

    config.include(".config")
    config.include(".models")
    config.include(".routes")
    config.include(".assets")
    config.scan()
    return config.make_wsgi_app()
