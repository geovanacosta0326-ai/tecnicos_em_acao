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
    # Gap: dias desde a última visita até hoje — sempre >= 0
    hoje = pd.Timestamp('today').normalize()
    df['gap_dias'] = (hoje - df['data_ultima_visita']).dt.days.fillna(0).clip(lower=0).astype(int)
    return df

@st.cache_data(ttl=3600)
def carregar_geojson():
    try:
        return requests.get(
            "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json",
            timeout=10
        ).json()
    except:
        return None

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
df_proc = (
    df_raw
    .assign(cod_ibge=df_raw['codigos_ibge'].astype(str).str.split(', '))
    .explode('cod_ibge')
)
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

min_m, max_m = int(df_mapa['tempo_projeto_meses'].min()), int(df_mapa['tempo_projeto_meses'].max())
meses_sel = st.sidebar.slider("⏱️ Tempo de Projeto (Meses)", min_m, max_m, (min_m, max_m))

sup_sel  = st.sidebar.multiselect("👤 Supervisores",  sorted(df_mapa['supervisor_atual'].dropna().unique()))
proj_sel = st.sidebar.multiselect("📂 Projetos",      sorted(df_mapa['projeto'].dropna().unique()))
atv_sel  = st.sidebar.multiselect("🌿 Atividades",    sorted(df_mapa['atividade'].dropna().unique()))

status_opcoes = ["Todos", "🔴 Crítico (>30 dias)", "🟡 Atenção (16–30 dias)", "🟢 OK (≤15 dias)"]
status_sel    = st.sidebar.selectbox("⚠️ Status do Gap", status_opcoes)

df_f = df_mapa.copy()
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
n_tec       = df_f['tecnico'].nunique()
n_atv_kpi   = df_f['atividade'].nunique()
n_proj_kpi  = df_f['projeto'].nunique()
n_mun       = df_f['nome'].nunique()
media_mes   = round(df_f['tempo_projeto_meses'].mean(), 1) if not df_f.empty else 0
n_critico   = int((df_f['gap_dias'] > 30).sum())
pct_critico = round(n_critico / len(df_f) * 100, 1) if len(df_f) > 0 else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("👤 Técnicos",    n_tec)
k2.metric("🌱 Atividades",  n_atv_kpi)
k3.metric("📂 Projetos",    n_proj_kpi)
k4.metric("🏙️ Municípios",  n_mun)
k5.metric("📈 Média Meses", media_mes)
k6.metric("🚨 Gap Crítico", n_critico,
          delta=f"{pct_critico}% do total", delta_color="inverse")

st.divider()

# ─────────────────────────────────────────────
# 7. ABAS
# ─────────────────────────────────────────────
aba_visao, aba_equipe, aba_mapa_tab, aba_alertas, aba_download = st.tabs([
    "📊 Visão Geral",
    "👥 Equipe & Projetos",
    "🗺️ Mapa Operacional",
    "🚨 Alertas",
    "📥 Exportar"
])

