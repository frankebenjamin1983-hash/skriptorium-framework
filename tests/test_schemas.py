"""
Tests fuer schemas.py – Round-Trips und Validierung.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import (
    Card, Chapter, EditReview, FactReview, Outline, read_json, write_json,
)


def test_card_roundtrip(tmp_artifacts: Path):
    card = Card(
        id="c1", topic="Funktionen", subtopic="def", level="beginner",
        source="cs50p_l0", content_md="Mit `def` definieren.",
    )
    p = tmp_artifacts / "card.json"
    write_json(p, card, model=Card)
    loaded = read_json(p, model=Card)
    assert isinstance(loaded, Card)
    assert loaded == card


def test_card_list_roundtrip(tmp_artifacts: Path):
    cards = [
        Card(id=f"c{i}", topic="T", subtopic=f"S{i}", level="beginner",
             source="x", content_md=f"body {i}") for i in range(3)
    ]
    p = tmp_artifacts / "cards.json"
    write_json(p, cards, model=Card)
    loaded = read_json(p, model=Card)
    assert isinstance(loaded, list)
    assert len(loaded) == 3
    assert all(isinstance(c, Card) for c in loaded)


def test_card_validation_rejects_missing_field():
    # 'content_md' fehlt -> ValidationError
    with pytest.raises(ValidationError):
        Card.model_validate({
            "id": "c1", "topic": "T", "subtopic": "S",
            "level": "beginner", "source": "x",
        })


def test_read_json_without_model_returns_raw(tmp_artifacts: Path):
    p = tmp_artifacts / "raw.json"
    p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    assert read_json(p) == {"hello": "world"}


def test_outline_with_chapters(tmp_artifacts: Path):
    outline = Outline(
        book_title="Test", language="de",
        chapters=[Chapter(id="01", title="A", topic="A", card_ids=["x"])],
    )
    p = tmp_artifacts / "outline.json"
    write_json(p, outline, model=Outline)
    loaded = read_json(p, model=Outline)
    assert loaded.book_title == "Test"
    assert loaded.chapters[0].id == "01"


def test_fact_review_and_edit_review():
    fr = FactReview(chapter_id="01", char_count=100, issues=["i1"], verdict="warn")
    assert fr.verdict == "warn"
    er = EditReview(
        chapter_id="01", style_issues=[], structure_issues=["s1"],
        fact_issues_referenced=1, suggested_diff="",
    )
    assert er.fact_issues_referenced == 1


def test_write_json_validates_invalid_data(tmp_artifacts: Path):
    """Wenn das write_json gegen ein Modell validiert und Daten kaputt sind, muss es scheitern."""
    p = tmp_artifacts / "bad.json"
    with pytest.raises(ValidationError):
        write_json(p, {"id": "c1"}, model=Card)  # zu wenig Felder
