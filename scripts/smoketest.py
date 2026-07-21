#!/usr/bin/env python3
"""Live smoketest for the Azure OpenAI Conversation integration.

Reads configuration from a git-ignored ``.env`` file and exercises the *actual*
integration request code against your real Azure resources:

1. LLM (Azure OpenAI)   -- a minimal Responses API call (falls back to models.list)
2. Voices (Azure Speech) -- GET voices/list
3. TTS (Azure Speech)   -- synthesize a phrase and save the audio
4. STT round-trip        -- synthesize the phrase as 16 kHz PCM WAV, then recognize it

Usage:
    cp .env.example .env      # then fill in your values
    uv run python scripts/smoketest.py
    # or: mise run smoketest

No secrets are printed or committed.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

import httpx
import openai

# Make the custom_components package importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.aoai_conversation.client import (
    normalize_azure_endpoint,
)
from custom_components.aoai_conversation.speech import (
    async_list_voices,
    async_recognize,
    async_synthesize,
    build_ssml,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "smoketest-output"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _load_env() -> None:
    """Load .env if python-dotenv is available; otherwise rely on the environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print(f"{YELLOW}python-dotenv not installed; reading os.environ only.{RESET}")
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"{YELLOW}No .env file found at {env_path}; reading os.environ.{RESET}")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _speech_endpoint(kind: str) -> str:
    """Return the STT/TTS endpoint, falling back to the shared Speech endpoint."""
    return os.environ.get(f"AOAI_{kind}_ENDPOINT", "").strip() or _require(
        "AOAI_SPEECH_ENDPOINT"
    )


def _speech_key(kind: str) -> str:
    return os.environ.get(f"AOAI_{kind}_API_KEY", "").strip() or _require(
        "AOAI_SPEECH_API_KEY"
    )


async def check_llm() -> str:
    """Validate the Azure OpenAI connection with a tiny Responses call."""

    endpoint = _require("AOAI_LLM_ENDPOINT")
    api_key = _require("AOAI_LLM_API_KEY")
    model = _require("AOAI_LLM_CHAT_MODEL")

    client = openai.AsyncOpenAI(
        base_url=normalize_azure_endpoint(endpoint),
        api_key=api_key,
    )
    try:
        response = await client.responses.create(
            model=model,
            input="Reply with the single word: OK",
            max_output_tokens=16,
        )
        text = (response.output_text or "").strip()
        return f"model={model!r} responded: {text!r}"
    except openai.OpenAIError:
        # Fall back to a cheaper capability probe.
        models = await client.models.list()
        count = len(getattr(models, "data", []) or [])
        return f"responses.create unavailable; models.list returned {count} models"
    finally:
        await client.close()


async def check_foundry_agent() -> str:
    """Call a persistent Foundry agent via the Responses API (agent_reference)."""
    endpoint = os.environ.get("AOAI_AGENT_ENDPOINT", "").strip()
    agent_name = os.environ.get("AOAI_AGENT_NAME", "").strip()
    if not endpoint or not agent_name:
        return "skipped (set AOAI_AGENT_ENDPOINT and AOAI_AGENT_NAME to test)"

    api_key = os.environ.get("AOAI_AGENT_API_KEY", "").strip() or _require(
        "AOAI_LLM_API_KEY"
    )
    agent_reference: dict = {"type": "agent_reference", "name": agent_name}
    if version := os.environ.get("AOAI_AGENT_VERSION", "").strip():
        agent_reference["version"] = version

    client = openai.AsyncOpenAI(
        base_url=normalize_azure_endpoint(endpoint),
        api_key=api_key,
    )
    conversations_url = f"{normalize_azure_endpoint(endpoint)}conversations"
    try:
        # Create a server-side conversation (thread) and do a 2-turn exchange to
        # prove the agent retains context across turns.
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                conversations_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={},
                timeout=30.0,
            )
            resp.raise_for_status()
            conv_id = resp.json()["id"]

        extra = {"agent_reference": agent_reference, "conversation": conv_id}
        first = await client.responses.create(
            input="My favorite color is teal. Reply with the single word: OK.",
            extra_body=extra,
        )
        second = await client.responses.create(
            input="What is my favorite color? Reply with one word.",
            extra_body=extra,
        )
        return (
            f"agent={agent_name!r} thread={conv_id} "
            f"turn1={(first.output_text or '').strip()!r} "
            f"turn2={(second.output_text or '').strip()!r}"
        )
    finally:
        await client.close()


