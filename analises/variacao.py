# analises/variacao.py

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def mostrar_analise_variacao(df_long: pd.DataFrame) -> None:
    """
    Exibe as maiores variações (em tabelas) e o comparativo de saldos por mês/ano,
    com a formatação numérica e de percentual correta.
    """
    st.subheader("🔁 Variação Mês a Mês (Real)")
    st.markdown("Esta análise mostra a movimentação mensal real, calculada com base na diferença entre os saldos acumulados de meses consecutivos.")

    df_var = df_long.dropna(subset=["SaldoAnterior", "ValorMensal"]).copy()
    
    # --- FUNÇÕES DE FORMATAÇÃO ---
    def formatar_br_final(valor):
        try:
            num = float(valor)
            s_valor = f"{num:.2f}"
            partes = s_valor.split('.')
            inteiro = partes[0]
            decimal = partes[1]
            sinal = ""
            if inteiro.startswith('-'):
                sinal = "-"
                inteiro = inteiro[1:]
            inteiro_reverso = inteiro[::-1]
            inteiro_com_pontos_reverso = '.'.join(inteiro_reverso[i:i+3] for i in range(0, len(inteiro_reverso), 3))
            inteiro_formatado = inteiro_com_pontos_reverso[::-1]
            return f"{sinal}{inteiro_formatado},{decimal}"
        except (ValueError, TypeError):
            return ""

    # A função 'formatar_percentual_com_limite' foi removida.

    # --- Variações Absolutas > R$ 3 Milhões ---
    st.markdown("### 💰 Variações Absolutas > R$ 3 Milhões")
    variacoes_3milhoes = df_var[df_var["ValorMensal"].abs() > 3_000_000].sort_values("ValorMensal", ascending=False)

    if not variacoes_3milhoes.empty:
        display_3m = variacoes_3milhoes.copy()
        
        colunas_moeda = ['ValorMensal', 'Saldo', 'SaldoAnterior']
        for col in colunas_moeda:
            display_3m[col] = display_3m[col].apply(formatar_br_final)
            
        display_3m['MesReferencia'] = display_3m['MesReferencia'].dt.strftime('%b/%Y')
        
        # A linha que aplicava a formatação na 'VariacaoPercentual' foi removida.
        
        st.dataframe(
            display_3m,
            column_config={
                # Usamos NumberColumn para formatar o número como percentual.
                "VariacaoPercentual": st.column_config.NumberColumn(
                    "Variação (%)",
                    format="%.2f%%"
                ),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma conta teve variação absoluta superior a R$ 3 milhões neste período.")


    # --- Variações Percentuais > 50% ---
    st.markdown("### 🔼 Variações Percentuais > 50%")
    variacoes_percentuais = df_var.copy()
    variacoes_percentuais = variacoes_percentuais[variacoes_percentuais["VariacaoPercentual"].abs() > 50]
    
    if not variacoes_percentuais.empty:
        display_50p = variacoes_percentuais.copy()
        colunas_moeda = ['ValorMensal', 'Saldo', 'SaldoAnterior']
        for col in colunas_moeda:
            display_50p[col] = display_50p[col].apply(formatar_br_final)
        
        display_50p['MesReferencia'] = display_50p['MesReferencia'].dt.strftime('%b/%Y')

        # A linha que aplicava a formatação na 'VariacaoPercentual' foi removida.
        
        st.dataframe(
            display_50p,
            column_config={
                # Usamos NumberColumn para formatar o número como percentual.
                "VariacaoPercentual": st.column_config.NumberColumn(
                    "Variação (%)",
                    format="%.2f%%"
                ),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma conta teve variação percentual superior a 50% neste período.")

    # --- Gráfico Comparativo (INTOCADO) ---
    st.markdown("### 📅 Comparativo de Saldo Entre Dois Meses para uma Conta Específica")
    contas_opcoes = sorted(df_long["Conta Contábil"].dropna().unique())
    conta_escolhida = st.selectbox("Escolha a Conta Contábil:", contas_opcoes, key="var_conta_comp")

    meses_ordenados = sorted(df_long["MesReferencia"].dt.to_period('M').unique())
    meses_opcoes = [m.strftime("%b/%Y") for m in meses_ordenados]
    
    index_1 = max(0, len(meses_opcoes) - 2)
    index_2 = max(0, len(meses_opcoes) - 1)

    mes_escolhido_1 = st.selectbox("Escolha o primeiro mês:", meses_opcoes, index=index_1, key="var_mes1_comp")
    mes_escolhido_2 = st.selectbox("Escolha o segundo mês:", meses_opcoes, index=index_2, key="var_mes2_comp")

    if mes_escolhido_1 and mes_escolhido_2 and conta_escolhida:
        df_comparativo = df_long[
            (df_long["Conta Contábil"] == conta_escolhida) &
            (df_long["MesReferencia"].dt.strftime("%b/%Y").isin([mes_escolhido_1, mes_escolhido_2]))
        ].copy()

        df_comparativo.sort_values("MesReferencia", inplace=True)
        df_comparativo['Mes/Ano'] = df_comparativo['MesReferencia'].dt.strftime('%b/%Y')

        if not df_comparativo.empty:
            fig = px.bar(
                df_comparativo,
                x="Mes/Ano",
                y="Saldo",
                color="Mes/Ano",
                title=f"Comparativo de Saldo para a Conta {conta_escolhida}",
                labels={"Saldo": "Saldo (R$)", "Mes/Ano": "Mês de Referência"},
                text="Saldo"
            )
            fig.update_traces(texttemplate='R$ %{text:,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."), textposition='outside')
            fig.update_layout(xaxis_title=None, yaxis_title="Saldo (R$)", hovermode="x unified", legend_title_text="Mês de Referência")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados não encontrados para a conta e meses selecionados.")