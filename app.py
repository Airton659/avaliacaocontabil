# app.py

import streamlit as st
import pandas as pd
from src.file_loader import carregar_planilha, transformar_para_formato_long
from analises.temporal import mostrar_analise_temporal
from analises.variacao import mostrar_analise_variacao
from analises.por_tipo import mostrar_analise_por_tipo
# Importe a nova análise
from analises.surgidas_zeradas import mostrar_analise_surgidas_zeradas
from src.constantes import COLUNAS_FIXAS, PADRAO_MES
import re

st.set_page_config(page_title="Análise Contábil", layout="wide")

st.title("📊 Analisador de Contas Contábeis")
st.markdown("Faça o upload da planilha mensal para iniciar a análise.")

uploaded_file = st.file_uploader("📁 Envie a planilha (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner("🔄 Carregando e processando a planilha..."):
        try:
            df_original, colunas_mes_originais = carregar_planilha(uploaded_file)

            st.success("✅ Planilha carregada com sucesso!")

            df_ordenado = df_original.copy()
            colunas_mes = [col for col in df_ordenado.columns if re.match(PADRAO_MES, col)]

            def chave_ordenacao_mes(coluna_nome):
                try:
                    mapa_meses = {
                        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
                        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
                        "000": 0
                    }
                    parte, ano = coluna_nome.strip().upper().split("/")
                    mes = mapa_meses.get(parte)
                    return (int(ano), mes)
                except (ValueError, TypeError, AttributeError):
                    return (9999, 99)
            
            colunas_mes.sort(key=chave_ordenacao_mes)
            colunas_ordenadas_utilizadas = COLUNAS_FIXAS + colunas_mes
            df_ordenado = df_ordenado[colunas_ordenadas_utilizadas]
            
            df_long = transformar_para_formato_long(df_ordenado, colunas_mes)

            with st.expander("🔍 Visualizar dados originais (como no arquivo)"):
                st.dataframe(df_original, use_container_width=True)

            with st.expander("📅 Visualizar dados em ordem cronológica"):
                st.dataframe(df_ordenado, use_container_width=True)

            st.sidebar.title("🔎 Navegação")
            
            # Adiciona a nova opção ao menu
            opcoes = [
                "📈 Análise Temporal",
                "🔁 Variação Mês a Mês",
                "📊 Análise por Tipo de Conta",
                "🔄 Contas Surgidas e Zeradas"
            ]
            
            opcao = st.sidebar.radio("Escolha a análise:", opcoes)

            if opcao == "📈 Análise Temporal":
                mostrar_analise_temporal(df_long)
            elif opcao == "🔁 Variação Mês a Mês":
                mostrar_analise_variacao(df_long)
            elif opcao == "📊 Análise por Tipo de Conta":
                mostrar_analise_por_tipo(df_long)
            # Adiciona a chamada para a nova função
            elif opcao == "🔄 Contas Surgidas e Zeradas":
                mostrar_analise_surgidas_zeradas(df_long)

        except Exception as e:
            st.error(f"Erro ao processar a planilha: {e}")