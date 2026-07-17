from __future__ import annotations

from pathlib import Path
from typing import Optional

from .adapters.http import HttpExecutor
from .adapters.native_browser import NativeBrowserExecutor
from .adapters.pc_worker import PcWorkerExecutor
from .adapters.research import ResearchExecutor
from .approvals import ApprovalStore
from .bridge import BridgeControlPlane
from .config import OperatorConfig, load_config
from .contracts import ExecutionLevel
from .coordinator import WebOperator
from .live_wiring import load_browser_callables, load_research_callables, wire_status
from .network import DestinationGuard
from .policy import PolicyEngine
from .storage import StateStore


def build_operator(
    config_path: Path,
    *,
    allow_fixture: bool = False,
    wire_live: bool = True,
    config: Optional[OperatorConfig] = None,
) -> WebOperator:
    cfg = config or load_config(config_path, allow_fixture=allow_fixture)
    state_dir = Path(cfg.state_dir).expanduser()
    store = StateStore(state_dir / "state.db")
    policy = PolicyEngine()
    approvals = ApprovalStore(store, policy)
    guard = DestinationGuard(
        allowed_schemes=cfg.allowed_schemes,
        deny_private=cfg.deny_private_destinations,
        fixture_mode=cfg.fixture_mode,
        max_redirects=cfg.max_redirects,
    )

    browser_kwargs: dict = {}
    research_kwargs: dict = {}
    if wire_live and not cfg.fixture_mode:
        b_call, _ = load_browser_callables()
        r_call, _ = load_research_callables()
        browser_kwargs = b_call
        research_kwargs = r_call

    executors = {
        ExecutionLevel.L1: HttpExecutor(guard, max_bytes=cfg.max_response_bytes),
        ExecutionLevel.L2: ResearchExecutor(**research_kwargs),
        ExecutionLevel.L3: NativeBrowserExecutor(guard, **browser_kwargs),
    }
    # Enable L4 when configured OR when bridge devices/status exist (live enroll).
    bridge = None
    try:
        from .crypto import CryptoError

        bridge = BridgeControlPlane(state_dir)
    except Exception:
        bridge = None
    enable_l4 = bool(cfg.pc_worker_enabled)
    if bridge is not None:
        enable_l4 = enable_l4 or any(bridge.paths.devices.glob("*.json")) or any(
            bridge.paths.status.glob("*.json")
        )
    if enable_l4 and bridge is not None:
        executors[ExecutionLevel.L4] = PcWorkerExecutor(
            issuer=bridge.issuer,
            bridge=bridge,
            default_device_id=cfg.pc_device_id,
        )
    elif enable_l4:
        executors[ExecutionLevel.L4] = PcWorkerExecutor(default_device_id=cfg.pc_device_id)

    return WebOperator(
        config=cfg,
        store=store,
        policy=policy,
        approvals=approvals,
        guard=guard,
        executors=executors,
        artifact_root=state_dir / "artifacts",
    )


def live_wire_report() -> dict:
    return wire_status()
