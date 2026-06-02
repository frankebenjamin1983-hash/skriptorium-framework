"""
Tests pro Agent: Dummy laeuft durch, OUTPUT_SCHEMA validiert, Artefakte
landen am erwarteten Ort.
"""

from pathlib import Path

from agents import (
    DummyArchivar, DummyAutor, DummyChefredakteur, DummyFaktenpruefer,
    DummyLektor, DummyLektorat, DummyQuizMaster,
)


def test_archivar_writes_cards(tmp_artifacts: Path):
    out = DummyArchivar().run({}, tmp_artifacts)
    assert "cards_path" in out
    assert Path(out["cards_path"]).exists()
    assert out["cards_count"] >= 1


def test_lektor_produces_chapters(tmp_artifacts: Path):
    ctx = DummyArchivar().run({}, tmp_artifacts)
    out = DummyLektor().run(ctx, tmp_artifacts)
    assert "chapters" in out
    assert isinstance(out["chapters"], list)
    assert len(out["chapters"]) >= 1
    # Schema-Erwartungen
    ch = out["chapters"][0]
    assert {"id", "title", "topic", "card_ids"}.issubset(ch.keys())


def _full_context(tmp_artifacts: Path) -> dict:
    """Pipeline bis einschliesslich Lektor laufen lassen, Kontext zurueckgeben."""
    ctx = {}
    ctx.update(DummyArchivar().run(ctx, tmp_artifacts))
    ctx.update(DummyLektor().run(ctx, tmp_artifacts))
    return ctx


def test_autor_writes_chapter_drafts(tmp_artifacts: Path):
    ctx = _full_context(tmp_artifacts)
    out = DummyAutor().run(ctx, tmp_artifacts)
    drafts = out["chapter_drafts"]
    assert drafts and all(Path(d["path"]).exists() for d in drafts)


def test_faktenpruefer_produces_reviews(tmp_artifacts: Path):
    ctx = _full_context(tmp_artifacts)
    ctx.update(DummyAutor().run(ctx, tmp_artifacts))
    out = DummyFaktenpruefer().run(ctx, tmp_artifacts)
    assert all(Path(r["path"]).exists() for r in out["facts_reviews"])


def test_lektorat_produces_edits(tmp_artifacts: Path):
    ctx = _full_context(tmp_artifacts)
    ctx.update(DummyAutor().run(ctx, tmp_artifacts))
    ctx.update(DummyFaktenpruefer().run(ctx, tmp_artifacts))
    out = DummyLektorat().run(ctx, tmp_artifacts)
    assert all(Path(e["path"]).exists() for e in out["edit_reviews"])


def test_quizmaster_writes_exercises(tmp_artifacts: Path):
    ctx = _full_context(tmp_artifacts)
    out = DummyQuizMaster().run(ctx, tmp_artifacts)
    assert all(Path(e["path"]).exists() for e in out["exercises"])


def test_chefredakteur_assembles_book(tmp_artifacts: Path):
    ctx = _full_context(tmp_artifacts)
    ctx.update(DummyAutor().run(ctx, tmp_artifacts))
    ctx.update(DummyFaktenpruefer().run(ctx, tmp_artifacts))
    ctx.update(DummyLektorat().run(ctx, tmp_artifacts))
    ctx.update(DummyQuizMaster().run(ctx, tmp_artifacts))
    out = DummyChefredakteur().run(ctx, tmp_artifacts)
    book_dir = Path(out["book_dir"])
    assert (book_dir / "index.md").exists()
    assert any((book_dir / "chapters").iterdir())


def test_all_dummies_have_output_schema():
    """Strukturelle Pruefung: jeder Dummy deklariert OUTPUT_SCHEMA."""
    for cls in [DummyArchivar, DummyLektor, DummyAutor, DummyFaktenpruefer,
                DummyLektorat, DummyQuizMaster, DummyChefredakteur]:
        assert cls.OUTPUT_SCHEMA is not None, f"{cls.__name__} ohne OUTPUT_SCHEMA"
