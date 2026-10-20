// Busca e estatísticas sobre o oportunidades.csv, no navegador. Espelha a TUI
// (tui.py) e o `stats` do CLI; os filtros seguem query.py.
"use strict";

const STATUS = {
  A: "Aberta para envio de proposta",
  J: "Julgamento",
  R: "Resultado",
  F: "Finalizada",
  CC: "Cancelada",
};
const SHORT_STATUS = { ...STATUS, A: "Aberta" };
const NA = "Não aplicável";
const PENDING_PARTNER = "Aguardando resultado do certame";
const LIST_SEP = " | ";
const TZ = "America/Sao_Paulo";

const TEXT_KEYS = [
  "numberOP", "titleOP", "objective", "challenge", "expectedSolutionDetail",
  "expectedSolution", "theme", "subTheme", "area",
];
// Menus de valor exato: (coluna, rótulo).
const EXACT_FILTERS = [
  ["area", "Área de pesquisa"],
  ["theme", "Tema"],
  ["subTheme", "Subtema"],
  ["intendedTrl", "TRL pretendido"],
  ["expectedSolution", "Solução esperada"],
];
// Colunas resumidas nas estatísticas: (campo, rótulo).
const STATS_COLUMNS = [
  ["status", "Status"],
  ["year", "Ano de publicação"],
  ["area", "Área de pesquisa"],
  ["theme", "Tema"],
  ["subTheme", "Subtema"],
  ["commitment", "Obrigação regulatória"],
  ["regulatoryAgency", "Agência"],
  ["intendedTrl", "TRL pretendido"],
  ["intendedCrl", "CRL pretendido"],
  ["expectedSolution", "Solução esperada"],
  ["developmentDeadline", "Prazo de desenvolvimento (meses)"],
  ["selectedPartnership", "Parceira selecionada"],
];
const SORT_KEYS = {
  deadline: (o) => o.deadlineSubmissionOfProposal || "",
  number: (o) => o.numberOP,
  published: (o) => o.publicationDate || "",
};
const TOP = 10;

const $ = (sel) => document.querySelector(sel);
const fmtDay = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" });
const isoDay = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const nf = new Intl.NumberFormat("pt-BR");

let rows = [];
let byOp = new Map();
let results = [];
let current = null;
const expanded = new Set(); // gráficos com "mostrar todos"

// ------------------------------------------------------------------ texto e datas

/** Minúsculas e sem acentos, para busca (render.norm). */
function norm(text) {
  return String(text).normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase();
}

function parseDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtDate(value) {
  const d = parseDate(value);
  return d ? fmtDay.format(d) : "-";
}

/** AAAA-MM-DD no fuso de Brasília. */
function dayOf(value) {
  const d = parseDate(value);
  return d ? isoDay.format(d) : null;
}

// ------------------------------------------------------------------ CSV

function fromRow(row) {
  const d = {};
  for (const [k, v] of Object.entries(row)) d[k] = v === "" ? null : v;
  d.id = Number(d.id);
  d.numberOP = Number(d.numberOP);
  d.nodeBackend = d.nodeBackend === "true";
  d.selectedPartnership = d.selectedPartnership ? d.selectedPartnership.split(LIST_SEP) : null;
  d._hay = norm(TEXT_KEYS.map((k) => d[k] ?? "").join(" "));
  return d;
}

async function load() {
  const res = await fetch("oportunidades.csv", { cache: "no-cache" });
  if (!res.ok) throw new Error(`oportunidades.csv: HTTP ${res.status}`);
  const text = await res.text();
  const parsed = Papa.parse(text, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h.replace(/^﻿/, ""),
  });
  rows = parsed.data.filter((r) => r.numberOP).map(fromRow);
  byOp = new Map(rows.map((o) => [o.numberOP, o]));

  let updated = null;
  try {
    const meta = await (await fetch("meta.json", { cache: "no-cache" })).json();
    updated = meta.updatedAt;
  } catch {
    updated = res.headers.get("last-modified");
  }
  const parts = [`${nf.format(rows.length)} oportunidades`];
  if (updated && parseDate(updated)) parts.push(`dados de ${fmtDate(updated)}`);
  parts.push("atualizado semanalmente a partir do SIGITEC Competitividade");
  $("#meta").textContent = parts.join(" · ");
}

