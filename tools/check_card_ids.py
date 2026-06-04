"""Quick collision check on artifacts/cards_real.json."""
import json
from pathlib import Path

data = json.loads(
    (Path(__file__).resolve().parent.parent / "artifacts" / "cards_real.json")
    .read_text(encoding="utf-8")
)
ids = [c["id"] for c in data]
unique = set(ids)
print(f"  Gesamt-Karten:    {len(data):>5}")
print(f"  Eindeutige IDs:   {len(unique):>5}")
print(f"  Kollisionen:      {len(ids) - len(unique):>5}")
print()
print("  3 Beispiel-IDs:")
for c in data[:3]:
    print(f"    {c['id']}")
