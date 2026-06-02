"""
agents/faktenpruefer.py – Inhaltliche Kontrolle der Kapitel-Drafts.

Stufe 1: Leere Review-Stubs.
Stufe 2: Grok-fast vergleicht Aussagen mit Original-Karten.
"""

from pathlib import Path

from schemas import (
    FactReview, FactReviewRef, FaktenpruferInput, FaktenpruferOutput, write_json,
)

from .base import Agent


class DummyFaktenpruefer(Agent):
    INPUT_SCHEMA = FaktenpruferInput
    OUTPUT_SCHEMA = FaktenpruferOutput

    def __init__(self):
        super().__init__("Faktenprüfer")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        drafts = context["chapter_drafts"]

        out_dir = artifacts_dir / "reviews"
        out_dir.mkdir(exist_ok=True)

        reviews: list[FactReviewRef] = []
        for d in drafts:
            chapter_text = Path(d["path"]).read_text(encoding="utf-8")
            review = FactReview(
                chapter_id=d["id"],
                char_count=len(chapter_text),
                issues=[],   # Stufe 2: erkannte Halluzinationen / fehlende Belege
                verdict="ok",
            )
            path = out_dir / f"{d['id']}_facts.json"
            write_json(path, review, model=FactReview)
            reviews.append(FactReviewRef(id=d["id"], path=str(path), issue_count=len(review.issues)))

        return {"facts_reviews": [r.model_dump() for r in reviews]}
