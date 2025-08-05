# app.py

import streamlit as st
import pandas as pd
from src.file_loader import carregar_e_preparar_dados, transformar_para_formato_long

st.set_page_config(page_title="Análise Contábil", layout="wide")
st.title("📊 Analisador de Contas Contábeis")
st.markdown("Faça o upload da planilha mensal para iniciar a análise.")

uploaded_file = st.file_uploader("📁 Envie a planilha (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner("🔄 Carregando e processando a planilha..."):
        try:
            df_original_limpo, df_cronologico, colunas_mes = carregar_e_preparar_dados(uploaded_file)
            st.success("✅ Planilha carregada com sucesso!")

            df_long = transformar_para_formato_long(df_cronologico.copy(), colunas_mes)

            def formatar_br_final(valor):
                # Se o valor for nulo (NaN, None), retorna uma string vazia
                if pd.isna(valor):
                    return ""
                try:
                    num = float(valor)
                    # Formata no padrão americano e depois inverte os separadores
                    s_us = f"{num:,.2f}"
                    s_br = s_us.replace(",", "X").replace(".", ",").replace("X", ".")
                    return s_br
                except (ValueError, TypeError):
                    return str(valor) # Se não for número, retorna como texto

            # --- PREPARAÇÃO PARA EXIBIÇÃO ---
            # Aplica a MESMA formatação nos dois DataFrames
            df_display_original = df_original_limpo.copy()
            for col in df_display_original.columns:
                if col in colunas_mes:
                    df_display_original[col] = df_display_original[col].apply(formatar_br_final)

            df_display_cronologico = df_cronologico.copy()
            for col in colunas_mes:
                df_display_cronologico[col] = df_display_cronologico[col].apply(formatar_br_final)

            # --- EXIBIÇÃO ---
            with st.expander("🔍 Visualizar dados originais (Formatado)"):
                st.dataframe(df_display_original, use_container_width=True)

            with st.expander("📅 Visualizar dados em ordem cronológica (Formatado)"):
                st.dataframe(df_display_cronologico, use_container_width=True)

            # O resto do app
            st.sidebar.title("🔎 Navegação")
            opcoes = ["📈 Análise Temporal", "🔁 Variação Mês a Mês", "📊 Análise por Tipo de Conta", "🔄 Contas Surgidas e Zeradas"]
            opcao = st.sidebar.radio("Escolha a análise:", opcoes)

            if opcao == "📈 Análise Temporal":
                from analises.temporal import mostrar_analise_temporal
                mostrar_analise_temporal(df_long)
            elif opcao == "🔁 Variação Mês a Mês":
                from analises.variacao import mostrar_analise_variacao
                mostrar_analise_variacao(df_long)
            elif opcao == "📊 Análise por Tipo de Conta":
                from analises.por_tipo import mostrar_analise_por_tipo
                mostrar_analise_por_tipo(df_long)
            elif opcao == "🔄 Contas Surgidas e Zeradas":
                from analises.surgidas_zeradas import mostrar_analise_surgidas_zeradas
                mostrar_analise_surgidas_zeradas(df_long)
        except Exception as e:
            st.error(f"Erro ao processar a planilha: {e}")