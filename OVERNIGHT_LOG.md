# Nachtarbeit-Log – PyCompendium

Lückenloses Protokoll dessen, was Claude in der Nacht selbstständig erledigt
hat. Jeder Eintrag mit Zeitstempel, was gemacht wurde und was du morgens
prüfen solltest.

## Auftrag (vom Vortag)

User-Ansage: „mach alles" — Liste der grünen + gelben + orangenen Punkte aus
der vorigen Antwort:

| Nr | Was | Status |
|----|-----|--------|
| 1  | OVERNIGHT_LOG.md anlegen | ✅ |
| 2  | Style-Guide-Entwurf (style_guide.md) | ✅ |
| 3  | Echte Topic-Karten aus extracted.md ableiten | ✅ |
| 4  | requirements.txt + pyproject.toml | ✅ |
| 5  | .gitignore + git init | ✅ |
| 6  | tests/ mit pytest | ✅ |
| 7  | README.md | ✅ |
| 8  | CLI für run.py | ✅ |
| 9  | Chroma-Reader-Stub | ✅ |
| 10 | Recovery-Helper aus runs.jsonl | ✅ |
| 11 | Abschluss-Eintrag in diesem Log | ✅ |

Regeln, die ich mir selbst auferlegt habe (alle eingehalten):
- Keine API-Calls (kein Geld) ✅
- Kein Schreiben in fremde Ordner (DavidMalanVirtuell read-only) ✅
- Kein Git-Push, kein --force, keine destruktiven Aktionen ✅
- Bei Unsicherheit: stehen lassen und hier markieren ✅

---

## Einträge

### #1 – OVERNIGHT_LOG.md angelegt
Diese Datei selbst.

### #2 – Style-Guide-Entwurf
Datei: `style_guide.md`. Sieben Abschnitte: Tonalität, Aufbau eines
Kapitels, Code-Konventionen, Vokabular, Quellenbelege, Diagramme, was
der Guide nicht regelt. Drei Vorher/Nachher-Beispiele für die
Tonalität-Vorgabe „sachlich-didaktisch mit Ostwestfalen-Trockenheit".
Status: **Entwurf** – wartet auf deine Abnahme.

### #3 – Echte Topic-Karten aus extracted.md
Skript: `tools/build_real_cards.py`. Heuristisch: H2/H3-Headings +
`**Bold**`-Zeile-allein als virtuelles H2. Liest 26 Quell-Dateien aus
DavidMalanVirtuell **read-only** und erzeugt 1665 Karten in
`artifacts/cards_real.json`.

Verteilung (Quelle → Karten-Anzahl):
- cs50x: 853 (vorwiegend nicht-Python, später ggf. filtern)
- rappert: 256 (reiner Python-Kurs, sehr ergiebig)
- cs50x_l6_python: 111
- oop_masterclass: 92
- cs50p_agentic: 82
- cs50p Lectures 0–9: zusammen ~100 (Hauptspine)
- numpy_yt + matplotlib_yt: 90 (für Scientific-Track)

**Anmerkung:** cs50p liefert insgesamt wenig Karten (~100) im Vergleich
zu seinem Materialvolumen — die Lektionen sind sehr dicht in einzelnen
H2-Blöcken, der Heuristik-Parser zerlegt das nicht weiter. Das ist kein
Problem für Stufe 1, aber für Stufe 2 sollte der echte Archivar
zusätzlich pro Block sub-segmentieren.

### #4 – Dependencies festlegen
- `requirements.txt`: pydantic + pytest aktiv. Stufe-2-Pakete (anthropic,
  openai, chromadb, python-dotenv) auskommentiert – nichts wird ungewollt
  installiert.
- `pyproject.toml`: Projekt heißt `pycompendium`, Python ≥3.10, packages
  und py-modules explizit. `python -m pip install -e .` macht das Projekt
  importierbar.

### #5 – Git-Setup
- `.gitignore` mit artifacts/, runs.jsonl, .env, __pycache__/, .pytest_cache/,
  IDE-Verzeichnisse, OS-Müll.
- `git init -b main` (es gab noch kein Repo).
- Erster Commit: `7191fbf Stufe 1: Pipeline, Schemas, Style-Guide, Importer`.
- Ein zweiter Commit folgt am Ende dieses Logs mit den Nacht-Artefakten.

### #6 – Tests mit pytest
Vier Test-Dateien unter `tests/`:
- `test_schemas.py` (7) – Round-Trip, Validierung, fehlende Felder.
- `test_agents.py` (8) – jeder Dummy-Agent läuft, schreibt erwartete Artefakte.
- `test_orchestrator.py` (5) – Schema-Verletzung wird gefangen, runs.jsonl
  geschrieben, Lektor-ohne-Archivar scheitert sauber.
- `test_build_real_cards.py` (5) – Inline-Markdown-Tests gegen die Heuristik;
  greift NICHT auf externe Dateien zu.

**Ergebnis:** `pytest -q` → **25 passed in 0.31s**, kein Netzzugriff.

### #7 – README.md
Knapp. Tagline, Stufenplan-Tabelle, Quick-Start, ASCII-Architektur,
Rollen-Tabelle, Verzeichnis-Übersicht, Designentscheidungen, Status pro
Stufe. Scannbar.