# ══════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ══════════════════════════════════════════════
with aba_visao:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="sec-header">Técnicos por atividade</div>', unsafe_allow_html=True)
        df_atv_vis = (
            df_f.groupby('atividade')['tecnico'].nunique().reset_index()
            .rename(columns={'atividade': 'Atividade', 'tecnico': 'Técnicos'})
            .sort_values('Técnicos', ascending=True)
        )
        fig_a = px.bar(df_atv_vis, x='Técnicos', y='Atividade', orientation='h',
                       color='Técnicos', color_continuous_scale='Greens', text='Técnicos')
        fig_a.update_traces(textposition='outside')
        fig_a.update_layout(height=max(300, len(df_atv_vis)*36),
                            margin=dict(l=0, r=40, t=10, b=10),
                            coloraxis_showscale=False,
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_a, use_container_width=True)

    with col_b:
        st.markdown('<div class="sec-header">Status do gap — visão geral</div>', unsafe_allow_html=True)
        contagem = df_f['status_gap'].value_counts().reset_index()
        contagem.columns = ['Status', 'Qtd']
        cor_map = {"🔴 Crítico": "#E24B4A", "🟡 Atenção": "#BA7517", "🟢 OK": "#1D9E75"}
        fig_b = px.pie(contagem, names='Status', values='Qtd',
                       color='Status', color_discrete_map=cor_map, hole=0.55)
        fig_b.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=10),
                            legend=dict(orientation='h', y=-0.15),
                            paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_b, use_container_width=True)

    st.divider()
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown('<div class="sec-header">Top 10 municípios — nº de técnicos</div>', unsafe_allow_html=True)
        df_mun_top = (
            df_f.groupby('nome')['tecnico'].nunique().reset_index()
            .rename(columns={'nome': 'Município', 'tecnico': 'Técnicos'})
            .sort_values('Técnicos', ascending=False).head(10)
        )
        fig_c = px.bar(df_mun_top, x='Município', y='Técnicos',
                       color='Técnicos', color_continuous_scale='teal', text='Técnicos')
        fig_c.update_traces(textposition='outside')
        fig_c.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=90),
                            coloraxis_showscale=False,
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(tickangle=-35, showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_c, use_container_width=True)

    with col_d:
        st.markdown('<div class="sec-header">Tempo médio por projeto (meses)</div>', unsafe_allow_html=True)
        df_proj_med = (
            df_f.groupby('projeto')['tempo_projeto_meses'].mean().reset_index()
            .rename(columns={'projeto': 'Projeto', 'tempo_projeto_meses': 'Média (meses)'})
        )
        df_proj_med['Média (meses)'] = df_proj_med['Média (meses)'].round(1)
        df_proj_med = df_proj_med.sort_values('Média (meses)', ascending=True)
        fig_d = px.bar(df_proj_med, x='Média (meses)', y='Projeto', orientation='h',
                       color='Média (meses)', color_continuous_scale='Blues', text='Média (meses)')
        fig_d.update_traces(textposition='outside')
        fig_d.update_layout(height=max(280, len(df_proj_med)*44),
                            margin=dict(l=0, r=40, t=10, b=10),
                            coloraxis_showscale=False,
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_d, use_container_width=True)

