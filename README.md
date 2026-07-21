# Azure OpenAI Conversation for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that adds an
**Azure OpenAI / Azure AI Foundry**–backed conversation agent and AI Task entity,
plus **Azure AI Speech**–backed speech‑to‑text (STT) and text‑to‑speech (TTS).

The conversation/AI‑Task side tracks the **latest** upstream OpenAI Conversation
integration (Responses API, config *subentries* architecture) but points at your Azure
OpenAI resource. STT and TTS are **hard‑wired to Azure AI Speech** (neural voices,
e.g. German `de‑DE‑KatjaNeural`) via the Speech REST API — no OpenAI audio models.

> **Home Assistant support:** latest release only (built and tested against
> **2026.7.2**). No backwards compatibility is provided.

## Features

- 💬 **Conversation agent** (Azure OpenAI, or a **Microsoft Foundry Agent**) — control
  your home through Assist, with tool calling, streaming, web search, code interpreter
  and reasoning options (model dependent). Configured with **model + endpoint + API key**,
  or point it at a persistent **Foundry agent** (see below).
- 🧠 **AI Task** (Azure OpenAI) — `ai_task.generate_data` (structured output) and
  `ai_task.generate_image`. The image model field accepts a **custom Azure
  deployment name** (default `gpt-image-2`).
- 🎙️ **Speech‑to‑Text** (Azure AI Speech) — short‑audio recognition via the Speech
  REST API. Configured with **endpoint URI + API key + language**.
- 🔊 **Text‑to‑Speech** (Azure AI Speech) — neural voices via SSML. Configured with
  **endpoint URI + API key + voice** (+ optional output format, rate, pitch, style).

> **Removed actions.** The legacy `aoai_conversation.generate_content` and
> `aoai_conversation.generate_image` actions are **not supported** — calling either
> raises an error and logs a message directing you to the `ai_task.generate_data`
> and `ai_task.generate_image` actions instead.

## Requirements

- An **Azure AI Foundry / Azure OpenAI** resource in a region that supports the
  [Responses API](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/responses),
  with a **chat model deployment** (e.g. `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5.x`).
- For STT/TTS: an **Azure AI Speech** endpoint. A **multi‑service Azure AI Foundry
  resource exposes one key that works for both Azure OpenAI and Azure AI Speech**, so
  you can reuse the same key — you just point STT/TTS at the Speech endpoint
  (e.g. `https://your-resource.cognitiveservices.azure.com/`). A standalone Speech
  resource works too.
- **API keys** for the resource(s) — this integration uses API‑key authentication.

> **Endpoints & deployment names.** For conversation/AI‑Task, the "model" fields are
> your Azure **deployment names**. For STT/TTS you provide the **Speech endpoint URI**
> and **voice short name** (e.g. `de-DE-KatjaNeural`) directly, since the Speech
> endpoint differs per install.


## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category: *Integration*):
   `https://github.com/olohmann/home-assistant-aoai-conversation`.
2. Install **Azure OpenAI Conversation**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/aoai_conversation` into your Home Assistant
`config/custom_components/` directory and restart Home Assistant.

> The integration ships its own brand icon in `custom_components/aoai_conversation/brand/`
> (supported natively since HA 2026.3). It may take a browser refresh / HA restart to
> appear, as brand images are cached.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Azure OpenAI
   Conversation**.
2. Enter the **LLM connection** (Azure OpenAI):
   - **API key** — your Azure OpenAI resource API key.
   - **Endpoint** — your resource endpoint, e.g.
     `https://your-resource.services.ai.azure.com/`.
3. The integration creates four entities (subentries): **Conversation**, **AI Task**,
   **STT** and **TTS**. Configure each via **Configure** → the respective subentry:
   - **Conversation / AI Task** — set the model to your Azure **deployment name**.
   - **STT** (Azure AI Speech) — set the **endpoint URI**
     (e.g. `https://your-resource.cognitiveservices.azure.com/`), the **API key**, and
     the recognition **language** (e.g. `de-DE`).
   - **TTS** (Azure AI Speech) — set the **endpoint URI**, the **API key**, the
     **voice** short name (e.g. `de-DE-KatjaNeural`), and optionally output format,
     rate, pitch and speaking style.

