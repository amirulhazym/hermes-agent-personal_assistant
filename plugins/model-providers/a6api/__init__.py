"""A6API provider profile — OpenAI-compatible routing proxy/gateway.

A6API (a6api.com) is a model aggregator/router similar to OpenRouter.
OpenAI-compatible API, multi-vendor auto-routing.
Base URL: https://a6api.com/v1
"""

from providers import register_provider
from providers.base import ProviderProfile

a6api = ProviderProfile(
    name="a6api",
    aliases=("a6api-gateway",),
    display_name="A6API",
    description="A6API model gateway — multi-vendor routing proxy",
    signup_url="https://a6api.com",
    env_vars=("A6API_API_KEY",),
    base_url="https://a6api.com/v1",
    auth_type="api_key",
    default_aux_model="gpt-5.4-mini",
    fallback_models=(
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "claude-sonnet-5",
        "claude-opus-4-8",
        "grok-4.5",
    ),
)

register_provider(a6api)
