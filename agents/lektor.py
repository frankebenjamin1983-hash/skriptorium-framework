"""
agents/lektor.py – Buchstruktur aus Topic-Karten ableiten.

Stufe 1: Triviale Gruppierung nach Topic.
Stufe 2: Claude Opus mit Reasoning über Lernkurve, Reihenfolge, Lernziele.
"""

from pathlib import Path

from schemas import (
    Card, Chapter, LektorInput, LektorOutput, Outline, read_json, write_json,
)

from .base import Agent


class DummyLektor(Agent):
    INPUT_SCHEMA = LektorInput
    OUTPUT_SCHEMA = LektorOutput

    def __init__(self):
        super().__init__("Lektor")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        cards: list[Card] = read_json(Path(context["cards_path"]), model=Card)

        topics = sorted({c.topic for c in cards})
        chapters = [
            Chapter(
                id=f"{i:02d}",
                title=topic,
                topic=topic,
                card_ids=[c.id for c in cards if c.topic == topic],
            )
            for i, topic in enumerate(topics, start=1)
        ]

        outline = Outline(
            book_title="PyCompendium – Vom Anfänger zum Profi",
            language="de",
            chapters=chapters,
        )
        out = artifacts_dir / "outline.json"
        write_json(out, outline, model=Outline)

        return {
            "outline_path": str(out),
            "chapters": [c.model_dump() for c in chapters],
            "chapter_count": len(chapters),
        }
