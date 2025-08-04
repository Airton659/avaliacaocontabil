# analises/surgidas_zeradas.py

import streamlit as st
import pandas as pd

def mostrar_analise_surgidas_zeradas(df_long: pd.DataFrame):
    """
    Identifica e exibe contas que surgiram (saldo 0 -> não 0) ou
    foram zeradas (saldo não 0 -> 0) para um MÊS SELECIONADO pelo usuário.
    """
    st.subheader("🔄 Contas Surgidas e Zeradas por Mês")
    st.markdown("Selecione um mês para analisar as contas que iniciaram ou encerraram movimentação de saldo.")

    # Garante que as colunas necessárias não tenham valores nulos
    df_analise = df_long.dropna(subset=["SaldoAnterior", "Saldo", "MesReferencia"]).copy()

    # --- Filtro Interativo por Mês ---
    meses_disponiveis = sorted(df_analise["MesReferencia"].unique())
    # Formata os meses para exibição no selectbox
    meses_formatados = [pd.to_datetime(mes).strftime("%b/%Y") for mes in meses_disponiveis]
    
    # Remove o primeiro mês da lista, pois não há dados de "SaldoAnterior" para ele
    if meses_formatados:
        meses_para_selecao = meses_formatados[1:]
    else:
        meses_para_selecao = []

    if not meses_para_selecao:
        st.warning("Não há meses suficientes para realizar a comparação de contas surgidas/zeradas.")
        return

    mes_selecionado_str = st.selectbox(
        "Escolha o mês para a análise:",
        options=meses_para_selecao,
        index=len(meses_para_selecao) - 1,  # Padrão para o último mês disponível
        help="Esta análise compara o mês selecionado com o mês imediatamente anterior."
    )
    
    # Converte a string do mês de volta para datetime para filtrar
    mes_selecionado_dt = pd.to_datetime(mes_selecionado_str, format="%b/%Y")
    
    # Filtra o DataFrame para o mês selecionado
    df_mes = df_analise[df_analise["MesReferencia"] == mes_selecionado_dt]

    # --- Lógica de Identificação ---
    # Contas Surgidas: Saldo anterior era 0 e o atual não é.
    df_surgidas = df_mes[(df_mes["SaldoAnterior"] == 0) & (df_mes["Saldo"] != 0)]
    
    # Contas Zeradas: Saldo anterior não era 0 e o atual é.
    df_zeradas = df_mes[(df_mes["SaldoAnterior"] != 0) & (df_mes["Saldo"] == 0)]

    # --- Exibição dos resultados ---
    st.markdown(f"#### 🌱 Contas com Saldo Surgido em {mes_selecionado_str}")
    if not df_surgidas.empty:
        st.dataframe(
            df_surgidas[["Conta Contábil", "Saldo"]],
            use_container_width=True,
            column_config={
                "Conta Contábil": "Conta Contábil",
                "Saldo": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f")
            },
            hide_index=True
        )
    else:
        st.info(f"Nenhuma conta com saldo surgido foi identificada em {mes_selecionado_str}.")

    st.markdown(f"#### 💤 Contas com Saldo Zerado em {mes_selecionado_str}")
    if not df_zeradas.empty:
        st.dataframe(
            df_zeradas[["Conta Contábil", "SaldoAnterior"]],
            use_container_width=True,
            column_config={
                "Conta Contábil": "Conta Contábil",
                "SaldoAnterior": st.column_config.NumberColumn("Saldo do Mês Anterior", format="R$ %.2f")
            },
            hide_index=True
        )
    else:
        st.info(f"Nenhuma conta com saldo zerado foi identificada em {mes_selecionado_str}.")