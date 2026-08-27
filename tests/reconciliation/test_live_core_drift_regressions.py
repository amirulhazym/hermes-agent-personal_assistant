from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "docs/reconciliation/hermes-runtime-source-lock.json"
TREE_MANIFEST = REPO / "docs/reconciliation/hermes-runtime-tree-manifest.json"
RECONSTRUCT = REPO / "scripts/reconstruct_hermes_runtime.py"
LIVE_UPSTREAM = Path("/home/ubuntu/.hermes/hermes-agent")


@pytest.fixture(scope="module")
def reconstructed_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("runtime") / "hermes-agent"
    result = subprocess.run(
        [
            sys.executable,
            str(RECONSTRUCT),
            "--lock",
            str(LOCK),
            "--tree-manifest",
            str(TREE_MANIFEST),
            "--base-repo",
            str(LIVE_UPSTREAM),
            "--output",
            str(output),
            "--validate",
        ],
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output


def run_isolated_probe(tree: Path, code: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "HERMES_HOME": str(hermes_home),
        "PYTHONPATH": str(tree),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=tree,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_resume_clears_both_failure_counters_in_materialized_runtime(
    reconstructed_tree: Path, tmp_path: Path
):
    result = run_isolated_probe(
        reconstructed_tree,
        """
from hermes_cli import goals

saved = []
goals.save_goal = lambda session_id, state: saved.append(state)
manager = goals.GoalManager.__new__(goals.GoalManager)
manager.session_id = 'isolated-resume-test'
manager._state = goals.GoalState(
    goal='bounded probe',
    status='paused',
    consecutive_parse_failures=2,
    consecutive_transport_failures=5,
)
state = manager.resume()
assert state is not None
assert state.status == 'active'
assert state.consecutive_parse_failures == 0
assert state.consecutive_transport_failures == 0
assert len(saved) == 1
print('resume_counters=0,0')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "resume_counters=0,0"


def test_auxiliary_sync_completion_uses_execution_middleware(
    reconstructed_tree: Path, tmp_path: Path
):
    result = run_isolated_probe(
        reconstructed_tree,
        """
from unittest.mock import patch
import agent.auxiliary_client as auxiliary

seen = []

def middleware(request, create, *, provider=None):
    seen.append(provider)
    return create(request)

context = auxiliary._RELAY_AUX_CALL_CONTEXT.set({
    'task': 'goal_judge',
    'request_id': 'isolated-middleware-test',
    'attempt_count': 0,
    'provider': 'antigravity',
    'model': 'gemini-3.7-flash',
    'response_model': None,
    'api_mode': 'chat_completions',
})
try:
    with patch('hermes_cli.middleware.run_llm_execution_middleware', side_effect=middleware):
        with patch(
            'agent.relay_llm.execute_current',
            side_effect=lambda request, callback, **kwargs: callback(request),
        ):
            value = auxiliary._relay_sync_completion(
                object(),
                {'model': 'gemini-3.7-flash', 'messages': []},
                provider='antigravity',
                create=lambda request: {'ok': True},
            )
finally:
    auxiliary._RELAY_AUX_CALL_CONTEXT.reset(context)

assert value == {'ok': True}
assert seen == ['antigravity']
print('middleware_provider=antigravity')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "middleware_provider=antigravity"


def test_auxiliary_sync_completion_does_not_retry_provider_after_provider_error(
    reconstructed_tree: Path, tmp_path: Path
):
    result = run_isolated_probe(
        reconstructed_tree,
        """
from unittest.mock import patch
import agent.auxiliary_client as auxiliary

provider_calls = []
def provider(request):
    provider_calls.append(request)
    raise RuntimeError('provider-failure')

def middleware(request, create, *, provider=None):
    return create(request)

context = auxiliary._RELAY_AUX_CALL_CONTEXT.set({
    'task': 'goal_judge',
    'request_id': 'isolated-provider-error-test',
    'attempt_count': 0,
    'provider': 'antigravity',
    'model': 'gemini-3.7-flash',
    'response_model': None,
    'api_mode': 'chat_completions',
})
try:
    with patch('hermes_cli.middleware.run_llm_execution_middleware', side_effect=middleware):
        with patch(
            'agent.relay_llm.execute_current',
            side_effect=lambda request, callback, **kwargs: callback(request),
        ):
            try:
                auxiliary._relay_sync_completion(
                    object(), {'model': 'gemini-3.7-flash', 'messages': []},
                    provider='antigravity', create=provider,
                )
            except RuntimeError as exc:
                assert str(exc) == 'provider-failure'
            else:
                raise AssertionError('provider error was swallowed')
finally:
    auxiliary._RELAY_AUX_CALL_CONTEXT.reset(context)

assert len(provider_calls) == 1, provider_calls
print('provider_calls=1')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "provider_calls=1"


def test_auxiliary_sync_completion_does_not_bypass_failed_middleware(
    reconstructed_tree: Path, tmp_path: Path
):
    result = run_isolated_probe(
        reconstructed_tree,
        """
from unittest.mock import patch
import agent.auxiliary_client as auxiliary

provider_calls = []
def provider(request):
    provider_calls.append(request)
    return {'unexpected': True}

def middleware(request, create, *, provider=None):
    raise RuntimeError('middleware-failure')

context = auxiliary._RELAY_AUX_CALL_CONTEXT.set({
    'task': 'goal_judge',
    'request_id': 'isolated-middleware-error-test',
    'attempt_count': 0,
    'provider': 'antigravity',
    'model': 'gemini-3.7-flash',
    'response_model': None,
    'api_mode': 'chat_completions',
})
try:
    with patch('hermes_cli.middleware.run_llm_execution_middleware', side_effect=middleware):
        with patch(
            'agent.relay_llm.execute_current',
            side_effect=lambda request, callback, **kwargs: callback(request),
        ):
            try:
                auxiliary._relay_sync_completion(
                    object(), {'model': 'gemini-3.7-flash', 'messages': []},
                    provider='antigravity', create=provider,
                )
            except RuntimeError as exc:
                assert str(exc) == 'middleware-failure'
            else:
                raise AssertionError('middleware error was swallowed')
finally:
    auxiliary._RELAY_AUX_CALL_CONTEXT.reset(context)

assert provider_calls == [], provider_calls
print('middleware_failure_preserved=true')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "middleware_failure_preserved=true"