async def check_voices(client: httpx.AsyncClient) -> str:
    """List the neural voices and confirm the configured voice exists."""
    endpoint = _speech_endpoint("TTS")
    api_key = _speech_key("TTS")
    voice = os.environ.get("AOAI_TTS_VOICE", "de-DE-KatjaNeural").strip()

    voices = await async_list_voices(client, endpoint, api_key)
    names = {v.get("ShortName") for v in voices}
    present = voice in names
    marker = f"{GREEN}found{RESET}" if present else f"{YELLOW}NOT found{RESET}"
    return f"{len(voices)} voices; configured voice {voice!r} {marker}"


async def check_tts(client: httpx.AsyncClient) -> str:
    """Synthesize the phrase and save the audio file."""
    endpoint = _speech_endpoint("TTS")
    api_key = _speech_key("TTS")
    voice = os.environ.get("AOAI_TTS_VOICE", "de-DE-KatjaNeural").strip()
    output_format = os.environ.get(
        "AOAI_TTS_OUTPUT_FORMAT", "audio-24khz-48kbitrate-mono-mp3"
    ).strip()
    language = os.environ.get("AOAI_STT_LANGUAGE", "de-DE").strip()
    phrase = os.environ.get(
        "AOAI_SMOKETEST_PHRASE", "Schalte das Licht im Wohnzimmer ein."
    )

    ssml = build_ssml(phrase, voice, language)
    audio = await async_synthesize(client, endpoint, api_key, ssml, output_format)

    OUTPUT_DIR.mkdir(exist_ok=True)
    ext = (
        "mp3"
        if "mp3" in output_format
        else ("wav" if "riff" in output_format else "bin")
    )
    out = OUTPUT_DIR / f"tts-sample.{ext}"
    out.write_bytes(audio)
    return f"{len(audio)} bytes ({output_format}) saved to {out}"


async def check_stt_roundtrip(client: httpx.AsyncClient) -> str:
    """Synthesize the phrase as 16 kHz PCM WAV, then recognize it back."""
    tts_endpoint = _speech_endpoint("TTS")
    tts_key = _speech_key("TTS")
    stt_endpoint = _speech_endpoint("STT")
    stt_key = _speech_key("STT")
    voice = os.environ.get("AOAI_TTS_VOICE", "de-DE-KatjaNeural").strip()
    language = os.environ.get("AOAI_STT_LANGUAGE", "de-DE").strip()
    phrase = os.environ.get(
        "AOAI_SMOKETEST_PHRASE", "Schalte das Licht im Wohnzimmer ein."
    )

    ssml = build_ssml(phrase, voice, language)
    wav = await async_synthesize(
        client, tts_endpoint, tts_key, ssml, "riff-16khz-16bit-mono-pcm"
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "stt-input.wav").write_bytes(wav)

    text = await async_recognize(client, stt_endpoint, stt_key, wav, language)
    if not text:
        raise RuntimeError("STT returned no transcript")

    def _norm(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum())

    match = "≈ match" if _norm(text) == _norm(phrase) else "differs (see below)"
    return f"said {phrase!r} -> heard {text!r} [{match}]"


async def main() -> int:
    _load_env()
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"{BOLD}Azure OpenAI Conversation -- local smoketest{RESET}\n")

    results: list[tuple[str, bool, str]] = []

    # LLM check (no shared httpx client needed).
    try:
        detail = await check_llm()
        results.append(("LLM (Azure OpenAI)", True, detail))
    except Exception as err:
        results.append(("LLM (Azure OpenAI)", False, str(err)))

    # Foundry agent check (optional; skipped unless configured).
    try:
        detail = await check_foundry_agent()
        results.append(("Foundry agent", True, detail))
    except Exception as err:
        results.append(("Foundry agent", False, str(err)))

    # Speech checks share one httpx client.
    async with httpx.AsyncClient() as client:
        for name, coro in (
            ("Voices (Azure Speech)", check_voices),
            ("TTS (Azure Speech)", check_tts),
            ("STT round-trip (Azure Speech)", check_stt_roundtrip),
        ):
            try:
                detail = await coro(client)
                results.append((name, True, detail))
            except Exception as err:
                results.append((name, False, str(err)))

    print(f"\n{BOLD}Results{RESET}")
    all_ok = True
    for name, ok, detail in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {name}: {detail}")
        all_ok = all_ok and ok

    print()
    if all_ok:
        print(f"{GREEN}{BOLD}All checks passed.{RESET}")
        return 0
    print(f"{RED}{BOLD}Some checks failed.{RESET}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