// ------------------------------------------------------------------ filtros (query.py)

function distinct(key) {
  const set = new Set(rows.map((o) => o[key]).filter(Boolean));
  return [...set].sort((a, b) => norm(a).localeCompare(norm(b), "pt-BR"));
}

function readFilter() {
  const equals = {};
  for (const [key] of EXACT_FILTERS) {
    const v = $(`#eq-${key}`).value;
    if (v) equals[key] = v;
  }
  return {
    terms: norm($("#terms").value).split(/\s+/).filter(Boolean),
    statuses: new Set([...document.querySelectorAll("#statuses input:checked")].map((i) => i.value)),
    equals,
    after: dateInput("after"),
    before: dateInput("before"),
  };
}

/** Data do campo; inválida é ignorada e o campo fica marcado. */
function dateInput(id) {
  const el = $(`#${id}`);
  const ok = el.validity.valid;
  el.classList.toggle("invalid", !ok);
  return ok && el.value ? el.value : null;
}

function matches(o, f) {
  if (f.statuses.size && !f.statuses.has(o.status)) return false;
  for (const [k, v] of Object.entries(f.equals)) if (o[k] !== v) return false;
  if (f.after || f.before) {
    const d = dayOf(o.deadlineSubmissionOfProposal);
    if (!d) return false;
    if ((f.after && d < f.after) || (f.before && d > f.before)) return false;
  }
  return f.terms.every((t) => o._hay.includes(t));
}

function search() {
  const f = readFilter();
  const key = SORT_KEYS[$("#sort").value] || SORT_KEYS.deadline;
  const dir = $("#asc").checked ? 1 : -1;
  return rows
    .filter((o) => matches(o, f))
    .sort((a, b) => {
      const ka = key(a), kb = key(b);
      return (ka < kb ? -1 : ka > kb ? 1 : 0) * dir;
    });
}

// ------------------------------------------------------------------ estado na URL

function saveHash() {
  const p = new URLSearchParams();
  const terms = $("#terms").value.trim();
  if (terms) p.set("q", terms);
  const st = [...document.querySelectorAll("#statuses input:checked")].map((i) => i.value);
  if (st.length) p.set("status", st.join(","));
  for (const [key] of EXACT_FILTERS) {
    const v = $(`#eq-${key}`).value;
    if (v) p.set(key, v);
  }
  for (const id of ["after", "before"]) if ($(`#${id}`).value) p.set(id, $(`#${id}`).value);
  if ($("#sort").value !== "deadline") p.set("sort", $("#sort").value);
  if ($("#asc").checked) p.set("asc", "1");
  if (current) p.set("op", current.numberOP);
  if (!$("#view-stats").hidden) p.set("view", "stats");
  const hash = p.toString();
  history.replaceState(null, "", hash ? `#${hash}` : location.pathname + location.search);
}

function loadHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  $("#terms").value = p.get("q") || "";
  const st = new Set((p.get("status") || "").split(",").map((s) => s.toUpperCase()));
  for (const i of document.querySelectorAll("#statuses input")) i.checked = st.has(i.value);
  for (const [key] of EXACT_FILTERS) {
    const sel = $(`#eq-${key}`);
    const v = p.get(key) || "";
    sel.value = [...sel.options].some((o) => o.value === v) ? v : "";
  }
  $("#after").value = p.get("after") || "";
  $("#before").value = p.get("before") || "";
  $("#sort").value = SORT_KEYS[p.get("sort")] ? p.get("sort") : "deadline";
  $("#asc").checked = p.get("asc") === "1";
  return { op: Number(p.get("op")) || null, view: p.get("view") };
}

// ------------------------------------------------------------------ montagem dos filtros

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c != null) e.append(c);
  return e;
}

function statusBadge(code, short = true) {
  return el(
    "span",
    { class: "status", style: `--dot: var(--st-${code}, var(--muted))` },
    (short ? SHORT_STATUS : STATUS)[code] || code,
  );
}

