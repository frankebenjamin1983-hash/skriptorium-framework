"""Zeigt Faktenpruefer- und Lektorats-Reviews fuer ein Kapitel."""

import json
import sys
from pathlib import Path


def main() -> None:
    chapter = sys.argv[1] if len(sys.argv) > 1 else "07"
    root = Path(__file__).resolve().parent.parent / "artifacts" / "reviews"

    fp = root / f"{chapter}_facts.json"
    if fp.exists():
        r = json.loads(fp.read_text(encoding="utf-8"))
        print(f"═══ Faktenpruefer Kapitel {chapter} ═══")
        print(f"Verdict: {r.get('verdict')}")
        print(f"Char-Count: {r.get('char_count')}")
        issues = r.get("issues", [])
        print(f"Issues ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print(f"(kein {fp.name})")

    lp = root / f"{chapter}_edit.json"
    if lp.exists():
        r = json.loads(lp.read_text(encoding="utf-8"))
        print(f"\n═══ Lektorat Kapitel {chapter} ═══")
        print(f"Verdict: {r.get('suggested_diff')}")
        s = r.get("style_issues", [])
        print(f"\nStyle-Issues ({len(s)}):")
        for i in s:
            print(f"  * {i[:250]}")
        st = r.get("structure_issues", [])
        print(f"\nStruktur-/Flow-/Code-Issues ({len(st)}):")
        for i in st:
            print(f"  * {i[:250]}")
    else:
        print(f"(kein {lp.name})")


if __name__ == "__main__":
    main()
