# analises/temporal.py

import streamlit as st
import plotly.express as px

def mostrar_analise_temporal(df_long: "pd.DataFrame") -> None:
    """
    Exibe gráfico de evolução temporal de uma conta contábil.
    """
    st.subheader("📈 Análise Temporal")
    st.markdown("Selecione uma conta para visualizar a evolução ao longo do tempo.")

    contas = df_long["Conta Contábil"].dropna().unique()
    conta_selecionada = st.selectbox("🔎 Conta Contábil:", contas)

    df_filtrado = df_long[df_long["Conta Contábil"] == conta_selecionada]
    df_filtrado = df_filtrado.sort_values("MesReferencia")

    fig = px.line(
        df_filtrado,
        x="MesReferencia",
        y="Saldo",
        title=f"Evolução temporal da conta {conta_selecionada}",
        markers=True
    )

    fig.update_layout(
        xaxis=dict(
            tickformat="%b/%Y",
            tickmode="linear",
            dtick="M1"
        ),
        xaxis_title="Mês",
        yaxis_title="Saldo (R$)",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)
