"""
agents/archivar_real.py – Echter Archivar (Stufe 2).

Liest die heuristisch erzeugten Karten aus artifacts/cards_real.json
(Output von tools/build_real_cards.py) und schaerft pro Karte mit Grok:
  - topic       (deutscher, kanonischer Themenname statt Roh-Heading)
  - subtopic    (was genau in der Karte steckt)
  - level       (eingeschaetzt aus content_md, nicht aus dem Pfad)

UNVERAENDERT bleiben: id, source, content_md, role, track.
So bleibt die Lineage zur heuristischen Vorstufe nachvollziehbar.

Kostenkontrolle:
  - Default: kein Sample-Limit, alle Karten verarbeiten
  - sample=N im Konstruktor verarbeitet nur die ersten N Karten (Test)
  - batch_size: wie viele Karten gemeinsam an Grok geschickt werden
"""

from __future__ import annotations

import json
from pathlib import Path

from llm import GrokClient
from schemas import ArchivarOutput, Card, read_json, write_json

from .base import Agent


SYSTEM_PROMPT = """\
Du bist ein praeziser Wissens-Archivar fuer ein deutsches Python-Lehrbuch.

Du bekommst eine Liste von Mini-Karten als JSON. Jede Karte hat:
  id, topic (roh, evtl. Englisch), subtopic, content_md

Deine Aufgabe: pro Karte saubere Metadaten erzeugen.

Antworte mit reinem JSON-Array. Pro Karte ein Objekt:
{
  "id":       (unveraendert uebernehmen),
  "topic":    griffiger deutscher Themenname, max. 4 Woerter,
              z. B. "Funktionen", "Listen", "Klassen und Objekte"
              (nicht das Roh-Heading uebernehmen, falls es englisch
              oder zu lang/zu eng ist),
  "subtopic": was genau in der Karte steckt, max. 6 Woerter,
              z. B. "Default-Argumente", "List Comprehensions",
              "Vererbung und super()",
  "level":   "beginner" | "intermediate" | "advanced"
              (eingeschaetzt aus content_md, nicht aus dem topic-Namen!
              Faustregel: beginner = Erst-Begegnung mit dem Konzept,
              intermediate = baut auf Grundlagen auf, advanced =
              Eigenheiten, Idiome, Performance-Themen, Metaprogrammierung)
}

Antworte ausschliesslich mit dem JSON-Array. Keine Erklaerung, keine
Code-Block-Marker, kein Fliesstext davor oder dahinter.
"""


class RealArchivar(Agent):
    """Grok-getriebener Archivar."""

    INPUT_SCHEMA = None       # liest direkt von der Platte
    OUTPUT_SCHEMA = ArchivarOutput

    def __init__(
        self,
        source_cards_path: Path | str | None = None,
        sample: int | None = None,
        batch_size: int = 20,
        model: str = "grok-4-1-fast",
    ):
        super().__init__("Archivar")
        self.source_cards_path = (
            Path(source_cards_path)
            if source_cards_path
            else Path(__file__).resolve().parent.parent / "artifacts" / "cards_real.json"
        )
        self.sample = sample
        self.batch_size = batch_size
        self.client = GrokClient(model=model)

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        if not self.source_cards_path.exists():
            raise FileNotFoundError(
                f"Quell-Karten fehlen: {self.source_cards_path}. "
                "Erst 'python -m tools.build_real_cards' laufen lassen."
            )

        raw_cards: list[Card] = read_json(self.source_cards_path, model=Card)
        if self.sample is not None:
            raw_cards = raw_cards[: self.sample]
        print(f"  -> {len(raw_cards)} Karten zu verarbeiten "
              f"(batches a {self.batch_size}) ...")

        enriched: list[Card] = []
        cards_by_id = {c.id: c for c in raw_cards}

        for i in range(0, len(raw_cards), self.batch_size):
            batch = raw_cards[i:i + self.batch_size]
            try:
                refinements = self._refine_batch(batch)
            except Exception as exc:
                print(f"  [{i:>4}-{i+len(batch):>4}] FEHLER: {exc} (Batch uebersprungen)")
                enriched.extend(batch)   # Fallback: rohe Karten behalten
                continue

            # Refinements mit Original mergen: nur topic/subtopic/level
            # uebernehmen, Rest behalten.
            updated = self._merge(refinements, cards_by_id)
            enriched.extend(updated)
            print(f"  [{i:>4}-{i+len(batch):>4}] ok "
                  f"(in={self.client.total_tokens_in} out={self.client.total_tokens_out})")

        out = artifacts_dir / "cards.json"
        write_json(out, enriched, model=Card)

        return {
            "cards_path": str(out),
            "cards_count": len(enriched),
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _refine_batch(self, batch: list[Card]) -> list[dict]:
        """Schickt einen Batch an Grok und parst das Ergebnis."""
        # Wir senden nur was Grok braucht, nicht den ganzen content_md
        # ungekuerzt – das spart Tokens.
        payload = [
            {
                "id": c.id,
                "topic": c.topic,
                "subtopic": c.subtopic,
                "content_md": c.content_md[:600],   # 600 Zeichen reichen fuer Klassifikation
            }
            for c in batch
        ]
        user_msg = json.dumps(payload, ensure_ascii=False)
        result = self.client.complete_json(SYSTEM_PROMPT, user_msg, max_tokens=2000)
        if not isinstance(result, list):
            raise ValueError(f"Grok gab kein JSON-Array zurueck: {type(result).__name__}")
        return result

    def _merge(self, refinements: list[dict], cards_by_id: dict[str, Card]) -> list[Card]:
        """Refinements ueber die Original-Karten legen."""
        merged: list[Card] = []
        for r in refinements:
            cid = r.get("id")
            original = cards_by_id.get(cid)
            if original is None:
                # Grok hat eine id erfunden – ueberspringen
                continue
            merged.append(Card(
                id=original.id,
                topic=str(r.get("topic", original.topic)).strip() or original.topic,
                subtopic=str(r.get("subtopic", original.subtopic)).strip() or original.subtopic,
                level=str(r.get("level", original.level)).strip() or original.level,
                source=original.source,
                content_md=original.content_md,
                role=original.role,
                track=original.track,
            ))
        return merged
