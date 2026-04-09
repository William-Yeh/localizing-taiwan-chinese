import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=120.0)
    yield
    await http_client.aclose()


app = FastAPI(lifespan=lifespan)

MODEL_NAME    = os.environ.get("TAIDE_MODEL_NAME", "taide-q8")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
TEMPERATURE   = float(os.environ.get("TAIDE_TEMPERATURE", "0.1"))

SYSTEM_PROMPT = (
    "你是專業的台灣中文編輯。請將以下文字改寫為純正台灣現代中文，遵守以下規則：\n\n"
    "1. 用語轉換：將大陸用語改為台灣慣用語。"
    "常見對照：軟件→軟體、硬件→硬體、程序→程式、視頻→影片、"
    "網絡→網路、信息→訊息、鏈接→連結、文件→檔案、手機→手機。\n"
    "2. 語法調整：使用台灣人習慣的表達方式。\n"
    "3. 格式規範：僅輸出修飾後的純文字，不含任何解釋、開場白或結束語。\n"
    "4. 標點符號：使用台灣習慣的全形標點符號，如 「」『』⋯⋯。\n"
    "5. 括號：括號內無中文字時使用半形括號，如 (English terms)。\n\n"
    "直接輸出修改後的文字，不要加任何說明。"
)


class LocalizeRequest(BaseModel):
    text: str


class HealthResponse(BaseModel):
    status: str
    model: str


class LocalizeResponse(BaseModel):
    result: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/localize", response_model=LocalizeResponse)
async def localize(req: LocalizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    assert http_client is not None, "http_client not initialised — lifespan not running"
    try:
        resp = await http_client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": req.text,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": TEMPERATURE},
            },
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama error: {exc.response.status_code}")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to connect to Ollama: {exc}")

    return {"result": resp.json()["response"]}
