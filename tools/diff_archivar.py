"""tools/diff_archivar.py – Zeigt raw vs enriched cards.

Aufruf:
    python -m tools.diff_archivar                    # alle, gruppiert nach Quelle
    python -m tools.diff_archivar --max-per-source 3 # max 3 pro Quelle
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-source", type=int, default=None,
                    help="Maximal so viele Beispiele pro Quelle anzeigen.")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent / "artifacts"
    raw = json.loads((root / "cards_real.json").read_text(encoding="utf-8"))
    enr = json.loads((root / "cards.json").read_text(encoding="utf-8"))
    by_id_raw = {c["id"]: c for c in raw}
    by_source = defaultdict(list)
    for e in enr:
        by_source[e["source"]].append(e)

    print(f"Vergleich {len(enr)} verfeinerte Karten "
          f"(aus {len(by_source)} Quellen)\n")

    n_topic_changed = 0
    n_sub_changed = 0
    n_level_changed = 0

    for source, cards in by_source.items():
        print(f"━━━ Quelle: {source}  ({len(cards)} Karten)" + "━" * 30)
        sample = cards[: args.max_per_source] if args.max_per_source else cards
        for e in sample:
            r = by_id_raw.get(e["id"], {})
            t_chg = "←" if r.get("topic") != e["topic"] else " "
            s_chg = "←" if r.get("subtopic") != e["subtopic"] else " "
            l_chg = "←" if r.get("level") != e["level"] else " "
            print(f"  {e['id']}")
            print(f"    topic    {t_chg} {r.get('topic',''):<40} -> {e['topic']}")
            print(f"    subtopic {s_chg} {r.get('subtopic',''):<40} -> {e['subtopic']}")
            print(f"    level    {l_chg} {r.get('level',''):<40} -> {e['level']}")
        print()

    # Statistik ueber alle (auch nicht angezeigt)
    for e in enr:
        r = by_id_raw.get(e["id"], {})
        if r.get("topic") != e["topic"]:
            n_topic_changed += 1
        if r.get("subtopic") != e["subtopic"]:
            n_sub_changed += 1
        if r.get("level") != e["level"]:
            n_level_changed += 1

    print("─" * 70)
    print("Statistik (Grok hat geändert):")
    print(f"  topic:    {n_topic_changed:>3} von {len(enr)}  ({n_topic_changed*100//len(enr)}%)")
    print(f"  subtopic: {n_sub_changed:>3} von {len(enr)}  ({n_sub_changed*100//len(enr)}%)")
    print(f"  level:    {n_level_changed:>3} von {len(enr)}  ({n_level_changed*100//len(enr)}%)")


if __name__ == "__main__":
    main()
