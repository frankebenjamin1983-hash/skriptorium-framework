"""
run.py – Entry-Point + CLI.

Stufe 1: Dummy-Crew sequenziell. Kein API-Call, kein Geld.

Aufrufe (vom Projektordner):

    python run.py                       # ganze Pipeline
    python run.py --dry-run             # nur Plan zeigen
    python run.py --clean               # artifacts/ + runs.jsonl vorher loeschen
    python run.py --only Lektor         # nur diesen Agenten ausfuehren
    python run.py --from Autor          # ab diesem Agenten weitermachen
    python run.py --list                # Agentenliste mit Namen

--from setzt voraus, dass die Artefakte der Vorgaenger schon da sind. Wir
rekonstruieren den Kontext aus den vorhandenen Dateien (cards.json /
outline.json), damit der Folge-Agent seine INPUT_SCHEMA-Pruefung besteht.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from agents import (
    DummyArchivar, DummyAutor, DummyChefredakteur, DummyFaktenpruefer,
    DummyLektor, DummyLektorat, DummyQuizMaster,
)
from agents.base import Agent
from orchestrator import Orchestrator


# ──────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────

def default_pipeline(
    real_archivar: bool = False,
    real_lektor: bool = False,
    real_autor: bool = False,
    real_fakt: bool = False,
    real_lektorat: bool = False,
    real_revisor: bool = False,
    sample: int | None = None,
    chapter: str | None = None,
) -> list[Agent]:
    """
    Standard-Reihenfolge. Echte Agenten werden ueber Flags zugeschaltet,
    Default ist die Stufe-1-Dummy-Crew.
    """
    if real_archivar:
        from agents.archivar_real import RealArchivar
        archivar: Agent = RealArchivar(sample=sample)
    else:
        archivar = DummyArchivar()

    if real_lektor:
        from agents.lektor_real import RealLektor
        lektor: Agent = RealLektor()
    else:
        lektor = DummyLektor()

    if real_autor:
        from agents.autor_real import RealAutor
        autor: Agent = RealAutor(chapter_id=chapter)
    else:
        autor = DummyAutor()

    if real_fakt:
        from agents.faktenpruefer_real import RealFaktenpruefer
        fakt: Agent = RealFaktenpruefer(chapter_id=chapter)
    else:
        fakt = DummyFaktenpruefer()

    if real_lektorat:
        from agents.lektorat_real import RealLektorat
        lektorat: Agent = RealLektorat(chapter_id=chapter)
    else:
        lektorat = DummyLektorat()

    if real_revisor:
        from agents.revisor_real import RealRevisor
        revisor: Agent = RealRevisor(chapter_id=chapter)
    else:
        from agents import DummyRevisor
        revisor = DummyRevisor()

    return [
        archivar,
        lektor,
        autor,
        fakt,
        lektorat,
        revisor,
        DummyQuizMaster(),
        DummyChefredakteur(),
    ]


# ──────────────────────────────────────────────────────────────────────────
# Kontext-Rekonstruktion fuer --from / --only
# ──────────────────────────────────────────────────────────────────────────

def restore_context_from_artifacts(artifacts_dir: Path) -> dict:
    """
    Versucht den Kontext aus Artefakten frueherer Laeufe zu rekonstruieren,
    damit Folge-Agenten ihre Input-Schemas erfuellen.

    Nimmt nur, was nachweislich existiert. Wenn z.B. nur cards.json da ist,
    aber outline.json fehlt, gibt es eben nur cards_path im Kontext.

    Wir laden hier keine grossen Inhalte – wir reichen nur die Indizes
    (Pfade + chapters-Liste) durch. Das ist die gleiche Konvention wie
    waehrend des regulaeren Laufs.
    """
    ctx: dict = {}

    cards_path = artifacts_dir / "cards.json"
    if cards_path.exists():
        ctx["cards_path"] = str(cards_path)
        try:
            ctx["cards_count"] = len(json.loads(cards_path.read_text(encoding="utf-8")))
        except Exception:
            pass

    outline_path = artifacts_dir / "outline.json"
    if outline_path.exists():
        ctx["outline_path"] = str(outline_path)
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            ctx["chapters"] = outline.get("chapters", [])
            ctx["chapter_count"] = len(ctx["chapters"])
        except Exception:
            pass

    # chapter_drafts aus chapters/-Verzeichnis
    ch_dir = artifacts_dir / "chapters"
    if ch_dir.exists():
        drafts = []
        for md in sorted(ch_dir.glob("*.md")):
            drafts.append({
                "id": md.stem, "path": str(md), "chars": md.stat().st_size,
            })
        if drafts:
            ctx["chapters_dir"] = str(ch_dir)
            ctx["chapter_drafts"] = drafts

    # facts_reviews / edit_reviews aus reviews/-Verzeichnis
    rev_dir = artifacts_dir / "reviews"
    if rev_dir.exists():
        facts = []
        edits = []
        for j in sorted(rev_dir.glob("*.json")):
            stem = j.stem  # z.B. "01_facts" oder "01_edit"
            if stem.endswith("_facts"):
                chap_id = stem[:-len("_facts")]
                facts.append({"id": chap_id, "path": str(j), "issue_count": 0})
            elif stem.endswith("_edit"):
                chap_id = stem[:-len("_edit")]
                edits.append({"id": chap_id, "path": str(j)})
        if facts:
            ctx["facts_reviews"] = facts
        if edits:
            ctx["edit_reviews"] = edits

    # exercises
    ex_dir = artifacts_dir / "exercises"
    if ex_dir.exists():
        exercises = [
            {"id": md.stem, "path": str(md)} for md in sorted(ex_dir.glob("*.md"))
        ]
        if exercises:
            ctx["exercises"] = exercises

    return ctx


# ──────────────────────────────────────────────────────────────────────────
# Auswahl-Helpers
# ──────────────────────────────────────────────────────────────────────────

def select_pipeline(
    pipeline: list[Agent],
    only: str | None,
    start_from: str | None,
    end_at: str | None = None,
) -> list[Agent]:
    """--only / --from / --to in die Pipeline-Auswahl uebersetzen."""
    if only:
        for a in pipeline:
            if a.name == only:
                return [a]
        raise SystemExit(f"Unbekannter Agent: {only}. Verfuegbar: {[a.name for a in pipeline]}")

    names = [a.name for a in pipeline]
    start_idx = 0
    if start_from:
        if start_from not in names:
            raise SystemExit(f"Unbekannter Agent: {start_from}. Verfuegbar: {names}")
        start_idx = names.index(start_from)

    end_idx = len(pipeline)
    if end_at:
        if end_at not in names:
            raise SystemExit(f"Unbekannter Agent: {end_at}. Verfuegbar: {names}")
        end_idx = names.index(end_at) + 1  # inklusive

    return pipeline[start_idx:end_idx]


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skriptorium – Agenten-Pipeline. Stufe 1: Dummy-Crew, kein API-Call.",
    )
    parser.add_argument("--list", action="store_true",
                        help="Agentenliste zeigen und beenden.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Pipeline-Plan ausgeben, nichts ausfuehren.")
    parser.add_argument("--clean", action="store_true",
                        help="artifacts/ und runs.jsonl vor dem Lauf loeschen.")
    parser.add_argument("--only", metavar="AGENT",
                        help="Nur diesen Agenten ausfuehren (Name aus --list).")
    parser.add_argument("--from", dest="start_from", metavar="AGENT",
                        help="Ab diesem Agenten weitermachen (vorherige Artefakte muessen existieren).")
    parser.add_argument("--to", dest="end_at", metavar="AGENT",
                        help="Bei diesem Agenten aufhoeren (inklusive).")
    parser.add_argument("--real-archivar", action="store_true",
                        help="Stufe-2-Archivar (Grok) statt Dummy verwenden. Kostet Tokens!")
    parser.add_argument("--real-lektor", action="store_true",
                        help="Stufe-2-Lektor (Claude Sonnet) statt Dummy verwenden.")
    parser.add_argument("--real-autor", action="store_true",
                        help="Stufe-2-Autor (Claude Sonnet) statt Dummy verwenden.")
    parser.add_argument("--real-fakt", action="store_true",
                        help="Stufe-2-Faktenpruefer (Grok-fast) statt Dummy verwenden.")
    parser.add_argument("--real-lektorat", action="store_true",
                        help="Stufe-2-Lektorat (Claude Sonnet) statt Dummy verwenden.")
    parser.add_argument("--real-revisor", action="store_true",
                        help="Stufe-2-Revisor (Claude Sonnet) statt Dummy verwenden.")
    parser.add_argument("--chapter", metavar="ID",
                        help="Nur dieses Kapitel verarbeiten (z. B. '07'). Nur sinnvoll mit --real-autor.")
    parser.add_argument("--sample", type=int, metavar="N",
                        help="Nur die ersten N Karten verarbeiten (Kostenkontrolle).")
    args = parser.parse_args()

    if args.only and args.start_from:
        raise SystemExit("--only und --from sind sich gegenseitig ausschliessend.")

    root = Path(__file__).resolve().parent
    artifacts_dir = root / "artifacts"
    runs_log = root / "runs.jsonl"

    pipeline = default_pipeline(
        real_archivar=args.real_archivar,
        real_lektor=args.real_lektor,
        real_autor=args.real_autor,
        real_fakt=args.real_fakt,
        real_lektorat=args.real_lektorat,
        real_revisor=args.real_revisor,
        sample=args.sample,
        chapter=args.chapter,
    )

    if args.list:
        print("Pipeline-Reihenfolge:")
        for i, a in enumerate(pipeline, 1):
            print(f"  {i:>2}. {a.name}")
        return

    selected = select_pipeline(
        pipeline, only=args.only, start_from=args.start_from, end_at=args.end_at,
    )

    if args.dry_run:
        print("Dry-Run – wuerde ausfuehren:")
        for i, a in enumerate(selected, 1):
            print(f"  {i:>2}. {a.name}")
        return

    if args.clean:
        if artifacts_dir.exists():
            shutil.rmtree(artifacts_dir)
        if runs_log.exists():
            runs_log.unlink()
        print(f"Aufgeraeumt: {artifacts_dir} + {runs_log.name}")

    # Falls wir nicht von vorn anfangen, vorhandenen Kontext laden.
    initial_ctx: dict = {}
    if args.start_from or args.only:
        initial_ctx = restore_context_from_artifacts(artifacts_dir)
        if initial_ctx:
            print(f"Kontext aus Artefakten rekonstruiert: {sorted(initial_ctx.keys())}")
        else:
            print("Keine vorherigen Artefakte gefunden – Pipeline laeuft mit leerem Kontext.")

    orch = Orchestrator(project_root=root)
    final = orch.run(selected, initial_context=initial_ctx)
    print("\nEnd-Kontext-Keys:", sorted(final.keys()))


if __name__ == "__main__":
    main()
