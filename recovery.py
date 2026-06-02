"""
recovery.py – Wiederanlauf-Helper auf Basis von runs.jsonl.

Stufe 1: Nur Helper-Funktionen + Standalone-CLI fuer Inspektion.
Stufe 2: Der Orchestrator kann hierueber den naechsten Agenten ermitteln,
         der ausgefuehrt werden muss – wichtig, sobald Laeufe Geld kosten
         und ein Abbruch in der Mitte vorkommen kann.

CLI:
    python -m recovery               # Zusammenfassung aller Laeufe
    python -m recovery <run_id>      # Details zu einem Lauf
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from agents.base import Agent


DEFAULT_RUNS_LOG = Path(__file__).resolve().parent / "runs.jsonl"


# ──────────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────────

def iter_entries(runs_log: Path = DEFAULT_RUNS_LOG) -> Iterable[dict]:
    """Liest runs.jsonl Zeile fuer Zeile."""
    if not runs_log.exists():
        return
    with runs_log.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # kaputte Zeile ueberspringen, nicht den ganzen Lauf kippen
                continue


# ──────────────────────────────────────────────────────────────────────────
# Public Helpers
# ──────────────────────────────────────────────────────────────────────────

def last_successful_run_id(runs_log: Path = DEFAULT_RUNS_LOG) -> str | None:
    """run_id des letzten Eintrags mit status='ok'."""
    last = None
    for e in iter_entries(runs_log):
        if e.get("status") == "ok":
            last = e.get("run_id")
    return last


def agents_completed_in_run(
    runs_log: Path,
    run_id: str,
) -> list[str]:
    """Agenten in run_id mit status='ok', in Reihenfolge des Auftretens."""
    seen: list[str] = []
    for e in iter_entries(runs_log):
        if e.get("run_id") == run_id and e.get("status") == "ok":
            seen.append(e.get("agent", ""))
    # Duplikate eliminieren, Reihenfolge erhalten
    out: list[str] = []
    for name in seen:
        if name and name not in out:
            out.append(name)
    return out


def next_agent_to_run(
    pipeline: list[Agent],
    runs_log: Path,
    run_id: str,
) -> Agent | None:
    """
    Naechster Agent aus der Pipeline, der noch nicht erfolgreich war.

    Bricht beim ersten Agenten ab, der NICHT in der completed-Liste auftaucht.
    Gibt None zurueck, wenn alles fertig ist.
    """
    completed = set(agents_completed_in_run(runs_log, run_id))
    for agent in pipeline:
        if agent.name not in completed:
            return agent
    return None


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def _summary(runs_log: Path) -> None:
    """Tabellarische Uebersicht: pro run_id letzter Status + letzter Agent."""
    by_run: dict[str, list[dict]] = defaultdict(list)
    for e in iter_entries(runs_log):
        run_id = e.get("run_id", "?")
        by_run[run_id].append(e)

    if not by_run:
        print(f"(leer) {runs_log}")
        return

    print(f"Laeufe in {runs_log.name}:")
    print(f"{'run_id':<22}  {'Schritte':>8}  {'OK':>4}  {'Fehler':>6}  letzter Agent")
    print("-" * 80)
    for run_id, entries in by_run.items():
        ok = sum(1 for e in entries if e.get("status") == "ok")
        err = sum(1 for e in entries if e.get("status") != "ok")
        last = entries[-1]
        last_agent = last.get("agent", "")
        last_status = last.get("status", "")
        marker = "✓" if last_status == "ok" else f"⚠ ({last_status})"
        print(f"{run_id:<22}  {len(entries):>8}  {ok:>4}  {err:>6}  {last_agent} {marker}")


def _details(runs_log: Path, run_id: str) -> None:
    """Alle Schritte eines bestimmten Laufs."""
    entries = [e for e in iter_entries(runs_log) if e.get("run_id") == run_id]
    if not entries:
        print(f"Kein Lauf '{run_id}' gefunden.")
        return
    print(f"Lauf {run_id} – {len(entries)} Schritte")
    for e in entries:
        agent = e.get("agent", "?")
        status = e.get("status", "?")
        dur = e.get("duration_s", 0)
        print(f"  [{status:<14}] {agent:<18} {dur:>6}s")


def main() -> None:  # pragma: no cover
    runs_log = DEFAULT_RUNS_LOG
    if len(sys.argv) > 1:
        _details(runs_log, sys.argv[1])
    else:
        _summary(runs_log)


if __name__ == "__main__":  # pragma: no cover
    main()
