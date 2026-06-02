"""
tools/build_real_cards.py – Heuristischer Importer.

Liest read-only aus DavidMalanVirtuell/knowledge/**_extracted.md und erzeugt
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

Aufruf (vom PyCompendium-Root):
    python -m tools.build_real_cards
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Wir wollen Cards-Schema validieren – PyCompendium-Root muss im Pfad sein.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas import Card, write_json


# ──────────────────────────────────────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────────────────────────────────────

KNOWLEDGE_ROOT = Path(r"C:\Users\bfran\Ai Projekte\DavidMalanVirtuell\knowledge")

# Pfad-Substring -> (track, default_level, source_short_prefix)
# Reihenfolge wichtig: spezifischeres zuerst.
SOURCE_MAP = [
    ("cs50p\\12_agentic",       ("advanced",       "advanced",     "cs50p_agentic")),
    ("cs50p\\02_",              ("core",           "beginner",     "cs50p_l0_functions")),
    ("cs50p\\03_",              ("core",           "beginner",     "cs50p_l1_conditionals")),
    ("cs50p\\04_",              ("core",           "beginner",     "cs50p_l2_loops")),
    ("cs50p\\05_",              ("core",           "beginner",     "cs50p_l3_exceptions")),
    ("cs50p\\06_",              ("core",           "intermediate", "cs50p_l4_libraries")),
    ("cs50p\\07_",              ("core",           "intermediate", "cs50p_l5_unit_tests")),
    ("cs50p\\08_",              ("core",           "intermediate", "cs50p_l6_file_io")),
    ("cs50p\\09_",              ("core",           "intermediate", "cs50p_l7_regex")),
    ("cs50p\\10_",              ("core",           "intermediate", "cs50p_l8_oop")),
    ("cs50p\\11_",              ("core",           "advanced",     "cs50p_l9_etcetera")),
    ("cs50x\\lektion_06_python", ("core",            "beginner",     "cs50x_l6_python")),
    ("cs50x\\CS50x.md",          ("cs_fundamentals","overview",     "cs50x_overview")),
    ("cs50x\\",                  ("cs_fundamentals","beginner",     "cs50x")),
    ("Mathplotlib\\",            ("scientific",     "intermediate", "matplotlib_yt")),
    ("Numpy\\",                  ("scientific",     "intermediate", "numpy_yt")),
    ("OOP Masterclass\\",        ("core",           "intermediate", "oop_masterclass")),
    ("PythonFabianRappert\\",    ("core",           "mixed",        "rappert")),
]


# Heading-Regex.
H_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# Manche Quellen nutzen **Bold**-Zeile statt ## H2. Wir erkennen die separat
# und mappen sie auf "virtuelles H2", wenn die Zeile nichts anderes enthält.
BOLD_AS_H2_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")


# ──────────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────────

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
      [(1, "Cs50P Lecture 0", ""),
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


def cards_from_file(file_path: Path) -> list[Card]:
    """Heuristik: H2 = topic, H3 = subtopic; Inhalt darunter = content_md."""
    track, default_level, source_short = classify_source(file_path)
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
                ))
        # H4+ werden zum vorherigen H3-Block addiert (ignorieren wir hier strukturell)

    flush_pending()
    return cards


# ──────────────────────────────────────────────────────────────────────────
# Hauptlauf
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    if not KNOWLEDGE_ROOT.exists():
        print(f"FEHLER: knowledge-Ordner nicht gefunden: {KNOWLEDGE_ROOT}", file=sys.stderr)
        sys.exit(1)

    files = sorted(KNOWLEDGE_ROOT.rglob("*_extracted.md"))
    print(f"Gefundene Quell-Dateien: {len(files)}")

    all_cards: list[Card] = []
    for f in files:
        cards = cards_from_file(f)
        print(f"  {f.relative_to(KNOWLEDGE_ROOT)} -> {len(cards)} Karten")
        all_cards.extend(cards)

    # Schreiben + validieren in einem Rutsch.
    out_dir = Path(__file__).resolve().parent.parent / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "cards_real.json"
    write_json(out_path, all_cards, model=Card)

    # Statistik.
    from collections import Counter
    by_track = Counter(c.source for c in all_cards)
    print(f"\nGesamt: {len(all_cards)} Karten in {out_path}")
    print("Verteilung nach Quelle:")
    for src, n in by_track.most_common():
        print(f"  {src:30s} {n:4d}")


if __name__ == "__main__":
    main()
