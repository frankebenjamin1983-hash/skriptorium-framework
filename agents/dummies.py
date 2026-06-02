"""
HINWEIS: Diese Datei ist aufgelöst.

Jede Rolle liegt jetzt in ihrem eigenen Modul unter agents/. Importiere aus
dem Paket:

    from agents import DummyArchivar, DummyLektor, DummyAutor, ...

Begründung: Sobald in Stufe 2 daneben die echten LLM-Varianten kommen
(EchterArchivar etc.), wird eine zentrale Datei zu groß und vermischt
Verantwortlichkeiten.

Re-Exports stehen unten – nur als Übergangs-Shim, damit alte Importe nicht
sofort brechen. Neuen Code bitte aus 'agents' importieren.
"""

from .archivar import DummyArchivar  # noqa: F401
from .lektor import DummyLektor  # noqa: F401
