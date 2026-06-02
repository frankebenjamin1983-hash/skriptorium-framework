# PyCompendium

Agententeam aus Claude + Grok, das aus mehreren Python-Lehrmaterialien
(cs50p, OOP Masterclass, NumPy/Matplotlib, Rappert, Python-Doku) ein
zusammenhängendes deutsches Fachbuch baut – kapitelweise, mit
Quellenbelegen, ohne Redundanz.

## Stufenplan

| Stufe | Was | Status |
|-------|-----|--------|
| 1 | Pipeline-Gerüst, Schemas, Dummy-Agenten, Heuristik-Importer, Tests | ✅ |
| 2 | Echte LLM-Calls (Claude für Autor/Lektorat, Grok für Archivar/Faktenprüfer/Quiz) | offen |
| 3 | Async + Fan-out pro Kapitel | offen |
| 4 | Stilfeinheiten, Quellen-Verifikation, MkDocs-Rendering | offen |

## Quick-Start

```powershell
# Abhängigkeiten
python -m pip install -r requirements.txt

# Dummy-Pipeline durchlaufen (kein Geld, kein Netz)
python run.py

# Tests
python -m pytest -q
```

## Architektur

```
Quell-MDs (DavidMalanVirtuell)
        │
        ▼
 ┌──────────────┐
 │  Archivar    │  Grok    – Topic-Karten taggen
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │   Lektor     │  Opus    – Buch-Outline
 └──────┬───────┘
        ▼
 ┌─ pro Kapitel ─────────────────────┐
 │ Autor  → Faktenprüfer → Lektorat  │  Sonnet / Grok / Sonnet
 │                       → Quiz       │  Grok
 └──────┬─────────────────────────────┘
        ▼
 ┌──────────────┐
 │ Chefredakteur│  Opus    – Buch konsolidieren
 └──────────────┘
        ▼
   artifacts/book/
```

## Rollen

| Agent | Modell (Stufe 2) | Liest | Schreibt |
|-------|------------------|-------|----------|
| Archivar | Grok-fast | Quell-MDs / Chroma | `cards.json` |
| Lektor | Claude Opus | `cards.json` | `outline.json` |
| Autor | Claude Sonnet | `outline`, Karten | `chapters/NN.md` |
| Faktenprüfer | Grok-fast | Drafts, Karten | `reviews/NN_facts.json` |
| Lektorat | Claude Sonnet | Drafts, Fakten-Reviews | `reviews/NN_edit.json` |
| Quiz-Master | Grok-fast | `chapters` | `exercises/NN.md` |
| Chefredakteur | Claude Opus | alles | `book/` |

## Verzeichnisse

```
PyCompendium/
├── agents/          # Eine Datei pro Rolle
├── tools/           # One-Shot-Skripte (Importer)
├── sources/         # Read-only-Adapter (Chroma, später Python-Doku)
├── tests/           # pytest – deterministisch, kein Netz
├── artifacts/       # Laufzeit-Output (gitignored)
├── schemas.py       # Pydantic-Verträge
├── orchestrator.py  # Sequenzielle Pipeline + Validierung + Log
├── recovery.py      # Wiederanlauf aus runs.jsonl
├── run.py           # CLI-Entry-Point
├── style_guide.md   # Tonalität & Code-Konventionen
└── runs.jsonl       # eine JSON-Zeile pro Agent-Lauf
```

## Designentscheidungen

- **Kontext nur als Pfade + Metadaten.** Große Inhalte landen in Dateien,
  niemals im RAM-Dict. Macht Zwischenstände auf der Platte inspizierbar
  und vermeidet Memory-Bloat.
- **Pydantic-Verträge an Agenten-Grenzen.** Tippfehler in Schlüsselnamen
  werden sofort gefangen, statt im nächsten Agenten als KeyError oder
  stilles Fehlverhalten aufzutauchen.
- **Eine Datei pro Agent.** Macht Stufe 2 (Composition mit LLM-Client)
  ohne Mega-Datei-Wuchern möglich.
- **Chroma-Reader auf DavidMalanVirtuell.** Wir bauen keine zweite
  Klassifikations-Pipeline neben dem existierenden Vector-Index – nur
  einen Reader, der dessen Chunks als Karten interpretiert.

## Stand pro Stufe

### Stufe 1 (✅)

- 7-Agenten-Dummy-Pipeline (`agents/*.py`)
- Pydantic-Verträge mit Pre/Post-Validierung im Orchestrator
- `runs.jsonl` mit Run-IDs (Lauf-Auflösung möglich)
- Heuristik-Importer `tools/build_real_cards.py` → 1665 realistische Karten
- pytest-Suite (25 Tests, < 1 s)
- Style-Guide-Entwurf in `style_guide.md`

### Stufe 2 (offen)

- Composition statt Vererbung: jeder Agent bekommt einen `llm_client` im
  Konstruktor injiziert.
- `sources/chroma_reader.py` (Stub fertig) wird zur Quelle für den echten
  Archivar.
- Token-/Kosten-Tracking pro Agent in `runs.jsonl`.
- Prompts pro Rolle in `prompts/<agent>.md`.

## Sicherheits-Regeln

- Niemals in fremde Ordner schreiben. `DavidMalanVirtuell` wird
  ausschließlich lesend benutzt.
- Keine Git-Pushes, keine zerstörerischen Aktionen.
- `.env` mit API-Keys ist gitignored.
