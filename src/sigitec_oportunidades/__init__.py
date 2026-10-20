"""Busca oportunidades públicas no SIGITEC Competitividade (Petrobras).

Os dados ficam num CSV local, atualizado pelo comando `sync`; `search`, `show` e
`stats` leem desse arquivo. Veja `sigitec-oportunidades skill`.
"""

from .cli import main

__all__ = ["main"]
