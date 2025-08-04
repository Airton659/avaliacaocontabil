# analises/por_tipo.py

import streamlit as st
import plotly.express as px
import pandas as pd

def mostrar_analise_por_tipo(df_long: pd.DataFrame):
    """
    Exibe análises agrupadas por "Tipo Conta Corrente Lançamento".
    - Gráfico de Pizza: Distribuição percentual em um mês.
    - Gráfico de Barras: Evolução mensal dos saldos por tipo.
    """
    st.subheader("📊 Análise por Tipo de Conta")

    # Garante que a coluna de tipo de conta não tenha valores nulos para a análise
    df_tipo = df_long.dropna(subset=["Tipo Conta Corrente Lançamento"])
    df_tipo = df_tipo[df_tipo["Tipo Conta Corrente Lançamento"].str.strip() != ""]

    if df_tipo.empty:
        st.warning("Não há dados de 'Tipo Conta Corrente Lançamento' para analisar.")
        return

    # --- Gráfico de Pizza ---
    st.markdown("#### 🍕 Distribuição Percentual por Tipo de Conta")
    
    meses_disponiveis = sorted(df_tipo["MesReferencia"].unique())
    # Formata os meses para exibição no selectbox
    meses_formatados = [pd.to_datetime(mes).strftime("%b/%Y") for mes in meses_disponiveis]
    
    mes_selecionado_str = st.selectbox(
        "Selecione o mês para o gráfico de pizza:",
        options=meses_formatados,
        index=len(meses_formatados) - 1  # Padrão para o último mês
    )
    
    # Converte a string do mês de volta para datetime para filtrar
    mes_selecionado = pd.to_datetime(mes_selecionado_str, format="%b/%Y")

    df_mes_filtrado = df_tipo[df_tipo["MesReferencia"] == mes_selecionado]

    if not df_mes_filtrado.empty:
        df_pizza = df_mes_filtrado.groupby("Tipo Conta Corrente Lançamento")["Saldo"].sum().reset_index()
        
        fig_pizza = px.pie(
            df_pizza,
            names="Tipo Conta Corrente Lançamento",
            values="Saldo",
            title=f"Distribuição de Saldo por Tipo de Conta em {mes_selecionado_str}"
        )
        st.plotly_chart(fig_pizza, use_container_width=True)
    else:
        st.info(f"Não há dados de saldo para o mês de {mes_selecionado_str}.")


    # --- Gráfico de Barras Agrupadas ---
    st.markdown("#### Evolução Mensal por Tipo de Conta")

    df_barras = df_tipo.groupby(["MesReferencia", "Tipo Conta Corrente Lançamento"])["Saldo"].sum().reset_index()
    df_barras["MesReferencia"] = df_barras["MesReferencia"].dt.strftime("%b/%Y")
    
    fig_barras = px.bar(
        df_barras,
        x="MesReferencia",
        y="Saldo",
        color="Tipo Conta Corrente Lançamento",
        title="Evolução Mensal do Saldo por Tipo de Conta",
        barmode="group"
    )
    
    fig_barras.update_layout(
        xaxis_title="Mês",
        yaxis_title="Saldo Total (R$)",
        legend_title="Tipo de Conta"
    )
    st.plotly_chart(fig_barras, use_container_width=True)