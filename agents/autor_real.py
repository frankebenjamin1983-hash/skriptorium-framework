"""
agents/autor_real.py – Echter Autor (Stufe 2).

Liest Kapitel-Spezifikation aus der Lektor-Outline + alle Karten, deren
IDs darin stehen, und laesst Claude Sonnet daraus den Kapitel-Volltext
schreiben. Style-Guide wird als System-Prompt-Bestandteil mitgegeben.

Modell: claude-sonnet-4-5 (gute Didaktik, vertraegliche Kosten).

Konstruktor-Parameter:
  chapter_id: nur EIN Kapitel verarbeiten (Test- bzw. Iterationsmodus).
              None = alle Kapitel der Outline.

Stufe-3-Naht: Iteration ueber Kapitel kommt in den Orchestrator,
sobald Fan-out und Parallelitaet stehen.
"""

from __future__ import annotations

import json
from pathlib import Path

from llm import ClaudeClient
from schemas import AutorInput, AutorOutput, Card, ChapterDraftRef, read_json

from .base import Agent


SYSTEM_PROMPT_TEMPLATE = """\
Du schreibst Kapitel fuer ein deutsches Python-Lehrbuch nach diesem Style-Guide:

══════════════ STYLE-GUIDE ══════════════
{style_guide}
══════════════════════════════════════════

Du bekommst:
- Kapitel-Spezifikation (Titel, Teil, Lernziele)
- Wissens-Karten als JSON-Array (id, topic, subtopic, source, content)

Schreibe den Kapitel-Volltext als reines Markdown, exakt nach Style-Guide-
Abschnitt "2. Aufbau eines Kapitels":

  1. Lernziele     (## H2 "Lernziele", uebernimmst die Liste vom Briefing,
                    ggf. leicht aufgeraeumt)
  2. Einstieg      (## H2 "Einstieg", 1 Absatz, max 6 Saetze)
  3. Hauptteil     (mehrere ## H2-Abschnitte. Innerhalb: ### H3 fuer
                    Konzept/Beispiel/Stolperfalle. Code-Bloecke nach
                    Style-Guide Abschnitt 3.)
  4. Zum Mitnehmen (## H2 "Zum Mitnehmen", 3-5 Bullets, je 1-2 Saetze)

Reihenfolge der Abschnitte: Grundkonzept zuerst, Erweiterungen danach.
Dokumentation (Docstrings) gehoert direkt nach "Funktionen definieren",
nicht ans Kapitelende.

Pflichten:
- TONALITAET wie Style-Guide: sachlich, knapp, leichter ostwestfaelischer
  Zynismus wo natuerlich, keine Werbe-Sprache, keine Ausrufezeichen am
  Satzende.
- ALLE Aussagen muessen sich auf die Wissens-Karten stuetzen. Fuer jede
  nicht-triviale Aussage eine Fussnote. KRITISCH: Die Fussnote-ID MUSS
  EXAKT der id-Feld-Wert aus dem JSON sein (z. B. source_a__0003),
  NICHT abgekuerzt. Syntax im Text: [^source_a__0003]
  Sammelliste am Ende:
    [^source_a__0003]: source_a__0003
  Falsch: [^card_003] – das ist eine erfundene ID.
  Richtig: [^source_a__0003] – exakt die id aus den Karten.
- KEINE Aussagen erfinden, die nicht in den Karten stehen.
- Code-Beispiele nur, wenn sie aus den Karten kommen ODER wenn sie eine
  Karte direkt illustrieren. Max 15 Zeilen pro Block.
- Type Hints ab Kapitel 5 ja (Kapitel-ID >= 05), davor weglassen.

Antworte mit dem reinen Markdown-Volltext. Kein "Hier ist das Kapitel:"
davor, keine Erklaerung dahinter.
"""


class RealAutor(Agent):
    INPUT_SCHEMA = AutorInput
    OUTPUT_SCHEMA = AutorOutput

    def __init__(
        self,
        chapter_id: str | None = None,
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.5,
        max_output_tokens: int = 5000,
    ):
        super().__init__("Autor")
        self.client = ClaudeClient(model=model, temperature=temperature)
        self.chapter_id = chapter_id
        self.max_output_tokens = max_output_tokens
        # Style-Guide aus Projekt-Root laden – einmal, nicht pro Kapitel
        sg_path = Path(__file__).resolve().parent.parent / "style_guide.md"
        self.style_guide = sg_path.read_text(encoding="utf-8") if sg_path.exists() else ""
        # .format() faellt bei den vielen {} in Style-Guide/JSON-Beispiel auf die Nase
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{style_guide}", self.style_guide)

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        chapters = context["chapters"]
        all_cards: list[Card] = read_json(Path(context["cards_path"]), model=Card)
        cards_by_id = {c.id: c for c in all_cards}

        # Filter wenn nur ein Kapitel gewuenscht
        if self.chapter_id is not None:
            chapters = [ch for ch in chapters if ch["id"] == self.chapter_id]
            if not chapters:
                raise ValueError(
                    f"Kapitel-ID '{self.chapter_id}' nicht in Outline."
                )

        out_dir = artifacts_dir / "chapters"
        out_dir.mkdir(exist_ok=True)

        drafts: list[ChapterDraftRef] = []
        for ch in chapters:
            ch_cards = [cards_by_id[cid] for cid in ch["card_ids"] if cid in cards_by_id]
            print(f"  -> Kapitel {ch['id']}: '{ch['title']}' "
                  f"({len(ch_cards)} Karten)")

            body = self._write_chapter(ch, ch_cards)
            path = out_dir / f"{ch['id']}.md"
            path.write_text(body, encoding="utf-8")
            drafts.append(ChapterDraftRef(
                id=ch["id"], path=str(path), chars=len(body),
            ))
            print(f"     fertig ({len(body):,} Zeichen, "
                  f"in={self.client.total_tokens_in} out={self.client.total_tokens_out})")

        return {
            "chapters_dir": str(out_dir),
            "chapter_drafts": [d.model_dump() for d in drafts],
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _write_chapter(self, chapter_spec: dict, cards: list[Card]) -> str:
        """Ein einzelner Sonnet-Call pro Kapitel."""
        # Karten als kompakte JSON-Pakete fuer Claude
        card_pack = [
            {
                "id": c.id,
                "topic": c.topic,
                "subtopic": c.subtopic,
                "source": c.source,
                "level": c.level,
                "content": c.content_md,
            }
            for c in cards
        ]

        lz = "\n".join(f"- {x}" for x in chapter_spec.get("learning_objectives", []))
        topics = ", ".join(chapter_spec.get("topics", [chapter_spec.get("topic", "")]))

        user_msg = (
            f"# Kapitel-Spezifikation\n\n"
            f"- Titel: **{chapter_spec.get('title', '?')}**\n"
            f"- Teil: {chapter_spec.get('part', '?')}\n"
            f"- Themen: {topics}\n"
            f"- Lernziele:\n{lz}\n\n"
            f"# Wissens-Karten ({len(cards)})\n\n"
            f"```json\n{json.dumps(card_pack, ensure_ascii=False, indent=2)}\n```\n"
        )

        return self.client.complete_text(
            self.system_prompt, user_msg, max_tokens=self.max_output_tokens,
        )
