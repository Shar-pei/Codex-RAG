from __future__ import annotations

from lightrag.api import runtime_bootstrap


def test_bootstrap_runtime_environment_loads_dotenv_and_reads_config():
    calls = []

    class FakeConfig:
        def __init__(self):
            self.read_calls = []

        def read(self, path):
            self.read_calls.append(path)
            calls.append(("config.read", path))

    fake_config = FakeConfig()

    config = runtime_bootstrap.bootstrap_runtime_environment(
        dotenv_loader=lambda **kwargs: calls.append(("load_dotenv", kwargs)),
        config_parser_factory=lambda: calls.append(("ConfigParser",)) or fake_config,
    )

    assert config is fake_config
    assert calls == [
        ("load_dotenv", {"dotenv_path": ".env", "override": False}),
        ("ConfigParser",),
        ("config.read", "config.ini"),
    ]


def test_bootstrap_runtime_environment_forwards_custom_paths_and_override():
    dotenv_calls = []
    read_calls = []

    class FakeConfig:
        def read(self, path):
            read_calls.append(path)

    runtime_bootstrap.bootstrap_runtime_environment(
        dotenv_path="custom.env",
        override=True,
        config_path="custom.ini",
        dotenv_loader=lambda **kwargs: dotenv_calls.append(kwargs),
        config_parser_factory=FakeConfig,
    )

    assert dotenv_calls == [{"dotenv_path": "custom.env", "override": True}]
    assert read_calls == ["custom.ini"]
