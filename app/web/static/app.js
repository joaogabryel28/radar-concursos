const estado = { aba: "abertas", uf: "", area: "", curso: "", nivel: "", q: "" };
let requisicaoAtual = 0;
const ROTULO_STATUS = {
  previsto: "Previsto",
  autorizado: "Autorizado",
  edital_publicado: "Edital publicado",
  inscricoes_abertas: "Inscrições abertas",
  encerrado: "Encerrado",
};
const NIVEL = { federal: "Federal", estadual: "Estadual", municipal: "Municipal" };
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

function esc(s) {
  return (s ?? "").toString().replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtQuando(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const hoje = new Date();
  const umDia = 86400000;
  const d0 = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const h0 = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const dias = Math.round((h0 - d0) / umDia);
  if (dias === 0) return "hoje";
  if (dias === 1) return "ontem";
  if (dias < 7) return `${dias} dias atrás`;
  return d.toLocaleDateString("pt-BR");
}

function eNovo(iso) {
  if (!iso) return false;
  return (Date.now() - new Date(iso).getTime()) < 3 * 86400000;
}

function chip(id, rotulo, valor) {
  return `<div class="chip" data-aba="${id}"><b>${valor}</b>${rotulo}</div>`;
}

function renderStats(meta) {
  const c = meta.contagens || {};
  const el = document.getElementById("stats");
  el.innerHTML =
    chip("abertas", "inscrições abertas", c.inscricoes_abertas || 0) +
    chip("publicados", "editais publicados", c.edital_publicado || 0) +
    chip("previstos", "previstos e autorizados", (c.previsto || 0) + (c.autorizado || 0)) +
    chip("todos", "no total", Object.values(c).reduce((a, b) => a + b, 0)) +
    `<div class="chip" style="cursor:default"><b>${meta.novos_7d}</b>detectados nos últimos 7 dias</div>`;
  marcarSelecionados();
}

function marcarSelecionados() {
  document.querySelectorAll(".chip[data-aba]").forEach(ch =>
    ch.classList.toggle("selecionado", ch.dataset.aba === estado.aba));
  document.querySelectorAll("#tabs button").forEach(b =>
    b.classList.toggle("ativo", b.dataset.aba === estado.aba));
}

function card(it) {
  const badges = [];
  if (it.uf) badges.push(`<span class="badge uf">${esc(it.uf)}</span>`);
  if (it.nivel) badges.push(`<span class="badge uf">${NIVEL[it.nivel] || esc(it.nivel)}</span>`);
  badges.push(`<span class="badge status-${esc(it.status)}">${ROTULO_STATUS[it.status] || esc(it.status)}</span>`);
  if (it.banca) badges.push(`<span class="badge banca">banca ${esc(it.banca)}</span>`);
  if (eNovo(it.primeira_deteccao)) badges.push(`<span class="badge novo">NOVO</span>`);

  const infos = [];
  if (it.vagas) infos.push(`👥 <b>${it.vagas}</b> vagas`);
  if (it.salario_max) infos.push(`💰 até <b>${brl.format(it.salario_max)}</b>`);
  if (it.data_inscricoes) infos.push(`📅 inscrições até <b>${new Date(it.data_inscricoes + "T12:00").toLocaleDateString("pt-BR")}</b>`);
  if (it.data_prova) infos.push(`📝 prova em <b>${new Date(it.data_prova + "T12:00").toLocaleDateString("pt-BR")}</b>`);

  const links = [];
  if (it.edital_url) links.push(`<a href="${esc(it.edital_url)}" target="_blank" rel="noopener">📄 Edital / página oficial</a>`);
  if (it.inscricoes_url) links.push(`<a href="${esc(it.inscricoes_url)}" target="_blank" rel="noopener">✍️ Inscrições</a>`);
  if (it.fonte_url && it.fonte_url !== it.edital_url) links.push(`<a href="${esc(it.fonte_url)}" target="_blank" rel="noopener">🔗 Fonte</a>`);

  const onde = [it.municipio, it.uf].filter(Boolean).join("/");
  const detalhe = it.descricao && it.descricao !== it.orgao ? it.descricao : "";

  return `<article class="card">
    <h3><a href="${esc(it.edital_url || it.fonte_url)}" target="_blank" rel="noopener">${esc(it.orgao)}</a></h3>
    ${detalhe ? `<h3 style="font-size:13.5px;color:#475569;font-weight:500;margin:-2px 0 6px">${esc(detalhe)}</h3>` : ""}
    <div class="badges">${badges.join("")}</div>
    ${infos.length ? `<div class="info">${infos.join("")}</div>` : ""}
    ${it.resumo ? `<p class="resumo">${esc(it.resumo)}</p>` : ""}
    <div class="links">${links.join("")}</div>
    <div class="rodape">Detectado ${fmtQuando(it.primeira_deteccao)} via ${esc(it.fonte_nome || it.fonte)}${onde ? " · " + esc(onde) : ""}${(it.areas || []).length ? " · " + esc(it.areas.join(", ")) : ""}</div>
  </article>`;
}

async function carregar() {
  const lista = document.getElementById("lista");
  const meuToken = ++requisicaoAtual;
  lista.innerHTML = `<div class="carregando">Carregando…</div>`;
  const p = new URLSearchParams({ aba: estado.aba });
  for (const k of ["uf", "area", "curso", "nivel", "q"]) if (estado[k]) p.set(k, estado[k]);
  try {
    const r = await fetch("/api/concursos?" + p.toString());
    if (!r.ok) throw new Error("servidor respondeu " + r.status);
    const dados = await r.json();
    if (meuToken !== requisicaoAtual) return; // resposta antiga: ignora
    if (!dados.itens.length) {
      lista.innerHTML = `<div class="vazio">Nenhum concurso encontrado com esses filtros.<br>Tente a aba "Todos", limpe os filtros ou clique em "⟳ Buscar agora".</div>`;
      return;
    }
    lista.innerHTML = `<div class="contador">${dados.total} concurso${dados.total > 1 ? "s" : ""} nesta visão</div>` +
      dados.itens.map(card).join("");
  } catch (err) {
    if (meuToken !== requisicaoAtual) return;
    lista.innerHTML = `<div class="vazio">Falha ao carregar (${esc(err.message)}).<br>Verifique se o servidor está rodando e <a href="#" onclick="carregar();return false" style="color:var(--azul)">tente de novo</a>.</div>`;
  }
}

async function carregarMeta() {
  const r = await fetch("/api/meta");
  const meta = await r.json();
  renderStats(meta);
  const preencher = (id, valores, atual) => {
    const sel = document.getElementById(id);
    sel.querySelectorAll("option:not([value=''])").forEach(o => o.remove());
    valores.forEach(v => {
      const o = document.createElement("option");
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    });
    if (atual) sel.value = atual;
  };
  preencher("f-uf", meta.ufs || [], estado.uf);
  preencher("f-area", meta.areas || [], estado.area);
  preencher("f-curso", meta.cursos || [], estado.curso);
}

function setAba(aba) {
  estado.aba = aba;
  marcarSelecionados();
  carregar();
}

// Delegação com closest: o clique vale em qualquer ponto do botão/chip
document.getElementById("tabs").addEventListener("click", e => {
  const btn = e.target.closest("button[data-aba]");
  if (btn) setAba(btn.dataset.aba);
});
document.getElementById("stats").addEventListener("click", e => {
  const ch = e.target.closest(".chip[data-aba]");
  if (ch) setAba(ch.dataset.aba);
});

for (const [id, chave] of [["f-uf", "uf"], ["f-area", "area"], ["f-curso", "curso"], ["f-nivel", "nivel"]]) {
  document.getElementById(id).addEventListener("change", e => {
    estado[chave] = e.target.value;
    carregar();
  });
}
let timerQ = null;
document.getElementById("f-q").addEventListener("input", e => {
  clearTimeout(timerQ);
  timerQ = setTimeout(() => { estado.q = e.target.value.trim(); carregar(); }, 300);
});
document.getElementById("btn-limpar").addEventListener("click", () => {
  Object.assign(estado, { uf: "", area: "", curso: "", nivel: "", q: "" });
  for (const id of ["f-uf", "f-area", "f-curso", "f-nivel", "f-q"]) document.getElementById(id).value = "";
  carregar();
});

document.getElementById("btn-coletar").addEventListener("click", async e => {
  const btn = e.target;
  btn.disabled = true;
  btn.textContent = "Coletando… (1-2 min)";
  try {
    const r = await fetch("/api/coletar", { method: "POST" });
    const resumo = await r.json();
    const partes = Object.entries(resumo).map(([f, i]) =>
      i.erro ? `${f}: ERRO (${i.erro.slice(0, 60)})` : `${f}: ${i.vistos} vistos, ${i.novos} novos`);
    mostrarToast("Coleta concluída!\n" + partes.join("\n"));
    await Promise.all([carregarMeta(), carregar()]);
  } catch (err) {
    mostrarToast("Falha na coleta: " + err);
  } finally {
    btn.disabled = false;
    btn.textContent = "⟳ Buscar agora";
  }
});

let toastTimer = null;
function mostrarToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("visivel");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("visivel"), 6000);
}

carregarMeta();
carregar();