function buildFilters() {
  const counts = {};
  for (const o of rows) counts[o.status] = (counts[o.status] || 0) + 1;
  $("#statuses").replaceChildren(
    ...Object.entries(STATUS).map(([code]) =>
      el(
        "label",
        { class: "check" },
        el("input", { type: "checkbox", value: code }),
        statusBadge(code, false),
        el("span", { class: "n" }, nf.format(counts[code] || 0)),
      ),
    ),
  );
  $("#exact").replaceChildren(
    ...EXACT_FILTERS.flatMap(([key, label]) => [
      el("label", { for: `eq-${key}` }, label),
      el(
        "select",
        { id: `eq-${key}` },
        el("option", { value: "" }, "Todos"),
        distinct(key).map((v) => el("option", { value: v, title: v }, v)),
      ),
    ]),
  );
}

// ------------------------------------------------------------------ lista

function apply({ keepSelection = true } = {}) {
  results = search();
  const tbody = $("#results tbody");
  tbody.replaceChildren(
    ...results.map((o) =>
      el(
        "tr",
        { "data-op": o.numberOP, "aria-selected": "false" },
        el("td", {}, `OP${o.numberOP}`),
        el("td", {}, fmtDate(o.deadlineSubmissionOfProposal)),
        el("td", {}, statusBadge(o.status)),
        el("td", {}, (o.titleOP || "").trim()),
      ),
    ),
  );
  if (!results.length) {
    tbody.append(el("tr", {}, el("td", { colspan: 4, class: "empty" }, "Nenhuma oportunidade encontrada.")));
  }
  $("#count").textContent = `${nf.format(results.length)} de ${nf.format(rows.length)} oportunidade(s)`;
  const keep = keepSelection && current && results.includes(current) ? current : results[0] || null;
  select(keep, { scroll: true });
  if (!$("#view-stats").hidden) renderStats();
  saveHash();
}

function select(o, { scroll = false } = {}) {
  current = o;
  for (const tr of document.querySelectorAll("#results tr[aria-selected='true']")) {
    tr.setAttribute("aria-selected", "false");
  }
  if (o) {
    const tr = document.querySelector(`#results tr[data-op="${o.numberOP}"]`);
    if (tr) {
      tr.setAttribute("aria-selected", "true");
      if (scroll) scrollIntoTable(tr);
    }
  }
  renderDetail(o);
  saveHash();
}

/** Rola só a tabela (scrollIntoView rolaria a página inteira no celular). */
function scrollIntoTable(tr) {
  const wrap = tr.closest(".table-wrap");
  const head = wrap.querySelector("thead").offsetHeight;
  const top = tr.offsetTop - head;
  if (top < wrap.scrollTop) wrap.scrollTop = top;
  else if (tr.offsetTop + tr.offsetHeight > wrap.scrollTop + wrap.clientHeight) {
    wrap.scrollTop = tr.offsetTop + tr.offsetHeight - wrap.clientHeight;
  }
}

function move(step) {
  if (!results.length) return;
  const i = current ? results.indexOf(current) : -1;
  const next = results[Math.min(results.length - 1, Math.max(0, i + step))];
  select(next, { scroll: true });
}

// ------------------------------------------------------------------ detalhe (render.to_markdown)

