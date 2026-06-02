"""
Tests fuer Orchestrator: Validierungs-Fangstellen + runs.jsonl-Schreibung.
"""

import json
from pathlib import Path

import pytest

from agents import DummyArchivar, DummyLektor
from agents.base import Agent
from orchestrator import Orchestrator, SchemaViolation
from schemas import ArchivarOutput


class BrokenOutputArchivar(Agent):
    """Liefert absichtlich falschen Schluessel."""
    OUTPUT_SCHEMA = ArchivarOutput

    def __init__(self):
        super().__init__("BrokenArchivar")

    def run(self, context, artifacts_dir):
        # falscher Key: 'cards_pat' statt 'cards_path'
        return {"cards_pat": "x", "cards_count": 0}


class BrokenReturnTypeAgent(Agent):
    """Gibt kein Dict zurueck."""
    def __init__(self):
        super().__init__("Broken")

    def run(self, context, artifacts_dir):
        return ["not", "a", "dict"]


def test_pipeline_runs_clean(tmp_path: Path):
    orch = Orchestrator(project_root=tmp_path)
    ctx = orch.run([DummyArchivar(), DummyLektor()])
    assert "cards_path" in ctx
    assert "outline_path" in ctx


def test_schema_violation_on_bad_output(tmp_path: Path):
    orch = Orchestrator(project_root=tmp_path)
    with pytest.raises(SchemaViolation):
        orch.run([BrokenOutputArchivar()])


def test_type_error_on_non_dict_return(tmp_path: Path):
    orch = Orchestrator(project_root=tmp_path)
    with pytest.raises(TypeError):
        orch.run([BrokenReturnTypeAgent()])


def test_runs_jsonl_written(tmp_path: Path):
    orch = Orchestrator(project_root=tmp_path)
    orch.run([DummyArchivar()])
    log = tmp_path / "runs.jsonl"
    assert log.exists()
    entries = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert entries
    assert entries[-1]["agent"] == "Archivar"
    assert entries[-1]["status"] == "ok"


def test_input_validation_blocks_lektor_without_archivar(tmp_path: Path):
    """Lektor ohne vorherigen Archivar -> Input-Schema-Verletzung."""
    orch = Orchestrator(project_root=tmp_path)
    with pytest.raises(SchemaViolation):
        orch.run([DummyLektor()])
