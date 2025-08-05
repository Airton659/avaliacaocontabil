# src/file_loader.py

import pandas as pd
import re
from datetime import datetime
from .constantes import COLUNAS_FIXAS, PADRAO_MES

def carregar_e_preparar_dados(caminho_arquivo: str):
    """
    Função central que carrega, junta as descrições e limpa os dados,
    retornando um DataFrame limpo na ordem original e outro na ordem cronológica.
    """
    # ETAPA 1: Leitura e junção das descrições (lógica já validada)
    df = pd.read_excel(caminho_arquivo, header=None, dtype=str)
    header_row_idx = -1
    for i, row in df.iterrows():
        if all(col in row.values for col in COLUNAS_FIXAS):
            header_row_idx = i
            break
    if header_row_idx == -1:
        raise ValueError("Cabeçalho com colunas esperadas não encontrado.")

    df = pd.read_excel(caminho_arquivo, header=header_row_idx)
    df.columns = df.columns.str.strip()

    if 'Unnamed: 2' in df.columns:
        df.rename(columns={'Unnamed: 2': 'Nome Conta'}, inplace=True)
        conta_str = df['Conta Contábil'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        nome_conta_str = df['Nome Conta'].fillna('').astype(str)
        df['Conta Contábil'] = conta_str + ' - ' + nome_conta_str
        df['Conta Contábil'] = df['Conta Contábil'].str.strip(' -').str.strip()
        df = df.drop(columns=['Nome Conta'])

    if 'Unnamed: 4' in df.columns:
        df.rename(columns={'Unnamed: 4': 'Nome Tipo Conta'}, inplace=True)
        tipo_conta_str = df['Tipo Conta Corrente Lançamento'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        nome_tipo_conta_str = df['Nome Tipo Conta'].fillna('').astype(str)
        df['Tipo Conta Corrente Lançamento'] = tipo_conta_str + ' - ' + nome_tipo_conta_str
        df['Tipo Conta Corrente Lançamento'] = df['Tipo Conta Corrente Lançamento'].str.strip(' -').str.strip()
        df = df.drop(columns=['Nome Tipo Conta'])

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # ETAPA 2: Limpeza e conversão dos valores monetários
    colunas_mes = [col for col in df.columns if isinstance(col, str) and re.match(PADRAO_MES, col)]

    def convert_to_float_final(value):
        # Se já for um número, apenas o retorna.
        if isinstance(value, (int, float)):
            return float(value)
        # Se for um texto, faz a limpeza segura.
        try:
            s = str(value).strip()
            if not s or s == '-': return 0.0
            is_negative = s.startswith('(') and s.endswith(')')
            if is_negative: s = '-' + s[1:-1]
            s = s.replace('.', '').replace(',', '.')
            return float(s)
        except (ValueError, TypeError):
            return None # Retorna None se não puder converter

    # Aplica a limpeza em todas as colunas de mês
    for col in colunas_mes:
        df[col] = df[col].apply(convert_to_float_final)
    
    df_original_limpo = df.copy()

    # ETAPA 3: Criar a versão com ordem cronológica
    def chave_ordenacao_mes(col):
        try:
            mapa = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12, "000": 0}
            p, a = col.strip().upper().split("/"); return (int(a), mapa.get(p, 99))
        except: return (9999, 99)

    col_mes_ord = sorted(colunas_mes, key=chave_ordenacao_mes)
    col_fixas_ok = [c for c in COLUNAS_FIXAS if c in df.columns]
    
    df_cronologico = df[col_fixas_ok + col_mes_ord]

    return df_original_limpo, df_cronologico, col_mes_ord

def transformar_para_formato_long(df: pd.DataFrame, colunas_mes: list) -> pd.DataFrame:
    col_fixas_ok = [c for c in COLUNAS_FIXAS if c in df.columns]
    df_long = df.melt(id_vars=col_fixas_ok, value_vars=colunas_mes, var_name="MesReferencia", value_name="Saldo")
    
    def conv_data(v):
        try:
            mapa = {"JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04", "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08", "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12"}
            p, a = v.strip().upper().split("/"); m = mapa.get(p)
            return pd.to_datetime(f"{a}-{m}-01") if m else pd.NaT
        except: return pd.NaT
            
    df_long["MesReferencia"] = df_long["MesReferencia"].apply(conv_data)
    df_long = df_long.dropna(subset=["MesReferencia"])
    df_long = df_long.sort_values(["Conta Contábil", "MesReferencia"])
    df_long["SaldoAnterior"] = df_long.groupby("Conta Contábil")["Saldo"].shift(1)
    df_long["ValorMensal"] = df_long["Saldo"] - df_long["SaldoAnterior"].fillna(0)
    df_long["VariacaoPercentual"] = (df_long["ValorMensal"] / df_long["SaldoAnterior"]) * 100
    return df_long