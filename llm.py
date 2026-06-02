"""
llm.py – Duenne Adapter um die zwei LLM-SDKs.

Eine gemeinsame Schnittstelle (`complete_json`, `complete_text`) ueber zwei
unterschiedliche Response-Formate (Anthropic vs OpenAI-kompatibel-fuer-Grok).
Das ist die Stelle, an der spezifische SDK-Eigenheiten gekapselt werden,
damit Agenten beide Anbieter gleich ansprechen koennen.

Jeder Client zaehlt Tokens mit. Nach jedem Aufruf koennen die Counters
gelesen werden, damit der Agent sie ins Artefakt-/runs.jsonl-Log schreiben
kann.

KEINE Retry-Logik in Stufe 2. Wenn der Aufruf scheitert: Fehler hochreichen,
Orchestrator loggt ihn. Retry/Backoff kommt erst, wenn wir sehen, wo es
tatsaechlich knirscht.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# .env aus dem Projekt-Root laden, mit override=True damit eine leere
# Shell-Umgebungsvariable (z. B. ANTHROPIC_API_KEY='') unsere Werte nicht killt.
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env", override=True)


# ──────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> Any:
    """
    Findet das erste valide JSON-Array oder -Objekt im Antworttext.

    Manche Modelle wickeln JSON in Markdown-Code-Blocks; manche schreiben
    Vorrede. Wir nehmen den groesstmoeglichen Match, der parsbar ist.
    """
    # 1) Codeblock probieren
    block = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if block:
        try:
            return json.loads(block.group(1))
        except json.JSONDecodeError:
            pass

    # 2) Erstes [ ... ] oder { ... } greifen
    for opener, closer in [("[", "]"), ("{", "}")]:
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    # 3) Letzte Chance: alles parsen
    return json.loads(text)


# ──────────────────────────────────────────────────────────────────────────
# Grok (xAI)
# ──────────────────────────────────────────────────────────────────────────

class GrokClient:
    """
    Wrapper um die OpenAI-kompatible xAI-API.

    Modellnamen siehe https://docs.x.ai/docs/models – wir nutzen
    'grok-4-1-fast' als Default fuer billige, schnelle Bulk-Arbeit
    (Archivar, Faktenpruefer, Quiz-Master).
    """

    def __init__(self, model: str = "grok-4-1-fast", temperature: float = 0.2):
        from openai import OpenAI
        key = os.getenv("XAI_API_KEY")
        if not key:
            raise RuntimeError("XAI_API_KEY fehlt in .env")
        base = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        self._client = OpenAI(api_key=key, base_url=base)
        self.model = model
        self.temperature = temperature
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.calls = 0

    def complete_text(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=max_tokens,
        )
        self.calls += 1
        self.total_tokens_in += resp.usage.prompt_tokens
        self.total_tokens_out += resp.usage.completion_tokens
        return resp.choices[0].message.content

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> Any:
        """Wie complete_text, aber Antwort wird als JSON geparst."""
        raw = self.complete_text(system, user, max_tokens=max_tokens)
        return _extract_json(raw)


# ──────────────────────────────────────────────────────────────────────────
# Claude (Anthropic)
# ──────────────────────────────────────────────────────────────────────────

class ClaudeClient:
    """
    Wrapper um die Anthropic-API.

    Default 'claude-haiku-4-5' fuer billige Aufrufe; Sonnet/Opus
    werden vom Aufrufer ueber model= ueberschrieben (Autor: Sonnet,
    Lektor/Chefredakteur: Opus).
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        temperature: float = 0.4,
    ):
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY fehlt in .env")
        self._client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.temperature = temperature
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.calls = 0

    def complete_text(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
    ) -> str:
        resp = self._client.messages.create(
            model=self.model,
            system=system,
            max_tokens=max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": user}],
        )
        self.calls += 1
        self.total_tokens_in += resp.usage.input_tokens
        self.total_tokens_out += resp.usage.output_tokens
        # Claude liefert Content als Liste von Blocks – wir konkatenieren
        # die Text-Blocks (zukunftssicher gegenueber Tool-Use-Blocks).
        return "".join(block.text for block in resp.content if hasattr(block, "text"))

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> Any:
        raw = self.complete_text(system, user, max_tokens=max_tokens)
        return _extract_json(raw)
