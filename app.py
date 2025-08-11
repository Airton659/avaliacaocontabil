# contas_dashboard_streamlit.py
# -*- coding: utf-8 -*-
# Regras:
# - NUNCA agrega CO_TP_CCOR diferentes. Cada série/linha é (Conta, CO_TP_CCOR).
# - Mês 0 aparece nas tabelas; fica fora de KPIs e gráficos.
# - Matriz cronológica não substitui ausentes por zero (vazio != zero).
# - Abas SURGIU/ZEROU expandidas por tipo; função de expansão preserva colunas de referência.
# - Navegação na lateral; filtros dentro de cada página.

import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# ----------------------
# Config & Constantes
# ----------------------
st.set_page_config(page_title="Painel Contábil", layout="wide")

# DADOS (nomes da sua planilha)
COL_ID_CONTA = "ID_CONTA_CONTABIL"
COL_NO_CONTA = "NO_CONTA_CONTABIL"
COL_ANO = "ID_ANO_LANC"
COL_MES = "ID_MES_LANC"
COL_DATA = "DATA"  # só p/ meses válidos
COL_SALDO = "SALDORCONTACONTBIL"
COL_MES_TXT = "SG_MES_COMPLETO"

# Tipificação
COL_ID_TP = "ID_TP_CCOR"
COL_CO_TP = "CO_TP_CCOR"
COL_NO_TP = "NO_TP_CCOR"

# EVENTOS
EV_ANT_ANO = "ANO_ANTERIOR"
EV_ANT_MES = "MES_ANTERIOR"
EV_SEG_ANO = "ANO_SEGUINTE"
EV_SEG_MES = "MES_SEGUINTE"
EV_SALDO_ANT = "SALDO_ANTERIOR"  # só em SURGIU

# ----------------------
# Helpers
# ----------------------
def format_brl(value) -> str:
    """Formata números como Real: R$ 1.234.567,89"""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "-"
    neg = x < 0
    x = abs(x)
    inteiro, decimal = divmod(round(x * 100), 100)
    inteiro_str = f"{int(inteiro):,}".replace(",", ".")
    decimal_str = f"{int(decimal):02d}"
    s = f"R$ {inteiro_str},{decimal_str}"
    return f"-{s}" if neg else s

def as_text_no_sep(series):
    """Converte números para texto sem separadores (evita 2,025 etc.)."""
    def fmt(v):
        try:
            if pd.isna(v):
                return ""
            iv = int(v)
            if float(v) == iv:
                return str(iv)
        except Exception:
            pass
        return str(v)
    return series.apply(fmt)

def month_label(dt: pd.Timestamp) -> str:
    """Ex.: 2025-08-01 -> 'Ago/2025'"""
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    return f"{meses[dt.month-1]}/{dt.year}"

def build_month_slider_options(df_mes_valido: pd.DataFrame):
    """Retorna (lista_de_datas, lista_de_labels). Usa apenas meses válidos (DATA)."""
    if df_mes_valido[COL_DATA].notna().any():
        datas = sorted(pd.to_datetime(df_mes_valido[COL_DATA].dropna().unique()).tolist())
        labels = [month_label(d) for d in datas]
        return datas, labels
    return [], []

@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes):
    with io.BytesIO(file_bytes) as buffer:
        dados = pd.read_excel(buffer, sheet_name="DADOS")
        surg = pd.read_excel(buffer, sheet_name="SALDO-SURGIU")
        zerou = pd.read_excel(buffer, sheet_name="SALDO-ZEROU")
    return dados, surg, zerou

def ensure_datetime_and_flags(dados: pd.DataFrame) -> pd.DataFrame:
    """Cria MES_VALIDO (1..12) e DATA só para meses válidos; mantém mês 0 nas tabelas."""
    y = pd.to_numeric(dados.get(COL_ANO, pd.Series(dtype="float")), errors="coerce")
    m = pd.to_numeric(dados.get(COL_MES, pd.Series(dtype="float")), errors="coerce")
    dados["MES_VALIDO"] = m.between(1, 12)
    dados[COL_DATA] = pd.NaT
    mask_valid = y.notna() & m.notna() & dados["MES_VALIDO"]
    if mask_valid.any():
        yy = y[mask_valid].astype(int)
        mm = m[mask_valid].astype(int)
        dados.loc[mask_valid, COL_DATA] = pd.to_datetime(dict(year=yy, month=mm, day=1), errors="coerce")
    qtd_m0 = int((m == 0).sum())
    if qtd_m0 > 0:
        st.info(f"ℹ️ {qtd_m0} linha(s) com mês = 0. Elas aparecem nas tabelas, mas ficam fora de KPIs e gráficos.")
    return dados

