"""
agents/lektorat_real.py – Echtes Lektorat (Stufe 2).

Liest Kapitel-Volltext + (optional) Faktenpruefer-Issues + Style-Guide
und laesst Claude Sonnet didaktische und stilistische Verbesserungs-
Vorschlaege schreiben.

Vorschlaege werden als strukturierte Patches geliefert (Stelle + before +
after + Begruendung), nicht als komplettes Re-Write. So entscheidet der
Chefredakteur spaeter, was uebernommen wird, und nichts wird im Stillen
veraendert.

Output: reviews/<id>_edit.json mit suggested_diff (strukturiert).
"""

from __future__ import annotations

import json
from pathlib import Path

from llm import ClaudeClient
from schemas import (
    EditReview, EditReviewRef, LektoratInput, LektoratOutput, write_json,
)

from .base import Agent


SYSTEM_PROMPT_TEMPLATE = """\
Du bist Lektor eines deutschen Python-Lehrbuchs.

Du bekommst:
1. Den Kapitel-Volltext
2. Den Style-Guide
3. (optional) Issues vom Faktenpruefer

Aufgabe: Identifiziere bis zu 8 KONKRETE Verbesserungsvorschlaege.
Pro Vorschlag exakt: Stelle + Original-Text + verbesserter Text +
kurze Begruendung.

Pruef-Dimensionen:
  style       Verstoss gegen Tonalitaet/Stil aus dem Style-Guide
              (Ausrufezeichen am Satzende, Werbe-Sprache, künstliche
               Begeisterung, fehlende ostwestfälische Trockenheit)
  structure   Aufbau-Problem (fehlende Lernziele, falsche Reihenfolge,
              kein Zum-Mitnehmen, etc.)
  flow        Schlechter Lesefluss, holprige Uebergange, Wiederholungen
  code        Code-Konventionen nicht befolgt (.format statt f-string,
              Imports fehlen, > 15 Zeilen, kein # → Output-Marker)
  citation    Fehlende Belege fuer wichtige Aussagen (wenn nicht schon
              vom Faktenpruefer gemeldet)

Antwortformat: REINES JSON. Kein Code-Block, keine Erklaerung
davor/dahinter.

{
  "style_issues":      [{"location": "...", "before": "...", "after": "...", "reason": "..."}],
  "structure_issues":  [...],
  "flow_issues":       [...],
  "code_issues":       [...],
  "citation_issues":   [...],
  "overall_verdict":   "publish_ready|minor_revisions|major_revisions"
}

Wenn eine Dimension keine Issues hat: leere Liste.

══════════════ STYLE-GUIDE ══════════════
{style_guide}
══════════════════════════════════════════
"""


class RealLektorat(Agent):
    INPUT_SCHEMA = LektoratInput
    OUTPUT_SCHEMA = LektoratOutput

    def __init__(
        self,
        chapter_id: str | None = None,
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.3,
    ):
        super().__init__("Lektorat")
        self.client = ClaudeClient(model=model, temperature=temperature)
        self.chapter_id = chapter_id
        sg_path = Path(__file__).resolve().parent.parent / "style_guide.md"
        style_guide = sg_path.read_text(encoding="utf-8") if sg_path.exists() else ""
        # .format() faellt bei den vielen {} im JSON-Beispiel auf die Nase
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{style_guide}", style_guide)

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        drafts = context["chapter_drafts"]
        if self.chapter_id is not None:
            drafts = [d for d in drafts if d["id"] == self.chapter_id]
            if not drafts:
                raise ValueError(f"Kapitel '{self.chapter_id}' nicht in chapter_drafts.")

        facts = context.get("facts_reviews", [])
        facts_by_id = {f["id"]: f for f in facts}

        out_dir = artifacts_dir / "reviews"
        out_dir.mkdir(exist_ok=True)

        edits: list[EditReviewRef] = []
        for d in drafts:
            text = Path(d["path"]).read_text(encoding="utf-8")

            # Zugehoeriges Fakten-Review laden, falls vorhanden
            fact_summary = ""
            fact_ref = facts_by_id.get(d["id"])
            if fact_ref:
                fact_data = json.loads(Path(fact_ref["path"]).read_text(encoding="utf-8"))
                fact_summary = (
                    f"\n# Faktenpruefer-Issues (Verdict: {fact_data.get('verdict','?')})\n"
                    + "\n".join(f"- {i}" for i in fact_data.get("issues", []))
                )

            print(f"  -> Kapitel {d['id']}: {len(text):,} Zeichen, "
                  f"Fakten-Issues: {fact_ref['issue_count'] if fact_ref else '-'}")

            review = self._review_chapter(d["id"], text, fact_summary)

            path = out_dir / f"{d['id']}_edit.json"
            write_json(path, review, model=EditReview)
            edits.append(EditReviewRef(id=d["id"], path=str(path)))
            print(f"     {len(review.style_issues)} Style, "
                  f"{len(review.structure_issues)} Struktur "
                  f"(in={self.client.total_tokens_in} out={self.client.total_tokens_out})")

        return {
            "edit_reviews": [e.model_dump() for e in edits],
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _review_chapter(self, chapter_id: str, text: str, fact_summary: str) -> EditReview:
        user_msg = (
            "# Kapitel-Volltext\n\n"
            f"{text}\n"
            f"{fact_summary}\n"
        )
        result = self.client.complete_json(self.system_prompt, user_msg, max_tokens=3000)

        if not isinstance(result, dict):
            raise ValueError(f"Claude lieferte kein dict: {type(result).__name__}")

        # Issues kompakt in das vereinfachte EditReview-Schema serialisieren
        def _flatten(key: str) -> list[str]:
            items = result.get(key, []) or []
            return [
                f"{i.get('location','?')} | before: «{i.get('before','')[:80]}» | "
                f"after: «{i.get('after','')[:80]}» | reason: {i.get('reason','')}"
                for i in items
            ]

        style = _flatten("style_issues")
        struct = _flatten("structure_issues")
        flow = _flatten("flow_issues")
        code = _flatten("code_issues")
        citation = _flatten("citation_issues")

        # Wir packen flow+code+citation in structure_issues mit Prefix –
        # bewahrt das Schema, behaelt aber die Differenzierung lesbar
        struct_combined = struct + [f"[flow] {x}" for x in flow] \
                                 + [f"[code] {x}" for x in code] \
                                 + [f"[citation] {x}" for x in citation]

        return EditReview(
            chapter_id=chapter_id,
            style_issues=style,
            structure_issues=struct_combined,
            fact_issues_referenced=len(result.get("citation_issues", []) or []),
            suggested_diff=result.get("overall_verdict", ""),
        )
