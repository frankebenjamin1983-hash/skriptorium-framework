"""
tests/conftest.py – gemeinsame Fixtures.

Wir wollen Tests, die:
  - in einem isolierten Temp-Verzeichnis laufen (kein Stören am echten artifacts/)
  - keine Abhängigkeit auf externe Dateien haben
  - keine Netzwerk-Calls auslösen
"""

import sys
from pathlib import Path

import pytest

# Projekt-Root in sys.path, damit `from agents import ...` ohne Install funktioniert.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_artifacts(tmp_path: Path) -> Path:
    """Frisches artifacts/-Verzeichnis pro Test."""
    d = tmp_path / "artifacts"
    d.mkdir()
    return d
