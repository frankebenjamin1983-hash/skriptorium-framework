# 📚 Skriptorium

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet%20%2B%20Opus-D97757?logo=anthropic&logoColor=white)
![Grok](https://img.shields.io/badge/xAI-Grok-000000)
![Pydantic](https://img.shields.io/badge/Pydantic-Verträge-E92063?logo=pydantic&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-2EA043)

**Ein Team aus spezialisierten KI-Agenten (Claude + Grok), das aus bereitgestellten Quellmaterialien ein zusammenhängendes deutsches Fachbuch baut — kapitelweise, mit Quellenbelegen, ohne Redundanz. Jedes Modell macht das, was es am besten kann: Grok für Tempo, Sonnet für Qualität, Opus für die Synthese.**
*A team of specialized AI agents (Claude + Grok) that turns provided source material into a coherent German textbook — chapter by chapter, with citations, without redundancy. Each model does what it's best at: Grok for speed, Sonnet for quality, Opus for synthesis.*

> Sieben Rollen in einer Pipeline: **Archivar** (Grok) taggt Topic-Karten, **Lektor** (Sonnet) baut die Outline, pro Kapitel schreiben **Autor → Faktenprüfer → Lektorat → Quiz** (Sonnet/Grok), und der **Chefredakteur** (Opus) konsolidiert alles zum Buch. Agenten-Grenzen sind durch **Pydantic-Verträge** abgesichert, Zwischenstände liegen als inspizierbare Dateien auf der Platte, und `runs.jsonl` erlaubt den Wiederanlauf.

### Beispiel-Output (`artifacts/book/chapters/03.md`)
```markdown
## 3. Wärmeübertragung in Plattenwärmetauschern

Plattenwärmetauscher übertragen Wärme zwischen zwei Fluiden über dünne,
geprägte Edelstahlplatten. Die Prägung erzwingt turbulente Strömung schon
bei niedrigen Reynolds-Zahlen — das steigert den Wärmeübergangskoeffizienten
gegenüber dem Rohrbündel deutlich. [Quelle: handbuch_kap2_extracted.md]

> **Merksatz:** Mehr Turbulenz = besserer Wärmeübergang, aber höherer Druckverlust.

### Übungsfrage
Warum erreichen Plattenwärmetauscher bei gleicher Fläche höhere Leistung als Rohrbündel?
```

---

## 🇩🇪 Was dieses Projekt demonstriert

| Bereich | Konkret |
|---|---|
| **Multi-Agenten-Orchestrierung** | 7 spezialisierte Rollen in einer sequenziellen Pipeline (+ geplantes Fan-out pro Kapitel), klare Lese-/Schreib-Verträge je Agent |
| **Modell-Routing nach Aufgabe** | Grok-fast für Taggen/Faktencheck/Quiz, Claude Sonnet für Outline/Schreiben/Lektorat, Claude Opus für die finale Synthese — kostenbewusst statt „ein Modell für alles" |
| **Robuste Pipeline** | Pydantic-Verträge an den Agenten-Grenzen (Tippfehler werden sofort gefangen), Kontext nur als Pfade+Metadaten (kein RAM-Bloat), Wiederanlauf aus `runs.jsonl` |
| **Kostendisziplin** | `--real-*`-Flags schalten echte LLM-Calls gezielt frei, Dry-Run & Dummy-Pipeline ohne Netz/Geld, dokumentierte Lauf-Kosten (z. B. Archivar ~6 Cent) |
| **Test-Disziplin** | Deterministische pytest-Suite ohne Netz, Heuristik-Importer für reproduzierbare Läufe |

## 🇬🇧 Skills demonstrated

| Area | Details |
|---|---|
| **Multi-agent orchestration** | 7 specialized roles in a sequential pipeline (+ planned per-chapter fan-out), explicit read/write contracts per agent |
| **Task-based model routing** | Grok-fast for tagging/fact-check/quiz, Claude Sonnet for outline/writing/editing, Claude Opus for final synthesis — cost-aware rather than one-model-fits-all |
| **Robust pipeline** | Pydantic contracts at agent boundaries (typos caught immediately), context as paths+metadata only (no RAM bloat), recovery from `runs.jsonl` |
| **Cost discipline** | `--real-*` flags enable real LLM calls selectively, dry-run & dummy pipeline with no network/cost, documented run costs |
| **Testing discipline** | Deterministic pytest suite with no network, heuristic importer for reproducible runs |

> Quellen sind vom Nutzer bereitzustellen (eigene Notizen, gemeinfreie Materialien, offene Doku) als Verzeichnis mit `*_extracted.md`-Dateien, angegeben über `SKRIPTORIUM_SOURCE_DIR`.

---

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
$env:SKRIPTORIUM_SOURCE_DIR = "C:\Pfad\zu\deinem\knowledge"

python -m tools.build_real_cards          # Karten aus Quellen ableiten
python -m tools.probe_keys                # Health-Check beider APIs
python run.py --only Archivar --real-archivar   # Volllauf Archivar (~6 Cent)
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

- **Kontext nur als Pfade + Metadaten.** Große Inhalte landen in Dateien, niemals im RAM-Dict. Macht Zwischenstände inspizierbar und vermeidet Memory-Bloat.
- **Pydantic-Verträge an Agenten-Grenzen.** Tippfehler in Schlüsselnamen werden sofort gefangen, statt im nächsten Agenten still durchzuschlagen.
- **Eine Datei pro Agent.** Composition statt Vererbung, jeder Agent bekommt seinen LLM-Client im Konstruktor.
- **Quellen sind extern.** Der Importer liest ausschließlich, das Quellverzeichnis bleibt außerhalb des Repos.

## CLI-Optionen

```
python run.py --list                          # Pipeline anzeigen
python run.py --dry-run                       # Plan ohne Ausführung
python run.py --clean                         # artifacts/ + runs.jsonl löschen
python run.py --only AGENT                    # nur einen Agent
python run.py --from AGENT [--to AGENT]       # Bereich
python run.py --chapter NN                    # ein Kapitel
python run.py --real-archivar [--sample N]    # echte Grok-Calls
python run.py --real-lektor / --real-autor / --real-fakt / --real-lektorat
```

## Hinweis zur Nutzung

Die erzeugten Texte stützen sich auf die vom Nutzer bereitgestellten Quellen. Für eine Veröffentlichung der Ausgabe ist sicherzustellen, dass alle Quellen entsprechend lizenziert oder selbst verfasst sind und alle nötigen Belege im Buch enthalten sind.

---

<!-- Offen für Freelance- und Projektarbeit / Open for freelance & project work — Kontakt / Contact: <E-Mail oder LinkedIn-URL eintragen> -->