# ══════════════════════════════════════════════
# ABA 2 — EQUIPE & PROJETOS  (hierarquia clara)
# ══════════════════════════════════════════════
with aba_equipe:

    # ─── NÍVEL 1: totais por projeto ───────────────────────────────
    st.markdown('<div class="sec-header">📂 Total de técnicos por projeto</div>', unsafe_allow_html=True)

    df_por_proj = (
        df_f.groupby('projeto')
        .agg(
            Técnicos   = ('tecnico',   'nunique'),
            Atividades = ('atividade', 'nunique'),
            Municípios = ('nome',      'nunique'),
            Gap_Médio  = ('gap_dias',  'mean'),
            Críticos   = ('gap_dias',  lambda x: (x > 30).sum()),
        )
        .reset_index()
        .rename(columns={'projeto': 'Projeto'})
        .sort_values('Técnicos', ascending=False)
    )
    df_por_proj['Gap_Médio'] = df_por_proj['Gap_Médio'].round(1)

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        fig_p = px.bar(
            df_por_proj.sort_values('Técnicos'),
            x='Técnicos', y='Projeto', orientation='h',
            color='Técnicos', color_continuous_scale='Greens', text='Técnicos'
        )
        fig_p.update_traces(textposition='outside')
        fig_p.update_layout(
            height=max(280, len(df_por_proj)*50),
            margin=dict(l=0, r=40, t=10, b=10), coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_p, use_container_width=True)

    with col_p2:
        st.dataframe(
            df_por_proj.style
                .format({'Gap_Médio': '{:.1f} dias'})
                .background_gradient(subset=['Gap_Médio'], cmap='RdYlGn_r', vmin=0, vmax=40)
                .background_gradient(subset=['Críticos'],  cmap='Reds',     vmin=0),
            use_container_width=True, hide_index=True,
            height=max(280, len(df_por_proj)*40)
        )

    st.divider()

    # ─── NÍVEL 2: atividades dentro do projeto ─────────────────────
    st.markdown('<div class="sec-header">🌿 Técnicos por atividade — detalhamento</div>', unsafe_allow_html=True)

    projetos_disp = sorted(df_f['projeto'].dropna().unique())
    proj_detalhe  = st.selectbox("Selecione o projeto:", projetos_disp)
    df_det = df_f[df_f['projeto'] == proj_detalhe]

    df_atv_det = (
        df_det.groupby('atividade')
        .agg(
            Técnicos  = ('tecnico',  'nunique'),
            Gap_Médio = ('gap_dias', 'mean'),
            Críticos  = ('gap_dias', lambda x: (x > 30).sum()),
        )
        .reset_index()
        .rename(columns={'atividade': 'Atividade'})
        .sort_values('Técnicos', ascending=False)
    )
    df_atv_det['Gap_Médio'] = df_atv_det['Gap_Médio'].round(1)

    col_a1, col_a2 = st.columns([1, 1])
    with col_a1:
        fig_a2 = px.bar(
            df_atv_det.sort_values('Técnicos'),
            x='Técnicos', y='Atividade', orientation='h',
            color='Técnicos', color_continuous_scale='Greens', text='Técnicos'
        )
        fig_a2.update_traces(textposition='outside')
        fig_a2.update_layout(
            height=max(260, len(df_atv_det)*46),
            margin=dict(l=0, r=40, t=10, b=10), coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_a2, use_container_width=True)

    with col_a2:
        st.dataframe(
            df_atv_det.style
                .format({'Gap_Médio': '{:.1f} dias'})
                .background_gradient(subset=['Gap_Médio'], cmap='RdYlGn_r', vmin=0, vmax=40)
                .background_gradient(subset=['Críticos'],  cmap='Reds',     vmin=0),
            use_container_width=True, hide_index=True,
            height=max(260, len(df_atv_det)*44)
        )

    st.divider()

    # ─── NÍVEL 3: lista de técnicos ────────────────────────────────
    st.markdown('<div class="sec-header">👤 Técnicos por atividade</div>', unsafe_allow_html=True)

    atividades_disp = sorted(df_det['atividade'].dropna().unique())
    atv_detalhe     = st.selectbox("Selecione a atividade:", atividades_disp, key='atv_equipe')

    df_tec = (
        df_det[df_det['atividade'] == atv_detalhe]
        [['tecnico', 'supervisor_atual', 'nome', 'gap_dias', 'status_gap', 'tempo_projeto_meses']]
        .drop_duplicates('tecnico')
        .rename(columns={
            'tecnico':            'Técnico',
            'supervisor_atual':   'Supervisor',
            'nome':               'Município',
            'gap_dias':           'Gap (dias)',
            'status_gap':         'Status',
            'tempo_projeto_meses':'Meses'
        })
        .sort_values('Gap (dias)', ascending=False)
    )
    st.dataframe(
        df_tec.style.background_gradient(subset=['Gap (dias)'], cmap='RdYlGn_r', vmin=0, vmax=40),
        use_container_width=True, hide_index=True
    )

    st.divider()

    # ─── Resumo por supervisor ──────────────────────────────────────
    st.markdown('<div class="sec-header">👤 Resumo por supervisor</div>', unsafe_allow_html=True)

    df_sup = (
        df_f.groupby('supervisor_atual')
        .agg(
            Técnicos   = ('tecnico',  'nunique'),
            Municípios = ('nome',     'nunique'),
            Projetos   = ('projeto',  'nunique'),
            Gap_Médio  = ('gap_dias', 'mean'),
            Críticos   = ('gap_dias', lambda x: (x > 30).sum()),
        )
        .reset_index()
        .rename(columns={'supervisor_atual': 'Supervisor'})
        .sort_values('Técnicos', ascending=False)
    )
    df_sup['Gap_Médio'] = df_sup['Gap_Médio'].round(1)

    st.dataframe(
        df_sup.style
            .format({'Gap_Médio': '{:.1f} dias'})
            .background_gradient(subset=['Gap_Médio'], cmap='RdYlGn_r', vmin=0, vmax=40)
            .background_gradient(subset=['Críticos'],  cmap='Reds',     vmin=0),
        use_container_width=True, hide_index=True
    )

