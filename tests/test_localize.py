import pytest
import time
import httpx
from unittest.mock import patch, MagicMock

import localize


def test_missing_env_var_exits_with_message(monkeypatch, capsys):
    monkeypatch.delenv("TAIDE_ENDPOINT_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        localize.get_endpoint_url()
    assert exc.value.code == 1
    assert "TAIDE_ENDPOINT_URL" in capsys.readouterr().err


def test_env_var_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("TAIDE_ENDPOINT_URL", "http://example.com/")
    assert localize.get_endpoint_url() == "http://example.com"


def test_wait_for_ready_already_up():
    mock_resp = MagicMock(status_code=200)
    with patch("localize.httpx.get", return_value=mock_resp) as mock_get:
        localize.wait_for_ready("http://example.com")
    mock_get.assert_called_once()


def test_wait_for_ready_prints_warming_up_message(capsys):
    responses = [httpx.RequestError("down"), MagicMock(status_code=200)]
    call_count = 0

    def side_effect(url, timeout):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        if isinstance(r, Exception):
            raise r
        return r

    with patch("localize.httpx.get", side_effect=side_effect), \
         patch("localize.time.sleep"):
        localize.wait_for_ready("http://example.com")

    assert "warming up" in capsys.readouterr().err


def test_wait_for_ready_timeout_exits(capsys):
    with patch("localize.httpx.get", side_effect=httpx.RequestError("down")), \
         patch("localize.time.sleep"):
        with pytest.raises(SystemExit) as exc:
            localize.wait_for_ready("http://example.com", timeout=10)
    assert exc.value.code == 1
    assert "10s" in capsys.readouterr().err


def test_backoff_cap_is_60s():
    sleep_calls = []

    with patch("localize.httpx.get", side_effect=httpx.RequestError("down")), \
         patch("localize.time.sleep", side_effect=sleep_calls.append):
        with pytest.raises(SystemExit):
            localize.wait_for_ready("http://example.com", timeout=300)

    assert all(d <= 60 for d in sleep_calls)
    assert 60 in sleep_calls


def test_localize_returns_result():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"result": "軟體下載"}

    with patch("localize.httpx.post", return_value=mock_resp):
        result = localize.localize("软件下载", "http://example.com")

    assert result == "軟體下載"


def test_localize_respects_request_timeout():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"result": "ok"}
    captured = {}

    def mock_post(url, json=None, timeout=None, **kwargs):
        captured["timeout"] = timeout
        return mock_resp

    with patch("localize.httpx.post", side_effect=mock_post):
        localize.localize("text", "http://example.com", timeout=60.0)

    assert captured["timeout"] == 60.0


def test_localize_server_error_exits(capsys):
    mock_resp = MagicMock(status_code=500, text="Internal Server Error")

    with patch("localize.httpx.post", return_value=mock_resp):
        with pytest.raises(SystemExit) as exc:
            localize.localize("text", "http://example.com")

    assert exc.value.code == 1
    assert "Internal Server Error" in capsys.readouterr().err


def test_main_uses_cli_arg(monkeypatch, capsys):
    monkeypatch.setenv("TAIDE_ENDPOINT_URL", "http://example.com")
    monkeypatch.setattr("sys.argv", ["localize.py", "软件下载"])

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"result": "軟體下載"}

    with patch("localize.httpx.get", return_value=MagicMock(status_code=200)), \
         patch("localize.httpx.post", return_value=mock_resp):
        localize.main()

    assert "軟體下載" in capsys.readouterr().out


def test_main_uses_warmup_and_request_timeouts(monkeypatch):
    monkeypatch.setenv("TAIDE_ENDPOINT_URL", "http://example.com")
    monkeypatch.setenv("TAIDE_WARMUP_TIMEOUT", "30")
    monkeypatch.setenv("TAIDE_REQUEST_TIMEOUT", "60")
    monkeypatch.setattr("sys.argv", ["localize.py", "test"])

    captured = {}

    def mock_wait(base_url, timeout=120):
        captured["warmup_timeout"] = timeout

    def mock_localize(text, base_url, timeout=120.0):
        captured["request_timeout"] = timeout
        return "ok"

    with patch.object(localize, "wait_for_ready", side_effect=mock_wait), \
         patch.object(localize, "localize", side_effect=mock_localize):
        localize.main()

    assert captured["warmup_timeout"] == 30
    assert captured["request_timeout"] == 60.0


def test_main_no_input_exits(monkeypatch, capsys):
    monkeypatch.setenv("TAIDE_ENDPOINT_URL", "http://example.com")
    monkeypatch.setattr("sys.argv", ["localize.py"])
    monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))

    with pytest.raises(SystemExit) as exc:
        localize.main()

    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().err
