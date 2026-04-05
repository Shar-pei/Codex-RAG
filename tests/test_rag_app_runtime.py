from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import rag_app_runtime


def _args(**overrides):
    defaults = {
        "working_dir": "runtime-dir",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _runtime_dependencies(**overrides):
    defaults = {
        "config_cache": "config-cache",
        "llm_timeout": 30,
        "embedding_timeout": 12,
        "embedding_func": "embedding-func",
        "rerank_model_func": "rerank-func",
        "ollama_server_infos": "ollama-info",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_rag_app_runtime_prepares_workdir_and_forwards_runtime_inputs():
    args = _args()
    runtime_dependencies = _runtime_dependencies()
    mkdir_calls = []
    rag_calls = []

    class FakePath:
        def __init__(self, path):
            self.path = path

        def mkdir(self, parents, exist_ok):
            mkdir_calls.append(
                {
                    "path": self.path,
                    "parents": parents,
                    "exist_ok": exist_ok,
                }
            )

    def fake_rag_builder(**kwargs):
        rag_calls.append(kwargs)
        return "rag-instance"

    runtime = rag_app_runtime.build_rag_app_runtime(
        args=args,
        runtime_dependencies=runtime_dependencies,
        rag_builder=fake_rag_builder,
        path_class=FakePath,
    )

    assert runtime == rag_app_runtime.RagAppRuntime(
        rag="rag-instance",
        rerank_enabled=True,
    )
    assert mkdir_calls == [
        {"path": "runtime-dir", "parents": True, "exist_ok": True}
    ]
    assert rag_calls == [
        {
            "args": args,
            "config_cache": "config-cache",
            "llm_timeout": 30,
            "embedding_timeout": 12,
            "embedding_func": "embedding-func",
            "rerank_model_func": "rerank-func",
            "ollama_server_infos": "ollama-info",
        }
    ]


def test_build_rag_app_runtime_reports_rerank_disabled_when_func_is_none():
    runtime = rag_app_runtime.build_rag_app_runtime(
        args=_args(),
        runtime_dependencies=_runtime_dependencies(rerank_model_func=None),
        rag_builder=lambda **kwargs: "rag-instance",
        path_class=lambda path: SimpleNamespace(
            mkdir=lambda parents, exist_ok: None,
        ),
    )

    assert runtime.rag == "rag-instance"
    assert runtime.rerank_enabled is False
