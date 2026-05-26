import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import sys
from datetime import datetime

def realizar_migracao_completa():
    # =====================================================
    # 1. CONFIGURAÇÃO DAS CONEXÕES
    # =====================================================

    # Conexão Local (Origem)
    engine_local = create_engine(
        "postgresql+psycopg2://postgres:faecsenar2022@localhost:5432/api_sisateg"
    )

    # Conexão Remota (Destino)
    url_remota = URL.create(
        "postgresql+psycopg2",
        username="postgres",
        password="ranes%2015",
        host="177.22.38.27",
        port=6432,
        database="painel_ateg"
    )
    engine_remoto = create_engine(url_remota)

    try:
        print("==================================================")
        print("INICIANDO MIGRAÇÃO: LOCAL -> SERVIDOR")
        print("==================================================")

        # =====================================================
        # 2. LEITURA DOS DADOS LOCAIS
        # =====================================================
        query_local = "SELECT * FROM public.vw_mapa_consolidado_ateg_georrefercnaias"

        print("Lendo dados da view local...")
        df = pd.read_sql(query_local, engine_local)

        if df.empty:
            print("A view está vazia. Abortando migração.")
            return

        # =====================================================
        # 3. PREPARAÇÃO DOS DADOS
        # =====================================================
        df['data_atualizacao'] = datetime.now()

        # Colunas que são datas de verdade
        cols_data = [
            "data_primeira_visita",
            "data_ultima_visita",
            "data_atualizacao",
        ]

        # Colunas que são números inteiros (NÃO converter para datetime)
        cols_inteiras = [
            "total_visitas",
            "visitas_validas",
            "visitas_invalidas",
            "total_propriedades",
            "propriedades_ativas",
            "propriedades_inativas",
            "tempo_projeto_meses",
        ]

        # Converte apenas as colunas de data reais
        for col in cols_data:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Garante que colunas numéricas sejam inteiros
        for col in cols_inteiras:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        print(f"Campos identificados: {list(df.columns)}")
        print(f"Dtypes após preparação:")
        for col in df.columns:
            print(f"  {col}: {df[col].dtype}")
        print(f"Total de registros a enviar: {len(df)}")

        # =====================================================
        # 4. ENVIO PARA O SERVIDOR
        # =====================================================
        print("\nEnviando dados para o servidor remoto (substituindo tabela)...")

        df.to_sql(
            'mapa_consolidado_ateg',
            engine_remoto,
            schema='public',
            if_exists='replace',
            index=False,
            chunksize=300,
            method='multi'
        )

        print("==================================================")
        print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("==================================================")

    except Exception as e:
        print("==================================================")
        print("ERRO CRÍTICO NA MIGRAÇÃO")
        print("==================================================")
        print(f"Detalhes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    realizar_migracao_completa()