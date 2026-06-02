"""
agents/lektor_real.py – Echter Lektor (Stufe 2).

Liest die konsolidierte cards.json (Output von Archivar + Konsolidierung),
filtert auf Python-Kernmaterial (role=primary, kein __nicht_python__ /
__example__) und laesst Claude Sonnet daraus eine Buchstruktur entwerfen:
Teile (4-6), Kapitel (15-25), Lernziele pro Kapitel.

Claude bekommt einen kompakten Themen-Ueberblick (Topic + Subtopic-Sample
+ Level-Verteilung), nicht die Karten-Inhalte – das spart Tokens, weil
zur Strukturplanung der genaue Wortlaut nicht noetig ist.

Modell: claude-sonnet-4-5 (gute Didaktik, deutlich guenstiger als Opus).
Wer eine besonders durchdachte Struktur will, kann beim Konstruktor
model='claude-opus-4-5' setzen.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from llm import ClaudeClient
from schemas import (
    Card, Chapter, LektorInput, LektorOutput, Outline, read_json, write_json,
)

from .base import Agent


SYSTEM_PROMPT = """\
Du bist Lektor eines deutschen Python-Lehrbuchs vom Anfaenger zum Profi.

Du bekommst eine Themen-Liste aus extrahiertem Lehrmaterial: pro Thema
Anzahl Karten, Level-Verteilung und ein paar Beispiel-Subtopics.

Aufgabe: entwirf die Buchstruktur.

Regeln:
- 4-6 Teile (Teil I, II, III, ...), thematische Klammern
- 15-25 Kapitel insgesamt
- Lernkurve vom Einfachen zum Komplexen, am Anfang Grundlagen
- Ein Kapitel kann MEHRERE verwandte Themen abdecken
  (z. B. "Variablen, Datentypen, Operatoren" -> Kapitel "Grundbausteine")
- Themen-Namen in topics[] muessen EXAKT so heissen wie in der Vorlage
  (nicht uebersetzen, nicht umformulieren)
- Pro Kapitel 3-5 konkrete Lernziele in ICH-FORM:
  "Funktionen mit Default-Argumenten definieren",
  "Vererbung mit super() einsetzen"
- Stil: sachlich-didaktisch, keine Werbe-Sprache, keine Ausrufezeichen

Antwortformat: REINES JSON-Objekt. Keine Code-Block-Marker, keine
Erklaerung davor oder dahinter.

