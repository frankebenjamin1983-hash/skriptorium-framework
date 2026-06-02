"""
agents/lektorat.py – Didaktischer Feinschliff.

Stufe 1: Leere Edit-Stubs.
Stufe 2: Claude Sonnet liest Draft + Faktenprüfer-Issues, schlägt
         Verbesserungs-Diff vor (NICHT das ganze Kapitel neu).
"""

from pathlib import Path

from schemas import (
    EditReview, EditReviewRef, LektoratInput, LektoratOutput, write_json,
)

from .base import Agent


class DummyLektorat(Agent):
    INPUT_SCHEMA = LektoratInput
    OUTPUT_SCHEMA = LektoratOutput

    def __init__(self):
        super().__init__("Lektorat")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        drafts = context["chapter_drafts"]
        facts = context.get("facts_reviews", [])
        facts_by_id = {f["id"]: f for f in facts}

        out_dir = artifacts_dir / "reviews"
        out_dir.mkdir(exist_ok=True)

        edits: list[EditReviewRef] = []
        for d in drafts:
            fact_issues = facts_by_id.get(d["id"], {}).get("issue_count", 0)
            edit = EditReview(
                chapter_id=d["id"],
                style_issues=[],     # Stufe 2: Tonalität, Wortwahl, Ostwestfalen-Charme
                structure_issues=[], # Stufe 2: Aufbau, Übergänge
                fact_issues_referenced=fact_issues,
                suggested_diff="",   # Stufe 2: unified diff oder strukturierte Patches
            )
            path = out_dir / f"{d['id']}_edit.json"
            write_json(path, edit, model=EditReview)
            edits.append(EditReviewRef(id=d["id"], path=str(path)))

        return {"edit_reviews": [e.model_dump() for e in edits]}
