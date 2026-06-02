"""
tools/build_real_cards.py – Heuristischer Importer.

Liest read-only aus dem Quellordner *_extracted.md und erzeugt
realistische Topic-Karten, ohne LLM. Heuristik:

  H1   = Quell-Lektion (ignoriert für Karten – steht im Pfad)
  H2   = Topic
  H3   = Subtopic
  Text/Listen unter H2/H3 = content_md

Eine Karte pro (H2, H3)-Paar. Wenn unter einem H2 kein H3 kommt, wird
das H2 selbst zur Karte.

Level + Track werden über den Quell-Pfad abgeleitet (Mapping unten).
Die Verfeinerung pro Karte (z. B. „intermediate" statt pauschaler
Default) ist Job des echten Archivars in Stufe 2.

Aufruf (vom Skriptorium-Root):
    python -m tools.build_real_cards
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Wir wollen Cards-Schema validieren – Skriptorium-Root muss im Pfad sein.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas import Card, write_json


# ──────────────────────────────────────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────────────────────────────────────

# Quellordner kommt aus:
#   1. --source CLI-Argument (hoechste Prioritaet)
#   2. Umgebungsvariable SKRIPTORIUM_SOURCE_DIR
#   3. ../knowledge_source (Fallback fuer Quick-Demo)
#
# Der Quellordner darf, soll und wird nicht im Skriptorium-Repo liegen.

# Default-Mapping fuer Pfad-Substring -> (track, default_level, source_short).
# Kann durch tools/source_map.json ueberschrieben werden (siehe load_source_map).
# Bewusst minimal: greift, wenn keine projektspezifische Konfiguration da ist.
DEFAULT_SOURCE_MAP = [
    ("python_doc",  ("core", "intermediate", "python_doc")),
    ("",            ("core", "beginner",     "source")),   # Ultimate Fallback
]


# Heading-Regex.
H_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# Manche Quellen nutzen **Bold**-Zeile statt ## H2. Wir erkennen die separat
# und mappen sie auf "virtuelles H2", wenn die Zeile nichts anderes enthält.
BOLD_AS_H2_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")


# ──────────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────────

def load_source_map() -> list[tuple[str, tuple[str, str, str]]]:
    """
    Laedt das Source-Mapping. Sucht in dieser Reihenfolge:
      1. tools/source_map.json (lokale, projektspezifische Konfiguration)
      2. DEFAULT_SOURCE_MAP (generischer Fallback)

    JSON-Format:
      [
        ["pfad_substring", ["track", "default_level", "source_short"]],
        ...
      ]
    Reihenfolge wichtig: spezifischere Eintraege zuerst.
    """
    import json
    local = Path(__file__).resolve().parent / "source_map.json"
    if local.exists():
        raw = json.loads(local.read_text(encoding="utf-8"))
        return [(item[0], tuple(item[1])) for item in raw]
    return DEFAULT_SOURCE_MAP


SOURCE_MAP = load_source_map()


def classify_source(file_path: Path) -> tuple[str, str, str]:
    """Pfad -> (track, default_level, source_short). Fallback: ('unknown', 'beginner', stem)."""
    p = str(file_path)
    for sub, value in SOURCE_MAP:
        if sub in p:
            return value
    return ("unknown", "beginner", file_path.stem)


def split_by_headings(text: str) -> list[tuple[int, str, str]]:
    """
    Zerlegt Markdown in (level, heading, body)-Blöcke.

    Beispiel-Output:
      [(1, "Quell-Lektion", ""),
       (2, "Program Execution", "- Python source files use ..."),
       (2, "Core Language Elements", ""),
       (3, "Functions", "- A function is ..."),
       ...]
    """
    blocks: list[tuple[int, str, list[str]]] = []
    current: tuple[int, str, list[str]] | None = None

    for line in text.splitlines():
        m = H_RE.match(line)
        bm = BOLD_AS_H2_RE.match(line.strip()) if not m else None
        if m:
            if current is not None:
                blocks.append(current)
            current = (len(m.group(1)), m.group(2).strip(), [])
        elif bm:
            # **Bold** alleine in Zeile -> virtuelles H2
            if current is not None:
                blocks.append(current)
            current = (2, bm.group(1).strip(), [])
        else:
            if current is None:
                current = (0, "", [])
            current[2].append(line)
    if current is not None:
        blocks.append(current)

    return [(lvl, head, "\n".join(body).strip()) for lvl, head, body in blocks]


def role_for_track(track: str) -> str:
    """
    Welche Rolle haben Karten dieses Tracks im Python-Buch?

    fundamentals = Inhalte aus angrenzenden Themen (C, SQL, HTML, etc.)
        → supplementary: nicht primär Python, taugen aber als Querverweise
        wo sie Python-Themen erhellen (z. B. C-Algorithmen → algorithmische
        Effizienz in Python).

    Alle anderen Tracks (core, scientific, advanced) → primary.
    """
    if track == "fundamentals":
        return "supplementary"
    return "primary"


def cards_from_file(file_path: Path) -> list[Card]:
    """Heuristik: H2 = topic, H3 = subtopic; Inhalt darunter = content_md."""
    track, default_level, source_short = classify_source(file_path)
    role = role_for_track(track)
    blocks = split_by_headings(file_path.read_text(encoding="utf-8", errors="ignore"))

    cards: list[Card] = []
    current_topic: str | None = None
    pending_topic_body: str = ""  # Wenn H2 Body hat, aber kein H3 folgt
    counter = 0
    seen_h3_under_topic = False

    def flush_pending():
        nonlocal counter, pending_topic_body
        if current_topic and pending_topic_body and not seen_h3_under_topic:
            counter += 1
            cards.append(Card(
                id=f"{source_short}__{counter:04d}",
                topic=current_topic,
                subtopic=current_topic,  # kein H3 → Topic auch als Subtopic
                level=default_level,
                source=source_short,
                content_md=pending_topic_body,
                role=role,
                track=track,
            ))
        pending_topic_body = ""

    for lvl, head, body in blocks:
        if lvl == 1:
            # H1 ignorieren – kommt aus dem Pfad
            continue
        elif lvl == 2:
            flush_pending()
            current_topic = head
            pending_topic_body = body
            seen_h3_under_topic = False
        elif lvl == 3:
            seen_h3_under_topic = True
            if not current_topic:
                # H3 ohne H2-Kontext → Topic = H3
                current_topic = head
            if body or head:
                counter += 1
                cards.append(Card(
                    id=f"{source_short}__{counter:04d}",
                    topic=current_topic or head,
                    subtopic=head,
                    level=default_level,
                    source=source_short,
                    content_md=body or f"_(siehe übergeordnetes Topic: {current_topic})_",
                    role=role,
                    track=track,
                ))
        # H4+ werden zum vorherigen H3-Block addiert (ignorieren wir hier strukturell)

    flush_pending()
    return cards


# ──────────────────────────────────────────────────────────────────────────
# Hauptlauf
# ──────────────────────────────────────────────────────────────────────────

def resolve_source_dir(cli_source: str | None) -> Path:
    """Aufloest: CLI -> ENV -> Fallback."""
    if cli_source:
        return Path(cli_source).expanduser().resolve()
    env_dir = os.getenv("SKRIPTORIUM_SOURCE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    fallback = Path(__file__).resolve().parent.parent.parent / "knowledge_source"
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Heuristik-Importer fuer Topic-Karten aus extrahierten MDs.",
    )
    parser.add_argument(
        "--source", metavar="DIR",
        help="Quellordner mit *_extracted.md-Dateien. "
             "Default: $SKRIPTORIUM_SOURCE_DIR oder ../knowledge_source.",
    )
    args = parser.parse_args()

    knowledge_root = resolve_source_dir(args.source)
    if not knowledge_root.exists():
        print(
            f"FEHLER: Quellordner nicht gefunden: {knowledge_root}\n"
            f"  Setze --source DIR oder Umgebungsvariable SKRIPTORIUM_SOURCE_DIR.",
            file=sys.stderr,
        )
        sys.exit(1)

    files = sorted(knowledge_root.rglob("*_extracted.md"))
    print(f"Quellordner: {knowledge_root}")
    print(f"Gefundene Quell-Dateien: {len(files)}")

    all_cards: list[Card] = []
    for f in files:
        cards = cards_from_file(f)
        print(f"  {f.relative_to(knowledge_root)} -> {len(cards)} Karten")
        all_cards.extend(cards)

    # Schreiben + validieren in einem Rutsch.
    out_dir = Path(__file__).resolve().parent.parent / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "cards_real.json"
    write_json(out_path, all_cards, model=Card)

    # Statistik.
    from collections import Counter
    by_source = Counter(c.source for c in all_cards)
    by_role = Counter(c.role for c in all_cards)
    by_track = Counter(c.track for c in all_cards)
    print(f"\nGesamt: {len(all_cards)} Karten in {out_path}")
    print("\nVerteilung nach Rolle:")
    for r, n in by_role.most_common():
        print(f"  {r:15s} {n:5d}")
    print("\nVerteilung nach Track:")
    for t, n in by_track.most_common():
        print(f"  {t:18s} {n:5d}")
    print("\nVerteilung nach Quelle (Top 10):")
    for src, n in by_source.most_common(10):
        print(f"  {src:30s} {n:4d}")


if __name__ == "__main__":
    main()
