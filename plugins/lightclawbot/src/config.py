"""
LightClaw adapter — constants and utility functions.
Mirrors: src/config.ts
"""

import os
import time
import uuid

# ---------------------------------------------------------------------------
# Channel key
# ---------------------------------------------------------------------------

CHANNEL_KEY = "lightclawbot"

# ---------------------------------------------------------------------------
# Event names
# ---------------------------------------------------------------------------

EVENT_MESSAGE_PRIVATE   = "message:private"
EVENT_MESSAGE_ACK       = "message:ack"
EVENT_HANDSHAKE         = "__handshake__"
EVENT_HISTORY_REQUEST   = "message:history:request"
EVENT_HISTORY_RESPONSE  = "message:history:response"
EVENT_SESSIONS_REQUEST  = "sessions:request"
EVENT_SESSIONS_RESPONSE = "sessions:response"
# chat CRUD 信令：新版前端多会话（chats.json）通道，
# 承载 list/create/update/delete/clearContext 请求。
EVENT_CHAT_REQUEST      = "chat:request"
EVENT_CHAT_RESPONSE     = "chat:response"
# Agent 列表查询（agents:request/response 已在 IMEventType 中，ai-server 原生支持）
EVENT_AGENTS_REQUEST     = "agents:request"
EVENT_AGENTS_RESPONSE    = "agents:response"
AGENTS_CONFIG_FILENAME   = "agents.json"

# ---------------------------------------------------------------------------
# Site (cn / intl)
# ---------------------------------------------------------------------------
# 因此由前端在调用 hermes_install.sh 时以 SITE 传入，脚本落盘到
# ``~/.hermes/.env`` 的 LIGHTCLAW_SITE，插件启动时读取并推导三个 URL Host（WS / API / Upload）

DEFAULT_SITE = "cn"

# host
SITE_HOSTS = {
    "cn":   "lightai.cloud.tencent.com",
    "intl": "lightai.tencentcloud.com",
}


def normalize_site(site):
    """site：非法 / 空值一律回退 cn（对齐 web 端 || AI_SERVER_DOMAINS.cn）。"""
    s = (site or "").strip().lower()
    return s if s in SITE_HOSTS else DEFAULT_SITE


def resolve_site_urls(site=None):
    """根据 *site* 解析 ws / api / upload 三类 base url。

    *site* 缺省（None）时读环境变量 ``LIGHTCLAW_SITE``；非法值回退 cn。
    """
    if site is None:
        site = os.getenv("LIGHTCLAW_SITE")
    host = SITE_HOSTS[normalize_site(site)]
    return {
        "ws":     f"wss://{host}",
        "api":    f"https://{host}",
        "upload": f"https://{host}",
    }


_SITE_URLS = resolve_site_urls()

# ---------------------------------------------------------------------------
# Server URLs / paths
# ---------------------------------------------------------------------------
DEFAULT_WS_BASE_URL  = _SITE_URLS["ws"]
DEFAULT_API_BASE_URL = _SITE_URLS["api"]
SOCKET_PATH          = "/ws/agent"
API_PATH_TICKET      = "/cgi/ticket"

# ---------------------------------------------------------------------------
# Protocol limits
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 4096

# Default agentId (mirrors DEFAULT_AGENT_ID in config.ts)
DEFAULT_AGENT_ID = "main"

# ---------------------------------------------------------------------------
# Reconnect strategy (mirrors NativeSocketClient)
# ---------------------------------------------------------------------------

RECONNECT_DELAY_BASE = 1.0   # seconds
RECONNECT_DELAY_MAX  = 30.0  # seconds

# ---------------------------------------------------------------------------
# ReliableEmitter config (mirrors reliable-emitter.ts)
# ---------------------------------------------------------------------------

EMIT_ACK_TIMEOUT      = 5.0   # seconds
EMIT_MAX_RETRIES      = 3
EMIT_RETRY_BASE_DELAY = 2.0   # seconds
EMIT_RETRY_MAX_DELAY  = 15.0  # seconds
EMIT_PENDING_MAX      = 500