function renderDetail(d) {
  const box = $("#detail");
  if (!d) {
    box.replaceChildren(el("p", { class: "empty" }, "Nenhuma oportunidade encontrada."));
    return;
  }
  const text = (v) => el("p", { class: "text" }, (v || NA).replace(/\r\n/g, "\n").trim());
  const dl = (...pairs) => el("dl", {}, pairs.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
  const link = (v) => (v && /^https?:\/\//.test(v) ? el("a", { href: v, target: "_blank", rel: "noopener" }, v) : v || NA);

  const notes = [];
  if (d.nodeBackend) notes.push(el("p", { class: "note" }, "SIGITEC antigo: só o resumo está disponível."));
  else if (!d.detailFetchedAt) notes.push(el("p", { class: "note" }, "Sem detalhes no CSV; serão baixados no próximo sync."));

  const framing = [["Obrigação", d.commitment === "SIM" ? "Sim" : "Não"]];
  if (d.commitment !== "NAO") framing.push(["Agência", d.regulatoryAgency || NA]);
  framing.push(["Tema", d.theme || NA], ["Subtema", d.subTheme || NA]);

  box.replaceChildren(
    ...notes,
    el("h2", {}, `OP${d.numberOP} - ${(d.titleOP || "").trim()}`),
    el("div", { class: "actions" },
      el("a", { href: d.url, target: "_blank", rel: "noopener", title: "Abrir no SIGITEC (o)" }, "Abrir no SIGITEC ↗")),
    dl(
      ["Prazo para envio de proposta", fmtDate(d.deadlineSubmissionOfProposal)],
      ["Status", statusBadge(d.status, false)],
      ["Publicação", fmtDate(d.publicationDate)],
      ["Área de pesquisa", d.area || NA],
    ),
    el("h3", {}, "Intenção de enquadramento"),
    dl(...framing),
    el("h3", {}, "Desafio"),
    text(d.challenge),
    el("h3", {}, "Objetivo"),
    text(d.objective),
    dl(
      ["TRL pretendido", d.intendedTrl || NA],
      ["CRL pretendido", d.intendedCrl || NA],
      ["Prazo para desenvolvimento", `${d.developmentDeadline || 0} meses`],
    ),
    el("h3", {}, "Solução esperada"),
    text(d.expectedSolution),
    el("h3", {}, "Solução detalhada"),
    text(d.expectedSolutionDetail),
    el("h3", {}, "Pitch e Live"),
    dl(
      ["Pitch", link(d.linkToVideOrpresentation)],
      ["Live", link(d.liveLink)],
      ["Data", d.liveDate ? fmtDate(d.liveDate) : NA],
      ["Hora início", d.liveStartTime || NA],
      ["Hora término", d.liveEndTime || NA],
    ),
    el("h3", {}, "Parceira(s) selecionada(s)"),
    el("ul", {}, (d.selectedPartnership || [NA]).map((p) => el("li", {}, p))),
  );
  box.scrollTop = 0;
}

// ------------------------------------------------------------------ estatísticas (query.stat_values)

function statValues(o, key) {
  if (key === "status") return [STATUS[o.status] || String(o.status)];
  if (key === "year") {
    const d = dayOf(o.publicationDate);
    return d ? [d.slice(0, 4)] : [];
  }
  if (key === "selectedPartnership") {
    return (o.selectedPartnership || []).map((p) => p.trim()).filter((p) => p && p !== PENDING_PARTNER);
  }
  const v = o[key];
  return v != null && String(v).trim() !== "" ? [String(v).trim()] : [];
}

function columnStats(list, key) {
  const counts = new Map();
  let missing = 0;
  for (const o of list) {
    const values = statValues(o, key);
    for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
    if (!values.length) missing++;
  }
  return { counts, missing };
}

const STATUS_BY_LABEL = Object.fromEntries(Object.entries(STATUS).map(([k, v]) => [v, k]));
const EXACT_KEYS = new Set(EXACT_FILTERS.map(([k]) => k));

/** Clique numa barra: liga/desliga o filtro correspondente, se houver. */
function filterAction(key, value) {
  if (key === "status") {
    const code = STATUS_BY_LABEL[value];
    if (!code) return null;
    const boxes = [...document.querySelectorAll("#statuses input")];
    const only = boxes.every((b) => b.checked === (b.value === code));
    return {
      active: only,
      run: () => {
        for (const b of boxes) b.checked = !only && b.value === code;
        apply();
      },
    };
  }
  if (EXACT_KEYS.has(key)) {
    const sel = $(`#eq-${key}`);
    const active = sel.value === value;
    return { active, run: () => { sel.value = active ? "" : value; apply(); } };
  }
  return null;
}

function renderStats() {
  const list = results;
  const legacy = list.filter((o) => o.nodeBackend).length;
  const withDetail = list.filter((o) => o.detailFetchedAt).length;
  const open = list.filter((o) => o.status === "A").length;
  const tile = (k, v, hero = false) =>
    el("div", { class: `tile${hero ? " hero" : ""}` }, el("div", { class: "k" }, k), el("div", { class: "v" }, nf.format(v)));
  $("#tiles").replaceChildren(
    tile(list.length === rows.length ? "Oportunidades" : "Oportunidades no filtro", list.length, true),
    tile("Abertas para proposta", open),
    tile("Com detalhes", withDetail),
    tile("SIGITEC antigo (só resumo)", legacy),
  );

  const cards = [];
  for (const [key, label] of STATS_COLUMNS) {
    const { counts, missing } = columnStats(list, key);
    if (!counts.size) continue;
    cards.push(key === "year" ? yearCard(label, counts, missing) : barCard(key, label, counts, missing));
  }
  if (!cards.length) cards.push(el("p", { class: "empty" }, "Nenhuma oportunidade no filtro."));
  $("#charts").replaceChildren(...cards);
}

function footer(counts, shown, missing, key) {
  const parts = [`${counts.size} valores distintos`];
  if (missing) parts.push(`${nf.format(missing)} sem valor`);
  const foot = el("div", { class: "foot" }, parts.join(" · "));
  if (counts.size > TOP) {
    const all = expanded.has(key);
    foot.append(
      el("button", {
        onclick: () => {
          all ? expanded.delete(key) : expanded.add(key);
          renderStats();
        },
      }, all ? "mostrar menos" : `mostrar todos (+${counts.size - shown})`),
    );
  }
  return foot;
}

function barCard(key, label, counts, missing) {
  const sorted = [...counts].sort((a, b) => b[1] - a[1] || norm(a[0]).localeCompare(norm(b[0])));
  const shown = expanded.has(key) ? sorted : sorted.slice(0, TOP);
  const base = [...counts.values()].reduce((a, b) => a + b, 0);
  const max = sorted[0][1];
  const grid = el("div", { class: "hbars", role: "table", "aria-label": label });
  for (const [value, n] of shown) {
    const action = filterAction(key, value);
    const pct = Math.round((100 * n) / base);
    const row = el(
      "div",
      {
        class: `row${action ? " clickable" : ""}${action?.active ? " active" : ""}`,
        role: "row",
        title: action ? (action.active ? "Remover filtro" : "Filtrar por este valor") : value,
      },
      el("span", { class: "lbl", role: "cell", title: value }, value),
      el("span", { class: "track", role: "cell", "aria-hidden": "true" },
        el("div", { class: "fill", style: `width:${(100 * n) / max}%` })),
      el("span", { class: "val", role: "cell" }, nf.format(n), el("span", { class: "pct" }, `${pct}%`)),
    );
    if (action) row.addEventListener("click", action.run);
    grid.append(row);
  }
  const wide = key === "selectedPartnership" || key === "theme" || key === "subTheme" || key === "area";
  return el("div", { class: `card${wide ? " span" : ""}` }, el("h3", {}, label), grid, footer(counts, shown.length, missing, key));
}

function yearCard(label, counts, missing) {
  const years = [...counts.keys()].map(Number).sort((a, b) => a - b);
  const first = years[0], last = years[years.length - 1];
  const data = [];
  for (let y = first; y <= last; y++) data.push([y, counts.get(String(y)) || 0]);
  const max = Math.max(...data.map((d) => d[1]));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;

  // Desenha na largura real do cartão, para o texto não escalar com o viewBox.
  const W = Math.max(280, $("#charts").clientWidth - 30), H = 200, padL = 32, padB = 22, padT = 16;
  const plotW = W - padL, plotH = H - padB - padT;
  const slot = plotW / data.length;
  const bw = Math.min(24, slot - 2);
  const y = (v) => padT + plotH - (v / top) * plotH;
  const svgNS = "http://www.w3.org/2000/svg";
  const s = (tag, attrs, text) => {
    const e = document.createElementNS(svgNS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text != null) e.textContent = text;
    return e;
  };
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": `${label}: ${data.map(([yr, n]) => `${yr}: ${n}`).join(", ")}` });
  for (let v = 0; v <= top; v += step) {
    svg.append(s("line", { class: v ? "grid" : "base", x1: padL, x2: W, y1: y(v), y2: y(v) }));
    svg.append(s("text", { class: "tick", x: padL - 6, y: y(v) + 4, "text-anchor": "end" }, nf.format(v)));
  }
  const labelEvery = Math.ceil(data.length / Math.max(2, Math.floor(plotW / 48)));
  data.forEach(([yr, n], i) => {
    const cx = padL + slot * i + slot / 2;
    const g = s("g", {});
    const h = Math.max(0, y(0) - y(n));
    if (n) {
      // 4px de raio na ponta, base reta.
      const r = Math.min(4, h, bw / 2);
      const x0 = cx - bw / 2, x1 = cx + bw / 2, y0 = y(0), yt = y(n);
      g.append(s("path", {
        class: "bar",
        d: `M${x0},${y0}V${yt + r}Q${x0},${yt} ${x0 + r},${yt}H${x1 - r}Q${x1},${yt} ${x1},${yt + r}V${y0}Z`,
      }));
    }
    if (i % labelEvery === 0 || i === data.length - 1) {
      g.append(s("text", { class: "tick", x: cx, y: H - 6, "text-anchor": "middle" }, String(yr)));
    }
    if (n === max) g.append(s("text", { class: "cap", x: cx, y: y(n) - 4, "text-anchor": "middle" }, nf.format(n)));
    const hit = s("rect", { class: "hit", x: padL + slot * i, y: padT, width: slot, height: plotH });
    hit.addEventListener("mousemove", (ev) => showTip(ev, `${yr}`, `${nf.format(n)} oportunidade(s)`));
    hit.addEventListener("mouseleave", hideTip);
    g.append(hit);
    svg.append(g);
  });
  return el("div", { class: "card span cols" }, el("h3", {}, label), svg, footer(counts, counts.size, missing, "year"));
}

function niceStep(max) {
  const raw = Math.max(1, max / 4);
  const mag = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 5, 10]) if (raw <= m * mag) return m * mag;
  return 10 * mag;
}