def name_map(dados: pd.DataFrame) -> pd.DataFrame:
    return (
        dados[[COL_ID_CONTA, COL_NO_CONTA]]
        .dropna()
        .drop_duplicates(subset=[COL_ID_CONTA], keep="last")
    )

def enrich_event_sheet(event_df: pd.DataFrame, nm: pd.DataFrame) -> pd.DataFrame:
    if COL_ID_CONTA not in event_df.columns:
        st.warning("A planilha de evento não possui a coluna ID_CONTA_CONTABIL.")
    return event_df.merge(nm, on=COL_ID_CONTA, how="left")

def tipo_rotulo(co, no) -> str:
    if pd.isna(co) and pd.isna(no):
        return "(tipo desconhecido)"
    if pd.isna(no):
        return f"{int(co)}"
    if pd.isna(co):
        return str(no)
    return f"{int(co)} - {no}"

def conta_tipo_label(conta, co, no) -> str:
    return f"{conta} | {tipo_rotulo(co, no)}"

def build_month_order_labels(dados: pd.DataFrame) -> list:
    """Ordena SG_MES_COMPLETO por (ANO, MES_ORDER) com mês 0 vindo antes de jan."""
    if all(c in dados.columns for c in [COL_ANO, COL_MES, COL_MES_TXT]):
        tmp = dados[[COL_ANO, COL_MES, COL_MES_TXT]].dropna(subset=[COL_ANO, COL_MES]).drop_duplicates()
        tmp["MES_ORDER"] = np.where(tmp[COL_MES] == 0, -1, tmp[COL_MES])
        tmp.sort_values([COL_ANO, "MES_ORDER"], inplace=True)
        return tmp[COL_MES_TXT].tolist()
    return []

def parse_co_from_label(label: str):
    """Extrai CO_TP_CCOR numérico de um rótulo 'CO - NO' quando possível."""
    if " - " in label:
        head = label.split(" - ")[0]
        return int(head) if head.isdigit() else None
    return None

def add_valor_fmt(df: pd.DataFrame, value_col: str = COL_SALDO):
    """Adiciona coluna VALOR_FMT em BRL para usar no hover de gráficos."""
    df = df.copy()
    df["VALOR_FMT"] = df[value_col].apply(format_brl)
    return df

def apply_hover_brl(fig):
    """Hover mostra BRL e oculta extra."""
    fig.update_traces(hovertemplate="%{text}<extra></extra>")
    return fig

def expandir_eventos_por_tipo(event_df: pd.DataFrame, usar_mes: str) -> pd.DataFrame:
    """
    Retorna tabela expandida em (Conta, Tipo) para o período do evento.
    usar_mes: "seguinte" -> join com (ANO_SEGUINTE, MES_SEGUINTE)
              "anterior" -> join com (ANO_ANTERIOR, MES_ANTERIOR)
    Preserva SEMPRE as colunas de referência (ANTERIOR e SEGUINTE).
    """
    keep_cols = [COL_ID_CONTA, COL_NO_CONTA, EV_SEG_ANO, EV_SEG_MES, EV_ANT_ANO, EV_ANT_MES]
    keep_cols = [c for c in keep_cols if c in event_df.columns]
    eventos = event_df[keep_cols].copy()

    if usar_mes == "seguinte":
        ycol, mcol = EV_SEG_ANO, EV_SEG_MES
    else:
        ycol, mcol = EV_ANT_ANO, EV_ANT_MES

    eventos = eventos.rename(columns={ycol: "ANO_EVT", mcol: "MES_EVT"})

    j = eventos.merge(
        dados_analise_base[[COL_ID_CONTA, COL_CO_TP, COL_NO_TP, COL_ANO, COL_MES, COL_SALDO]],  # meses válidos
        left_on=[COL_ID_CONTA, "ANO_EVT", "MES_EVT"],
        right_on=[COL_ID_CONTA, COL_ANO, COL_MES],
        how="left"
    )
    j["TIPO_ROT"] = j.apply(lambda r: tipo_rotulo(r.get(COL_CO_TP), r.get(COL_NO_TP)), axis=1)
    return j