{
  "book_title": "Kurzer Buchtitel (max 6 Woerter)",
  "subtitle": "Untertitel mit Tonalitaet (max 12 Woerter)",
  "parts": [
    {
      "title": "Teil I: ...",
      "chapters": [
        {
          "title": "Kapitel-Titel (4-6 Woerter)",
          "topics": ["Variablen", "Datentypen"],
          "learning_objectives": [
            "Erstes Lernziel ...",
            "Zweites Lernziel ...",
            "Drittes Lernziel ..."
          ]
        }
      ]
    }
  ]
}
"""


# Topics, die NICHT ins Buch gehoeren
EXCLUDED_TOPICS = {"__nicht_python__", "__example__"}


class RealLektor(Agent):
    INPUT_SCHEMA = LektorInput
    OUTPUT_SCHEMA = LektorOutput

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.4,
        subtopic_sample: int = 8,
    ):
        super().__init__("Lektor")
        self.client = ClaudeClient(model=model, temperature=temperature)
        self.subtopic_sample = subtopic_sample

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        all_cards: list[Card] = read_json(Path(context["cards_path"]), model=Card)

        # Nur Python-Kernmaterial fuer die Strukturplanung
        relevant = [
            c for c in all_cards
            if c.role == "primary" and c.topic not in EXCLUDED_TOPICS
        ]
        print(f"  -> {len(relevant)} primary-Python-Karten verteilt auf "
              f"{len(set(c.topic for c in relevant))} Topics")

        topic_summary = self._build_topic_summary(relevant)
        print(f"  -> Themen-Briefing an {self.client.model} "
              f"({len(topic_summary)} Zeichen)")

        response = self.client.complete_json(
            SYSTEM_PROMPT, topic_summary, max_tokens=4000,
        )

        if not isinstance(response, dict) or "parts" not in response:
            raise ValueError(
                f"Claude lieferte unerwartetes Format: keys={list(response)[:10] if isinstance(response, dict) else type(response).__name__}"
            )

        # Strukturierte Antwort -> flache Chapter-Liste mit Card-IDs
        chapters = self._translate_to_chapters(response, relevant)

        outline = Outline(
            book_title=response.get("book_title", "PyCompendium"),
            language="de",
            chapters=chapters,
        )
        # subtitle bewahren wir zusaetzlich, schmuggeln ihn als Kommentar in
        # outline.json (nicht im strikt validierten Modell)
        out = artifacts_dir / "outline.json"
        outline_dict = outline.model_dump()
        if "subtitle" in response:
            outline_dict["subtitle"] = response["subtitle"]
        out.write_text(json.dumps(outline_dict, ensure_ascii=False, indent=2),
                       encoding="utf-8")

        print(f"  -> {len(chapters)} Kapitel in "
              f"{len(set(c.part for c in chapters))} Teilen")

        return {
            "outline_path": str(out),
            "chapters": [c.model_dump() for c in chapters],
            "chapter_count": len(chapters),
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _build_topic_summary(self, cards: list[Card]) -> str:
        """Kompakter Themen-Ueberblick fuer Claude (ohne Karten-Volltexte)."""
        per_topic: dict[str, dict] = defaultdict(
            lambda: {"subtopics": set(), "levels": Counter(), "count": 0}
        )
        for c in cards:
            d = per_topic[c.topic]
            d["subtopics"].add(c.subtopic)
            d["levels"][c.level] += 1
            d["count"] += 1

        lines: list[str] = ["# Verfuegbare Themen\n"]
        for topic in sorted(per_topic, key=lambda t: -per_topic[t]["count"]):
            d = per_topic[topic]
            levels_str = ", ".join(f"{n} {lvl}" for lvl, n in d["levels"].most_common())
            lines.append(f"\n## {topic}  ({d['count']} Karten | {levels_str})")
            for sub in sorted(d["subtopics"])[: self.subtopic_sample]:
                lines.append(f"  - {sub}")
            if len(d["subtopics"]) > self.subtopic_sample:
                lines.append(f"  - ... und {len(d['subtopics']) - self.subtopic_sample} weitere")
        return "\n".join(lines)

    def _translate_to_chapters(
        self,
        response: dict,
        relevant_cards: list[Card],
    ) -> list[Chapter]:
        """Claude-Output in Chapter-Liste mit Card-IDs uebersetzen."""
        cards_by_topic: dict[str, list[Card]] = defaultdict(list)
        for c in relevant_cards:
            cards_by_topic[c.topic].append(c)

        chapters: list[Chapter] = []
        ch_counter = 0
        for part in response.get("parts", []):
            part_title = part.get("title", "Unbenannter Teil")
            for ch in part.get("chapters", []):
                ch_counter += 1
                topics = ch.get("topics", [])
                # Karten fuer alle in diesem Kapitel genannten Topics einsammeln
                card_ids: list[str] = []
                for t in topics:
                    matches = cards_by_topic.get(t, [])
                    if not matches:
                        # Claude hat ein Topic erfunden – nur warnen
                        print(f"  WARN: Topic '{t}' (Kapitel '{ch.get('title')}')"
                              f" ist nicht in den Karten")
                        continue
                    card_ids.extend(c.id for c in matches)

                chapters.append(Chapter(
                    id=f"{ch_counter:02d}",
                    title=ch.get("title", f"Kapitel {ch_counter}"),
                    topic=topics[0] if topics else "",  # Haupttopic
                    topics=topics,
                    card_ids=card_ids,
                    part=part_title,
                    learning_objectives=ch.get("learning_objectives", []),
                ))
        return chapters
