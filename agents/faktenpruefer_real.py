"""
agents/faktenpruefer_real.py – Echter Faktenpruefer (Stufe 2).

Liest pro Kapitel den Volltext + die in den Fussnoten zitierten Karten
und schickt sie an Grok-fast mit dem Auftrag, vier Arten von Issues zu
identifizieren:

  hallucination     – Aussage steht nicht in den zitierten Karten
  unsupported       – wichtige Aussage ohne Fussnote (sollte belegt sein)
  broken_citation   – Fussnoten-Card-ID existiert nicht (in den Karten)
  contradiction     – Karte A sagt X, Karte B sagt ~X, beide zitiert

Output pro Kapitel: reviews/<id>_facts.json mit issues-Liste und Verdict.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from llm import GrokClient
from schemas import (
    Card, FactReview, FactReviewRef, FaktenpruferInput, FaktenpruferOutput,
    read_json, write_json,
)

from .base import Agent


# Erkennt alle [^...] Fußnoten – unabhaengig vom ID-Format
FOOTNOTE_RE = re.compile(r"\[\^([\w]+(?:__[\w]+)*)\]")
# Sammelliste am Ende: [^id]: id
FOOTNOTE_DEF_RE = re.compile(r"\[\^([\w]+(?:__[\w]+)*)\]:\s*(\S+)")


SYSTEM_PROMPT = """\
Du bist Faktenpruefer fuer ein deutsches Python-Lehrbuch.

Du bekommst:
1. Den Kapitel-Volltext (Markdown mit Fussnoten [^card_xxx])
2. Eine Liste der zitierten Karten als JSON (id, content_md)

Pruefe auf vier Issue-Typen:
  hallucination     Eine Aussage im Text steht NICHT in den zitierten Karten
                    -> erfunden oder falsch zugeordnet
  unsupported       Eine WICHTIGE Aussage hat KEINE Fussnote, obwohl sie
                    eine haette haben sollen (triviale Aussagen ausgenommen)
  broken_citation   Eine Fussnote zitiert eine Karte, die nicht in der Liste
                    der Original-Karten steht
  contradiction     Zwei zitierte Karten widersprechen sich, beide werden
                    im Text genutzt

Output: REINES JSON-Objekt. Kein Code-Block, keine Erklaerung davor/danach.

{
  "issues": [
    {
      "type": "hallucination|unsupported|broken_citation|contradiction",
      "location": "kurze Beschreibung WO im Text (Abschnitt/Zitat)",
      "severity": "high|medium|low",
      "explanation": "warum es ein Issue ist, was passieren sollte"
    }
  ],
  "verdict": "ok|minor_issues|major_issues"
}

Verdict-Regel:
  ok              keine Issues, oder nur low-severity unsupported
  minor_issues    bis zu 3 medium-Issues, keine high
  major_issues    >=1 high-Issue oder mehr als 3 medium-Issues