# ----------------------
# UI (upload + navegação lateral)
# ----------------------
st.title("📊 Painel Contábil (Streamlit)")
st.caption("Sem agregação entre CO_TP_CCOR. Mês 0 fora de KPIs/gráficos; visível nas tabelas.")

uploaded = st.file_uploader("📎 Envie o arquivo Excel", type=["xlsx", "xls"])
if not uploaded:
    st.info("🔼 Envie o arquivo para iniciar.")
    st.stop()

dados, surg_raw, zerou_raw = load_excel(uploaded.read())

# Preparação base
dados = ensure_datetime_and_flags(dados)
dados_analise_base = dados[dados["MES_VALIDO"]].copy()   # só meses válidos (para KPIs/gráficos)
dados_tabela  = dados.copy()                              # todas as linhas (inclui mês 0) para tabelas
if dados_analise_base[COL_DATA].notna().any():
    dados_analise_base.sort_values(COL_DATA, inplace=True)

nm = name_map(dados)
surg = enrich_event_sheet(surg_raw.copy(), nm)
zerou = enrich_event_sheet(zerou_raw.copy(), nm)

# Navegação lateral
page = st.sidebar.radio(
    "Navegação",
    ["Visão Geral da Conta", "Análise Comparativa", "Matriz Cronológica", "Saldo Surgiu", "Saldo Zerou"]
)

# ----------------------
# PÁGINA: Visão Geral da Conta
# ----------------------
if page == "Visão Geral da Conta":
    st.subheader("🔎 Visão Geral da Conta")

    # Período por MÊS (select_slider com labels tipo Jan/2024)
    datas_opts, labels_opts = build_month_slider_options(dados_analise_base)
    if datas_opts:
        v0, v1 = st.select_slider(
            "Período (mensal)",
            options=datas_opts,
            format_func=lambda d: month_label(pd.to_datetime(d)),
            value=(datas_opts[0], datas_opts[-1]),
        )
        mask = (dados_analise_base[COL_DATA] >= v0) & (dados_analise_base[COL_DATA] <= v1)
        dados_analise = dados_analise_base[mask].copy()
    else:
        dados_analise = dados_analise_base.copy()

    contas = sorted(dados_tabela[COL_NO_CONTA].dropna().unique().tolist())
    conta_sel = st.selectbox("Conta", options=contas, index=0 if contas else None)

    if conta_sel:
        tipos_conta = (
            dados_tabela.loc[dados_tabela[COL_NO_CONTA] == conta_sel, [COL_CO_TP, COL_NO_TP]]
            .drop_duplicates()
            .sort_values(COL_CO_TP, na_position="last")
        )
        if len(tipos_conta) == 0:
            st.warning("Conta sem CO_TP_CCOR informado.")
        else:
            opts = [tipo_rotulo(r[COL_CO_TP], r[COL_NO_TP]) for _, r in tipos_conta.iterrows()]
            tipo_sel_label = opts[0] if len(opts) == 1 else st.selectbox("CO_TP_CCOR (obrigatório quando houver mais de um)", options=opts)
            co_sel = parse_co_from_label(tipo_sel_label)

            base_pair = dados_analise[(dados_analise[COL_NO_CONTA] == conta_sel) & (dados_analise[COL_CO_TP] == co_sel)].copy()
            base_pair = base_pair.groupby(COL_DATA, as_index=False)[COL_SALDO].sum()

            if base_pair.empty:
                st.warning("Sem dados (com mês válido) para esse par Conta/Tipo no período.")
            else:
                saldo_recente = base_pair.iloc[-1][COL_SALDO]
                pico_saldo = base_pair[COL_SALDO].max()
                variacao_total = base_pair.iloc[-1][COL_SALDO] - base_pair.iloc[0][COL_SALDO]
                c1, c2, c3 = st.columns(3)
                c1.metric("Saldo Mais Recente", format_brl(saldo_recente))
                c2.metric("Pico de Saldo", format_brl(pico_saldo))
                c3.metric("Variação Total no Período", format_brl(variacao_total))

                no_tp = tipos_conta.set_index(COL_CO_TP).loc[co_sel, COL_NO_TP] if co_sel in tipos_conta[COL_CO_TP].values else ""
                titulo = f"Evolução do Saldo — {conta_tipo_label(conta_sel, co_sel, no_tp)}"
                chart_df = add_valor_fmt(base_pair, COL_SALDO)
                fig = px.line(chart_df, x=COL_DATA, y=COL_SALDO, text="VALOR_FMT", title=titulo, markers=True)
                fig.update_layout(xaxis_title="Data", yaxis_title="Saldo", legend_title=None)
                fig.update_traces(mode="lines+markers+text", textposition="top center", textfont_size=12)
                fig = apply_hover_brl(fig)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecione uma conta.")