# ══════════════════════════════════════════════
# ABA 3 — MAPA OPERACIONAL
# ══════════════════════════════════════════════
with aba_mapa_tab:
    CORES = ["#1D9E75","#E63946","#1D3557","#FFB703","#7B2D8B",
             "#FB8500","#F4A261","#606C38","#023047","#8ECAE6",
             "#E9C46A","#264653","#A8DADC","#457B9D","#F4A261"]
    cor_atv_map = {
        atv: CORES[i % len(CORES)]
        for i, atv in enumerate(sorted(df_f['atividade'].dropna().unique()))
    }

    col_map, col_leg = st.columns([4, 1])
    with col_leg:
        st.markdown("**Legenda**")
        for atv in sorted(df_f['atividade'].dropna().unique()):
            cor = cor_atv_map.get(atv, "#CCC")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
                f'<div style="width:12px;height:12px;background:{cor};border-radius:50%;flex-shrink:0;"></div>'
                f'<span style="font-size:11px;">{atv}</span></div>',
                unsafe_allow_html=True
            )
        st.caption(f"{df_f.shape[0]} pontos")

    with col_map:
        m = folium.Map(location=[-5.2, -39.5], zoom_start=7, tiles='cartodbpositron')
        if geo_ceara:
            folium.GeoJson(
                geo_ceara,
                style_function=lambda x: {'fillColor': 'transparent', 'color': '#bdc3c7', 'weight': 0.8}
            ).add_to(m)

        for _, row in df_f.iterrows():
            cor_hex   = cor_atv_map.get(row['atividade'], '#1B4332')
            inicial   = str(row['tecnico']).strip()[0].upper()
            gap_color = "#E24B4A" if row['gap_dias'] > 30 else ("#BA7517" if row['gap_dias'] > 15 else "#1D9E75")
            gap_label = "🚨 Crítico" if row['gap_dias'] > 30 else ("⚠️ Atenção" if row['gap_dias'] > 15 else "✅ OK")

            html_icone = (
                f'<div style="width:30px;height:30px;border-radius:50%;background:{cor_hex};'
                f'border:2px solid white;display:flex;align-items:center;justify-content:center;'
                f'color:white;font-weight:bold;font-size:13px;box-shadow:0 2px 5px rgba(0,0,0,0.3);">{inicial}</div>'
            )
            html_popup = f"""
            <div style="font-family:sans-serif;background:white;border-radius:10px;width:230px;
                        overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,0.12);border:1px solid #eee;">
                <div style="background:{cor_hex};color:white;padding:9px 13px;">
                    <div style="font-size:13px;font-weight:700;">{row['tecnico']}</div>
                    <div style="font-size:11px;opacity:.85;">{row['atividade']}</div>
                </div>
                <div style="padding:9px 13px;font-size:12px;color:#333;line-height:1.7;">
                    <div><b>Supervisor:</b> {row['supervisor_atual']}</div>
                    <div><b>Município:</b> {row['nome']}</div>
                    <div><b>Projeto:</b> {row['projeto']}</div>
                    <div><b>Tempo:</b> {int(row['tempo_projeto_meses'])} meses</div>
                    <div style="color:{gap_color};font-weight:700;">
                        <b>GAP:</b> {int(row['gap_dias'])} dias — {gap_label}
                    </div>
                </div>
            </div>"""

            folium.Marker(
                [row['latitude'], row['longitude']],
                icon=DivIcon(html=html_icone, icon_size=(30, 30), icon_anchor=(15, 15)),
                popup=folium.Popup(html_popup, max_width=260)
            ).add_to(m)

        st_folium(m, width='100%', height=620)