"""


class RealFaktenpruefer(Agent):
    INPUT_SCHEMA = FaktenpruferInput
    OUTPUT_SCHEMA = FaktenpruferOutput

    def __init__(
        self,
        chapter_id: str | None = None,
        model: str = "grok-4-1-fast",
        temperature: float = 0.0,
    ):
        super().__init__("Faktenprüfer")
        self.client = GrokClient(model=model, temperature=temperature)
        self.chapter_id = chapter_id

    def run(self, context: dict, artifacts_dir: Path) -> dict:
        drafts = context["chapter_drafts"]
        if self.chapter_id is not None:
            drafts = [d for d in drafts if d["id"] == self.chapter_id]
            if not drafts:
                raise ValueError(f"Kapitel '{self.chapter_id}' nicht in chapter_drafts.")

        # Karten zum Nachschlagen
        all_cards: list[Card] = read_json(
            Path(context.get("cards_path", artifacts_dir / "cards.json")), model=Card,
        )
        cards_by_id = {c.id: c for c in all_cards}

        out_dir = artifacts_dir / "reviews"
        out_dir.mkdir(exist_ok=True)

        reviews: list[FactReviewRef] = []
        for d in drafts:
            draft_path = Path(d["path"])
            text = draft_path.read_text(encoding="utf-8")

            cited_ids = self._extract_cited_card_ids(text)
            cited_cards = [cards_by_id[cid] for cid in cited_ids if cid in cards_by_id]
            missing_ids = [cid for cid in cited_ids if cid not in cards_by_id]

            print(f"  -> Kapitel {d['id']}: {len(cited_ids)} Fussnoten, "
                  f"{len(cited_cards)} Karten geladen, {len(missing_ids)} nicht gefunden")

            review = self._check_chapter(d["id"], text, cited_cards, missing_ids)

            path = out_dir / f"{d['id']}_facts.json"
            write_json(path, review, model=FactReview)
            reviews.append(FactReviewRef(
                id=d["id"], path=str(path), issue_count=len(review.issues),
            ))
            print(f"     verdict: {review.verdict}, {len(review.issues)} issues "
                  f"(in={self.client.total_tokens_in} out={self.client.total_tokens_out})")

        return {
            "facts_reviews": [r.model_dump() for r in reviews],
            "tokens_in": self.client.total_tokens_in,
            "tokens_out": self.client.total_tokens_out,
            "api_calls": self.client.calls,
        }

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_cited_card_ids(text: str) -> list[str]:
        """Liest die Fussnoten-Sammelliste am Ende des Markdowns aus."""
        ids = []
        for m in FOOTNOTE_DEF_RE.finditer(text):
            ids.append(m.group(2).strip())
        return ids

    def _check_chapter(
        self,
        chapter_id: str,
        text: str,
        cards: list[Card],
        missing_ids: list[str],
    ) -> FactReview:
        # Karten kompakt fuer Grok packen
        card_pack = [{"id": c.id, "content": c.content_md} for c in cards]

        user_msg = (
            "# Kapitel-Volltext (Markdown)\n\n"
            f"{text}\n\n"
            "# Zitierte Karten\n\n"
            f"```json\n{json.dumps(card_pack, ensure_ascii=False)}\n```\n"
        )
        if missing_ids:
            user_msg += (
                f"\n# Vorab erkannte broken_citation-Issues\n"
                f"Diese Card-IDs werden zitiert, sind aber nicht in den Karten:\n"
                f"{json.dumps(missing_ids, ensure_ascii=False)}\n"
                f"Bitte als broken_citation-Issues mit aufnehmen.\n"
            )

        result = self.client.complete_json(SYSTEM_PROMPT, user_msg, max_tokens=2500)

        # Grok ist mal grosszuegig: liefert manchmal direkt die issues-Liste
        # ohne Wrapper. Normalisieren.
        if isinstance(result, list):
            result = {"issues": result, "verdict": "minor_issues" if result else "ok"}
        if not isinstance(result, dict):
            raise ValueError(f"Grok lieferte weder dict noch list: {type(result).__name__}")

        issues_raw = result.get("issues", []) or []
        # Normalisieren auf list[str] fuer das FactReview-Schema.
        issues_strs = [
            f"[{i.get('severity','?')}] {i.get('type','?')}: "
            f"{i.get('location','')} – {i.get('explanation','')}"
            for i in issues_raw
        ]

        # HARTE PRUEFUNG: broken_citation darf nicht von Grok abhaengen.
        # Wir verifizieren das selbst und ergaenzen Issues unabhaengig vom LLM.
        broken_existing = {i.get("location") for i in issues_raw
                           if i.get("type") == "broken_citation"}
        for missing in missing_ids:
            if missing not in broken_existing:
                issues_strs.append(
                    f"[high] broken_citation: {missing} – "
                    f"Fussnote zitiert eine Karten-ID, die nicht in den "
                    f"verfuegbaren Karten existiert."
                )

        # Verdict ggf. eskalieren
        verdict = str(result.get("verdict", "ok"))
        if missing_ids:
            verdict = "major_issues" if len(missing_ids) > 3 else "minor_issues"

        return FactReview(
            chapter_id=chapter_id,
            char_count=len(text),
            issues=issues_strs,
            verdict=verdict,
        )
