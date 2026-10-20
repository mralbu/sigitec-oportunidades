"""Endereços da API, status e colunas do CSV."""

from datetime import timedelta, timezone

SITE = "https://sigitec-competitividade.petrobras.com.br"
API = f"{SITE}/v2/ms-authorization/opportunity"
PAGE_URL = f"{SITE}/v2/public/opportunity/{{id}}"
# Oportunidades do SIGITEC antigo (nodeBackend=true) têm outra página e o detalhe
# vem de um host interno da Petrobras, inacessível de fora: ficam só com o resumo.
LEGACY_PAGE_URL = f"{SITE}/v2/public/opportunitysigitec/{{id}}"

APP_NAME = "sigitec-oportunidades"
CSV_ENVVAR = "SIGITEC_OPORTUNIDADES_CSV"

STATUS = {
    "A": "Aberta para envio de proposta",
    "J": "Julgamento",
    "R": "Resultado",
    "F": "Finalizada",
    "CC": "Cancelada",
}
STATUS_COLORS = {"A": "green", "J": "yellow", "R": "cyan", "F": "dim", "CC": "red"}
BRT = timezone(timedelta(hours=-3))
NA = "Não aplicável"

# Colunas do CSV, na ordem. Campos da API fora desta lista são descartados.
COLUMNS = [
    "id",
    "numberOP",
    "titleOP",
    "status",
    "deadlineSubmissionOfProposal",
    "publicationDate",
    "area",
    "commitment",
    "regulatoryAgency",
    "theme",
    "subTheme",
    "intendedTrl",
    "intendedCrl",
    "developmentDeadline",
    "expectedSolution",
    "objective",
    "challenge",
    "expectedSolutionDetail",
    "selectedPartnership",
    "live",
    "linkToVideOrpresentation",
    "liveLink",
    "liveDate",
    "liveStartTime",
    "liveEndTime",
    "fileName",
    "nodeBackend",
    "url",
    "detailFetchedAt",
]
# Campos que vêm na listagem; se mudarem, o detalhe é baixado de novo.
SUMMARY_KEYS = ["titleOP", "status", "deadlineSubmissionOfProposal", "publicationDate", "objective"]
# Campos usados na busca de texto livre.
TEXT_KEYS = [
    "numberOP",
    "titleOP",
    "objective",
    "challenge",
    "expectedSolutionDetail",
    "expectedSolution",
    "theme",
    "subTheme",
    "area",
]
LIST_SEP = " | "
STALE_AFTER = timedelta(hours=24)

# Colunas resumidas pelo `stats`: (campo, rótulo).
STATS_COLUMNS = [
    ("status", "Status"),
    ("year", "Ano de publicação"),
    ("area", "Área de pesquisa"),
    ("theme", "Tema"),
    ("subTheme", "Subtema"),
    ("commitment", "Obrigação regulatória"),
    ("regulatoryAgency", "Agência"),
    ("intendedTrl", "TRL pretendido"),
    ("intendedCrl", "CRL pretendido"),
    ("expectedSolution", "Solução esperada"),
    ("developmentDeadline", "Prazo de desenvolvimento (meses)"),
    ("selectedPartnership", "Parceira selecionada"),
]
PENDING_PARTNER = "Aguardando resultado do certame"
