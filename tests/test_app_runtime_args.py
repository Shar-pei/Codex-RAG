from types import SimpleNamespace

import pytest

from lightrag.api import app_runtime_args


def _args(**overrides):
    defaults = {
        "llm_binding": "openai",
        "embedding_binding": "openai",
        "llm_binding_host": None,
        "embedding_binding_host": None,
        "ssl": False,
        "ssl_certfile": None,
        "ssl_keyfile": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_normalize_runtime_args_fills_missing_default_hosts(monkeypatch):
    args = _args()

    monkeypatch.setattr(
        app_runtime_args,
        "get_default_host",
        lambda binding: f"https://{binding}.example.com",
    )

    normalized = app_runtime_args.normalize_runtime_args(args)

    assert normalized is args
    assert args.llm_binding_host == "https://openai.example.com"
    assert args.embedding_binding_host == "https://openai.example.com"


def test_normalize_runtime_args_rejects_unsupported_llm_binding():
    with pytest.raises(Exception, match="llm binding not supported"):
        app_runtime_args.normalize_runtime_args(_args(llm_binding="unsupported"))


def test_normalize_runtime_args_rejects_unsupported_embedding_binding():
    with pytest.raises(Exception, match="embedding binding not supported"):
        app_runtime_args.normalize_runtime_args(
            _args(embedding_binding="unsupported")
        )


def test_normalize_runtime_args_requires_ssl_cert_and_key():
    with pytest.raises(
        Exception,
        match="SSL certificate and key files must be provided when SSL is enabled",
    ):
        app_runtime_args.normalize_runtime_args(_args(ssl=True))


def test_normalize_runtime_args_requires_existing_ssl_cert(monkeypatch):
    args = _args(ssl=True, ssl_certfile="cert.pem", ssl_keyfile="key.pem")
    monkeypatch.setattr(
        app_runtime_args.os.path,
        "exists",
        lambda path: path == "key.pem",
    )

    with pytest.raises(Exception, match=r"SSL certificate file not found: cert\.pem"):
        app_runtime_args.normalize_runtime_args(args)


def test_normalize_runtime_args_requires_existing_ssl_key(monkeypatch):
    args = _args(ssl=True, ssl_certfile="cert.pem", ssl_keyfile="key.pem")
    monkeypatch.setattr(
        app_runtime_args.os.path,
        "exists",
        lambda path: path == "cert.pem",
    )

    with pytest.raises(Exception, match=r"SSL key file not found: key\.pem"):
        app_runtime_args.normalize_runtime_args(args)
