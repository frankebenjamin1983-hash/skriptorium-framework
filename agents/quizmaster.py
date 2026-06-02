"""
agents/quizmaster.py – Übungen pro Kapitel.

Stufe 1: Mini-Übungsdatei pro Kapitel.
Stufe 2: Grok-fast: 5 Verständnisfragen + 3 Code-Aufgaben + 1 Mini-Projekt.
"""

from pathlib import Path

from schemas import ExerciseRef, QuizMasterInput, QuizMasterOutput

from .base import Agent


class DummyQuizMaster(Agent):
    INPUT_SCHEMA = QuizMasterInput
    OUTPUT_SCHEMA = QuizMasterOutput

    def __init__(self):
        super().__init__("Quiz-Master")

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        chapters = context["chapters"]

        out_dir = artifacts_dir / "exercises"
        out_dir.mkdir(exist_ok=True)

        exercises: list[ExerciseRef] = []
        for ch in chapters:
            content = (
                f"# Übungen zu Kapitel {ch['id']}: {ch['title']}\n\n"
                f"_Stufe-1-Mock-Übungen._\n\n"
                f"1. Verständnisfrage (Mock)\n"
                f"2. Code-Aufgabe (Mock)\n"
            )
            path = out_dir / f"{ch['id']}.md"
            path.write_text(content, encoding="utf-8")
            exercises.append(ExerciseRef(id=ch["id"], path=str(path)))

        return {"exercises": [e.model_dump() for e in exercises]}