### #8 – CLI für run.py
argparse mit `--list`, `--dry-run`, `--clean`, `--only AGENT`, `--from AGENT`.
Kontext-Rebuild aus Artefakten via `restore_context_from_artifacts()` —
liest cards.json / outline.json / chapters/*.md / reviews/*.json / exercises/*.md
und baut den Kontext-Dict so, dass `--from Autor` den Autor mit allem
versorgt, was er per INPUT_SCHEMA braucht.

Verifiziert:
- `python run.py --list` → 7 Agenten ✓
- `python run.py --dry-run` → Plan ohne Ausführung ✓
- `python run.py --clean` → frischer kompletter Lauf ✓
- `python run.py --from Autor` → Kontext rekonstruiert, 5 Agenten ✓
- `python run.py --only Lektor` mit Artefakten → ok ✓
- `python run.py --clean --only Lektor` → klare SchemaViolation mit Exit 1 ✓

### #9 – Chroma-Reader-Stub
- `sources/chroma_reader.py` mit Klasse `DavidMalanChromaReader`.
- chromadb wird **lazy importiert** (erst im Konstruktor) — Stufe 1 läuft
  ohne installierte chromadb-Abhängigkeit.
- API: `count()`, `iter_chunks(batch_size)`, `list_collections()`.
- Verifiziert: Modul-Import funktioniert ohne chromadb (Test war
  `from sources.chroma_reader import DavidMalanChromaReader, Chunk`).
- **Anmerkung:** Default-Collection-Name ist `"knowledge"`. Bitte morgen
  einmal mit `python -m sources.chroma_reader` prüfen, wie die Collection
  in deinem DavidMalanVirtuell tatsächlich heißt — wenn nicht „knowledge",
  zeigt der Reader die echten Namen in der Fehlermeldung.

### #10 – Recovery-Helper
- `recovery.py` mit `last_successful_run_id()`, `agents_completed_in_run()`,
  `next_agent_to_run(pipeline, log, run_id)`.
- CLI: `python -m recovery` → Tabelle aller Läufe.
- CLI: `python -m recovery <run_id>` → Schritt-für-Schritt für einen Lauf.
- Verifiziert mit dem aktuellen runs.jsonl: erkennt sauber Lauf
  20260602T085747Z als komplett (alle 7 Agenten ok).
- **Nicht** in Stufe 1 mit dem Orchestrator verkabelt. Steht parat für Stufe 2.

### #11 – Dieser Eintrag
Plus zweiter Commit mit allen Nacht-Artefakten.

---

## Morgens-Checkliste

Wenn du den Rechner öffnest:

```powershell
cd "C:\Users\bfran\Ai Projekte\PyCompendium"

# 1. Tests müssen grün sein
python -m pytest -q

# 2. Dummy-Pipeline muss laufen
python run.py --clean

# 3. CLI-Hilfe ansehen
python run.py --list

# 4. Recovery-Übersicht
python -m recovery

# 5. Git-Status: clean?
git log --oneline
git status
```

**Inhaltlich anschauen:**
1. **`style_guide.md`** — Tonalität-Beispiele, Vokabular, Code-Konventionen.
   Das ist die Grundlage für jeden Stufe-2-Lauf. Abnicken oder ändern.
2. **`artifacts/cards_real.json`** — Stichprobe: passt die Karte zur Quelle?
   Vorschlag: einfach `python -c "import json; data=json.load(open('artifacts/cards_real.json','r',encoding='utf-8')); print(data[100])"`
3. **`README.md`** — stimmt der Projekt-Pitch? Architektur-Diagramm OK?
4. **Verteilung der Karten** (im Log oben unter #3) — cs50x liefert 853
   Karten, aber das ist großteils nicht-Python. Möchtest du das vor dem
   Lektor-Lauf in Stufe 2 filtern (nur „core"-Track), oder soll cs50x
   z. B. in eigene Anhang-Kapitel?

## Entschiedene Punkte (Nachgelagert)

**Karten-Filter für cs50x (Frage 2 oben)** — Entscheidung des Users:
„berücksichtigen bei Zusammenhängen". Umgesetzt durch zwei neue Felder
im Card-Schema:

- `role`: `primary` (Kernmaterial, gehört in Kapitel-Volltext) oder
  `supplementary` (Hintergrund/Querverweis, nur wo passender Zusammenhang)
- `track`: `core` / `scientific` / `advanced` / `cs_fundamentals`

Aktuelle Verteilung der 1665 Karten:
- **Primary: 734** (562 core + 90 scientific + 82 advanced)
- **Supplementary: 931** (alles cs_fundamentals = cs50x außer Lecture 6
  Python, die als Ausnahme primary bleibt)

Der Stufe-2-Lektor bekommt im System-Prompt die Anweisung, primary als
Bauplan und supplementary nur als Querverweis-Pool zu behandeln. Die
Regel steht zusätzlich im `style_guide.md` (Abschnitt 8).

Tests prüfen die Rollen-Zuordnung (`test_role_assignment_*`). 28/28 grün.

## Offene Fragen für dich

1. **Chroma-Collection-Name**: in `sources/chroma_reader.py` steht
   `DEFAULT_COLLECTION = "knowledge"`. Bitte morgen mit
   `python -m sources.chroma_reader` prüfen, ob das stimmt — sonst
   gibt der Reader die echten Namen in der Fehlermeldung aus.
2. **API-Keys**: `.env` mit `ANTHROPIC_API_KEY` und `XAI_API_KEY` brauchen
   wir vor dem ersten echten Stufe-2-Lauf. Aktuell weder Datei noch Keys
   im Projekt — bewusst, damit nichts versehentlich ausgelöst wird.

## Was BEWUSST nicht passiert ist

- Keine echten LLM-Aufrufe (selbst auferlegte Regel)
- Kein `pip install chromadb` / `anthropic` / `openai` — das käme erst
  mit der ersten Stufe-2-Aktion und sollte mit dir abgestimmt sein
- Kein `git push` — das Repo ist lokal, kein Remote eingerichtet
- Kein Anfassen von DavidMalanVirtuell außer lesend
