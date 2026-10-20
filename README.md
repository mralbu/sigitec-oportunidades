# sigitec-oportunidades

CLI para buscar as oportunidades públicas de P&D da Petrobras no
[SIGITEC Competitividade](https://sigitec-competitividade.petrobras.com.br/v2/public/opportunities).

Os dados são baixados para um CSV local (`sync`) e consultados offline (`search`, `show`,
`stats`). A documentação completa do CLI e da API está em `sigitec-oportunidades skill`.

## Instalação

```sh
uv tool install .                 # instala o comando sigitec-oportunidades
sigitec-oportunidades sync        # baixa listagem e detalhes (incremental)
sigitec-oportunidades search --open
sigitec-oportunidades show OP3449
sigitec-oportunidades stats --open -c theme
```

O CSV fica no diretório de dados do usuário (veja `--help`); use `--csv ARQUIVO` ou
`SIGITEC_OPORTUNIDADES_CSV` para outro local.

### Autocompletar

```sh
eval "$(sigitec-oportunidades completion bash)"   # ~/.bashrc
eval "$(sigitec-oportunidades completion zsh)"    # ~/.zshrc
sigitec-oportunidades completion fish > ~/.config/fish/completions/sigitec-oportunidades.fish
```

## Desenvolvimento

Requer [uv](https://docs.astral.sh/uv/) e [just](https://just.systems/).

```sh
just sync      # cria/atualiza o .venv
just format    # ruff format + ruff check --fix
just lint      # ruff + ty
just test      # pytest (sem acesso à rede)
just check     # lint + test
just run ...   # roda o CLI, ex.: just run search --open
just clean     # remove caches e dist/
```

Com [direnv](https://direnv.net/), `direnv allow` ativa o `.venv` ao entrar no diretório
e instala o autocompletar do fish em `~/.config/fish/completions`.

## Estrutura

| Módulo | Conteúdo |
|---|---|
| `api.py` | Cliente HTTP da API pública do SIGITEC |
| `store.py` | CSV local e `sync` incremental |
| `query.py` | Filtros do `search` e contagens do `stats` (funções puras) |
| `render.py` | Normalização de texto, datas e Markdown |
| `cli.py` | Comandos (click) |
| `skill.py` | Texto do comando `skill` |
| `constants.py` | URLs, status e colunas do CSV |
