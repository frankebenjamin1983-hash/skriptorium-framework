"""
tools/probe_keys.py – winziger Probe-Aufruf an beide APIs.

Pro Anbieter ein Aufruf mit ~10 Output-Tokens. Gesamtkosten erfahrungsgemaess
unter 1 Cent. Zweck: vor Stufe 2 verifizieren, dass

  - .env korrekt geladen wird
  - beide API-Keys gueltig sind
  - die SDKs richtig sprechen
  - Modellnamen erreichbar sind

Aufruf:
    python -m tools.probe_keys
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Repo-Root in sys.path, falls vom Tools-Ordner gestartet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv(override=True)  # .env hat Vorrang vor existierenden Umgebungsvariablen


def probe_grok() -> dict:
    """Grok via OpenAI-kompatibler API."""
    from openai import OpenAI
    key = os.getenv("XAI_API_KEY")
    base = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
    if not key:
        return {"ok": False, "error": "XAI_API_KEY fehlt in .env"}
    try:
        client = OpenAI(api_key=key, base_url=base)
        # grok-4-1-fast: günstigstes/schnellstes Grok-Modell – passt zum Archivar-Rolle
        resp = client.chat.completions.create(
            model="grok-4-1-fast",
            messages=[{"role": "user", "content": "Antworte nur mit dem Wort: pong"}],
            max_tokens=10,
            temperature=0,
        )
        return {
            "ok": True,
            "model": resp.model,
            "answer": resp.choices[0].message.content.strip(),
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def probe_claude() -> dict:
    """Claude via Anthropic-SDK."""
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY fehlt in .env"}
    try:
        client = anthropic.Anthropic(api_key=key)
        # claude-haiku-4-5 ist Anthropics aktueller Haiku – billigste Probe.
        # Falls dieser Name nicht greift, zeigt der Fehler die akzeptierten Modelle.
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": "Antworte nur mit dem Wort: pong"}],
        )
        return {
            "ok": True,
            "model": resp.model,
            "answer": resp.content[0].text.strip() if resp.content else "",
            "tokens_in": resp.usage.input_tokens,
            "tokens_out": resp.usage.output_tokens,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    print("Probe-Aufrufe an Stufe-2-APIs …\n")

    for label, fn in [("Grok (xAI)", probe_grok), ("Claude (Anthropic)", probe_claude)]:
        print(f"== {label} ==")
        result = fn()
        if result["ok"]:
            print(f"  OK    Modell:  {result['model']}")
            print(f"        Antwort: '{result['answer']}'")
            print(f"        Tokens:  {result['tokens_in']} in, {result['tokens_out']} out")
        else:
            print(f"  FEHLER: {result['error']}")
        print()


if __name__ == "__main__":
    main()
