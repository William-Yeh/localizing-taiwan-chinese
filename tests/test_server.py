import os
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("TAIDE_MODEL_NAME", "taide-q8")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def ollama_mock(response_text: str = "ok"):
    """Return a mock httpx.AsyncClient with a post() that succeeds."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"response": response_text}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client, mock_resp


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model"] == "taide-q8"


def test_localize_empty_text_returns_422():
    resp = client.post("/localize", json={"text": ""})
    assert resp.status_code == 422


def test_localize_whitespace_only_returns_422():
    resp = client.post("/localize", json={"text": "   "})
    assert resp.status_code == 422


def test_localize_calls_ollama_and_returns_result():
    mock_client, _ = ollama_mock("軟體下載")
    with patch("main.http_client", mock_client):
        resp = client.post("/localize", json={"text": "软件下载"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "軟體下載"}


def test_localize_passes_system_prompt_to_ollama():
    mock_client, _ = ollama_mock()
    with patch("main.http_client", mock_client):
        resp = client.post("/localize", json={"text": "测试"})
    assert resp.status_code == 200
    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert "system" in payload
    assert "台灣" in payload["system"]
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.1


def test_temperature_env_var_is_used(monkeypatch):
    import main as m
    monkeypatch.setattr(m, "TEMPERATURE", 0.3)
    mock_client, _ = ollama_mock()
    with patch("main.http_client", mock_client):
        client.post("/localize", json={"text": "测试"})
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["options"]["temperature"] == 0.3


def test_ollama_base_url_env_var_is_used(monkeypatch):
    import main as m
    monkeypatch.setattr(m, "OLLAMA_BASE_URL", "http://custom-ollama:11434")
    mock_client, _ = ollama_mock()
    with patch("main.http_client", mock_client):
        client.post("/localize", json={"text": "测试"})
    call_url = mock_client.post.call_args[0][0]
    assert call_url.startswith("http://custom-ollama:11434")


def test_localize_ollama_unreachable_returns_503():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    with patch("main.http_client", mock_client):
        resp = client.post("/localize", json={"text": "测试"})
    assert resp.status_code == 503


def test_localize_ollama_http_error_returns_503():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_resp
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    with patch("main.http_client", mock_client):
        resp = client.post("/localize", json={"text": "测试"})
    assert resp.status_code == 503
