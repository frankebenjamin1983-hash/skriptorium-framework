"""
orchestrator.py – Führt eine Liste von Agenten sequenziell aus.

Verantwortlich für:
  - Kontext-Weitergabe (Output_n -> Input_n+1)
  - Artefakte-Verzeichnis bereitstellen
  - Schema-Validierung an den Agenten-Grenzen (pre + post)
  - runs.jsonl-Log (eine Zeile pro Agent-Lauf)
  - Fehler propagieren, aber davor loggen

NICHT verantwortlich für:
  - Parallelität (Stufe 3)
  - Retry/Backoff (Stufe 2, sobald echte APIs ins Spiel kommen)
  - Caching
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from agents.base import Agent


class SchemaViolation(RuntimeError):
    """Geworfen, wenn Kontext-Input oder Agent-Output nicht zum Schema passt."""


class Orchestrator:
    def __init__(self, project_root: Path):
        self.root = Path(project_root)
        self.artifacts_dir = self.root / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.runs_log = self.root / "runs.jsonl"

    # ────────────────────────────────────────────────────────────────────
    # Öffentliches API
    # ────────────────────────────────────────────────────────────────────

    def run(self, agents: list[Agent], initial_context: dict | None = None) -> dict:
        context: dict = dict(initial_context or {})
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        print(f"\n=== Lauf {run_id} – {len(agents)} Agent(en) ===")

        for agent in agents:
            self._run_one(agent, context, run_id)

        print(f"\n=== Lauf {run_id} fertig ===")
        return context

    # ────────────────────────────────────────────────────────────────────
    # Intern
    # ────────────────────────────────────────────────────────────────────

    def _run_one(self, agent: Agent, context: dict, run_id: str) -> None:
        print(f"\n→ {agent.name} …", end=" ", flush=True)
        t0 = time.time()

        # ---- Pre-Validierung: hat der Kontext, was der Agent braucht? ----
        if agent.INPUT_SCHEMA is not None:
            try:
                agent.INPUT_SCHEMA.model_validate(context)
            except ValidationError as exc:
                duration = time.time() - t0
                self._log(run_id, agent.name, "input_invalid", duration,
                          {"errors": exc.errors()})
                print(f"INPUT INVALID: {self._format_errors(exc)}")
                raise SchemaViolation(
                    f"{agent.name}: Input-Schema verletzt – {self._format_errors(exc)}"
                ) from exc

        # ---- Eigentlicher Lauf ----
        try:
            update = agent.run(context, self.artifacts_dir)
        except Exception as exc:
            duration = time.time() - t0
            self._log(run_id, agent.name, "error", duration, {"error": repr(exc)})
            print(f"FEHLER ({duration:.2f}s): {exc}")
            raise

        # ---- Post-Validierung: liefert der Agent, was er soll? ----
        if not isinstance(update, dict):
            duration = time.time() - t0
            self._log(run_id, agent.name, "bad_return_type", duration,
                      {"got": type(update).__name__})
            raise TypeError(
                f"{agent.name}.run() muss dict zurückgeben, bekam {type(update).__name__}"
            )

        if agent.OUTPUT_SCHEMA is not None:
            try:
                agent.OUTPUT_SCHEMA.model_validate(update)
            except ValidationError as exc:
                duration = time.time() - t0
                self._log(run_id, agent.name, "output_invalid", duration,
                          {"errors": exc.errors(), "got_keys": sorted(update.keys())})
                print(f"OUTPUT INVALID: {self._format_errors(exc)}")
                raise SchemaViolation(
                    f"{agent.name}: Output-Schema verletzt – {self._format_errors(exc)}"
                ) from exc

        # ---- OK ----
        duration = time.time() - t0
        context.update(update)
        self._log(run_id, agent.name, "ok", duration, update)
        print(f"ok ({duration:.2f}s)  -> {list(update.keys())}")

    def _log(self, run_id: str, agent_name: str, status: str, duration_s: float, payload: dict) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "agent": agent_name,
            "status": status,
            "duration_s": round(duration_s, 3),
            "payload": payload,
        }
        with self.runs_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _format_errors(exc: ValidationError) -> str:
        """Kompakte, lesbare Zusammenfassung der Pydantic-Fehler."""
        parts = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e["loc"]) or "<root>"
            parts.append(f"{loc}: {e['msg']}")
        return "; ".join(parts)
