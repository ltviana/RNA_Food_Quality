/* Controle de Qualidade de Frutas — interface em JavaScript puro (sem frameworks).
   Conversa com o servidor Python (servidor_app.py) pela API /api/... */
(function () {
  "use strict";

  // =================================================================== ícones
  const ICONES = {
    grid: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    plus: '<circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/>',
    layers: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    truck: '<path d="M3 6h11v10H3z"/><path d="M14 9h4l3 3v4h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    sair: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    entrar: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5M15 12H3"/>',
    fruta: '<path d="M12 7.5c-1.5-1-4.5-1.2-6 1-1.6 2.4-1 6.5 1 9 1.2 1.5 2.5 2.3 3.5 1.8.7-.3 1.3-.3 3 0 1 .5 2.3-.3 3.5-1.8 2-2.5 2.6-6.6 1-9-1.5-2.2-4.5-2-6-1z"/><path d="M12 7.5c0-2 1-3.5 3-4"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
    alerta: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z"/><circle cx="12" cy="13" r="3"/>',
    filme: '<rect x="2" y="3" width="20" height="18" rx="2"/><path d="M7 3v18M17 3v18M2 8h5M2 16h5M17 8h5M17 16h5M2 12h20"/>',
    lixo: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    parar: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    caixa: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    dinheiro: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    queda: '<path d="m22 17-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/>',
    alta: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    porcento: '<path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    folha: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z"/><path d="M2 21c0-3 1.9-5.4 5.1-6"/>',
    duvida: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
    carteira: '<rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20M16 15h2"/>',
    etiqueta: '<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.7 8.7a2.4 2.4 0 0 0 3.4 0l6.6-6.6a2.4 2.4 0 0 0 0-3.4z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    ajustes: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    relogio: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    lapis: '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/>',
    alvo: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    brilho: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    cadeado: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    chave: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
    sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    lua: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    seta: '<path d="m6 9 6 6 6-6"/>',
    salvar: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    sobe: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    desce: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
    atualizar: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    predio: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    imagem: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    olho: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  };

  // ================================================================ utilidades
  function icone(nome, cls) {
    const s = document.createElement("span");
    s.className = "ic" + (cls ? " " + cls : "");
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = '<svg viewBox="0 0 24 24">' + (ICONES[nome] || "") + "</svg>";   // conteúdo fixo, seguro
    return s;
  }

  // Cria elementos sem innerHTML (os textos vêm do banco e são sempre tratados como texto)
  function h(tag, attrs, ...filhos) {
    const el = document.createElement(tag);
    const props = {};
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (["value", "checked", "disabled", "selected"].includes(k)) props[k] = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const f of filhos.flat(Infinity)) {
      if (f == null || f === false) continue;
      el.append(f instanceof Node ? f : document.createTextNode(String(f)));
    }
    Object.assign(el, props);
    return el;
  }

  const nfInt = new Intl.NumberFormat("pt-BR");
  const nfBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmt = {
    int: (v) => nfInt.format(Math.round(v || 0)),
    brl: (v) => nfBRL.format(v || 0),
    pct: (v) => nf1.format((v || 0) * 100) + "%",
    pctEixo: (v) => Math.round(v * 100) + "%",
    brlEixo: (v) => {
      const a = Math.abs(v);
      if (a >= 1e6) return "R$ " + (v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi";
      if (a >= 1e3) return "R$ " + (v / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mil";
      return "R$ " + nfInt.format(Math.round(v));
    },
    brlCurto: (v) => {
      const a = Math.abs(v);
      if (a >= 1e6) return "R$ " + nf1.format(v / 1e6) + " mi";
      if (a >= 1e3) return "R$ " + nf1.format(v / 1e3) + " mil";
      return "R$ " + nfInt.format(Math.round(v));
    },
    intCurto: (v) => (Math.abs(v) >= 1e4 ? nf1.format(v / 1e3) + " mil" : nfInt.format(Math.round(v))),
    data: (iso) => (iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) : ""),
    dataHora: (txt) => (txt ? fmt.data(txt.slice(0, 10)) + " " + txt.slice(11, 16) : ""),
  };
  const pad = (n) => String(n).padStart(2, "0");
  const isoDe = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const hojeISO = () => isoDe(new Date());
  function somarDias(iso, n) { const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + n); return isoDe(d); }
  function diasEntre(a, b) { return Math.round((new Date(b + "T00:00:00") - new Date(a + "T00:00:00")) / 864e5); }
  function inicioSemana(iso) { const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return isoDe(d); }
  // Preferência de animações do próprio app (não depende da configuração de animações do Windows)
  function preferenciaMovimento() { try { return localStorage.getItem("movimento") || "normal"; } catch (e) { return "normal"; } }
  function aplicarMovimento(v) {
    try { localStorage.setItem("movimento", v); } catch (e) { /* armazenamento indisponível */ }
    if (v === "reduzido") document.documentElement.dataset.movimento = "reduzido";
    else delete document.documentElement.dataset.movimento;
  }
  aplicarMovimento(preferenciaMovimento());
  const semMovimento = () => document.documentElement.dataset.movimento === "reduzido";

  // ---- giro dos ícones: ao entrar com o mouse, o ícone dá uma volta completa com um leve "pulo" de mola.
  // Feito com Web Animations para a volta sempre terminar, mesmo que o mouse saia no meio.
  const ALVOS_GIRO = ".nav a, .btn, .aba, .kpi, .segmentado button, .zona-envio, .cartao.vivo, .chip, .marca-app, .seletor-botao";
  const QUADROS_GIRO = [
    { transform: "rotate(0deg) scale(1)" },
    { transform: "rotate(-24deg) scale(0.92)", offset: 0.14 },
    { transform: "rotate(230deg) scale(1.22)", offset: 0.55 },
    { transform: "rotate(378deg) scale(1.04)", offset: 0.8 },
    { transform: "rotate(360deg) scale(1)" },
  ];
  function girar(el) {
    if (!el || semMovimento() || !el.animate) return;
    if (el._giro && el._giro.playState === "running") return;          // não reinicia no meio da volta
    el._giro = el.animate(QUADROS_GIRO, { duration: 900, easing: "cubic-bezier(0.25, 0.8, 0.3, 1)" });
  }
  document.addEventListener("pointerover", (ev) => {
    const alvo = ev.target.closest && ev.target.closest(ALVOS_GIRO);
    if (!alvo || (ev.relatedTarget && alvo.contains(ev.relatedTarget))) return;   // só ao entrar no elemento
    if (alvo.disabled) return;
    if (alvo.matches(".seletor-botao")) return;                         // a seta do seletor só vira ao abrir
    const ic = alvo.matches(".marca-app") ? alvo.querySelector(".logo")
      : alvo.matches(".kpi") ? alvo.querySelector(".bolha .ic")
      : alvo.matches(".cartao.vivo") ? alvo.querySelector("h3 .ic")
      : alvo.querySelector(".ic");
    girar(ic);
  });

  // ====================================================================== API
  async function api(metodo, url, corpo) {
    const op = { method: metodo, credentials: "same-origin", headers: {} };
    if (metodo !== "GET") {
      op.headers["Content-Type"] = "application/json";
      op.headers["X-Frutas"] = "1";
      op.body = JSON.stringify(corpo || {});
    }
    let r;
    try { r = await fetch(url, op); }
    catch (e) { throw new Error("Sem conexão com o servidor. Confira se a janela do servidor está aberta."); }
    let dados = null;
    try { dados = await r.json(); } catch (e) { /* resposta sem JSON */ }
    if (r.status === 401 && !["/api/login", "/api/estado"].includes(url)) {
      estado.usuario = null;
      telaLogin("Sua sessão expirou. Entre novamente.");
      throw new Error("Sessão expirada.");
    }
    if (!r.ok) throw new Error((dados && dados.erro) || `Erro ${r.status}`);
    return dados;
  }

  // ============================================================ componentes
  function toast(msg, tipo) {
    const t = h("div", { class: "toast " + (tipo || "ok"), role: "status" }, icone(tipo === "erro" ? "alerta" : "check"), h("span", {}, msg));
    document.getElementById("toasts").appendChild(t);
    setTimeout(() => { t.classList.add("saindo"); setTimeout(() => t.remove(), 320); }, tipo === "erro" ? 5200 : 3200);
  }

  function onda(ev) {
    const btn = ev.currentTarget;
    if (btn.disabled || semMovimento()) return;
    const r = btn.getBoundingClientRect();
    const d = Math.max(r.width, r.height);
    const o = h("span", { class: "onda", style: { width: d + "px", height: d + "px", left: ev.clientX - r.left - d / 2 + "px", top: ev.clientY - r.top - d / 2 + "px" } });
    btn.appendChild(o);
    setTimeout(() => o.remove(), 650);
  }

  // Botão com ícone, efeito de onda e estado "carregando" enquanto a ação assíncrona roda
  function botao(texto, op) {
    op = op || {};
    const b = h("button", { type: op.submit ? "submit" : "button", class: "btn " + (op.tipo || "") + (op.pequeno ? " pequeno" : "") + (!texto ? " icone-so" : ""),
      disabled: !!op.desabilitado, title: op.titulo || null, "aria-label": op.titulo || null },
      op.icone ? icone(op.icone) : null, texto || null);
    b.addEventListener("pointerdown", onda);
    if (op.acao) {
      b.addEventListener("click", async (ev) => {
        if (b.disabled) return;
        b.classList.add("carregando");
        try { await op.acao(ev); }
        catch (e) { if (e.message !== "Sessão expirada.") toast(e.message, "erro"); }
        finally { b.classList.remove("carregando"); }
      });
    }
    return b;
  }

  function campo(rotulo, controle, dica) {
    return h("div", { class: "campo" }, h("label", {}, rotulo), controle, dica ? h("span", { class: "dica-campo" }, dica) : null);
  }
  function entrada(tipo, attrs) { return h("input", Object.assign({ type: tipo }, attrs || {})); }
  function selecao(opcoes, valor, attrs) {
    const s = h("select", attrs || {}, opcoes.map(([v, t]) => h("option", { value: String(v) }, t)));
    if (valor != null) s.value = String(valor);
    return s;
  }
  function aviso(tipo, ...conteudo) {
    const ic = { ok: "check", aviso: "alerta", erro: "alerta", info: "info" }[tipo];
    return h("div", { class: "alerta-msg " + tipo, role: tipo === "erro" ? "alert" : null }, icone(ic), h("div", {}, ...conteudo));
  }
  function cartao(titulo, ic, sub, ...corpo) {
    const temGrafico = corpo.flat().some((c) => c instanceof Element && (c.classList.contains("grafico") || c.querySelector(".grafico")));
    return h("section", { class: "cartao vivo" + (temGrafico ? " de-grafico" : "") + (estado.semEntrada ? "" : " entrar") },
      titulo ? h("header", { class: "cartao-cab" }, h("div", {}, h("h3", {}, ic ? icone(ic) : null, titulo), sub ? h("p", { class: "sub" }, sub) : null)) : null,
      h("div", { class: "cartao-corpo" }, !titulo && sub ? h("p", { class: "sub" }, sub) : null, ...corpo));
  }
  function etiqueta(texto, tipo, ic) { return h("span", { class: "etiqueta " + (tipo || "neutra") }, ic ? icone(ic) : null, texto); }

  function confirmar(titulo, texto, rotuloBotao, perigo) {
    return new Promise((ok) => {
      const fechar = (v) => { fundo.remove(); document.removeEventListener("keydown", esc); ok(v); };
      const esc = (e) => { if (e.key === "Escape") fechar(false); };
      const fundo = h("div", { class: "fundo-modal", onclick: (e) => { if (e.target === fundo) fechar(false); } },
        h("div", { class: "modal", role: "dialog", "aria-modal": "true" }, h("h2", {}, titulo), h("p", {}, texto),
          h("div", { class: "acoes", style: { justifyContent: "flex-end" } },
            botao("Cancelar", { tipo: "fantasma", acao: () => fechar(false) }),
            botao(rotuloBotao || "Confirmar", { tipo: perigo ? "primario" : "primario", icone: perigo ? "lixo" : "check", acao: () => fechar(true) }))));
      document.addEventListener("keydown", esc);
      document.body.appendChild(fundo);
      fundo.querySelector(".btn.primario").focus();
    });
  }
  function pedirTexto(titulo, rotulo, tipo) {
    return new Promise((ok) => {
      const inp = entrada(tipo || "text", { autocomplete: "new-password" });
      const fechar = (v) => { fundo.remove(); ok(v); };
      const fundo = h("div", { class: "fundo-modal" },
        h("form", { class: "modal", onsubmit: (e) => { e.preventDefault(); fechar(inp.value); } },
          h("h2", {}, titulo), h("div", { class: "form-coluna", style: { margin: "16px 0" } }, campo(rotulo, inp)),
          h("div", { class: "acoes", style: { justifyContent: "flex-end" } },
            botao("Cancelar", { tipo: "fantasma", acao: () => fechar(null) }), botao("Salvar", { tipo: "primario", icone: "salvar", submit: true }))));
      document.body.appendChild(fundo);
      inp.focus();
    });
  }

  // Seletor de vários itens (fornecedores / frutas)
  function seletorMultiplo(itens, selecionados, rotuloTodos, aoMudar) {
    const sel = new Set(selecionados);
    const raiz = h("div", { class: "seletor" });
    const txt = h("span", {});
    const botaoSel = h("button", { type: "button", class: "seletor-botao", "aria-haspopup": "listbox" }, txt, icone("seta"));
    const lista = h("div", { class: "seletor-lista", role: "listbox" });
    const atualizarTexto = () => {
      txt.textContent = !sel.size ? rotuloTodos : sel.size === 1 ? itens.find((i) => sel.has(i.id))?.nome || "1 selecionado" : sel.size + " selecionados";
    };
    for (const it of itens) {
      const cb = h("input", { type: "checkbox", checked: sel.has(it.id) });
      cb.addEventListener("change", () => { cb.checked ? sel.add(it.id) : sel.delete(it.id); atualizarTexto(); aoMudar([...sel]); });
      lista.appendChild(h("label", {}, cb, it.nome));
    }
    lista.appendChild(h("div", { class: "limpar" }, botao("Limpar seleção", { tipo: "fantasma", pequeno: true, icone: "x", acao: () => {
      sel.clear(); lista.querySelectorAll("input").forEach((c) => (c.checked = false)); atualizarTexto(); aoMudar([]);
    } })));
    botaoSel.addEventListener("click", () => raiz.classList.toggle("aberto"));
    document.addEventListener("click", (e) => { if (!raiz.contains(e.target)) raiz.classList.remove("aberto"); });
    raiz.append(botaoSel, lista);
    atualizarTexto();
    return raiz;
  }

  // Tabela simples: colunas = [{titulo, valor:(linha)=>..., num:true}]
  function tabela(colunas, linhas, op) {
    op = op || {};
    const corpo = h("tbody", {});
    for (const l of linhas) {
      const tr = h("tr", { class: (op.aoClicar ? "clicavel " : "") + (op.classeLinha ? op.classeLinha(l) : "") },
        colunas.map((c) => h("td", { class: c.num ? "num" : "" }, c.valor(l))));
      if (op.aoClicar) tr.addEventListener("click", (ev) => op.aoClicar(l, tr, ev));
      corpo.appendChild(tr);
    }
    if (!linhas.length) corpo.appendChild(h("tr", {}, h("td", { colspan: colunas.length, style: { textAlign: "center", color: "var(--texto-3)" } }, op.vazio || "Nada para mostrar.")));
    return h("div", { class: "tabela-wrap" + (op.rolagem ? " tabela-rolagem" : "") },
      h("table", {}, h("thead", {}, h("tr", {}, colunas.map((c) => h("th", { class: c.num ? "num" : "" }, c.titulo)))), corpo));
  }

  // Indicador com número que "conta" até o valor e variação contra o período anterior
  function kpi(o) {
    const de = estado.kpiAnterior[o.rotulo] != null ? estado.kpiAnterior[o.rotulo] : 0;
    estado.kpiAnterior[o.rotulo] = o.valor;
    const valor = h("div", { class: "valor" }, o.formato(de));
    const el = h("div", { class: "kpi" + (estado.semEntrada ? "" : " entrar"), title: o.ajuda || null },
      h("div", { class: "topo" }, h("span", { class: "rotulo" }, o.rotulo), h("span", { class: "bolha" }, icone(o.icone || "info"))),
      valor,
      o.delta ? h("span", { class: "delta " + o.delta.classe }, icone(o.delta.sobe ? "sobe" : "desce"), o.delta.texto) : null,
      o.ajuda ? h("div", { class: "ajuda" }, o.ajuda) : null);
    contar(valor, o.valor, o.formato, de);
    return el;
  }
  function contar(el, alvo, formato, de) {
    de = de || 0;
    if (semMovimento() || !isFinite(alvo) || !isFinite(de)) { el.textContent = formato(alvo); return; }
    const t0 = performance.now(), dur = 800;
    const passo = (t) => {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = formato(de + (alvo - de) * e);
      if (p < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }
  // variação: bomSubir=true quando aumentar é bom (lucro), false quando é ruim (perda), null = neutro
  function delta(atual, anterior, tipo, bomSubir) {
    if (anterior == null) return null;
    const d = atual - anterior;
    if (Math.abs(d) < 1e-9) return { texto: "sem variação", classe: "neutro", sobe: true };
    const texto = tipo === "pp" ? (d > 0 ? "+" : "") + nf1.format(d * 100) + " p.p." :
      tipo === "brl" ? (d > 0 ? "+" : "−") + nfBRL.format(Math.abs(d)) : (d > 0 ? "+" : "−") + nfInt.format(Math.abs(Math.round(d)));
    const classe = bomSubir == null ? "neutro" : (d > 0) === bomSubir ? "bom" : "ruim";
    return { texto, classe, sobe: d > 0 };
  }

  // ================================================================== tema
  function aplicarTema(t) {
    if (t === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("tema", t); } catch (e) { /* armazenamento indisponível */ }
    window.dispatchEvent(new Event("tema-alterado"));
  }
  function temaAtual() { try { return localStorage.getItem("tema") || "auto"; } catch (e) { return "auto"; } }
  aplicarTema(temaAtual());
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => window.dispatchEvent(new Event("tema-alterado")));

  // ============================================================ marca (logo/nome)
  const faviconPadrao = (document.querySelector("link[rel=icon]") || {}).href;
  // Cria o quadrado da logo; ele é atualizado sozinho quando a logo muda (data-logo)
  function logoEl(classeIcone) {
    const el = h("div", { class: "logo", "data-logo": classeIcone || "" });
    preencherLogo(el);
    return el;
  }
  function preencherLogo(el) {
    const url = estado.marca && estado.marca.logo_url;
    el.classList.toggle("com-imagem", !!url);
    el.replaceChildren(url ? h("img", { src: url, alt: "Logo " + (estado.marca.nome || "") }) : icone("fruta", el.dataset.logo || ""));
  }
  function aplicarMarca(m) {
    if (m) estado.marca = m;
    const mc = estado.marca || {};
    document.querySelectorAll("[data-logo]").forEach(preencherLogo);
    document.querySelectorAll("[data-empresa-nome]").forEach((el) => (el.textContent = mc.nome || el.dataset.empresaNome || "Frutas"));
    document.querySelectorAll("[data-empresa-slogan]").forEach((el) => (el.textContent = mc.slogan || "Qualidade de frutas"));
    let fav = document.querySelector("link[rel=icon]");
    if (!fav) { fav = h("link", { rel: "icon" }); document.head.appendChild(fav); }
    fav.href = mc.logo_url || faviconPadrao;
  }

  // ================================================================ estado
  const estado = { usuario: null, meta: null, timers: [], rodada: 0,
    dash: { periodo: "30", ini: somarDias(hojeISO(), -29), fim: hojeISO(), forn: [], frutas: [], aba: "volume",
      sel: { fornecedor: [], fruta: [], tempo: [] } }, kpiAnterior: {} };
  const raiz = document.getElementById("raiz");
  const PAGINAS = [
    { id: "dashboard", nome: "Dashboard", grupo: "Análise", icone: "grid", perfis: ["admin", "operador", "visualizador"], render: paginaDashboard },
    { id: "esteira", nome: "Executar esteira", grupo: "Operação", icone: "play", perfis: ["admin", "operador"], render: paginaEsteira },
    { id: "registrar", nome: "Registrar contagem", grupo: "Operação", icone: "plus", perfis: ["admin", "operador"], render: paginaRegistrar },
    { id: "lotes", nome: "Lotes e revisão", grupo: "Operação", icone: "layers", perfis: ["admin", "operador", "visualizador"], render: paginaLotes },
    { id: "fornecedores", nome: "Fornecedores e preços", grupo: "Cadastros", icone: "truck", perfis: ["admin"], render: paginaFornecedores },
    { id: "usuarios", nome: "Usuários", grupo: "Administração", icone: "users", perfis: ["admin"], render: paginaUsuarios },
    { id: "empresa", nome: "Dados da empresa", grupo: "Administração", icone: "predio", perfis: ["admin"], render: paginaEmpresa },
    { id: "conta", nome: "Minha conta", grupo: "Conta", icone: "user", perfis: ["admin", "operador", "visualizador"], render: paginaConta },
  ];
  const ehAdmin = () => estado.usuario && estado.usuario.perfil === "admin";
  const podeOperar = () => estado.usuario && ["admin", "operador"].includes(estado.usuario.perfil);
  function intervalo(fn, ms) { const id = setInterval(fn, ms); estado.timers.push(id); return id; }
  function nomeFruta(id) { return (estado.meta && estado.meta.nomes[String(id).toLowerCase()]) || id; }

  // ============================================================ login / setup
  async function iniciar() {
    let e;
    try { e = await api("GET", "/api/estado"); }
    catch (err) { raiz.replaceChildren(h("div", { class: "tela-login" }, aviso("erro", err.message))); return; }
    estado.marca = e.marca;
    aplicarMarca();
    if (!e.tem_usuarios) return telaSetup();
    if (!e.usuario) return telaLogin();
    estado.usuario = e.usuario;
    await montarApp();
  }

  function telaLogin(msg) {
    estado.timers.forEach(clearInterval); estado.timers = [];
    const login = entrada("text", { autocomplete: "username", required: true });
    const senha = entrada("password", { autocomplete: "current-password", required: true });
    const erro = h("div", {});
    const form = h("form", { class: "form-coluna" }, erro, campo("Login", login), campo("Senha", senha),
      botao("Entrar", { tipo: "primario", icone: "entrar", submit: true }));
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const b = form.querySelector("button[type=submit]");
      b.classList.add("carregando");
      try {
        const r = await api("POST", "/api/login", { login: login.value, senha: senha.value });
        estado.usuario = r.usuario;
        await montarApp();
      } catch (e) { erro.replaceChildren(aviso("erro", e.message)); senha.select(); }
      finally { b.classList.remove("carregando"); }
    });
    raiz.replaceChildren(telaAcesso("Acesse sua conta", "Entre com o login e a senha fornecidos pelo administrador.",
      msg ? aviso("info", msg) : null, form));
    login.focus();
  }

  // Tela de acesso: painel da marca à esquerda, formulário à direita
  function telaAcesso(titulo, sub, extra, form) {
    const mc = estado.marca || {};
    return h("div", { class: "tela-login" },
      h("aside", { class: "painel-marca" },
        h("div", { class: "entrar" }, logoEl(),
          h("h1", { "data-empresa-nome": "Controle de Qualidade" }, mc.nome || "Controle de Qualidade"),
          h("div", { class: "slogan" }, mc.slogan || "Qualidade do campo à mesa"),
          h("p", { class: "descricao" }, mc.descricao || "Sistema de controle de qualidade e perdas de frutas e hortaliças, com contagem automática por visão computacional.")),
        h("div", { class: "rodape" }, "© " + new Date().getFullYear() + " " + (mc.nome || "") + " · Sistema de Controle de Qualidade")),
      h("main", { class: "lado-form" }, h("div", { class: "caixa-login entrar" },
        h("h2", {}, titulo), h("p", { class: "sub" }, sub), extra, form,
        h("div", { class: "seguro" }, icone("cadeado"), "Conexão local protegida · sessão expira após 12 horas sem uso"))));
  }

  function telaSetup() {
    const c = { empresa: entrada("text"), nome: entrada("text"), login: entrada("text", { autocomplete: "username" }),
      senha: entrada("password", { autocomplete: "new-password" }), senha2: entrada("password", { autocomplete: "new-password" }) };
    const erro = h("div", {});
    const form = h("form", { class: "form-coluna" }, erro, campo("Nome da empresa", c.empresa), campo("Seu nome", c.nome),
      campo("Login (sem espaços)", c.login), campo("Senha", c.senha, "Mínimo de 8 caracteres, com maiúsculas, minúsculas e número."),
      campo("Repita a senha", c.senha2), botao("Criar conta de administrador", { tipo: "primario", icone: "check", submit: true }));
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      try {
        await api("POST", "/api/setup", Object.fromEntries(Object.entries(c).map(([k, v]) => [k, v.value])));
        toast("Conta criada! Entre com seu login e senha.");
        telaLogin();
      } catch (e) { erro.replaceChildren(aviso("erro", e.message)); }
    });
    raiz.replaceChildren(telaAcesso("Primeiro acesso", "Crie a empresa e a conta do administrador.", null, form));
    c.empresa.focus();
  }

  // ============================================================ estrutura
  async function carregarMeta() { estado.meta = await api("GET", "/api/meta"); aplicarMarca(estado.meta.marca); }

  async function montarApp() {
    await carregarMeta();
    const u = estado.usuario;
    const nav = h("nav", { class: "nav", "aria-label": "Menu" });
    let grupoAtual = null;
    for (const p of PAGINAS.filter((p) => p.perfis.includes(u.perfil))) {
      if (p.grupo !== grupoAtual) { grupoAtual = p.grupo; nav.appendChild(h("div", { class: "rotulo-secao-nav" }, p.grupo)); }
      nav.appendChild(h("a", { href: "#/" + p.id, "data-pagina": p.id }, icone(p.icone), p.nome));
    }
    const iniciais = u.nome.split(/\s+/).filter(Boolean).slice(0, 2).map((x) => x[0].toUpperCase()).join("");
    const temas = [["auto", "monitor", "Tema: automático"], ["light", "sol", "Tema: claro"], ["dark", "lua", "Tema: escuro"]];
    const botaoTema = h("button", { type: "button", class: "btn fantasma icone-so" });
    const pintarTema = () => { const t = temas.find((x) => x[0] === temaAtual()) || temas[0]; botaoTema.replaceChildren(icone(t[1])); botaoTema.title = t[2]; botaoTema.setAttribute("aria-label", t[2]); };
    botaoTema.addEventListener("click", () => { const i = temas.findIndex((x) => x[0] === temaAtual()); aplicarTema(temas[(i + 1) % 3][0]); pintarTema(); });
    botaoTema.addEventListener("pointerdown", onda);
    pintarTema();
    const nomeEmpresa = h("div", { class: "nome", "data-empresa-nome": "Frutas" }, estado.marca.nome || "Frutas");
    const lateral = h("aside", { class: "lateral" },
      h("a", { class: "marca-app", href: "#/dashboard", style: { textDecoration: "none", color: "inherit" } }, logoEl("grande"),
        h("div", {}, nomeEmpresa, h("div", { class: "sub", "data-empresa-slogan": "" }, estado.marca.slogan || "Qualidade de frutas"))),
      nav, h("div", { class: "espaco" }),
      h("div", { class: "cartao-usuario" }, h("div", { class: "avatar" }, iniciais || "?"),
        h("div", { class: "quem" }, h("b", {}, u.nome), h("span", {}, u.perfil)), botaoTema),
      h("div", { class: "acoes-lateral" }, botao("Sair", { icone: "sair", pequeno: true, acao: async () => {
        await api("POST", "/api/logout"); estado.usuario = null; location.hash = ""; telaLogin();
      } })),
      h("div", { class: "rodape-lateral" }, "Sistema de Controle de Qualidade"));
    const app = h("div", { class: "app" });
    const barraMovel = h("div", { class: "barra-movel" },
      botao("", { tipo: "fantasma", icone: "menu", titulo: "Abrir menu", acao: () => app.classList.toggle("menu-aberto") }),
      logoEl(), h("b", { "data-empresa-nome": "Frutas" }, estado.marca.nome || "Frutas"));
    const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    const cabecalho = h("header", { class: "cabecalho" },
      h("div", { class: "trilha", id: "trilha" }),
      h("div", { class: "direita" }, h("span", {}, hoje.charAt(0).toUpperCase() + hoje.slice(1)), h("span", { class: "selo-ao-vivo" }, "Sistema online")));
    const principal = h("main", { class: "principal" }, h("div", { class: "conteudo", id: "conteudo" }));
    app.append(lateral, h("div", {}, barraMovel, cabecalho, principal));
    nav.addEventListener("click", () => app.classList.remove("menu-aberto"));
    raiz.replaceChildren(app);
    aplicarMarca();
    rotear();
  }

  function rotear() {
    if (!estado.usuario) return;
    estado.timers.forEach(clearInterval);
    estado.timers = [];
    estado.rodada++;
    window.Graficos.esconderDica();
    const partes = location.hash.replace(/^#\/?/, "").split("/");
    const permitidas = PAGINAS.filter((p) => p.perfis.includes(estado.usuario.perfil));
    const pag = permitidas.find((p) => p.id === partes[0]) || permitidas[0];
    document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("ativo", a.dataset.pagina === pag.id));
    estado.paginaAtual = pag;
    document.title = pag.nome + " · " + ((estado.marca && estado.marca.nome) || "Qualidade de Frutas");
    const trilha = document.getElementById("trilha");
    if (trilha) trilha.replaceChildren(h("span", { "data-empresa-nome": "Frutas" }, (estado.marca && estado.marca.nome) || "Frutas"),
      h("span", { class: "sep" }, "/"), h("span", {}, pag.grupo), h("span", { class: "sep" }, "/"), h("b", {}, pag.nome));
    const cont = document.getElementById("conteudo");
    if (!cont) return;
    cont.replaceChildren();
    const r = estado.rodada;
    Promise.resolve(pag.render(cont, partes[1])).catch((e) => {
      if (r === estado.rodada && e.message !== "Sessão expirada.") cont.appendChild(aviso("erro", e.message));
    }).finally(() => window.Graficos.limpar());
  }
  window.addEventListener("hashchange", rotear);

  function topo(titulo, sub, ...acoes) {
    const grupo = estado.paginaAtual && estado.paginaAtual.grupo;
    return h("div", { class: "topo-pagina" }, h("div", {}, grupo ? h("div", { class: "sobretitulo" }, grupo === "Análise" ? "Painel executivo" : grupo) : null,
      h("h1", {}, titulo), sub ? h("p", {}, sub) : null),
      acoes.length ? h("div", { class: "acoes" }, ...acoes) : null);
  }

  // =================================================================== DASHBOARD
  const SOMAS = ["frescas", "estragadas", "incertas", "total", "custo_total", "receita_potencial", "receita_realizada",
    "receita_perdida", "custo_perdido", "receita_em_revisao", "lucro_realizado"];
  function somar(linhas) {
    const t = Object.fromEntries(SOMAS.map((k) => [k, 0]));
    for (const r of linhas) for (const k of SOMAS) t[k] += r[k] || 0;
    t.perda_pct = t.total ? t.estragadas / t.total : 0;
    t.margem = t.receita_realizada ? t.lucro_realizado / t.receita_realizada : 0;
    return t;
  }
  function agrupar(linhas, chave) {
    const m = new Map();
    for (const r of linhas) { const k = chave(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    return [...m].map(([k, rs]) => Object.assign({ chave: k }, somar(rs)));
  }

  function intervaloDashboard() {
    const d = estado.dash, hoje = hojeISO();
    if (d.periodo === "30") return [somarDias(hoje, -29), hoje];
    if (d.periodo === "90") return [somarDias(hoje, -89), hoje];
    if (d.periodo === "ano") return [hoje.slice(0, 4) + "-01-01", hoje];
    if (d.periodo === "tudo") return ["2000-01-01", hoje];
    return [d.ini || hoje, d.fim || hoje];
  }

  async function paginaDashboard(cont, sub) {
    const d = estado.dash;
    if (sub === "financeiro" || sub === "volume") d.aba = sub;
    const meta = estado.meta;
    cont.appendChild(topo("Dashboard", "Clique nos gráficos para filtrar · Ctrl + clique escolhe vários",
      botao("Baixar CSV", { icone: "download", acao: () => baixarCSV() })));
    if (!meta.fornecedores.length) {
      cont.appendChild(aviso("info", "Nenhum fornecedor cadastrado ainda. Cadastre fornecedores, preços e contagens para ver o dashboard."));
      if (ehAdmin()) cont.appendChild(botao("Gerar dados de exemplo", { icone: "brilho", tipo: "primario", acao: async () => {
        await api("POST", "/api/exemplo"); await carregarMeta(); rotear();
      } }));
      return;
    }
    // ---- filtros (uma linha, acima de tudo)
    const ini = entrada("date", { value: d.ini, max: hojeISO() });
    const fim = entrada("date", { value: d.fim, max: hojeISO() });
    const datas = h("div", { class: "campo", style: { display: d.periodo === "custom" ? "flex" : "none", flexDirection: "row", gap: "8px" } },
      campo("De", ini), campo("Até", fim));
    const periodo = selecao([["30", "Últimos 30 dias"], ["90", "Últimos 90 dias"], ["ano", "Este ano"], ["tudo", "Tudo"], ["custom", "Personalizado"]], d.periodo);
    periodo.addEventListener("change", () => { d.periodo = periodo.value; d.sel.tempo = []; datas.style.display = d.periodo === "custom" ? "flex" : "none"; carregar(); });
    ini.addEventListener("change", () => { d.ini = ini.value; d.sel.tempo = []; carregar(); });
    fim.addEventListener("change", () => { d.fim = fim.value; d.sel.tempo = []; carregar(); });
    const selForn = seletorMultiplo(meta.fornecedores.map((f) => ({ id: f.id, nome: f.nome })), d.forn, "Todos os fornecedores", (v) => { d.forn = v; carregar(); });
    const selFrutas = seletorMultiplo(meta.frutas.map((f) => ({ id: f.id, nome: f.nome })), d.frutas, "Todas as frutas", (v) => { d.frutas = v; carregar(); });
    cont.appendChild(h("div", { class: "filtros" }, campo("Período", periodo), datas, campo("Fornecedores", selForn), campo("Frutas", selFrutas)));

    // ---- abas
    const abaVol = h("button", { type: "button", class: "aba", role: "tab" }, icone("caixa"), "Volume de frutas");
    const abaFin = h("button", { type: "button", class: "aba", role: "tab" }, icone("dinheiro"), "Financeiro (R$)");
    const pintarAbas = () => { abaVol.classList.toggle("ativa", d.aba === "volume"); abaFin.classList.toggle("ativa", d.aba === "financeiro");
      abaVol.setAttribute("aria-selected", d.aba === "volume"); abaFin.setAttribute("aria-selected", d.aba === "financeiro"); };
    const trocar = (a) => { d.aba = a; pintarAbas(); history.replaceState(null, "", "#/dashboard/" + a); desenhar(true); };
    abaVol.addEventListener("click", () => trocar("volume"));
    abaFin.addEventListener("click", () => trocar("financeiro"));
    pintarAbas();
    cont.appendChild(h("div", { class: "abas", role: "tablist" }, abaVol, abaFin));
    const area = h("div", {});
    cont.appendChild(area);

    let dados = null, versao = 0;
    async function carregar() {
      const v = ++versao;
      const [a, b] = intervaloDashboard();
      const q = (x, y) => `/api/linhas?ini=${x}&fim=${y}&forn=${d.forn.join(",")}&frutas=${encodeURIComponent(d.frutas.join(","))}`;
      area.classList.add("recarregando");                           // mantém o desenho anterior enquanto recarrega
      const dias = diasEntre(a, b) + 1;
      const [atual, anterior] = await Promise.all([api("GET", q(a, b)),
        d.periodo === "tudo" ? Promise.resolve(null) : api("GET", q(somarDias(a, -dias), somarDias(a, -1)))]);
      if (v !== versao) return;
      dados = { linhas: atual, anterior, ini: a, fim: b, dias, semanal: dias > 45 };
      area.classList.remove("recarregando");
      desenhar(true);
    }
    // Filtro cruzado: clicar num item seleciona; clicar de novo desmarca; Ctrl/Shift + clique soma à seleção
    function alternar(dim, chave, ev) {
      const lista = d.sel[dim];
      const tem = lista.includes(chave);
      if (ev && (ev.ctrlKey || ev.metaKey || ev.shiftKey)) d.sel[dim] = tem ? lista.filter((x) => x !== chave) : lista.concat([chave]);
      else d.sel[dim] = tem && lista.length === 1 ? [] : [chave];
      desenhar(false);
    }
    function limparDim(dim) { if (d.sel[dim].length) { d.sel[dim] = []; desenhar(false); } }
    function definir(parcial) { Object.assign(d.sel, parcial); desenhar(false); }
    function desenhar(animar) {
      if (!dados) return;
      const y = window.scrollY;
      area.style.minHeight = area.offsetHeight + "px";                  // evita "pulo" da página ao redesenhar
      area.replaceChildren();
      window.Graficos.esconderDica();
      window.Graficos.definirAnimacao(animar);
      estado.semEntrada = !animar;
      if (!dados.linhas.length) area.appendChild(aviso("aviso", "Não há contagens neste período/filtro."));
      else {
        const ctx = criarContexto(dados, d.sel, alternar, limparDim, definir);
        area.appendChild(barraFiltrosAtivos(d.sel, dados.semanal, () => { d.sel = { fornecedor: [], fruta: [], tempo: [] }; desenhar(false); },
          (dim, chave) => { d.sel[dim] = d.sel[dim].filter((x) => x !== chave); desenhar(false); }));
        (d.aba === "financeiro" ? abaFinanceiro : abaVolume)(area, ctx);
        estado.dash.ultimas = ctx.filtrar(null);
      }
      window.Graficos.definirAnimacao(true);
      estado.semEntrada = false;
      window.Graficos.limpar();
      requestAnimationFrame(() => { area.style.minHeight = ""; if (!animar) window.scrollTo(0, y); });
    }
    await carregar();
  }

  // Monta funções de filtro para o desenho atual
  function criarContexto(dd, sel, alternar, limparDim, definir) {
    const semanal = dd.semanal;
    const chaveTempo = (r) => (semanal ? inicioSemana(r.data) : r.data);
    const passa = (r, exceto) =>
      (exceto === "fornecedor" || !sel.fornecedor.length || sel.fornecedor.includes(r.fornecedor)) &&
      (exceto === "fruta" || !sel.fruta.length || sel.fruta.includes(r.fruta_nome)) &&
      (exceto === "tempo" || !sel.tempo.length || sel.tempo.includes(chaveTempo(r)));
    const filtrar = (exceto, linhas) => (linhas || dd.linhas).filter((r) => passa(r, exceto));
    const marcado = (dim) => (chave) => (sel[dim].length ? sel[dim].includes(chave) : null);
    // o período anterior respeita fornecedor/fruta selecionados; com dia/semana selecionado não há comparação justa
    const anterior = dd.anterior && dd.anterior.length && !sel.tempo.length ? filtrar("tempo", dd.anterior) : null;
    return { dd, semanal, chaveTempo, filtrar, marcado, alternar, limparDim, definir, anterior,
      tituloTempo: (k) => (semanal ? "Semana de " : "") + fmt.data(k), sel };
  }

  function barraFiltrosAtivos(sel, semanal, limparTudo, remover) {
    const chips = [];
    const nomes = { fornecedor: "Fornecedor", fruta: "Fruta", tempo: semanal ? "Semana de" : "Dia" };
    for (const dim of ["fornecedor", "fruta", "tempo"])
      for (const k of sel[dim]) {
        const b = h("button", { type: "button", class: "chip", title: "Remover filtro" }, h("span", { class: "chip-dim" }, nomes[dim]),
          dim === "tempo" ? fmt.data(k) : k, icone("x"));
        b.addEventListener("click", () => remover(dim, k));
        chips.push(b);
      }
    if (!chips.length) return h("div", { class: "filtros-ativos vazio" }, icone("olho"), "Clique em uma barra, ponto ou linha de tabela para filtrar todo o painel.");
    return h("div", { class: "filtros-ativos" }, icone("ajustes"), h("span", { class: "rotulo-campo" }, "Filtrado por:"), ...chips,
      botao("Limpar filtros", { tipo: "fantasma", pequeno: true, icone: "x", acao: async () => limparTudo() }));
  }

  function serieTempo(linhas, ctx) {
    const grupos = agrupar(linhas, ctx.chaveTempo).filter((g) => g.total > 0);
    grupos.sort((a, b) => (a.chave < b.chave ? -1 : 1));
    return grupos;
  }

  function alertasLimite(area, porForn, limite) {
    const acima = porForn.filter((f) => f.perda_pct > limite && f.total >= 50).sort((a, b) => b.perda_pct - a.perda_pct);
    if (acima.length)
      area.appendChild(aviso("erro", `Fornecedores acima do limite de perda de ${fmt.pct(limite)}: `,
        acima.map((f, i) => [i ? "; " : "", h("b", {}, f.chave), " " + fmt.pct(f.perda_pct)])));
  }
  const classeSelecao = (estadoSel) => (estadoSel === true ? "selecionada" : estadoSel === false ? "esmaecida" : "");

  // ------------------------------------------------------------- aba VOLUME
  function abaVolume(area, ctx) {
    const tudo = ctx.filtrar(null);
    const t = somar(tudo), ta = ctx.anterior ? somar(ctx.anterior) : null;
    const limite = estado.meta.limite_perda / 100;
    const porFornTodos = agrupar(ctx.filtrar("fornecedor"), (r) => r.fornecedor);
    alertasLimite(area, porFornTodos, limite);
    area.appendChild(h("div", { class: "kpis" },
      kpi({ rotulo: "Frutas processadas", valor: t.total, formato: fmt.int, icone: "caixa", delta: ta && delta(t.total, ta.total, "int", null) }),
      kpi({ rotulo: "Frescas", valor: t.frescas, formato: fmt.int, icone: "folha", delta: ta && delta(t.frescas, ta.frescas, "int", true) }),
      kpi({ rotulo: "Estragadas", valor: t.estragadas, formato: fmt.int, icone: "lixo", delta: ta && delta(t.estragadas, ta.estragadas, "int", false) }),
      kpi({ rotulo: "Taxa de perda", valor: t.perda_pct, formato: fmt.pct, icone: "porcento", delta: ta && delta(t.perda_pct, ta.perda_pct, "pp", false) }),
      kpi({ rotulo: "Incertas a revisar", valor: t.incertas, formato: fmt.int, icone: "duvida", ajuda: "A IA não teve certeza; revise em Lotes e revisão." })));
    area.appendChild(notaComparacao(ctx));

    const grupos = serieTempo(ctx.filtrar("tempo"), ctx);
    const unidade = ctx.semanal ? "semana" : "dia";
    const gLinha = h("div", { class: "grafico" }), gVol = h("div", { class: "grafico" });
    const gForn = h("div", { class: "grafico" }), gComp = h("div", { class: "grafico" }), gFruta = h("div", { class: "grafico" });
    area.appendChild(h("div", { class: "grade-2" },
      cartao("Perda ao longo do tempo", "queda", `% de frutas estragadas por ${unidade} · linha tracejada = limite de ${fmt.pct(limite)}`, gLinha),
      cartao("Volume processado", "caixa", `Frutas por ${unidade}, por estado`, gVol)));
    area.appendChild(h("div", { class: "grade-2" },
      cartao("Perda por fornecedor", "truck", "% de frutas estragadas", gForn),
      cartao("Composição por fornecedor", "layers", "Proporção de frescas, estragadas e incertas", gComp)));
    const porFruta = agrupar(ctx.filtrar("fruta"), (r) => r.fruta_nome).sort((a, b) => b.total - a.total);
    area.appendChild(h("div", { class: "secao" }, cartao("Frutas por tipo", "fruta", "Quantidade processada de cada fruta, por estado", gFruta)));

    const series3 = [{ nome: "Frescas", cor: "--c-fresca" }, { nome: "Estragadas", cor: "--c-estragada" }, { nome: "Incertas", cor: "--c-incerta" }];
    const G = window.Graficos;
    const tempoSel = ctx.marcado("tempo"), fornSel = ctx.marcado("fornecedor"), frutaSel = ctx.marcado("fruta");
    const clicaTempo = { aoClicar: (it, ev) => ctx.alternar("tempo", it.x, ev), aoLimpar: () => ctx.limparDim("tempo"), selecao: (it) => tempoSel(it.x) };
    const clicaForn = { aoClicar: (it, ev) => ctx.alternar("fornecedor", it.rotulo, ev), aoLimpar: () => ctx.limparDim("fornecedor"), selecao: (it) => fornSel(it.rotulo) };
    const clicaFruta = { aoClicar: (it, ev) => ctx.alternar("fruta", it.rotulo, ev), aoLimpar: () => ctx.limparDim("fruta"), selecao: (it) => frutaSel(it.rotulo) };

    G.linha(gLinha, Object.assign({ pontos: grupos.map((g) => ({ x: g.chave, y: g.perda_pct, g })), cor: "--c-estragada", fmtY: fmt.pctEixo,
      limite, rotuloLimite: "Limite " + fmt.pct(limite), tituloDica: (p) => ctx.tituloTempo(p.x),
      dica: (p) => [["perda", fmt.pct(p.y), "--c-estragada"], ["estragadas", fmt.int(p.g.estragadas)], ["frutas", fmt.int(p.g.total)]] }, clicaTempo));
    G.colunasEmpilhadas(gVol, Object.assign({ itens: grupos.map((g) => ({ x: g.chave, titulo: ctx.tituloTempo(g.chave), partes: [g.frescas, g.estragadas, g.incertas] })),
      series: series3, fmt: fmt.int, fmtEixo: fmt.intCurto }, clicaTempo));
    const fornOrd = [...porFornTodos].sort((a, b) => b.perda_pct - a.perda_pct);
    G.barrasH(gForn, Object.assign({ itens: fornOrd.map((f) => ({ rotulo: f.chave, valor: f.perda_pct, f })), fmt: fmt.pct, limite, rotuloLimite: "Limite",
      dica: (it) => [["perda", fmt.pct(it.valor), "--c-estragada"], ["estragadas", fmt.int(it.f.estragadas)], ["frutas", fmt.int(it.f.total)]] }, clicaForn));
    G.empilhadaH(gComp, Object.assign({ itens: fornOrd.map((f) => ({ rotulo: f.chave, partes: [f.frescas, f.estragadas, f.incertas] })), series: series3, normalizar: true, fmt: fmt.int }, clicaForn));
    G.empilhadaH(gFruta, Object.assign({ itens: porFruta.map((f) => ({ rotulo: f.chave, partes: [f.frescas, f.estragadas, f.incertas], f })), series: series3, fmt: fmt.int, fmtEixo: fmt.intCurto,
      dica: (it) => [["frescas", fmt.int(it.partes[0]), "--c-fresca"], ["estragadas", fmt.int(it.partes[1]), "--c-estragada"], ["incertas", fmt.int(it.partes[2]), "--c-incerta"], ["perda", fmt.pct(it.f.perda_pct)]] }, clicaFruta));

    area.appendChild(h("div", { class: "secao" }, cartao("Ranking de fornecedores", "truck", "Ordenado pela taxa de perda · clique em uma linha para filtrar", tabela([
      { titulo: "Fornecedor", valor: (r) => r.chave },
      { titulo: "Frutas", num: true, valor: (r) => fmt.int(r.total) },
      { titulo: "Frescas", num: true, valor: (r) => fmt.int(r.frescas) },
      { titulo: "Estragadas", num: true, valor: (r) => fmt.int(r.estragadas) },
      { titulo: "Incertas", num: true, valor: (r) => fmt.int(r.incertas) },
      { titulo: "Perda", num: true, valor: (r) => fmt.pct(r.perda_pct) },
      { titulo: "Status", valor: (r) => (r.perda_pct > limite && r.total >= 50 ? etiqueta("Acima do limite", "alerta", "alerta") : etiqueta("OK", "ok", "check")) },
    ], fornOrd, { aoClicar: (r, tr, ev) => ctx.alternar("fornecedor", r.chave, ev), classeLinha: (r) => classeSelecao(fornSel(r.chave)) }))));
  }

  function notaComparacao(ctx) {
    const txt = ctx.anterior ? `Variações comparadas ao período anterior de mesmo tamanho (${ctx.dd.dias} dias).`
      : ctx.sel.tempo.length ? "Com um dia/semana selecionado no gráfico, as variações contra o período anterior ficam ocultas." : "";
    return h("p", { class: "sub", style: { color: "var(--texto-3)", fontSize: ".84rem", margin: "8px 0 0" } }, txt);
  }

  // ---------------------------------------------------------- aba FINANCEIRO
  function abaFinanceiro(area, ctx) {
    const tudo = ctx.filtrar(null);
    const t = somar(tudo), ta = ctx.anterior ? somar(ctx.anterior) : null;
    const semPreco = new Map();
    for (const r of tudo) if (!r.preco_unit && r.total > 0) semPreco.set(r.fornecedor + "|" + r.fruta_nome, `${r.fruta_nome} (${r.fornecedor})`);
    if (semPreco.size) area.appendChild(aviso("aviso", "Há frutas sem preço cadastrado, então os valores em R$ estão subestimados: ",
      [...semPreco.values()].join("; "), ". Cadastre em ", h("b", {}, "Fornecedores e preços"), "."));
    area.appendChild(h("div", { class: "kpis" },
      kpi({ rotulo: "Custo de aquisição", valor: t.custo_total, formato: fmt.brl, icone: "carteira", delta: ta && delta(t.custo_total, ta.custo_total, "brl", null) }),
      kpi({ rotulo: "Receita potencial", valor: t.receita_potencial, formato: fmt.brl, icone: "alvo", ajuda: "Se nenhuma fruta estragasse." }),
      kpi({ rotulo: "Receita realizada", valor: t.receita_realizada, formato: fmt.brl, icone: "dinheiro", delta: ta && delta(t.receita_realizada, ta.receita_realizada, "brl", true), ajuda: "Frutas frescas × preço de venda." }),
      kpi({ rotulo: "Receita perdida", valor: t.receita_perdida, formato: fmt.brl, icone: "queda", delta: ta && delta(t.receita_perdida, ta.receita_perdida, "brl", false), ajuda: "Frutas estragadas × preço de venda." })));
    area.appendChild(h("div", { class: "kpis", style: { marginTop: "14px" } },
      kpi({ rotulo: "Custo perdido", valor: t.custo_perdido, formato: fmt.brl, icone: "lixo", delta: ta && delta(t.custo_perdido, ta.custo_perdido, "brl", false), ajuda: "O que foi pago por frutas que estragaram." }),
      kpi({ rotulo: "Lucro bruto realizado", valor: t.lucro_realizado, formato: fmt.brl, icone: "alta", delta: ta && delta(t.lucro_realizado, ta.lucro_realizado, "brl", true), ajuda: "Receita das frescas menos o custo de todas as frutas." }),
      kpi({ rotulo: "Margem realizada", valor: t.margem, formato: fmt.pct, icone: "porcento", delta: ta && delta(t.margem, ta.margem, "pp", true) }),
      kpi({ rotulo: "Receita em revisão", valor: t.receita_em_revisao, formato: fmt.brl, icone: "duvida", ajuda: "Frutas incertas × preço de venda." })));
    area.appendChild(notaComparacao(ctx));

    const grupos = serieTempo(ctx.filtrar("tempo"), ctx);
    const porFruta = agrupar(ctx.filtrar("fruta"), (r) => r.fruta_nome).sort((a, b) => b.receita_perdida - a.receita_perdida);
    const porForn = agrupar(ctx.filtrar("fornecedor"), (r) => r.fornecedor).sort((a, b) => b.receita_perdida - a.receita_perdida);
    const g1 = h("div", { class: "grafico" }), g2 = h("div", { class: "grafico" }), g3 = h("div", { class: "grafico" }), g4 = h("div", { class: "grafico" });
    area.appendChild(h("div", { class: "grade-2" },
      cartao("Receita perdida ao longo do tempo", "queda", `R$ perdidos por ${ctx.semanal ? "semana" : "dia"} com frutas estragadas`, g1),
      cartao("Receita perdida por fruta", "fruta", "Onde está o maior prejuízo", g2)));
    area.appendChild(h("div", { class: "grade-2" },
      cartao("Receita perdida por fornecedor", "truck", "Frutas estragadas × preço de venda", g3),
      cartao("Custo × receita realizada", "carteira", "Por fornecedor; a diferença é o lucro bruto", g4)));
    const G = window.Graficos;
    const tempoSel = ctx.marcado("tempo"), fornSel = ctx.marcado("fornecedor"), frutaSel = ctx.marcado("fruta");
    const clicaTempo = { aoClicar: (it, ev) => ctx.alternar("tempo", it.x, ev), aoLimpar: () => ctx.limparDim("tempo"), selecao: (it) => tempoSel(it.x) };
    const clicaForn = { aoClicar: (it, ev) => ctx.alternar("fornecedor", it.rotulo, ev), aoLimpar: () => ctx.limparDim("fornecedor"), selecao: (it) => fornSel(it.rotulo) };
    const clicaFruta = { aoClicar: (it, ev) => ctx.alternar("fruta", it.rotulo, ev), aoLimpar: () => ctx.limparDim("fruta"), selecao: (it) => frutaSel(it.rotulo) };
    G.linha(g1, Object.assign({ pontos: grupos.map((g) => ({ x: g.chave, y: g.receita_perdida, g })), cor: "--c-estragada", fmtY: fmt.brlEixo,
      tituloDica: (p) => ctx.tituloTempo(p.x),
      dica: (p) => [["receita perdida", fmt.brl(p.y), "--c-estragada"], ["custo perdido", fmt.brl(p.g.custo_perdido)], ["perda", fmt.pct(p.g.perda_pct)]] }, clicaTempo));
    G.barrasV(g2, Object.assign({ itens: porFruta.map((f) => ({ rotulo: f.chave, valor: f.receita_perdida, f })), fmt: fmt.brl, fmtCurto: fmt.brlCurto, fmtEixo: fmt.brlEixo,
      dica: (it) => [["receita perdida", fmt.brl(it.valor), "--c-estragada"], ["custo perdido", fmt.brl(it.f.custo_perdido)], ["perda", fmt.pct(it.f.perda_pct)]] }, clicaFruta));
    G.barrasH(g3, Object.assign({ itens: porForn.map((f) => ({ rotulo: f.chave, valor: f.receita_perdida, f })), fmt: fmt.brlCurto,
      dica: (it) => [["receita perdida", fmt.brl(it.valor), "--c-estragada"], ["custo perdido", fmt.brl(it.f.custo_perdido)], ["perda", fmt.pct(it.f.perda_pct)]] }, clicaForn));
    const porCusto = [...porForn].sort((a, b) => b.custo_total - a.custo_total);
    G.agrupadasH(g4, Object.assign({ itens: porCusto.map((f) => ({ rotulo: f.chave, valores: [f.custo_total, f.receita_realizada], f })),
      series: [{ nome: "Custo de aquisição", cor: "--c-neutra" }, { nome: "Receita realizada", cor: "--c-fresca" }], fmt: fmt.brl, fmtCurto: fmt.brlCurto, fmtEixo: fmt.brlEixo,
      dica: (it) => [["custo", fmt.brl(it.valores[0]), "--c-neutra"], ["receita realizada", fmt.brl(it.valores[1]), "--c-fresca"],
        ["lucro bruto", fmt.brl(it.f.lucro_realizado)], ["margem", fmt.pct(it.f.margem)]] }, clicaForn));

    area.appendChild(h("div", { class: "secao" }, cartao("Ranking financeiro de fornecedores", "dinheiro", "Ordenado pela receita perdida · clique em uma linha para filtrar", tabela([
      { titulo: "Fornecedor", valor: (r) => r.chave },
      { titulo: "Custo de aquisição", num: true, valor: (r) => fmt.brl(r.custo_total) },
      { titulo: "Receita realizada", num: true, valor: (r) => fmt.brl(r.receita_realizada) },
      { titulo: "Receita perdida", num: true, valor: (r) => fmt.brl(r.receita_perdida) },
      { titulo: "Custo perdido", num: true, valor: (r) => fmt.brl(r.custo_perdido) },
      { titulo: "Lucro realizado", num: true, valor: (r) => fmt.brl(r.lucro_realizado) },
      { titulo: "Margem", num: true, valor: (r) => fmt.pct(r.margem) },
    ], porForn, { aoClicar: (r, tr, ev) => ctx.alternar("fornecedor", r.chave, ev), classeLinha: (r) => classeSelecao(fornSel(r.chave)) }))));
    const SEP = "\u0000";
    const cruz = agrupar(tudo, (r) => r.fornecedor + SEP + r.fruta_nome).sort((a, b) => b.receita_perdida - a.receita_perdida);
    area.appendChild(h("div", { class: "secao" }, cartao("Fornecedor × fruta", "layers", "Clique em uma linha para filtrar por aquele fornecedor e fruta", tabela([
      { titulo: "Fornecedor", valor: (r) => r.chave.split(SEP)[0] },
      { titulo: "Fruta", valor: (r) => r.chave.split(SEP)[1] },
      { titulo: "Frutas", num: true, valor: (r) => fmt.int(r.total) },
      { titulo: "Perda", num: true, valor: (r) => fmt.pct(r.perda_pct) },
      { titulo: "Receita perdida", num: true, valor: (r) => fmt.brl(r.receita_perdida) },
      { titulo: "Custo perdido", num: true, valor: (r) => fmt.brl(r.custo_perdido) },
    ], cruz, { rolagem: true, aoClicar: (r) => {
      const [f, fr] = r.chave.split(SEP);
      const ja = ctx.sel.fornecedor.length === 1 && ctx.sel.fornecedor[0] === f && ctx.sel.fruta.length === 1 && ctx.sel.fruta[0] === fr;
      ctx.definir({ fornecedor: ja ? [] : [f], fruta: ja ? [] : [fr] });
    } }))));
  }

  function baixarCSV() {
    const linhas = estado.dash.ultimas || [];
    if (!linhas.length) { toast("Não há dados no filtro atual.", "erro"); return; }
    const cols = ["data", "lote_id", "fornecedor", "fruta", "frescas", "estragadas", "incertas", "custo_unit", "preco_unit", "custo_total",
      "receita_potencial", "receita_realizada", "receita_perdida", "custo_perdido", "lucro_realizado", "origem", "referencia"];
    const cel = (v) => {
      if (typeof v === "number") return String(Math.round(v * 100) / 100).replace(".", ",");
      const s = String(v == null ? "" : v);
      const seguro = /^[=+\-@]/.test(s) ? "'" + s : s;                         // evita fórmulas no Excel
      return /[;"\n]/.test(seguro) ? '"' + seguro.replace(/"/g, '""') + '"' : seguro;
    };
    const txt = [cols.join(";")].concat(linhas.map((r) => cols.map((c) => cel(r[c])).join(";"))).join("\r\n");
    const [a, b] = intervaloDashboard();
    const link = h("a", { href: URL.createObjectURL(new Blob(["﻿" + txt], { type: "text/csv;charset=utf-8" })), download: `contagens_${a}_${b}.csv` });
    document.body.appendChild(link); link.click(); link.remove();
  }

  // =========================================================== EXECUTAR ESTEIRA
  async function paginaEsteira(cont) {
    cont.appendChild(topo("Executar esteira", "A janela de vídeo abre neste computador. Ao terminar, a contagem é gravada para o fornecedor escolhido."));
    const forn = estado.meta.fornecedores.filter((f) => f.ativo);
    if (!forn.length) { cont.appendChild(aviso("info", "Cadastre ao menos um fornecedor ativo (menu Fornecedores e preços) antes de rodar a esteira.")); return; }
    let info = await api("GET", "/api/esteira/estado");
    if (info.faltando.length) {
      cont.appendChild(aviso("erro", "Faltam arquivos na pasta do programa: " + info.faltando.join(", ") + ". Rode o treino_multiclasse.py antes."));
      return;
    }
    const ui = estado.esteiraUI || (estado.esteiraUI = { origem: "video", video: null });
    const selForn = selecao(forn.map((f) => [f.id, f.nome]), ui.fornecedor || forn[0].id);
    const ref = entrada("text", { placeholder: "Nota fiscal, nº da carga…", value: ui.referencia || "" });
    selForn.addEventListener("change", () => (ui.fornecedor = selForn.value));
    ref.addEventListener("input", () => (ui.referencia = ref.value));

    const bVideo = h("button", { type: "button" }, icone("filme"), "Vídeo");
    const bCam = h("button", { type: "button" }, icone("camera"), "Câmera (webcam)");
    const seg = h("div", { class: "segmentado", role: "tablist" }, bVideo, bCam);
    const areaOrigem = h("div", {});
    const selVideo = h("select", {});
    const caminho = entrada("text", { placeholder: "C:\\videos\\esteira.mp4" });
    const tempoReal = h("input", { type: "checkbox" });
    const camera = entrada("number", { min: 0, max: 10, step: 1, value: 0, style: { maxWidth: "140px" } });
    const progresso = h("div", { class: "barra-progresso", style: { display: "none" } }, h("div", {}));
    const arquivo = h("input", { type: "file", accept: ".mp4,.avi,.mov,.mkv,.wmv", style: { display: "none" } });
    const zona = h("div", { class: "zona-envio", tabindex: 0, role: "button" }, icone("upload", "grande"), h("div", {}, "Clique ou arraste um vídeo aqui para enviá-lo à pasta videos/"));

    function preencherVideos(videos, escolher) {
      selVideo.replaceChildren(...videos.map((v) => h("option", { value: v.caminho }, v.nome)), h("option", { value: "__outro" }, "Outro caminho…"));
      selVideo.value = escolher && videos.some((v) => v.caminho === escolher) ? escolher : (videos[0] ? videos[0].caminho : "__outro");
      caminho.parentElement && (caminho.parentElement.style.display = selVideo.value === "__outro" ? "flex" : "none");
    }
    const campoCaminho = campo("Caminho completo do vídeo", caminho);
    selVideo.addEventListener("change", () => { campoCaminho.style.display = selVideo.value === "__outro" ? "flex" : "none"; ui.video = selVideo.value; });
    function desenharOrigem() {
      bVideo.classList.toggle("ativo", ui.origem === "video");
      bCam.classList.toggle("ativo", ui.origem === "camera");
      areaOrigem.replaceChildren();
      if (ui.origem === "video") {
        areaOrigem.append(h("div", { class: "linha-form" }, campo("Vídeo", selVideo, "Vídeos da pasta do programa e da subpasta videos/."), campoCaminho),
          h("label", { class: "caixa-check", style: { marginBottom: "14px" } }, tempoReal, "Simular o ritmo real do vídeo (descarta quadros se o computador atrasar)"),
          zona, progresso, arquivo);
        campoCaminho.style.display = selVideo.value === "__outro" ? "flex" : "none";
      } else {
        areaOrigem.append(campo("Número da câmera", camera, "0 = webcam padrão. Se houver mais de uma câmera, tente 1, 2…"));
      }
    }
    bVideo.addEventListener("click", () => { ui.origem = "video"; desenharOrigem(); });
    bCam.addEventListener("click", () => { ui.origem = "camera"; desenharOrigem(); });
    preencherVideos(info.videos, ui.video);
    desenharOrigem();

    function enviar(file) {
      if (!file) return;
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/esteira/upload");
      xhr.setRequestHeader("X-Frutas", "1");
      xhr.setRequestHeader("X-Nome-Arquivo", encodeURIComponent(file.name));
      progresso.style.display = "block";
      xhr.upload.onprogress = (e) => { if (e.lengthComputable) progresso.firstChild.style.width = (e.loaded / e.total) * 100 + "%"; };
      xhr.onload = async () => {
        progresso.style.display = "none"; progresso.firstChild.style.width = "0";
        let r = {}; try { r = JSON.parse(xhr.responseText); } catch (e) { /* vazio */ }
        if (xhr.status !== 200) return toast(r.erro || "Falha no envio.", "erro");
        toast("Vídeo salvo: " + r.nome);
        const novo = await api("GET", "/api/esteira/estado");
        ui.video = r.caminho;
        preencherVideos(novo.videos, r.caminho);
      };
      xhr.onerror = () => { progresso.style.display = "none"; toast("Falha no envio.", "erro"); };
      xhr.send(file);
    }
    zona.addEventListener("click", () => arquivo.click());
    zona.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); arquivo.click(); } });
    arquivo.addEventListener("change", () => enviar(arquivo.files[0]));
    zona.addEventListener("dragover", (e) => { e.preventDefault(); zona.classList.add("arrastando"); });
    zona.addEventListener("dragleave", () => zona.classList.remove("arrastando"));
    zona.addEventListener("drop", (e) => { e.preventDefault(); zona.classList.remove("arrastando"); enviar(e.dataTransfer.files[0]); });

    const bIniciar = botao("Iniciar esteira", { tipo: "primario", icone: "play", acao: async () => {
      const corpo = { fornecedor_id: +selForn.value, referencia: ref.value, origem: ui.origem, camera: +camera.value || 0, tempo_real: tempoReal.checked,
        video: selVideo.value === "__outro" ? caminho.value.trim().replace(/^"|"$/g, "") : selVideo.value };
      await api("POST", "/api/esteira/iniciar", corpo);
      toast("Esteira iniciada. A janela do vídeo vai abrir em instantes.");
      await atualizar();
    } });
    const formulario = cartao("Configuração", "ajustes", null,
      h("div", { class: "linha-form" }, campo("Fornecedor", selForn), campo("Referência (opcional)", ref)),
      h("div", { class: "campo", style: { marginBottom: "14px" } }, h("span", { class: "rotulo-campo" }, "Origem das imagens"), seg),
      areaOrigem, h("div", { class: "acoes", style: { marginTop: "16px" } }, bIniciar));
    const status = h("section", { class: "cartao entrar cartao-simples" });
    cont.append(formulario, status);

    let pedidoEm = 0;
    function travar(rodando) {
      formulario.querySelectorAll("input, select, .segmentado button").forEach((el) => (el.disabled = rodando));
      zona.style.pointerEvents = rodando ? "none" : ""; zona.style.opacity = rodando ? 0.5 : "";
      bIniciar.disabled = rodando;
    }
    function desenharStatus() {
      const s = info;
      status.replaceChildren();
      travar(s.rodando);
      if (s.rodando) {
        const seg = Math.round(s.segundos);
        status.append(h("div", { class: "status-esteira" }, h("span", { class: "pulso" }),
          h("div", {}, h("h3", {}, "Esteira em execução"), h("p", { class: "sub", style: { margin: 0 } },
            `Rodando há ${Math.floor(seg / 60)} min ${seg % 60} s. Para encerrar, use o botão abaixo ou aperte q na janela do vídeo.`))));
        const acoes = h("div", { class: "acoes", style: { marginTop: "14px" } },
          botao("Encerrar e gravar contagem", { tipo: "primario", icone: "parar", acao: async () => { await api("POST", "/api/esteira/parar"); pedidoEm = Date.now(); await atualizar(); } }));
        if (s.segundos_parada > 0) {
          acoes.appendChild(h("span", { class: "sub", style: { color: "var(--texto-2)" } }, "Encerrando e gravando a contagem…"));
          if (s.segundos_parada > 15) acoes.appendChild(botao("Forçar parada", { tipo: "perigo", icone: "x", acao: async () => {
            if (!(await confirmar("Forçar parada?", "A esteira será interrompida na hora e a contagem desta execução NÃO será gravada.", "Forçar parada", true))) return;
            await api("POST", "/api/esteira/forcar"); toast("Esteira interrompida. A contagem não foi gravada.", "erro"); await atualizar();
          } }));
        }
        status.appendChild(acoes);
      } else {
        status.appendChild(h("h3", {}, icone("relogio"), "Última execução"));
        const r = s.resultado;
        if (!r) status.appendChild(h("p", { class: "sub" }, "Nenhuma execução desde que o servidor foi aberto."));
        else if (r.lote) status.appendChild(aviso("ok", `Contagem gravada no lote #${r.lote}. `, h("a", { href: "#/dashboard" }, "Ver no Dashboard"), "."));
        else if (r.codigo !== 0 && r.codigo != null) status.appendChild(aviso("erro", "A esteira terminou com erro. Veja o registro abaixo."));
        else status.appendChild(aviso("aviso", "A esteira terminou sem gravar contagem" + (r.erro_banco ? ": " + r.erro_banco : ".")));
        if (r && r.resumo) status.appendChild(h("pre", { class: "registro", style: { marginBottom: "12px" } }, r.resumo));
      }
      if (s.log) {
        const det = h("details", { open: s.rodando || null, style: { marginTop: "12px" } }, h("summary", { style: { cursor: "pointer", color: "var(--texto-2)" } }, "Registro da esteira"),
          h("pre", { class: "registro", style: { marginTop: "8px" } }, s.log));
        status.appendChild(det);
        const pre = det.querySelector("pre"); pre.scrollTop = pre.scrollHeight;
      }
    }
    let rodavaAntes = info.rodando;
    async function atualizar() {
      info = await api("GET", "/api/esteira/estado");
      if (rodavaAntes && !info.rodando && info.resultado && info.resultado.lote) toast(`Contagem gravada no lote #${info.resultado.lote}.`);
      rodavaAntes = info.rodando;
      desenharStatus();
    }
    desenharStatus();
    const r = estado.rodada;
    intervalo(() => { if (r === estado.rodada && document.visibilityState === "visible") atualizar().catch(() => {}); }, 2000);
  }

  // ========================================================== REGISTRAR CONTAGEM
  async function paginaRegistrar(cont) {
    cont.appendChild(topo("Registrar contagem", "Lançamento manual. Contagens da esteira entram sozinhas e aparecem na lista abaixo."));
    const forn = estado.meta.fornecedores.filter((f) => f.ativo);
    const recentes = h("div", {});
    if (!forn.length) {
      cont.appendChild(aviso("info", "Cadastre ao menos um fornecedor (menu Fornecedores e preços) antes de registrar contagens."));
    } else {
      const selForn = selecao(forn.map((f) => [f.id, f.nome]), forn[0].id);
      const data = entrada("date", { value: hojeISO(), max: hojeISO() });
      const ref = entrada("text", { placeholder: "Nota fiscal, nº da carga…" });
      const corpoTabela = h("div", {});
      const resumo = h("div", { style: { margin: "12px 0", color: "var(--texto-2)" } });
      const avisoPreco = h("div", {});
      let itens = [];
      const bSalvar = botao("Salvar contagem", { tipo: "primario", icone: "salvar", desabilitado: true, acao: async () => {
        const contagens = {};
        for (const it of itens) { const v = it.inputs.map((i) => Math.max(0, parseInt(i.value || "0", 10) || 0)); if (v.some((x) => x > 0)) contagens[it.fruta] = v; }
        const r = await api("POST", "/api/contagens", { fornecedor_id: +selForn.value, data: data.value, referencia: ref.value, contagens });
        toast(`Lote #${r.lote} salvo.`);
        itens.forEach((it) => it.inputs.forEach((i) => (i.value = 0)));
        ref.value = "";
        recalcular();
        carregarRecentes(r.lote);
      } });
      function recalcular() {
        let tot = 0, est = 0, perda = 0; const semPreco = [];
        for (const it of itens) {
          const [f, e, i] = it.inputs.map((x) => Math.max(0, parseInt(x.value || "0", 10) || 0));
          if (f + e + i > 0) { tot += f + e + i; est += e; perda += e * it.preco; if (!it.cadastrado) semPreco.push(it.nome); }
        }
        bSalvar.disabled = tot === 0;
        resumo.replaceChildren(tot ? h("span", {}, h("b", {}, fmt.int(tot)), " frutas · perda ", h("b", {}, fmt.pct(est / tot)), " · receita perdida ", h("b", {}, fmt.brl(perda))) : "Preencha as quantidades das frutas recebidas.");
        avisoPreco.replaceChildren(semPreco.length ? aviso("aviso", "Sem preço cadastrado para este fornecedor: " + semPreco.join(", ") + ". A contagem será salva, mas os valores em R$ ficarão zerados.") : "");
      }
      async function carregarPrecos() {
        const precos = await api("GET", "/api/precos?fornecedor=" + selForn.value);
        itens = precos.map((p) => ({ fruta: p.fruta, nome: p.fruta_nome, preco: p.preco_unit, cadastrado: p.cadastrado,
          inputs: [0, 1, 2].map(() => { const i = entrada("number", { min: 0, step: 1, value: 0 }); i.addEventListener("input", recalcular); i.addEventListener("focus", () => i.select()); return i; }) }));
        corpoTabela.replaceChildren(tabela([
          { titulo: "Fruta", valor: (it) => it.nome },
          { titulo: "Frescas", num: true, valor: (it) => it.inputs[0] },
          { titulo: "Estragadas", num: true, valor: (it) => it.inputs[1] },
          { titulo: "Incertas", num: true, valor: (it) => it.inputs[2] },
          { titulo: "Preço de venda", num: true, valor: (it) => (it.cadastrado ? fmt.brl(it.preco) : etiqueta("sem preço", "neutra")) },
        ], itens));
        recalcular();
      }
      selForn.addEventListener("change", carregarPrecos);
      cont.appendChild(cartao("Nova contagem", "plus", null,
        h("div", { class: "linha-form" }, campo("Fornecedor", selForn), campo("Data", data), campo("Referência (opcional)", ref)),
        corpoTabela, resumo, avisoPreco, h("div", { class: "acoes" }, bSalvar)));
      await carregarPrecos();
    }

    // ---- lotes recentes (manual + esteira), atualiza sozinho
    let selecionado = null;
    const detalhe = h("div", { style: { marginTop: "14px" } });
    async function mostrarDetalhe(id) {
      selecionado = id;
      const det = await api("GET", "/api/lotes/detalhe?id=" + id);
      detalhe.replaceChildren(h("h3", { style: { margin: "6px 0 10px" } }, `Lote #${id} por fruta`), tabela([
        { titulo: "Fruta", valor: (d) => d.fruta_nome },
        { titulo: "Frescas", num: true, valor: (d) => fmt.int(d.frescas) },
        { titulo: "Estragadas", num: true, valor: (d) => fmt.int(d.estragadas) },
        { titulo: "Incertas", num: true, valor: (d) => fmt.int(d.incertas) },
      ], det));
    }
    let assinatura = "";
    async function carregarRecentes(destacar) {
      const lotes = await api("GET", "/api/lotes/recentes?n=15");
      const nova = JSON.stringify(lotes);
      if (nova === assinatura && !destacar) return;                         // nada mudou: não redesenha
      assinatura = nova;
      const origemTag = (o) => (o === "esteira" ? etiqueta("Esteira", "esteira", "play") : o === "manual" ? etiqueta("Manual", "neutra", "lapis") : etiqueta("Exemplo", "neutra", "brilho"));
      recentes.replaceChildren(tabela([
        { titulo: "Lote", valor: (l) => "#" + l.lote_id },
        { titulo: "Registrado em", valor: (l) => fmt.dataHora(l.criado_em) },
        { titulo: "Fornecedor", valor: (l) => l.fornecedor },
        { titulo: "Origem", valor: (l) => origemTag(l.origem) },
        { titulo: "Referência", valor: (l) => l.referencia || "—" },
        { titulo: "Frutas", num: true, valor: (l) => fmt.int(l.frescas + l.estragadas + l.incertas) },
        { titulo: "Estragadas", num: true, valor: (l) => fmt.int(l.estragadas) },
        { titulo: "Perda", num: true, valor: (l) => fmt.pct(l.estragadas / Math.max(1, l.frescas + l.estragadas + l.incertas)) },
      ], lotes, { vazio: "Nenhuma contagem registrada ainda.", aoClicar: (l, tr) => {
        recentes.querySelectorAll("tr.selecionada").forEach((x) => x.classList.remove("selecionada"));
        tr.classList.add("selecionada"); mostrarDetalhe(l.lote_id);
      }, classeLinha: (l) => (l.lote_id === (destacar || selecionado) ? "selecionada" : "") }));
      if (destacar) mostrarDetalhe(destacar);
    }
    cont.appendChild(cartao("Contagens registradas recentemente", "relogio", "Atualiza sozinha a cada 5 segundos. Clique em um lote para ver o detalhe por fruta.", recentes, detalhe));
    await carregarRecentes();
    const r = estado.rodada;
    intervalo(() => { if (r === estado.rodada && document.visibilityState === "visible") carregarRecentes().catch(() => {}); }, 5000);
  }

  // ============================================================ LOTES E REVISÃO
  async function paginaLotes(cont) {
    cont.appendChild(topo("Lotes e revisão", "Histórico de contagens, revisão das frutas incertas e exclusão de lotes"));
    const ini = entrada("date", { value: somarDias(hojeISO(), -29), max: hojeISO() });
    const fim = entrada("date", { value: hojeISO(), max: hojeISO() });
    const area = h("div", {});
    cont.append(h("div", { class: "filtros" }, campo("De", ini), campo("Até", fim)), area);
    async function carregar() {
      const linhas = await api("GET", `/api/linhas?ini=${ini.value}&fim=${fim.value}`);
      area.replaceChildren();
      if (!linhas.length) { area.appendChild(aviso("info", "Nenhuma contagem no período.")); return; }
      const lotes = agrupar(linhas, (r) => r.lote_id).map((g) => { const l = linhas.find((x) => x.lote_id === g.chave); return Object.assign(g, { data: l.data, fornecedor: l.fornecedor, origem: l.origem, referencia: l.referencia }); })
        .sort((a, b) => b.chave - a.chave);
      area.appendChild(cartao("Lotes do período", "layers", null, tabela([
        { titulo: "Lote", valor: (l) => "#" + l.chave },
        { titulo: "Data", valor: (l) => fmt.data(l.data) },
        { titulo: "Fornecedor", valor: (l) => l.fornecedor },
        { titulo: "Origem", valor: (l) => l.origem },
        { titulo: "Referência", valor: (l) => l.referencia || "—" },
        { titulo: "Frutas", num: true, valor: (l) => fmt.int(l.total) },
        { titulo: "Estragadas", num: true, valor: (l) => fmt.int(l.estragadas) },
        { titulo: "Incertas", num: true, valor: (l) => fmt.int(l.incertas) },
        { titulo: "Perda", num: true, valor: (l) => fmt.pct(l.perda_pct) },
        { titulo: "Receita perdida", num: true, valor: (l) => fmt.brl(l.receita_perdida) },
      ], lotes, { rolagem: true })));

      if (podeOperar()) {
        const inc = linhas.filter((r) => r.incertas > 0).sort((a, b) => b.lote_id - a.lote_id);
        if (!inc.length) area.appendChild(cartao("Revisar frutas incertas", "duvida", "Nenhuma contagem com frutas incertas no período."));
        else {
          const sel = selecao(inc.map((r) => [r.contagem_id, `Lote ${r.lote_id} · ${fmt.data(r.data)} · ${r.fornecedor} · ${r.fruta_nome} · ${r.incertas} incertas`]));
          const fr = entrada("number", { min: 0, step: 1, value: 0 }), es = entrada("number", { min: 0, step: 1, value: 0 });
          const ajustarMax = () => { const m = inc.find((r) => r.contagem_id === +sel.value).incertas; fr.max = m; es.max = m; };
          sel.addEventListener("change", ajustarMax); ajustarMax();
          area.appendChild(cartao("Revisar frutas incertas", "duvida", "Informe quantas das frutas incertas eram, na verdade, frescas ou estragadas.",
            h("div", { class: "linha-form" }, campo("Contagem", sel), campo("Eram frescas", fr), campo("Eram estragadas", es)),
            h("div", { class: "acoes" }, botao("Aplicar revisão", { tipo: "primario", icone: "check", acao: async () => {
              await api("POST", "/api/incertas", { contagem_id: +sel.value, frescas: +fr.value || 0, estragadas: +es.value || 0 });
              toast("Revisão aplicada."); await carregar();
            } }))));
        }
      }
      if (ehAdmin()) {
        const sel = selecao(lotes.map((l) => [l.chave, `#${l.chave} · ${fmt.data(l.data)} · ${l.fornecedor} · ${fmt.int(l.total)} frutas`]));
        area.appendChild(cartao("Excluir lote", "lixo", "A exclusão é definitiva e some do dashboard.",
          h("div", { class: "linha-form" }, campo("Lote", sel)),
          h("div", { class: "acoes" }, botao("Excluir lote", { tipo: "perigo", icone: "lixo", acao: async () => {
            if (!(await confirmar("Excluir lote?", `O lote #${sel.value} e todas as contagens dele serão apagados definitivamente.`, "Excluir", true))) return;
            await api("POST", "/api/lotes/excluir", { lote_id: +sel.value }); toast("Lote excluído."); await carregar();
          } }))));
      }
    }
    ini.addEventListener("change", carregar);
    fim.addEventListener("change", carregar);
    await carregar();
  }

  // ======================================================= FORNECEDORES E PREÇOS
  async function paginaFornecedores(cont, sub) {
    cont.appendChild(topo("Fornecedores e preços", "Cadastro de fornecedores, preços por fruta e configurações gerais"));
    const abas = [["fornecedores", "truck", "Fornecedores"], ["precos", "etiqueta", "Preços por fornecedor"], ["config", "ajustes", "Configurações"]];
    let atual = abas.some((a) => a[0] === sub) ? sub : "fornecedores";
    const barra = h("div", { class: "abas", role: "tablist" });
    const area = h("div", {});
    const botoes = abas.map(([id, ic, nome]) => {
      const b = h("button", { type: "button", class: "aba", role: "tab" }, icone(ic), nome);
      b.addEventListener("click", () => { atual = id; history.replaceState(null, "", "#/fornecedores/" + id); desenhar(); });
      barra.appendChild(b);
      return [id, b];
    });
    cont.append(barra, area);
    async function desenhar() {
      botoes.forEach(([id, b]) => b.classList.toggle("ativa", id === atual));
      area.replaceChildren();
      if (atual === "fornecedores") await abaCadastro(area);
      else if (atual === "precos") await abaPrecos(area);
      else abaConfig(area);
    }
    await desenhar();
  }

  async function abaCadastro(area) {
    const lista = await api("GET", "/api/fornecedores");
    let editando = null;
    const nome = entrada("text"), cnpj = entrada("text"), contato = entrada("text");
    const ativo = h("input", { type: "checkbox", checked: true });
    const tituloForm = h("h3", {}, icone("plus"), "Novo fornecedor");
    const bCancelar = botao("Cancelar edição", { tipo: "fantasma", icone: "x", acao: () => preencher(null) });
    function preencher(f) {
      editando = f;
      nome.value = f ? f.nome : ""; cnpj.value = f ? f.cnpj : ""; contato.value = f ? f.contato : ""; ativo.checked = f ? !!f.ativo : true;
      tituloForm.replaceChildren(icone(f ? "lapis" : "plus"), f ? `Editar: ${f.nome}` : "Novo fornecedor");
      bCancelar.style.display = f ? "" : "none";
      if (f) nome.focus();
    }
    area.appendChild(cartao("Fornecedores cadastrados", "truck", null, tabela([
      { titulo: "ID", valor: (f) => f.id },
      { titulo: "Nome", valor: (f) => f.nome },
      { titulo: "CNPJ", valor: (f) => f.cnpj || "—" },
      { titulo: "Contato", valor: (f) => f.contato || "—" },
      { titulo: "Status", valor: (f) => (f.ativo ? etiqueta("Ativo", "ok", "check") : etiqueta("Inativo", "neutra")) },
      { titulo: "", valor: (f) => botao("Editar", { pequeno: true, icone: "lapis", acao: async () => preencher(f) }) },
    ], lista, { vazio: "Nenhum fornecedor cadastrado." })));
    const form = h("form", {}, tituloForm,
      h("div", { class: "linha-form", style: { marginTop: "12px" } }, campo("Nome", nome), campo("CNPJ", cnpj), campo("Contato (telefone / e-mail)", contato)),
      h("label", { class: "caixa-check" }, ativo, "Ativo"),
      h("div", { class: "acoes", style: { marginTop: "14px" } }, botao("Salvar fornecedor", { tipo: "primario", icone: "salvar", submit: true }), bCancelar));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("POST", "/api/fornecedores", { id: editando ? editando.id : null, nome: nome.value, cnpj: cnpj.value, contato: contato.value, ativo: ativo.checked });
        toast("Fornecedor salvo."); await carregarMeta(); area.replaceChildren(); await abaCadastro(area);
      } catch (err) { toast(err.message, "erro"); }
    });
    area.appendChild(h("section", { class: "cartao vivo entrar" }, form));
    preencher(null);
  }

  async function abaPrecos(area) {
    const forn = estado.meta.fornecedores;
    if (!forn.length) { area.appendChild(aviso("info", "Cadastre um fornecedor primeiro.")); return; }
    const sel = selecao(forn.map((f) => [f.id, f.nome]), estado.precoForn || forn[0].id);
    const corpo = h("div", {});
    let itens = [];
    async function carregar() {
      estado.precoForn = sel.value;
      const precos = await api("GET", "/api/precos?fornecedor=" + sel.value);
      itens = precos.map((p) => ({ fruta: p.fruta, nome: p.fruta_nome,
        custo: entrada("number", { min: 0, step: 0.05, value: (+p.custo_unit).toFixed(2) }),
        preco: entrada("number", { min: 0, step: 0.05, value: (+p.preco_unit).toFixed(2) }) }));
      corpo.replaceChildren(tabela([
        { titulo: "Fruta", valor: (i) => i.nome },
        { titulo: "Custo de compra (R$/un)", num: true, valor: (i) => i.custo },
        { titulo: "Preço de venda (R$/un)", num: true, valor: (i) => i.preco },
      ], itens));
    }
    sel.addEventListener("change", carregar);
    area.appendChild(cartao("Preços por fornecedor", "etiqueta", "Os preços valem para as próximas contagens. O histórico guarda o preço da época do registro. Deixe 0 e 0 para remover.",
      h("div", { class: "linha-form" }, campo("Fornecedor", sel)), corpo,
      h("div", { class: "acoes", style: { marginTop: "14px" } }, botao("Salvar preços", { tipo: "primario", icone: "salvar", acao: async () => {
        await api("POST", "/api/precos", { fornecedor_id: +sel.value, itens: itens.map((i) => ({ fruta: i.fruta, custo_unit: +i.custo.value || 0, preco_unit: +i.preco.value || 0 })) });
        toast("Preços salvos.");
      } }))));
    await carregar();
  }

  function abaConfig(area) {
    const limite = entrada("number", { min: 0, max: 100, step: 0.5, value: estado.meta.limite_perda });
    area.appendChild(cartao("Configurações", "ajustes", "Nome, logo e descrição da empresa ficam em Dados da empresa.",
      h("div", { class: "linha-form" }, campo("Limite de perda aceitável (%)", limite, "Fornecedores acima deste valor aparecem em alerta no dashboard.")),
      h("div", { class: "acoes" }, botao("Salvar configurações", { tipo: "primario", icone: "salvar", acao: async () => {
        await api("POST", "/api/config", { limite_perda: +limite.value });
        await carregarMeta(); toast("Configurações salvas.");
      } }))));
    area.appendChild(cartao("Dados de exemplo", "brilho", "Cria três fornecedores fictícios com 90 dias de contagens (origem = exemplo), para conhecer o dashboard.",
      botao("Gerar dados de exemplo", { icone: "brilho", acao: async () => {
        if (!(await confirmar("Gerar dados de exemplo?", "Serão criados fornecedores e lotes fictícios. Depois você pode excluí-los em Lotes e revisão.", "Gerar"))) return;
        const r = await api("POST", "/api/exemplo"); await carregarMeta(); toast(`${r.lotes} lotes de exemplo criados.`);
      } })));
  }


  // ============================================================ DADOS DA EMPRESA
  async function paginaEmpresa(cont) {
    cont.appendChild(topo("Dados da empresa", "Identidade da indústria: aparece no login, no menu, na aba do navegador e nos relatórios"));
    let dados = await api("GET", "/api/empresa");
    const campos = {
      nome: entrada("text", { value: dados.nome, maxlength: 120, required: true }),
      slogan: entrada("text", { value: dados.slogan, maxlength: 140, placeholder: "Ex.: Qualidade do campo à mesa" }),
      descricao: h("textarea", { maxlength: 1200, placeholder: "Quem é a empresa, o que processa, onde atua…" }),
      cnpj: entrada("text", { value: dados.cnpj, maxlength: 30, placeholder: "00.000.000/0000-00" }),
      telefone: entrada("text", { value: dados.telefone, maxlength: 40 }),
      email: entrada("text", { value: dados.email, maxlength: 120, placeholder: "contato@empresa.com.br" }),
      site: entrada("text", { value: dados.site, maxlength: 200, placeholder: "www.empresa.com.br" }),
      endereco: entrada("text", { value: dados.endereco, maxlength: 300 }),
    };
    campos.descricao.value = dados.descricao || "";
    const contador = h("span", { class: "dica-campo" });

    // ---- prévia ao vivo (como fica no menu e no login)
    const pNome = h("b", {}), pSlogan = h("div", { class: "sub", style: { fontSize: ".8rem", color: "var(--texto-2)" } });
    const pDesc = h("p", { class: "descricao", style: { margin: "6px 0 0" } });
    const pLogo = h("div", { class: "logo" }), pLogoGrande = h("div", { class: "logo" });
    function pintarPrevia() {
      const url = dados.logo_url;
      for (const el of [pLogo, pLogoGrande]) {
        el.classList.toggle("com-imagem", !!url);
        el.replaceChildren(url ? h("img", { src: url, alt: "Logo" }) : icone("fruta"));
      }
      pNome.textContent = campos.nome.value || "Nome da empresa";
      pSlogan.textContent = campos.slogan.value || "Qualidade de frutas";
      pDesc.textContent = campos.descricao.value || "A descrição aparece na tela de login.";
      contador.textContent = campos.descricao.value.length + " / 1200";
      bRemover.style.display = url ? "" : "none";
    }
    Object.values(campos).forEach((c) => c.addEventListener("input", pintarPrevia));

    // ---- logo
    const arquivo = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp", style: { display: "none" } });
    const progresso = h("div", { class: "barra-progresso", style: { display: "none" } }, h("div", {}));
    const zona = h("div", { class: "zona-envio", tabindex: 0, role: "button", style: { flex: "1", minWidth: "220px" } },
      icone("imagem", "grande"), h("div", {}, "Clique ou arraste a imagem da logo"), h("div", { class: "dica-campo" }, "PNG, JPG ou WEBP · até 3 MB · de preferência quadrada"));
    async function enviarLogo(file) {
      if (!file) return;
      if (file.size > 3 * 1024 * 1024) return toast("Imagem grande demais (limite de 3 MB).", "erro");
      progresso.style.display = "block"; progresso.firstChild.style.width = "35%";
      try {
        const r = await fetch("/api/empresa/logo", { method: "POST", credentials: "same-origin", headers: { "X-Frutas": "1", "Content-Type": file.type || "application/octet-stream" }, body: file });
        progresso.firstChild.style.width = "100%";
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.erro || "Falha no envio da logo.");
        dados = j;
        aplicarMarca({ nome: j.nome, slogan: j.slogan, descricao: j.descricao, logo_url: j.logo_url });
        pintarPrevia();
        toast("Logo atualizada em todo o sistema.");
      } catch (e) { toast(e.message, "erro"); }
      finally { setTimeout(() => { progresso.style.display = "none"; progresso.firstChild.style.width = "0"; }, 400); arquivo.value = ""; }
    }
    zona.addEventListener("click", () => arquivo.click());
    zona.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); arquivo.click(); } });
    zona.addEventListener("dragover", (e) => { e.preventDefault(); zona.classList.add("arrastando"); });
    zona.addEventListener("dragleave", () => zona.classList.remove("arrastando"));
    zona.addEventListener("drop", (e) => { e.preventDefault(); zona.classList.remove("arrastando"); enviarLogo(e.dataTransfer.files[0]); });
    arquivo.addEventListener("change", () => enviarLogo(arquivo.files[0]));
    const bRemover = botao("Remover logo", { tipo: "perigo", icone: "lixo", acao: async () => {
      if (!(await confirmar("Remover a logo?", "O sistema volta a usar o ícone padrão em todos os lugares.", "Remover", true))) return;
      dados = await api("POST", "/api/empresa/logo/remover");
      aplicarMarca({ nome: dados.nome, slogan: dados.slogan, descricao: dados.descricao, logo_url: dados.logo_url });
      pintarPrevia(); toast("Logo removida.");
    } });

    const form = h("form", {},
      h("div", { class: "linha-form" }, campo("Nome da empresa", campos.nome), campo("Slogan (frase curta)", campos.slogan, "Aparece abaixo do nome, no menu e no login.")),
      h("div", { class: "campo", style: { marginBottom: "14px" } }, h("label", {}, "Descrição"), campos.descricao, contador),
      h("div", { class: "linha-form" }, campo("CNPJ", campos.cnpj), campo("Telefone", campos.telefone), campo("E-mail", campos.email), campo("Site", campos.site)),
      h("div", { class: "linha-form" }, campo("Endereço", campos.endereco)),
      h("div", { class: "acoes" }, botao("Salvar dados da empresa", { tipo: "primario", icone: "salvar", submit: true })));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const b = form.querySelector("button[type=submit]");
      b.classList.add("carregando");
      try {
        dados = await api("POST", "/api/empresa", Object.fromEntries(Object.entries(campos).map(([k, v]) => [k, v.value])));
        aplicarMarca({ nome: dados.nome, slogan: dados.slogan, descricao: dados.descricao, logo_url: dados.logo_url });
        if (estado.meta) estado.meta.empresa = dados.nome;
        toast("Dados da empresa salvos.");
      } catch (err) { toast(err.message, "erro"); }
      finally { b.classList.remove("carregando"); }
    });

    cont.append(
      cartao("Logo", "imagem", "A imagem é trocada no menu, na tela de login, na barra do celular e no ícone da aba do navegador.",
        h("div", { class: "previa-logo" }, pLogoGrande, zona), progresso, arquivo, h("div", { class: "acoes", style: { marginTop: "12px" } }, bRemover)),
      h("div", { class: "grade-2" },
        cartao("Informações", "predio", null, form),
        cartao("Prévia", "olho", "Como a marca aparece no menu e no login.",
          h("div", { class: "previa-marca" }, pLogo, h("div", {}, pNome, pSlogan)), pDesc)));
    pLogoGrande.style.cssText = "width:96px;height:96px;border-radius:22px";
    pintarPrevia();
  }

  // ==================================================================== USUÁRIOS
  async function paginaUsuarios(cont) {
    cont.appendChild(topo("Usuários", "admin: tudo · operador: registra contagens, roda a esteira e revisa · visualizador: só consulta"));
    const area = h("div", {});
    cont.appendChild(area);
    async function carregar() {
      const us = await api("GET", "/api/usuarios");
      area.replaceChildren(cartao("Contas", "users", null, tabela([
        { titulo: "Login", valor: (u) => u.login },
        { titulo: "Nome", valor: (u) => u.nome },
        { titulo: "Perfil", valor: (u) => etiqueta(u.perfil, u.perfil === "admin" ? "alerta" : "neutra") },
        { titulo: "Status", valor: (u) => (u.ativo ? etiqueta("Ativo", "ok", "check") : etiqueta("Inativo", "neutra")) },
        { titulo: "Criado em", valor: (u) => fmt.dataHora(u.criado_em) },
        { titulo: "", valor: (u) => h("div", { class: "acoes", style: { margin: 0, flexWrap: "nowrap" } },
          u.login !== estado.usuario.login ? botao(u.ativo ? "Desativar" : "Reativar", { pequeno: true, icone: u.ativo ? "cadeado" : "check", acao: async () => {
            await api("POST", "/api/usuarios/ativo", { login: u.login, ativo: !u.ativo }); toast("Usuário atualizado."); await carregar();
          } }) : null,
          botao("Redefinir senha", { pequeno: true, icone: "chave", acao: async () => {
            const s = await pedirTexto("Nova senha para " + u.login, "Nova senha (8+ caracteres, maiúsculas, minúsculas e número)", "password");
            if (s == null) return;
            await api("POST", "/api/usuarios/senha", { login: u.login, senha: s }); toast("Senha alterada.");
          } })) },
      ], us)));
      const login = entrada("text"), nome = entrada("text"), senha = entrada("password", { autocomplete: "new-password" });
      const perfil = selecao([["operador", "operador"], ["visualizador", "visualizador"], ["admin", "admin"]], "operador");
      const form = h("form", {}, h("h3", {}, icone("plus"), "Novo usuário"),
        h("div", { class: "linha-form", style: { marginTop: "12px" } }, campo("Login", login), campo("Nome", nome), campo("Perfil", perfil), campo("Senha inicial", senha)),
        h("div", { class: "acoes" }, botao("Criar usuário", { tipo: "primario", icone: "check", submit: true })));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await api("POST", "/api/usuarios", { login: login.value, nome: nome.value, senha: senha.value, perfil: perfil.value }); toast("Usuário criado."); await carregar(); }
        catch (err) { toast(err.message, "erro"); }
      });
      area.appendChild(h("section", { class: "cartao vivo entrar" }, form));
    }
    await carregar();
  }

  // ================================================================== MINHA CONTA
  function paginaConta(cont) {
    const u = estado.usuario;
    cont.appendChild(topo("Minha conta", null));
    const atual = entrada("password", { autocomplete: "current-password" }), nova = entrada("password", { autocomplete: "new-password" }), nova2 = entrada("password", { autocomplete: "new-password" });
    const form = h("form", {}, h("div", { class: "linha-form" }, campo("Senha atual", atual), campo("Nova senha", nova, "8+ caracteres, maiúsculas, minúsculas e número."), campo("Repita a nova senha", nova2)),
      h("div", { class: "acoes" }, botao("Trocar senha", { tipo: "primario", icone: "chave", submit: true })));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try { await api("POST", "/api/conta/senha", { atual: atual.value, nova: nova.value, nova2: nova2.value }); toast("Senha alterada."); form.reset(); }
      catch (err) { toast(err.message, "erro"); }
    });
    const reduzir = h("input", { type: "checkbox", checked: preferenciaMovimento() === "reduzido" });
    reduzir.addEventListener("change", () => { aplicarMovimento(reduzir.checked ? "reduzido" : "normal"); toast(reduzir.checked ? "Animações reduzidas neste navegador." : "Animações ligadas."); });
    cont.append(cartao(u.nome, "user", `Login ${u.login} · perfil ${u.perfil}`), cartao("Trocar senha", "chave", null, form),
      cartao("Aparência", "brilho", "Vale só para este navegador.", h("label", { class: "caixa-check" }, reduzir, "Reduzir animações (ícones girando, gráficos crescendo, números contando)")));
  }

  iniciar();
})();
