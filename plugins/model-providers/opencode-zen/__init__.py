"""OpenCode provider profiles (Zen + Go).

Routing rules per OpenCode official documentation (2026-09-04):
  - OpenCode Zen:
      * Claude → anthropic_messages (/v1/messages)
      * GPT-5 / Codex / Grok / Muse Spark → codex_responses (/v1/responses)
      * MiniMax (minimax-m3, minimax-m2.7, minimax-m2.5), Gemini, GLM, Kimi,
        DeepSeek, MiMo, Nemotron, Laguna, Big Pickle → chat_completions (/v1/chat/completions)
  - OpenCode Go:
      * MiniMax → anthropic_messages (/v1/messages)
      * Qwen → anthropic_messages (/v1/messages)
      * GPT-5.6-Luna, Grok, Muse Spark → codex_responses (/v1/responses)
      * GLM, Kimi, DeepSeek, MiMo, Hy3/4, Omen → chat_completions (/v1/chat/completions)
"""

from __future__ import annotations

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


def _flat_model_name(model: str | None) -> str:
    """Return the bare OpenCode model ID, tolerating aggregator prefixes."""
    return (model or "").strip().rsplit("/", 1)[-1].lower()


def _is_kimi_k2_model(model: str | None) -> bool:
    return _flat_model_name(model).startswith("kimi-k2")


def _is_deepseek_thinking_model(model: str | None) -> bool:
    m = _flat_model_name(model)
    if m.startswith("deepseek-v") and not m.startswith("deepseek-v3"):
        return True
    return False


# Official 7 OpenCode Zen free models (2026-09-04 docs)
OPENCODE_ZEN_OFFICIAL_FREE: tuple[str, ...] = (
    "muse-spark-1.3-contributor-free",
    "muse-spark-1.2-contributor-free",
    "nemotron-3.5-lightning-free",
    "big-pickle",
    "mimo-v2.5-free",
    "ling-3.0-flash-fin-free",
    "nemotron-3-ultra-free",
)

# Secondary / undocumented live-catalog free candidate (keyed only, not official/keyless)
OPENCODE_ZEN_SECONDARY_FREE: tuple[str, ...] = (
    "laguna-s-2.1-free",
)

# Explicitly delisted/deprecated models to filter out from Zen picker
OPENCODE_ZEN_DEPRECATED_OR_DELISTED: frozenset[str] = frozenset({
    # Delisted free models
    "deepseek-v4-flash-free",
    "x-preview-f-free",
    "hy3-free",
    # Official deprecated models (Zen docs)
    "gpt-5.2-codex",
    "gpt-5.1-codex",
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
    "gpt-5-codex",
    "claude-opus-4.1",
    "claude-sonnet-4",
    "claude-haiku-3.5",
    "gemini-3-pro",
    "minimax-m2.5",
    "minimax-m2.1",
    "glm-5",
    "glm-4.7",
    "glm-4.6",
    "kimi-k2.5",
    "kimi-k2-thinking",
    "kimi-k2",
})

# Official 27 models offered by OpenCode Go (2026-09-04 docs)
OPENCODE_GO_OFFICIAL_MODELS: tuple[str, ...] = (
    "grok-4.6",
    "glm-5.3-flash",
    "glm-5.3",
    "glm-5.2",
    "glm-5.1",
    "gpt-5.6-luna",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "longcat-2.0",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "minimax-m3",
    "minimax-m2.7",
    "muse-spark-1.3-contributor",
    "muse-spark-1.2-contributor",
    "qwen3.8-max",
    "qwen3.8-flash",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp",
    "hy4-preview",
    "hy3",
    "omen-alpha",
)


