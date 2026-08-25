import os
import streamlit as st
import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
import warnings
import requests
import io
import math
from datetime import datetime, timedelta
from folium import DivIcon
from sqlalchemy import text
from streamlit_folium import st_folium

try:
    from conexao import get_engine
except ImportError:
    from db_config import get_engine

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="Monitoramento ATeG", layout="wide", page_icon="🌱", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght=300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

[data-testid="stAppViewContainer"] {
    background-color: #f0f4f2;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B4332 0%, #2D6A4F 100%);
    border-right: none;
}
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
    visibility: hidden !important;
}
[data-testid="stSidebar"] * {
    color: #d8f3dc !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label {
    color: #95d5b2 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: white !important;
    border-radius: 8px !important;
}
section[data-testid="stMain"] [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #e2ede8 !important;
    color: #1B4332 !important;
    border-radius: 8px !important;
}
section[data-testid="stMain"] [data-baseweb="select"] span {
    color: #1B4332 !important;
}
[data-testid="stSidebar"] h1 {
    color: white !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #b7e4c7 !important;
    font-size: 12px !important;
}

[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 700 !important; color: #0F6E56 !important; font-family: 'DM Sans', sans-serif !important; }
[data-testid="stMetricLabel"] { font-size: 12px !important; color: #52796f !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; }

h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; }
h1 { color: #1B4332 !important; font-size: 22px !important; font-weight: 700 !important; }
h2 { color: #2D6A4F !important; font-size: 17px !important; font-weight: 600 !important; }
h3 { color: #2D6A4F !important; font-size: 14px !important; font-weight: 600 !important; }

header { visibility: hidden !important; height: 0 !important; }
footer { visibility: hidden !important; height: 0 !important; }
#MainMenu { visibility: hidden !important; }
[data-testid="manage-app-button"] { display: none !important; }
.stDeployButton { display: none !important; }
.block-container { padding-top: 0.75rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }

.kpi-card {
    background: white;
    border-radius: 8px;
    padding: 10px 14px;
    border: 1px solid #e2ede8;
    box-shadow: 0 1px 3px rgba(27,67,50,0.06);
    transition: box-shadow 0.2s ease;
    height: 100%;
}
.kpi-card:hover {
    box-shadow: 0 3px 10px rgba(27,67,50,0.1);
}
.kpi-label {
    font-size: 9px;
    color: #74a49c;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 3px;
    font-family: 'DM Sans', sans-serif;
}
.kpi-value {
    font-size: 22px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 3px;
    font-family: 'DM Sans', sans-serif;
}
.kpi-sub {
    font-size: 10px;
    color: #9ab4ae;
    font-weight: 400;
    font-family: 'DM Sans', sans-serif;
}
.kpi-accent-green  { color: #0F6E56; }
.kpi-accent-teal   { color: #1D9E75; }
.kpi-accent-red    { color: #D94040; }
.kpi-accent-dark   { color: #1B4332; }
.kpi-accent-blue   { color: #1e6091; }

.kpi-border-green  { border-left: 3px solid #0F6E56 !important; }
.kpi-border-teal   { border-left: 3px solid #1D9E75 !important; }
.kpi-border-red    { border-left: 3px solid #D94040 !important; }
.kpi-border-amber  { border-left: 3px solid #d4900a !important; }
.kpi-border-blue   { border-left: 3px solid #1e6091 !important; }

.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 12px 0;
}
.section-title {
    font-size: 13px;
    font-weight: 700;
    color: #52796f;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: 'DM Sans', sans-serif;
}
.section-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #c8dfd3, transparent);
}

.alert-card-critico {
    background: #fbe9e9;
    border-left: 4px solid #B52C2C;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 7px;
    box-shadow: 0 2px 6px rgba(181,44,44,0.15);
}
.alert-card-atencao {
    background: #fdf3d7;
    border-left: 4px solid #b87200;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 7px;
    box-shadow: 0 2px 6px rgba(184,114,0,0.15);
}
.alert-card-ok {
    background: #e4f5ec;
    border-left: 4px solid #0d7a52;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 7px;
}

.badge-critico { background:#B52C2C; color:#fff; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-atencao { background:#b87200; color:#fff; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-ok      { background:#0d7a52; color:#fff; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:700; }

[data-baseweb="tab-list"] {
    background: white !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid #e2ede8 !important;
    gap: 2px !important;
    box-shadow: 0 1px 3px rgba(27,67,50,0.05) !important;
}
[data-baseweb="tab"] {
    border-radius: 7px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #52796f !important;
    padding: 6px 14px !important;
    transition: all 0.15s ease !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    background: #1B4332 !important;
    color: white !important;
    font-weight: 600 !important;
}

.custom-table {
    width: 100%;
    border-collapse: collapse;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(27,67,50,0.08);
    font-family: 'DM Sans', sans-serif;
}
.custom-table thead tr {
    background: #2D6A4F;
}
.custom-table th {
    padding: 10px 14px;
    font-size: 12px;
    color: white;
    font-weight: 600;
    text-align: left;
    letter-spacing: 0.3px;
}
.custom-table tbody tr:hover {
    background: #f5faf7;
}
.custom-table td {
    padding: 8px 14px;
    border-bottom: 1px solid #eef4f1;
    font-size: 13px;
}
.custom-table tfoot tr {
    background: #1B4332;
}
.custom-table tfoot td {
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 700;
    color: white;
    border-bottom: none;
}

.tecnico-card {
    padding: 9px 13px;
    margin-bottom: 6px;
    background: white;
    border-radius: 9px;
    border: 1px solid #e2ede8;
    box-shadow: 0 1px 3px rgba(27,67,50,0.04);
    transition: box-shadow 0.15s ease;
}
.tecnico-card:hover {
    box-shadow: 0 3px 10px rgba(27,67,50,0.1);
}

.filter-count {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #d8f3dc;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    font-family: 'DM Sans', sans-serif;
}

.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }
.stDownloadButton button {
    background: #1B4332 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton button:hover {
    background: #2D6A4F !important;
    box-shadow: 0 4px 12px rgba(27,67,50,0.25) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CABEÇALHO
# ─────────────────────────────────────────────
_data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(
    f'<div style="background:linear-gradient(120deg,#1B4332 0%,#2D6A4F 50%,#40916C 100%);'
    f'border-radius:14px;padding:28px 36px;margin-bottom:20px;'
    f'box-shadow:0 8px 32px rgba(27,67,50,0.28);position:relative;overflow:hidden;">'
    f'<div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;'
    f'background:rgba(255,255,255,0.03);border-radius:50%;"></div>'
    f'<div style="position:absolute;bottom:-60px;right:80px;width:160px;height:160px;'
    f'background:rgba(255,255,255,0.03);border-radius:50%;"></div>'
    f'<div style="font-size:10px;color:#95d5b2;font-weight:700;letter-spacing:3px;'
    f'text-transform:uppercase;margin-bottom:8px;">🌿 Serviço Nacional de Aprendizagem Rural</div>'
    f'<div style="font-size:28px;font-weight:800;color:white;line-height:1.2;margin-bottom:2px;'
    f'font-family:\'DM Sans\',sans-serif;">Assistência Técnica e Gerencial</div>'
    f'<div style="font-size:28px;font-weight:800;color:#95d5b2;line-height:1.2;margin-bottom:12px;'
    f'font-family:\'DM Sans\',sans-serif;">ATeG — Painel de Monitoramento</div>'
    f'<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.1);'
    f'border-radius:20px;padding:4px 14px;">'
    f'<span style="width:6px;height:6px;background:#52B788;border-radius:50%;display:inline-block;"></span>'
    f'<span style="font-size:11px;color:#d8f3dc;font-weight:500;">{_data_hora} · Atualizado a cada 5 min</span>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# 3. CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_dados():
    engine_pg = get_engine()
    query = "SELECT * FROM public.mapa_consolidado_ateg"
    with engine_pg.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df["data_ultima_visita"]  = pd.to_datetime(df["data_ultima_visita"],  errors="coerce")
        df["data_primeira_visita"] = pd.to_datetime(df["data_primeira_visita"], errors="coerce")
        df["data_atualizacao"]    = pd.to_datetime(df["data_atualizacao"],    errors="coerce")

        cols_datetime_como_int = ["total_visitas", "visitas_validas", "visitas_invalidas"]
        for col in cols_datetime_como_int:
            if col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.day.fillna(0).astype(int)
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        cols_numericas = [
            "total_propriedades", "propriedades_ativas", "propriedades_inativas",
            "tempo_projeto_meses",
        ]
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        hoje = pd.Timestamp.now().normalize()
        df["gap_dias"] = (hoje - df["data_ultima_visita"]).dt.days.fillna(0).astype(int)
        df["gap_dias"] = df["gap_dias"].replace(0, 1)  # visita hoje conta como 1 dia, não 0
        return df

@st.cache_data(ttl=3600)
def carregar_geojson():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json"
    try:
        return requests.get(url, timeout=10).json()
    except Exception:
        return None

@st.cache_data(ttl=3600)
def carregar_coordenadas():
    url = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    df = pd.read_csv(url)
    df["codigo_ibge"] = df["codigo_ibge"].astype(str)
    return df

df_raw    = carregar_dados()
geo_ceara = carregar_geojson()
df_coords = carregar_coordenadas()

# ─────────────────────────────────────────────
# 4. PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────
df_proc = df_raw.assign(
    cod_ibge=df_raw["cod_ibge"].astype(str).str.split(", ")
).explode("cod_ibge")
df_proc["cod_ibge"] = df_proc["cod_ibge"].astype(str).str.strip()

df_mapa = df_proc.merge(df_coords, left_on="cod_ibge", right_on="codigo_ibge", how="left")
df_mapa["latitude"]  = df_mapa["latitude"].fillna(-5.2)
df_mapa["longitude"] = df_mapa["longitude"].fillna(-39.5)
df_mapa["nome"]      = df_mapa["nome"].fillna("Município não identificado")

def classificar_gap(gap):
    if gap > 45: return "🔴 Crítico"
    if gap > 30: return "🟡 Em Atenção"
    return "🟢 Em Dia"

df_mapa["status_gap"] = df_mapa["gap_dias"].apply(classificar_gap)

# ─────────────────────────────────────────────
# 5. SIDEBAR — FILTROS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:2px;color:#95d5b2;text-transform:uppercase;margin-bottom:4px;">🎛️ Filtros</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:8px 0 16px 0;border-color:rgba(255,255,255,0.1);">', unsafe_allow_html=True)

    min_m_all = int(df_mapa["tempo_projeto_meses"].min()) if not df_mapa.empty else 1
    max_m_all = int(df_mapa["tempo_projeto_meses"].max()) if not df_mapa.empty else 31
    if min_m_all == max_m_all: max_m_all += 1
    meses_sel = st.slider("⏱️ Tempo de Projeto (meses)", min_m_all, max_m_all, (min_m_all, max_m_all))

    st.markdown('<hr style="margin:4px 0 10px 0;border-color:rgba(255,255,255,0.1);">', unsafe_allow_html=True)

    opcoes_regiao = sorted(df_mapa["regiao_faec"].dropna().unique())
    regiao_sel = st.multiselect("Região FAEC", opcoes_regiao, placeholder="Todas as regiões", key="ms_regiao")

    df_sidebar = df_mapa.copy()
    if regiao_sel:
        df_sidebar = df_sidebar[df_sidebar["regiao_faec"].isin(regiao_sel)]

    def _limpar_selecao(key, opcoes_validas):
        """Remove do session_state valores que não existem mais nas opções atuais,
        evitando erro do Streamlit quando um filtro anterior muda e 'órfa' uma seleção."""
        if key in st.session_state:
            st.session_state[key] = [v for v in st.session_state[key] if v in opcoes_validas]

    # Sindicato — opções dependem da Região já selecionada
    opcoes_sindicato = sorted(df_sidebar["sindicato"].dropna().unique())
    _limpar_selecao("ms_sindicato", opcoes_sindicato)
    sindicato_sel = st.multiselect("Sindicato", opcoes_sindicato, placeholder="Todos", key="ms_sindicato")

    if sindicato_sel:
        df_sidebar = df_sidebar[df_sidebar["sindicato"].isin(sindicato_sel)]

    # Município — opções dependem de Região + Sindicato já selecionados
    opcoes_municipio = sorted(df_sidebar["municipio_atual"].dropna().unique())
    _limpar_selecao("ms_municipio", opcoes_municipio)
    municipio_sel = st.multiselect("Município", opcoes_municipio, placeholder="Todos", key="ms_municipio")

    if municipio_sel:
        df_sidebar = df_sidebar[df_sidebar["municipio_atual"].isin(municipio_sel)]

    # Supervisor — opções dependem dos filtros acima
    opcoes_sup = sorted(df_sidebar["supervisor"].dropna().unique())
    _limpar_selecao("ms_supervisor", opcoes_sup)
    sup_sel = st.multiselect("Supervisores", opcoes_sup, placeholder="Todos", key="ms_supervisor")

    if sup_sel:
        df_sidebar = df_sidebar[df_sidebar["supervisor"].isin(sup_sel)]

    # Técnico — opções dependem dos filtros acima
    opcoes_tecnico = sorted(df_sidebar["tecnico"].dropna().unique())
    _limpar_selecao("ms_tecnico", opcoes_tecnico)
    tecnico_sel = st.multiselect("Técnico", opcoes_tecnico, placeholder="Todos", key="ms_tecnico")

    if tecnico_sel:
        df_sidebar = df_sidebar[df_sidebar["tecnico"].isin(tecnico_sel)]

    # Projeto — opções dependem dos filtros acima
    opcoes_projeto = sorted(df_sidebar["projeto"].dropna().unique())
    _limpar_selecao("ms_projeto", opcoes_projeto)
    projetos_sel = st.multiselect("Projetos", opcoes_projeto, placeholder="Todos", key="ms_projeto")

    if projetos_sel:
        df_sidebar = df_sidebar[df_sidebar["projeto"].isin(projetos_sel)]

    # Atividade — opções dependem de todos os filtros acima
    options_atividade = sorted(df_sidebar["atividade"].dropna().unique())
    _limpar_selecao("ms_atividade", options_atividade)
    atividades_sel = st.multiselect("Atividades", options_atividade, placeholder="Todas", key="ms_atividade")

    if atividades_sel:
        df_sidebar = df_sidebar[df_sidebar["atividade"].isin(atividades_sel)]

    status_opcoes = ["Todos", "🔴 Crítico (>45 dias)", "🟡 Em Atenção (31–45 dias)", "🟢 Em Dia (≤30 dias)"]
    status_sel = st.selectbox("Status do Gap", status_opcoes)

    df_f = df_sidebar.copy()
    df_f = df_f[(df_f["tempo_projeto_meses"] >= meses_sel[0]) & (df_f["tempo_projeto_meses"] <= meses_sel[1])]
    
    if status_sel == "🔴 Crítico (>45 dias)":
        df_f = df_f[df_f["gap_dias"] > 45]
    elif status_sel == "🟡 Em Atenção (31–45 dias)":
        df_f = df_f[(df_f["gap_dias"] > 30) & (df_f["gap_dias"] <= 45)]
    elif status_sel == "🟢 Em Dia (≤30 dias)":
        df_f = df_f[df_f["gap_dias"] <= 30]

    st.markdown('<hr style="margin:16px 0 8px 0;border-color:rgba(255,255,255,0.1);">', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><span class="filter-count">{len(df_f)} registros</span></div>', unsafe_allow_html=True)

def section_header(title):
    st.markdown(f'<div class="section-header"><span class="section-title">{title}</span><div class="section-line"></div></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 6. KPIs
# ─────────────────────────────────────────────
n_sup  = df_f["supervisor"].nunique() if "supervisor" in df_f.columns else 0
n_tec  = df_f["tecnico"].nunique()
n_proj = df_f["projeto"].nunique()
n_atv  = df_f["atividade"].nunique()
n_mun  = df_f["nome"].nunique()

t_propriedades = df_f["total_propriedades"].sum()
p_ativas   = df_f["propriedades_ativas"].sum()
p_inativas = df_f["propriedades_inativas"].sum()

t_visitas  = df_f["total_visitas"].sum()
v_validas  = df_f["visitas_validas"].sum()
v_invalidas = df_f["visitas_invalidas"].sum()

pct_ativas         = round((p_ativas / t_propriedades * 100), 1) if t_propriedades > 0 else 0
pct_inativas       = round((p_inativas / t_propriedades * 100), 1) if t_propriedades > 0 else 0
pct_aproveitamento = round((v_validas / t_visitas * 100), 1) if t_visitas > 0 else 0

def fmt_br(n): return f"{int(n):,}".replace(",", ".")
def kpi_card(label, value, sub, color_class="kpi-accent-dark", border_class=""):
    return f'<div class="kpi-card {border_class}"><div class="kpi-label">{label}</div><div class="kpi-value {color_class}">{value}</div><div class="kpi-sub">{sub}</div></div>'

section_header("Estrutura Operacional")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(kpi_card("Supervisores", n_sup, "👥 Gestores de equipe", "kpi-accent-dark", "kpi-border-green"), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Técnicos", n_tec, "👤 Em campo", "kpi-accent-dark", "kpi-border-green"), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("Projetos", n_proj, "📂 Ativos", "kpi-accent-dark", "kpi-border-teal"), unsafe_allow_html=True)
with c4: st.markdown(kpi_card("Atividades", n_atv, "🌿 Cadeias", "kpi-accent-dark", "kpi-border-teal"), unsafe_allow_html=True)
with c5: st.markdown(kpi_card("Municípios", n_mun, "🏙️ Cobertura", "kpi-accent-dark", "kpi-border-blue"), unsafe_allow_html=True)

section_header("Propriedades")
cp1, cp2, cp3 = st.columns(3)
with cp1: st.markdown(kpi_card("Total de Propriedades", fmt_br(t_propriedades), "🏡 Mapeadas no sistema", "kpi-accent-green", "kpi-border-green"), unsafe_allow_html=True)
with cp2: st.markdown(kpi_card("Propriedades Ativas", fmt_br(p_ativas), f"📈 {pct_ativas}% do total", "kpi-accent-teal", "kpi-border-teal"), unsafe_allow_html=True)
with cp3: st.markdown(kpi_card("Propriedades Inativas", fmt_br(p_inativas), f"📉 {pct_inativas}% do total", "kpi-accent-red", "kpi-border-red"), unsafe_allow_html=True)

section_header("Auditoria de Visitas")
cv1, cv2, cv3, cv4 = st.columns(4)
with cv1: st.markdown(kpi_card("Total de Visitas", fmt_br(t_visitas), "📊 Realizadas", "kpi-accent-dark", "kpi-border-green"), unsafe_allow_html=True)
with cv2: st.markdown(kpi_card("Visitas Válidas", fmt_br(v_validas), "✅ Conformidade OK", "kpi-accent-teal", "kpi-border-teal"), unsafe_allow_html=True)
with cv3: st.markdown(kpi_card("Visitas Inválidas", fmt_br(v_invalidas), "⚠️ Revisar", "kpi-accent-red", "kpi-border-red"), unsafe_allow_html=True)
with cv4: st.markdown(kpi_card("Taxa de Aproveitamento", f"{pct_aproveitamento}%", "🎯 Eficiência geral", "kpi-accent-green", "kpi-border-green"), unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# 7. ABAS PRINCIPAIS
# ─────────────────────────────────────────────
aba_visao, aba_mapa, aba_equipe, aba_alertas, aba_inteligencia, aba_download, aba_consolidado, aba_historico = st.tabs([
    "📊 Visão Geral", "🗺️ Mapa Operacional", "👥 Equipe & Supervisores", "🚨 Alertas", "🧠 Inteligência", "📥 Exportar", "📋 Consolidado", "🔄 Histórico"
])

CORES = ["#E63946","#1D9E75","#FFB703","#7B2D8B4A","#FB8500","#1D3557","#AD5DBD","#EF476F","#118AB2","#8B4513","#2EC4B6","#FF6B6B","#6A0572","#74410B85","#4CC9F0"]
LAYOUT_BASE = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans, sans-serif", size=12))

# Mapa de cores por atividade (usado no mapa operacional)
_atividades_unicas = sorted(df_mapa["atividade"].dropna().unique())
cor_atv_map = {atv: CORES[i % len(CORES)] for i, atv in enumerate(_atividades_unicas)}

# ════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ════════════════════════════════════════════
with aba_visao:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Técnicos por atividade")
        df_atv = df_f.groupby("atividade")["tecnico"].nunique().reset_index().rename(columns={"atividade": "Atividade", "tecnico": "Técnicos"}).sort_values("Técnicos", ascending=True)
        fig_atv = px.bar(df_atv, x="Técnicos", y="Atividade", orientation="h", color="Técnicos", color_continuous_scale=["#52B788", "#1B4332"], text="Técnicos")
        fig_atv.update_traces(textposition="auto", textfont_size=12)
        fig_atv.update_layout(**LAYOUT_BASE, height=350, coloraxis_showscale=False, margin=dict(l=0, r=60, t=10, b=10), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_atv, use_container_width=True)

    with col_b:
        st.subheader("Status do Acompanhamento Técnico das Visitas (dias)")
        
        if df_f.empty:
            st.info("Nenhum dado disponível para os filtros selecionados.")
        else:
            # Faixas de Gaps
            bins   = [0, 30, 45, 9999]
            labels = ["✅ Em Dia (≤30 dias)", "⚠️ Em Atenção (31–45 dias)", "🚨 Crítico (>45 dias)"]
            
            # Agrupa por técnico pegando o maior gap real dele sem duplicar por município
            df_gap_cat = df_f.groupby("tecnico", as_index=False)["gap_dias"].max()

            # Processamento das faixas de gap
            df_gap_cat["faixa"] = pd.cut(
                df_gap_cat["gap_dias"],
                bins=bins,
                labels=labels,
                include_lowest=True
            )

            # Contagem para o gráfico de pizza/rosca
            df_gap_pie = df_gap_cat.groupby("faixa", as_index=False).size()
            df_gap_pie.columns = ["Faixa", "Qtd"]

            if df_gap_pie["Qtd"].sum() > 0:
                fig_pie = px.pie(
                    df_gap_pie, names="Faixa", values="Qtd", hole=0.55,
                    color="Faixa",
                    color_discrete_map={
                        "✅ Em Dia (≤30 dias)":        "#1D9E75",
                        "⚠️ Em Atenção (31–45 dias)": "#d4900a",
                        "🚨 Crítico (>45 dias)":       "#D94040",
                    },
                )
                fig_pie.update_layout(**LAYOUT_BASE, height=350,
                    margin=dict(l=0, r=0, t=10, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sem registros nas faixas de gap.")

    st.divider()
    col_c, col_d = st.columns([2, 1])
    with col_c:
        st.subheader("Top 10 municípios atendidos")
        df_mun_top = df_f.groupby("nome")["tecnico"].nunique().reset_index().rename(columns={"nome": "Município", "tecnico": "Técnicos"}).sort_values("Técnicos", ascending=False).head(10)
        fig_mun = px.bar(df_mun_top, x="Município", y="Técnicos", color="Técnicos", text="Técnicos", color_continuous_scale=["#74C69D", "#1B4332"])
        fig_mun.update_traces(textposition="outside", textfont_size=11)
        fig_mun.update_layout(**LAYOUT_BASE, height=380, coloraxis_showscale=False, margin=dict(l=20, r=20, t=20, b=60), xaxis=dict(tickangle=-35, showgrid=False, tickfont=dict(size=11), title=None), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_mun, use_container_width=True)

    with col_d:
        st.subheader("Tempo médio por projeto (meses)")
        df_proj = df_f.groupby("projeto")["tempo_projeto_meses"].mean().reset_index().rename(columns={"projeto": "Projeto", "tempo_projeto_meses": "Média"})
        df_proj["Média"] = df_proj["Média"].round(1)
        df_proj = df_proj.sort_values("Média", ascending=True)
        fig_proj = px.bar(df_proj, x="Média", y="Projeto", orientation="h", color="Média", color_continuous_scale="Blues", text="Média")
        fig_proj.update_traces(textposition="outside")
        fig_proj.update_layout(**LAYOUT_BASE, height=380, coloraxis_showscale=False, margin=dict(l=100, r=50, t=20, b=60), xaxis=dict(showgrid=False, title="Média (meses)"), yaxis=dict(showgrid=False, title=None, automargin=True))
        st.plotly_chart(fig_proj, use_container_width=True)

# ════════════════════════════════════════════
# ABA 2 — MAPA OPERACIONAL
# ════════════════════════════════════════════
with aba_mapa:
    m = folium.Map(
        location=[-5.2, -39.5],
        zoom_start=7,
        tiles="cartodbpositron"
    )

    if geo_ceara:
        folium.GeoJson(
            geo_ceara,
            style_function=lambda x: {
                "fillColor": "transparent",
                "color": "#bdc3c7",
                "weight": 0.8
            }
        ).add_to(m)

    totais = {}

    for _, row in df_f.iterrows():
        key = (round(row["latitude"], 4), round(row["longitude"], 4))
        totais[key] = totais.get(key, 0) + 1

    coord_counter2 = {}
    RAIO = 0.04

    # =========================================
    # MARCADORES
    # =========================================
    for _, row in df_f.iterrows():

        key = (round(row["latitude"], 4), round(row["longitude"], 4))

        idx = coord_counter2.get(key, 0)
        coord_counter2[key] = idx + 1

        total = totais[key]

        if total == 1:
            lat_off, lon_off = row["latitude"], row["longitude"]

        else:
            angulo = (2 * math.pi / total) * idx
            raio = RAIO * (1 + (total // 8) * 0.3)

            lat_off = row["latitude"] + raio * math.cos(angulo)
            lon_off = row["longitude"] + raio * math.sin(angulo)

        cor_hex = cor_atv_map.get(row["atividade"], "#1B4332")

        inicial = str(row["tecnico"]).strip()[0].upper()

        gap_color = (
            "#D94040"
            if row["gap_dias"] > 45
            else (
                "#d4900a"
                if row["gap_dias"] > 30
                else "#1D9E75"
            )
        )

        html_icone = f"""
        <div style="
            width:30px;
            height:30px;
            border-radius:50%;
            background:{cor_hex};
            border:2px solid white;
            display:flex;
            align-items:center;
            justify-content:center;
            color:white;
            font-weight:bold;
            font-size:13px;
            box-shadow:0 2px 6px rgba(0,0,0,0.3);
        ">
            {inicial}
        </div>
        """

        html_tooltip = f"""
        <div style="
            font-family:'DM Sans',sans-serif;
            background:white;
            border-radius:10px;
            width:230px;
            overflow:hidden;
            box-shadow:0 4px 20px rgba(0,0,0,0.15);
        ">

            <div style="
                background:{cor_hex};
                padding:10px 14px;
            ">
                <div style="
                    font-size:12px;
                    font-weight:700;
                    color:white;
                ">
                    {row["tecnico"]}
                </div>

                <div style="
                    font-size:10px;
                    color:rgba(255,255,255,0.8);
                    margin-top:2px;
                ">
                    {row["atividade"]}
                </div>
            </div>

            <div style="padding:10px 14px 4px;">

                <div style="
                    font-size:11px;
                    color:#555;
                    margin-bottom:4px;
                ">
                    👤 {row["supervisor"]}
                </div>

                <div style="
                    font-size:11px;
                    color:#555;
                    margin-bottom:4px;
                ">
                    📍 {row["nome"]}
                </div>

                <div style="
                    font-size:11px;
                    color:#555;
                    margin-bottom:4px;
                ">
                    📂 {row["projeto"]}
                </div>

                <div style="
                    font-size:11px;
                    color:#555;
                    margin-bottom:8px;
                ">
                    ⏱️ {int(row["tempo_projeto_meses"])} meses
                </div>

            </div>
        </div>
        """

        folium.Marker(
            location=[lat_off, lon_off],
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=html_icone
            ),
            tooltip=html_tooltip
        ).add_to(m)

    # =========================================
    # HASH DO MAPA
    # =========================================
    _map_hash = str(
        abs(hash(tuple(sorted(df_f["tecnico"].tolist()))))
    )[:10]

    # =========================================
    # LEGENDA DAS ATIVIDADES
    # =========================================
    legend_items = ""

    for atividade, cor in sorted(cor_atv_map.items()):

        legend_items += f"""
        <div style="
            display:flex;
            align-items:center;
            margin-bottom:4px;
        ">

            <div style="
                width:10px;
                height:10px;
                border-radius:50%;
                background:{cor};
                margin-right:6px;
                border:1px solid #ccc;
            ">
            </div>

            <span style="
                font-size:10px;
            ">
                {atividade}
            </span>

        </div>
        """

    legend_html = f"""
    <div style="
        position: fixed;
        top: 70px;
        right: 10px;
        z-index: 9999;
        background: rgba(255,255,255,0.95);
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        font-family: Arial;
        width: 170px;
        line-height: 1.2;
    ">

        <div style="
            font-size:12px;
            font-weight:bold;
            margin-bottom:8px;
            text-align:center;
        ">
            Atividades
        </div>

        {legend_items}

    </div>
    """

    m.get_root().html.add_child(
        folium.Element(legend_html)
    )

    st_folium(
        m,
        width="100%",
        height=550,
        key=f"mapa_ateg_{_map_hash}",
        returned_objects=[]
    )

    # =========================================
    # EXPORTAÇÃO — SUPERVISOR x TÉCNICOS
    # =========================================
    st.markdown('<hr style="margin:20px 0;border-color:rgba(0,0,0,0.08);">', unsafe_allow_html=True)
    section_header("Supervisores e Técnicos")

    df_sup_tec = (
        df_f[["supervisor", "tecnico", "municipio_atual", "atividade", "tempo_projeto_meses"]]
        .dropna(subset=["supervisor", "tecnico"])
        .drop_duplicates()
        .sort_values(["supervisor", "tecnico"])
        .copy()
    )
    df_sup_tec["tempo_projeto_meses"] = df_sup_tec["tempo_projeto_meses"].round(0).astype("Int64")
    df_sup_tec.columns = ["Supervisor", "Técnico", "Município", "Cadeia Produtiva", "Tempo de Projeto (meses)"]

    def gerar_excel_sup_tec(df_tabela_out, nome_aba="Supervisores e Técnicos"):
        buf = io.BytesIO()
        nome_aba = nome_aba[:31]
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df_tabela_out.to_excel(writer, sheet_name=nome_aba, index=False)
            wb = writer.book
            ws = writer.sheets[nome_aba]
            fmt_header = wb.add_format({
                "bold": True, "bg_color": "#2D6A4F", "font_color": "white",
                "border": 1, "align": "center",
            })
            for col_num, col_name in enumerate(df_tabela_out.columns):
                ws.write(0, col_num, col_name, fmt_header)
                ws.set_column(col_num, col_num, max(len(str(col_name)) + 4, 16))
        return buf.getvalue()

    col_dlm1, col_dlm2, col_spacerm = st.columns([2, 2, 3])
    with col_dlm1:
        st.download_button(
            label="📥 Exportar Supervisores e Técnicos — Excel",
            data=gerar_excel_sup_tec(df_sup_tec),
            file_name=f"supervisores_tecnicos_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mapa_sup_tec_excel",
        )
    with col_dlm2:
        st.download_button(
            label="📄 Exportar Supervisores e Técnicos — CSV",
            data=df_sup_tec.to_csv(index=False, sep=";").encode("utf-8"),
            file_name=f"supervisores_tecnicos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="dl_mapa_sup_tec_csv",
        )

    st.dataframe(df_sup_tec, use_container_width=True, hide_index=True)
# ════════════════════════════════════════════
# ABA 3 — EQUIPE & SUPERVISORES
# ════════════════════════════════════════════
with aba_equipe:
    supervisores_lista = ["Todos"] + sorted(df_f["supervisor"].dropna().unique())
    sup_escolhido = st.selectbox("👤 Selecione um supervisor", options=supervisores_lista)
    df_sup_sel = df_f if sup_escolhido == "Todos" else df_f[df_f["supervisor"] == sup_escolhido]

    n_tec_sup  = df_sup_sel["tecnico"].nunique()
    n_mun_sup  = df_sup_sel["municipio_atual"].nunique()
    n_proj_sup = df_sup_sel["projeto"].nunique()
    n_crit_sup = (df_sup_sel["gap_dias"] > 45).sum()
    gap_medio  = round(df_sup_sel["gap_dias"].mean(), 1) if not df_sup_sel.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("👤 Técnicos",   n_tec_sup)
    k2.metric("🏙️ Municípios", n_mun_sup)
    k3.metric("📂 Projetos",   n_proj_sup)
    k4.metric("⏱️ Gap Médio",  f"{gap_medio} dias")
    k5.metric("🚨 Críticos",   n_crit_sup)

    st.divider()
    col_l, col_r = st.columns([2, 3])

    with col_l:
        st.subheader("👥 Técnicos da equipe")
        df_tec_sup = (
            df_sup_sel.groupby("tecnico")
            .agg(
                Atividade=("atividade","first"),
                Município=("municipio_atual","first"),
                Gap=("gap_dias","max"),
                DataVisita=("data_ultima_visita","max"),
            )
            .reset_index().rename(columns={"tecnico":"Técnico"})
            .sort_values("Gap", ascending=False)
        )
        cards_html = ""
        for _, r in df_tec_sup.iterrows():
            if r["Gap"] > 45:
                badge = f'<span class="badge-critico">{int(r["Gap"])} dias</span>'
            elif r["Gap"] > 30:
                badge = f'<span class="badge-atencao">{int(r["Gap"])} dias</span>'
            else:
                badge = f'<span class="badge-ok">{int(r["Gap"])} dias</span>'
            data_fmt = pd.to_datetime(r["DataVisita"]).strftime("%d/%m/%Y") if pd.notna(r["DataVisita"]) else "—"
            cards_html += (
                f'<div class="tecnico-card">'
                f'<div style="font-weight:600;font-size:13px;color:#1B4332;">{r["Técnico"]}</div>'
                f'<div style="font-size:11px;color:#74a49c;margin-top:2px;">{r["Atividade"]} · {r["Município"]} &nbsp;{badge}</div>'
                f'<div style="font-size:10px;color:#9ab4ae;margin-top:3px;">📅 Última visita: {data_fmt}</div>'
                f'</div>'
            )
        st.markdown(cards_html, unsafe_allow_html=True)

    with col_r:
        st.subheader("🌿 Técnicos por atividade")
        df_atv_sup = (
            df_sup_sel.groupby("atividade")["tecnico"].nunique().reset_index()
            .rename(columns={"atividade":"Atividade","tecnico":"Técnicos"})
            .sort_values("Técnicos", ascending=True)
        )
        fig_atv_sup = px.bar(
            df_atv_sup, x="Técnicos", y="Atividade", orientation="h",
            color="Técnicos", color_continuous_scale=["#74C69D","#1B4332"], text="Técnicos",
        )
        fig_atv_sup.update_traces(textposition="outside")
        fig_atv_sup.update_layout(**LAYOUT_BASE, height=max(300, len(df_atv_sup)*56),
            coloraxis_showscale=False,
            margin=dict(l=0, r=60, t=10, b=10),
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=False, title=None))
        st.plotly_chart(fig_atv_sup, use_container_width=True)


# ════════════════════════════════════════════
# ABA 4 — ALERTAS & ACOMPANHAMENTO
# ════════════════════════════════════════════
with aba_alertas:
    # drop_duplicates: 1 linha por técnico (evita duplicar pelo nº de municípios)
    df_f_tec = df_f.drop_duplicates(subset=["tecnico"])
    df_critico = df_f_tec[df_f_tec["gap_dias"] > 45].sort_values("gap_dias", ascending=False)
    df_atencao = df_f_tec[(df_f_tec["gap_dias"] > 30) & (df_f_tec["gap_dias"] <= 45)].sort_values("gap_dias", ascending=False)

    col_al1, col_al2 = st.columns(2)

    with col_al1:
        st.markdown(
            f'<div style="font-size:14px;font-weight:700;color:#D94040;margin-bottom:10px;">'
            f'🚨 Crítico — Gap &gt; 45 dias &nbsp;'
            f'<span style="background:#fde8e8;color:#a82e2e;padding:2px 8px;border-radius:10px;font-size:12px;">'
            f'{len(df_critico)}</span></div>',
            unsafe_allow_html=True,
        )
        if df_critico.empty:
            st.success("Nenhum técnico em situação crítica!")
        else:
            html_crit = ""
            for _, r in df_critico.iterrows():
                data_fmt = pd.to_datetime(r["data_ultima_visita"]).strftime("%d/%m/%Y") if pd.notna(r["data_ultima_visita"]) else "—"
                html_crit += (
                    f'<div class="alert-card-critico">'
                    f'<b style="color:#1B4332;font-size:13px;">{r["tecnico"]}</b> &nbsp;'
                    f'<span class="badge-critico">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:11px;color:#444;">{r["atividade"]} · {r["supervisor"]} · {r["nome"]}</span><br>'
                    f'<span style="font-size:10px;color:#555;">📅 Última visita: {data_fmt}</span>'
                    f'</div>'
                )
            st.markdown(html_crit, unsafe_allow_html=True)

    with col_al2:
        st.markdown(
            f'<div style="font-size:14px;font-weight:700;color:#d4900a;margin-bottom:10px;">'
            f'⚠️ Em Atenção — Gap 31–45 dias &nbsp;'
            f'<span style="background:#fef3d8;color:#8a5800;padding:2px 8px;border-radius:10px;font-size:12px;">'
            f'{len(df_atencao)}</span></div>',
            unsafe_allow_html=True,
        )
        if df_atencao.empty:
            st.success("Nenhum técnico em atenção!")
        else:
            html_atencao = ""
            for _, r in df_atencao.iterrows():
                data_fmt = pd.to_datetime(r["data_ultima_visita"]).strftime("%d/%m/%Y") if pd.notna(r["data_ultima_visita"]) else "—"
                html_atencao += (
                    f'<div class="alert-card-atencao">'
                    f'<b style="color:#1B4332;font-size:13px;">{r["tecnico"]}</b> &nbsp;'
                    f'<span class="badge-atencao">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:11px;color:#444;">{r["atividade"]} · {r["supervisor"]} · {r["nome"]}</span><br>'
                    f'<span style="font-size:10px;color:#555;">📅 Última visita: {data_fmt}</span>'
                    f'</div>'
                )
            st.markdown(html_atencao, unsafe_allow_html=True)

    st.divider()
    st.subheader("Ranking de gap — top 20 técnicos")
    df_gap_rank = (
        df_f[df_f["gap_dias"] > 0][["tecnico","gap_dias","atividade"]]
        .drop_duplicates("tecnico").sort_values("gap_dias", ascending=False).head(20)
    )
    df_gap_rank["cor"] = df_gap_rank["gap_dias"].apply(
        lambda x: "#D94040" if x > 45 else ("#d4900a" if x > 30 else "#1D9E75")
    )
    fig_rank = go.Figure(go.Bar(
        x=df_gap_rank["tecnico"], y=df_gap_rank["gap_dias"],
        marker_color=df_gap_rank["cor"],
        text=df_gap_rank["gap_dias"], textposition="outside",
    ))
    # ── Apenas linha dos 30 dias ──
    fig_rank.add_hline(y=45, line_dash="dash", line_color="#D94040", annotation_text="Crítico (>45 dias)")
    fig_rank.add_hline(y=30, line_dash="dot",  line_color="#d4900a", annotation_text="Em Atenção (>30 dias)")
    fig_rank.update_layout(**LAYOUT_BASE, height=380,
        margin=dict(l=0, r=0, t=20, b=80),
        xaxis=dict(tickangle=-40, showgrid=False),
        yaxis=dict(title="Gap (dias)", showgrid=True, gridcolor="#eef4f1"))
    st.plotly_chart(fig_rank, use_container_width=True)

    st.divider()
    st.subheader("📈 Tendência de gap médio — últimas 8 semanas")
    hoje = datetime.now()
    semanas, gaps_medios = [], []
    for i in range(7, -1, -1):
        data_ref = hoje - timedelta(weeks=i)
        df_temp  = df_f.drop_duplicates(subset=["tecnico"])[df_f.drop_duplicates(subset=["tecnico"])["data_ultima_visita"] <= data_ref].copy()
        if not df_temp.empty:
            df_temp["gap_sim"] = (data_ref - df_temp["data_ultima_visita"]).dt.days
            gaps_medios.append(round(df_temp["gap_sim"].mean(), 1))
        else:
            gaps_medios.append(0)
        semanas.append(f"S{8-i}")

    df_trend = pd.DataFrame({"Semana": semanas, "Gap médio (dias)": gaps_medios})
    fig_trend = px.line(df_trend, x="Semana", y="Gap médio (dias)", markers=True,
        line_shape="spline", color_discrete_sequence=["#1D9E75"])
    # ── Apenas linha dos 30 dias ──
    fig_trend.add_hline(y=45, line_dash="dash", line_color="#D94040", annotation_text="Crítico (>45 dias)")
    fig_trend.add_hline(y=30, line_dash="dot",  line_color="#d4900a", annotation_text="Em Atenção (>30 dias)")
    fig_trend.update_layout(**LAYOUT_BASE, height=300,
        margin=dict(l=0, r=0, t=20, b=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#eef4f1"))
    st.plotly_chart(fig_trend, use_container_width=True)

# ════════════════════════════════════════════
# ABA — INTELIGÊNCIA
# ════════════════════════════════════════════
with aba_inteligencia:

    # =========================================
    # 1) RANKING DE PRODUTIVIDADE
    # =========================================
    section_header("Ranking de Produtividade")

    nivel_rank = st.radio("Ver ranking por:", ["Técnico", "Supervisor"], horizontal=True, key="radio_rank_produtividade")
    campo_rank = "tecnico" if nivel_rank == "Técnico" else "supervisor"

    df_prod = (
        df_f.groupby(campo_rank)
        .agg(
            Total=("total_propriedades", "sum"),
            Ativas=("propriedades_ativas", "sum"),
            Inativas=("propriedades_inativas", "sum"),
            Visitas_Validas=("visitas_validas", "sum"),
            Visitas_Invalidas=("visitas_invalidas", "sum"),
            Gap_Medio=("gap_dias", "mean"),
        )
        .reset_index()
    )
    df_prod = df_prod[df_prod["Total"] > 0].copy()
    df_prod["Taxa_Ativas"] = (df_prod["Ativas"] / df_prod["Total"] * 100).round(1)
    df_prod["Total_Visitas"] = df_prod["Visitas_Validas"] + df_prod["Visitas_Invalidas"]
    df_prod["Taxa_Visitas_Validas"] = df_prod.apply(
        lambda r: round((r["Visitas_Validas"] / r["Total_Visitas"]) * 100, 1) if r["Total_Visitas"] > 0 else 0.0,
        axis=1,
    )
    df_prod["Gap_Medio"] = df_prod["Gap_Medio"].round(0).astype(int)

    if df_prod.empty:
        st.warning("Nenhum dado disponível com os filtros atuais.")
    else:
        max_prop_disp = int(df_prod["Total"].max())
        min_prop = st.slider(
            "Mostrar apenas quem tem pelo menos X propriedades (evita distorção de quem tem poucos casos)",
            1, max(2, max_prop_disp), min(3, max_prop_disp), key="slider_min_prop_rank",
        )
        df_prod_f = df_prod[df_prod["Total"] >= min_prop].sort_values("Total", ascending=False).copy()

        if df_prod_f.empty:
            st.warning("Nenhum técnico atinge esse mínimo de propriedades.")
        else:
            if len(df_prod_f) <= 5:
                # Poucos resultados: não faz sentido um slider, mostra tudo direto.
                top_n = len(df_prod_f)
            else:
                top_n = st.slider(
                    "Quantidade no ranking", 5, min(30, len(df_prod_f)), min(15, len(df_prod_f)),
                    key="slider_top_prod",
                )
            df_prod_top = df_prod_f.head(top_n)

            def _cor_faixa(taxa):
                if taxa >= 80: return "#1D9E75"
                if taxa >= 50: return "#d4900a"
                return "#D94040"

            df_prod_top = df_prod_top.copy()
            df_prod_top["cor"] = df_prod_top["Taxa_Ativas"].apply(_cor_faixa)
            df_prod_top["rotulo"] = df_prod_top.apply(
                lambda r: f'{int(r["Total"])} ({r["Taxa_Ativas"]:.0f}%)', axis=1
            )

            fig_prod = go.Figure()
            fig_prod.add_trace(go.Bar(
                x=df_prod_top[campo_rank], y=df_prod_top["Total"],
                marker_color=df_prod_top["cor"],
                text=df_prod_top["rotulo"], textposition="outside",
            ))
            fig_prod.update_layout(**LAYOUT_BASE, height=420,
                margin=dict(l=0, r=0, t=40, b=100),
                xaxis=dict(tickangle=-40, showgrid=False),
                yaxis=dict(title="Total de Propriedades", showgrid=True, gridcolor="#eef4f1"))
            st.plotly_chart(fig_prod, use_container_width=True)

            st.markdown(
                '<div style="font-size:12px;color:#555;margin-top:-10px;margin-bottom:10px;">'
                'Altura da barra = volume de propriedades atendidas · Cor = desempenho '
                '(<span style="color:#1D9E75;font-weight:700;">🟢 ≥80% ativas</span> · '
                '<span style="color:#d4900a;font-weight:700;">🟡 50–79% ativas</span> · '
                '<span style="color:#D94040;font-weight:700;">🔴 &lt;50% ativas</span>) · '
                'Rótulo = total de propriedades (taxa de ativas %)'
                '</div>',
                unsafe_allow_html=True,
            )

            df_prod_tabela = df_prod_top.rename(columns={
                campo_rank: nivel_rank, "Total": "Total Propriedades", "Ativas": "Ativas",
                "Inativas": "Inativas", "Taxa_Ativas": "Taxa Ativas (%)",
                "Visitas_Validas": "Visitas Válidas", "Visitas_Invalidas": "Visitas Inválidas",
                "Taxa_Visitas_Validas": "Taxa Visitas Válidas (%)", "Gap_Medio": "Gap Médio (dias)",
            })[[nivel_rank, "Total Propriedades", "Ativas", "Inativas", "Taxa Ativas (%)",
                "Visitas Válidas", "Visitas Inválidas", "Taxa Visitas Válidas (%)", "Gap Médio (dias)"]]

            st.dataframe(df_prod_tabela, use_container_width=True, hide_index=True)

    st.divider()

    # =========================================
    # 2) BENCHMARK ENTRE REGIÕES / SINDICATOS
    # =========================================
    section_header("Benchmark entre Regiões e Sindicatos")

    nivel_bench = st.radio("Comparar por:", ["Região FAEC", "Sindicato"], horizontal=True, key="radio_bench")
    campo_bench = "regiao_faec" if nivel_bench == "Região FAEC" else "sindicato"

    if campo_bench not in df_f.columns:
        st.warning(f"Campo '{campo_bench}' não encontrado na base.")
    else:
        df_bench = (
            df_f.groupby(campo_bench)
            .agg(
                Total=("total_propriedades", "sum"),
                Ativas=("propriedades_ativas", "sum"),
                Inativas=("propriedades_inativas", "sum"),
                Gap_Medio=("gap_dias", "mean"),
                Tecnicos=("tecnico", "nunique"),
                Supervisores=("supervisor", "nunique"),
            )
            .reset_index()
        )
        df_bench = df_bench[df_bench["Total"] > 0].copy()

        if df_bench.empty:
            st.warning("Nenhum dado disponível com os filtros atuais.")
        else:
            df_bench["Taxa_Ativas"] = (df_bench["Ativas"] / df_bench["Total"] * 100).round(1)
            df_bench["Gap_Medio"] = df_bench["Gap_Medio"].round(0).astype(int)
            df_bench = df_bench.sort_values("Taxa_Ativas", ascending=False)

            # ── Cor por faixa fixa (não mais relativa à média — com tudo entre
            # 98% e 100%, comparar com a média fazia metade virar "vermelho" à toa) ──
            def _cor_taxa(taxa):
                if taxa >= 99: return "#1D9E75"
                if taxa >= 95: return "#d4900a"
                return "#D94040"

            df_bench["cor"] = df_bench["Taxa_Ativas"].apply(_cor_taxa)

            # ── Zoom no eixo Y: começa perto do menor valor, não em 0,
            # pra diferença entre regiões ficar visível ──
            piso_eixo = max(0, float(df_bench["Taxa_Ativas"].min()) - 3)

            col_bench1, col_bench2 = st.columns(2)

            with col_bench1:
                st.markdown(f'<div style="font-size:13px;font-weight:700;color:#1B4332;margin-bottom:6px;">Taxa de Propriedades Ativas (%)</div>', unsafe_allow_html=True)
                fig_bench = go.Figure(go.Bar(
                    x=df_bench[campo_bench], y=df_bench["Taxa_Ativas"],
                    marker_color=df_bench["cor"],
                    text=df_bench["Taxa_Ativas"].astype(str) + "%", textposition="outside",
                ))
                fig_bench.update_layout(**LAYOUT_BASE, height=380,
                    margin=dict(l=0, r=0, t=30, b=90),
                    xaxis=dict(tickangle=-35, showgrid=False),
                    yaxis=dict(title="Taxa Ativas (%)", showgrid=True, gridcolor="#eef4f1",
                               range=[piso_eixo, 101]))
                st.plotly_chart(fig_bench, use_container_width=True)
                st.markdown(
                    '<div style="font-size:11px;color:#666;margin-top:-12px;">'
                    '🟢 ≥99% · 🟡 95–98,9% · 🔴 &lt;95% &nbsp;·&nbsp; eixo começa acima de 0 para destacar a diferença real'
                    '</div>', unsafe_allow_html=True,
                )

            with col_bench2:
                df_bench_inat = df_bench.sort_values("Inativas", ascending=False)
                st.markdown(f'<div style="font-size:13px;font-weight:700;color:#1B4332;margin-bottom:6px;">Propriedades Inativas (nº absoluto)</div>', unsafe_allow_html=True)
                fig_inat = go.Figure(go.Bar(
                    x=df_bench_inat[campo_bench], y=df_bench_inat["Inativas"],
                    marker_color="#D94040",
                    text=df_bench_inat["Inativas"], textposition="outside",
                ))
                fig_inat.update_layout(**LAYOUT_BASE, height=380,
                    margin=dict(l=0, r=0, t=30, b=90),
                    xaxis=dict(tickangle=-35, showgrid=False),
                    yaxis=dict(title="Propriedades Inativas", showgrid=True, gridcolor="#eef4f1"))
                st.plotly_chart(fig_inat, use_container_width=True)
                st.markdown(
                    '<div style="font-size:11px;color:#666;margin-top:-12px;">'
                    'Mostra onde o volume de propriedades inativas está concentrado — útil quando a % sozinha não diferencia bem'
                    '</div>', unsafe_allow_html=True,
                )

            df_bench_tabela = df_bench.rename(columns={
                campo_bench: nivel_bench, "Total": "Total Propriedades", "Ativas": "Ativas",
                "Inativas": "Inativas", "Taxa_Ativas": "Taxa Ativas (%)",
                "Gap_Medio": "Gap Médio (dias)", "Tecnicos": "Técnicos", "Supervisores": "Supervisores",
            })[[nivel_bench, "Total Propriedades", "Ativas", "Inativas", "Taxa Ativas (%)",
                "Gap Médio (dias)", "Técnicos", "Supervisores"]]

            st.dataframe(df_bench_tabela, use_container_width=True, hide_index=True)

            criticos = df_bench[df_bench["Taxa_Ativas"] < 95][campo_bench].tolist()
            if criticos:
                st.warning(f"⚠️ Abaixo de 95% de propriedades ativas: " + ", ".join(criticos))

    st.divider()

    # =========================================
    # 3) RESUMO EXECUTIVO AUTOMÁTICO (IA)
    # =========================================
    section_header("Resumo Executivo Automático")
    st.caption("Gera um resumo em linguagem natural com base nos dados filtrados, usando a API da Anthropic.")

    def _obter_chave_anthropic():
        try:
            return st.secrets["anthropic"]["api_key"]
        except Exception:
            return os.environ.get("ANTHROPIC_API_KEY")

    def gerar_resumo_executivo(df_base):
        chave = _obter_chave_anthropic()
        if not chave:
            return None, "Chave da API Anthropic não configurada. Adicione ANTHROPIC_API_KEY em st.secrets ou variável de ambiente."

        total_prop = int(df_base["total_propriedades"].sum())
        ativas = int(df_base["propriedades_ativas"].sum())
        inativas = int(df_base["propriedades_inativas"].sum())
        taxa_ativas = (ativas / total_prop * 100) if total_prop > 0 else 0
        n_tecnicos = df_base["tecnico"].nunique()
        n_supervisores = df_base["supervisor"].nunique()
        gap_medio = df_base["gap_dias"].mean() if not df_base.empty else 0
        n_criticos = df_base.drop_duplicates("tecnico")[df_base.drop_duplicates("tecnico")["gap_dias"] > 45].shape[0]
        n_atencao = df_base.drop_duplicates("tecnico")[
            (df_base.drop_duplicates("tecnico")["gap_dias"] > 30) & (df_base.drop_duplicates("tecnico")["gap_dias"] <= 45)
        ].shape[0]

        top_atividade = (
            df_base.groupby("atividade")["total_propriedades"].sum().sort_values(ascending=False)
        )
        atividade_destaque = top_atividade.index[0] if not top_atividade.empty else "—"

        prompt = f"""Você é um analista de dados de um programa de assistência técnica rural (ATeG).
Com base nos números abaixo, escreva um resumo executivo curto (máximo 6 frases, em português, tom direto e profissional, sem saudação) destacando: situação geral, pontos de atenção e uma recomendação prática.

Dados atuais (já filtrados conforme seleção do usuário):
- Total de propriedades: {total_prop}
- Propriedades ativas: {ativas} ({taxa_ativas:.1f}%)
- Propriedades inativas: {inativas}
- Técnicos em campo: {n_tecnicos}
- Supervisores: {n_supervisores}
- Gap médio de visita: {gap_medio:.0f} dias
- Técnicos em situação crítica (gap > 45 dias): {n_criticos}
- Técnicos em atenção (gap 31-45 dias): {n_atencao}
- Atividade com maior volume de propriedades: {atividade_destaque}
"""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": chave,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 400,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            return texto.strip(), None
        except Exception as e:
            return None, f"Erro ao chamar a API: {e}"

    if st.button("✨ Gerar Resumo da Semana", key="btn_gerar_resumo_ia"):
        with st.spinner("Gerando resumo..."):
            texto_resumo, erro = gerar_resumo_executivo(df_f)
        if erro:
            st.error(erro)
        else:
            st.markdown(
                f'<div style="background:#f1f8f4;border-left:4px solid #1D9E75;padding:14px 18px;'
                f'border-radius:8px;font-size:14px;color:#1B4332;line-height:1.6;">{texto_resumo}</div>',
                unsafe_allow_html=True,
            )

# ════════════════════════════════════════════
# ABA 5 — EXPORTAR DADOS
# ════════════════════════════════════════════
with aba_download:
    st.subheader("📥 Exportação de Dados")
    st.info(f"Exportando **{len(df_f)}** registros conforme filtros aplicados.")

    COLS_EXPORT = [
        "regiao_faec", "supervisor", "projeto", "atividade", "tecnico",
        "municipios", "municipio_atual", "data_primeira_visita", "data_ultima_visita",
        "tempo_projeto_meses", "status_tecnico",
    ]

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        buffer_full = io.BytesIO()
        with pd.ExcelWriter(buffer_full, engine="xlsxwriter") as writer:
            df_f[COLS_EXPORT].to_excel(writer, sheet_name="Base Completa", index=False)
            (
                df_f.groupby("supervisor")
                .agg(Técnicos=("tecnico","nunique"), Municípios=("municipio_atual","nunique"), Projetos=("projeto","nunique"))
                .reset_index()
                .to_excel(writer, sheet_name="Resumo Supervisores", index=False)
            )
        st.download_button(label="📊 Excel Completo", data=buffer_full.getvalue(),
            file_name=f"ateg_completo_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col_d2:
        st.download_button(label="📄 CSV Base Completa",
            data=df_f[COLS_EXPORT].to_csv(index=False, sep=";").encode("utf-8"),
            file_name=f"ateg_base_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

    with col_d3:
        df_sup_csv = (
            df_f.groupby("supervisor")
            .agg(Técnicos=("tecnico","nunique"), Municípios=("municipio_atual","nunique"), Projetos=("projeto","nunique"))
            .reset_index()
        )
        st.download_button(label="👤 Resumo Supervisores",
            data=df_sup_csv.to_csv(index=False, sep=";").encode("utf-8"),
            file_name=f"ateg_supervisores_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

    st.divider()
    st.subheader("📋 Prévia dos Dados")
    df_preview = df_f.copy()
    df_preview["data_primeira_visita"] = pd.to_datetime(df_preview["data_primeira_visita"]).dt.strftime("%d/%m/%Y")
    df_preview["data_ultima_visita"]   = pd.to_datetime(df_preview["data_ultima_visita"]).dt.strftime("%d/%m/%Y")
    st.dataframe(
        df_preview[COLS_EXPORT].sort_values("tempo_projeto_meses", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "regiao_faec":          "Região FAEC",
            "projeto":              "Projeto",
            "atividade":            "Atividade",
            "supervisor":     "Supervisor",
            "tecnico":              "Técnico",
            "municipios":           "Municípios",
            "municipio_atual":      "Município Atual",
            "data_primeira_visita": "Primeira Visita",
            "data_ultima_visita":   "Última Visita",
            "tempo_projeto_meses":  st.column_config.NumberColumn("Tempo (Meses)", format="%.0f", width="small"),
            "status_tecnico":       "Status",
        },
    )

# ════════════════════════════════════════════
# ABA 6 — CONSOLIDADO
# ════════════════════════════════════════════
with aba_consolidado:
    st.subheader("📋 Tabela Consolidada")

    col_radio, col_spacer = st.columns([3, 1])
    with col_radio:
        tipo_filtro = st.radio(
            "Visualizar por:",
            ["Todos", "Região FAEC", "Supervisor", "Projeto"],
            horizontal=True,
            key="radio_consolidado",
        )

    df_cons_base = df_f.copy()
    escolha = "Todos"

    if tipo_filtro == "Região FAEC":
        opcoes_reg = ["Todos"] + sorted(df_f["regiao_faec"].dropna().unique())
        if len(opcoes_reg) > 1:
            col_f1, col_f2 = st.columns([2, 3])
            with col_f1:
                escolha = st.selectbox("Selecione a Região FAEC", opcoes_reg, key="sb_regiao_cons")
            if escolha == "Todos":
                df_cons_base = df_f.copy()
                muns_regiao = sorted(df_cons_base["nome"].dropna().unique())
            else:
                df_cons_base = df_f[df_f["regiao_faec"] == escolha]
                muns_regiao = sorted(df_cons_base["nome"].dropna().unique())
            with col_f2:
                mun_sel_cons = st.multiselect(
                    f"Municípios ({len(muns_regiao)} disponíveis)",
                    options=muns_regiao,
                    default=[],
                    placeholder="Todos os municípios",
                    key="mun_sel_cons",
                )
            if mun_sel_cons:
                df_cons_base = df_cons_base[df_cons_base["nome"].isin(mun_sel_cons)]
        else:
            st.warning("Nenhuma Região FAEC disponível com os filtros atuais.")
            df_cons_base = pd.DataFrame()

    elif tipo_filtro == "Supervisor":
        opcoes_sv = ["Todos"] + sorted(df_f["supervisor"].dropna().unique())
        if len(opcoes_sv) > 1:
            escolha = st.selectbox("Selecione o Supervisor", opcoes_sv, key="sb_supervisor_cons")
            if escolha == "Todos":
                df_cons_base = df_f.copy()
            else:
                df_cons_base = df_f[df_f["supervisor"] == escolha]
        else:
            st.warning("Nenhum Supervisor disponível.")
            df_cons_base = pd.DataFrame()

    elif tipo_filtro == "Projeto":
        opcoes_pj = ["Todos"] + sorted(df_f["projeto"].dropna().unique())
        if len(opcoes_pj) > 1:
            escolha = st.selectbox("Selecione o Projeto", opcoes_pj, key="sb_projeto_cons")
            if escolha == "Todos":
                df_cons_base = df_f.copy()
            else:
                df_cons_base = df_f[df_f["projeto"] == escolha]
        else:
            st.warning("Nenhum Projeto disponível.")
            df_cons_base = pd.DataFrame()

    st.divider()

    def gerar_excel_consolidado(df_tabela_out, nome_aba="Consolidado"):
        buf = io.BytesIO()
        nome_aba = nome_aba[:31]
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df_tabela_out.to_excel(writer, sheet_name=nome_aba, index=False)
            wb  = writer.book
            ws  = writer.sheets[nome_aba]
            fmt_header = wb.add_format({
                "bold": True, "bg_color": "#2D6A4F", "font_color": "white",
                "border": 1, "align": "center",
            })
            fmt_total = wb.add_format({
                "bold": True, "bg_color": "#1B4332", "font_color": "white",
                "border": 1, "align": "center",
            })
            for col_num, col_name in enumerate(df_tabela_out.columns):
                ws.write(0, col_num, col_name, fmt_header)
                ws.set_column(col_num, col_num, max(len(str(col_name)) + 4, 14))
            last_row = len(df_tabela_out) + 1
            for col_num in range(len(df_tabela_out.columns)):
                ws.write(last_row, col_num, "", fmt_total)
        return buf.getvalue()

    if not df_cons_base.empty:
        df_tabela = (
            df_cons_base.groupby("atividade")
            .agg(
                Supervisores=("supervisor", "nunique"),
                Tecnicos=("tecnico", "nunique"),
                Ativas=("propriedades_ativas", "sum"),
                Inativas=("propriedades_inativas", "sum"),
                Total=("total_propriedades", "sum"),
            )
            .reset_index()
            .sort_values("Total", ascending=False)
        )

        col_dl1, col_dl2, col_spacer2 = st.columns([2, 2, 3])
        with col_dl1:
            df_export_cons = df_tabela.copy()
            df_export_cons.columns = ["Atividade", "Supervisores", "Técnicos", "Prop. Ativas", "Prop. Inativas", "Total Prop."]
            st.download_button(
                label="📥 Exportar Tabela — Excel",
                data=gerar_excel_consolidado(df_export_cons, "Consolidado por Atividade"),
                file_name=f"consolidado_{tipo_filtro.lower().replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_tabela_atividade",
            )
        with col_dl2:
            st.download_button(
                label="📄 Exportar Tabela — CSV",
                data=df_export_cons.to_csv(index=False, sep=";").encode("utf-8"),
                file_name=f"consolidado_{tipo_filtro.lower().replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="dl_tabela_atividade_csv",
            )

        linhas_html = ""
        for _, r in df_tabela.iterrows():
            tot = r["Total"] if r["Total"] > 0 else 1
            pct_a = (r["Ativas"]   / tot) * 100
            pct_i = (r["Inativas"] / tot) * 100
            linhas_html += (
                f'<tr>'
                f'<td style="color:#1B4332;">{r["atividade"]}</td>'
                f'<td style="text-align:center;">{int(r["Supervisores"])}</td>'
                f'<td style="text-align:center;">{int(r["Tecnicos"])}</td>'
                f'<td style="text-align:center;color:#1D9E75;font-weight:600;">{fmt_br(r["Ativas"])} <span style="font-size:11px;color:#52B788;font-weight:400;">({pct_a:.1f}%)</span></td>'
                f'<td style="text-align:center;color:#D94040;font-weight:600;">{fmt_br(r["Inativas"])} <span style="font-size:11px;color:#f3a5a5;font-weight:400;">({pct_i:.1f}%)</span></td>'
                f'<td style="text-align:center;font-weight:700;color:#1B4332;">{fmt_br(r["Total"])}</td>'
                f'</tr>'
            )
        s_sup = int(df_tabela["Supervisores"].sum())
        s_tec = int(df_tabela["Tecnicos"].sum())
        s_atv = int(df_tabela["Ativas"].sum())
        s_ina = int(df_tabela["Inativas"].sum())
        s_tot = int(df_tabela["Total"].sum())
        g_tot = s_tot if s_tot > 0 else 1

        linhas_html += (
            f'<tr style="background:#1B4332;">'
            f'<td style="color:white;font-weight:800;border-bottom:none;">TOTAL GERAL</td>'
            f'<td style="text-align:center;color:white;font-weight:800;border-bottom:none;">{s_sup}</td>'
            f'<td style="text-align:center;color:white;font-weight:800;border-bottom:none;">{s_tec}</td>'
            f'<td style="text-align:center;color:#95d5b2;font-weight:800;border-bottom:none;">{fmt_br(s_atv)} ({s_atv/g_tot*100:.1f}%)</td>'
            f'<td style="text-align:center;color:#f3a5a5;font-weight:800;border-bottom:none;">{fmt_br(s_ina)} ({s_ina/g_tot*100:.1f}%)</td>'
            f'<td style="text-align:center;color:white;font-weight:800;border-bottom:none;">{fmt_br(s_tot)}</td>'
            f'</tr>'
        )

        st.markdown(
            f'<div style="overflow-x:auto;">'
            f'<table class="custom-table">'
            f'<thead><tr>'
            f'<th>Atividade</th><th style="text-align:center;">Supervisores</th>'
            f'<th style="text-align:center;">Técnicos</th>'
            f'<th style="text-align:center;">Prop. Ativas (%)</th>'
            f'<th style="text-align:center;">Prop. Inativas (%)</th>'
            f'<th style="text-align:center;">Total</th>'
            f'</tr></thead><tbody>{linhas_html}</tbody></table></div>',
            unsafe_allow_html=True,
        )

        if tipo_filtro == "Supervisor":
            st.divider()
            st.subheader(f"👥 Técnicos de {escolha}")

            df_tec_detalhe = (
                df_cons_base.groupby("tecnico")
                .agg(
                    Atividade=("atividade", "first"),
                    Ativas=("propriedades_ativas", "sum"),
                    Inativas=("propriedades_inativas", "sum"),
                    Total=("total_propriedades", "sum"),
                    Primeira_Visita=("data_primeira_visita", "min"),
                    Ultima_Visita=("data_ultima_visita", "max"),
                    Tempo_Meses=("tempo_projeto_meses", "mean"),
                )
                .reset_index()
                .sort_values("Total", ascending=False)
            )

            col_dl3, col_dl4, _ = st.columns([2, 2, 3])
            df_tec_export = df_tec_detalhe.copy()
            df_tec_export["Primeira_Visita"] = pd.to_datetime(df_tec_export["Primeira_Visita"], errors="coerce").dt.strftime("%d/%m/%Y")
            df_tec_export["Ultima_Visita"]   = pd.to_datetime(df_tec_export["Ultima_Visita"],   errors="coerce").dt.strftime("%d/%m/%Y")
            df_tec_export["Tempo_Meses"]     = df_tec_export["Tempo_Meses"].round(0).astype("Int64")
            df_tec_export.columns = ["Técnico","Atividade","Prop. Ativas","Prop. Inativas","Total","Primeira Visita","Última Visita","Tempo (meses)"]
            with col_dl3:
                st.download_button(
                    label="📥 Exportar Técnicos — Excel",
                    data=gerar_excel_consolidado(df_tec_export, "Técnicos por Supervisor"),
                    file_name=f"tecnicos_{escolha.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_tec_excel",
                )
            with col_dl4:
                st.download_button(
                    label="📄 Exportar Técnicos — CSV",
                    data=df_tec_export.to_csv(index=False, sep=";").encode("utf-8"),
                    file_name=f"tecnicos_{escolha.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="dl_tec_csv",
                )

            linhas_tec = ""
            for _, r in df_tec_detalhe.iterrows():
                t_p = r["Total"] if r["Total"] > 0 else 1
                p_a = (r["Ativas"]   / t_p) * 100
                p_i = (r["Inativas"] / t_p) * 100
                p_v = pd.to_datetime(r["Primeira_Visita"], errors="coerce")
                u_v = pd.to_datetime(r["Ultima_Visita"],   errors="coerce")
                p_v_str = p_v.strftime("%d/%m/%Y") if pd.notna(p_v) else "—"
                u_v_str = u_v.strftime("%d/%m/%Y") if pd.notna(u_v) else "—"
                meses   = int(round(r["Tempo_Meses"])) if pd.notna(r["Tempo_Meses"]) else 0
                linhas_tec += (
                    f'<tr>'
                    f'<td style="color:#1B4332;font-weight:600;">{r["tecnico"]}</td>'
                    f'<td>{r["Atividade"]}</td>'
                    f'<td style="text-align:center;">{p_v_str}</td>'
                    f'<td style="text-align:center;">{u_v_str}</td>'
                    f'<td style="text-align:center;">{meses}</td>'
                    f'<td style="text-align:center;color:#1D9E75;font-weight:600;">{fmt_br(r["Ativas"])} <span style="font-size:11px;color:#52B788;font-weight:400;">({p_a:.1f}%)</span></td>'
                    f'<td style="text-align:center;color:#D94040;font-weight:600;">{fmt_br(r["Inativas"])} <span style="font-size:11px;color:#f3a5a5;font-weight:400;">({p_i:.1f}%)</span></td>'
                    f'<td style="text-align:center;font-weight:700;color:#1B4332;">{fmt_br(r["Total"])}</td>'
                    f'</tr>'
                )

            t_atv_tec = int(df_tec_detalhe["Ativas"].sum())
            t_ina_tec = int(df_tec_detalhe["Inativas"].sum())
            t_tot_tec = int(df_tec_detalhe["Total"].sum())
            d_t = t_tot_tec if t_tot_tec > 0 else 1

            linhas_tec += (
                f'<tr style="background:#1B4332;">'
                f'<td style="color:white;font-weight:800;border-bottom:none;">TOTAL</td>'
                f'<td style="color:white;border-bottom:none;">—</td>'
                f'<td style="color:white;text-align:center;border-bottom:none;">—</td>'
                f'<td style="color:white;text-align:center;border-bottom:none;">—</td>'
                f'<td style="color:white;text-align:center;font-weight:800;border-bottom:none;">{len(df_tec_detalhe)} técnicos</td>'
                f'<td style="color:#95d5b2;text-align:center;font-weight:800;border-bottom:none;">{fmt_br(t_atv_tec)} ({t_atv_tec/d_t*100:.1f}%)</td>'
                f'<td style="color:#f3a5a5;text-align:center;font-weight:800;border-bottom:none;">{fmt_br(t_ina_tec)} ({t_ina_tec/d_t*100:.1f}%)</td>'
                f'<td style="color:white;text-align:center;font-weight:800;border-bottom:none;">{fmt_br(t_tot_tec)}</td>'
                f'</tr>'
            )

            st.markdown(
                f'<div style="overflow-x:auto;">'
                f'<table class="custom-table">'
                f'<thead><tr>'
                f'<th>Técnico</th><th>Atividade</th>'
                f'<th style="text-align:center;">Primeira Visita</th>'
                f'<th style="text-align:center;">Última Visita</th>'
                f'<th style="text-align:center;">Tempo (meses)</th>'
                f'<th style="text-align:center;">Prop. Ativas (%)</th>'
                f'<th style="text-align:center;">Prop. Inativas (%)</th>'
                f'<th style="text-align:center;">Total</th>'
                f'</tr></thead><tbody>{linhas_tec}</tbody></table></div>',
                unsafe_allow_html=True,
            )

        if tipo_filtro == "Região FAEC":
            st.divider()
            st.subheader(f"🏙️ Municípios da Região {escolha}")

            df_mun_cons = (
                df_cons_base.groupby("nome")
                .agg(
                    Técnicos=("tecnico", "nunique"),
                    Ativas=("propriedades_ativas", "sum"),
                    Inativas=("propriedades_inativas", "sum"),
                    Total=("total_propriedades", "sum"),
                )
                .reset_index()
                .rename(columns={"nome": "Município"})
                .sort_values("Total", ascending=False)
            )

            col_dl5, _ = st.columns([2, 5])
            with col_dl5:
                df_mun_exp = df_mun_cons.copy()
                st.download_button(
                    label="📥 Exportar Municípios — Excel",
                    data=gerar_excel_consolidado(df_mun_exp, f"Municípios {escolha}"),
                    file_name=f"municipios_{escolha.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_mun_excel",
                )

            linhas_mun = ""
            for _, r in df_mun_cons.iterrows():
                t_m = r["Total"] if r["Total"] > 0 else 1
                p_a = (r["Ativas"]   / t_m) * 100
                p_i = (r["Inativas"] / t_m) * 100
                linhas_mun += (
                    f'<tr>'
                    f'<td style="color:#1B4332;font-weight:500;">{r["Município"]}</td>'
                    f'<td style="text-align:center;">{int(r["Técnicos"])}</td>'
                    f'<td style="text-align:center;color:#1D9E75;font-weight:600;">{fmt_br(r["Ativas"])} <span style="font-size:11px;color:#52B788;font-weight:400;">({p_a:.1f}%)</span></td>'
                    f'<td style="text-align:center;color:#D94040;font-weight:600;">{fmt_br(r["Inativas"])} <span style="font-size:11px;color:#f3a5a5;font-weight:400;">({p_i:.1f}%)</span></td>'
                    f'<td style="text-align:center;font-weight:700;color:#1B4332;">{fmt_br(r["Total"])}</td>'
                    f'</tr>'
                )
            st.markdown(
                f'<div style="overflow-x:auto;">'
                f'<table class="custom-table">'
                f'<thead><tr>'
                f'<th>Município</th>'
                f'<th style="text-align:center;">Técnicos</th>'
                f'<th style="text-align:center;">Prop. Ativas (%)</th>'
                f'<th style="text-align:center;">Prop. Inativas (%)</th>'
                f'<th style="text-align:center;">Total</th>'
                f'</tr></thead><tbody>{linhas_mun}</tbody></table></div>',
                unsafe_allow_html=True,
            )

    else:
        st.info("Altere os filtros da barra lateral para exibir os dados consolidados.")

# ════════════════════════════════════════════
# ABA 7 — HISTÓRICO DE TROCAS
# ════════════════════════════════════════════
with aba_historico:

    @st.cache_data(ttl=60)
    def carregar_historico():
        engine_pg = get_engine()
        try:
            with engine_pg.connect() as conn:
                return pd.read_sql(text("SELECT * FROM public.historico_trocas ORDER BY data_troca DESC"), conn)
        except Exception:
            return pd.DataFrame(columns=[
                "id","data_troca","tipo_troca","projeto","atividade",
                "regiao_faec","pessoa_saindo","pessoa_entrando",
                "motivo","observacao","registrado_por","data_registro"
            ])

    def salvar_troca(dados):
        engine_pg = get_engine()
        with engine_pg.connect() as conn:
            conn.execute(text("""
                INSERT INTO public.historico_trocas
                    (data_troca, tipo_troca, projeto, atividade, regiao_faec,
                     pessoa_saindo, pessoa_entrando, motivo, observacao, registrado_por)
                VALUES
                    (:data_troca, :tipo_troca, :projeto, :atividade, :regiao_faec,
                     :pessoa_saindo, :pessoa_entrando, :motivo, :observacao, :registrado_por)
            """), dados)
            conn.commit()

    df_hist = carregar_historico()

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    col_h1.metric("🔄 Total de Trocas",       len(df_hist))
    col_h2.metric("👤 Trocas de Técnico",     len(df_hist[df_hist["tipo_troca"]=="Técnico"])    if not df_hist.empty else 0)
    col_h3.metric("🧑‍💼 Trocas de Supervisor", len(df_hist[df_hist["tipo_troca"]=="Supervisor"]) if not df_hist.empty else 0)
    col_h4.metric("📅 Último Registro",
        df_hist["data_troca"].max().strftime("%d/%m/%Y") if not df_hist.empty and pd.notna(df_hist["data_troca"].max()) else "—"
    )

    st.divider()
    col_form, col_tabela = st.columns([1, 2])

    with col_form:
        st.subheader("➕ Registrar Troca")

        supervisor_sel = st.selectbox(
            "🧑‍💼 Supervisor", sorted(df_f["supervisor"].dropna().unique()), key="sup_form_sel"
        )
        tecnicos_sup = sorted(df_f[df_f["supervisor"]==supervisor_sel]["tecnico"].dropna().unique())
        st.caption(f"{len(tecnicos_sup)} técnicos vinculados")

        acao = st.radio("Ação", ["➕ Vincular técnico", "➖ Desvincular técnico"], horizontal=True, key="acao_troca")

        tecnico_novo = False
        supervisor_destino_ext = supervisor_sel
        if acao == "➕ Vincular técnico":
            supervisor_destino_ext = st.selectbox(
                "🧑‍💼 Vincular para qual supervisor",
                sorted(df_f["supervisor"].dropna().unique()), key="sup_dest_ext"
            )
            tecnico_novo = st.checkbox("É um técnico novo (não está na lista)?", key="chk_novo")

        with st.form("form_troca", clear_on_submit=True):
            data_troca = st.date_input("📅 Data", value=datetime.now().date())

            if acao == "➕ Vincular técnico":
                if tecnico_novo:
                    novo_tecnico = st.text_input("👤 Nome do novo técnico")
                else:
                    novo_tecnico = st.selectbox("👤 Técnico a vincular", sorted(df_f["tecnico"].dropna().unique()))
                pessoa_saindo      = "—"
                supervisor_destino = supervisor_destino_ext
                tipo_registro      = "Vínculo"
                motivo_label       = "❓ Motivo da entrada"
            else:
                supervisor_destino = supervisor_sel
                pessoa_saindo = st.selectbox("👤 Técnico a desvincular", tecnicos_sup)
                novo_tecnico  = "—"
                tipo_registro = "Desvinculo"
                motivo_label  = "❓ Motivo do desvinculo"

            motivo = st.selectbox(motivo_label, [
                "Desligamento","Transferência","Licença","Promoção","Aprovado pelo Credenciamento","Outro"
            ])
            observacao     = st.text_area("📝 Observação (opcional)", height=50)
            registrado_por = st.text_input("✍️ Registrado por")
            submitted = st.form_submit_button("💾 Salvar", use_container_width=True)

            if submitted:
                if not registrado_por.strip():
                    st.error("Preencha quem registrou.")
                elif acao == "➕ Vincular técnico" and not str(novo_tecnico).strip():
                    st.error("Informe o técnico a vincular.")
                else:
                    dados_tec = df_f[
                        (df_f["supervisor"]==supervisor_sel) &
                        (df_f["tecnico"]==pessoa_saindo)
                    ]
                    projeto_troca   = dados_tec.iloc[0]["projeto"]     if not dados_tec.empty else ""
                    atividade_troca = dados_tec.iloc[0]["atividade"]   if not dados_tec.empty else ""
                    regiao_troca    = dados_tec.iloc[0]["regiao_faec"] if not dados_tec.empty else ""
                    try:
                        salvar_troca({
                            "data_troca":      str(data_troca),
                            "tipo_troca":      "Técnico",
                            "projeto":         projeto_troca,
                            "atividade":       atividade_troca,
                            "regiao_faec":     regiao_troca,
                            "pessoa_saindo":   pessoa_saindo.upper(),
                            "pessoa_entrando": str(novo_tecnico).strip().upper(),
                            "motivo":          motivo,
                            "observacao":      f"Ação: {tipo_registro} | Supervisor origem: {supervisor_sel} | Supervisor destino: {supervisor_destino}" + (f" | {observacao}" if observacao else ""),
                            "registrado_por":  registrado_por.strip().upper(),
                        })
                        st.success(f"✅ {tipo_registro} registrado!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    with col_tabela:
        st.subheader("📋 Histórico de Trocas")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos","Técnico","Supervisor"], key="hist_tipo")
        with col_f2:
            filtro_proj = st.selectbox("Filtrar por projeto", ["Todos"] + sorted(df_f["projeto"].dropna().unique()), key="hist_proj")

        df_hist_f = df_hist.copy()
        if filtro_tipo != "Todos":
            df_hist_f = df_hist_f[df_hist_f["tipo_troca"]==filtro_tipo]
        if filtro_proj != "Todos":
            df_hist_f = df_hist_f[df_hist_f["projeto"]==filtro_proj]

        if df_hist_f.empty:
            st.info("Nenhuma troca registrada ainda.")
        else:
            df_hist_f["data_troca"] = pd.to_datetime(df_hist_f["data_troca"]).dt.strftime("%d/%m/%Y")

            def extrair_campo(obs, campo):
                if pd.isna(obs): return "—"
                for part in str(obs).split("|"):
                    if f"{campo}:" in part:
                        return part.split(":",1)[1].strip()
                return "—"

            df_hist_f["acao"]        = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Ação"))
            df_hist_f["sup_origem"]  = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Supervisor origem"))
            df_hist_f["sup_destino"] = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Supervisor destino"))

            linhas_hist = ""
            for _, r in df_hist_f.iterrows():
                cor_acao = "#1D9E75" if "Vínculo" in str(r["acao"]) else "#D94040"
                linhas_hist += (
                    f'<tr>'
                    f'<td style="white-space:nowrap;font-size:12px;">{r["data_troca"]}</td>'
                    f'<td><span style="background:{cor_acao}22;color:{cor_acao};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{r["acao"]}</span></td>'
                    f'<td style="font-size:12px;color:#555;">{r["sup_origem"]}</td>'
                    f'<td style="font-size:12px;color:#1B4332;font-weight:600;">{r["sup_destino"]}</td>'
                    f'<td style="font-size:12px;color:#D94040;">{r["pessoa_saindo"]}</td>'
                    f'<td style="font-size:12px;color:#1D9E75;font-weight:600;">{r["pessoa_entrando"]}</td>'
                    f'<td style="font-size:12px;">{r["motivo"]}</td>'
                    f'</tr>'
                )

            st.markdown(
                f'<div style="overflow-x:auto;">'
                f'<table class="custom-table">'
                f'<thead><tr>'
                f'<th>Data</th><th>Ação</th><th>Sup. Origem</th>'
                f'<th>Sup. Destino</th><th>Saiu</th><th>Entrou</th><th>Motivo</th>'
                f'</tr></thead><tbody>{linhas_hist}</tbody></table></div>',
                unsafe_allow_html=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)
            df_export_hist = df_hist_f[["data_troca","acao","sup_origem","sup_destino","pessoa_saindo","pessoa_entrando","motivo"]].copy()
            df_export_hist.columns = ["Data","Ação","Sup. Origem","Sup. Destino","Saiu","Entrou","Motivo"]
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df_export_hist.to_excel(writer, sheet_name="Histórico Trocas", index=False)
            st.download_button(
                label="📥 Baixar Excel",
                data=buf.getvalue(),
                file_name=f"historico_trocas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.divider()
            st.markdown("**🗑️ Excluir registro**")
            ids_disp = df_hist_f["id"].tolist()
            id_excluir = st.selectbox(
                "Selecione o ID para excluir", ids_disp,
                format_func=lambda x: f"ID {x} — {df_hist_f[df_hist_f['id']==x]['pessoa_saindo'].values[0]} → {df_hist_f[df_hist_f['id']==x]['pessoa_entrando'].values[0]}",
                key="del_id"
            )
            if st.button("🗑️ Excluir", type="secondary", key="btn_del"):
                try:
                    engine_pg = get_engine()
                    with engine_pg.connect() as conn:
                        conn.execute(text("DELETE FROM public.historico_trocas WHERE id = :id"), {"id": int(id_excluir)})
                        conn.commit()
                    st.success(f"Registro ID {id_excluir} excluído!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

        st.divider()
        if not df_hist.empty:
            st.subheader("⚠️ Projetos com mais trocas")
            df_instavel = (
                df_hist.groupby("projeto").size().reset_index(name="Trocas")
                .sort_values("Trocas", ascending=False).head(8)
            )
            fig_inst = px.bar(
                df_instavel, x="Trocas", y="projeto", orientation="h",
                color="Trocas", color_continuous_scale=["#74C69D","#D94040"], text="Trocas",
            )
            fig_inst.update_traces(textposition="outside")
            fig_inst.update_layout(**LAYOUT_BASE, height=300, coloraxis_showscale=False,
                margin=dict(l=0, r=40, t=10, b=10),
                xaxis=dict(showgrid=False, title=None),
                yaxis=dict(showgrid=False, title=None))
            st.plotly_chart(fig_inst, use_container_width=True)