# ---------------------------------------------------------------------------
# Media / file storage (mirrors src/config.ts media section)
# ---------------------------------------------------------------------------

# Remote file storage service base URL
SERVER_UPLOAD_BASE_URL = _SITE_URLS["upload"]
API_PATH_UPLOAD        = "/drive/save"       # POST multipart/form-data
API_PATH_DOWNLOAD      = "/drive/preview"    # GET ?filePath=...

# Single-file hard limit: 100 MB (mirrors MEDIA_MAX_BYTES)
MEDIA_MAX_BYTES = 100 * 1024 * 1024
# Upload/download timeout in seconds (mirrors UPLOAD_TIMEOUT=120_000ms)
UPLOAD_TIMEOUT   = 120.0
DOWNLOAD_TIMEOUT = 60.0

# URI scheme for local-file references embedded in AI replies.
# Front-end recognises this prefix and issues a file:download signal to
# trigger on-demand upload + download.
LOCALFILE_SCHEME = "localfile://"

# Auth header `x-product` value (mirrors TS X_PRODUCT)
X_PRODUCT = "channel"

# ---------------------------------------------------------------------------
# file:download signalling (kind field value + status enum)
# ---------------------------------------------------------------------------

KIND_FILE_DOWNLOAD = "file:download"

# ---------------------------------------------------------------------------
# Token usage frame (kind field value)
# ---------------------------------------------------------------------------
# Per-turn token consumption carried under ``extra.usage`` (UnifiedUsage):
#   { kind: 'usage', extra: { chatId: '', usage: { inputTokens, outputTokens, totalTokens } } }
KIND_USAGE = "usage"

# ---------------------------------------------------------------------------
# Thinking step frame (kind field value)
# ---------------------------------------------------------------------------
# 工具调用时间线条目，承载 agent "思考过程" 行级展示。
# 协议契约：见 docs/PROTOCOL.md §thinking_step。
#
# 帧结构示例：
#   {
#     kind: 'thinking_step',
#     content: '',
#     extra: {
#       chatId: '',
#       step: {
#         stepId:   'step-1-exec',                        # 同一行的合并锚点
#         seq:      1,                                    # 时间线位置序号
#         type:     'cmd',                                # 6 分类: tool|cmd|patch|browser|subagent|plan
#         text:     '执行了 执行命令: lsof -i :9222',     # verb + summary 重组后文案
#         status:   'running',                            # 阶段一只发 running
#         toolName: 'exec',                               # 原始工具名
#         detail:   'lsof -i :9222'                       # 折叠展开内容（冒号后部分）
#       }
#     }
#   }
#
# 阶段一不发 status=done 帧（hermes 框架未暴露工具结束钩子）。
# 旧前端忽略未知 kind 即可平滑过渡。
KIND_THINKING_STEP = "thinking_step"