# ----------------------
# PÁGINA: Análise Comparativa
# ----------------------
elif page == "Análise Comparativa":
    st.subheader("📈 Análise Comparativa")

    datas_opts, labels_opts = build_month_slider_options(dados_analise_base)
    if datas_opts:
        v0, v1 = st.select_slider(
            "Período (mensal)",
            options=datas_opts,
            format_func=lambda d: month_label(pd.to_datetime(d)),
            value=(datas_opts[0], datas_opts[-1]),
            key="cmp_period"
        )
        mask = (dados_analise_base[COL_DATA] >= v0) & (dados_analise_base[COL_DATA] <= v1)
        dados_analise = dados_analise_base[mask].copy()
    else:
        dados_analise = dados_analise_base.copy()

    pares = (
        dados_tabela[[COL_NO_CONTA, COL_CO_TP, COL_NO_TP]]
        .dropna(subset=[COL_NO_CONTA, COL_CO_TP])
        .drop_duplicates()
    )
    pares["LABEL"] = pares.apply(lambda r: conta_tipo_label(r[COL_NO_CONTA], r[COL_CO_TP], r[COL_NO_TP]), axis=1)

    sel = st.multiselect(
        "Selecione de 2 a 5 pares (Conta | CO_TP_CCOR – NO_TP_CCOR)",
        options=sorted(pares["LABEL"].tolist())
    )
    if sel and len(sel) > 5:
        st.warning("Selecione no máximo 5 pares. Considerando apenas os 5 primeiros.")
        sel = sel[:5]

    if not sel or len(sel) < 2:
        st.info("Selecione pelo menos 2 pares para comparar.")
    else:
        pares_sel = pares[pares["LABEL"].isin(sel)]
        base = dados_analise.merge(pares_sel[[COL_NO_CONTA, COL_CO_TP, "LABEL"]], on=[COL_NO_CONTA, COL_CO_TP], how="inner")
        if base.empty:
            st.warning("Sem dados no período selecionado para os pares escolhidos.")
        else:
            grp = base.groupby(["LABEL", COL_DATA], as_index=False)[COL_SALDO].sum()
            chart_df = add_valor_fmt(grp, COL_SALDO)
            fig = px.line(chart_df, x=COL_DATA, y=COL_SALDO, color="LABEL", text="VALOR_FMT",
                          title="Comparativo (uma série por Conta | Tipo)", markers=True)
            fig.update_layout(xaxis_title="Data", yaxis_title="Saldo", legend_title="")
            fig.update_traces(mode="lines+markers+text", textposition="top center", textfont_size=11)
            fig = apply_hover_brl(fig)
            st.plotly_chart(fig, use_container_width=True)

