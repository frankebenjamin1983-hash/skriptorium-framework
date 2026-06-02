"""
agents/revisor_real.py – Revisor (Stufe 2).

Liest Kapitel-Draft + Lektorat-Review (+ Fakten-Review wenn vorhanden)
und laesst Claude Sonnet die Verbesserungsvorschlaege in den Volltext
einarbeiten. Output: revidiertes Kapitel UEBERSCHREIBT chapters/NN.md
(Original-Stand bleibt in der Git-Historie nachvollziehbar).

Zusaetzlich: revisions/NN_applied.json als Audit-Trail – was wurde
geaendert, welche Anmerkungen wurden uebernommen.

Modell: claude-sonnet-4-5. Reasoning ueber Style/Struktur/Code ist
genau Sonnets Staerke; Opus waere Overkill.
"""

from __future__ import annotations

import json
from pathlib import Path

from llm import ClaudeClient
from schemas import (
    ChapterDraftRef, RevisorInput, RevisorOutput,
)

from .base import Agent


SYSTEM_PROMPT_TEMPLATE = """\
Du bist Revisor eines deutschen Python-Lehrbuchs.

Du bekommst:
1. Den Kapitel-Volltext (Markdown)
2. Strukturierte Verbesserungsvorschlaege vom Lektorat
3. Optional: Issues vom Faktenpruefer

Aufgabe: Arbeite ALLE Vorschlaege ein und liefere den REVIDIERTEN Volltext
zurueck. Behalte das gleiche Format (Markdown, ## H2 / ### H3, Code-Bloecke,
Fussnoten). Aendere NICHT:
- Die Card-IDs in Fussnoten (z. B. [^source_a__0003]) und die Sammelliste
  am Kapitelende. Die ID-Form ist verbindlich.
- Das Lernziele-Briefing (uebernimm 1:1 oder leichte Aufraeumung).

Aendere AKTIV:
- Stil/Tonalitaet entsprechend den Lektorat-Hinweisen
- Struktur-Reihenfolgen (z. B. Docstrings nach vorne, falls Lektorat das
  vorschlaegt)
- Fluss/Uebergaenge zwischen Abschnitten
- Code-Konventionen (z. B. Type Hints nachruesten, falls Lektorat das
  bemerkt hat und das Kapitel >= 05 ist)
- Fehlende Citations (Lektorat citation_issues) – passende vorhandene
  Card-ID in der Naehe zuordnen, KEINE neue ID erfinden

Wenn ein Lektorat-Vorschlag inhaltlich falsch oder unklug ist, ueberspringe
ihn still (kein Streit-Kommentar im Text).

Antwortformat: REINER Markdown-Volltext des revidierten Kapitels.
Kein "Hier ist die Revision:" davor, keine Erklaerung dahinter.

══════════════ STYLE-GUIDE ══════════════
{style_guide}
══════════════════════════════════════════
"""


class RealRevisor(Agent):
    INPUT_SCHEMA = RevisorInput
    OUTPUT_SCHEMA = RevisorOutput

    def __init__(
        self,
        chapter_id: str | None = None,
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.3,
        max_output_tokens: int = 6000,
    ):
        super().__init__("Revisor")
        self.client = ClaudeClient(model=model, temperature=temperature)
        self.chapter_id = chapter_id
        self.max_output_tokens = max_output_tokens
        sg_path = Path(__file__).resolve().parent.parent / "style_guide.md"
        style_guide = sg_path.read_text(encoding="utf-8") if sg_path.exists() else ""
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{style_guide}", style_guide)

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        drafts = context["chapter_drafts"]
        edit_reviews_by_id = {e["id"]: e for e in context["edit_reviews"]}
        facts_by_id = {f["id"]: f for f in context.get("facts_reviews", [])}

        if self.chapter_id is not None:
            drafts = [d for d in drafts if d["id"] == self.chapter_id]
            if not drafts:
                raise ValueError(f"Kapitel '{self.chapter_id}' nicht in chapter_drafts.")

        revisions_dir = artifacts_dir / "revisions"
        revisions_dir.mkdir(exist_ok=True)

        new_drafts: list[ChapterDraftRef] = []
        for d in drafts:
            chapter_id = d["id"]
            draft_path = Path(d["path"])
            original_text = draft_path.read_text(encoding="utf-8")
            original_chars = len(original_text)

            edit_ref = edit_reviews_by_id.get(chapter_id)
            if not edit_ref:
                print(f"  -> Kapitel {chapter_id}: kein Lektorat-Review – uebersprungen")
                new_drafts.append(ChapterDraftRef(**d))
                continue

            edit_data = json.loads(Path(edit_ref["path"]).read_text(encoding="utf-8"))
            facts_data = None
            if chapter_id in facts_by_id:
                facts_data = json.loads(
                    Path(facts_by_id[chapter_id]["path"]).read_text(encoding="utf-8")
                )

            print(f"  -> Kapitel {chapter_id}: revidiere ({original_chars:,} Zeichen)")

            revised_text = self._revise_chapter(original_text, edit_data, facts_data)
            new_chars = len(revised_text)

            # Original wird ueberschrieben (Git-Historie = Audit-Trail)
            draft_path.write_text(revised_text, encoding="utf-8")
            new_drafts.append(ChapterDraftRef(
                id=chapter_id, path=str(draft_path), chars=new_chars,
            ))

            # Audit-Trail
            audit = {
                "chapter_id": chapter_id,
                "before_chars": original_chars,
                "after_chars": new_chars,
                "delta_chars": new_chars - original_chars,
                "lektorat_verdict": edit_data.get("suggested_diff"),
                "lektorat_style_count": len(edit_data.get("style_issues", [])),
                "lektorat_structure_count": len(edit_data.get("structure_issues", [])),
                "facts_verdict": facts_data.get("verdict") if facts_data else None,
            }
            (revisions_dir / f"{chapter_id}_applied.json").write_text(
                json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            print(f"     fertig ({new_chars:,} Zeichen, Δ={new_chars-original_chars:+d}; "
                  f"in={self.client.total_tokens_in} out={self.client.total_tokens_out})")

        return {
            "chapter_drafts": [d.model_dump() for d in new_drafts],
            "revisions_dir": str(revisions_dir),
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _revise_chapter(
        self,
        text: str,
        edit_data: dict,
        facts_data: dict | None,
    ) -> str:
        user_msg_parts = [
            "# Kapitel-Volltext\n",
            text,
            "\n# Lektorat-Vorschlaege\n",
            f"Verdict: {edit_data.get('suggested_diff', '?')}\n",
            "Style-Issues:\n",
            *[f"- {s}\n" for s in edit_data.get("style_issues", [])],
            "Struktur/Flow/Code/Citation-Issues:\n",
            *[f"- {s}\n" for s in edit_data.get("structure_issues", [])],
        ]
        if facts_data and facts_data.get("issues"):
            user_msg_parts.extend([
                "\n# Fakten-Issues (zur Beachtung beim Revidieren)\n",
                f"Verdict: {facts_data.get('verdict', '?')}\n",
                *[f"- {s}\n" for s in facts_data.get("issues", [])],
            ])

        user_msg = "".join(user_msg_parts)
        return self.client.complete_text(
            self.system_prompt, user_msg, max_tokens=self.max_output_tokens,
        )
