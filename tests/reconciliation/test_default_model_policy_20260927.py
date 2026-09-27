from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[2]
CONFIG_TEMPLATE = REPO / "config/config.yaml.template"


def test_global_default_is_verified_codex_gpt6_luna():
    config = yaml.safe_load(CONFIG_TEMPLATE.read_text(encoding="utf-8"))
    model = config["model"]

    assert model["provider"] == "openai-codex"
    assert model["default"] == "gpt-6-luna"
    assert "base_url" not in model


def test_global_default_does_not_declare_unverified_gpt6_900k_alias():
    config = yaml.safe_load(CONFIG_TEMPLATE.read_text(encoding="utf-8"))
    model = config["model"]
    configured_models = model.get("models") or {}

    assert "gpt-6-luna-900k" not in configured_models
