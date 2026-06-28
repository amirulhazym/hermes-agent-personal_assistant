from .provider import TrafilaturaWebSearchProvider

def register(ctx) -> None:
    ctx.register_web_search_provider(TrafilaturaWebSearchProvider())
