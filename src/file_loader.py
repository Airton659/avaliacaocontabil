# src/file_loader.py

import pandas as pd
import re
from datetime import datetime
import openpyxl  # Usaremos openpyxl para ler os valores brutos
from .constantes import COLUNAS_FIXAS, PADRAO_MES

def clean_and_convert_value(value):
    """
    Função final para limpar e converter valores monetários.
    Trata strings, números, parênteses e valores nulos.
    """
    if value is None or str(value).strip() == '':
        return 0.0

    # Converte para string para manipulação
    s = str(value).strip()

    # Trata formato contábil negativo (parênteses)
    is_negative = s.startswith('(') and s.endswith(')')
    if is_negative:
        s = '-' + s[1:-1]

    # Remove caracteres não numéricos, exceto a vírgula do decimal e o sinal de menos
    # Isso limpa pontos de milhar, R$, etc.
    s = re.sub(r'[^\d,-]', '', s)
    
    # Troca a vírgula do decimal por um ponto
    s = s.replace(',', '.')

    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def carregar_planilha(caminho_arquivo: str) -> pd.DataFrame:
    """
    Lê a planilha usando openpyxl para garantir a leitura correta dos valores,
    depois monta o DataFrame com os dados limpos e convertidos.
    """
    # Carrega o arquivo com openpyxl
    workbook = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    sheet = workbook.active

    # Converte os dados da planilha para uma lista de listas
    data = list(sheet.values)

    # Encontra a linha do cabeçalho
    header_row_idx = -1
    for i, row in enumerate(data):
        row_str_upper = [str(v).strip().upper() for v in row]
        if all(col.upper() in row_str_upper for col in COLUNAS_FIXAS):
            header_row_idx = i
            break
    
    if header_row_idx == -1:
        raise ValueError("Cabeçalho com colunas esperadas não encontrado na planilha.")

    # Cria o DataFrame a partir dos dados e do cabeçalho encontrado
    header = [str(h).strip() for h in data[header_row_idx]]
    data_rows = data[header_row_idx + 1:]
    
    df = pd.DataFrame(data_rows, columns=header)

    # Filtra apenas as colunas que serão utilizadas
    colunas_mes = [col for col in df.columns if re.match(PADRAO_MES, str(col))]
    colunas_utilizadas = COLUNAS_FIXAS + colunas_mes
    df = df[colunas_utilizadas]

    # Aplica a função de limpeza e conversão em todas as colunas de mês
    for col in colunas_mes:
        df[col] = df[col].apply(clean_and_convert_value)

    return df, colunas_mes


def transformar_para_formato_long(df: pd.DataFrame, colunas_mes: list) -> pd.DataFrame:
    """
    Transforma o dataframe para formato long e calcula os valores mensais.
    """
    df_long = df.melt(
        id_vars=COLUNAS_FIXAS,
        value_vars=colunas_mes,
        var_name="MesReferencia",
        value_name="Saldo"
    )

    df_long["MesReferencia"] = df_long["MesReferencia"].astype(str).str.strip().str.upper()
    df_long["MesReferencia"] = df_long["MesReferencia"].apply(converter_mes_ano_para_data)
    df_long = df_long.dropna(subset=["MesReferencia"])
    
    df_long["Conta Contábil"] = df_long["Conta Contábil"].fillna("(Conta não especificada)").astype(str)

    df_long = df_long.sort_values(["Conta Contábil", "MesReferencia"])
    df_long["SaldoAnterior"] = df_long.groupby("Conta Contábil")["Saldo"].shift(1)
    df_long["ValorMensal"] = df_long["Saldo"] - df_long["SaldoAnterior"]
    df_long["VariacaoPercentual"] = (df_long["ValorMensal"] / df_long["SaldoAnterior"]) * 100

    return df_long

def converter_mes_ano_para_data(valor: str) -> datetime:
    """
    Converte strings como 'JAN/2025' em datetime.
    """
    try:
        mapa_meses = {
            "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
            "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
            "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12"
        }
        parte, ano = valor.strip().upper().split("/")
        mes = mapa_meses.get(parte)
        if mes is None:
            return pd.NaT
        return pd.to_datetime(f"{ano}-{mes}-01")
    except:
        return pd.NaT