function showTip(ev, title, body) {
  const tip = $("#tooltip");
  tip.replaceChildren(el("div", {}, el("b", {}, title)), el("div", {}, body));
  tip.hidden = false;
  const { innerWidth: w } = window;
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(ev.clientX + 12, w - r.width - 8)}px`;
  tip.style.top = `${ev.clientY - r.height - 10}px`;
}

function hideTip() {
  $("#tooltip").hidden = true;
}

// ------------------------------------------------------------------ abas e atalhos

function showView(view) {
  const stats = view === "stats";
  $("#view-list").hidden = stats;
  $("#view-stats").hidden = !stats;
  $("#tab-list").setAttribute("aria-selected", String(!stats));
  $("#tab-stats").setAttribute("aria-selected", String(stats));
  if (stats) renderStats();
  saveHash();
}

function toggleFilters(force) {
  const hidden = $("#filters").classList.toggle("hidden", force);
  $("#toggle-filters").setAttribute("aria-expanded", String(!hidden));
}

function reset() {
  $("#terms").value = "";
  $("#after").value = "";
  $("#before").value = "";
  for (const i of document.querySelectorAll("#statuses input")) i.checked = false;
  for (const [key] of EXACT_FILTERS) $(`#eq-${key}`).value = "";
  apply();
}

