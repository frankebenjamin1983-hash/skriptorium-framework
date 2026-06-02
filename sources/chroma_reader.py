"""
sources/chroma_reader.py – Read-only-Adapter auf den DavidMalanVirtuell-Vectorstore.

Single-Source-of-Truth fuer Stufe-2-Quellinhalt. Der echte Archivar in
Stufe 2 importiert ausschliesslich diesen Reader – nicht chromadb direkt
und auch nicht die _extracted.md-Dateien. So bleiben Indizierung und
Buch-Generierung auf demselben Stand, ohne dass wir eine zweite Pipeline
pflegen muessten.

Vertrag:
  - liest read-only aus C:\\Users\\bfran\\Ai Projekte\\DavidMalanVirtuell\\data\\vectorstore
  - chromadb wird LAZY importiert (erst im Konstruktor), damit Stufe 1
    ohne installierte chromadb-Abhaengigkeit laeuft
  - liefert Chunks als Pydantic-Modelle (id, document, metadata)

Aufruf-Beispiel (Stufe 2):

    from sources.chroma_reader import DavidMalanChromaReader
    reader = DavidMalanChromaReader()
    print(reader.count(), "Chunks im Index")
    for chunk in reader.iter_chunks(batch_size=100):
        ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel


DEFAULT_VECTORSTORE_PATH = Path(
    r"C:\Users\bfran\Ai Projekte\DavidMalanVirtuell\data\vectorstore"
)
DEFAULT_COLLECTION = "cs50"  # aus DavidMalanVirtuell/knowledge/cs50x/rag_index.py


class Chunk(BaseModel):
    """Ein indizierter Text-Abschnitt aus dem Chroma-Store."""
    id: str
    document: str
    metadata: dict[str, Any] = {}


class DavidMalanChromaReader:
    """Read-only-Wrapper um den Chroma-PersistentClient."""

    def __init__(
        self,
        store_path: Path = DEFAULT_VECTORSTORE_PATH,
        collection_name: str = DEFAULT_COLLECTION,
    ):
        self.store_path = Path(store_path)
        self.collection_name = collection_name

        if not self.store_path.exists():
            raise FileNotFoundError(
                f"Chroma-Store nicht gefunden: {self.store_path}. "
                "Pfad pruefen oder DavidMalanVirtuell-Indizierung laufen lassen."
            )

        # Lazy import – chromadb ist eine Stufe-2-Dependency.
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb fehlt. Fuer Stufe 2 mit `pip install chromadb` "
                "installieren oder den entsprechenden Block in requirements.txt "
                "entkommentieren."
            ) from exc

        self._client = chromadb.PersistentClient(path=str(self.store_path))
        try:
            self._collection = self._client.get_collection(self.collection_name)
        except Exception as exc:
            # Falls die Collection anders heisst – wir listen die vorhandenen.
            available = [c.name for c in self._client.list_collections()]
            raise RuntimeError(
                f"Collection '{self.collection_name}' nicht gefunden. "
                f"Vorhanden: {available}"
            ) from exc

    # ────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Anzahl Chunks im Index."""
        return self._collection.count()

    def iter_chunks(self, batch_size: int = 100) -> Iterator[Chunk]:
        """
        Iteriert ueber alle Chunks. Batched, damit der Speicher nicht
        explodiert bei grossen Stores.

        Stufe 2: der Archivar laesst Grok pro Batch klassifizieren und
        schreibt die Metadaten im Anschluss zurueck (separate Methode,
        kommt mit Stufe 2).
        """
        total = self.count()
        offset = 0
        while offset < total:
            batch = self._collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"],
            )
            ids = batch.get("ids", []) or []
            docs = batch.get("documents", []) or []
            metas = batch.get("metadatas", []) or []
            for i, doc_id in enumerate(ids):
                yield Chunk(
                    id=doc_id,
                    document=docs[i] if i < len(docs) else "",
                    metadata=metas[i] if i < len(metas) else {},
                )
            offset += batch_size

    def list_collections(self) -> list[str]:
        """Hilfreich zum Debuggen: welche Collections gibt es im Store?"""
        return [c.name for c in self._client.list_collections()]


# ──────────────────────────────────────────────────────────────────────────
# Self-Test (manuell aufrufen, NICHT von Tests)
# ──────────────────────────────────────────────────────────────────────────

def _smoke():  # pragma: no cover
    """Manueller Smoke-Test. python -m sources.chroma_reader"""
    reader = DavidMalanChromaReader()
    print(f"Store: {reader.store_path}")
    print(f"Collections: {reader.list_collections()}")
    print(f"Chunks in '{reader.collection_name}': {reader.count()}")
    print("Erste 3 Chunks:")
    for i, chunk in enumerate(reader.iter_chunks(batch_size=10)):
        if i >= 3:
            break
        snippet = chunk.document[:80].replace("\n", " ")
        print(f"  [{chunk.id}] {snippet}…")
        print(f"      metadata={chunk.metadata}")


if __name__ == "__main__":  # pragma: no cover
    _smoke()
