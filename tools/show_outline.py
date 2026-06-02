"""Zeigt artifacts/outline.json als lesbares Inhaltsverzeichnis."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    path = Path(__file__).resolve().parent.parent / "artifacts" / "outline.json"
    d = json.loads(path.read_text(encoding="utf-8"))

    print(f"BUCHTITEL:   {d['book_title']}")
    if "subtitle" in d:
        print(f"UNTERTITEL:  {d['subtitle']}")
    print()

    current_part = None
    for ch in d["chapters"]:
        if ch.get("part") != current_part:
            current_part = ch.get("part")
            print(f"\n══════ {current_part} ══════")
        topics = ch.get("topics") or [ch.get("topic", "")]
        topics_str = ", ".join(t for t in topics if t)
        print(f"\n  Kapitel {ch['id']}: {ch['title']}")
        print(f"    Themen ({len(ch['card_ids'])} Karten): {topics_str}")
        for obj in ch.get("learning_objectives", [])[:4]:
            print(f"      - {obj}")


if __name__ == "__main__":
    main()
