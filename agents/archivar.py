"""
agents/archivar.py – Topic-Karten aus Quell-MDs erzeugen.

Stufe 1: Feste Mock-Karten, kein LLM.
Stufe 2: Liest die existierenden Chroma-Chunks aus dem Vectorstore,
         Grok ergänzt nur Metadaten (Topic/Subtopic/Level).
"""

from pathlib import Path

from schemas import ArchivarOutput, Card, write_json

from .base import Agent


class DummyArchivar(Agent):
    INPUT_SCHEMA = None  # erster Agent – braucht keinen Vorgänger
    OUTPUT_SCHEMA = ArchivarOutput

    def __init__(self):
        super().__init__("Archivar")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        cards = [
            Card(
                id="card_001",
                topic="Funktionen",
                subtopic="Definition mit def",
                level="beginner",
                source="dummy:source_a_lecture_0",
                content_md="Funktionen werden mit `def name():` definiert.",
            ),
            Card(
                id="card_002",
                topic="Funktionen",
                subtopic="Parameter und Rückgabewerte",
                level="beginner",
                source="dummy:source_a_lecture_0",
                content_md="Parameter stehen in Klammern, `return` liefert ein Ergebnis.",
            ),
            Card(
                id="card_003",
                topic="Klassen",
                subtopic="Dataclasses",
                level="intermediate",
                source="dummy:source_b",
                content_md="`@dataclass` erzeugt `__init__`, `__repr__` etc. automatisch.",
            ),
        ]
        out = artifacts_dir / "cards.json"
        # write_json validiert jedes Card-Modell vor dem Schreiben.
        write_json(out, cards, model=Card)
        return {"cards_path": str(out), "cards_count": len(cards)}
