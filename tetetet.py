import streamlit as st
import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
import warnings
import requests
import io
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
st.set_page_config(page_title="Monitoramento ATeG", layout="wide", page_icon="🌱")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #f8faf9; }
[data-testid="stSidebar"]          { background-color: #f0f7f4; }
[data-testid="stMetricValue"]      { font-size: 28px !important; font-weight: 700 !important; color: #0F6E56 !important; }
[data-testid="stMetricLabel"]      { font-size: 13px !important; color: #2D6A4F !important; font-weight: 500 !important; }
h1 { color: #1B4332 !important; font-size: 22px !important; font-weight: 700 !important; }
h2 { color: #2D6A4F !important; font-size: 17px !important; font-weight: 600 !important; }
.equipe-assinatura { font-size: 11px; color: #52796f; margin-top: -12px; margin-bottom: 18px; }
.alert-card-critico {
    background: #fff5f5; border-left: 4px solid #E24B4A;
    border-radius: 8px; padding: 10px 14px; margin-bottom: 7px;
}
.alert-card-atencao {
    background: #fffbf0; border-left: 4px solid #BA7517;
    border-radius: 8px; padding: 10px 14px; margin-bottom: 7px;
}
.badge-critico { background:#fde8e8; color:#A32D2D; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-atencao { background:#fef3d8; color:#854F0B; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-ok      { background:#e0f5ec; color:#0F6E56; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; }
.sec-header {
    font-size: 13px; font-weight: 600; color: #2D6A4F;
    border-bottom: 2px solid #c8e6d5; padding-bottom: 4px;
    margin-bottom: 12px; margin-top: 4px;
}
.leaflet-popup-content-wrapper { background: transparent !important; box-shadow: none !important; padding: 0 !important; }
.leaflet-popup-tip-container    { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CABEÇALHO
# ─────────────────────────────────────────────
col_title, col_hora = st.columns([5, 1])
with col_title:
    st.title("🌱 Assistência Técnica e Gerencial — ATeG")
    st.markdown('<p class="equipe-assinatura">Equipe CIIAGRO · atualizado a cada 5 min</p>', unsafe_allow_html=True)
with col_hora:
    st.markdown(
        f"<p style='text-align:right;font-size:12px;color:#52796f;padding-top:16px;'>"
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# 3. CARREGAMENTO
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_dados():
    engine_pg = get_engine()
    with engine_pg.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM public.mapa_consolidado_ateg"), conn)
    df['data_ultima_visita'] = pd.to_datetime(df['data_ultima_visita'], errors='coerce')
    df['data_atualizacao']   = pd.to_datetime(df['data_atualizacao'],   errors='coerce')
    hoje = pd.Timestamp('today').normalize()
    df['gap_dias'] = (hoje - df['data_ultima_visita']).dt.days.fillna(0).clip(lower=0).astype(int)
    return df

@st.cache_data(ttl=3600)
def carregar_geojson():
    try:
        return requests.get("https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json", timeout=10).json()
    except: return None

@st.cache_data(ttl=3600)
def carregar_coordenadas():
    df = pd.read_csv("https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv")
    df['codigo_ibge'] = df['codigo_ibge'].astype(str)
    return df

df_raw    = carregar_dados()
geo_ceara = carregar_geojson()
df_coords = carregar_coordenadas()

# ─────────────────────────────────────────────
# 4. PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────
df_proc = (df_raw.assign(cod_ibge=df_raw['codigos_ibge'].astype(str).str.split(', ')).explode('cod_ibge'))
df_proc['cod_ibge'] = df_proc['cod_ibge'].astype(str).str.strip()
df_mapa = df_proc.merge(df_coords, left_on='cod_ibge', right_on='codigo_ibge', how='inner')

def status_gap(g):
    if g > 30: return "🔴 Crítico"
    if g > 15: return "🟡 Atenção"
    return "🟢 OK"
df_mapa['status_gap'] = df_mapa['gap_dias'].apply(status_gap)

# ─────────────────────────────────────────────
# 5. SIDEBAR — FILTROS
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filtros")
st.sidebar.markdown("---")

regioes_disp = sorted(df_mapa['regiao_faec'].dropna().unique())
regiao_sel = st.sidebar.multiselect("📍 Região FAEC", regioes_disp)

min_m, max_m = int(df_mapa['tempo_projeto_meses'].min()), int(df_mapa['tempo_projeto_meses'].max())
meses_sel = st.sidebar.slider("⏱️ Tempo de Projeto (Meses)", min_m, max_m, (min_m, max_m))

sup_sel  = st.sidebar.multiselect("👤 Supervisores",  sorted(df_mapa['supervisor_atual'].dropna().unique()))
proj_sel = st.sidebar.multiselect("📂 Projetos",      sorted(df_mapa['projeto'].dropna().unique()))
atv_sel  = st.sidebar.multiselect("🌿 Atividades",    sorted(df_mapa['atividade'].dropna().unique()))

status_opcoes = ["Todos", "🔴 Crítico (>30 dias)", "🟡 Atenção (16–30 dias)", "🟢 OK (≤15 dias)"]
status_sel    = st.sidebar.selectbox("⚠️ Status do Gap", status_opcoes)

df_f = df_mapa.copy()
if regiao_sel: df_f = df_f[df_f['regiao_faec'].isin(regiao_sel)]
if sup_sel:  df_f = df_f[df_f['supervisor_atual'].isin(sup_sel)]
if proj_sel: df_f = df_f[df_f['projeto'].isin(proj_sel)]
if atv_sel:  df_f = df_f[df_f['atividade'].isin(atv_sel)]
df_f = df_f[(df_f['tempo_projeto_meses'] >= meses_sel[0]) & (df_f['tempo_projeto_meses'] <= meses_sel[1])]

if status_sel == "🔴 Crítico (>30 dias)":     df_f = df_f[df_f['gap_dias'] > 30]
elif status_sel == "🟡 Atenção (16–30 dias)": df_f = df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)]
elif status_sel == "🟢 OK (≤15 dias)":        df_f = df_f[df_f['gap_dias'] <= 15]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(df_f)}** registros no filtro")

# ─────────────────────────────────────────────
# 6. KPIs
# ─────────────────────────────────────────────
n_tec = df_f['tecnico'].nunique()
n_atv_kpi = df_f['atividade'].nunique()
n_proj_kpi = df_f['projeto'].nunique()
n_mun = df_f['nome'].nunique()
media_mes = round(df_f['tempo_projeto_meses'].mean(), 1) if not df_f.empty else 0
n_critico = int((df_f['gap_dias'] > 30).sum())
pct_critico = round(n_critico / len(df_f) * 100, 1) if len(df_f) > 0 else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("👤 Técnicos", n_tec)
k2.metric("🌱 Atividades", n_atv_kpi)
k3.metric("📂 Projetos", n_proj_kpi)
k4.metric("🏙️ Municípios", n_mun)
k5.metric("📈 Média Meses", media_mes)
k6.metric("🚨 Gap Crítico", n_critico, delta=f"{pct_critico}%", delta_color="inverse")

st.divider()

# ─────────────────────────────────────────────
# 7. ABAS
# ─────────────────────────────────────────────
aba_visao, aba_equipe, aba_mapa_tab, aba_alertas, aba_download = st.tabs([
    "📊 Visão Geral", "👥 Equipe & Projetos", "🗺️ Mapa Operacional", "🚨 Alertas", "📥 Exportar"
])

# VISÃO GERAL
with aba_visao:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="sec-header">Técnicos por atividade</div>', unsafe_allow_html=True)
        df_atv_vis = df_f.groupby('atividade')['tecnico'].nunique().reset_index().rename(columns={'atividade': 'Atividade', 'tecnico': 'Técnicos'}).sort_values('Técnicos', ascending=True)
        fig_a = px.bar(df_atv_vis, x='Técnicos', y='Atividade', orientation='h', color='Técnicos', color_continuous_scale='Greens', text='Técnicos')
        fig_a.update_layout(height=max(300, len(df_atv_vis)*36), margin=dict(l=0, r=40, t=10, b=10), coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_a, use_container_width=True)
    with col_b:
        st.markdown('<div class="sec-header">Status do gap — visão geral</div>', unsafe_allow_html=True)
        contagem = df_f['status_gap'].value_counts().reset_index()
        contagem.columns = ['Status', 'Qtd']
        cor_map = {"🔴 Crítico": "#E24B4A", "🟡 Atenção": "#BA7517", "🟢 OK": "#1D9E75"}
        fig_b = px.pie(contagem, names='Status', values='Qtd', color='Status', color_discrete_map=cor_map, hole=0.55)
        fig_b.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=10), legend=dict(orientation='h', y=-0.15))
        st.plotly_chart(fig_b, use_container_width=True)

# ABA 2 — EQUIPE & PROJETOS
with aba_equipe:
    st.markdown('<div class="sec-header">👤 Resumo por supervisor</div>', unsafe_allow_html=True)
    df_sup_res = df_f.groupby('supervisor_atual').agg(
        Tec=('tecnico', 'nunique'), Mun=('nome', 'nunique'), Proj=('projeto', 'nunique'), Gap=('gap_dias', 'mean'), Crit=('gap_dias', lambda x: int((x > 30).sum()))
    ).reset_index().rename(columns={'supervisor_atual': 'Supervisor'}).sort_values('Gap', ascending=False)
    
    for c in ['Tec', 'Mun', 'Proj', 'Crit']: df_sup_res[c] = df_sup_res[c].fillna(0).astype(int)

    st.dataframe(df_sup_res.style.format({'Gap': '{:.1f}', 'Tec': '{:d}', 'Mun': '{:d}', 'Proj': '{:d}', 'Crit': '{:d}'})
                 .background_gradient(subset=['Gap'], cmap='YlGn', vmax=60).background_gradient(subset=['Crit'], cmap='PuRd', vmax=15)
                 .set_properties(**{'font-size': '11px', 'padding': '0px'}), use_container_width=False, hide_index=True, height=220)

    st.divider()
    st.markdown('<div class="sec-header">🌿 Detalhamento por Atividade</div>', unsafe_allow_html=True)
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        proj_detalhe = st.selectbox("1. Selecione o Projeto:", sorted(df_f['projeto'].dropna().unique()), key='sel_proj_aba2')
    
    df_det = df_f[df_f['projeto'] == proj_detalhe]
    
    with col_sel2:
        atv_detalhe = st.selectbox("2. Selecione a Atividade:", sorted(df_det['atividade'].dropna().unique()), key='sel_atv_aba2')

    # CORREÇÃO: Filtrando a tabela para mostrar apenas a atividade selecionada acima
    df_por_proj = df_det[df_det['atividade'] == atv_detalhe].groupby('atividade').agg(
        Tec=('tecnico', 'nunique'), 
        Gap=('gap_dias', 'mean'), 
        Crit=('gap_dias', lambda x: int((x > 30).sum()))
    ).reset_index().rename(columns={'atividade': 'Atividade'})
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        # Gráfico comparativo (mostra todas as atividades do projeto selecionado)
        df_atv_proj = df_det.groupby('atividade')['tecnico'].nunique().reset_index().rename(columns={'atividade': 'Atividade', 'tecnico': 'Tec'})
        fig_atv = px.bar(df_atv_proj, x='Tec', y='Atividade', orientation='h', color='Tec', color_continuous_scale='Greens', text_auto=True)
        fig_atv.update_layout(height=200, margin=dict(l=0, r=10, t=0, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_atv, use_container_width=True)
    with col_g2:
        # Tabela resumo (mostra apenas a atividade selecionada no passo 2)
        st.dataframe(df_por_proj.style.format({'Gap': '{:.1f}', 'Tec': '{:d}', 'Crit': '{:d}'}).set_properties(**{'font-size': '11px'}), use_container_width=True, hide_index=True, height=200)

    st.divider()
    st.markdown(f'<div class="sec-header">👤 Técnicos em: {atv_detalhe}</div>', unsafe_allow_html=True)
    df_tec_lista = df_det[df_det['atividade'] == atv_detalhe][['tecnico', 'supervisor_atual', 'gap_dias', 'tempo_projeto_meses']].drop_duplicates('tecnico').sort_values('gap_dias', ascending=False)
    df_tec_lista['gap_dias'] = df_tec_lista['gap_dias'].fillna(0).astype(int)
    df_tec_lista['tempo_projeto_meses'] = df_tec_lista['tempo_projeto_meses'].fillna(0).astype(int)
    st.dataframe(df_tec_lista.style.format({'gap_dias': '{:d}', 'tempo_projeto_meses': '{:d}'}).background_gradient(subset=['gap_dias'], cmap='YlGn', vmax=45).set_properties(**{'font-size': '11px'}), use_container_width=True, hide_index=True, height=250)

# ABA 3 — MAPA
with aba_mapa_tab:
    CORES = ["#1D9E75","#E63946","#1D3557","#FFB703","#7B2D8B","#FB8500"]
    cor_atv_map = {atv: CORES[i % len(CORES)] for i, atv in enumerate(sorted(df_f['atividade'].dropna().unique()))}
    col_map, col_leg = st.columns([4, 1])
    with col_leg:
        for atv, cor in cor_atv_map.items():
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;"><div style="width:12px;height:12px;background:{cor};border-radius:50%;"></div><span style="font-size:11px;">{atv}</span></div>', unsafe_allow_html=True)
    with col_map:
        m = folium.Map(location=[-5.2, -39.5], zoom_start=7, tiles='cartodbpositron')
        for _, row in df_f.iterrows():
            folium.Marker([row['latitude'], row['longitude']], icon=DivIcon(html=f'<div style="width:30px;height:30px;border-radius:50%;background:{cor_atv_map.get(row["atividade"], "#CCC")};border:2px solid white;color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;">{str(row["tecnico"])[0]}</div>')).add_to(m)
        st_folium(m, width='100%', height=600)

# ABA 4 — ALERTAS
with aba_alertas:
    c1, c2 = st.columns(2)
    df_crit = df_f[df_f['gap_dias'] > 30]
    with c1:
        st.markdown(f'<div class="sec-header">🚨 Crítico ({len(df_crit)})</div>', unsafe_allow_html=True)
        for _, r in df_crit.iterrows():
            st.markdown(f'<div class="alert-card-critico"><b>{r["tecnico"]}</b> - {r["gap_dias"]} dias</div>', unsafe_allow_html=True)

# ABA 5 — EXPORTAR
with aba_download:
    st.subheader("📥 Exportação de Dados")
    df_export = df_f[['regiao_faec', 'projeto', 'atividade', 'supervisor_atual', 'tecnico', 'nome', 'data_ultima_visita', 'gap_dias', 'status_gap']].sort_values(['regiao_faec', 'supervisor_atual'], ascending=[True, True])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, sheet_name='Base', index=False)
        df_sup_res.to_excel(writer, sheet_name='Supervisores', index=False)
    st.download_button("📊 Baixar Excel", data=buf.getvalue(), file_name="ateg_relatorio.xlsx", mime="application/vnd.ms-excel")
    st.dataframe(df_export, use_container_width=True, hide_index=True)