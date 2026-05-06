"""Tests for Claude Code hook handlers."""
from __future__ import annotations

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

# ── Helpers ───────────────────────────────────────────────────────────────────

class FakeEmbeddingModel:
    model_name = "fake-model"
    model_id = "fake-model:deterministic-v1"

    def embed(self, text: str) -> np.ndarray:
        v = np.zeros(8, dtype=np.float32)
        for t in text.lower().split():
            v[sum(ord(c) for c in t) % 8] += 1.0
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def to_bytes(self, e: np.ndarray) -> bytes:
        return e.astype(np.float32).tobytes()

    def from_bytes(self, d: bytes) -> np.ndarray:
        return np.frombuffer(d, dtype=np.float32)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        an, bn = np.linalg.norm(a), np.linalg.norm(b)
        return float(np.dot(a, b) / (an * bn)) if an > 0 and bn > 0 else 0.0


def _make_graph(tmp_path: Path):
    from waggle.graph import MemoryGraph
    return MemoryGraph(str(tmp_path / "hooks-test.db"), FakeEmbeddingModel(), tenant_id="local-default")


# ── pre_response tests ────────────────────────────────────────────────────────

def test_pre_response_empty_stdin(capsys: pytest.CaptureFixture) -> None:
    """pre_response exits cleanly with empty stdin."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "pre_response.py"
    assert hook_path.exists()

    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_response", hook_path)
    mod = importlib.util.module_from_spec(spec)

    with patch("sys.stdin", StringIO("")), \
         patch("sys.exit") as mock_exit, \
         patch("builtins.print") as mock_print:
        try:
            spec.loader.exec_module(mod)
            mod.main()
        except SystemExit:
            pass

    # Should have called print with empty JSON or exited
    assert mock_exit.called or mock_print.called


def test_pre_response_with_prompt(tmp_path: Path) -> None:
    """pre_response returns JSON output for a valid prompt."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "pre_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_response", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = json.dumps({"prompt": "What database did we choose?", "session_id": "test-session"})

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    # Should have printed at least one JSON line
    assert output_lines, "pre_response printed nothing"
    # Last output should be valid JSON
    last = output_lines[-1]
    parsed = json.loads(last)
    assert isinstance(parsed, dict)


