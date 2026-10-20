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

# Roda os hooks do prek em todos os arquivos (ou: just pre-commit --files X)
pre-commit *args="--all-files":
    uv run prek run {{ args }}

# Instala os hooks do prek no git (pre-commit e pre-push)
pre-commit-install:
    uv run prek install

# Roda o CLI, ex.: just run search --open
run *args:
    uv run sigitec-oportunidades {{ args }}

# Atualiza data/oportunidades.csv (o mesmo que o GitHub Actions faz todo mês)
update-data *args:
    uv run sigitec-oportunidades --csv data/oportunidades.csv sync {{ args }}

# Monta o site estático em _site/ (site/ + CSV), como no deploy do GitHub Pages
site-build:
    rm -rf _site
    mkdir -p _site
    cp -r site/. _site/
    cp data/oportunidades.csv _site/oportunidades.csv

# Monta e serve o site em http://localhost:8000
site port="8000": site-build
    uv run python -m http.server {{ port }} --directory _site

# Gera wheel e sdist em dist/
build:
    uv build

# Remove caches e artefatos de build (mantém .venv)
clean:
    rm -rf dist build _site .pytest_cache .ruff_cache
    find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
