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
/* ── Reset e base ── */
[data-testid="stAppViewContainer"] { background-color: #f8faf9; }
[data-testid="stSidebar"] { background-color: #f0f7f4; }
[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #0F6E56 !important; }
[data-testid="stMetricLabel"] { font-size: 13px !important; color: #2D6A4F !important; font-weight: 500 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ── Títulos ── */
h1 { color: #1B4332 !important; font-size: 24px !important; font-weight: 700 !important; }
h2 { color: #2D6A4F !important; font-size: 18px !important; font-weight: 600 !important; }
h3 { color: #2D6A4F !important; font-size: 15px !important; font-weight: 600 !important; }

/* ── Cards ── */
.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 16px 20px;
    border: 1px solid #e8f4ee;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.alert-card-critico {
    background: #fff5f5;
    border-left: 4px solid #E24B4A;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.alert-card-atencao {
    background: #fffbf0;
    border-left: 4px solid #BA7517;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.alert-card-ok {
    background: #f0faf5;
    border-left: 4px solid #1D9E75;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}

/* ── Badge de status ── */
.badge-critico { background:#fde8e8; color:#A32D2D; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-atencao { background:#fef3d8; color:#854F0B; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-ok      { background:#e0f5ec; color:#0F6E56; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }

/* ── Assinatura ── */
.equipe-assinatura { font-size: 11px; color: #52796f; margin-top: -12px; font-weight: 400; margin-bottom: 18px; }

/* ── Tabelas ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── Popups folium ── */
.leaflet-popup-content-wrapper { background: transparent !important; box-shadow: none !important; padding: 0 !important; }
.leaflet-popup-tip-container { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CABEÇALHO
# ─────────────────────────────────────────────
col_title, col_logo = st.columns([5, 1])
with col_title:
    st.title("🌱 Assistência Técnica e Gerencial — ATeG")
    st.markdown('<p class="equipe-assinatura">Equipe CIIAGRO · Atualizado automaticamente a cada 5 minutos</p>', unsafe_allow_html=True)
with col_logo:
    st.markdown(f"<p style='text-align:right; font-size:12px; color:#52796f; padding-top:16px;'>📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3. CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_dados():
    engine_pg = get_engine()
    query = "SELECT * FROM public.mapa_consolidado_ateg"
    with engine_pg.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df['data_ultima_visita'] = pd.to_datetime(df['data_ultima_visita'], errors='coerce')
        df['data_atualizacao']   = pd.to_datetime(df['data_atualizacao'],   errors='coerce')
        df['gap_dias']           = (df['data_atualizacao'] - df['data_ultima_visita']).dt.days.fillna(0).astype(int)
        return df

@st.cache_data(ttl=3600)
def carregar_geojson():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return None

@st.cache_data(ttl=3600)
def carregar_coordenadas():
    url = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    df = pd.read_csv(url)
    df['codigo_ibge'] = df['codigo_ibge'].astype(str)
    return df

df_raw      = carregar_dados()
geo_ceara   = carregar_geojson()
df_coords   = carregar_coordenadas()

# ─────────────────────────────────────────────
# 4. PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────
df_proc = df_raw.assign(
    cod_ibge=df_raw['codigos_ibge'].astype(str).str.split(', ')
).explode('cod_ibge')
df_proc['cod_ibge'] = df_proc['cod_ibge'].astype(str).str.strip()

df_mapa = df_proc.merge(
    df_coords, left_on='cod_ibge', right_on='codigo_ibge', how='inner'
)

# Classificação de status do gap
def classificar_gap(gap):
    if gap > 30:   return "🔴 Crítico"
    if gap > 15:   return "🟡 Atenção"
    return              "🟢 OK"

df_mapa['status_gap'] = df_mapa['gap_dias'].apply(classificar_gap)

# ─────────────────────────────────────────────
# 5. SIDEBAR — FILTROS
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filtros")
st.sidebar.markdown("---")

# Filtro de meses
min_m = int(df_mapa['tempo_projeto_meses'].min())
max_m = int(df_mapa['tempo_projeto_meses'].max())
meses_sel = st.sidebar.slider("⏱️ Tempo de Projeto (Meses)", min_m, max_m, (min_m, max_m))

# Filtro supervisor
opcoes_sup = sorted(df_mapa['supervisor_atual'].dropna().unique())
sup_sel = st.sidebar.multiselect("👤 Supervisores", opcoes_sup)

# Filtro projeto
opcoes_projeto = sorted(df_mapa['projeto'].dropna().unique())
projetos_sel = st.sidebar.multiselect("📂 Projetos", opcoes_projeto)

# Filtro atividade
opcoes_atividade = sorted(df_mapa['atividade'].dropna().unique())
atividades_sel = st.sidebar.multiselect("🌿 Atividades", opcoes_atividade)

# Filtro status gap
status_opcoes = ["Todos", "🔴 Crítico (>30 dias)", "🟡 Atenção (16–30 dias)", "🟢 OK (≤15 dias)"]
status_sel = st.sidebar.selectbox("⚠️ Status do Gap", status_opcoes)

# Aplicar filtros
df_f = df_mapa.copy()
if sup_sel:        df_f = df_f[df_f['supervisor_atual'].isin(sup_sel)]
if projetos_sel:   df_f = df_f[df_f['projeto'].isin(projetos_sel)]
if atividades_sel: df_f = df_f[df_f['atividade'].isin(atividades_sel)]
df_f = df_f[(df_f['tempo_projeto_meses'] >= meses_sel[0]) & (df_f['tempo_projeto_meses'] <= meses_sel[1])]
if status_sel == "🔴 Crítico (>30 dias)":       df_f = df_f[df_f['gap_dias'] > 30]
elif status_sel == "🟡 Atenção (16–30 dias)":   df_f = df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)]
elif status_sel == "🟢 OK (≤15 dias)":          df_f = df_f[df_f['gap_dias'] <= 15]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(df_f)}** registros no filtro")

# ─────────────────────────────────────────────
# 6. KPIs
# ─────────────────────────────────────────────
n_tec      = df_f['tecnico'].nunique()
n_atv      = df_f['atividade'].nunique()
n_proj     = df_f['projeto'].nunique()
n_mun      = df_f['nome'].nunique()
media_mes  = round(df_f['tempo_projeto_meses'].mean(), 1) if not df_f.empty else 0
n_critico  = (df_f['gap_dias'] > 30).sum()
pct_critico = round((n_critico / len(df_f) * 100), 1) if len(df_f) > 0 else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("👤 Técnicos",    n_tec)
k2.metric("🌱 Atividades",  n_atv)
k3.metric("📂 Projetos",    n_proj)
k4.metric("🏙️ Municípios",  n_mun)
k5.metric("📈 Média Meses", media_mes)
k6.metric("🚨 Gap Crítico", n_critico, delta=f"{pct_critico}% do total", delta_color="inverse")

st.divider()

# ─────────────────────────────────────────────
# 7. ABAS PRINCIPAIS
# ─────────────────────────────────────────────
aba_visao, aba_mapa, aba_equipe, aba_alertas, aba_download = st.tabs([
    "📊 Visão Geral",
    "🗺️ Mapa Operacional",
    "👥 Equipe & Supervisores",
    "🚨 Alertas & Acompanhamento",
    "📥 Exportar Dados"
])

# ════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ════════════════════════════════════════════
with aba_visao:

    col_a, col_b = st.columns(2)

    # Gráfico 1: Técnicos por atividade
    with col_a:
        st.subheader("Técnicos por atividade")
        df_atv = df_f.groupby('atividade')['tecnico'].nunique().reset_index()
        df_atv.columns = ['Atividade', 'Técnicos']
        df_atv = df_atv.sort_values('Técnicos', ascending=True)
        fig_atv = px.bar(
            df_atv, x='Técnicos', y='Atividade', orientation='h',
            color='Técnicos', color_continuous_scale='Greens',
            text='Técnicos'
        )
        fig_atv.update_traces(textposition='outside')
        fig_atv.update_layout(
            height=350, margin=dict(l=0, r=20, t=10, b=10),
            coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_atv, use_container_width=True)

    # Gráfico 2: Distribuição do Gap
    with col_b:
        st.subheader("Distribuição do gap (dias)")
        bins   = [0, 15, 30, 9999]
        labels = ["✅ OK (0–15)", "⚠️ Atenção (16–30)", "🚨 Crítico (>30)"]
        df_gap_cat = df_f.copy()
        df_gap_cat['faixa'] = pd.cut(df_gap_cat['gap_dias'], bins=bins, labels=labels)
        df_gap_pie = df_gap_cat['faixa'].value_counts().reset_index()
        df_gap_pie.columns = ['Faixa', 'Qtd']
        fig_pie = px.pie(
            df_gap_pie, names='Faixa', values='Qtd',
            color='Faixa',
            color_discrete_map={
                "✅ OK (0–15)":       "#1D9E75",
                "⚠️ Atenção (16–30)": "#BA7517",
                "🚨 Crítico (>30)":  "#E24B4A"
            },
            hole=0.5
        )
        fig_pie.update_layout(
            height=350, margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(orientation='h', yanchor='bottom', y=-0.2),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    col_c, col_d = st.columns(2)

    # Gráfico 3: Municípios com mais atendimentos
    with col_c:
        st.subheader("Top 10 municípios atendidos")
        df_mun_top = df_f.groupby('nome')['tecnico'].nunique().reset_index()
        df_mun_top.columns = ['Município', 'Técnicos']
        df_mun_top = df_mun_top.sort_values('Técnicos', ascending=False).head(10)
        fig_mun = px.bar(
            df_mun_top, x='Município', y='Técnicos',
            color='Técnicos', color_continuous_scale='teal',
            text='Técnicos'
        )
        fig_mun.update_traces(textposition='outside')
        fig_mun.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=80),
            coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickangle=-35, showgrid=False),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_mun, use_container_width=True)

    # Gráfico 4: Tempo médio por projeto
    with col_d:
        st.subheader("Tempo médio por projeto (meses)")
        df_proj = df_f.groupby('projeto')['tempo_projeto_meses'].mean().reset_index()
        df_proj.columns = ['Projeto', 'Média (meses)']
        df_proj['Média (meses)'] = df_proj['Média (meses)'].round(1)
        df_proj = df_proj.sort_values('Média (meses)', ascending=True)
        fig_proj = px.bar(
            df_proj, x='Média (meses)', y='Projeto', orientation='h',
            color='Média (meses)', color_continuous_scale='Blues',
            text='Média (meses)'
        )
        fig_proj.update_traces(textposition='outside')
        fig_proj.update_layout(
            height=320, margin=dict(l=0, r=30, t=10, b=10),
            coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_proj, use_container_width=True)

# ════════════════════════════════════════════
# ABA 2 — MAPA OPERACIONAL
# ════════════════════════════════════════════
with aba_mapa:
    CORES = [
        "#1D9E75","#E63946","#1D3557","#FFB703","#7B2D8B",
        "#FB8500","#F4A261","#606C38","#023047","#8ECAE6"
    ]
    cor_atv_map = {
        atv: CORES[i % len(CORES)]
        for i, atv in enumerate(sorted(df_f['atividade'].dropna().unique()))
    }

    col_map, col_leg = st.columns([4, 1])

    with col_leg:
        st.markdown("### Legenda")
        for atv in sorted(df_f['atividade'].dropna().unique()):
            cor = cor_atv_map.get(atv, "#CCC")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
                f'<div style="width:14px;height:14px;background:{cor};border-radius:50%;flex-shrink:0;"></div>'
                f'<span style="font-size:12px;">{atv}</span></div>',
                unsafe_allow_html=True
            )
        st.markdown(f"**{df_f.shape[0]}** pontos no mapa")

    with col_map:
        m = folium.Map(location=[-5.2, -39.5], zoom_start=7, tiles='cartodbpositron')
        if geo_ceara:
            folium.GeoJson(
                geo_ceara,
                style_function=lambda x: {'fillColor': 'transparent', 'color': '#bdc3c7', 'weight': 0.8}
            ).add_to(m)

        for _, row in df_f.iterrows():
            cor_hex = cor_atv_map.get(row['atividade'], '#1B4332')
            inicial = str(row['tecnico']).strip()[0].upper()

            gap_color = "#E24B4A" if row['gap_dias'] > 30 else ("#BA7517" if row['gap_dias'] > 15 else "#1D9E75")
            gap_label = "🚨 Crítico" if row['gap_dias'] > 30 else ("⚠️ Atenção" if row['gap_dias'] > 15 else "✅ OK")

            html_icone = (
                f'<div style="width:30px;height:30px;border-radius:50%;background:{cor_hex};'
                f'border:2px solid white;display:flex;align-items:center;justify-content:center;'
                f'color:white;font-weight:bold;font-size:13px;'
                f'box-shadow:0px 2px 5px rgba(0,0,0,0.35);">{inicial}</div>'
            )

            html_tooltip = f"""
            <div style="font-family:sans-serif;background:white;border-radius:10px;
                        width:240px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,0.12);border:1px solid #eee;">
                <div style="background:{cor_hex};color:white;padding:10px 14px;">
                    <div style="font-size:13px;font-weight:700;text-transform:uppercase;">{row['tecnico']}</div>
                    <div style="font-size:11px;opacity:0.85;">{row['atividade']}</div>
                </div>
                <div style="padding:10px 14px;font-size:12px;color:#333;line-height:1.6;">
                    <div><b>Supervisor:</b> {row['supervisor_atual']}</div>
                    <div><b>Município:</b> {row['nome']}</div>
                    <div><b>Projeto:</b> {row['projeto']}</div>
                    <div><b>Tempo:</b> {int(row['tempo_projeto_meses'])} meses</div>
                    <div style="color:{gap_color};font-weight:700;margin-top:4px;">
                        <b>GAP:</b> {int(row['gap_dias'])} dias — {gap_label}
                    </div>
                </div>
            </div>"""

            folium.Marker(
                [row['latitude'], row['longitude']],
                icon=DivIcon(html=html_icone, icon_size=(30, 30), icon_anchor=(15, 15)),
                popup=folium.Popup(html_tooltip, max_width=280)
            ).add_to(m)

        st_folium(m, width='100%', height=620)

# ════════════════════════════════════════════
# ABA 3 — EQUIPE & SUPERVISORES
# ════════════════════════════════════════════
with aba_equipe:

    col_e1, col_e2 = st.columns(2)

    # Gráfico: carga por supervisor
    with col_e1:
        st.subheader("Carga por supervisor")
        df_sup = df_f.groupby('supervisor_atual').agg(
            Técnicos=('tecnico', 'nunique'),
            Municípios=('nome', 'nunique'),
            Projetos=('projeto', 'nunique'),
            Gap_Médio=('gap_dias', 'mean')
        ).reset_index().rename(columns={'supervisor_atual': 'Supervisor'})
        df_sup['Gap_Médio'] = df_sup['Gap_Médio'].round(1)

        fig_sup = go.Figure()
        fig_sup.add_trace(go.Bar(
            name='Técnicos', x=df_sup['Supervisor'], y=df_sup['Técnicos'],
            marker_color='#1D9E75', text=df_sup['Técnicos'], textposition='outside'
        ))
        fig_sup.add_trace(go.Bar(
            name='Municípios', x=df_sup['Supervisor'], y=df_sup['Municípios'],
            marker_color='#378ADD', text=df_sup['Municípios'], textposition='outside'
        ))
        fig_sup.update_layout(
            barmode='group', height=320,
            margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(orientation='h', y=-0.2),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_sup, use_container_width=True)

    # Tabela: detalhes por supervisor
    with col_e2:
        st.subheader("Resumo por supervisor")
        st.dataframe(
            df_sup.style.format({'Gap_Médio': '{:.1f} dias'})
                        .background_gradient(subset=['Gap_Médio'], cmap='RdYlGn_r'),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # Scatter: tempo de projeto vs. gap por técnico
    st.subheader("Tempo de projeto × Gap — por técnico")
    df_scatter = df_f[['tecnico', 'tempo_projeto_meses', 'gap_dias', 'atividade', 'supervisor_atual']].drop_duplicates('tecnico')
    fig_scat = px.scatter(
        df_scatter,
        x='tempo_projeto_meses', y='gap_dias',
        color='atividade', hover_name='tecnico',
        hover_data={'supervisor_atual': True, 'atividade': True},
        labels={'tempo_projeto_meses': 'Tempo de projeto (meses)', 'gap_dias': 'Gap (dias)'},
        size_max=14,
        color_discrete_sequence=CORES
    )
    fig_scat.add_hline(y=30, line_dash='dash', line_color='#E24B4A',
                       annotation_text='Limite crítico (30 dias)', annotation_position='top right')
    fig_scat.add_hline(y=15, line_dash='dot', line_color='#BA7517',
                       annotation_text='Limite atenção (15 dias)', annotation_position='top right')
    fig_scat.update_layout(
        height=380, margin=dict(l=0, r=0, t=30, b=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=-0.25)
    )
    st.plotly_chart(fig_scat, use_container_width=True)

    st.divider()

    # Tabela detalhada
    st.subheader("Detalhamento por equipe")
    df_equipe_tab = df_f[['projeto', 'atividade', 'tecnico', 'supervisor_atual', 'gap_dias', 'status_gap', 'tempo_projeto_meses']].copy()
    df_equipe_tab.columns = ['Projeto', 'Atividade', 'Técnico', 'Supervisor', 'Gap (dias)', 'Status', 'Meses']
    df_equipe_tab = df_equipe_tab.sort_values(['Supervisor', 'Atividade', 'Técnico'])
    st.dataframe(df_equipe_tab, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════
# ABA 4 — ALERTAS & ACOMPANHAMENTO
# ════════════════════════════════════════════
with aba_alertas:

    col_al1, col_al2 = st.columns([1, 1])

    df_critico  = df_f[df_f['gap_dias'] > 30].sort_values('gap_dias', ascending=False)
    df_atencao  = df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)].sort_values('gap_dias', ascending=False)
    df_ok       = df_f[df_f['gap_dias'] <= 15]

    with col_al1:
        st.markdown(f"### 🚨 Crítico — Gap > 30 dias ({len(df_critico)} técnicos)")
        if df_critico.empty:
            st.success("Nenhum técnico em situação crítica!")
        else:
            for _, r in df_critico.iterrows():
                st.markdown(
                    f'<div class="alert-card-critico">'
                    f'<b>{r["tecnico"]}</b> &nbsp;<span class="badge-critico">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:12px;color:#666;">{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with col_al2:
        st.markdown(f"### ⚠️ Atenção — Gap 16–30 dias ({len(df_atencao)} técnicos)")
        if df_atencao.empty:
            st.success("Nenhum técnico em atenção!")
        else:
            for _, r in df_atencao.iterrows():
                st.markdown(
                    f'<div class="alert-card-atencao">'
                    f'<b>{r["tecnico"]}</b> &nbsp;<span class="badge-atencao">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:12px;color:#666;">{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.divider()

    # Gráfico de barras: gap por técnico (top 20)
    st.subheader("Ranking de gap — top 20 técnicos")
    df_gap_rank = (
        df_f[df_f['gap_dias'] > 0][['tecnico', 'gap_dias', 'atividade']]
        .drop_duplicates('tecnico')
        .sort_values('gap_dias', ascending=False)
        .head(20)
    )
    df_gap_rank['cor'] = df_gap_rank['gap_dias'].apply(
        lambda x: "#E24B4A" if x > 30 else ("#BA7517" if x > 15 else "#1D9E75")
    )
    fig_rank = go.Figure(go.Bar(
        x=df_gap_rank['tecnico'], y=df_gap_rank['gap_dias'],
        marker_color=df_gap_rank['cor'],
        text=df_gap_rank['gap_dias'], textposition='outside'
    ))
    fig_rank.add_hline(y=30, line_dash='dash', line_color='#E24B4A')
    fig_rank.add_hline(y=15, line_dash='dot',  line_color='#BA7517')
    fig_rank.update_layout(
        height=380, margin=dict(l=0, r=0, t=20, b=80),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickangle=-40, showgrid=False),
        yaxis=dict(title='Gap (dias)', showgrid=True, gridcolor='#f0f0f0')
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.divider()

    # Tendência simulada de gap médio por semana
    st.subheader("📈 Tendência de gap médio — últimas 8 semanas")
    st.caption("Cálculo baseado em data_ultima_visita vs. data_atualizacao por período.")

    # Cálculo real: gerar semanas retroativas e calcular gap por semana
    hoje = datetime.now()
    semanas, gaps_medios = [], []
    for i in range(7, -1, -1):
        data_ref = hoje - timedelta(weeks=i)
        df_temp  = df_f[df_f['data_ultima_visita'] <= data_ref].copy()
        if not df_temp.empty:
            df_temp['gap_sim'] = (data_ref - df_temp['data_ultima_visita']).dt.days
            gaps_medios.append(round(df_temp['gap_sim'].mean(), 1))
        else:
            gaps_medios.append(0)
        semanas.append(f"S{8-i}")

    df_trend = pd.DataFrame({'Semana': semanas, 'Gap médio (dias)': gaps_medios})
    fig_trend = px.line(
        df_trend, x='Semana', y='Gap médio (dias)',
        markers=True, line_shape='spline',
        color_discrete_sequence=['#1D9E75']
    )
    fig_trend.add_hline(y=30, line_dash='dash', line_color='#E24B4A', annotation_text='Crítico')
    fig_trend.add_hline(y=15, line_dash='dot',  line_color='#BA7517', annotation_text='Atenção')
    fig_trend.update_layout(
        height=300, margin=dict(l=0, r=0, t=20, b=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ════════════════════════════════════════════
# ABA 5 — EXPORTAR DADOS
# ════════════════════════════════════════════
with aba_download:
    st.subheader("📥 Exportação de Dados")
    st.info(f"Exportando **{len(df_f)}** registros conforme filtros aplicados.")

    col_d1, col_d2, col_d3 = st.columns(3)

    # Excel completo
    with col_d1:
        buffer_full = io.BytesIO()
        with pd.ExcelWriter(buffer_full, engine='xlsxwriter') as writer:
            df_f.to_excel(writer, sheet_name='Base Completa', index=False)
            # Alertas
            df_critico_exp = df_f[df_f['gap_dias'] > 30]
            df_atencao_exp = df_f[(df_f['gap_dias'] > 15) & (df_f['gap_dias'] <= 30)]
            if not df_critico_exp.empty:
                df_critico_exp.to_excel(writer, sheet_name='Críticos (>30d)', index=False)
            if not df_atencao_exp.empty:
                df_atencao_exp.to_excel(writer, sheet_name='Atenção (16-30d)', index=False)
            # Resumo supervisores
            df_sup_exp = df_f.groupby('supervisor_atual').agg(
                Técnicos=('tecnico', 'nunique'),
                Municípios=('nome', 'nunique'),
                Gap_Médio=('gap_dias', 'mean')
            ).reset_index()
            df_sup_exp.to_excel(writer, sheet_name='Resumo Supervisores', index=False)
        st.download_button(
            label="📊 Base Completa + Alertas (Excel)",
            data=buffer_full.getvalue(),
            file_name=f"ateg_completo_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # CSV alertas críticos
    with col_d2:
        df_crit_csv = df_f[df_f['gap_dias'] > 30][['tecnico', 'atividade', 'supervisor_atual', 'nome', 'gap_dias']]
        st.download_button(
            label="🚨 Alertas Críticos (CSV)",
            data=df_crit_csv.to_csv(index=False, sep=';').encode('utf-8'),
            file_name=f"ateg_criticos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # CSV resumo por supervisor
    with col_d3:
        df_sup_csv = df_f.groupby('supervisor_atual').agg(
            Técnicos=('tecnico', 'nunique'),
            Municípios=('nome', 'nunique'),
            Projetos=('projeto', 'nunique'),
            Gap_Médio=('gap_dias', 'mean')
        ).reset_index()
        df_sup_csv['Gap_Médio'] = df_sup_csv['Gap_Médio'].round(1)
        st.download_button(
            label="👤 Resumo Supervisores (CSV)",
            data=df_sup_csv.to_csv(index=False, sep=';').encode('utf-8'),
            file_name=f"ateg_supervisores_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="text/csv"
        )

    st.divider()
    st.subheader("Prévia dos dados exportados")
    st.dataframe(
        df_f[['tecnico', 'atividade', 'supervisor_atual', 'nome', 'projeto',
              'tempo_projeto_meses', 'gap_dias', 'status_gap', 'data_ultima_visita']]
        .sort_values('gap_dias', ascending=False),
        use_container_width=True, hide_index=True
    )