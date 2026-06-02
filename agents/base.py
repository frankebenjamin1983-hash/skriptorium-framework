"""
agents/base.py – Agent-Basisklasse.

Ein Agent ist ein eigenständiger Bearbeitungsschritt im Buch-Workflow.
Er bekommt einen Kontext (Dict mit Artefakten der Vor-Agenten) und ein
Artefakte-Verzeichnis, in das er seine Outputs als Dateien schreibt.

Schema-Verträge:
  - INPUT_SCHEMA: Pydantic-Modell, das beschreibt, was der Agent
    vom Kontext braucht. Wenn None: keine Pre-Validierung.
  - OUTPUT_SCHEMA: Pydantic-Modell, das beschreibt, was run() im
    Rückgabe-Dict liefern muss. Wenn None: keine Post-Validierung.

Der Orchestrator validiert beides um run() herum. Das fängt Tippfehler
in Schlüsselnamen sofort, statt sie im nächsten Agenten als KeyError
oder stilles Fehlverhalten auftauchen zu lassen.

Was wir BEWUSST nicht in die Basisklasse stecken:
  - LLM-Clients (kommt in Stufe 2 als Composition)
  - Async (kommt in Stufe 3)
  - Token-/Kosten-Tracking (kommt in Stufe 2 mit echten Calls)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel


class Agent(ABC):
    """Basisklasse für alle Agenten."""

    # Subklassen überschreiben diese mit konkreten Pydantic-Modellen.
    INPUT_SCHEMA: ClassVar[type[BaseModel] | None] = None
    OUTPUT_SCHEMA: ClassVar[type[BaseModel] | None] = None

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, context: dict, artifacts_dir: Path) -> dict:
        """
        Führt den Agenten aus.

        context: Dict mit Artefakten der vorherigen Agenten. Werte sind
                 primitive Daten oder Pfade als Strings, NIE große
                 Inhalte (die landen in Dateien).

        artifacts_dir: Wohin der Agent seine Artefakte schreiben darf.

        return: Dict, der in den Kontext gemerged wird. MUSS dem
                OUTPUT_SCHEMA entsprechen (falls definiert).
        """
        raise NotImplementedError
