import streamlit as st
import urllib.parse
from sqlalchemy import create_engine

def get_engine():
    # Busca os dados do painel de Secrets do Streamlit
    db_data = st.secrets["postgres"]
    
    usuario = db_data["username"]
    # Pega a senha e protege o caractere '%' para o SQLAlchemy não quebrar
    senha = urllib.parse.quote_plus(db_data["password"])
    host = db_data["host"]
    porta = db_data["port"]
    banco = db_data["database"]
    
    str_conexao = f"postgresql://{usuario}:{senha}@{host}:{porta}/{banco}"
    return create_engine(str_conexao)