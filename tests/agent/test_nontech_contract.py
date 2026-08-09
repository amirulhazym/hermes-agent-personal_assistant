"""Contract tests for the canonical non-tech explanation skill."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

from agent.skill_commands import build_skill_invocation_message, scan_skill_commands


def _load_trigger_handler():
    path = Path.home() / ".hermes" / "hooks" / "skill-trigger" / "handler.py"
    spec = importlib.util.spec_from_file_location("skill_trigger_handler", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_skill(skills_dir, name, body="Explain clearly."):
    skill_dir = skills_dir / "communication" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_canonical_nontech_skill_is_discoverable_without_accidental_names(tmp_path):
    _make_skill(tmp_path, "non-tech")

    with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
        commands = scan_skill_commands()

    assert "/non-tech" in commands
    assert "/non-technical-explanation" not in commands
    assert "/budak" not in commands


def test_nontech_invocation_preserves_explicit_deep_argument(tmp_path):
    _make_skill(tmp_path, "non-tech")

    with patch("agent.skill_commands.get_skill_commands", return_value={
                "/non-tech": {"skill_dir": "communication/non-tech"},
            }):
        with patch(
            "agent.skill_commands._load_skill_payload",
            return_value=(
                {"name": "non-tech", "content": "Explain clearly."},
                tmp_path / "communication" / "non-tech",
                "non-tech",
            ),
        ):
            message = build_skill_invocation_message("/non-tech", "--deep explain this")

    assert message is not None
    assert "--deep explain this" in message


def test_confusion_phrase_triggers_only_canonical_nontech(tmp_path):
    handler = _load_trigger_handler()
    trigger_file = tmp_path / "triggered_skills.txt"
    with patch.object(handler, "TRIGGER_FILE", trigger_file):
        handler.handle("agent:start", {"message": "aku tak faham apa benda ni"})

    assert trigger_file.read_text(encoding="utf-8") == "non-tech"


def test_confusion_trigger_never_requests_deep_mode(tmp_path):
    handler = _load_trigger_handler()
    trigger_file = tmp_path / "triggered_skills.txt"
    with patch.object(handler, "TRIGGER_FILE", trigger_file):
        handler.handle("agent:start", {"message": "explain balik, aku lost"})

    content = trigger_file.read_text(encoding="utf-8")
    assert content == "non-tech"
    assert "deep" not in content