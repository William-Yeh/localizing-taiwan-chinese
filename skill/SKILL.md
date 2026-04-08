---
name: localizing-taiwan-chinese
description: >
  Use when the user wants to rewrite or localize Chinese text into
  Taiwan Modern Chinese (純正台灣現代中文), or says "幫我修稿", "去大陸化",
  "localise this", or invokes /localize.
compatibility: Requires uv and TAIDE_ENDPOINT_URL env var pointing to the RunPod endpoint.
allowed-tools: Bash(uv:*)
metadata:
  author: William-Yeh
---

# localizing-taiwan-chinese

Rewrite Chinese text into 純正台灣現代中文 using the TAIDE model on RunPod.

## Usage

Requires `TAIDE_ENDPOINT_URL` in environment. Optional: `TAIDE_WARMUP_TIMEOUT` (default 120s), `TAIDE_REQUEST_TIMEOUT` (default 120s).

When the user says "幫我修稿", "去大陸化", "localise this", or invokes /localize:

1. Extract the Chinese text to rewrite from the user's message or the file they referenced.
2. Run:
   ```bash
   uv run skill/scripts/localize.py "<text>"
   ```
   Or for multi-line text, pipe it:
   ```bash
   echo "<text>" | uv run skill/scripts/localize.py
   ```
3. Display the output verbatim — do not post-process or rephrase the result.

## Cold start

If the RunPod endpoint is sleeping, the script prints `⏳ TAIDE endpoint warming up...`
and waits up to 120 seconds (exponential backoff, capped at 60s intervals). No action needed.

## What the model does

Rewrites input according to these rules:
- 用語轉換：大陸用語 → 台灣慣用語（軟件→軟體、視頻→影片、信息→訊息⋯⋯）
- 語法調整：台灣人習慣的表達方式
- 標點符號：台灣全形標點「」『』⋯⋯
- 括號：括號內無中文時用半形 (like this)
- 輸出：純文字，無解釋或開場白
