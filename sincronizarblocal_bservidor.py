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

        # 2. LEITURA DOS DADOS LOCAIS
        # Usando o nome exato da view que você confirmou
        query_local = "SELECT * FROM public.vw_mapa_consolidado_ateg_georrefercnaias"
        
        print(f"Lendo dados da view local...")
        df = pd.read_sql(query_local, engine_local)

        if df.empty:
            print("A view está vazia. Abortando migração.")
            return

        # 3. PREPARAÇÃO DOS DADOS
        # Adicionamos a coluna de controle que você tem no servidor
        df['data_atualizacao'] = datetime.now()
        
        # Garantir que colunas de data sejam tratadas corretamente
        for col in df.columns:
            if 'data' in col or 'visita' in col:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        print(f"Campos identificados: {list(df.columns)}")
        print(f"Total de registros a enviar: {len(df)}")

        # 4. ENVIO PARA O SERVIDOR
        # Usamos 'replace' para que o banco remoto aceite as NOVAS colunas
        print("Enviando dados para o servidor remoto (Substituindo tabela)...")
        
        df.to_sql(
            'mapa_consolidado_ateg', 
            engine_remoto,
            schema='public',
            if_exists='replace', # Isso resolve o erro de 'coluna inexistente'
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