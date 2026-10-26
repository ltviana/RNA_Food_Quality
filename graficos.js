/* Gráficos em SVG, sem bibliotecas externas.
   Todos recebem um elemento (container) e um objeto de opções; redesenham sozinhos ao redimensionar.
   Cores vêm das variáveis CSS (--c-fresca, --c-estragada, ...), então acompanham o tema claro/escuro. */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const semMovimento = () => document.documentElement.dataset.movimento === "reduzido";

  function s(tag, attrs, pai) {
    const el = document.createElementNS(NS, tag);
    for (const k in attrs || {}) if (attrs[k] != null) el.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(el);
    return el;
  }
  function texto(pai, x, y, conteudo, attrs) {
    const t = s("text", Object.assign({ x, y }, attrs || {}), pai);
    t.textContent = conteudo;                       // nunca innerHTML: rótulos vêm do banco
    return t;
  }
  function cor(nome) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
    return v || nome;
  }
  function resolverCor(c) { return c && c.startsWith("--") ? cor(c) : c; }

  // ---------------------------------------------------------------- dica (tooltip)
  let dica;
  function mostrarDica(ev, titulo, linhas) {
    if (!dica) {
      dica = document.createElement("div");
      dica.className = "dica-grafico";
      document.body.appendChild(dica);
    }
    dica.replaceChildren();
    if (titulo) {
      const t = document.createElement("div");
      t.className = "dica-titulo";
      t.textContent = titulo;
      dica.appendChild(t);
    }
    for (const [rotulo, valor, c] of linhas) {
      const l = document.createElement("div");
      l.className = "dica-linha";
      if (c) {
        const k = document.createElement("span");
        k.className = "dica-chave";
        k.style.background = resolverCor(c);
        l.appendChild(k);
      }
      const v = document.createElement("strong");
      v.textContent = valor;
      const r = document.createElement("span");
      r.textContent = rotulo;
      l.append(v, r);
      dica.appendChild(l);
    }
    dica.classList.add("visivel");
    const w = dica.offsetWidth, h = dica.offsetHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - 14;
    dica.style.transform = `translate(${Math.max(8, x)}px, ${Math.max(8, y)}px)`;
  }
  function esconderDica() { if (dica) dica.classList.remove("visivel"); }
  window.addEventListener("scroll", esconderDica, { passive: true });

  // ------------------------------------------------------------------ utilidades
  function escalaNice(max, n) {
    if (!(max > 0)) return { max: 1, passos: [0, 0.25, 0.5, 0.75, 1] };
    const bruto = max / n;
    const mag = Math.pow(10, Math.floor(Math.log10(bruto)));
    const f = bruto / mag;
    const passo = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag;
    const topo = Math.ceil(max / passo) * passo;
    const passos = [];
    for (let v = 0; v <= topo + passo / 2; v += passo) passos.push(+v.toFixed(10));
    return { max: topo, passos };
  }
  function medir(txt, tamanho) { return String(txt).length * (tamanho || 12) * 0.56; }
  function cortar(txt, maxPx, tamanho) {
    txt = String(txt);
    const maxC = Math.max(4, Math.floor(maxPx / ((tamanho || 12) * 0.56)));
    return txt.length > maxC ? txt.slice(0, maxC - 1) + "…" : txt;
  }
  // barra com só a ponta de dados arredondada (a base fica reta, presa ao eixo)
  function caminhoBarraH(x, y, w, h, r) {
    r = Math.min(r, w, h / 2);
    if (w <= 0) return "";
    return `M${x},${y}h${w - r}a${r},${r} 0 0 1 ${r},${r}v${h - 2 * r}a${r},${r} 0 0 1 ${-r},${r}h${-(w - r)}z`;
  }
  function caminhoBarraV(x, yBase, w, h, r) {
    r = Math.min(r, h, w / 2);
    if (h <= 0) return "";
    const y = yBase - h;
    return `M${x},${yBase}v${-(h - r)}a${r},${r} 0 0 1 ${r},${-r}h${w - 2 * r}a${r},${r} 0 0 1 ${r},${r}v${h - r}z`;
  }
  function legenda(container, series, tipo) {
    if (!series || series.length < 2) return;
    const l = document.createElement("div");
    l.className = "legenda";
    for (const sr of series) {
      const it = document.createElement("span");
      it.className = "legenda-item";
      const k = document.createElement("span");
      k.className = tipo === "linha" ? "legenda-linha" : "legenda-caixa";
      k.style.background = resolverCor(sr.cor);
      const t = document.createElement("span");
      t.textContent = sr.nome;
      it.append(k, t);
      l.appendChild(it);
    }
    container.appendChild(l);
  }
  function fmtData(d) {
    const dt = d instanceof Date ? d : new Date(d + "T00:00:00");
    return String(dt.getDate()).padStart(2, "0") + "/" + String(dt.getMonth() + 1).padStart(2, "0");
  }
  function animar(el, cls, atraso) {
    if (semMovimento() || !el) return;
    el.classList.add(cls);
    el.style.animationDelay = (atraso || 0) + "ms";
  }

  // ---- interação estilo Power BI: clique filtra, item selecionado destaca e os demais esmaecem
  function interagir(g, it, o, ver) {
    const sel = o.selecao ? o.selecao(it) : null;
    if (sel === false) g.classList.add("esmaecido");
    if (sel === true) g.classList.add("selecionado");
    g.addEventListener("pointermove", ver);
    g.addEventListener("pointerleave", esconderDica);
    g.addEventListener("focus", () => { const r = g.getBoundingClientRect(); ver({ clientX: r.left + r.width / 2, clientY: r.top }); });
    g.addEventListener("blur", esconderDica);
    if (o.aoClicar) {
      g.classList.add("clicavel");
      g.setAttribute("role", "button");
      g.addEventListener("click", (ev) => { ev.stopPropagation(); esconderDica(); o.aoClicar(it, ev); });
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); o.aoClicar(it, ev); } });
    }
  }
  // clique no fundo do gráfico (fora das marcas) limpa a seleção daquele gráfico
  function limparNoFundo(svg, o) {
    if (!o.aoLimpar) return;
    svg.addEventListener("click", (ev) => { if (!ev.target.closest(".marca")) o.aoLimpar(); });
  }
  let animacaoLigada = true;
  function definirAnimacao(v) { animacaoLigada = !!v; }

  // Cada gráfico é registrado para redesenhar ao mudar tamanho ou tema
  const ativos = new Map();
  const observador = new ResizeObserver((entradas) => {
    for (const e of entradas) {
      const reg = ativos.get(e.target);
      if (!reg) continue;
      const w = Math.round(e.contentRect.width);
      if (w && Math.abs(w - reg.largura) > 4) {
        reg.largura = w;
        clearTimeout(reg.t);
        reg.t = setTimeout(() => reg.desenhar(false), 120);
      }
    }
  });
  window.addEventListener("tema-alterado", () => { for (const reg of ativos.values()) reg.desenhar(false); });
  function registrar(container, desenhar) {
    const anterior = ativos.get(container);
    if (!anterior) observador.observe(container);
    const reg = { desenhar, largura: container.clientWidth };
    ativos.set(container, reg);
    desenhar(animacaoLigada);
  }
  // limpa registros de gráficos que saíram da página
  function limpar() {
    for (const el of [...ativos.keys()]) if (!document.body.contains(el)) { observador.unobserve(el); ativos.delete(el); }
  }

  function novoSvg(container, altura) {
    container.replaceChildren();
    const largura = Math.max(260, container.clientWidth || 560);
    const svg = s("svg", { width: largura, height: altura, viewBox: `0 0 ${largura} ${altura}`, role: "img", class: "svg-grafico" });
    return { svg, largura };
  }
  function vazio(container, msg) {
    container.replaceChildren();
    const d = document.createElement("div");
    d.className = "grafico-vazio";
    d.textContent = msg || "Sem dados para mostrar.";
    container.appendChild(d);
  }

  // ===================================================================== LINHA
  function linha(container, o) {
    registrar(container, (animado) => {
      const pts = (o.pontos || []).filter((p) => p.y != null);
      if (!pts.length) return vazio(container);
      const altura = o.altura || 250;
      const { svg, largura } = novoSvg(container, altura);
      const m = { t: 16, r: o.limite != null ? 74 : 18, b: 28, l: 54 };
      const W = largura - m.l - m.r, H = altura - m.t - m.b;
      const maxY = Math.max(...pts.map((p) => p.y), o.limite || 0) * 1.08;
      const esc = escalaNice(maxY, 4);
      const xs = pts.map((p) => +new Date(p.x + (typeof p.x === "string" && p.x.length === 10 ? "T00:00:00" : "")));
      const x0 = Math.min(...xs), x1 = Math.max(...xs);
      const X = (t) => (x1 === x0 ? m.l + W / 2 : m.l + ((t - x0) / (x1 - x0)) * W);
      const Y = (v) => m.t + H - (v / esc.max) * H;
      const c = resolverCor(o.cor || "--c-estragada");

      s("rect", { x: m.l, y: m.t, width: W, height: H, rx: 4, class: "moldura-plot" }, svg);
      const grade = s("g", { class: "grade" }, svg);
      for (const v of esc.passos) {
        s("line", { x1: m.l, x2: m.l + W, y1: Y(v), y2: Y(v) }, grade);
        texto(grade, m.l - 8, Y(v) + 4, o.fmtY ? o.fmtY(v) : v, { "text-anchor": "end", class: "rotulo-eixo" });
      }
      const nRot = Math.max(2, Math.floor(W / 70));
      const passo = Math.max(1, Math.ceil(pts.length / nRot));
      pts.forEach((p, i) => {
        if (i % passo === 0 ? (pts.length - 1 - i >= passo / 2 || i === pts.length - 1) : i === pts.length - 1)
          texto(grade, X(xs[i]), altura - 8, fmtData(p.x), { "text-anchor": "middle", class: "rotulo-eixo" });
      });
      if (o.limite != null) {
        s("line", { x1: m.l, x2: m.l + W, y1: Y(o.limite), y2: Y(o.limite), class: "linha-limite" }, svg);
        texto(svg, m.l + W + 6, Y(o.limite) + 4, o.rotuloLimite || "Limite", { class: "rotulo-limite" });
      }
      const d = pts.map((p, i) => (i ? "L" : "M") + X(xs[i]).toFixed(1) + "," + Y(p.y).toFixed(1)).join("");
      const caminho = s("path", { d, fill: "none", stroke: c, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      if (animado && !semMovimento()) {
        caminho.setAttribute("pathLength", "1");
        caminho.classList.add("desenhar-linha");
      }
      const pontos = s("g", {}, svg);
      const circulos = pts.map((p, i) => {
        const sel = o.selecao ? o.selecao(p) : null;
        const ci = s("circle", { cx: X(xs[i]), cy: Y(p.y), r: pts.length > 40 ? 2.5 : 4, fill: c,
          class: "ponto" + (sel === true ? " selecionado" : sel === false ? " esmaecido" : "") }, pontos);
        if (animado) animar(ci, "surgir", 300 + i * 12);
        return ci;
      });
      const guia = s("line", { y1: m.t, y2: m.t + H, class: "guia", opacity: 0 }, svg);
      const captura = s("rect", { x: m.l, y: m.t, width: W, height: H, fill: "transparent", class: "marca" + (o.aoClicar ? " clicavel" : "") }, svg);
      let ativo = -1;
      if (o.aoClicar) captura.addEventListener("click", (ev) => { if (ativo >= 0) { esconderDica(); o.aoClicar(pts[ativo], ev); } });
      captura.addEventListener("pointermove", (ev) => {
        const r = svg.getBoundingClientRect();
        const px = ev.clientX - r.left;
        let melhor = 0, dist = Infinity;
        xs.forEach((t, i) => { const dd = Math.abs(X(t) - px); if (dd < dist) { dist = dd; melhor = i; } });
        if (ativo >= 0) circulos[ativo].classList.remove("ativo");
        ativo = melhor;
        circulos[ativo].classList.add("ativo");
        guia.setAttribute("x1", X(xs[melhor])); guia.setAttribute("x2", X(xs[melhor])); guia.setAttribute("opacity", 1);
        const p = pts[melhor];
        mostrarDica(ev, o.tituloDica ? o.tituloDica(p) : fmtData(p.x), o.dica ? o.dica(p) : [[o.nome || "", o.fmtY ? o.fmtY(p.y) : p.y, c]]);
      });
      captura.addEventListener("pointerleave", () => {
        guia.setAttribute("opacity", 0);
        if (ativo >= 0) circulos[ativo].classList.remove("ativo");
        esconderDica();
      });
      limparNoFundo(svg, o);
      container.appendChild(svg);
    });
  }

  // ============================================================ BARRAS HORIZONTAIS
  function barrasH(container, o) {
    registrar(container, (animado) => {
      const itens = o.itens || [];
      if (!itens.length) return vazio(container);
      const alturaLinha = 34, esp = 16;
      const largEtiqueta = Math.min(190, Math.max(...itens.map((i) => medir(i.rotulo))) + 22);
      const altura = itens.length * alturaLinha + (o.limite != null ? 30 : 12);
      const { svg, largura } = novoSvg(container, altura);
      const m = { t: o.limite != null ? 22 : 6, r: 70, l: largEtiqueta };
      const W = largura - m.l - m.r;
      const maxV = Math.max(...itens.map((i) => i.valor), o.limite || 0) || 1;
      const X = (v) => (v / maxV) * W;
      const c = resolverCor(o.cor || "--c-estragada");
      if (o.limite != null) {
        const xl = m.l + X(o.limite);
        s("line", { x1: xl, x2: xl, y1: m.t - 6, y2: altura - 4, class: "linha-limite" }, svg);
        texto(svg, xl, 12, o.rotuloLimite || "Limite", { "text-anchor": "middle", class: "rotulo-limite" });
      }
      itens.forEach((it, i) => {
        const y = m.t + i * alturaLinha;
        const g = s("g", { class: "marca", tabindex: 0 }, svg);
        s("rect", { x: 0, y, width: largura, height: alturaLinha, fill: "transparent" }, g);   // alvo maior que a barra
        texto(g, m.l - 10, y + alturaLinha / 2 + 4, cortar(it.rotulo, largEtiqueta - 12), { "text-anchor": "end", class: "rotulo-cat" });
        const corItem = resolverCor(it.cor) || c;
        const barra = s("path", { d: caminhoBarraH(m.l, y + (alturaLinha - esp) / 2, Math.max(2, X(it.valor)), esp, 4), fill: corItem, class: "barra" }, g);
        if (animado) animar(barra, "crescer-x", i * 60);
        texto(g, m.l + X(it.valor) + 8, y + alturaLinha / 2 + 4, o.fmt ? o.fmt(it.valor) : it.valor, { class: "rotulo-valor" });
        const ver = (ev) => mostrarDica(ev, it.rotulo, o.dica ? o.dica(it) : [[o.nome || "", o.fmt ? o.fmt(it.valor) : it.valor, corItem]]);
        interagir(g, it, o, ver);
      });
      s("line", { x1: m.l, x2: m.l, y1: m.t - 2, y2: altura - (o.limite != null ? 4 : 2), class: "eixo-base" }, svg);
      limparNoFundo(svg, o);
      container.appendChild(svg);
    });
  }

  // ============================================================== COLUNAS VERTICAIS
  function barrasV(container, o) {
    registrar(container, (animado) => {
      const itens = o.itens || [];
      if (!itens.length) return vazio(container);
      const altura = o.altura || 250;
      const { svg, largura } = novoSvg(container, altura);
      const m = { t: 22, r: 12, b: 30, l: 58 };
      const W = largura - m.l - m.r, H = altura - m.t - m.b;
      const esc = escalaNice(Math.max(...itens.map((i) => i.valor)) * 1.05, 4);
      const Y = (v) => (v / esc.max) * H;
      const banda = W / itens.length, larg = Math.min(48, banda * 0.62);
      const c = resolverCor(o.cor || "--c-estragada");
      s("rect", { x: m.l, y: m.t, width: W, height: H, rx: 4, class: "moldura-plot" }, svg);
      const grade = s("g", { class: "grade" }, svg);
      for (const v of esc.passos) {
        const y = m.t + H - Y(v);
        s("line", { x1: m.l, x2: m.l + W, y1: y, y2: y }, grade);
        texto(grade, m.l - 8, y + 4, o.fmtEixo ? o.fmtEixo(v) : (o.fmt ? o.fmt(v) : v), { "text-anchor": "end", class: "rotulo-eixo" });
      }
      itens.forEach((it, i) => {
        const x = m.l + i * banda + (banda - larg) / 2;
        const g = s("g", { class: "marca", tabindex: 0 }, svg);
        s("rect", { x: m.l + i * banda, y: m.t, width: banda, height: H + m.b, fill: "transparent" }, g);
        const barra = s("path", { d: caminhoBarraV(x, m.t + H, larg, Math.max(2, Y(it.valor)), 4), fill: c, class: "barra" }, g);
        if (animado) animar(barra, "crescer-y", i * 60);
        texto(g, x + larg / 2, altura - 10, cortar(it.rotulo, banda - 4), { "text-anchor": "middle", class: "rotulo-cat" });
        if (itens.length <= 10 && banda > 54)
          texto(g, x + larg / 2, m.t + H - Y(it.valor) - 7, o.fmtCurto ? o.fmtCurto(it.valor) : (o.fmt ? o.fmt(it.valor) : it.valor), { "text-anchor": "middle", class: "rotulo-valor" });
        const ver = (ev) => mostrarDica(ev, it.rotulo, o.dica ? o.dica(it) : [[o.nome || "", o.fmt ? o.fmt(it.valor) : it.valor, c]]);
        interagir(g, it, o, ver);
      });
      limparNoFundo(svg, o);
      container.appendChild(svg);
    });
  }

  // ===================================================== BARRAS EMPILHADAS (horizontais)
  function empilhadaH(container, o) {
    registrar(container, (animado) => {
      const itens = o.itens || [];
      if (!itens.length) return vazio(container);
      container.replaceChildren();
      legenda(container, o.series, "caixa");
      const holder = document.createElement("div");
      container.appendChild(holder);
      const alturaLinha = 34, esp = 18;
      const largEtiqueta = Math.min(190, Math.max(...itens.map((i) => medir(i.rotulo))) + 22);
      const altura = itens.length * alturaLinha + 26;
      const largura = Math.max(260, container.clientWidth || 560);
      const svg = s("svg", { width: largura, height: altura, viewBox: `0 0 ${largura} ${altura}`, class: "svg-grafico" });
      const m = { t: 4, r: o.normalizar ? 14 : 70, l: largEtiqueta };
      const W = largura - m.l - m.r;
      const maxTot = o.normalizar ? 1 : Math.max(...itens.map((i) => i.partes.reduce((a, b) => a + b, 0))) || 1;
      const cores = o.series.map((sr) => resolverCor(sr.cor));
      // eixo inferior
      const grade = s("g", { class: "grade" }, svg);
      const passos = o.normalizar ? [0, 0.25, 0.5, 0.75, 1] : escalaNice(maxTot, Math.max(2, Math.min(5, Math.floor(W / 95)))).passos.filter((v) => v <= maxTot * 1.001);
      for (const v of passos) {
        const x = m.l + (v / maxTot) * W;
        s("line", { x1: x, x2: x, y1: m.t, y2: altura - 22 }, grade);
        texto(grade, x, altura - 6, o.normalizar ? Math.round(v * 100) + "%" : (o.fmtEixo ? o.fmtEixo(v) : v), { "text-anchor": "middle", class: "rotulo-eixo" });
      }
      itens.forEach((it, i) => {
        const y = m.t + i * alturaLinha + (alturaLinha - esp) / 2;
        const tot = it.partes.reduce((a, b) => a + b, 0) || 1;
        const g = s("g", { class: "marca", tabindex: 0 }, svg);
        s("rect", { x: 0, y: m.t + i * alturaLinha, width: largura, height: alturaLinha, fill: "transparent" }, g);
        texto(g, m.l - 10, y + esp / 2 + 4, cortar(it.rotulo, largEtiqueta - 12), { "text-anchor": "end", class: "rotulo-cat" });
        let x = m.l;
        const ultimo = it.partes.reduce((u, v, k) => (v > 0 ? k : u), -1);
        const barras = s("g", {}, g);
        if (animado) animar(barras, "crescer-x", i * 60);
        it.partes.forEach((v, k) => {
          if (v <= 0) return;
          const w = (o.normalizar ? v / tot : v / maxTot) * W;
          const largSeg = Math.max(1, w - (k === ultimo ? 0 : 2));       // 2px de respiro entre segmentos
          s("path", { d: k === ultimo ? caminhoBarraH(x, y, largSeg, esp, 4) : `M${x},${y}h${largSeg}v${esp}h${-largSeg}z`, fill: cores[k], class: "barra" }, barras);
          x += w;
        });
        const ver = (ev) => mostrarDica(ev, it.rotulo, o.dica ? o.dica(it) :
          o.series.map((sr, j) => [sr.nome, (o.fmt ? o.fmt(it.partes[j]) : it.partes[j]) + " (" + ((it.partes[j] / tot) * 100).toFixed(1).replace(".", ",") + "%)", sr.cor]));
        interagir(g, it, o, ver);
        if (!o.normalizar)
          texto(g, x + 8, y + esp / 2 + 4, o.fmt ? o.fmt(tot) : tot, { class: "rotulo-valor" });
      });
      s("line", { x1: m.l, x2: m.l, y1: m.t, y2: altura - 22, class: "eixo-base" }, svg);
      limparNoFundo(svg, o);
      holder.appendChild(svg);
    });
  }

  // ============================================== COLUNAS EMPILHADAS NO TEMPO (volume)
  function colunasEmpilhadas(container, o) {
    registrar(container, (animado) => {
      const itens = o.itens || [];
      if (!itens.length) return vazio(container);
      container.replaceChildren();
      legenda(container, o.series, "caixa");
      const holder = document.createElement("div");
      container.appendChild(holder);
      const altura = o.altura || 230;
      const largura = Math.max(260, container.clientWidth || 560);
      const svg = s("svg", { width: largura, height: altura, viewBox: `0 0 ${largura} ${altura}`, class: "svg-grafico" });
      const m = { t: 10, r: 12, b: 28, l: 54 };
      const W = largura - m.l - m.r, H = altura - m.t - m.b;
      const tots = itens.map((it) => it.partes.reduce((a, b) => a + b, 0));
      const esc = escalaNice(Math.max(...tots) * 1.05, 4);
      const Y = (v) => (v / esc.max) * H;
      const banda = W / itens.length, larg = Math.max(2, Math.min(36, banda * 0.7));
      const cores = o.series.map((sr) => resolverCor(sr.cor));
      s("rect", { x: m.l, y: m.t, width: W, height: H, rx: 4, class: "moldura-plot" }, svg);
      const grade = s("g", { class: "grade" }, svg);
      for (const v of esc.passos) {
        const y = m.t + H - Y(v);
        s("line", { x1: m.l, x2: m.l + W, y1: y, y2: y }, grade);
        texto(grade, m.l - 8, y + 4, o.fmtEixo ? o.fmtEixo(v) : v, { "text-anchor": "end", class: "rotulo-eixo" });
      }
      const nRot = Math.max(2, Math.floor(W / 64));
      const passo = Math.max(1, Math.ceil(itens.length / nRot));
      itens.forEach((it, i) => {
        const x = m.l + i * banda + (banda - larg) / 2;
        const g = s("g", { class: "marca", tabindex: 0 }, svg);
        s("rect", { x: m.l + i * banda, y: m.t, width: banda, height: H, fill: "transparent" }, g);
        const col = s("g", {}, g);
        if (animado) animar(col, "crescer-y", Math.min(600, i * 18));
        let base = m.t + H;
        const ultimo = it.partes.reduce((u, v, k) => (v > 0 ? k : u), -1);
        it.partes.forEach((v, k) => {
          if (v <= 0) return;
          const hh = Y(v), hSeg = Math.max(1, hh - (k === ultimo ? 0 : (larg > 6 ? 2 : 0)));
          s("path", { d: k === ultimo ? caminhoBarraV(x, base, larg, hSeg, Math.min(4, larg / 2)) : `M${x},${base}v${-hSeg}h${larg}v${hSeg}z`, fill: cores[k], class: "barra" }, col);
          base -= hh;
        });
        if (i % passo === 0 ? (itens.length - 1 - i >= passo / 2 || i === itens.length - 1) : i === itens.length - 1)
          texto(svg, m.l + i * banda + banda / 2, altura - 8, it.rotulo || fmtData(it.x), { "text-anchor": "middle", class: "rotulo-eixo" });
        const ver = (ev) => mostrarDica(ev, it.titulo || it.rotulo || fmtData(it.x), o.dica ? o.dica(it) :
          o.series.map((sr, j) => [sr.nome, o.fmt ? o.fmt(it.partes[j]) : it.partes[j], sr.cor]));
        interagir(g, it, o, ver);
      });
      limparNoFundo(svg, o);
      holder.appendChild(svg);
    });
  }

  // ======================================================== BARRAS AGRUPADAS (horizontais)
  function agrupadasH(container, o) {
    registrar(container, (animado) => {
      const itens = o.itens || [];
      if (!itens.length) return vazio(container);
      container.replaceChildren();
      legenda(container, o.series, "caixa");
      const holder = document.createElement("div");
      container.appendChild(holder);
      const n = o.series.length, esp = 12, gap = 2, alturaLinha = n * esp + (n - 1) * gap + 18;
      const largEtiqueta = Math.min(190, Math.max(...itens.map((i) => medir(i.rotulo))) + 22);
      const altura = itens.length * alturaLinha + 24;
      const largura = Math.max(260, container.clientWidth || 560);
      const svg = s("svg", { width: largura, height: altura, viewBox: `0 0 ${largura} ${altura}`, class: "svg-grafico" });
      const m = { t: 4, r: 84, l: largEtiqueta };
      const W = largura - m.l - m.r;
      const maxV = Math.max(...itens.flatMap((i) => i.valores)) || 1;
      const esc = escalaNice(maxV, Math.max(2, Math.min(5, Math.floor(W / 95))));
      const X = (v) => (Math.max(0, v) / esc.max) * W;
      const cores = o.series.map((sr) => resolverCor(sr.cor));
      const grade = s("g", { class: "grade" }, svg);
      for (const v of esc.passos) {
        const x = m.l + X(v);
        s("line", { x1: x, x2: x, y1: m.t, y2: altura - 22 }, grade);
        texto(grade, x, altura - 6, o.fmtEixo ? o.fmtEixo(v) : v, { "text-anchor": "middle", class: "rotulo-eixo" });
      }
      itens.forEach((it, i) => {
        const y0 = m.t + i * alturaLinha + 9;
        const g = s("g", { class: "marca", tabindex: 0 }, svg);
        s("rect", { x: 0, y: m.t + i * alturaLinha, width: largura, height: alturaLinha, fill: "transparent" }, g);
        texto(g, m.l - 10, y0 + (n * esp + (n - 1) * gap) / 2 + 4, cortar(it.rotulo, largEtiqueta - 12), { "text-anchor": "end", class: "rotulo-cat" });
        it.valores.forEach((v, k) => {
          const y = y0 + k * (esp + gap);
          const b = s("path", { d: caminhoBarraH(m.l, y, Math.max(2, X(v)), esp, 4), fill: cores[k], class: "barra" }, g);
          if (animado) animar(b, "crescer-x", i * 60 + k * 40);
          texto(g, m.l + X(v) + 6, y + esp - 2, o.fmtCurto ? o.fmtCurto(v) : (o.fmt ? o.fmt(v) : v), { class: "rotulo-valor pequeno" });
        });
        const ver = (ev) => mostrarDica(ev, it.rotulo, o.dica ? o.dica(it) : o.series.map((sr, k) => [sr.nome, o.fmt ? o.fmt(it.valores[k]) : it.valores[k], sr.cor]));
        interagir(g, it, o, ver);
      });
      s("line", { x1: m.l, x2: m.l, y1: m.t, y2: altura - 22, class: "eixo-base" }, svg);
      limparNoFundo(svg, o);
      holder.appendChild(svg);
    });
  }

  window.Graficos = { definirAnimacao, linha, barrasH, barrasV, empilhadaH, colunasEmpilhadas, agrupadasH, limpar, esconderDica };
})();
