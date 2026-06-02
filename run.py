"""
run.py – Entry-Point.

Stufe 1: Volle Dummy-Crew (7 Rollen) sequenziell. Kein API-Call, kein Geld.

Aufruf vom Projektordner:
    python run.py
"""

from pathlib import Path

from agents import (
    DummyArchivar,
    DummyAutor,
    DummyChefredakteur,
    DummyFaktenpruefer,
    DummyLektor,
    DummyLektorat,
    DummyQuizMaster,
)
from orchestrator import Orchestrator


def main() -> None:
    orch = Orchestrator(project_root=Path(__file__).parent)
    pipeline = [
        DummyArchivar(),       # Topic-Karten aus Quellen
        DummyLektor(),         # Outline aus Karten
        DummyAutor(),          # Kapitel-Drafts aus Outline + Karten
        DummyFaktenpruefer(),  # inhaltliche Kontrolle der Drafts
        DummyLektorat(),       # didaktischer Feinschliff
        DummyQuizMaster(),     # Übungen pro Kapitel
        DummyChefredakteur(),  # finales Buch zusammenstellen
    ]
    final = orch.run(pipeline)

    # Nur die Schlüssel, nicht die Werte – die Werte sind oft Pfade.
    print("\nEnd-Kontext-Keys:", sorted(final.keys()))


if __name__ == "__main__":
    main()