class OpenCodeZenProfile(ProviderProfile):
    """OpenCode Zen - dynamic model catalog with Free-first ordering and deprecation filtering."""

    def fetch_models(self, **kwargs: Any) -> list[str] | None:
        raw = super().fetch_models(**kwargs)
        if not raw:
            # Fallback to official free + secondary free + curated paid
            return list(OPENCODE_ZEN_OFFICIAL_FREE + OPENCODE_ZEN_SECONDARY_FREE)

        # 1. Strip deprecated / delisted models
        filtered = [
            m for m in raw
            if _flat_model_name(m) not in OPENCODE_ZEN_DEPRECATED_OR_DELISTED
        ]

        # 2. Extract official free models in explicit priority order
        official_free = [m for m in OPENCODE_ZEN_OFFICIAL_FREE if m in filtered]

        # 3. Extract secondary free models (e.g. laguna-s-2.1-free)
        secondary_free = [m for m in OPENCODE_ZEN_SECONDARY_FREE if m in filtered]

        # 4. Any unexpected free models returned by live catalog
        other_free = [
            m for m in filtered
            if (m.endswith("-free") or m == "big-pickle")
            and m not in official_free
            and m not in secondary_free
        ]

        # 5. Extract paid models
        free_all_set = set(official_free + secondary_free + other_free)
        paid = [m for m in filtered if m not in free_all_set]

        # Final ordered list: Official Free (Page 1) -> Secondary Free -> Paid
        return official_free + secondary_free + other_free + paid


class OpenCodeGoProfile(ProviderProfile):
    """OpenCode Go - model-specific reasoning controls and 27-model catalog alignment."""

    _MODEL_MAX_TOKENS: dict[str, int] = {
        "mimo-v2.5-pro": 131072,
    }

    def fetch_models(self, **kwargs: Any) -> list[str] | None:
        raw = super().fetch_models(**kwargs)
        if not raw:
            return list(OPENCODE_GO_OFFICIAL_MODELS)
        
        # Align strictly with current official 27 models; do not expose raw stale extras
        raw_set = set(raw)
        aligned = [m for m in OPENCODE_GO_OFFICIAL_MODELS if m in raw_set]
        # In case some official models weren't in raw (or raw failed partially), include remaining official
        for m in OPENCODE_GO_OFFICIAL_MODELS:
            if m not in aligned:
                aligned.append(m)
        return aligned

    def get_max_tokens(self, model: str | None) -> int | None:
        cap = self._MODEL_MAX_TOKENS.get(_flat_model_name(model))
        if cap is not None:
            return cap
        return self.default_max_tokens

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None, **context
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        if _is_kimi_k2_model(model):
            if not isinstance(reasoning_config, dict):
                return extra_body, top_level

            enabled = reasoning_config.get("enabled") is not False
            if not enabled:
                extra_body["thinking"] = {"type": "disabled"}
                return extra_body, top_level

            effort = (reasoning_config.get("effort") or "").strip().lower()
            if effort in {"xhigh", "max"}:
                top_level["reasoning_effort"] = "high"
            elif effort in {"low", "medium", "high"}:
                top_level["reasoning_effort"] = effort

            if "reasoning_effort" not in top_level:
                extra_body["thinking"] = {"type": "enabled"}
            return extra_body, top_level

        if not _is_deepseek_thinking_model(model):
            return extra_body, top_level

        enabled = True
        if isinstance(reasoning_config, dict) and reasoning_config.get("enabled") is False:
            enabled = False

        if not enabled:
            extra_body["thinking"] = {"type": "disabled"}
            return extra_body, top_level

        if isinstance(reasoning_config, dict):
            effort = (reasoning_config.get("effort") or "").strip().lower()
            if effort in {"xhigh", "max"}:
                top_level["reasoning_effort"] = "max"
            elif effort in {"low", "medium", "high"}:
                top_level["reasoning_effort"] = effort

        if "reasoning_effort" not in top_level:
            extra_body["thinking"] = {"type": "enabled"}

        return extra_body, top_level


opencode_zen = OpenCodeZenProfile(
    name="opencode-zen",
    aliases=("opencode", "opencode_zen", "zen"),
    env_vars=("OPENCODE_ZEN_API_KEY",),
    base_url="https://opencode.ai/zen/v1",
    default_aux_model="gemini-3-flash",
)

opencode_go = OpenCodeGoProfile(
    name="opencode-go",
    aliases=("opencode_go", "go", "opencode-go-sub"),
    env_vars=("OPENCODE_GO_API_KEY",),
    base_url="https://opencode.ai/zen/go/v1",
    default_aux_model="glm-5.3",
)

register_provider(opencode_zen)
register_provider(opencode_go)