# ---------------------------------------------------------------------------
# Tool name → (type, verb) classification for thinking_step frames
# ---------------------------------------------------------------------------
# 6 分类（与 openclaw thinking-formatter.ts 对齐）：
#   - 'browser':   浏览器类工具    → Web 据此打开浏览器云桌面
#   - 'cmd':       命令执行类工具  → 终端图标
#   - 'patch':     文件编辑类工具  → 编辑图标
#   - 'subagent':  子任务派发      → 子任务图标
#   - 'plan':      计划更新        → 计划图标
#   - 'tool':      其他一切        → 默认通用图标
#
# 规则匹配按列表顺序、首个命中为准；未命中 → 'tool' 兜底。verb 用于 running
# 帧文案重组：`执行了 ${verb}: ${summary}` —— 与 openclaw 文案视觉风格保持一致。
#
# 注意：hermes 框架不暴露工具 args 结构化对象，summary 只能从已渲染文本里
# 提取冒号后部分（详见 outbound.py: _summarize_tool_text）。
_TOOL_TYPE_RULES = (
    # ── 浏览器类（按 hermes 真实工具名细分 verb，与 openclaw 文案对齐）──
    #
    # hermes 把 openclaw 的 browser+action 子命令拍平成独立工具名（如
    # browser_navigate / browser_click / browser_screenshot），无 args 概念。
    # 因此直接按工具名匹配 verb，无需 action 分支特化。具体规则放在通用
    # `browser` 兜底之前，保证更精确的匹配优先命中。
    #
    # 无副词类（screenshot/scroll/back/forward/reload/close）的 summary 通常是
    # SDK 内部句柄（如 page-5），需要在 outbound.py: _summarize_tool_text 处
    # 强制丢弃，避免出现 "执行了 页面截图: 5" 这类噪音文案。
    (lambda n: n in {"browser_navigate", "browser_open", "browser_goto"},
     "browser", "打开网页"),
    (lambda n: n in {"browser_click", "browser_tap"},
     "browser", "点击页面元素"),
    (lambda n: n in {"browser_type", "browser_fill", "browser_input"},
     "browser", "输入文本"),
    (lambda n: n == "browser_scroll",
     "browser", "滚动页面"),
    (lambda n: n == "browser_back",
     "browser", "返回上一页"),
    (lambda n: n == "browser_forward",
     "browser", "前进"),
    (lambda n: n in {"browser_reload", "browser_refresh"},
     "browser", "刷新页面"),
    (lambda n: n in {"browser_screenshot", "browser_snapshot"},
     "browser", "页面截图"),
    (lambda n: n == "browser_close",
     "browser", "关闭页面"),
    # 通用浏览器兜底（未知 browser_* 子命令、open_browser、playwright 等）
    (lambda n: n.startswith("browser") or n in {"open_browser", "playwright"},
     "browser", "操作浏览器"),
    # 命令执行类
    (lambda n: n == "exec" or n.startswith("exec_") or n in {
        "shell", "run_command", "terminal", "execute_code",
    },
     "cmd", "执行命令"),
    # 文件编辑类
    (lambda n: n in {"apply_patch", "edit_file", "write_file"} or n.startswith("str_replace"),
     "patch", "编辑文件"),
    # 文件查看类（归入 tool）
    (lambda n: n in {"read", "read_file", "view_code_item"},
     "tool", "查看文件"),
    # 网络访问类（归入 tool）
    (lambda n: n.startswith("web_") or n == "fetch",
     "tool", "访问网页"),
    # 子任务派发类
    (lambda n: ("session" in n and "spawn" in n) or n == "subagents",
     "subagent", "派发子任务"),
    # 计划更新类
    (lambda n: n in {"update_plan", "plan"},
     "plan", "更新计划"),
)


# 这些 browser 子命令的 verb 已经自包含语义（"页面截图" / "滚动页面" / "返回
# 上一页" 等），SDK 在冒号后给出的多为内部句柄噪音（如 page-5 / frame-7）。
# 在 outbound.py: _summarize_tool_text 中遇到这些工具时**强制丢弃 summary**，
# 保证文案干净（避免 "执行了 页面截图: 5" 这类劣化）。
#
# 与 openclaw thinking-formatter.ts: BROWSER_ACTION_VERBS 中无 summary 行为
# 的几项保持一致：scroll / back / forward / reload / refresh / screenshot /
# snapshot / close。
BROWSER_TOOLS_WITHOUT_SUMMARY = frozenset({
    "browser_scroll",
    "browser_back",
    "browser_forward",
    "browser_reload",
    "browser_refresh",
    "browser_screenshot",
    "browser_snapshot",
    "browser_close",
})


def _classify_tool(tool_name: str) -> tuple[str, str]:
    """内部使用：根据工具名返回 (type, verb) 二元组。

    与 openclaw `classifyTool` 对齐。未命中规则时返回 ('tool', '调用 ${name}')。
    """
    if not tool_name:
        return ("tool", "调用工具")
    name = tool_name.strip().lower()
    for matcher, type_, verb in _TOOL_TYPE_RULES:
        if matcher(name):
            return (type_, verb)
    return ("tool", f"调用 {tool_name}")


