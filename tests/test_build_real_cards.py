"""
Smoke-Test fuer den Heuristik-Importer.

Tests gegen Inline-Markdown – keine Abhaengigkeit auf externe Quelldaten.
Quellenspezifische Klassifikation (SOURCE_MAP) wird per Monkeypatching
abgedeckt, damit das Test-Verhalten unabhaengig von lokaler source_map.json
bleibt.
"""

from pathlib import Path

import pytest

from tools import build_real_cards
from tools.build_real_cards import cards_from_file, classify_source, split_by_headings


def test_split_basic():
    text = "# H1\n\n## A\nfoo\n\n### B\nbar\n"
    blocks = split_by_headings(text)
    levels = [lvl for lvl, _, _ in blocks]
    heads = [head for _, head, _ in blocks]
    assert 1 in levels and 2 in levels and 3 in levels
    assert "H1" in heads and "A" in heads and "B" in heads


def test_split_bold_as_h2():
    text = "# Title\n\n**Bold Topic**\nbody body\n"
    blocks = split_by_headings(text)
    assert any(lvl == 2 and head == "Bold Topic" for lvl, head, _ in blocks)


def test_cards_from_h2_h3(tmp_path: Path):
    md = (
        "# Lektion X\n\n"
        "## Topic A\n\n"
        "### Sub A1\nText A1\n\n"
        "### Sub A2\nText A2\n\n"
        "## Topic B\nText B (kein H3)\n"
    )
    f = tmp_path / "demo" / "01_demo_extracted.md"
    f.parent.mkdir(parents=True)
    f.write_text(md, encoding="utf-8")
    cards = cards_from_file(f)
    topics = [c.topic for c in cards]
    subtopics = [c.subtopic for c in cards]
    assert topics.count("Topic A") == 2
    assert "Sub A1" in subtopics and "Sub A2" in subtopics
    assert "Topic B" in topics


def test_classify_source_falls_back():
    track, level, src = classify_source(Path("C:/foo/bar/baz_extracted.md"))
    assert track == "unknown"
    assert level == "beginner"
    assert src == "baz_extracted"


@pytest.fixture
def patched_source_map(monkeypatch):
    """Setzt SOURCE_MAP fuer den Test deterministisch."""
    monkeypatch.setattr(build_real_cards, "SOURCE_MAP", [
        ("primary_dir", ("core", "beginner", "primary_src")),
        ("supp_dir",    ("fundamentals", "beginner", "supp_src")),
    ])


def test_classify_source_uses_mapping(patched_source_map):
    track, level, src = classify_source(Path("/x/primary_dir/file.md"))
    assert (track, level, src) == ("core", "beginner", "primary_src")


def test_role_supplementary_for_fundamentals(patched_source_map, tmp_path: Path):
    md = "# L\n\n## Topic\nBody.\n"
    f = tmp_path / "supp_dir" / "any_extracted.md"
    f.parent.mkdir(parents=True)
    f.write_text(md, encoding="utf-8")
    cards = cards_from_file(f)
    assert cards
    assert all(c.role == "supplementary" for c in cards)
    assert all(c.track == "fundamentals" for c in cards)


def test_role_primary_for_core(patched_source_map, tmp_path: Path):
    md = "# L\n\n## Topic\nBody.\n"
    f = tmp_path / "primary_dir" / "any_extracted.md"
    f.parent.mkdir(parents=True)
    f.write_text(md, encoding="utf-8")
    cards = cards_from_file(f)
    assert cards
    assert all(c.role == "primary" for c in cards)
    assert all(c.track == "core" for c in cards)
