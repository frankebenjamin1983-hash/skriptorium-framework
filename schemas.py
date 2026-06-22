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
    """Eine getaggte Topic-Karte aus den Quellen – die kleinste inhaltliche Einheit, aus der Kapitel gebaut werden."""
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
    """Ein geplantes Kapitel: Titel, Thema und die Karten-IDs, aus denen sein Text entsteht."""
    id: str
    title: str
    topic: str
    card_ids: list[str]
    # Optional in Stufe 1, vom Echt-Lektor (Stufe 2) gefuellt.
    part: str | None = None                       # "Teil I: Grundlagen"
    topics: list[str] = []                        # Mehrere Topics moeglich (Echt-Lektor)
    learning_objectives: list[str] = []           # 3-5 Lernziele pro Kapitel


class Outline(BaseModel):
    """Der Buch-Bauplan des Lektors: Titel, Sprache und die geordnete Kapitelliste."""
    book_title: str
    language: str
    chapters: list[Chapter]


class ChapterDraftRef(BaseModel):
    """Index-Eintrag im Kontext (nicht der Kapitel-Volltext – der steht auf Platte)."""
    id: str
    path: str
    chars: int


class FactReview(BaseModel):
    """Ergebnis des Faktenprüfers für ein Kapitel: gefundene Probleme und Gesamturteil."""
    chapter_id: str
    char_count: int
    issues: list[str]
    verdict: str


class FactReviewRef(BaseModel):
    """Index-Eintrag auf einen Fakten-Review auf der Platte (Pfad + Anzahl der Probleme)."""
    id: str
    path: str
    issue_count: int


class EditReview(BaseModel):
    """Ergebnis des Lektorats für ein Kapitel: Stil-/Struktur-Anmerkungen und Diff-Vorschlag."""
    chapter_id: str
    style_issues: list[str]
    structure_issues: list[str]
    fact_issues_referenced: int
    suggested_diff: str


class EditReviewRef(BaseModel):
    """Index-Eintrag auf einen Lektorat-Review auf der Platte."""
    id: str
    path: str


class ExerciseRef(BaseModel):
    """Index-Eintrag auf eine generierte Übungs-/Quiz-Datei auf der Platte."""
    id: str
    path: str


# ──────────────────────────────────────────────────────────────────────────
# KONTEXT-Schemas pro Agent (Input + Output)
# ──────────────────────────────────────────────────────────────────────────

# Archivar: kein Input, schreibt cards
class ArchivarOutput(ContextModel):
    """Was der Archivar in den Kontext schreibt: Pfad und Anzahl der getaggten Karten."""
    cards_path: str
    cards_count: int


# Lektor: liest cards, schreibt outline + chapter-Liste
class LektorInput(ContextModel):
    """Was der Lektor aus dem Kontext braucht: den Pfad zu den Karten."""
    cards_path: str

class LektorOutput(ContextModel):
    """Was der Lektor ergänzt: Outline-Pfad und die geplanten Kapitel."""
    outline_path: str
    chapters: list[Chapter]
    chapter_count: int


# Autor: liest chapters + cards_path, schreibt Drafts
class AutorInput(ContextModel):
    """Was der Autor braucht: die Kapitelplanung und den Karten-Pfad."""
    chapters: list[Chapter]
    cards_path: str

class AutorOutput(ContextModel):
    """Was der Autor ergänzt: Verzeichnis und Index der geschriebenen Kapitel-Drafts."""
    chapters_dir: str
    chapter_drafts: list[ChapterDraftRef]


# Faktenprüfer: liest Drafts, schreibt Fakten-Reviews
class FaktenpruferInput(ContextModel):
    """Was der Faktenprüfer braucht: die Kapitel-Draft-Referenzen."""
    chapter_drafts: list[ChapterDraftRef]

class FaktenpruferOutput(ContextModel):
    """Was der Faktenprüfer ergänzt: die Fakten-Review-Referenzen."""
    facts_reviews: list[FactReviewRef]


# Lektorat: liest Drafts (+ optional Fakten-Reviews), schreibt Edit-Reviews
class LektoratInput(ContextModel):
    """Was das Lektorat braucht: Kapitel-Drafts (Fakten-Reviews optional)."""
    chapter_drafts: list[ChapterDraftRef]
    facts_reviews: list[FactReviewRef] = []  # optional – Lektorat profitiert, kommt aber ohne aus

class LektoratOutput(ContextModel):
    """Was das Lektorat ergänzt: die Edit-Review-Referenzen."""
    edit_reviews: list[EditReviewRef]


# Quiz-Master: liest chapters, schreibt Übungen
class QuizMasterInput(ContextModel):
    """Was der Quiz-Master braucht: die Kapitel."""
    chapters: list[Chapter]

class QuizMasterOutput(ContextModel):
    """Was der Quiz-Master ergänzt: die Übungs-Referenzen."""
    exercises: list[ExerciseRef]


# Revisor: liest Drafts + Lektorat-/Fakten-Reviews, schreibt revidierte Kapitel
class RevisorInput(ContextModel):
    """Was der Revisor braucht: Drafts plus Lektorat- und (optional) Fakten-Reviews."""
    chapter_drafts: list[ChapterDraftRef]
    edit_reviews: list[EditReviewRef]
    facts_reviews: list[FactReviewRef] = []

class RevisorOutput(ContextModel):
    """Was der Revisor ergänzt: revidierte Kapitel (gleiche Schlüssel, neuer Stand)."""
    chapter_drafts: list[ChapterDraftRef]  # gleiche Schluessel, neue chars/Stand
    revisions_dir: str


# Chefredakteur: liest outline (Pfad), schreibt Buch
class ChefredakteurInput(ContextModel):
    """Was der Chefredakteur braucht: den Outline-Pfad."""
    outline_path: str

class ChefredakteurOutput(ContextModel):
    """Was der Chefredakteur ergänzt: Buch-Verzeichnis und Anzahl der Kapitel."""
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
