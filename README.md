![CI](https://github.com/William-Yeh/localizing-taiwan-chinese/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
[![Agent Skills](https://img.shields.io/badge/agent--skills-compatible-blue)](https://agentskills.io)
[![GHCR](https://img.shields.io/badge/ghcr.io-localizing--taiwan--chinese-blue?logo=docker)](https://github.com/William-Yeh/localizing-taiwan-chinese/pkgs/container/localizing-taiwan-chinese)

# localizing-taiwan-chinese

Rewrite Chinese text into 純正台灣現代中文 using the TAIDE model (Gemma-3-TAIDE-12b) on a RunPod serverless GPU.

## Installation

### Recommended: `npx skills`

```bash
npx skills add William-Yeh/localizing-taiwan-chinese
```

### Manual installation

Copy the `skill/` directory into your agent's skill folder:

| Agent | Directory |
|-------|-----------|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` |
| Gemini CLI | `.gemini/skills/` |

## Prerequisites

Set `TAIDE_ENDPOINT_URL` in your environment (required):

```bash
export TAIDE_ENDPOINT_URL=https://<your-runpod-endpoint-url>
```

Optional tuning:

| Variable | Default | Purpose |
|---|---|---|
| `TAIDE_WARMUP_TIMEOUT` | `120` | Max seconds to wait for cold-start warm-up |
| `TAIDE_REQUEST_TIMEOUT` | `120` | Max seconds to wait for the localize response |

## Usage

After installing, try these prompts with your agent:

- `幫我把這段文字去大陸化：軟件下載後請確認版本`
- `localize the content of CHANGELOG.md into Taiwan Chinese`
- `/localize 請問您對這個問題有什么看法？`

### CLI

You can also run the script directly:

```bash
# Inline text
uv run skill/scripts/localize.py "軟件下載後請確認版本"

# From a file
cat myfile.txt | uv run skill/scripts/localize.py
```

## Cold start

If the RunPod endpoint is sleeping, the script prints `⏳ TAIDE endpoint warming up...` and polls with exponential backoff (2 → 4 → 8 → … → 60s cap) until ready or the warmup timeout is reached.

## Server

The Docker image (`ghcr.io/William-Yeh/localizing-taiwan-chinese`) runs Ollama with the TAIDE model on a RunPod Flex Worker. See `./server/` for the Dockerfile and entrypoint.
