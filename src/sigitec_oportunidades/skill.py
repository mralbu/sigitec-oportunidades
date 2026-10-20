"""Texto do comando `skill`: documentação do CLI e da API para pessoas e agentes."""

from .constants import API, APP_NAME, CSV_ENVVAR, LIST_SEP, PENDING_PARTNER, SITE

SKILL = f"""\
# {APP_NAME}

CLI para buscar e ler as **oportunidades públicas** de P&D da Petrobras publicadas no
[SIGITEC Competitividade]({SITE}/v2/public/opportunities). Instale com
`uv tool install .` (ou rode no projeto com `uv run {APP_NAME}`).

## Arquitetura

- **`sync`** baixa os dados da API para um **CSV local** (padrão: `oportunidades.csv`
  no diretório de dados do usuário; mude com `--csv` ou `{CSV_ENVVAR}`).
- **`search`**, **`show`** e **`stats`** leem do CSV: busca offline, instantânea e em
  todos os campos.
- O `sync` é **incremental**: 1 requisição para a listagem completa e detalhes só para
  oportunidades novas, alteradas (status, prazo, título…) ou cujo detalhe falhou antes.
- Se o CSV não existir, `search`/`show`/`stats` baixam só a listagem (sem detalhes)
  automaticamente; com o CSV com mais de 24h aparece um aviso.

## Comandos

### `sync` — atualiza o CSV local

| Opção | Descrição |
|---|---|
| `--full` | Baixa de novo os detalhes de todas as oportunidades |
| `--no-details` | Só a listagem (rápido; sem desafio, tema, solução etc.) |
| `-j, --concurrency` | Requisições simultâneas de detalhe (padrão 4) |
| `--retries` | Novas tentativas por detalhe (padrão 1) |
| `--max-failures` | Interrompe após N falhas seguidas (padrão 5) |

### `search [TERMOS...]` — busca no CSV

| Opção | Descrição |
|---|---|
| `TERMOS` | Todos devem aparecer em título, objetivo, desafio, solução, tema ou área (ignora acentos) |
| `-t, --title` / `-o, --objective` | Trecho do título / objetivo |
| `--theme` | Trecho do tema, subtema ou área |
| `-c, --code` | Número da OP (ex.: `3449`) |
| `-s, --status` | `A` aberta, `J` julgamento, `R` resultado, `F` finalizada, `CC` cancelada (repetível) |
| `--open` | Atalho para `--status A` |
| `--after` / `--before` | Intervalo do prazo de proposta (`AAAA-MM-DD`) |
| `--sort` | `deadline` (padrão), `number` ou `published` |
| `--asc` | Ordem crescente (padrão: decrescente) |
| `-n, --limit` | Máximo de resultados (padrão 50; `0` = todos) |
| `--json` | Saída em JSON em vez de tabela |
| `-r, --refresh` | Roda `sync` antes |

### `show REF` — detalhes de uma oportunidade

`REF` é o número da OP (ex.: `OP3449`, preferível) ou o id interno (ex.: `2248`). Usa o CSV; se a
linha não tem detalhes (ou com `--online`) consulta a API. Por padrão renderiza
Markdown no terminal; `--markdown` imprime o Markdown cru (também quando a saída não é
um terminal), `--json` imprime os dados e `-o ARQUIVO` salva o Markdown.

### `stats` — contagens por coluna

Conta as oportunidades do CSV por status, ano de publicação, área, tema, subtema,
obrigação/agência, TRL/CRL, solução esperada, prazo de desenvolvimento e parceira
selecionada (ignorando "{PENDING_PARTNER}"). Tema, área etc. só existem nas linhas com
detalhes, então rode `sync` antes.

| Opção | Descrição |
|---|---|
| `-s, --status` / `--open` | Considera só estes status |
| `-c, --column` | Só estas colunas (repetível; ex.: `-c theme -c area`) |
| `-n, --top` | Valores por coluna (padrão 10; `0` = todos) |
| `--json` | Saída em JSON |
| `-r, --refresh` | Roda `sync` antes |

### `completion SHELL` — script de autocompletar

`SHELL` é `bash`, `zsh` ou `fish`. Exemplos:
`eval "$({APP_NAME} completion bash)"` no `~/.bashrc`,
`{APP_NAME} completion fish > ~/.config/fish/completions/{APP_NAME}.fish`.

### `skill` — imprime este texto

## Exemplos

```sh
{APP_NAME} sync
{APP_NAME} search microtomografia rocha
{APP_NAME} search --open --asc -n 0
{APP_NAME} search --theme petrofisica -s A -s J --json
{APP_NAME} show OP3449 -o op3449.md
{APP_NAME} stats --open -c theme -c intendedTrl
```

## API SIGITEC utilizada

API REST pública, sem autenticação, que alimenta a página pública (SPA React) do SIGITEC.

- **Base:** `{API}`
- **Página web de uma oportunidade:** `{SITE}/v2/public/opportunity/{{id}}`

### `GET /getAllPublicOpportunities`

Retorna **todas** as oportunidades públicas em um único array JSON (sem paginação,
~570 itens). Só os campos de resumo vêm preenchidos (`id`, `numberOP`, `titleOP`,
`objective`, `status`, `deadlineSubmissionOfProposal`, `publicationDate`); os demais
vêm `null`. Aceita filtros (`basicSearch`, ou `title`, `objective`, `code`, `status`,
`submissionDeadline`), mas o CLI baixa tudo e filtra localmente.

A listagem junta **dois sistemas**: o SIGITEC atual e o antigo (`nodeBackend: true`,
~210 oportunidades, todas finalizadas/canceladas). Os **ids se repetem** entre os dois
(o mesmo `id` pode ser duas OPs diferentes), então a chave única é o **`numberOP`**.
As antigas abrem em `{SITE}/v2/public/opportunitysigitec/{{id}}` e seu detalhe vem de
`sigitec-bfb-ms-opportunity-v2-prd.petrobras.com.br/api/opportunities/judgementFinished/{{id}}`,
um host interno inacessível de fora da Petrobras — no CSV elas ficam só com o resumo.

### `GET /public-opportunity/{{id}}`

Detalhe completo de uma oportunidade do SIGITEC atual pelo **id interno** (não pelo número da OP);
`404` se não existir. O backend consulta serviços internos da Petrobras e às vezes
responde `500` após ~30 s de timeout — por isso o `sync` tenta de novo, interrompe
após falhas seguidas e retoma no próximo `sync`. Campos principais:

| Campo | Significado |
|---|---|
| `numberOP`, `titleOP` | Número e título (exibido como `OP<número> - <título>`) |
| `status` | `A`, `J`, `R`, `F`, `CC` (ver acima) |
| `deadlineSubmissionOfProposal` | Prazo de proposta (UTC; `03:00Z` = meia-noite de Brasília) |
| `area`, `theme`, `subTheme` | Área de pesquisa, tema e subtema |
| `commitment`, `regulatoryAgency` | Obrigação regulatória (`SIM`/`NAO`) e agência (ANP, ANEEL…) |
| `challenge`, `objective` | Desafio e objetivo (texto com quebras de linha/listas) |
| `intendedTrl`, `intendedCrl` | Maturidade tecnológica/comercial pretendida |
| `developmentDeadline` | Prazo de desenvolvimento, em meses |
| `expectedSolution`, `expectedSolutionDetail` | Tipo de solução esperada e detalhamento |
| `linkToVideOrpresentation`, `liveLink`, `liveDate`, `liveStartTime`, `liveEndTime` | Pitch e live |
| `selectedPartnership` | Lista de parceiras selecionadas |

No CSV (uma linha por OP, chave `numberOP`), `selectedPartnership` vira texto separado
por `{LIST_SEP.strip()}`, `nodeBackend` indica o SIGITEC antigo, e há duas colunas extras:
`url` (página pública) e `detailFetchedAt` (quando o detalhe foi baixado; vazio = só resumo).
"""
