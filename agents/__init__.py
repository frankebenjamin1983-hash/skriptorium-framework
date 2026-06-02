"""Agenten-Paket für PyCompendium. Eine Datei pro Rolle."""

from .archivar import DummyArchivar
from .autor import DummyAutor
from .chefredakteur import DummyChefredakteur
from .faktenpruefer import DummyFaktenpruefer
from .lektor import DummyLektor
from .lektorat import DummyLektorat
from .quizmaster import DummyQuizMaster
from .revisor import DummyRevisor

__all__ = [
    "DummyArchivar",
    "DummyLektor",
    "DummyAutor",
    "DummyFaktenpruefer",
    "DummyLektorat",
    "DummyQuizMaster",
    "DummyRevisor",
    "DummyChefredakteur",
]
