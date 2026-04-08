#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""Localize Chinese text to Taiwan Modern Chinese via the TAIDE endpoint."""

import sys
import os
import time

import httpx


def get_endpoint_url() -> str:
    url = os.environ.get("TAIDE_ENDPOINT_URL")
    if not url:
        print(
            "Error: Set TAIDE_ENDPOINT_URL to your RunPod endpoint URL",
            file=sys.stderr,
        )
        sys.exit(1)
    return url.rstrip("/")


def wait_for_ready(base_url: str, timeout: int = 120) -> None:
    announced = False
    elapsed = 0.0
    delay = 2

    while True:
        try:
            resp = httpx.get(f"{base_url}/health", timeout=5)
            if resp.status_code == 200:
                return
        except httpx.RequestError:
            pass

        if not announced:
            print("⏳ TAIDE endpoint warming up...", file=sys.stderr)
            announced = True

        if elapsed >= timeout:
            print(
                f"Error: Endpoint did not become ready within {timeout}s",
                file=sys.stderr,
            )
            sys.exit(1)

        actual_delay = min(delay, timeout - elapsed)
        time.sleep(actual_delay)
        elapsed += actual_delay
        delay = min(delay * 2, 60)


def localize(text: str, base_url: str, timeout: float = 120.0) -> str:
    resp = httpx.post(
        f"{base_url}/localize",
        json={"text": text},
        timeout=timeout,
    )
    if resp.status_code != 200:
        print(resp.text, file=sys.stderr)
        sys.exit(1)
    return resp.json()["result"]


def main() -> None:
    base_url = get_endpoint_url()
    warmup_timeout = int(os.environ.get("TAIDE_WARMUP_TIMEOUT", "120"))
    request_timeout = float(os.environ.get("TAIDE_REQUEST_TIMEOUT", "120"))

    if len(sys.argv) > 1:
        text = sys.argv[1]
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print(
            "Usage: localize.py <text>  OR  echo <text> | localize.py",
            file=sys.stderr,
        )
        sys.exit(1)

    wait_for_ready(base_url, timeout=warmup_timeout)
    print(localize(text, base_url, timeout=request_timeout))


if __name__ == "__main__":
    main()