function bind() {
  let timer;
  $("#terms").addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(apply, 120);
  });
  $("#filters").addEventListener("change", (e) => {
    if (e.target.id !== "terms") apply();
  });
  $("#reset").addEventListener("click", reset);
  $("#toggle-filters").addEventListener("click", () => toggleFilters());
  $("#tab-list").addEventListener("click", () => showView("list"));
  $("#tab-stats").addEventListener("click", () => showView("stats"));
  $("#results tbody").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-op]");
    if (tr) select(byOp.get(Number(tr.dataset.op)));
  });

  document.addEventListener("keydown", (e) => {
    const typing = e.target.matches("input, select, textarea");
    if (e.key === "Escape" && typing) {
      e.target.blur();
      return;
    }
    if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
    switch (e.key) {
      case "/":
        e.preventDefault();
        toggleFilters(false);
        $("#terms").focus();
        break;
      case "f": toggleFilters(); break;
      case "x": reset(); break;
      case "o": if (current?.url) window.open(current.url, "_blank", "noopener"); break;
      case "j": case "ArrowDown": if (!$("#view-list").hidden) { e.preventDefault(); move(1); } break;
      case "k": case "ArrowUp": if (!$("#view-list").hidden) { e.preventDefault(); move(-1); } break;
      default: return;
    }
  });
}

async function main() {
  try {
    await load();
  } catch (err) {
    $("#meta").textContent = `Erro ao carregar os dados: ${err.message}`;
    return;
  }
  buildFilters();
  bind();
  const { op, view } = loadHash();
  if (op && byOp.has(op)) current = byOp.get(op);
  apply();
  if (view === "stats") showView("stats");
  if (matchMedia("(max-width: 720px)").matches) toggleFilters(true);
  let resize;
  window.addEventListener("resize", () => {
    clearTimeout(resize);
    resize = setTimeout(() => !$("#view-stats").hidden && renderStats(), 150);
  });
}

main();
