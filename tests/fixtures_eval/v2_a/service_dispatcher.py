# Service Dispatcher
from .config_resolver import resolve_route

def dispatch_request(req):
    # Apparent error looks like routing failure
    route = resolve_route(req)
    return route
