# Skriptorium

Agententeam aus Claude + Grok, das aus extrahierten Lehrmaterialien
ein zusammenhängendes deutsches Fachbuch baut – kapitelweise, mit
Quellenbelegen, ohne Redundanz.

Quellen sind vom Nutzer bereitzustellen (z. B. eigene Notizen,
gemeinfreie Materialien, offene Dokumentationen). Erwartet wird ein
Verzeichnis mit Markdown-Dateien nach dem Muster `*_extracted.md`,
das per Umgebungsvariable `SKRIPTORIUM_SOURCE_DIR` angegeben wird.

## Stufenplan

| Stufe | Was | Status |
|-------|-----|--------|
| 1 | Pipeline-Gerüst, Schemas, Dummy-Agenten, Heuristik-Importer, Tests | ✅ |
| 2 | Echte LLM-Calls für Archivar / Lektor / Autor / Faktenprüfer / Lektorat | ✅ |
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

Für die LLM-Pipeline:

```powershell
# .env anlegen (siehe .env.example) mit ANTHROPIC_API_KEY und XAI_API_KEY
# Quellordner setzen
$env:SKRIPTORIUM_SOURCE_DIR = "C:\Pfad\zu\deinem\knowledge"

# Karten aus Quellen ableiten
python -m tools.build_real_cards

# Health-Check beider APIs
python -m tools.probe_keys

# Volllauf Archivar (~6 Cent)
python run.py --only Archivar --real-archivar
```

## Architektur

```
Quell-MDs (SKRIPTORIUM_SOURCE_DIR)
        │
        ▼
 ┌──────────────┐
 │  Archivar    │  Grok    – Topic-Karten taggen
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │   Lektor     │  Sonnet  – Buch-Outline
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
| Archivar | Grok-fast | Quell-MDs | `cards.json` |
| Lektor | Claude Sonnet | `cards.json` | `outline.json` |
| Autor | Claude Sonnet | `outline`, Karten | `chapters/NN.md` |
| Faktenprüfer | Grok-fast | Drafts, Karten | `reviews/NN_facts.json` |
| Lektorat | Claude Sonnet | Drafts, Fakten-Reviews | `reviews/NN_edit.json` |
| Quiz-Master | Grok-fast | `chapters` | `exercises/NN.md` |
| Chefredakteur | Claude Opus | alles | `book/` |

## Verzeichnisse

```
Skriptorium/
├── agents/          # Eine Datei pro Rolle
├── tools/           # One-Shot-Skripte (Importer, Inspektion)
├── sources/         # Read-only-Adapter (Chroma-Stub für Stufe 3)
├── tests/           # pytest – deterministisch, kein Netz
├── artifacts/       # Laufzeit-Output (gitignored)
├── llm.py           # Adapter um Anthropic- und xAI-SDKs
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
- **Eine Datei pro Agent.** Composition statt Vererbung, jeder Agent
  bekommt seinen LLM-Client im Konstruktor.
- **Quellen sind extern.** Der Importer liest ausschließlich, das
  Quellverzeichnis bleibt außerhalb des Repos.

## CLI-Optionen

```
python run.py --list                          # Pipeline anzeigen
python run.py --dry-run                       # Plan ohne Ausführung
python run.py --clean                         # artifacts/ + runs.jsonl löschen
python run.py --only AGENT                    # nur einen Agent
python run.py --from AGENT [--to AGENT]       # Bereich
python run.py --chapter NN                    # ein Kapitel
python run.py --real-archivar [--sample N]    # echte Grok-Calls
python run.py --real-lektor                   # echter Lektor
python run.py --real-autor                    # echter Autor
python run.py --real-fakt                     # echter Faktenprüfer
python run.py --real-lektorat                 # echtes Lektorat
```

## Hinweis zur Nutzung

Die mit diesem Werkzeug erzeugten Texte stützen sich auf die vom
Nutzer bereitgestellten Quellen. Für eine Veröffentlichung der Ausgabe
ist sicherzustellen, dass alle Quellen entsprechend lizenziert oder
selbst verfasst sind und alle nötigen Belege im Buch enthalten sind.
