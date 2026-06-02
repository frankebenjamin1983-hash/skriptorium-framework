"""
agents/autor.py – Kapitel-Drafts schreiben.

Stufe 1: Mini-Inhalt aus den Karten zusammengestoppelt.
Stufe 2: Claude Sonnet mit Style-Guide + Quellenbelegen.

NAHT FÜR STUFE 3 (Async / Fan-out):
Hier iteriert der Agent intern über alle Kapitel. In Stufe 3 wird das
aufgelöst: der Orchestrator instanziiert pro Kapitel einen eigenen Autor
und lässt sie parallel laufen.
"""

from pathlib import Path

from schemas import (
    AutorInput, AutorOutput, Card, ChapterDraftRef, read_json,
)

from .base import Agent


class DummyAutor(Agent):
    INPUT_SCHEMA = AutorInput
    OUTPUT_SCHEMA = AutorOutput

    def __init__(self):
        super().__init__("Autor")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        chapters = context["chapters"]  # validiert durch INPUT_SCHEMA
        cards: list[Card] = read_json(Path(context["cards_path"]), model=Card)
        cards_by_id = {c.id: c for c in cards}

        out_dir = artifacts_dir / "chapters"
        out_dir.mkdir(exist_ok=True)

        drafts: list[ChapterDraftRef] = []
        for ch in chapters:
            ch_cards = [cards_by_id[cid] for cid in ch["card_ids"] if cid in cards_by_id]
            body = f"# Kapitel {ch['id']}: {ch['title']}\n\n"
            body += f"_Stufe-1-Mock-Inhalt, abgeleitet aus {len(ch_cards)} Karten._\n\n"
            for c in ch_cards:
                body += f"## {c.subtopic}\n\n{c.content_md}\n\n"
            path = out_dir / f"{ch['id']}.md"
            path.write_text(body, encoding="utf-8")
            drafts.append(ChapterDraftRef(id=ch["id"], path=str(path), chars=len(body)))

        return {
            "chapters_dir": str(out_dir),
            "chapter_drafts": [d.model_dump() for d in drafts],
        }