# ══════════════════════════════════════════════
# ABA 4 — ALERTAS
# ══════════════════════════════════════════════
with aba_alertas:
    df_critico = df_f[df_f['gap_dias'] > 30].sort_values('gap_dias', ascending=False)
    df_atencao = df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)].sort_values('gap_dias', ascending=False)

    col_al1, col_al2 = st.columns(2)
    with col_al1:
        st.markdown(
            f'<div class="sec-header">🚨 Crítico — gap > 30 dias &nbsp;<span class="badge-critico">{len(df_critico)}</span></div>',
            unsafe_allow_html=True
        )
        if df_critico.empty:
            st.success("Nenhum técnico em situação crítica!")
        else:
            for _, r in df_critico.iterrows():
                st.markdown(
                    f'<div class="alert-card-critico">'
                    f'<b>{r["tecnico"]}</b> &nbsp;<span class="badge-critico">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:11px;color:#666;">{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with col_al2:
        st.markdown(
            f'<div class="sec-header">⚠️ Atenção — gap 16–30 dias &nbsp;<span class="badge-atencao">{len(df_atencao)}</span></div>',
            unsafe_allow_html=True
        )
        if df_atencao.empty:
            st.success("Nenhum técnico em atenção!")
        else:
            for _, r in df_atencao.iterrows():
                st.markdown(
                    f'<div class="alert-card-atencao">'
                    f'<b>{r["tecnico"]}</b> &nbsp;<span class="badge-atencao">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:11px;color:#666;">{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.divider()

    st.markdown('<div class="sec-header">📊 Ranking de gap — top 20 técnicos</div>', unsafe_allow_html=True)
    df_rank = (
        df_f[df_f['gap_dias'] > 0][['tecnico', 'gap_dias', 'atividade']]
        .drop_duplicates('tecnico')
        .sort_values('gap_dias', ascending=False)
        .head(20)
    )
    df_rank['cor'] = df_rank['gap_dias'].apply(
        lambda x: "#E24B4A" if x > 30 else ("#BA7517" if x > 15 else "#1D9E75")
    )
    fig_rank = go.Figure(go.Bar(
        x=df_rank['tecnico'], y=df_rank['gap_dias'],
        marker_color=df_rank['cor'],
        text=df_rank['gap_dias'], textposition='outside'
    ))
    fig_rank.add_hline(y=30, line_dash='dash', line_color='#E24B4A',
                       annotation_text='Crítico (30d)', annotation_position='top right')
    fig_rank.add_hline(y=15, line_dash='dot', line_color='#BA7517',
                       annotation_text='Atenção (15d)', annotation_position='top right')
    fig_rank.update_layout(
        height=380, margin=dict(l=0, r=0, t=30, b=100),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickangle=-40, showgrid=False),
        yaxis=dict(title='Gap (dias)', showgrid=True, gridcolor='#f0f0f0')
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.divider()

    st.markdown('<div class="sec-header">📈 Tendência de gap médio — últimas 8 semanas</div>', unsafe_allow_html=True)
    hoje = pd.Timestamp('today').normalize()
    semanas, gaps_med = [], []
    for i in range(7, -1, -1):
        ref = hoje - timedelta(weeks=i)
        tmp = df_f[df_f['data_ultima_visita'] <= ref].copy()
        gap = round((ref - tmp['data_ultima_visita']).dt.days.clip(lower=0).mean(), 1) if not tmp.empty else 0
        semanas.append(f"S{8-i}")
        gaps_med.append(gap)
    df_trend = pd.DataFrame({'Semana': semanas, 'Gap médio (dias)': gaps_med})
    fig_trend = px.line(df_trend, x='Semana', y='Gap médio (dias)',
                        markers=True, line_shape='spline',
                        color_discrete_sequence=['#1D9E75'])
    fig_trend.add_hline(y=30, line_dash='dash', line_color='#E24B4A', annotation_text='Crítico')
    fig_trend.add_hline(y=15, line_dash='dot',  line_color='#BA7517', annotation_text='Atenção')
    fig_trend.update_layout(
        height=280, margin=dict(l=0, r=0, t=20, b=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ══════════════════════════════════════════════
# ABA 5 — EXPORTAR
# ══════════════════════════════════════════════
with aba_download:
    st.subheader("📥 Exportação de Dados")
    st.info(f"Exportando **{len(df_f)}** registros conforme os filtros aplicados.")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_f.to_excel(writer, sheet_name='Base Completa', index=False)
            df_f[df_f['gap_dias'] > 30].to_excel(writer, sheet_name='Críticos', index=False)
            df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)].to_excel(writer, sheet_name='Atenção', index=False)
            df_por_proj.to_excel(writer, sheet_name='Por Projeto', index=False)
            df_sup.to_excel(writer, sheet_name='Por Supervisor', index=False)
        st.download_button(
            "📊 Base Completa (Excel)",
            data=buf.getvalue(),
            file_name=f"ateg_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col_d2:
        csv_crit = df_f[df_f['gap_dias'] > 30][['tecnico', 'atividade', 'supervisor_atual', 'nome', 'gap_dias']]
        st.download_button(
            "🚨 Alertas Críticos (CSV)",
            data=csv_crit.to_csv(index=False, sep=';').encode('utf-8'),
            file_name=f"ateg_criticos_{datetime.now().strftime('%Y%m%d')}.csv"
        )

    with col_d3:
        st.download_button(
            "👤 Por Supervisor (CSV)",
            data=df_sup.to_csv(index=False, sep=';').encode('utf-8'),
            file_name=f"ateg_supervisores_{datetime.now().strftime('%Y%m%d')}.csv"
        )

    st.divider()
    st.markdown('<div class="sec-header">Prévia dos dados</div>', unsafe_allow_html=True)
    st.dataframe(
        df_f[['tecnico', 'atividade', 'supervisor_atual', 'projeto', 'nome',
              'tempo_projeto_meses', 'gap_dias', 'status_gap', 'data_ultima_visita']]
        .sort_values('gap_dias', ascending=False),
        use_container_width=True, hide_index=True
    )