# ----------------------
# PÁGINA: Matriz Cronológica
# ----------------------
elif page == "Matriz Cronológica":
    st.subheader("🧮 Matriz Cronológica (Pivot) — linhas por Conta | Tipo (sem agregação entre tipos)")

    # Filtro por 1 a 5 contas
    contas = sorted(dados_tabela[COL_NO_CONTA].dropna().unique().tolist())
    contas_sel = st.multiselect("Contas (1 a 5)", options=contas)
    if contas_sel and len(contas_sel) > 5:
        st.warning("Selecione no máximo 5 contas. Considerando apenas as 5 primeiras.")
        contas_sel = contas_sel[:5]

    if contas_sel:
        base_tab = dados_tabela[dados_tabela[COL_NO_CONTA].isin(contas_sel)].copy()
    else:
        base_tab = dados_tabela.copy()

    ordem_labels = build_month_order_labels(base_tab)
    if ordem_labels:
        cat_type = pd.CategoricalDtype(categories=ordem_labels, ordered=True)
        with pd.option_context("mode.chained_assignment", None):
            base_tab[COL_MES_TXT] = base_tab[COL_MES_TXT].astype(cat_type)

    df_rows = base_tab.copy()
    df_rows["ROW"] = df_rows.apply(lambda r: conta_tipo_label(r[COL_NO_CONTA], r[COL_CO_TP], r[COL_NO_TP]), axis=1)

    pivot_vals = pd.pivot_table(
        df_rows,
        index="ROW",
        columns=COL_MES_TXT if COL_MES_TXT in df_rows.columns else COL_DATA,
        values=COL_SALDO,
        aggfunc="sum"   # agrega apenas duplicatas do MESMO par
        # sem fill_value -> ausentes ficam NaN (vazio != zero)
    )

    pivot_fmt = pivot_vals.applymap(lambda v: format_brl(v) if pd.notna(v) else "-")
    nan_mask = pivot_vals.isna()
    def _style(_):
        return np.where(nan_mask.values, "background-color:#f6f6f6; color:#888;", "")
    st.dataframe(pivot_fmt.style.apply(_style, axis=None), use_container_width=True)

    # Diagnóstico: linhas com alguns "-" (para você verificar na prática)
    with st.expander("🔎 Linhas com células vazias (mostrar até 100)"):
        # lista meses/colunas com NaN
        empties = []
        for i, row in pivot_vals.iterrows():
            cols_na = row[row.isna()].index.tolist()
            if cols_na:
                empties.append({"Conta | Tipo": i, "Meses sem registro": ", ".join(map(str, cols_na))})
        if empties:
            diag = pd.DataFrame(empties)[:100]
            st.dataframe(diag, use_container_width=True)
            st.caption(f"Total de linhas com ao menos uma célula vazia: {len(empties)}")
        else:
            st.info("Não encontrei células vazias nesta seleção. Selecione outras contas para verificar.")

