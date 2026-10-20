# Desenvolvimento

Requer [uv](https://docs.astral.sh/uv/) e [just](https://just.systems/).

```sh
just sync      # cria/atualiza o .venv
just format    # ruff format + ruff check --fix
just lint      # ruff + ty
just test      # pytest (sem acesso à rede)
just check     # lint + test
just run ...   # roda o CLI, ex.: just run search --open
just pre-commit          # hooks do prek em todos os arquivos
just pre-commit-install  # instala os hooks no git (pre-commit e pre-push)
just clean     # remove caches e dist/
```

Os hooks ([prek](https://prek.j178.dev), `.pre-commit-config.yaml`) checam espaços,
fim de arquivo, YAML/TOML, conflitos, arquivos grandes e chaves privadas, além de
`uv lock --check`, `ruff format`, `ruff check` e `ty` a cada commit; o `pytest` roda no push.

Com [direnv](https://direnv.net/), `direnv allow` ativa o `.venv` ao entrar no diretório
e instala o autocompletar do fish em `~/.config/fish/completions`.

## Autocompletar

```sh
eval "$(sigitec-oportunidades completion bash)"   # ~/.bashrc
eval "$(sigitec-oportunidades completion zsh)"    # ~/.zshrc
sigitec-oportunidades completion fish > ~/.config/fish/completions/sigitec-oportunidades.fish
```

O CSV do CLI fica no diretório de dados do usuário (veja `--help`); use `--csv ARQUIVO` ou
`SIGITEC_OPORTUNIDADES_CSV` para outro local.

## Dados e site

O workflow [`dados-e-site.yml`](.github/workflows/dados-e-site.yml) roda toda segunda-feira
(ou manualmente, em *Actions → Dados e site → Run workflow*): faz o `sync` incremental
de [`data/oportunidades.csv`](data/oportunidades.csv), commita o CSV se mudou e publica no
GitHub Pages o site estático de [`site/`](site/). Pushes em `site/` ou no CSV também
republicam o site.

O Pages usa **GitHub Actions** como *Source* (*Settings → Pages*, ou
`gh api -X POST repos/OWNER/REPO/pages -f build_type=workflow` num fork).

```sh
just update-data   # sync de data/oportunidades.csv localmente
just site          # monta _site/ e serve em http://localhost:8000
```

## Estrutura

| Módulo | Conteúdo |
|---|---|
| `api.py` | Cliente HTTP da API pública do SIGITEC |
| `store.py` | CSV local e `sync` incremental |
| `query.py` | Filtros do `search` e contagens do `stats` (funções puras) |
| `render.py` | Normalização de texto, datas e Markdown |
| `cli.py` | Comandos (click) |
| `tui.py` | Interface interativa (Textual) |
| `skill.py` | Texto do comando `skill` |
| `constants.py` | URLs, status e colunas do CSV |
| `site/` | Site estático (HTML, CSS e JS, sem build) |
