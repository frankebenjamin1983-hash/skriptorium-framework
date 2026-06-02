"""
schemas.py – Pydantic-Verträge an Agenten-Grenzen und für Artefakte.

Zwei Arten von Schemas:

1. ARTEFAKT-Schemas (Card, Chapter, Outline, ...) – beschreiben die JSON-
   Dateien auf der Platte. Wird beim Schreiben/Lesen validiert (helpers
   weiter unten).

2. KONTEXT-Schemas (ArchivarOutput, LektorInput, ...) – beschreiben, was
   ein Agent aus dem Kontext erwartet (Input) bzw. ergänzt (Output).
   Wird vom Orchestrator pre- und post-run() geprüft.

Pydantic v2: Schreibfehler (z. B. 'facts_review' statt 'facts_reviews')
landen sofort als ValidationError – kein stiller Folge-Bug im nächsten Agenten.

Konvention: alle Kontext-Schemas erben von ContextModel und setzen
extra='ignore', weil der Kontext wachsen darf. Pflichtfelder sind die,
die der Agent wirklich braucht.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ContextModel(BaseModel):
    """Basis für Kontext-Schemas. Erlaubt zusätzliche Schlüssel, prüft die Pflicht."""
    model_config = ConfigDict(extra="ignore")


# ──────────────────────────────────────────────────────────────────────────
# ARTEFAKT-Schemas (Dateien auf der Platte)
# ──────────────────────────────────────────────────────────────────────────

class Card(BaseModel):
    id: str
    topic: str
    subtopic: str
    level: str
    source: str
    content_md: str
    # Rolle der Karte im Buch:
    #   "primary"        – Kernmaterial, gehört in einen Kapitel-Volltext
    #   "supplementary"  – Hintergrund/Querverweis, nur einbinden wo passender
    #                      Zusammenhang besteht (z. B. C-Speicher-Analogie im
    #                      Python-Kapitel „Referenzen und Identität")
    role: str = "primary"
    # Track entscheidet thematische Einsortierung (z. B. core, scientific,
    # fundamentals, advanced). Bei Stufe 1 weich, in Stufe 2 vom Lektor
    # respektiert.
    track: str = "core"


class Chapter(BaseModel):
    id: str
    title: str
    topic: str
    card_ids: list[str]
    # Optional in Stufe 1, vom Echt-Lektor (Stufe 2) gefuellt.
    part: str | None = None                       # "Teil I: Grundlagen"
    topics: list[str] = []                        # Mehrere Topics moeglich (Echt-Lektor)
    learning_objectives: list[str] = []           # 3-5 Lernziele pro Kapitel


class Outline(BaseModel):
    book_title: str
    language: str
    chapters: list[Chapter]


class ChapterDraftRef(BaseModel):
    """Index-Eintrag im Kontext (nicht der Kapitel-Volltext – der steht auf Platte)."""
    id: str
    path: str
    chars: int


class FactReview(BaseModel):
    chapter_id: str
    char_count: int
    issues: list[str]
    verdict: str


class FactReviewRef(BaseModel):
    id: str
    path: str
    issue_count: int


class EditReview(BaseModel):
    chapter_id: str
    style_issues: list[str]
    structure_issues: list[str]
    fact_issues_referenced: int
    suggested_diff: str


class EditReviewRef(BaseModel):
    id: str
    path: str


class ExerciseRef(BaseModel):
    id: str
    path: str


# ──────────────────────────────────────────────────────────────────────────
# KONTEXT-Schemas pro Agent (Input + Output)
# ──────────────────────────────────────────────────────────────────────────

# Archivar: kein Input, schreibt cards
class ArchivarOutput(ContextModel):
    cards_path: str
    cards_count: int


# Lektor: liest cards, schreibt outline + chapter-Liste
class LektorInput(ContextModel):
    cards_path: str

class LektorOutput(ContextModel):
    outline_path: str
    chapters: list[Chapter]
    chapter_count: int


# Autor: liest chapters + cards_path, schreibt Drafts
class AutorInput(ContextModel):
    chapters: list[Chapter]
    cards_path: str

class AutorOutput(ContextModel):
    chapters_dir: str
    chapter_drafts: list[ChapterDraftRef]


# Faktenprüfer: liest Drafts, schreibt Fakten-Reviews
class FaktenpruferInput(ContextModel):
    chapter_drafts: list[ChapterDraftRef]

class FaktenpruferOutput(ContextModel):
    facts_reviews: list[FactReviewRef]


# Lektorat: liest Drafts (+ optional Fakten-Reviews), schreibt Edit-Reviews
class LektoratInput(ContextModel):
    chapter_drafts: list[ChapterDraftRef]
    facts_reviews: list[FactReviewRef] = []  # optional – Lektorat profitiert, kommt aber ohne aus

class LektoratOutput(ContextModel):
    edit_reviews: list[EditReviewRef]


# Quiz-Master: liest chapters, schreibt Übungen
class QuizMasterInput(ContextModel):
    chapters: list[Chapter]

class QuizMasterOutput(ContextModel):
    exercises: list[ExerciseRef]


# Revisor: liest Drafts + Lektorat-/Fakten-Reviews, schreibt revidierte Kapitel
class RevisorInput(ContextModel):
    chapter_drafts: list[ChapterDraftRef]
    edit_reviews: list[EditReviewRef]
    facts_reviews: list[FactReviewRef] = []

class RevisorOutput(ContextModel):
    chapter_drafts: list[ChapterDraftRef]  # gleiche Schluessel, neue chars/Stand
    revisions_dir: str


# Chefredakteur: liest outline (Pfad), schreibt Buch
class ChefredakteurInput(ContextModel):
    outline_path: str

class ChefredakteurOutput(ContextModel):
    book_dir: str
    book_chapters: int


# ──────────────────────────────────────────────────────────────────────────
# Helper für Artefakt-Validierung beim Schreiben/Lesen
# ──────────────────────────────────────────────────────────────────────────

import json
from typing import TypeVar, Type

T = TypeVar("T", bound=BaseModel)


def write_json(path: Path, data, model: Type[BaseModel] | None = None) -> None:
    """
    Schreibt JSON. Wenn model angegeben: validiert vorher.
    Bei list[Model] muss der Aufrufer manuell pre-validieren.
    """
    if model is not None:
        if isinstance(data, list):
            # Liste von Modellen prüfen, dann als Dicts dumpen
            data = [model.model_validate(x).model_dump() for x in data]
        else:
            data = model.model_validate(data).model_dump()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, model: Type[T] | None = None) -> dict | list | T | list[T]:
    """
    Liest JSON. Wenn model angegeben: validiert beim Lesen.
    Listen werden zu list[Model] validiert.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if model is None:
        return raw
    if isinstance(raw, list):
        return [model.model_validate(x) for x in raw]
    return model.model_validate(raw)
