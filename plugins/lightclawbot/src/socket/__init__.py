"""
LightClaw socket layer.
Mirrors: src/socket/index.ts

D1 多租户改造后：
    - 移除 ``NativeSocketMixin``（已被 :class:`_PerUinSession` 取代）。
    - 暴露 :class:`_PerUinSession` 供 adapter 实例化使用。
"""

from .reliable_emitter import ReliableEmitter
from .per_uin_session import _PerUinSession

__all__ = ["ReliableEmitter", "_PerUinSession"]
