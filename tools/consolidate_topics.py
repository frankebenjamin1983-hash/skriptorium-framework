"""
tools/consolidate_topics.py – Mapt 722 zersplitterte Topics auf 30-50 kanonische.

Liest artifacts/cards.json (Output vom Echt-Archivar), sammelt alle
eindeutigen Topics + ihre Kartenzahl, schickt die Liste an Grok mit dem
Auftrag, sie auf eine kanonische deutsche Themenstruktur zu konsolidieren.

Output:
  artifacts/topic_mapping.json   – {raw_topic: canonical_topic}
  artifacts/cards.json           – ueberschrieben mit kanonischen Topics
  artifacts/cards_grok.json      – Backup des Pre-Konsolidierungs-Stands

Spezielle Werte im Mapping:
  __example__       Karte ist eine Beispielanwendung (Einkaufslisten-App etc.)
                    – nicht als Topic im Buch fuehren, aber als Code-Quelle behalten
  __nicht_python__  Inhalt ist nicht Python (C, HTML, SQL ohne Python-Bezug)

Aufruf:
    python -m tools.consolidate_topics
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import GrokClient
from schemas import Card, read_json, write_json


SYSTEM_PROMPT = """\
Du baust die Themen-Struktur fuer ein deutsches Python-Lehrbuch
(Anfaenger bis Fortgeschritten). Aus extrahierten Lehrmaterialien
liegt eine zersplitterte Topic-Liste vor.

Deine Aufgabe: konsolidiere auf 30-50 KANONISCHE deutsche
Buch-Themen. Jedes Eingangs-Topic wird auf genau ein kanonisches
Topic gemappt.

Regeln:

1. SYNONYME UND VARIANTEN VERSCHMELZEN
   "For-Schleifen", "While-Schleifen", "Schleifen", "Iteration"
       -> "Schleifen"
   "Exception Handling", "Fehlerbehandlung", "Try-Except"
       -> "Fehlerbehandlung"
   "OOP", "Klassen", "Klassen und Objekte", "Objektorientiertes Programmieren"
       -> "Klassen und Objekte"

2. BEISPIELE/APPS sind KEINE Topics
   "Einkaufslisten-App", "ATM-Programm", "Snake-Spiel", "Phonebook"
       -> "__example__"

3. NICHT-PYTHON-INHALTE markieren
   "HTML", "CSS", "SQL", "C-Pointers", "Flask", "JavaScript"
       -> "__nicht_python__"
   Ausnahme: Themen die ZWAR aus C/SQL kommen, aber Python-relevant sind
   (z. B. "Speichermodell", "Datenstrukturen") -> in passendes Python-Thema.

4. ZIELANZAHL kanonischer Topics: 30-50.
   Zu wenige = zu grobschlaechtig, zu viele = wieder fragmentiert.

5. KANONISCHE NAMEN sind kurz, deutsch, max. 4 Woerter, Substantiv-Stil:
   "Funktionen", "Listen und Tupel", "Klassen und Objekte",
   "Module und Pakete", "Dateien lesen und schreiben",
   "Algorithmische Effizienz", "Dekoratoren".

Output: REINES JSON-Objekt mit ALLEN Eingangs-Topics als Schluessel
und dem jeweiligen kanonischen Topic als Wert. Kein Code-Block, keine
Erklaerung davor oder dahinter.

Beispiel-Antwort:
{"For-Schleifen": "Schleifen", "Iteration": "Schleifen", ...}
"""


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "artifacts"
    cards_path = root / "cards.json"
    backup_path = root / "cards_grok.json"
    mapping_path = root / "topic_mapping.json"

    if not cards_path.exists():
        raise SystemExit(f"Fehlt: {cards_path}. Erst Archivar laufen lassen.")

    cards = read_json(cards_path, model=Card)
    print(f"Geladen: {len(cards)} Karten")

    topic_counts = Counter(c.topic for c in cards)
    topics_sorted = sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))
    print(f"Eindeutige Topics: {len(topic_counts)}")

    # Eingabe fuer Grok: Topic + Anzahl Karten, als kompakte Liste
    lines = [f"{topic}\t({n})" for topic, n in topics_sorted]
    user_msg = "Topics + Anzahl Karten:\n\n" + "\n".join(lines)

    # grok-4 (nicht -fast) fuer diesen einen Reasoning-Aufruf
    client = GrokClient(model="grok-4", temperature=0.1)
    print(f"\nSchicke an {client.model} ...")
    mapping = client.complete_json(SYSTEM_PROMPT, user_msg, max_tokens=16000)

    if not isinstance(mapping, dict):
        raise SystemExit(f"Grok lieferte kein Dict, sondern {type(mapping).__name__}")

    print(f"Mapping erhalten: {len(mapping)} Eintraege "
          f"({client.total_tokens_in} in, {client.total_tokens_out} out Tokens)")

    # Sicher: jeder rohe Topic muss im Mapping sein
    missing = [t for t in topic_counts if t not in mapping]
    if missing:
        print(f"\nWARNUNG: {len(missing)} Topics nicht im Mapping. "
              f"Beispiele: {missing[:5]}")
        print("  -> Fuer diese behalten wir das urspruengliche Topic.")

    # Backup vor Ueberschreiben
    cards_path.replace(backup_path)
    print(f"\nBackup: {backup_path.name}")

    # Mapping speichern
    mapping_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Mapping gespeichert: {mapping_path.name}")

    # Karten umschreiben
    updated: list[Card] = []
    for c in cards:
        new_topic = mapping.get(c.topic, c.topic)
        updated.append(Card(
            id=c.id, topic=new_topic, subtopic=c.subtopic, level=c.level,
            source=c.source, content_md=c.content_md, role=c.role, track=c.track,
        ))
    write_json(cards_path, updated, model=Card)

    # Statistik
    new_counts = Counter(c.topic for c in updated)
    print(f"\nKanonische Topics nach Konsolidierung: {len(new_counts)}")
    print(f"\nTop 30:")
    for t, n in new_counts.most_common(30):
        print(f"  {n:>4}  {t}")

    n_example = new_counts.get("__example__", 0)
    n_nonpy = new_counts.get("__nicht_python__", 0)
    print(f"\nSonderkategorien:")
    print(f"  __example__       {n_example:>4}")
    print(f"  __nicht_python__  {n_nonpy:>4}")


if __name__ == "__main__":
    main()
