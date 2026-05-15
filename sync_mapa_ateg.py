import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import sys

def realizar_migracao():

    # =====================================================
    # CONEXÃO LOCAL
    # =====================================================

    engine_local = create_engine(
        "postgresql+psycopg2://postgres:faecsenar2022@localhost:5432/api_sisateg"
    )

    # =====================================================
    # CONEXÃO REMOTA
    # =====================================================

    url_remota = URL.create(
        "postgresql+psycopg2",
        username="postgres",
        password="ranes%2015",
        host="177.22.38.27",
        port=6432,
        database="painel_ciiagro"
    )

    engine_remoto = create_engine(url_remota)

    try:

        print("====================================")
        print("INICIANDO MIGRAÇÃO MAPA ATEG")
        print("====================================")

        # =====================================================
        # LEITURA DOS DADOS
        # =====================================================

        print("Lendo VIEW local...")

        query = """
        SELECT *
        FROM public.vw_mapa_consolidado_ateg_georrefercnaias
        """

        df = pd.read_sql(query, engine_local)

        print(f"Total de registros: {len(df)}")

        if df.empty:
            print("Nenhum dado encontrado.")
            return

        # =====================================================
        # ENVIO PARA O SERVIDOR
        # =====================================================

        print("Enviando dados para servidor remoto...")

        df.to_sql(
            'mapa_consolidado_ateg',
            engine_remoto,
            schema='public',
            if_exists='replace',
            index=False,
            chunksize=1000,
            method='multi'
        )

        print("====================================")
        print("MIGRAÇÃO FINALIZADA COM SUCESSO")
        print("====================================")

    except Exception as e:

        print("====================================")
        print("ERRO NA MIGRAÇÃO")
        print("====================================")

        print(e)

        sys.exit(1)

# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":
    realizar_migracao()
    