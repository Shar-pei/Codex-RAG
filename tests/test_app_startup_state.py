from types import SimpleNamespace

from lightrag.api import app_startup_state


def _args(**overrides):
    defaults = {
        "key": "arg-key",
        "input_dir": "input-dir",
        "workspace": "workspace-a",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_app_startup_state_prefers_env_api_key_and_marks_outdated_frontend(
    monkeypatch,
):
    doc_manager_calls = []

    class FakeDocumentManager:
        def __init__(self, input_dir, workspace):
            doc_manager_calls.append((input_dir, workspace))
            self.input_dir = input_dir
            self.workspace = workspace

    monkeypatch.setattr(app_startup_state, "check_frontend_build", lambda: (True, True))
    monkeypatch.setenv("LIGHTRAG_API_KEY", "env-key")
    monkeypatch.setenv("WEBUI_TITLE", "LightRAG")
    monkeypatch.setenv("WEBUI_DESCRIPTION", "API")

    state = app_startup_state.build_app_startup_state(
        _args(),
        api_version="1.2.3",
        document_manager_factory=FakeDocumentManager,
    )

    assert state.webui_assets_exist is True
    assert state.api_version_display == "1.2.3\u26A0\uFE0F"
    assert state.api_key == "env-key"
    assert state.webui_title == "LightRAG"
    assert state.webui_description == "API"
    assert doc_manager_calls == [("input-dir", "workspace-a")]
    assert state.doc_manager.workspace == "workspace-a"


def test_build_app_startup_state_uses_arg_api_key_when_env_missing(monkeypatch):
    monkeypatch.setattr(
        app_startup_state,
        "check_frontend_build",
        lambda: (False, False),
    )
    monkeypatch.delenv("LIGHTRAG_API_KEY", raising=False)
    monkeypatch.delenv("WEBUI_TITLE", raising=False)
    monkeypatch.delenv("WEBUI_DESCRIPTION", raising=False)

    class FakeDocumentManager:
        def __init__(self, input_dir, workspace):
            self.input_dir = input_dir
            self.workspace = workspace

    state = app_startup_state.build_app_startup_state(
        _args(key="arg-only"),
        "1.2.3",
        document_manager_factory=FakeDocumentManager,
    )

    assert state.webui_assets_exist is False
    assert state.api_version_display == "1.2.3"
    assert state.api_key == "arg-only"
    assert state.webui_title is None
    assert state.webui_description is None
    assert state.doc_manager.input_dir == "input-dir"
