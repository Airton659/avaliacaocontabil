# analises/surgidas_zeradas.py

import streamlit as st
import pandas as pd

def mostrar_analise_surgidas_zeradas(df_long: pd.DataFrame):
    """
    Identifica contas "nascidas" (saldo anterior não existia) e
    "zeradas" (saldo anterior existia e o atual é zero).
    """
    st.subheader("🔄 Contas Surgidas e Zeradas por Mês")
    st.markdown("Análise de contas que iniciaram ou encerraram movimentação de saldo.")

    meses_disponiveis = sorted(df_long["MesReferencia"].unique())
    meses_formatados = [pd.to_datetime(mes).strftime("%b/%Y") for mes in meses_disponiveis]
    
    # Remove o primeiro mês, pois ele não tem dados anteriores para comparação
    if len(meses_formatados) > 1:
        meses_para_selecao = meses_formatados[1:]
    else:
        st.warning("É necessário ter pelo menos dois meses de dados para esta análise.")
        return

    mes_selecionado_str = st.selectbox(
        "Escolha o mês para a análise:",
        options=meses_para_selecao,
        index=len(meses_para_selecao) - 1
    )
    
    mes_selecionado_dt = pd.to_datetime(mes_selecionado_str, format="%b/%Y")
    df_mes = df_long[df_long["MesReferencia"] == mes_selecionado_dt]

    # LÓGICA CORRETA: "Nascida" -> Saldo anterior é NaN (vazio)
    df_surgidas = df_mes[df_mes["SaldoAnterior"].isna()]
    
    # LÓGICA CORRETA: "Zerada" -> Saldo anterior era um número e o saldo atual é 0
    df_zeradas = df_mes[df_mes["SaldoAnterior"].notna() & (df_mes["Saldo"] == 0)]

    st.markdown(f"#### 🌱 Contas Surgidas em {mes_selecionado_str}")
    st.info("Contas que não tinham registro no mês anterior e passaram a ter neste mês.")
    if not df_surgidas.empty:
        st.dataframe(df_surgidas[["Conta Contábil", "Saldo"]], use_container_width=True, hide_index=True)
    else:
        st.success(f"Nenhuma conta nova foi identificada em {mes_selecionado_str}.")

    st.markdown(f"#### 💤 Contas Zeradas em {mes_selecionado_str}")
    st.info("Contas que tinham saldo no mês anterior e foram zeradas neste mês.")
    if not df_zeradas.empty:
        st.dataframe(df_zeradas[["Conta Contábil", "SaldoAnterior"]], use_container_width=True, hide_index=True)
    else:
        st.success(f"Nenhuma conta foi zerada em {mes_selecionado_str}.")