> **Tip (single key).** With a multi‑service Azure AI Foundry resource, the STT/TTS
> API key is the same key you use for the LLM; only the Speech **endpoint URI** differs
> (`…cognitiveservices.azure.com`). Find neural voice names in the
> [Azure voice list](https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts).
>
> The integration accepts either a **custom‑subdomain** endpoint
> (`https://<name>.cognitiveservices.azure.com/`, the default for Azure AI Foundry /
> AI Services resources) or a **regional** Speech host
> (`https://<region>.tts.speech.microsoft.com/` / `…stt…`); the correct REST paths are
> appended automatically for each form.

### Use a Microsoft Foundry Agent (instead of a model)

A **Conversation** entity can route to a persistent **Microsoft Foundry agent** (Azure
AI Foundry Agent Service) instead of a plain chat‑model deployment. In the Conversation
subentry, leave **Model** empty and set:

- **Foundry agent project endpoint** — the project endpoint from the Foundry welcome
  screen, e.g. `https://your-resource.services.ai.azure.com/api/projects/your-project`.
- **Foundry agent name** — the name of your persistent agent.
- **Foundry agent version** — optional (defaults to the latest).

The same **API key** is reused (project endpoints accept API‑key auth). The agent is
called through the Responses API (`agent_reference`). Each config is either a **model**
or an **agent**, not both.

> **Device control in agent mode.** A persisted Foundry agent uses **only its own
> tools** — the Responses API does not accept request‑level tools when an agent is
> specified, so Home Assistant's Assist tools are **not** passed in agent mode. To let
> the agent control your home, enable Home Assistant's
> [**Model Context Protocol Server**](https://www.home-assistant.io/integrations/mcp_server/)
> and add it as an **MCP tool** on your agent in the Foundry portal. The agent then calls
> HA's tools server‑side. (The cloud agent must be able to reach your HA instance — e.g.
> via Home Assistant Cloud or a public/reverse‑proxied URL with a long‑lived token.)
> In plain **model** mode, HA's Assist tools are passed as usual and device control works
> out of the box.

To use the conversation agent, assign it (and the STT/TTS entities) to an
[Assist pipeline](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/).

## Development

This repo uses [`mise`](https://mise.jdx.dev/) to pin the toolchain (Python 3.14 +
[`uv`](https://docs.astral.sh/uv/)) and `uv` to manage the virtualenv.

```bash
mise install          # install Python 3.14 + uv
mise run sync         # uv sync — create .venv and install dev deps
mise run lint         # ruff check
mise run format       # ruff format
mise run test         # pytest
mise run check        # lint + format-check + test
```

Or directly with `uv`:

```bash
uv sync
uv run ruff check custom_components tests
uv run ruff format --check custom_components tests
uv run pytest
```

> Some Home Assistant dependencies (`conversation`, `ai_task`, `tts`) require native
> libraries to import in tests. On macOS: `brew install jpeg-turbo ffmpeg`. On
> Debian/Ubuntu: `sudo apt-get install libturbojpeg0 ffmpeg` (the CI workflow does
> this automatically).

### Local smoketest (live)

A standalone script validates the whole stack against your **real** Azure resources —
LLM, voice listing, TTS, and a TTS→STT round-trip — using the integration's actual
request code. All configuration comes from a **git-ignored `.env`** file; no secrets are
printed or committed.

```bash
cp .env.example .env      # then fill in your endpoints, keys, voice, etc.
mise run smoketest        # or: uv run python scripts/smoketest.py
```

It prints a per-check PASS/FAIL summary (and exits non-zero on failure), and saves the
synthesized audio under `smoketest-output/` (also git-ignored). The round-trip synthesizes
a German phrase as 16 kHz PCM WAV and feeds it back to STT, which also proves the
custom-domain `tts/` / `stt/` endpoint paths work end-to-end.

### CI

- **Validate** (`.github/workflows/validate.yaml`) — runs `hassfest` and HACS
  validation.
- **Lint & Test** (`.github/workflows/lint.yaml`) — runs ruff and pytest.

## Credits

Based on the Home Assistant core
[`openai_conversation`](https://github.com/home-assistant/core/tree/dev/homeassistant/components/openai_conversation)
integration (Apache‑2.0). Azure adaptation inspired by
[`joselcaguilar/azure-openai-ha`](https://github.com/joselcaguilar/azure-openai-ha).

## License

[Apache‑2.0](LICENSE).
