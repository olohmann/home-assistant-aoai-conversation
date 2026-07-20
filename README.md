# Azure OpenAI Conversation for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that adds an
**Azure OpenAI / Azure AI Foundry**–backed conversation agent, AI Task entity,
speech‑to‑text (STT) and text‑to‑speech (TTS) — full parity with the built‑in
[OpenAI Conversation](https://www.home-assistant.io/integrations/openai_conversation/)
integration, but talking to your own Azure OpenAI resource.

It is a clean re‑implementation tracking the **latest** upstream OpenAI Conversation
integration (Responses API, config *subentries* architecture). The only meaningful
difference is how the OpenAI client is constructed: it points at your Azure OpenAI
resource's v1 API surface.

> **Home Assistant support:** latest release only (built and tested against
> **2026.7.2**). No backwards compatibility is provided.

## Features

- 💬 **Conversation agent** — control your home through Assist, with tool calling,
  streaming, web search, code interpreter and reasoning options (model dependent).
- 🧠 **AI Task** — `ai_task.generate_data` (structured output) and
  `ai_task.generate_image`. The image model field accepts a **custom Azure
  deployment name** (default `gpt-image-2`), so you can point it at your own
  image deployment.
- 🎙️ **Speech‑to‑Text** — via transcription deployments (e.g. `gpt-4o-mini-transcribe`).
- 🔊 **Text‑to‑Speech** — via TTS deployments (e.g. `gpt-4o-mini-tts`).

> **Removed actions.** The legacy `aoai_conversation.generate_content` and
> `aoai_conversation.generate_image` actions are **not supported** — calling either
> raises an error and logs a message directing you to the `ai_task.generate_data`
> and `ai_task.generate_image` actions instead.

## Requirements

- An **Azure AI Foundry / Azure OpenAI** resource in a region that supports the
  [Responses API](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/responses).
- A **chat model deployment** (e.g. `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5.x`).
- Optional deployments for STT, TTS and image generation, depending on which
  features you want to use.
- An **API key** for the resource (this integration uses API‑key authentication).

> **Deployment names are your model names.** In Azure, the "model" fields in this
> integration refer to your **deployment name**, which you choose when you deploy a
> model in Azure AI Foundry. Set the model fields to match your deployments.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category: *Integration*):
   `https://github.com/olohmann/home-assistant-aoai-conversation`.
2. Install **Azure OpenAI Conversation**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/aoai_conversation` into your Home Assistant
`config/custom_components/` directory and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Azure OpenAI
   Conversation**.
2. Enter:
   - **API key** — your Azure OpenAI resource API key.
   - **Endpoint** — your resource endpoint, e.g.
     `https://your-resource.services.ai.azure.com/`.
3. The integration creates four entities (subentries): Conversation, AI Task, STT
   and TTS. Configure each via **Configure** → the respective subentry. Set the
   model/deployment fields to match your Azure deployments.

To use the conversation agent, assign it to an
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
