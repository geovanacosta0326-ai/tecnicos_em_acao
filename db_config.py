import urllib.parse
from sqlalchemy import create_engine

def get_engine():
    """
    Configura a conexão com o banco de dados PostgreSQL.
    Centraliza as credenciais para facilitar a manutenção.
    """
    # Credenciais do servidor
    usuario = "postgres"
    senha_bruta = "ranes%2015"
    ip_servidor = "177.22.38.27"
    porta = "6432"
    banco = "painel_ateg"

    # Tratamento para caracteres especiais na URL (como o espaço na senha)
    senha_segura = urllib.parse.quote_plus(senha_bruta)
    
    # Construção da string de conexão (URL)
    url_final = f"postgresql+psycopg2://{usuario}:{senha_segura}@{ip_servidor}:{porta}/{banco}"
    
    return create_engine(url_final)
if __name__ == "__main__":
    print("🔍 Testando conexão com o banco de dados...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Tenta rodar um comando simples de "Olá Mundo" no banco
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
            print("✅ SUCESSO: Conexão estabelecida com o servidor!")
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")