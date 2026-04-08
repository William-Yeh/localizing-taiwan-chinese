#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR="${OLLAMA_MODELS:-/runpod-volume/models}"
Q8_GGUF="$MODELS_DIR/Gemma-3-TAIDE-12b-Chat-2602-Q8_0.gguf"
Q4_GGUF="$MODELS_DIR/Gemma-3-TAIDE-12b-Chat-2602-Q4_K_M.gguf"
HF_REPO="audreyt/Gemma-3-TAIDE-12b-Chat-2602-GGUF"
OLLAMA_PID=""
UVICORN_PID=""

# Propagate SIGTERM/SIGINT to both child processes for graceful shutdown
cleanup() {
    echo "[entrypoint] Shutting down..."
    [[ -n "$UVICORN_PID" ]] && kill "$UVICORN_PID" 2>/dev/null
    [[ -n "$OLLAMA_PID" ]] && kill "$OLLAMA_PID" 2>/dev/null
    wait 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

# 1. Start Ollama in the background
OLLAMA_MODELS="$MODELS_DIR" ollama serve &
OLLAMA_PID=$!

# 2. Wait for Ollama to accept connections (hard timeout to fail fast)
echo "[entrypoint] Waiting for Ollama..."
OLLAMA_WAIT_TIMEOUT="${OLLAMA_WAIT_TIMEOUT:-120}"
OLLAMA_WAIT_ELAPSED=0
until curl -sf http://localhost:11434/ > /dev/null 2>&1; do
    sleep 1
    OLLAMA_WAIT_ELAPSED=$((OLLAMA_WAIT_ELAPSED + 1))
    if [[ $OLLAMA_WAIT_ELAPSED -ge $OLLAMA_WAIT_TIMEOUT ]]; then
        echo "[entrypoint] ERROR: Ollama did not start within ${OLLAMA_WAIT_TIMEOUT}s" >&2
        kill "$OLLAMA_PID" 2>/dev/null
        exit 1
    fi
done
echo "[entrypoint] Ollama ready."

# 3. Download GGUFs from HuggingFace if not already on Network Volume
download_if_missing() {
    local dest="$1"
    local filename="$2"
    if [[ ! -f "$dest" ]]; then
        echo "[entrypoint] Downloading $filename from HuggingFace..."
        mkdir -p "$(dirname "$dest")"
        huggingface-cli download "$HF_REPO" "$filename" \
            --local-dir "$(dirname "$dest")" \
            --local-dir-use-symlinks False
    else
        echo "[entrypoint] $filename already present."
    fi
}

download_if_missing "$Q8_GGUF" "Gemma-3-TAIDE-12b-Chat-2602-Q8_0.gguf"
download_if_missing "$Q4_GGUF" "Gemma-3-TAIDE-12b-Chat-2602-Q4_K_M.gguf"

# 4. Create Ollama Modelfiles (idempotent)
echo "FROM $Q8_GGUF" | OLLAMA_MODELS="$MODELS_DIR" ollama create taide-q8 -f - \
    && echo "[entrypoint] Created model taide-q8"
echo "FROM $Q4_GGUF" | OLLAMA_MODELS="$MODELS_DIR" ollama create taide-q4 -f - \
    && echo "[entrypoint] Created model taide-q4"

# 5. Test-load Q8_0; fall back to Q4_K_M on failure
MODEL_NAME=""
if OLLAMA_MODELS="$MODELS_DIR" ollama run taide-q8 "" --nowordwrap 2>/dev/null; then
    MODEL_NAME="taide-q8"
    echo "[entrypoint] Loaded Q8_0 model."
else
    echo "[entrypoint] WARNING: Q8_0 failed, falling back to Q4_K_M..." >&2
    if OLLAMA_MODELS="$MODELS_DIR" ollama run taide-q4 "" --nowordwrap 2>/dev/null; then
        MODEL_NAME="taide-q4"
        echo "[entrypoint] Loaded Q4_K_M model."
    else
        echo "[entrypoint] ERROR: Both models failed to load." >&2
        kill "$OLLAMA_PID"
        exit 1
    fi
fi

# 6. Start FastAPI in the background — trap above handles SIGTERM
export OLLAMA_MODELS="$MODELS_DIR"
export TAIDE_MODEL_NAME="$MODEL_NAME"
PORT="${PORT:-8080}"
echo "[entrypoint] Starting FastAPI with model=$MODEL_NAME port=$PORT"
uvicorn main:app --host 0.0.0.0 --port "$PORT" &
UVICORN_PID=$!

# Block until uvicorn exits (normal or via signal)
wait "$UVICORN_PID"
