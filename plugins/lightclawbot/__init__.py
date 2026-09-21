"""
lightclawbot — LightClaw platform plugin for Hermes Agent.

Registers the LightClaw adapter via the Hermes plugin discovery system.
No source-code modifications to lighthouse-hermes are required — the adapter
is discovered automatically when this package is placed under
``~/.hermes/plugins/lightclawbot/`` or installed via pip (entry_points).
"""

import os
import threading


_adapter_instance = None
_adapter_instance_lock = threading.Lock()


def _get_version() -> str:
    """Return package version from importlib.metadata, with fallback."""
    try:
        from importlib.metadata import version

        return version("lightclawbot")
    except Exception:
        return "0.0.0"


__version__ = _get_version()


def _load_platform_hint() -> str:
    """Return the LightClaw-specific LLM capability hint.

    Only contents that are *unique* to LightClaw belong here.  The generic
    ``MEDIA:/absolute/path/to/file`` protocol, supported extensions and
    text post-processing are owned by the framework
    (``BasePlatformAdapter.extract_media`` + ``PLATFORM_HINTS`` in
    ``agent/prompt_builder.py``) and are intentionally NOT re-stated here.
    """
    return (
        "You are on LightClaw, a WebSocket-based messaging platform. "
        "Markdown formatting is supported (code blocks, bold, italic, tables).\n\n"
        "FILE DELIVERY (MANDATORY — READ CAREFULLY):\n"
        "After ANY tool creates or writes a file, your reply MUST contain a "
        "MEDIA: tag for that file — one tag per file, each on its own line.\n"
        "The ONLY correct format is exactly:\n"
        "MEDIA:<absolute path>\n\n"
        "Correct examples:\n"
        "  MEDIA:/home/ubuntu/报告.md\n"
        "  MEDIA:/home/ubuntu/数据分析结果.xlsx\n\n"
        "WRONG — never do any of these:\n"
        "  [报告.md](/home/ubuntu/报告.md)        ← markdown link is WRONG\n"
        "  [下载文件]()                            ← empty markdown link is WRONG\n"
        "  MEDIA:[报告.md](...)                    ← MEDIA must be followed by a raw path only\n"
        "  localfile:///home/ubuntu/报告.md        ← URL schemes are WRONG\n"
        "  file:///home/ubuntu/报告.md             ← URL schemes are WRONG\n\n"
        "Rules:\n"
        "1. Use the literal prefix 'MEDIA:' followed immediately by the raw "
        "absolute path. No brackets, no parentheses, no markdown, no quotes.\n"
        "2. The path must be the FULL absolute path returned by the tool, "
        "even if it contains Chinese characters or spaces. Copy it verbatim.\n"
        "3. Emit the MEDIA: line even if you already described the file in prose.\n"
        "4. One MEDIA: line per file when multiple files were written.\n"
        "The framework converts each MEDIA: line into a download link for the "
        "user; without it the user gets NO download link.\n\n"
        "For cron jobs / reminders / scheduled tasks, always target the user "
        "who is talking to you right now: set "
        "deliver='lightclawbot:<chat_id>' (the current user's chat_id) so the "
        "result is delivered back to that same user. If you cannot determine "
        "the chat_id, use deliver='origin' — the framework will route the "
        "result to whoever created the task. Never omit deliver (results would "
        "be saved locally and the user would never see them)."
    )


def _validate_config(config) -> bool:
    """Check whether the platform config has enough info to connect.
    多用户隔离格式 LIGHTCLAW_API_KEY_${UIN}。
    """
    extra = getattr(config, "extra", {}) or {}
    if extra.get("api_keys"):
        return True
    # 检查多用户格式
    for key in os.environ:
        if key.startswith("LIGHTCLAW_API_KEY_"):
            if os.environ[key].strip():
                return True
    return False


def _is_connected(config) -> bool:
    """Check whether the platform is sufficiently configured (for status display).

    Hermes gateway 在启动时会用一个空的 ``PlatformConfig(enabled=True)`` 作为
    *probe_cfg* 来调用这个函数（见 ``gateway/config.py`` 的 plugin-platform
    enablement pass）。如果只检查 ``extra.api_keys``，env-only 配置（也就是
    把 ``LIGHTCLAW_API_KEY_${UIN}`` 写在 ``.env`` 而不写在 ``config.yaml``）会被
    误判为「未配置」，导致 gateway 跳过该平台、永不连接。

    所以必须兜底读 ENV。API key 等敏感凭证只应放在 ``.env``，``config.yaml``
    里仅放 ``platforms.lightclawbot.enabled: true`` 作为激活开关，这是
    hermes 官方插件（IRC / Teams / Line / ntfy 等）的通用做法。
    """
    extra = getattr(config, "extra", {}) or {}
    if extra.get("api_keys"):
        return True
    # 检查多用户格式
    for key in os.environ:
        if key.startswith("LIGHTCLAW_API_KEY_"):
            if os.environ[key].strip():
                return True
    return False


def _env_enablement_fn():
    """Read LIGHTCLAWBOT_HOME_CHANNEL from env and return seed dict.

    Called by the gateway config loader during _apply_env_overrides to wire
    up the home channel (and any future env-driven config) without requiring
    core code changes.
    """
    home_chat_id = os.getenv("LIGHTCLAWBOT_HOME_CHANNEL", "").strip()
    thread_id = os.getenv("LIGHTCLAWBOT_HOME_CHANNEL_THREAD_ID", "").strip()
    if not home_chat_id:
        return None
    result = {
        "home_channel": {
            "chat_id": home_chat_id,
            "name": "Home",
        }
    }
    if thread_id:
        result["home_channel"]["thread_id"] = thread_id
    return result


def _get_or_create_adapter(config):
    """在当前进程内只创建一个 LightClaw adapter。"""
    global _adapter_instance

    with _adapter_instance_lock:
        if _adapter_instance is None:
            from .src import LightClawAdapter

            _adapter_instance = LightClawAdapter(config)
        return _adapter_instance


def register(ctx):
    """Called by the Hermes plugin discovery system.

    Registers the LightClaw platform adapter so that:
      - Platform("lightclawbot") resolves to a dynamic enum member
      - The gateway creates and connects a LightClawAdapter at startup
      - send_message routes to the adapter via _send_via_adapter()
      - Cron delivery to "lightclawbot:<chat_id>" works automatically
      - User authorization respects LIGHTCLAW_ALLOWED_USERS env var
    """
    from .src import check_lightclaw_requirements

    ctx.register_platform(
        name="lightclawbot",
        label="LightClawBot",
        adapter_factory=_get_or_create_adapter,
        check_fn=check_lightclaw_requirements,
        validate_config=_validate_config,
        is_connected=_is_connected,
        required_env=["LIGHTCLAW_API_KEY_${UIN}"],
        install_hint="See https://pypi.org/project/lightclawbot/",
        allowed_users_env="LIGHTCLAW_ALLOWED_USERS",
        allow_all_env="LIGHTCLAW_ALLOW_ALL_USERS",
        max_message_length=4096,
        emoji="⚡",
        platform_hint=_load_platform_hint(),
        env_enablement_fn=_env_enablement_fn,
        cron_deliver_env_var="LIGHTCLAWBOT_HOME_CHANNEL",
    )


__all__ = ["register", "__version__"]
