from lightrag.api.app_factory_config import build_app_kwargs


def test_build_app_kwargs_without_api_key():
    app_kwargs = build_app_kwargs(api_key=None, api_version="1.2.3")

    assert app_kwargs["title"] == "LightRAG Server API"
    assert app_kwargs["version"] == "1.2.3"
    assert app_kwargs["description"] == (
        "Providing API for LightRAG core, Web UI and Ollama Model Emulation"
        "\n\n[View ReDoc documentation](/redoc)"
    )
    assert app_kwargs["openapi_url"] == "/openapi.json"
    assert app_kwargs["docs_url"] is None
    assert app_kwargs["redoc_url"] == "/redoc"
    assert app_kwargs["swagger_ui_parameters"] == {
        "persistAuthorization": True,
        "tryItOutEnabled": True,
    }


def test_build_app_kwargs_with_api_key_note():
    app_kwargs = build_app_kwargs(api_key="secret", api_version="1.2.3")

    assert app_kwargs["description"] == (
        "Providing API for LightRAG core, Web UI and Ollama Model Emulation"
        " (API-Key Enabled)"
        "\n\n[View ReDoc documentation](/redoc)"
    )
