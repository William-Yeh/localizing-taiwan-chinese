# ── Stage 1: build Python virtualenv ─────────────────────────────────────────
# uv:0.6 is distroless (no shell); copy the binary into a debian slim base
FROM ghcr.io/astral-sh/uv:0.6 AS uv
FROM python:3.11-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /build

COPY pyproject.toml ./pyproject.toml
RUN uv venv /build/.venv && \
    uv pip install --python /build/.venv/bin/python \
        "fastapi>=0.115" "uvicorn[standard]>=0.34" "httpx>=0.27" "huggingface-hub>=0.27"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM ollama/ollama:0.20.3

COPY --from=builder /build/.venv /app/.venv

WORKDIR /app
COPY main.py ./main.py
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV OLLAMA_MODELS=/runpod-volume/models
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

LABEL org.opencontainers.image.title="localizing-taiwan-chinese" \
      org.opencontainers.image.description="Taiwan Modern Chinese localizer using TAIDE (Gemma-3-TAIDE-12b) via Ollama" \
      org.opencontainers.image.source="https://github.com/William-Yeh/localizing-taiwan-chinese" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/docker-entrypoint.sh"]
