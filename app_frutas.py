"""
Controle de Qualidade de Frutas - aplicativo executivo (Streamlit + SQLite).

Como abrir (Anaconda Prompt, na pasta dos scripts):
    python -m pip install streamlit pandas
    python -m streamlit run app_frutas.py

O navegador abre sozinho em http://localhost:8501. No primeiro acesso você cria o administrador.
Os dados ficam em frutas.db (mesma pasta). A esteira grava nele com:
    python esteira.py --video video.mp4 --fornecedor "Nome do fornecedor"
"""
import io
import os
from datetime import date, timedelta
import time

import altair as alt
import pandas as pd
import streamlit as st

import frutas_db as db
import lancador_esteira as lanc

# ------------------------------------------------------------------ aparência
COR_PERDA = "#c8452f"      # estragadas / perdas
COR_OK = "#2e7d5b"         # frescas / lucro
COR_ALERTA = "#d89b1d"     # incertas / alerta
COR_NEUTRA = "#4b6fa5"     # volume / custo

st.set_page_config(page_title="Controle de Qualidade de Frutas", page_icon="🍎", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1280px;}
[data-testid="stMetric"] {background: rgba(128,128,128,.08); border-radius: 10px; padding: 12px 16px;}
[data-testid="stMetricLabel"] {opacity: .75;}
h1, h2, h3 {letter-spacing: -.01em;}
</style>
""", unsafe_allow_html=True)

PAGINAS_POR_PERFIL = {
    "admin": ["Dashboard", "Executar esteira", "Registrar contagem", "Lotes e revisão", "Fornecedores e preços", "Usuários", "Minha conta"],
    "operador": ["Dashboard", "Executar esteira", "Registrar contagem", "Lotes e revisão", "Minha conta"],
    "visualizador": ["Dashboard", "Lotes e revisão", "Minha conta"],
}


# ------------------------------------------------------------------ utilidades
def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v):
    return f"{v * 100:.1f}%".replace(".", ",")


def inteiro(v):
    return f"{int(v):,}".replace(",", ".")


def mostrar_grafico(chart):
    try:
        st.altair_chart(chart, width="stretch")
    except Exception:                       # versões antigas do Streamlit
        st.altair_chart(chart, use_container_width=True)


def mostrar_tabela(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def recarregar():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


@st.cache_resource
def _tentativas():
    return {}       # login -> (falhas, bloqueado_até)


# ---------------------------------------------------------------------- login
def tela_primeiro_acesso():
    st.title("Bem-vindo")
    st.write("Primeiro acesso: crie a empresa e a conta do **administrador**.")
    with st.form("setup"):
        empresa = st.text_input("Nome da empresa")
        nome = st.text_input("Seu nome")
        login = st.text_input("Login (sem espaços)")
        s1 = st.text_input("Senha", type="password", help="Mínimo de 8 caracteres, com maiúsculas, minúsculas e número.")
        s2 = st.text_input("Repita a senha", type="password")
        if st.form_submit_button("Criar conta"):
            try:
                if s1 != s2:
                    raise ValueError("As senhas não conferem.")
                if " " in login.strip():
                    raise ValueError("O login não pode ter espaços.")
                db.criar_usuario(login, nome, s1, "admin")
                db.set_config("empresa", empresa.strip() or "Minha empresa")
                st.success("Conta criada! Entre com o login e a senha.")
                time.sleep(1)
                recarregar()
            except ValueError as e:
                st.error(str(e))


def tela_login():
    empresa = db.get_config("empresa", "Controle de Qualidade de Frutas")
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        st.title(empresa)
        st.caption("Controle de qualidade e perdas de frutas")
        with st.form("login"):
            login = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
        if entrar:
            chave = login.strip().lower()
            falhas, ate = _tentativas().get(chave, (0, 0))
            if time.time() < ate:
                st.error(f"Muitas tentativas. Aguarde {int(ate - time.time())} s e tente de novo.")
                return
            usuario = db.autenticar(login, senha)
            if usuario:
                _tentativas().pop(chave, None)
                st.session_state["usuario"] = usuario
                recarregar()
            else:
                falhas += 1
                _tentativas()[chave] = (falhas, time.time() + 60 if falhas >= 5 else 0)
                st.error("Login ou senha incorretos.")


# ------------------------------------------------------------- dados/dashboard
def para_df(rows):
    cols = ["contagem_id", "lote_id", "data", "origem", "referencia", "usuario", "fornecedor_id", "fornecedor",
            "fruta", "frescas", "estragadas", "incertas", "custo_unit", "preco_unit", "total", "custo_total",
            "receita_potencial", "receita_realizada", "receita_perdida", "custo_perdido", "receita_em_revisao",
            "lucro_realizado"]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        df["Fruta"] = df["fruta"].map(db.nome_exibicao)
    else:
        df["Fruta"] = []
    return df


SOMAS = ["frescas", "estragadas", "incertas", "total", "custo_total", "receita_potencial",
         "receita_realizada", "receita_perdida", "custo_perdido", "receita_em_revisao", "lucro_realizado"]


def agrupar(df, chave):
    g = df.groupby(chave, as_index=False)[SOMAS].sum()
    g["perda_pct"] = (g["estragadas"] / g["total"]).where(g["total"] > 0, 0.0)
    g["incerta_pct"] = (g["incertas"] / g["total"]).where(g["total"] > 0, 0.0)
    return g


def totais(df):
    t = {k: float(df[k].sum()) for k in SOMAS}
    t["perda_pct"] = t["estragadas"] / t["total"] if t["total"] else 0.0
    return t


def pagina_dashboard():
    st.title("Dashboard")
    forn = db.listar_fornecedores()
    if not forn:
        st.info("Nenhum fornecedor cadastrado ainda. Cadastre fornecedores, preços e contagens para ver o dashboard.")
        if st.session_state["usuario"]["perfil"] == "admin" and st.button("Gerar dados de exemplo (para conhecer o painel)"):
            db.gerar_exemplo()
            recarregar()
        return

    # ---- filtros
    hoje = date.today()
    c1, c2, c3 = st.columns([1.2, 1.4, 1.4])
    atalho = c1.selectbox("Período", ["Últimos 30 dias", "Últimos 90 dias", "Este ano", "Tudo", "Personalizado"])
    if atalho == "Últimos 30 dias":
        d1, d2 = hoje - timedelta(days=29), hoje
    elif atalho == "Últimos 90 dias":
        d1, d2 = hoje - timedelta(days=89), hoje
    elif atalho == "Este ano":
        d1, d2 = date(hoje.year, 1, 1), hoje
    elif atalho == "Tudo":
        d1, d2 = date(2000, 1, 1), hoje
    else:
        intervalo = c1.date_input("De / até", value=(hoje - timedelta(days=29), hoje))
        d1, d2 = (intervalo if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2 else (hoje, hoje))
    nomes_forn = {f["id"]: f["nome"] for f in forn}
    sel_forn = c2.multiselect("Fornecedores", list(nomes_forn), format_func=nomes_forn.get,
                              placeholder="Todos os fornecedores")
    sel_frutas = c3.multiselect("Frutas", db.frutas_conhecidas(), format_func=db.nome_exibicao,
                                placeholder="Todas as frutas")

    df = para_df(db.linhas(d1, d2, sel_forn or None, sel_frutas or None))
    if df.empty:
        st.warning("Não há contagens neste período/filtro.")
        return

    # período anterior de mesmo tamanho (para comparar)
    dias = (d2 - d1).days + 1
    ant = para_df(db.linhas(d1 - timedelta(days=dias), d1 - timedelta(days=1), sel_forn or None, sel_frutas or None)) \
        if atalho != "Tudo" else pd.DataFrame(columns=df.columns)
    t, ta = totais(df), (totais(ant) if not ant.empty else None)
    limite = float(db.get_config("limite_perda", "10")) / 100

    # ---- alertas
    sem_preco = df[(df["preco_unit"] == 0) & (df["total"] > 0)][["fornecedor", "Fruta"]].drop_duplicates()
    if not sem_preco.empty:
        lista = "; ".join(f"{r.Fruta} ({r.fornecedor})" for r in sem_preco.itertuples())
        st.warning(f"Há frutas sem preço cadastrado, então os valores em R$ estão subestimados: {lista}. "
                   "Cadastre em *Fornecedores e preços*.")
    por_forn = agrupar(df, "fornecedor")
    acima = por_forn[(por_forn["perda_pct"] > limite) & (por_forn["total"] >= 50)].sort_values("perda_pct", ascending=False)
    if not acima.empty:
        txt = "; ".join(f"**{r.fornecedor}** {pct(r.perda_pct)}" for r in acima.itertuples())
        st.error(f"Fornecedores acima do limite de perda de {pct(limite)}: {txt}")

    # ---- KPIs
    def kpi(col, rotulo, valor, chave=None, fmt="num", bom_subir=False, ajuda=None):
        """Mostra o valor e, se houver período anterior, a variação (verde = melhorou)."""
        d = None
        if chave and ta is not None and ta["total"]:
            dif = t[chave] - ta[chave]
            d = (f"{dif * 100:+.1f} p.p.".replace(".", ",") if fmt == "pct"
                 else (brl(dif) if fmt == "brl" else f"{dif:+,.0f}".replace(",", ".")))
        cor = "off" if chave in (None, "total", "custo_total") else ("normal" if bom_subir else "inverse")
        col.metric(rotulo, valor, d, delta_color=cor, help=ajuda)

    k = st.columns(5)
    kpi(k[0], "Frutas processadas", inteiro(t["total"]), "total")
    kpi(k[1], "Taxa de perda", pct(t["perda_pct"]), "perda_pct", "pct")
    kpi(k[2], "Custo de aquisição", brl(t["custo_total"]), "custo_total", "brl")
    kpi(k[3], "Receita perdida", brl(t["receita_perdida"]), "receita_perdida", "brl",
        ajuda="Frutas estragadas × preço de venda.")
    kpi(k[4], "Lucro bruto realizado", brl(t["lucro_realizado"]), "lucro_realizado", "brl", True,
        "Receita das frescas menos o custo de todas as frutas compradas.")
    k2 = st.columns(5)
    kpi(k2[0], "Receita potencial", brl(t["receita_potencial"]), ajuda="Se nenhuma fruta estragasse.")
    kpi(k2[1], "Receita realizada", brl(t["receita_realizada"]), ajuda="Frutas frescas × preço de venda.")
    kpi(k2[2], "Custo perdido", brl(t["custo_perdido"]), ajuda="O que foi pago por frutas que estragaram.")
    margem = t["lucro_realizado"] / t["receita_realizada"] if t["receita_realizada"] else 0
    kpi(k2[3], "Margem realizada", pct(margem))
    kpi(k2[4], "Incertas a revisar", inteiro(t["incertas"]),
        ajuda="A IA não teve certeza; revise em Lotes e revisão.")
    if ta is not None and ta["total"]:
        st.caption(f"Variações comparadas ao período anterior de mesmo tamanho ({dias} dias).")

    st.divider()

    # ---- evolução no tempo
    freq = "D" if dias <= 45 else "W-MON"
    serie = df.set_index("data").groupby(pd.Grouper(freq=freq))[["estragadas", "total", "receita_perdida"]].sum().reset_index()
    serie = serie[serie["total"] > 0]
    serie["perda_pct"] = serie["estragadas"] / serie["total"]
    cl, cr = st.columns(2)
    with cl:
        st.subheader("Perda ao longo do tempo")
        base = alt.Chart(serie).encode(x=alt.X("data:T", title=None))
        linha = base.mark_line(point=True, color=COR_PERDA).encode(
            y=alt.Y("perda_pct:Q", title="% de frutas estragadas", axis=alt.Axis(format="%")),
            tooltip=[alt.Tooltip("data:T", title="Data"), alt.Tooltip("perda_pct:Q", title="Perda", format=".1%"),
                     alt.Tooltip("total:Q", title="Frutas"), alt.Tooltip("receita_perdida:Q", title="Receita perdida (R$)", format=",.2f")])
        regra = alt.Chart(pd.DataFrame({"y": [limite]})).mark_rule(strokeDash=[5, 4], color=COR_ALERTA).encode(y="y:Q")
        mostrar_grafico(linha + regra)
        st.caption(f"Linha tracejada = limite de perda ({pct(limite)}). Agrupado por {'dia' if freq == 'D' else 'semana'}.")
    with cr:
        st.subheader("Perda por fornecedor")
        ordem = por_forn.sort_values("perda_pct", ascending=False)["fornecedor"].tolist()
        barras = alt.Chart(por_forn).mark_bar(color=COR_PERDA).encode(
            y=alt.Y("fornecedor:N", sort=ordem, title=None),
            x=alt.X("perda_pct:Q", title="% de frutas estragadas", axis=alt.Axis(format="%")),
            tooltip=[alt.Tooltip("fornecedor:N", title="Fornecedor"), alt.Tooltip("perda_pct:Q", title="Perda", format=".1%"),
                     alt.Tooltip("estragadas:Q", title="Estragadas"), alt.Tooltip("total:Q", title="Total")])
        regra_h = alt.Chart(pd.DataFrame({"x": [limite]})).mark_rule(strokeDash=[5, 4], color=COR_ALERTA).encode(x="x:Q")
        mostrar_grafico(barras + regra_h)

    cl, cr = st.columns(2)
    por_fruta = agrupar(df, "Fruta")
    with cl:
        st.subheader("Receita perdida por fruta")
        ordem = por_fruta.sort_values("receita_perdida", ascending=False)["Fruta"].tolist()
        mostrar_grafico(alt.Chart(por_fruta).mark_bar(color=COR_PERDA).encode(
            x=alt.X("Fruta:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("receita_perdida:Q", title="R$ perdidos"),
            tooltip=[alt.Tooltip("Fruta:N"), alt.Tooltip("receita_perdida:Q", title="Receita perdida (R$)", format=",.2f"),
                     alt.Tooltip("perda_pct:Q", title="Perda", format=".1%")]))
    with cr:
        st.subheader("Composição por fornecedor")
        comp = por_forn.melt(id_vars="fornecedor", value_vars=["frescas", "estragadas", "incertas"],
                             var_name="Estado", value_name="Frutas")
        comp["Estado"] = comp["Estado"].map({"frescas": "Frescas", "estragadas": "Estragadas", "incertas": "Incertas"})
        mostrar_grafico(alt.Chart(comp).mark_bar().encode(
            y=alt.Y("fornecedor:N", title=None),
            x=alt.X("Frutas:Q", stack="normalize", title="Proporção", axis=alt.Axis(format="%")),
            color=alt.Color("Estado:N", scale=alt.Scale(domain=["Frescas", "Estragadas", "Incertas"],
                                                       range=[COR_OK, COR_PERDA, COR_ALERTA]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["fornecedor:N", "Estado:N", alt.Tooltip("Frutas:Q", format=",")]))

    # ---- ranking de fornecedores
    st.subheader("Ranking de fornecedores")
    rank = por_forn.sort_values("perda_pct", ascending=False).copy()
    tabela = pd.DataFrame({
        "Fornecedor": rank["fornecedor"], "Frutas": rank["total"].astype(int),
        "Perda %": (rank["perda_pct"] * 100).round(1), "Estragadas": rank["estragadas"].astype(int),
        "Custo de aquisição (R$)": rank["custo_total"].round(2), "Receita perdida (R$)": rank["receita_perdida"].round(2),
        "Custo perdido (R$)": rank["custo_perdido"].round(2), "Lucro realizado (R$)": rank["lucro_realizado"].round(2),
        "Status": ["⚠ Acima do limite" if (p > limite and n >= 50) else "OK" for p, n in zip(rank["perda_pct"], rank["total"])],
    })
    mostrar_tabela(tabela)

    st.subheader("Fornecedor × fruta")
    cruz = agrupar(df, ["fornecedor", "Fruta"]).sort_values("receita_perdida", ascending=False)
    mostrar_tabela(pd.DataFrame({
        "Fornecedor": cruz["fornecedor"], "Fruta": cruz["Fruta"], "Frutas": cruz["total"].astype(int),
        "Perda %": (cruz["perda_pct"] * 100).round(1), "Receita perdida (R$)": cruz["receita_perdida"].round(2),
        "Custo perdido (R$)": cruz["custo_perdido"].round(2)}))

    csv = df[["data", "lote_id", "fornecedor", "fruta", "frescas", "estragadas", "incertas", "custo_unit", "preco_unit",
              "custo_total", "receita_potencial", "receita_realizada", "receita_perdida", "custo_perdido",
              "lucro_realizado", "origem", "referencia"]].copy()
    csv["data"] = csv["data"].dt.strftime("%Y-%m-%d")
    st.download_button("Baixar dados filtrados (CSV para Excel)",
                       csv.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name=f"contagens_{d1}_{d2}.csv", mime="text/csv")


# ------------------------------------------------------------ registrar contagem
def _lotes_recentes():
    """Lista os últimos lotes (manuais e da esteira). Atualiza sozinha a cada 5 s quando o Streamlit permite."""
    st.subheader("Contagens registradas recentemente")
    lotes = db.ultimos_lotes(15)
    if not lotes:
        st.caption("Nenhuma contagem registrada ainda.")
        return
    rotulo_origem = {"manual": "Manual", "esteira": "Esteira", "exemplo": "Exemplo"}
    tab = pd.DataFrame([{
        "Lote": l["lote_id"], "Registrado em": l["criado_em"], "Data": l["data"], "Fornecedor": l["fornecedor"],
        "Origem": rotulo_origem.get(l["origem"], l["origem"]), "Referência": l["referencia"],
        "Frutas": l["frescas"] + l["estragadas"] + l["incertas"], "Frescas": l["frescas"],
        "Estragadas": l["estragadas"], "Incertas": l["incertas"],
        "Perda %": round(l["estragadas"] / max(1, l["frescas"] + l["estragadas"] + l["incertas"]) * 100, 1)} for l in lotes])
    mostrar_tabela(tab)
    ids = [l["lote_id"] for l in lotes]
    lid = st.selectbox("Ver detalhes por fruta do lote", ids, key="detalhe_lote")
    det = db.contagens_do_lote(lid)
    mostrar_tabela(pd.DataFrame([{"Fruta": db.nome_exibicao(d["fruta"]), "Frescas": d["frescas"],
                                  "Estragadas": d["estragadas"], "Incertas": d["incertas"]} for d in det]))
    if not hasattr(st, "fragment"):
        st.button("Atualizar lista")


if hasattr(st, "fragment"):
    _lotes_recentes = st.fragment(run_every=5)(_lotes_recentes)



def pagina_registrar():
    st.title("Registrar contagem")
    forn = db.listar_fornecedores(somente_ativos=True)
    if not forn:
        st.info("Cadastre ao menos um fornecedor (menu *Fornecedores e preços*) antes de registrar contagens.")
        return
    st.caption("Use quando a contagem não vier direto da esteira. Contagens da esteira entram sozinhas "
               "com `python esteira.py --fornecedor \"Nome\"`.")
    nomes = {f["id"]: f["nome"] for f in forn}
    c1, c2, c3 = st.columns(3)
    fid = c1.selectbox("Fornecedor", list(nomes), format_func=nomes.get)
    dia = c2.date_input("Data", value=date.today(), max_value=date.today())
    ref = c3.text_input("Referência (nota fiscal, nº da carga)")

    precos = {p["fruta"]: p for p in db.listar_precos(fid)}
    frutas = sorted(set(db.frutas_conhecidas()) | set(precos))
    base = pd.DataFrame({"Fruta": [db.nome_exibicao(f) for f in frutas], "Frescas": 0, "Estragadas": 0, "Incertas": 0})
    editado = st.data_editor(
        base, hide_index=True, disabled=["Fruta"], key=f"cont_{fid}",
        column_config={c: st.column_config.NumberColumn(c, min_value=0, step=1, format="%d")
                       for c in ("Frescas", "Estragadas", "Incertas")})
    inv = {db.nome_exibicao(f): f for f in frutas}
    contagens, sem_preco = {}, []
    for r in editado.itertuples(index=False):
        if r.Frescas + r.Estragadas + r.Incertas > 0:
            f = inv[r.Fruta]
            contagens[f] = (int(r.Frescas), int(r.Estragadas), int(r.Incertas))
            if f not in precos:
                sem_preco.append(r.Fruta)
    if contagens:
        tot = sum(sum(v) for v in contagens.values())
        est = sum(v[1] for v in contagens.values())
        perda_rs = sum(v[1] * precos.get(f, {}).get("preco_unit", 0) for f, v in contagens.items())
        st.write(f"**{inteiro(tot)}** frutas · perda **{pct(est / tot)}** · receita perdida **{brl(perda_rs)}**")
    if sem_preco:
        st.warning(f"Sem preço cadastrado para este fornecedor: {', '.join(sem_preco)}. "
                   "A contagem será salva, mas os valores em R$ ficarão zerados.")
    if st.button("Salvar contagem", type="primary", disabled=not contagens):
        try:
            lote = db.registrar_lote(fid, contagens, data=dia, origem="manual", referencia=ref,
                                     usuario=st.session_state["usuario"]["login"])
            st.success(f"Lote #{lote} salvo.")
        except ValueError as e:
            st.error(str(e))
    st.divider()
    _lotes_recentes()


# ------------------------------------------------------------- lotes e revisão
def pagina_lotes():
    st.title("Lotes e revisão")
    perfil = st.session_state["usuario"]["perfil"]
    hoje = date.today()
    c1, c2 = st.columns(2)
    intervalo = c1.date_input("Período", value=(hoje - timedelta(days=29), hoje))
    d1, d2 = intervalo if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2 else (hoje, hoje)
    df = para_df(db.linhas(d1, d2))
    if df.empty:
        st.info("Nenhuma contagem no período.")
        return
    lotes = df.groupby(["lote_id", "data", "fornecedor", "origem", "referencia"], as_index=False)[
        ["total", "frescas", "estragadas", "incertas", "receita_perdida"]].sum().sort_values("lote_id", ascending=False)
    lotes["Perda %"] = (lotes["estragadas"] / lotes["total"] * 100).round(1)
    lotes["data"] = lotes["data"].dt.strftime("%d/%m/%Y")
    mostrar_tabela(lotes.rename(columns={
        "lote_id": "Lote", "data": "Data", "fornecedor": "Fornecedor", "origem": "Origem", "referencia": "Referência",
        "total": "Frutas", "frescas": "Frescas", "estragadas": "Estragadas", "incertas": "Incertas",
        "receita_perdida": "Receita perdida (R$)"}))

    if perfil in ("admin", "operador"):
        st.subheader("Revisar frutas incertas")
        inc = df[df["incertas"] > 0].sort_values("lote_id", ascending=False)
        if inc.empty:
            st.caption("Nenhuma contagem com frutas incertas no período.")
        else:
            rotulos = {int(r.contagem_id): f"Lote {r.lote_id} · {r.data:%d/%m} · {r.fornecedor} · {r.Fruta} · {r.incertas} incertas"
                       for r in inc.itertuples()}
            cid = st.selectbox("Contagem", list(rotulos), format_func=rotulos.get)
            max_inc = int(inc[inc["contagem_id"] == cid]["incertas"].iloc[0])
            a, b, c = st.columns([1, 1, 1])
            fr = a.number_input("Eram frescas", 0, max_inc, 0)
            es = b.number_input("Eram estragadas", 0, max_inc, 0)
            if c.button("Aplicar revisão"):
                try:
                    db.resolver_incertas(int(cid), int(fr), int(es))
                    recarregar()
                except ValueError as e:
                    st.error(str(e))

    if perfil == "admin":
        st.subheader("Excluir lote")
        lid = st.selectbox("Lote", lotes["lote_id"].tolist(), key="del_lote")
        confirma = st.checkbox("Confirmo que quero excluir este lote definitivamente")
        if st.button("Excluir", disabled=not confirma):
            db.excluir_lote(int(lid))
            recarregar()


# ------------------------------------------------------ fornecedores e preços
def pagina_fornecedores():
    st.title("Fornecedores e preços")
    aba1, aba2, aba3 = st.tabs(["Fornecedores", "Preços por fornecedor", "Configurações"])
    forn = db.listar_fornecedores()
    with aba1:
        if forn:
            mostrar_tabela(pd.DataFrame(forn)[["id", "nome", "cnpj", "contato", "ativo"]].rename(
                columns={"id": "ID", "nome": "Nome", "cnpj": "CNPJ", "contato": "Contato", "ativo": "Ativo"}))
        st.subheader("Novo / editar")
        opcoes = {0: "➕ Novo fornecedor"} | {f["id"]: f["nome"] for f in forn}
        sel = st.selectbox("Fornecedor", list(opcoes), format_func=opcoes.get)
        atual = next((f for f in forn if f["id"] == sel), {"nome": "", "cnpj": "", "contato": "", "ativo": 1})
        with st.form(f"forn_{sel}"):
            nome = st.text_input("Nome", atual["nome"])
            cnpj = st.text_input("CNPJ", atual["cnpj"])
            contato = st.text_input("Contato (telefone / e-mail)", atual["contato"])
            ativo = st.checkbox("Ativo", bool(atual["ativo"]))
            if st.form_submit_button("Salvar"):
                try:
                    db.salvar_fornecedor(nome, cnpj, contato, id_=sel or None, ativo=ativo)
                    recarregar()
                except ValueError as e:
                    st.error(str(e))
    with aba2:
        if not forn:
            st.info("Cadastre um fornecedor primeiro.")
        else:
            nomes = {f["id"]: f["nome"] for f in forn}
            fid = st.selectbox("Fornecedor", list(nomes), format_func=nomes.get, key="preco_forn")
            existentes = {p["fruta"]: p for p in db.listar_precos(fid)}
            frutas = sorted(set(db.frutas_conhecidas()) | set(existentes))
            base = pd.DataFrame({
                "Fruta": [db.nome_exibicao(f) for f in frutas],
                "Custo de compra (R$/un)": [existentes.get(f, {}).get("custo_unit", 0.0) for f in frutas],
                "Preço de venda (R$/un)": [existentes.get(f, {}).get("preco_unit", 0.0) for f in frutas]})
            ed = st.data_editor(base, hide_index=True, disabled=["Fruta"], key=f"precos_{fid}",
                                column_config={c: st.column_config.NumberColumn(c, min_value=0.0, step=0.05, format="%.2f")
                                               for c in base.columns[1:]})
            st.caption("Os preços valem para as próximas contagens. O histórico guarda o preço da época do registro.")
            if st.button("Salvar preços", type="primary"):
                inv = {db.nome_exibicao(f): f for f in frutas}
                for r in ed.itertuples(index=False):
                    f, custo, preco = inv[r[0]], float(r[1]), float(r[2])
                    if custo > 0 or preco > 0:
                        db.salvar_preco(fid, f, custo, preco)
                    elif f in existentes:
                        db.remover_preco(fid, f)
                st.success("Preços salvos.")
    with aba3:
        atual = float(db.get_config("limite_perda", "10"))
        novo = st.number_input("Limite de perda aceitável (%)", 0.0, 100.0, atual, 0.5,
                               help="Fornecedores acima deste valor aparecem em alerta no dashboard.")
        nome_emp = st.text_input("Nome da empresa", db.get_config("empresa", ""))
        if st.button("Salvar configurações"):
            db.set_config("limite_perda", novo)
            db.set_config("empresa", nome_emp)
            st.success("Configurações salvas.")
        st.divider()
        if st.button("Gerar dados de exemplo"):
            n = db.gerar_exemplo()
            st.success(f"{n} lotes de exemplo criados (origem = 'exemplo').")


# ------------------------------------------------------------ executar esteira
def _acompanhar_esteira():
    """Mostra o andamento. Roda sozinho a cada 2 s (st.fragment) enquanto a esteira está ativa."""
    rodando = lanc.em_execucao()
    if st.session_state.get("_esteira_rodava") and not rodando:
        st.session_state["_esteira_rodava"] = False
        recarregar()                                  # libera o formulário quando a esteira termina
    st.session_state["_esteira_rodava"] = rodando

    if rodando:
        st.info(f"Esteira em execução há {int(lanc.segundos_rodando())} s. A janela do vídeo abriu neste computador "
                "(para encerrar também dá para apertar **q** nela).")
        c1, c2, _ = st.columns([1.3, 1, 2])
        if c1.button("Encerrar e gravar contagem", type="primary"):
            lanc.pedir_parada()
        espera = lanc.segundos_desde_pedido()
        if espera:
            st.caption("Encerrando e gravando a contagem...")
            if espera > 15 and c2.button("Forçar parada"):
                lanc.forcar_parada()
                st.warning("Esteira interrompida à força. A contagem desta execução NÃO foi gravada.")
                recarregar()
    else:
        res = lanc.resultado()
        if res:
            if res["lote"]:
                st.success(f"Contagem gravada no lote #{res['lote']}. Veja o resultado no Dashboard.")
            elif res["codigo"] not in (0, None):
                st.error("A esteira terminou com erro (veja o registro abaixo).")
            else:
                st.warning("A esteira terminou sem gravar contagem" + (f": {res['erro_banco']}" if res["erro_banco"] else "."))
            if res["resumo"]:
                st.code(res["resumo"], language=None)
    log = lanc.ler_log(40)
    if log:
        with st.expander("Registro da esteira", expanded=bool(lanc.em_execucao())):
            st.code(log, language=None)
    if not hasattr(st, "fragment") and lanc.em_execucao():
        st.button("Atualizar")


if hasattr(st, "fragment"):
    _acompanhar_esteira = st.fragment(run_every=2)(_acompanhar_esteira)


def pagina_esteira():
    st.title("Executar esteira")
    forn = db.listar_fornecedores(somente_ativos=True)
    if not forn:
        st.info("Cadastre ao menos um fornecedor (menu *Fornecedores e preços*) antes de rodar a esteira.")
        return
    faltam = lanc.arquivos_faltando()
    if faltam:
        st.error("Faltam arquivos na pasta do programa: " + ", ".join(faltam) + ". Rode o treino_multiclasse.py antes.")
        return
    rodando = lanc.em_execucao()
    st.caption("A esteira abre a própria janela de vídeo **neste computador** (onde o app está rodando). "
               "Ao terminar, a contagem de cada vegetal é gravada no banco para o fornecedor escolhido.")

    nomes = {f["id"]: f["nome"] for f in forn}
    c1, c2 = st.columns(2)
    fid = c1.selectbox("Fornecedor", list(nomes), format_func=nomes.get, disabled=rodando)
    ref = c2.text_input("Referência (nota fiscal, nº da carga)", disabled=rodando)
    origem = st.radio("Origem das imagens", ["Vídeo", "Câmera (webcam)"], horizontal=True, disabled=rodando)

    video, camera, tempo_real = None, 0, False
    if origem == "Vídeo":
        achados = lanc.videos_disponiveis()
        outro = "Outro caminho..."
        escolhas = {p: os.path.basename(p) for p in achados} | {outro: outro}
        sel = st.selectbox("Vídeo", list(escolhas), format_func=escolhas.get, disabled=rodando,
                           help="Vídeos encontrados na pasta do programa e na subpasta videos/.")
        if sel == outro:
            video = st.text_input("Caminho completo do vídeo", placeholder=r"C:\videos\esteira.mp4",
                                  disabled=rodando).strip().strip('"')
        else:
            video = sel
        with st.expander("Enviar um vídeo novo"):
            arq = st.file_uploader("Arquivo de vídeo", type=["mp4", "avi", "mov", "mkv", "wmv"], disabled=rodando)
            if arq is not None and st.button("Salvar na pasta videos/"):
                st.success(f"Salvo em {lanc.salvar_video_enviado(arq.name, arq.getbuffer())}. Selecione-o na lista acima.")
        tempo_real = st.checkbox("Simular o ritmo real do vídeo (descarta quadros se o computador atrasar)",
                                 disabled=rodando)
    else:
        camera = st.number_input("Número da câmera", min_value=0, max_value=10, value=0, step=1, disabled=rodando,
                                 help="0 = webcam padrão. Se houver mais de uma câmera, tente 1, 2...")

    if st.button("Iniciar esteira", type="primary", disabled=rodando):
        try:
            lanc.iniciar(fid, "video" if origem == "Vídeo" else "camera", video=video, camera=int(camera),
                         referencia=ref, tempo_real=tempo_real)
            recarregar()
        except ValueError as e:
            st.error(str(e))
    st.divider()
    _acompanhar_esteira()


# --------------------------------------------------------------------- usuários
def pagina_usuarios():
    st.title("Usuários")
    us = db.listar_usuarios()
    mostrar_tabela(pd.DataFrame(us).rename(columns={"login": "Login", "nome": "Nome", "perfil": "Perfil", "ativo": "Ativo",
                                                    "criado_em": "Criado em"}).drop(columns="id"))
    st.caption("**admin**: tudo · **operador**: registra contagens e revisa · **visualizador**: só consulta o dashboard.")
    with st.form("novo_usuario", clear_on_submit=True):
        st.subheader("Novo usuário")
        login = st.text_input("Login")
        nome = st.text_input("Nome")
        perfil = st.selectbox("Perfil", list(db.PERFIS), index=1)
        senha = st.text_input("Senha inicial", type="password")
        if st.form_submit_button("Criar"):
            try:
                db.criar_usuario(login, nome, senha, perfil)
                st.success("Usuário criado.")
                recarregar()
            except ValueError as e:
                st.error(str(e))
    st.subheader("Ativar / desativar")
    logins = [u["login"] for u in us if u["login"] != st.session_state["usuario"]["login"]]
    if logins:
        alvo = st.selectbox("Usuário", logins)
        ativo_atual = next(u["ativo"] for u in us if u["login"] == alvo)
        if st.button("Desativar" if ativo_atual else "Reativar"):
            try:
                db.definir_usuario_ativo(alvo, not ativo_atual)
                recarregar()
            except ValueError as e:
                st.error(str(e))
    st.subheader("Redefinir senha")
    with st.form("reset"):
        alvo2 = st.selectbox("Usuário", [u["login"] for u in us], key="reset_user")
        nova = st.text_input("Nova senha", type="password")
        if st.form_submit_button("Redefinir"):
            try:
                db.alterar_senha(alvo2, nova)
                st.success("Senha alterada.")
            except ValueError as e:
                st.error(str(e))


def pagina_conta():
    u = st.session_state["usuario"]
    st.title("Minha conta")
    st.write(f"**{u['nome']}** · login `{u['login']}` · perfil **{u['perfil']}**")
    with st.form("trocar"):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password")
        rep = st.text_input("Repita a nova senha", type="password")
        if st.form_submit_button("Trocar senha"):
            if db.autenticar(u["login"], atual) is None:
                st.error("Senha atual incorreta.")
            elif nova != rep:
                st.error("As senhas não conferem.")
            else:
                try:
                    db.alterar_senha(u["login"], nova)
                    st.success("Senha alterada.")
                except ValueError as e:
                    st.error(str(e))


# ------------------------------------------------------------------------ main
def main():
    db.iniciar()
    if not db.tem_usuarios():
        tela_primeiro_acesso()
        return
    if "usuario" not in st.session_state:
        tela_login()
        return
    u = st.session_state["usuario"]
    paginas = PAGINAS_POR_PERFIL[u["perfil"]]
    with st.sidebar:
        st.markdown(f"### {db.get_config('empresa', 'Frutas')}")
        st.caption(f"{u['nome']} · {u['perfil']}")
        pagina = st.radio("Menu", paginas, label_visibility="collapsed")
        if st.button("Sair"):
            del st.session_state["usuario"]
            recarregar()
    {"Dashboard": pagina_dashboard, "Executar esteira": pagina_esteira, "Registrar contagem": pagina_registrar, "Lotes e revisão": pagina_lotes,
     "Fornecedores e preços": pagina_fornecedores, "Usuários": pagina_usuarios, "Minha conta": pagina_conta}[pagina]()


main()
