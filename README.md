# SIGITEC Oportunidades

[![Site](https://img.shields.io/badge/site-mralbu.github.io-2a78d6)](https://mralbu.github.io/sigitec-oportunidades/)
[![Feed RSS](https://img.shields.io/badge/RSS-feed.xml-d96b16?logo=rss&logoColor=white)](https://mralbu.github.io/sigitec-oportunidades/feed.xml)
[![Dados atualizados](https://img.shields.io/github/last-commit/mralbu/sigitec-oportunidades/main?path=data%2Foportunidades.csv&label=dados%20atualizados&color=2a78d6)](https://github.com/mralbu/sigitec-oportunidades/commits/main/data/oportunidades.csv)
[![Atualização semanal](https://github.com/mralbu/sigitec-oportunidades/actions/workflows/dados-e-site.yml/badge.svg)](https://github.com/mralbu/sigitec-oportunidades/actions/workflows/dados-e-site.yml)

Busque as oportunidades públicas de P&D da Petrobras publicadas no
[SIGITEC Competitividade](https://sigitec-competitividade.petrobras.com.br/v2/public/opportunities).

## No navegador

**<https://mralbu.github.io/sigitec-oportunidades/>**

Busca por termos (sem diferenciar acentos), filtros por status, área, tema, subtema, TRL,
solução esperada e prazo, o detalhe completo de cada oportunidade e estatísticas. Os
dados são atualizados uma vez por semana, toda segunda-feira de manhã (por volta das 6h,
horário de Brasília).

## Feed RSS

Para acompanhar as novas oportunidades sem precisar abrir o site, assine
**<https://mralbu.github.io/sigitec-oportunidades/feed.xml>**. Ele traz as 50 publicadas
mais recentemente, com prazo, área, tema, TRL e o começo do objetivo; cada item abre a
oportunidade no site. Como os dados, o feed é atualizado toda segunda-feira de manhã.

Copie o endereço acima e cole num leitor de feeds (como
[Feedly](https://feedly.com/), [Inoreader](https://www.inoreader.com/),
[NetNewsWire](https://netnewswire.com/), [Feeder](https://gitlab.com/spacecowboy/Feeder)
ou [Thunderbird](https://www.thunderbird.net/)). Para receber em equipe ou por e-mail,
também dá para assinar no Slack (`/feed subscribe <endereço>`), no Microsoft Teams (via
fluxo de RSS) ou usando um serviço de RSS para e-mail (como
[Blogtrottr](https://blogtrottr.com/) ou [Feedrabbit](https://feedrabbit.com/)).

## Os dados

[`data/oportunidades.csv`](data/oportunidades.csv) tem todas as oportunidades, uma por
linha, com título, status, prazos, área, tema, TRL, desafio, objetivo, solução esperada e
parceiras selecionadas. O arquivo é atualizado automaticamente toda segunda-feira de manhã.

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
sigitec-oportunidades feed -o feed.xml       # feed RSS com as mais recentes
```

`sigitec-oportunidades --help` lista todas as opções e `sigitec-oportunidades skill`
explica o CLI e a API do SIGITEC em detalhe.