def classify_tool_type(tool_name: str) -> str:
    """根据工具名返回 thinking_step.step.type（6 分类之一）。

    未知 / 空工具名按 'tool' 兜底。本函数为对外契约，仅暴露 type。
    """
    return _classify_tool(tool_name)[0]


def classify_tool_verb(tool_name: str) -> str:
    """根据工具名返回中文动作短句（用于 running 帧文案重组）。

    与 classify_tool_type 共用同一张规则表，保证 type 与 verb 一一对应。
    """
    return _classify_tool(tool_name)[1]


class FileDownloadStatus:
    """Lifecycle statuses carried inside `extra.transferData.status`.

    Mirrors TS FILE_DOWNLOAD_STATUS enum.
    """
    REQ   = "download_req"    # client → bot
    READY = "download_ready"  # bot → client (file confirmed, upload starting)
    URL   = "download_url"    # bot → client (upload done, public URL ready)
    ERROR = "download_error"  # bot → client (any failure)


# ---------------------------------------------------------------------------
# MIME type lookup (aligned 1:1 with TS guessMimeByExt)
# ---------------------------------------------------------------------------

_MIME_MAP = {
    # image
    ".png":  "image/png",
    ".jpg":  "image/jpeg", ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".svg":  "image/svg+xml",
    # audio
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".ogg":  "audio/ogg",
    # video
    ".mp4":  "video/mp4",
    ".webm": "video/webm",
    # documents
    ".pdf":  "application/pdf",
    ".txt":  "text/plain",
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def generate_msg_id() -> str:
    """Generate a unique message ID."""
    return f"hermes_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def guess_mime(filename: str) -> str:
    """Guess MIME type from file extension."""
    ext = os.path.splitext(filename)[1].lower()
    return _MIME_MAP.get(ext, "application/octet-stream")


def check_lightclaw_requirements() -> bool:
    """Check if aiohttp is available (python-socketio no longer needed)."""
    try:
        import aiohttp  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# 指标采集与上报（mirrors lightclaw/src/config.ts §指标建设.md）
# ---------------------------------------------------------------------------

API_PATH_METRICS_REPORT = "/log/report"

# 聚合型指标（连接质量/消息可靠性/定时任务健康）窗口时长（秒）
METRICS_WINDOW_SECONDS = 60.0

# 单次上报请求最多携带的条目数，超出则分片多次请求
METRICS_BATCH_MAX_ITEMS = 200

# 上报 HTTP 请求超时（秒）
METRICS_REPORT_TIMEOUT = 8.0

# L1 短时抖动重试次数与指数退避参数（1s -> 3s -> 9s）
METRICS_REPORT_MAX_RETRIES = 3
METRICS_REPORT_RETRY_BASE_DELAY = 1.0
METRICS_REPORT_RETRY_FACTOR = 3

# 本地降级缓冲单文件大小上限（字节），超出则丢弃事件明细样本仅保留计数
METRICS_BUFFER_FILE_MAX_BYTES = 2 * 1024 * 1024

# 单个 uin 在一个聚合窗口（METRICS_WINDOW_SECONDS）内最多允许上报的event.error
# 条数：event.error 是"发生即立即上报"（每次 create_task 一个 HTTP 请求），
# 若上游出现错误风暴（如网络抽风导致大量 inbound 解析失败/outbound 发送失败），
# 会无限制创建 asyncio 任务、并对 ai-server 造成突发流量压力。超过阈值后静默
# 丢弃多余条目（不进降级缓冲，避免风暴期间缓冲文件被打爆），计数随窗口 flush
# 一起重置。
METRICS_EVENT_ERROR_MAX_PER_WINDOW = 20

# cron 定时任务健康检测轮询间隔（秒），与聚合窗口保持一致
METRICS_CRON_CHECK_INTERVAL_SECONDS = METRICS_WINDOW_SECONDS
