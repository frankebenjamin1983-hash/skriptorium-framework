"""
agents/chefredakteur.py – Finale Konsolidierung zum Buch.

Stufe 1: Klebt Drafts + Übungen zusammen, schreibt Inhaltsverzeichnis.
Stufe 2: Claude Opus liest ALLES im Block, prüft globale Konsistenz,
         schreibt Vorwort, Glossar, Index, entscheidet Review-Konflikte.
"""

from pathlib import Path

from schemas import (
    ChefredakteurInput, ChefredakteurOutput, Outline, read_json,
)

from .base import Agent


class DummyChefredakteur(Agent):
    INPUT_SCHEMA = ChefredakteurInput
    OUTPUT_SCHEMA = ChefredakteurOutput

    def __init__(self):
        super().__init__("Chefredakteur")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        outline: Outline = read_json(Path(context["outline_path"]), model=Outline)

        book_dir = artifacts_dir / "book"
        ch_out = book_dir / "chapters"
        ch_out.mkdir(parents=True, exist_ok=True)

        for ch in outline.chapters:
            draft_path = artifacts_dir / "chapters" / f"{ch.id}.md"
            exer_path = artifacts_dir / "exercises" / f"{ch.id}.md"
            parts = [draft_path.read_text(encoding="utf-8")]
            if exer_path.exists():
                parts.append(exer_path.read_text(encoding="utf-8"))
            (ch_out / f"{ch.id}.md").write_text("\n\n---\n\n".join(parts), encoding="utf-8")

        toc = f"# {outline.book_title}\n\n## Inhaltsverzeichnis\n\n"
        for ch in outline.chapters:
            toc += f"- [Kapitel {ch.id}: {ch.title}](chapters/{ch.id}.md)\n"
        (book_dir / "index.md").write_text(toc, encoding="utf-8")

        return {"book_dir": str(book_dir), "book_chapters": len(outline.chapters)}
