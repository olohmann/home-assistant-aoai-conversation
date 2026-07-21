# AGENTS.md

Context and conventions for AI agents working on **home-assistant-aoai-conversation**,
a custom Home Assistant integration (domain `aoai_conversation`).

## What this is

A custom HA integration providing:
- **Conversation** + **AI Task** → **Azure OpenAI** (Responses API, `openai` lib).
- **STT** + **TTS** → **Azure AI Speech** (plain REST, no SDK).

It is a port of HA core's `openai_conversation`, with the Azure delta kept **surgically
isolated** so upstream syncs stay easy. Latest HA only; **no backwards compatibility**.

## Golden rules (read before changing anything)

1. **Pin `openai==2.21.0`.** Released HA (through 2026.7.x) constrains `openai==2.21.0`;
   only the unreleased `dev` branch uses 2.45.0. Using 2.45.0 makes HA fail to install
   the integration (`RequirementsNotFound`). Keep `manifest.json` requirements **and**
   `pyproject.toml` `[project].dependencies` on `openai==2.21.0`.
2. **Keep the Azure delta isolated.** LLM client lives in `client.py`; Speech REST lives
   in `speech.py`; entity/conversation/ai_task are ~verbatim upstream. Don't scatter
   Azure specifics into ported files.
3. **STT/TTS are hard-wired to Azure Speech** — no OpenAI audio models, no toggles.
4. **Config subentry architecture** (parent connection entry + per-entity subentries).
   Don't reintroduce the legacy flat single-entry design.

## Architecture & config model

- **Parent config entry** = the Azure OpenAI (LLM) connection: `endpoint` + `api_key`.
  Chat model (deployment name) is per-subentry.
- **Subentries**: `conversation`, `ai_task_data`, `stt`, `tts`.
  - Conversation / AI Task read `chat_model` (= Azure **deployment name**).
  - **Conversation** may instead target a **Microsoft Foundry agent**: set
    `agent_name` + `agent_endpoint` (project endpoint) — exactly one of model/agent.
    The entity calls the Responses API with `extra_body={"agent_reference": {...}}` and
    no `model`, against a dedicated client for the project endpoint (same API key).
    **Agent mode sends NO `tools`** (the Responses API rejects request-level tools when
    an agent is specified); device control is wired on the agent side via HA's MCP
    Server. **Model mode** still passes HA's Assist tools + all model options as usual.
  - **STT** subentry carries its own `stt_endpoint` + `stt_api_key` + `stt_language`.
  - **TTS** subentry carries its own `tts_endpoint` + `tts_api_key` + `tts_voice`
    (+ output format / rate / pitch / style).
- `entry.runtime_data` = the `openai.AsyncOpenAI` client (used only by conversation/AI Task).
- Removed `generate_content` / `generate_image` services intentionally **raise** and log,
  pointing users to `ai_task.*`.

## Azure specifics (verified, non-obvious)

- **Azure OpenAI client** (`client.py`): `AsyncOpenAI(base_url=normalize_azure_endpoint(ep),
  api_key=..., default_query={"api-version": "preview"})`. Endpoint normalized to
  `https://<res>.services.ai.azure.com/openai/v1/`.
- **Azure Speech endpoint URLs are host-aware** (`speech.py::speech_url`):
  - Custom-subdomain host (`*.cognitiveservices.azure.com`) needs a **`tts/`** or
    **`stt/`** path prefix.
  - Regional host (`*.tts|stt.speech.microsoft.com`) uses **bare** paths.
  - TTS: `{base}/[tts/]cognitiveservices/v1`; voices: `.../voices/list`;
    STT: `{base}/[stt/]speech/recognition/conversation/cognitiveservices/v1`.
- Auth header for Speech: `Ocp-Apim-Subscription-Key`. TTS = SSML POST; STT = short-audio
  one-shot WAV (PCM 16 kHz mono) → `DisplayText`.
- `speech.py` async fns take an **`httpx.AsyncClient`** (not `hass`); entities pass
  `get_async_client(self.hass)`. Keep it that way (lets the smoketest run without HA).

## Dev environment

- **mise** (Python 3.14) + **uv**. Never use pip/pyenv/venv directly.
- Tasks: `mise run sync | lint | format | format-check | test | check | smoketest`.
- Or: `uv sync`, `uv run pytest`, `uv run ruff check custom_components tests scripts`,
  `uv run ruff format --check ...`.

## Testing

- Importing HA `conversation`/`ai_task`/`tts` in tests requires **native deps**:
  macOS `brew install jpeg-turbo ffmpeg`; Debian `apt-get install libturbojpeg0 ffmpeg`.
  Python deps (`PyTurboJPEG`, `ha-ffmpeg`, `hassil`, `home-assistant-intents`, `mutagen`)
  are already in the dev group.
- Tests must set up the `homeassistant` core component (registers `exposed_entities`),
  else `conversation` setup fails with `KeyError: 'homeassistant.exposed_entities'`
  (see `tests/conftest.py` autouse fixture).
- Speech tests pass an `httpx.MockTransport` client directly; entity TTS test patches
  `tts.get_async_client`.

## Live smoketest

- `scripts/smoketest.py` (or `mise run smoketest`) exercises the real request code
  against live Azure: LLM, voices, TTS, and a TTS→STT round-trip.
- Config from a **git-ignored `.env`** (`.env.example` is the template). Never commit
  secrets; audio lands in the git-ignored `smoketest-output/`.

## Brand icon

- Local brand images in `custom_components/aoai_conversation/brand/` (`icon.png` 256²,
  `icon@2x.png` 512²), supported since HA 2026.3 — no PR to `home-assistant/brands`.
- Must be **original** (no OpenAI / Azure / Microsoft / Home Assistant logos — trademark).

## Release process

1. Bump `version` in `manifest.json` (calendar-ish, e.g. `2026.7.1`).
2. Commit, then `gh release create vX.Y.Z --target main --title vX.Y.Z --notes "…"`.
3. Keep the tag (minus `v`) equal to the manifest `version` so HACS stays tidy.

## Commit conventions

- Subject: `<area>: <short imperative>` (e.g. `feat:`, `fix:`, `speech:`).
- Include the trailer:
  `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## Layout

```
custom_components/aoai_conversation/
  __init__.py        setup, services (removed ones error), client wiring
  client.py          Azure OpenAI client + endpoint normalization
  speech.py          Azure Speech REST (host-aware URLs, synth/voices/recognize)
  config_flow.py     parent (LLM) + subentry flows (conversation/ai_task/stt/tts)
  entity.py          shared OpenAI Responses base (conversation + ai_task)
  conversation.py ai_task.py stt.py tts.py
  const.py strings.json translations/en.json icons.json services.yaml manifest.json
  brand/icon.png brand/icon@2x.png
tests/               pytest suite
scripts/smoketest.py live .env-driven smoketest
```
