"""
Smoke-Test fuer den Heuristik-Importer. Wir testen NICHT gegen die echten
DavidMalanVirtuell-Dateien (Existenz ist nicht garantiert), sondern gegen
Inline-Markdown.
"""

from pathlib import Path

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
    # Erwarte einen Block mit Level 2 (virtuelles H2) und Heading "Bold Topic"
    assert any(lvl == 2 and head == "Bold Topic" for lvl, head, _ in blocks)


def test_cards_from_h2_h3(tmp_path: Path):
    md = (
        "# Lektion X\n\n"
        "## Topic A\n\n"
        "### Sub A1\nText A1\n\n"
        "### Sub A2\nText A2\n\n"
        "## Topic B\nText B (kein H3)\n"
    )
    f = tmp_path / "cs50p" / "02_dummy_extracted.md"
    f.parent.mkdir(parents=True)
    f.write_text(md, encoding="utf-8")
    cards = cards_from_file(f)
    # 2 Karten unter Topic A (Sub A1, Sub A2), 1 Karte fuer Topic B
    topics = [c.topic for c in cards]
    subtopics = [c.subtopic for c in cards]
    assert topics.count("Topic A") == 2
    assert "Sub A1" in subtopics and "Sub A2" in subtopics
    assert "Topic B" in topics


def test_classify_source_falls_back():
    # Unbekannter Pfad -> ('unknown', 'beginner', stem)
    track, level, src = classify_source(Path("C:/foo/bar/baz_extracted.md"))
    assert track == "unknown"
    assert level == "beginner"
    assert src == "baz_extracted"


def test_classify_source_cs50p_l0():
    p = Path(r"C:\x\cs50p\02_cs50p_-_lecture_0_-_functions_extracted.md")
    track, level, src = classify_source(p)
    assert track == "core"
    assert level == "beginner"
    assert "cs50p_l0" in src
