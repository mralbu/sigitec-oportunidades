# SIGITEC Oportunidades

[![Site](https://img.shields.io/badge/site-mralbu.github.io-2a78d6)](https://mralbu.github.io/sigitec-oportunidades/)
[![Dados atualizados](https://img.shields.io/github/last-commit/mralbu/sigitec-oportunidades/main?path=data%2Foportunidades.csv&label=dados%20atualizados&color=2a78d6)](https://github.com/mralbu/sigitec-oportunidades/commits/main/data/oportunidades.csv)
[![Atualização semanal](https://github.com/mralbu/sigitec-oportunidades/actions/workflows/dados-e-site.yml/badge.svg)](https://github.com/mralbu/sigitec-oportunidades/actions/workflows/dados-e-site.yml)

Busque as oportunidades públicas de P&D da Petrobras publicadas no
[SIGITEC Competitividade](https://sigitec-competitividade.petrobras.com.br/v2/public/opportunities).

## No navegador

**<https://mralbu.github.io/sigitec-oportunidades/>**

Busca por termos (sem diferenciar acentos), filtros por status, área, tema, subtema, TRL,
solução esperada e prazo, o detalhe completo de cada oportunidade e estatísticas. Os
dados são atualizados toda segunda-feira.

## Os dados

[`data/oportunidades.csv`](data/oportunidades.csv) tem todas as oportunidades, uma por
linha, com título, status, prazos, área, tema, TRL, desafio, objetivo, solução esperada e
parceiras selecionadas. O arquivo é atualizado automaticamente toda semana.

## No terminal

```sh
uv tool install git+https://github.com/mralbu/sigitec-oportunidades
```

```sh
sigitec-oportunidades sync                   # baixa as oportunidades para um CSV local
sigitec-oportunidades search reservatório --open  # busca entre as abertas
sigitec-oportunidades show OP3449            # detalhe de uma oportunidade
sigitec-oportunidades stats --open           # contagens por tema, área, TRL…
sigitec-oportunidades tui                    # interface interativa com filtros
```

`sigitec-oportunidades --help` lista todas as opções e `sigitec-oportunidades skill`
explica o CLI e a API do SIGITEC em detalhe.