# ----------------------
# PÁGINA: Saldo Surgiu
# ----------------------
elif page == "Saldo Surgiu":
    st.subheader("🟢 Saldo Surgiu (Fonte: SALDO-SURGIU) — sem agregação entre tipos")

    if all(c in surg.columns for c in [EV_SEG_ANO, EV_SEG_MES]):
        anos = sorted(surg[EV_SEG_ANO].dropna().astype(int).unique().tolist())
        meses = sorted(surg[EV_SEG_MES].dropna().astype(int).unique().tolist())
        c1, c2 = st.columns(2)
        ano_sel = c1.selectbox("Ano do evento (SEGUINTE)", options=anos, index=len(anos)-1 if anos else 0)
        mes_sel = c2.selectbox("Mês do evento (SEGUINTE)", options=meses, index=len(meses)-1 if meses else 0)

        base_evt = surg[(surg[EV_SEG_ANO] == ano_sel) & (surg[EV_SEG_MES] == mes_sel)].copy()
        if base_evt.empty:
            st.info("Sem registros para esse período.")
        else:
            exp = expandir_eventos_por_tipo(base_evt, usar_mes="seguinte")
            exp.rename(columns={COL_SALDO: "VALOR_QUE_SURGIU"}, inplace=True)

            qtd = len(exp)
            total_valor = exp["VALOR_QUE_SURGIU"].sum(skipna=True)
            k1, k2 = st.columns(2)
            k1.metric("Qtd. (Conta, Tipo)", f"{qtd}")
            k2.metric("Valor Total que Surgiu", format_brl(total_valor))

            cols_tab = [COL_NO_CONTA, "TIPO_ROT", "VALOR_QUE_SURGIU"]
            if EV_ANT_MES in exp.columns: cols_tab.append(EV_ANT_MES)
            if EV_ANT_ANO in exp.columns: cols_tab.append(EV_ANT_ANO)
            tabela = exp[cols_tab].copy()
            tabela["VALOR_QUE_SURGIU"] = tabela["VALOR_QUE_SURGIU"].apply(format_brl)
            if EV_ANT_MES in tabela.columns: tabela[EV_ANT_MES] = as_text_no_sep(tabela[EV_ANT_MES])
            if EV_ANT_ANO in tabela.columns: tabela[EV_ANT_ANO] = as_text_no_sep(tabela[EV_ANT_ANO])

            ren = {COL_NO_CONTA: "Conta", "TIPO_ROT": "CO_TP_CCOR"}
            if EV_ANT_MES in tabela.columns: ren[EV_ANT_MES] = "Mês Anterior Ref."
            if EV_ANT_ANO in tabela.columns: ren[EV_ANT_ANO] = "Ano Anterior Ref."
            tabela.rename(columns=ren, inplace=True)
            st.dataframe(tabela, use_container_width=True)

            st.markdown("#### 🔍 Investigação (Histórico do Par Conta/Tipo)")
            pares_evt = tabela.copy()
            pares_evt["LABEL"] = pares_evt["Conta"] + " | " + pares_evt["CO_TP_CCOR"]
            escolha = st.selectbox("Selecione um (Conta | Tipo)", options=sorted(pares_evt["LABEL"].unique().tolist()))
            if escolha:
                conta_escolhida, tipo_escolhido = escolha.split(" | ", 1)
                co_tp = parse_co_from_label(tipo_escolhido)
                base_ok = dados_analise_base[(dados_analise_base[COL_NO_CONTA] == conta_escolhida) & (dados_analise_base[COL_CO_TP] == co_tp)]
                grp = base_ok.groupby(COL_DATA, as_index=False)[COL_SALDO].sum()
                if grp.empty:
                    st.info("Sem meses válidos para traçar o gráfico deste par.")
                else:
                    chart_df = add_valor_fmt(grp, COL_SALDO)
                    titulo = f"Histórico — {conta_tipo_label(conta_escolhida, co_tp, None)}"
                    fig = px.line(chart_df, x=COL_DATA, y=COL_SALDO, text="VALOR_FMT", markers=True, title=titulo)
                    fig.update_layout(xaxis_title="Data", yaxis_title="Saldo")
                    fig.update_traces(mode="lines+markers+text", textposition="top center", textfont_size=12)
                    fig = apply_hover_brl(fig)
                    st.plotly_chart(fig, use_container_width=True)

                hist_tab = dados_tabela[(dados_tabela[COL_NO_CONTA] == conta_escolhida) & (dados_tabela[COL_CO_TP] == co_tp)][[COL_ANO, COL_MES, COL_SALDO]].sort_values([COL_ANO, COL_MES]).copy()
                hist_tab["Saldo"] = hist_tab[COL_SALDO].apply(format_brl)
                hist_tab["Ano"] = as_text_no_sep(hist_tab[COL_ANO])
                hist_tab["Mês"] = as_text_no_sep(hist_tab[COL_MES])
                st.dataframe(hist_tab[["Ano", "Mês", "Saldo"]], hide_index=True, use_container_width=True)
    else:
        st.warning("SALDO-SURGIU sem colunas esperadas (ANO/MÊS SEGUINTE).")

