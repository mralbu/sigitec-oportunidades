"""Console de mensagens (stderr), separado da saída de dados (stdout)."""

from rich.console import Console

console = Console(stderr=True, soft_wrap=True)
