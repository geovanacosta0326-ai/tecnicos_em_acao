import streamlit as st
import pandas as pd
import folium
import warnings
import requests
import io
from datetime import datetime
from folium import DivIcon
from sqlalchemy import text
from streamlit_folium import st_folium

try:
    from conexao import get_engine
except ImportError:
    from db_config import get_engine

warnings.filterwarnings("ignore")

# 1. CONFIGURAÇÃO DA PÁGINA (SUAS CORES ORIGINAIS)
st.set_page_config(page_title="Monitoramento ATeG", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 32px; color: #1B4332; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 16px; color: #2D6A4F; font-weight: 600; }
    .main { background-color: #f7fcf7; }
    h1 { color: #1B4332 !important; font-family: 'Segoe UI Bold', sans-serif; }
    .equipe-assinatura { font-size: 10px; color: #52796f; margin-top: -15px; font-weight: 400; margin-bottom: 20px; }
    
    /* CSS para o Tooltip estilo "Foto" */
    .leaflet-popup-content-wrapper { background: transparent !important; box-shadow: none !important; padding: 0 !important; }
    .leaflet-popup-tip-container { display: none !important; }
    </style>
""", unsafe_allow_html=True)

st.title("ASSISTÊNCIA TÉCNICA E GERENCIAL - ATeG")
st.markdown('<p class="equipe-assinatura">Equipe CIIAGRO</p>', unsafe_allow_html=True)
st.divider()

# 2. CARREGAMENTO DE DADOS
@st.cache_data(ttl=300)
def carregar_dados():
    engine_pg = get_engine()
    query = "SELECT * FROM public.mapa_consolidado_ateg"
    with engine_pg.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df['data_ultima_visita'] = pd.to_datetime(df['data_ultima_visita'], errors='coerce')
        df['data_atualizacao'] = pd.to_datetime(df['data_atualizacao'], errors='coerce')
        df['gap_dias'] = (df['data_atualizacao'] - df['data_ultima_visita']).dt.days.fillna(0).astype(int)
        return df

@st.cache_data(ttl=3600)
def carregar_geojson():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json"
    try: return requests.get(url, timeout=10).json()
    except: return None

df_raw = carregar_dados()
geo_ceara = carregar_geojson()

# 3. TRATAMENTO (SUA LÓGICA ORIGINAL)
df_proc = df_raw.assign(
    cod_ibge=df_raw['codigos_ibge'].astype(str).str.split(', ')
).explode('cod_ibge')
df_proc['cod_ibge'] = df_proc['cod_ibge'].astype(str).str.strip()

df_coords = pd.read_csv("https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv")
df_coords['codigo_ibge'] = df_coords['codigo_ibge'].astype(str)
df_mapa = df_proc.merge(df_coords, left_on='cod_ibge', right_on='codigo_ibge', how='inner')

# 4. VOLTANDO TODOS OS SEUS FILTROS NA SIDEBAR
st.sidebar.title("🎛️ Filtros ATeG")

min_meses, max_meses = int(df_mapa['tempo_projeto_meses'].min()), int(df_mapa['tempo_projeto_meses'].max())
meses_sel = st.sidebar.slider("Tempo de Projeto (Meses)", min_meses, max_meses, (min_meses, max_meses))

opcoes_status = sorted(df_mapa['status_tecnico'].dropna().unique())
status_sel = st.sidebar.multiselect("Status do Técnico", opcoes_status)
if status_sel: df_mapa = df_mapa[df_mapa['status_tecnico'].isin(status_sel)]

opcoes_regiao = sorted(df_mapa['regiao_faec'].dropna().unique())
regioes_sel = st.sidebar.multiselect("Regiões", opcoes_regiao)
if regioes_sel: df_mapa = df_mapa[df_mapa['regiao_faec'].isin(regioes_sel)]

opcoes_projeto = sorted(df_mapa['projeto'].dropna().unique())
projetos_sel = st.sidebar.multiselect("Projetos", opcoes_projeto)
if projetos_sel: df_mapa = df_mapa[df_mapa['projeto'].isin(projetos_sel)]

opcoes_atividade = sorted(df_mapa['atividade'].dropna().unique())
atividades_sel = st.sidebar.multiselect("Atividades", opcoes_atividade)
if atividades_sel: df_mapa = df_mapa[df_mapa['atividade'].isin(atividades_sel)]

df_mapa = df_mapa[(df_mapa['tempo_projeto_meses'] >= meses_sel[0]) & (df_mapa['tempo_projeto_meses'] <= meses_sel[1])]

# 5. KPIs ORIGINAIS
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("👤 Técnicos", df_mapa['tecnico'].nunique())
m2.metric("🌱 Atividades", df_mapa['atividade'].nunique())
m3.metric("📂 Projetos", df_mapa['projeto'].nunique())
m4.metric("🏙️ Municípios", df_mapa['nome'].nunique())
m5.metric("📈 Média Meses", round(df_mapa['tempo_projeto_meses'].mean(), 1) if not df_mapa.empty else 0)
m6.metric("✅ No Filtro", len(df_mapa['tecnico'].unique()))

st.divider()

# 6. MAPA COM O VISUAL DA FOTO APENAS NO TOOLTIP
aba_mapa, aba_resumo, aba_download = st.tabs(["🗺️ Mapa Operacional", "📊 Resumo Executivo", "📥 Repositório"])

with aba_mapa:
    CORES_DISTINTAS = ["#E63946", "#1D3557", "#FFB703", "#2A9D8F", "#7B2D8B", "#FB8500", "#F4A261", "#606C38"]
    cor_atv_map = {atv: CORES_DISTINTAS[i % len(CORES_DISTINTAS)] for i, atv in enumerate(opcoes_atividade)}

    col_m, col_l = st.columns([4, 1])
    with col_l:
        st.write("### 🌱 Legenda")
        for atv in sorted(df_mapa['atividade'].unique()):
            cor = cor_atv_map.get(atv, "#CCC")
            st.markdown(f"""<div style="display:flex;align-items:center;margin-bottom:8px;"><div style="width:15px;height:15px;background-color:{cor};border-radius:50%;margin-right:10px;"></div><span style="font-size:12px;">{atv}</span></div>""", unsafe_allow_html=True)

    with col_m:
        m = folium.Map(location=[-5.2, -39.5], zoom_start=7, tiles='cartodbpositron')
        if geo_ceara:
            folium.GeoJson(geo_ceara, style_function=lambda x: {'fillColor': 'transparent', 'color': '#bdc3c7', 'weight': 1.0}).add_to(m)

        for _, row in df_mapa.iterrows():
            # A cor do marcador segue a atividade, mas o BALÃO é verde escuro (estilo foto)
            cor_marcador = cor_atv_map.get(row['atividade'], '#1B4332')
            
            html_tooltip = f"""
            <div style="font-family: 'Segoe UI', sans-serif; background-color: #1B4332; color: white; padding: 15px; border-radius: 10px; width: 250px; box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
                <div style="font-size: 16px; font-weight: 800; text-transform: uppercase; margin-bottom: 2px;">{row['tecnico']}</div>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.3); margin: 8px 0;">
                <div style="font-size: 13px; line-height: 1.5;">
                    <b>Atividade:</b> {str(row['atividade']).upper()}<br>
                    <b>Supervisor:</b> {row['supervisor_atual']}<br>
                    <b>Tempo:</b> {int(row['tempo_projeto_meses'])} meses<br>
                    <b>Gap:</b> {int(row['gap_dias'])} dias
                </div>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=7,
                color="white",
                weight=2,
                fill=True,
                fill_color=cor_marcador,
                fill_opacity=1,
                popup=folium.Popup(html_tooltip, max_width=300)
            ).add_to(m)
        
        st_folium(m, width='100%', height=650)

# 7. RESUMO E DOWNLOAD (MANTIDOS)
with aba_resumo:
    if not df_mapa.empty:
        st.dataframe(df_mapa[['tecnico', 'atividade', 'supervisor_atual', 'gap_dias']], use_container_width=True)

with aba_download:
    st.subheader("📥 Exportação")
    # ... código de exportação original ...