# ----------------------
# PÁGINA: Saldo Zerou
# ----------------------
elif page == "Saldo Zerou":
    st.subheader("🔴 Saldo Zerou (Fonte: SALDO-ZEROU) — sem agregação entre tipos")

    if all(c in zerou.columns for c in [EV_SEG_ANO, EV_SEG_MES, EV_ANT_ANO, EV_ANT_MES]):
        anos = sorted(zerou[EV_SEG_ANO].dropna().astype(int).unique().tolist())
        meses = sorted(zerou[EV_SEG_MES].dropna().astype(int).unique().tolist())
        c1, c2 = st.columns(2)
        ano_sel = c1.selectbox("Ano do evento (SEGUINTE)", options=anos, index=len(anos)-1 if anos else 0)
        mes_sel = c2.selectbox("Mês do evento (SEGUINTE)", options=meses, index=len(meses)-1 if meses else 0)

        base_evt = zerou[(zerou[EV_SEG_ANO] == ano_sel) & (zerou[EV_SEG_MES] == mes_sel)].copy()
        if base_evt.empty:
            st.info("Sem registros para esse período.")
        else:
            exp_ant = expandir_eventos_por_tipo(base_evt, usar_mes="anterior")
            exp_ant.rename(columns={COL_SALDO: "VALOR_QUE_ZEROU"}, inplace=True)

            qtd = len(exp_ant)
            total_valor = exp_ant["VALOR_QUE_ZEROU"].sum(skipna=True)
            k1, k2 = st.columns(2)
            k1.metric("Qtd. (Conta, Tipo)", f"{qtd}")
            k2.metric("Valor Total que Zerou", format_brl(total_valor))

            cols_tab = [COL_NO_CONTA, "TIPO_ROT", "VALOR_QUE_ZEROU", EV_SEG_MES, EV_SEG_ANO]
            cols_tab = [c for c in cols_tab if c in exp_ant.columns]
            tabela = exp_ant[cols_tab].copy()
            tabela["VALOR_QUE_ZEROU"] = tabela["VALOR_QUE_ZEROU"].apply(format_brl)
            if EV_SEG_MES in tabela.columns: tabela[EV_SEG_MES] = as_text_no_sep(tabela[EV_SEG_MES])
            if EV_SEG_ANO in tabela.columns: tabela[EV_SEG_ANO] = as_text_no_sep(tabela[EV_SEG_ANO])
            tabela.rename(columns={
                COL_NO_CONTA: "Conta",
                "TIPO_ROT": "CO_TP_CCOR",
                EV_SEG_MES: "Mês Seguinte Ref.",
                EV_SEG_ANO: "Ano Seguinte Ref."
            }, inplace=True)
            st.dataframe(tabela, use_container_width=True)

            st.markdown("#### 🔍 Investigação (Histórico do Par Conta/Tipo)")
            pares_evt = tabela.copy()
            pares_evt["LABEL"] = pares_evt["Conta"] + " | " + pares_evt["CO_TP_CCOR"]
            escolha = st.selectbox("Selecione um (Conta | Tipo)", options=sorted(pares_evt["LABEL"].unique().tolist()))
            if escolha:
                conta_escolhida, tipo_escolhido = escolha.split(" | ", 1)
                co_tp = parse_co_from_label(tipo_escolhido)
                base_ok = dados_analise_base[(dados_analise_base[COL_NO_CONTA] == conta_escolhida) & (dados_analise_base[COL_CO_TP] == co_tp)]
                grp = base_ok.groupby(COL_DATA, as_index=False)[COL_SALDO].sum()
                if grp.empty:
                    st.info("Sem meses válidos para traçar o gráfico deste par.")
                else:
                    chart_df = add_valor_fmt(grp, COL_SALDO)
                    titulo = f"Histórico — {conta_tipo_label(conta_escolhida, co_tp, None)}"
                    fig = px.line(chart_df, x=COL_DATA, y=COL_SALDO, text="VALOR_FMT", markers=True, title=titulo)
                    fig.update_layout(xaxis_title="Data", yaxis_title="Saldo")
                    fig.update_traces(mode="lines+markers+text", textposition="top center", textfont_size=12)
                    fig = apply_hover_brl(fig)
                    st.plotly_chart(fig, use_container_width=True)

                hist_tab = dados_tabela[(dados_tabela[COL_NO_CONTA] == conta_escolhida) & (dados_tabela[COL_CO_TP] == co_tp)][[COL_ANO, COL_MES, COL_SALDO]].sort_values([COL_ANO, COL_MES]).copy()
                hist_tab["Saldo"] = hist_tab[COL_SALDO].apply(format_brl)
                hist_tab["Ano"] = as_text_no_sep(hist_tab[COL_ANO])
                hist_tab["Mês"] = as_text_no_sep(hist_tab[COL_MES])
                st.dataframe(hist_tab[["Ano", "Mês", "Saldo"]], hide_index=True, use_container_width=True)
    else:
        st.warning("SALDO-ZEROU sem colunas esperadas (ANO/MÊS SEGUINTE e ANTERIOR).")

st.caption("Feito com ❤️ em Streamlit. Regras: mês 0 fora das análises; cada série é um par (Conta, CO_TP_CCOR); vazio != zero.")
