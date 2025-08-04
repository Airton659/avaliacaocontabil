# analises/variacao.py

import streamlit as st
import plotly.express as px
import pandas as pd

def mostrar_analise_variacao(df_long: pd.DataFrame) -> None:
    """
    Exibe as maiores variações (em tabelas) e o comparativo de saldos por mês/ano.
    """
    st.subheader("🔁 Variação Mês a Mês (Real)")
    st.markdown("Esta análise mostra a movimentação mensal real, calculada com base na diferença entre os saldos acumulados de meses consecutivos.")

    # Filtra dados válidos
    df_var = df_long.dropna(subset=["SaldoAnterior", "ValorMensal", "VariacaoPercentual"]).copy()
    df_var = df_var.replace([float("inf"), float("-inf")], pd.NA).dropna(subset=["VariacaoPercentual"])
    
    # Conversão explícita para garantir tipo numérico
    df_var["VariacaoPercentual"] = pd.to_numeric(df_var["VariacaoPercentual"], errors="coerce").fillna(0.0)
    df_var["ValorMensal"] = pd.to_numeric(df_var["ValorMensal"], errors="coerce").fillna(0.0)
    
    df_var = df_var[df_var["VariacaoPercentual"].abs() < 100000]

    # --- Análises de Variação (em tabelas) ---

    # 💰 Variações Absolutas > R$ 3 Milhões
    st.markdown("### 💰 Variações Absolutas > R$ 3 Milhões")
    variacoes_3milhoes = df_var[df_var["ValorMensal"].abs() > 3_000_000].sort_values("ValorMensal", ascending=False)
    
    if not variacoes_3milhoes.empty:
        st.dataframe(variacoes_3milhoes, use_container_width=True)
    else:
        st.info("Nenhuma conta teve variação absoluta superior a R$ 3 milhões neste período.")

    # 🔼 Variações Percentuais > 50%
    st.markdown("### 🔼 Variações Percentuais > 50%")
    variacoes_50_percent = df_var[df_var["VariacaoPercentual"].abs() > 50].sort_values("VariacaoPercentual", ascending=False)
    
    if not variacoes_50_percent.empty:
        st.dataframe(variacoes_50_percent, use_container_width=True)
    else:
        st.info("Nenhuma conta teve variação percentual superior a 50% neste período.")

    # --- Análise Comparativa de Saldos ---
    st.markdown("### 📅 Comparativo de Saldo Entre Dois Meses para uma Conta Específica")

    df_long["Conta Contábil"] = df_long["Conta Contábil"].astype(str)
    contas_opcoes = sorted(df_long["Conta Contábil"].unique())
    conta_escolhida = st.selectbox("Escolha a Conta Contábil:", contas_opcoes)

    meses_ordenados = sorted(df_long["MesReferencia"].dt.to_period('M').unique())
    meses_opcoes = [m.strftime("%b/%Y") for m in meses_ordenados]

    # Garante que os índices não sejam negativos se houver poucos meses
    index_1 = max(0, len(meses_opcoes) - 2)
    index_2 = max(0, len(meses_opcoes) - 1)

    mes_escolhido_1 = st.selectbox("Escolha o primeiro mês:", meses_opcoes, index=index_1)
    mes_escolhido_2 = st.selectbox("Escolha o segundo mês:", meses_opcoes, index=index_2)

    if mes_escolhido_1 and mes_escolhido_2 and conta_escolhida:
        df_comparativo = df_long[
            (df_long["Conta Contábil"] == conta_escolhida) &
            (df_long["MesReferencia"].dt.strftime("%b/%Y").isin([mes_escolhido_1, mes_escolhido_2]))
        ].copy()

        df_comparativo.sort_values("MesReferencia", inplace=True)
        df_comparativo['Mes/Ano'] = df_comparativo['MesReferencia'].dt.strftime('%b/%Y')

        if not df_comparativo.empty:
            fig_comparativo = px.bar(
                df_comparativo,
                x="Mes/Ano",
                y="Saldo",
                color="Mes/Ano",
                title=f"Comparativo de Saldo para a Conta {conta_escolhida}",
                labels={"Saldo": "Saldo (R$)", "Mes/Ano": "Mês de Referência"},
                text="Saldo"
            )
            fig_comparativo.update_layout(
                xaxis_title=None,
                yaxis_title="Saldo (R$)",
                hovermode="x unified",
                legend_title_text="Mês de Referência"
            )
            fig_comparativo.update_yaxes(tickprefix="R$ ")
            fig_comparativo.update_traces(texttemplate='R$%{text:,.2f}', textposition='outside')
            st.plotly_chart(fig_comparativo, use_container_width=True)
        else:
            st.info("Dados não encontrados para a conta e meses selecionados.")