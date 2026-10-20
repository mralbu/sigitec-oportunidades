set shell := ["bash", "-euo", "pipefail", "-c"]

# Lista as receitas
default:
    @just --list

# Instala/atualiza o ambiente (.venv) com as dependências de desenvolvimento
sync:
    uv sync

# Formata o código e corrige o que o ruff consegue
format:
    uv run ruff format
    uv run ruff check --fix

# Lint: ruff (estilo/erros) e ty (tipos)
lint:
    uv run ruff format --check
    uv run ruff check
    uv run ty check

# Roda os testes
test *args:
    uv run pytest {{ args }}

# Lint + testes (o que a CI deveria rodar)
check: lint test

# Roda o CLI, ex.: just run search --open
run *args:
    uv run sigitec-oportunidades {{ args }}

# Gera wheel e sdist em dist/
build:
    uv build

# Remove caches e artefatos de build (mantém .venv)
clean:
    rm -rf dist build .pytest_cache .ruff_cache
    find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
