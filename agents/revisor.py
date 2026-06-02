"""
agents/revisor.py – Dummy-Revisor (Stufe 1).

No-Op-Variante: nimmt chapter_drafts entgegen, gibt sie unveraendert
zurueck. Existiert nur, damit die Pipeline-Struktur einheitlich bleibt,
bevor der echte Revisor (Stufe 2) zugeschaltet wird.
"""

from pathlib import Path

from schemas import RevisorInput, RevisorOutput

from .base import Agent


class DummyRevisor(Agent):
    INPUT_SCHEMA = RevisorInput
    OUTPUT_SCHEMA = RevisorOutput

    def __init__(self):
        super().__init__("Revisor")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        revisions_dir = artifacts_dir / "revisions"
        revisions_dir.mkdir(exist_ok=True)
        return {
            "chapter_drafts": context["chapter_drafts"],
            "revisions_dir": str(revisions_dir),
        }