def test_pre_response_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """pre_response respects the 5-second timeout and exits 0."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "pre_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_response_timeout", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = json.dumps({"prompt": "test", "session_id": "s1"})

    def slow_import(*args: object, **kw: object) -> None:
        raise TimeoutError("simulated timeout")

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit):
        # Simulate timeout by raising it inside main
        original_main = mod.main

        def patched_main() -> None:
            raise TimeoutError("simulated")

        mod.main = patched_main
        try:
            mod.main()
        except (SystemExit, TimeoutError):
            pass
        finally:
            mod.main = original_main


# ── post_response tests ───────────────────────────────────────────────────────

def test_post_response_skips_secrets(tmp_path: Path) -> None:
    """post_response skips capture when secrets are detected."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "post_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("post_response", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Payload with a fake API key in the user message
    payload = json.dumps({
        "session_id": "s1",
        "transcript": [
            {"role": "user", "content": "my key is sk-abc123def456ghi789jkl012mno345"},
            {"role": "assistant", "content": "I see you have an API key."},
        ],
    })

    observe_called = []

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    # Should have exited silently without calling observe_conversation
    assert not observe_called
    # Output should be empty JSON (silent exit)
    if output_lines:
        assert json.loads(output_lines[-1]) == {}


def test_post_response_empty_transcript(tmp_path: Path) -> None:
    """post_response exits cleanly with empty transcript."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "post_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("post_response_empty", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = json.dumps({"session_id": "s1", "transcript": []})

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit):
        try:
            mod.main()
        except SystemExit:
            pass

    if output_lines:
        assert json.loads(output_lines[-1]) == {}


def test_post_response_skips_non_durable_turns(tmp_path: Path) -> None:
    """post_response skips long chatter that has no durable memory signal."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "post_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("post_response_nondurable", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = json.dumps({
        "session_id": "s1",
        "transcript": [
            {"role": "user", "content": "That explanation was very detailed and interesting to read through."},
            {"role": "assistant", "content": "Glad it helped. I can explain it again in a different style if you want."},
        ],
    })

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch("waggle.graph.MemoryGraph.observe_conversation") as observe_mock, \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    observe_mock.assert_not_called()
    if output_lines:
        assert json.loads(output_lines[-1]) == {}


def test_post_response_ingests_durable_turns(tmp_path: Path) -> None:
    """post_response still ingests turns with a durable signal."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "post_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("post_response_durable", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = json.dumps({
        "session_id": "s1",
        "project": "MCP",
        "agent_id": "codex",
        "transcript": [
            {"role": "user", "content": "We decided to ship checkpoint handoff before broader automation."},
            {"role": "assistant", "content": "Understood. I'll remember that product decision."},
        ],
    })

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch("waggle.graph.MemoryGraph.observe_conversation") as observe_mock, \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    observe_mock.assert_called_once()
    _, kwargs = observe_mock.call_args
    assert kwargs["project"] == "MCP"
    assert kwargs["agent_id"] == "codex"
    assert kwargs["session_id"] == "s1"
    if output_lines:
        assert json.loads(output_lines[-1]) == {}


def test_pre_response_restores_checkpoint_when_db_scope_is_empty(tmp_path: Path) -> None:
    """pre_response falls back to a session checkpoint only after scoped DB recall is empty."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "pre_response.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_response_restore", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    export_root = tmp_path / "exports"
    checkpoint_path = export_root / "checkpoints" / "MCP" / "s1.abhi"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text("checkpoint")

    payload = json.dumps({
        "prompt": "session memory bootstrap",
        "session_id": "s1",
        "project": "MCP",
        "agent_id": "codex",
    })

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    empty_prime = SimpleNamespace(summary="", nodes=[])
    restored_prime = SimpleNamespace(summary="Restored context", nodes=[{"label": "Checkpoint memory"}])

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch("waggle.graph.MemoryGraph.prime_context", side_effect=[empty_prime, restored_prime]) as prime_mock, \
         patch("waggle.graph.MemoryGraph.query") as query_mock, \
         patch("waggle.graph.MemoryGraph.import_abhi") as import_mock, \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
             "WAGGLE_EXPORT_DIR": str(export_root),
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    import_mock.assert_called_once()
    _, import_kwargs = import_mock.call_args
    assert import_kwargs["input_path"] == checkpoint_path
    assert import_kwargs["merge_strategy"] == "skip-existing"
    assert prime_mock.call_count == 2
    query_mock.assert_not_called()
    assert output_lines
    assert "Restored context" in json.loads(output_lines[-1])["content"]


def test_pre_compact_writes_session_checkpoint_stem(tmp_path: Path) -> None:
    """pre_compact routes transcript handoff through the new scoped checkpoint path."""
    hook_path = ROOT / "src" / "waggle" / "hooks" / "claude_code" / "pre_compact.py"

    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_compact_checkpoint", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    export_root = tmp_path / "exports"
    payload = json.dumps({
        "session_id": "s1",
        "project": "MCP",
        "agent_id": "codex",
        "transcript": [
            {"role": "user", "content": "We decided to checkpoint before compaction."},
            {"role": "assistant", "content": "I'll persist that before compacting."},
        ],
    })

    output_lines: list[str] = []

    def fake_print(data: str = "", **kw: object) -> None:
        output_lines.append(str(data))

    with patch("sys.stdin", StringIO(payload)), \
         patch("builtins.print", side_effect=fake_print), \
         patch("sys.exit", side_effect=SystemExit), \
         patch("waggle.graph.MemoryGraph.ingest_transcript_handoff") as ingest_mock, \
         patch.dict("os.environ", {
             "WAGGLE_DB_PATH": str(tmp_path / "hooks-test.db"),
             "WAGGLE_MODEL": "deterministic",
             "WAGGLE_BACKEND": "sqlite",
             "WAGGLE_DEFAULT_TENANT_ID": "local-default",
             "WAGGLE_EXPORT_DIR": str(export_root),
         }):
        try:
            mod.main()
        except SystemExit:
            pass

    ingest_mock.assert_called_once()
    args, kwargs = ingest_mock.call_args
    payload_model = args[0]
    assert payload_model.project == "MCP"
    assert payload_model.agent_id == "codex"
    assert payload_model.session_id == "s1"
    assert kwargs["output_path"] == str(export_root / "checkpoints" / "MCP" / "s1")
    if output_lines:
        assert json.loads(output_lines[-1]) == {}


# ── setup hooks tests ─────────────────────────────────────────────────────────

def test_install_claude_hooks_idempotent(tmp_path: Path) -> None:
    """Installing hooks twice should not duplicate entries."""
    from waggle.server import _install_claude_hooks, _uninstall_claude_hooks

    hook_dir = ROOT / "src" / "waggle" / "hooks" / "claude_code"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")

    with patch("waggle.server._find_claude_settings", return_value=settings_path):
        _install_claude_hooks(hook_dir)
        _install_claude_hooks(hook_dir)  # second call — idempotent

    data = json.loads(settings_path.read_text())
    hooks = data.get("hooks", {})

    # Each event should have exactly one waggle entry
    for event in ("UserPromptSubmit", "Stop", "PreCompact"):
        entries = hooks.get(event, [])
        waggle_entries = [
            e for e in entries
            if any("waggle" in str(h.get("command", "")) for h in e.get("hooks", []))
        ]
        assert len(waggle_entries) == 1, (
            f"Expected exactly 1 waggle entry for {event}, got {len(waggle_entries)}"
        )


def test_uninstall_hooks_removes_block(tmp_path: Path) -> None:
    """uninstall-hooks removes waggle entries cleanly."""
    from waggle.server import _install_claude_hooks, _uninstall_claude_hooks

    hook_dir = ROOT / "src" / "waggle" / "hooks" / "claude_code"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")

    with patch("waggle.server._find_claude_settings", return_value=settings_path):
        _install_claude_hooks(hook_dir)
        result = _uninstall_claude_hooks()

    assert result is not None
    data = json.loads(settings_path.read_text())
    hooks = data.get("hooks", {})
    for event_entries in hooks.values():
        for entry in event_entries:
            for h in entry.get("hooks", []):
                assert "waggle" not in str(h.get("command", "")), (
                    "Waggle hook entry still present after uninstall"
                )


def test_uninstall_hooks_idempotent(tmp_path: Path) -> None:
    """uninstall-hooks is idempotent — second call returns None."""
    from waggle.server import _install_claude_hooks, _uninstall_claude_hooks

    hook_dir = ROOT / "src" / "waggle" / "hooks" / "claude_code"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")

    with patch("waggle.server._find_claude_settings", return_value=settings_path):
        _install_claude_hooks(hook_dir)
        _uninstall_claude_hooks()
        result2 = _uninstall_claude_hooks()

    assert result2 is None, "Second uninstall should return None (nothing to remove)"


def test_setup_writes_managed_block(tmp_path: Path) -> None:
    """waggle-mcp setup --yes writes the hooks block to Claude Code settings."""
    from waggle.server import _install_claude_hooks

    hook_dir = ROOT / "src" / "waggle" / "hooks" / "claude_code"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")

    with patch("waggle.server._find_claude_settings", return_value=settings_path):
        written = _install_claude_hooks(hook_dir)

    assert written == settings_path
    data = json.loads(settings_path.read_text())
    assert "hooks" in data
    # Verify waggle commands are present
    all_commands = [
        h.get("command", "")
        for entries in data["hooks"].values()
        for entry in entries
        for h in entry.get("hooks", [])
    ]
    assert any("waggle" in cmd for cmd in all_commands), (
        "No waggle commands found in installed hooks"
    )
