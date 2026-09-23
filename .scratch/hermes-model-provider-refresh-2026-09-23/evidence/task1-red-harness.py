from __future__ import annotations

from unittest.mock import patch

from hermes_cli.codex_models import DEFAULT_CODEX_MODELS, get_codex_model_ids
from hermes_cli.model_normalize import normalize_model_for_provider
import hermes_cli.models as models_mod
from hermes_cli.models import provider_model_ids, validate_requested_model


def test_codex_offline_fallback_contains_live_verified_gpt6_without_unverified_900k():
    expected = {"gpt-6-astra", "gpt-6-sol", "gpt-6-luna"}
    assert expected.issubset(DEFAULT_CODEX_MODELS)

    offline = get_codex_model_ids(access_token=None)
    assert expected.issubset(offline)
    assert not any(
        model.startswith("gpt-6-") and model.endswith("-900k")
        for model in offline
    )


def test_deepseek_legacy_flash_ids_normalize_to_v41_canonical():
    for legacy in (
        "deepseek-chat",
        "deepseek-reasoner",
        "deepseek-v4-flash",
        "deepseek-v4-flash-vision-exp",
        "deepseek/deepseek-v4-flash",
    ):
        assert normalize_model_for_provider(legacy, "deepseek") == "deepseek-flash"

    assert normalize_model_for_provider("deepseek-flash", "deepseek") == "deepseek-flash"
    assert normalize_model_for_provider("deepseek-v4-pro", "deepseek") == "deepseek-v4-pro"


def test_deepseek_profile_uses_current_flash_and_effort_mapping():
    import model_tools  # noqa: F401
    import providers

    profile = providers.get_provider_profile("deepseek")
    assert profile is not None
    assert profile.default_aux_model == "deepseek-flash"
    assert profile.fallback_models == ("deepseek-flash", "deepseek-v4-pro")

    extra, top = profile.build_api_kwargs_extras(
        reasoning_config=None,
        model="deepseek-flash",
    )
    assert extra == {"thinking": {"type": "enabled"}}
    assert top == {}

    for requested, expected in (
        ("minimal", "low"),
        ("low", "low"),
        ("medium", "high"),
        ("high", "high"),
        ("xhigh", "high"),
        ("max", "max"),
        ("ultra", "max"),
    ):
        extra, top = profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": requested},
            model="deepseek-flash",
        )
        assert extra == {"thinking": {"type": "enabled"}}
        assert top == {"reasoning_effort": expected}


def test_opencode_zen_free_only_policy_has_no_selectable_external_chat_models(monkeypatch):
    monkeypatch.setattr(
        models_mod,
        "_merge_with_models_dev",
        lambda _provider, curated: list(curated),
    )
    monkeypatch.setattr(
        models_mod,
        "fetch_api_models",
        lambda *args, **kwargs: None,
    )

    with patch(
        "hermes_cli.auth.resolve_api_key_provider_credentials",
        return_value={"api_key": "", "base_url": "https://opencode.ai/zen/v1"},
    ):
        assert provider_model_ids("opencode-zen", force_refresh=True) == []

    for model in ("gpt-6-sol", "big-pickle", "mimo-v2.5-free", "jev-1.13-free"):
        result = validate_requested_model(
            model,
            "opencode-zen",
            api_key="test-key",
            base_url="https://opencode.ai/zen/v1",
        )
        assert result["accepted"] is False
        assert result["persist"] is False
        assert result["recognized"] is False
        assert "free-only" in (result["message"] or "").lower()
