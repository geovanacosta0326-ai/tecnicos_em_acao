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
[data-testid="stSidebar"] { background-color: #f0f7f4; }
[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #0F6E56 !important; }
[data-testid="stMetricLabel"] { font-size: 13px !important; color: #2D6A4F !important; font-weight: 500 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
h1 { color: #1B4332 !important; font-size: 24px !important; font-weight: 700 !important; }
h2 { color: #2D6A4F !important; font-size: 18px !important; font-weight: 600 !important; }
h3 { color: #2D6A4F !important; font-size: 15px !important; font-weight: 600 !important; }

/* Esconder header e footer padrão do Streamlit 1.57 */
header { visibility: hidden !important; height: 0 !important; }
footer { visibility: hidden !important; height: 0 !important; }
#MainMenu { visibility: hidden !important; }

/* Remover padding do topo */
.block-container { padding-top: 0.5rem !important; }
.stApp > header { display: none !important; }
.kpi-card {
    background: white; border-radius: 10px; padding: 16px 20px;
    border: 1px solid #e8f4ee; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.alert-card-critico {
    background: #fff5f5; border-left: 4px solid #E24B4A;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
}
.alert-card-atencao {
    background: #fffbf0; border-left: 4px solid #BA7517;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
}
.alert-card-ok {
    background: #f0faf5; border-left: 4px solid #1D9E75;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
}
.badge-critico { background:#fde8e8; color:#A32D2D; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-atencao { background:#fef3d8; color:#854F0B; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-ok      { background:#e0f5ec; color:#0F6E56; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.equipe-assinatura { font-size: 11px; color: #52796f; margin-top: -12px; font-weight: 400; margin-bottom: 18px; }
.stDataFrame { border-radius: 8px; overflow: hidden; }
.leaflet-popup-content-wrapper { background: transparent !important; box-shadow: none !important; padding: 0 !important; }
.leaflet-popup-tip-container { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CABEÇALHO
# ─────────────────────────────────────────────
_data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(
    f'<div style="background:linear-gradient(120deg,#1B4332 0%,#2D6A4F 40%,#40916C 70%,#52B788 100%);border-radius:16px;padding:36px 44px;margin-bottom:24px;box-shadow:0 6px 24px rgba(27,67,50,0.35);overflow:hidden;">'
    f'<div style="font-size:11px;color:#95d5b2;font-weight:700;letter-spacing:4px;text-transform:uppercase;margin-bottom:10px;">🌿 Serviço Nacional de Aprendizagem Rural</div>'
    f'<div style="font-size:34px;font-weight:900;color:white;line-height:1.15;margin-bottom:6px;">Ações da Assistência Técnica</div>'
    f'<div style="font-size:34px;font-weight:900;color:#95d5b2;line-height:1.15;margin-bottom:14px;">e Gerencial — ATeG</div>'
    f'<div style="display:inline-block;background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 16px;font-size:12px;color:#d8f3dc;font-weight:500;">📅 {_data_hora} &nbsp;·&nbsp; Atualizado a cada 5 minutos</div>'
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
        df["data_ultima_visita"] = pd.to_datetime(df["data_ultima_visita"], errors="coerce")
        df["data_atualizacao"]   = pd.to_datetime(df["data_atualizacao"],   errors="coerce")
        df["gap_dias"]           = (
            (df["data_atualizacao"] - df["data_ultima_visita"]).dt.days.fillna(0).astype(int)
        )
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
    cod_ibge=df_raw["codigos_ibge"].astype(str).str.split(", ")
).explode("cod_ibge")
df_proc["cod_ibge"] = df_proc["cod_ibge"].astype(str).str.strip()

df_mapa = df_proc.merge(
    df_coords, left_on="cod_ibge", right_on="codigo_ibge", how="inner"
)


def classificar_gap(gap):
    if gap > 30:
        return "🔴 Crítico"
    if gap > 15:
        return "🟡 Atenção"
    return "🟢 OK"


df_mapa["status_gap"] = df_mapa["gap_dias"].apply(classificar_gap)

# ─────────────────────────────────────────────
# 5. SIDEBAR — FILTROS
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filtros")
st.sidebar.markdown("---")

min_m = int(df_mapa["tempo_projeto_meses"].min())
max_m = int(df_mapa["tempo_projeto_meses"].max())
meses_sel = st.sidebar.slider("⏱️ Tempo de Projeto (Meses)", min_m, max_m, (min_m, max_m))

opcoes_regiao = sorted(df_mapa["regiao_faec"].dropna().unique())
regiao_sel = st.sidebar.multiselect("🗺️ Região FAEC", opcoes_regiao)

opcoes_sup = sorted(df_mapa["supervisor_atual"].dropna().unique())
sup_sel = st.sidebar.multiselect("👤 Supervisores", opcoes_sup)

opcoes_projeto = sorted(df_mapa["projeto"].dropna().unique())
projetos_sel = st.sidebar.multiselect("📂 Projetos", opcoes_projeto)

options_atividade = sorted(df_mapa["atividade"].dropna().unique())
atividades_sel = st.sidebar.multiselect("🌿 Atividades", options_atividade)

status_opcoes = ["Todos", "🔴 Crítico (>30 dias)", "🟡 Atenção (16–30 dias)", "🟢 OK (≤15 dias)"]
status_sel = st.sidebar.selectbox("⚠️ Status do Gap", status_opcoes)

# Aplicar filtros
df_f = df_mapa.copy()
if regiao_sel:
    df_f = df_f[df_f["regiao_faec"].isin(regiao_sel)]
if sup_sel:
    df_f = df_f[df_f["supervisor_atual"].isin(sup_sel)]
if projetos_sel:
    df_f = df_f[df_f["projeto"].isin(projetos_sel)]
if atividades_sel:
    df_f = df_f[df_f["atividade"].isin(atividades_sel)]

df_f = df_f[
    (df_f["tempo_projeto_meses"] >= meses_sel[0])
    & (df_f["tempo_projeto_meses"] <= meses_sel[1])
]

if status_sel == "🔴 Crítico (>30 dias)":
    df_f = df_f[df_f["gap_dias"] > 30]
elif status_sel == "🟡 Atenção (16–30 dias)":
    df_f = df_f[(df_f["gap_dias"] > 15) & (df_f["gap_dias"] <= 30)]
elif status_sel == "🟢 OK (≤15 dias)":
    df_f = df_f[df_f["gap_dias"] <= 15]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(df_f)}** registros no filtro")

# ─────────────────────────────────────────────
# 6. KPIs
# ─────────────────────────────────────────────
n_tec       = df_f["tecnico"].nunique()
n_atv       = df_f["atividade"].nunique()
n_proj      = df_f["projeto"].nunique()
n_mun       = df_f["nome"].nunique()
media_mes   = round(df_f["tempo_projeto_meses"].mean(), 1) if not df_f.empty else 0
n_critico   = (df_f["gap_dias"] > 30).sum()
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
aba_visao, aba_mapa, aba_equipe, aba_alertas, aba_download, aba_consolidado = st.tabs([
    "📊 Visão Geral",
    "🗺️ Mapa Operacional",
    "👥 Equipe & Supervisores",
    "🚨 Alertas & Acompanhamento",
    "📥 Exportar Dados",
    "📋 Consolidado",
])

CORES = [
    "#1D9E75", "#E63946", "#1D3557", "#FFB703", "#7B2D8B",
    "#FB8500", "#F4A261", "#606C38", "#023047", "#8ECAE6",
]

# ════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ════════════════════════════════════════════
with aba_visao:
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Técnicos por atividade")
        df_atv = (
            df_f.groupby("atividade")["tecnico"]
            .nunique()
            .reset_index()
            .rename(columns={"atividade": "Atividade", "tecnico": "Técnicos"})
            .sort_values("Técnicos", ascending=True)
        )
        fig_atv = px.bar(
            df_atv, x="Técnicos", y="Atividade", orientation="h",
            color="Técnicos",
            color_continuous_scale=["#1B4332", "#2D6A4F", "#40916C", "#52B788", "#74C69D"],
            text="Técnicos",
        )
        fig_atv.update_traces(textposition="auto")
        fig_atv.update_layout(
            height=350,
            margin=dict(l=0, r=60, t=10, b=10),
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_atv, use_container_width=True)

    with col_b:
        st.subheader("Distribuição do gap (dias)")
        bins   = [0, 15, 30, 9999]
        labels = ["✅ OK (0–15)", "⚠️ Atenção (16–30)", "🚨 Crítico (>30)"]
        df_gap_cat = df_f.copy()
        df_gap_cat["faixa"] = pd.cut(df_gap_cat["gap_dias"], bins=bins, labels=labels)
        df_gap_pie = (
            df_gap_cat["faixa"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "Faixa", "faixa": "Qtd"})
        )
        df_gap_pie.columns = ["Faixa", "Qtd"]
        fig_pie = px.pie(
            df_gap_pie, names="Faixa", values="Qtd",
            color="Faixa",
            color_discrete_map={
                "✅ OK (0–15)":       "#1D9E75",
                "⚠️ Atenção (16–30)": "#BA7517",
                "🚨 Crítico (>30)":  "#E24B4A",
            },
            hole=0.5,
        )
        fig_pie.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    col_c, col_d = st.columns([2, 1])

    with col_c:
        st.subheader("Top 10 municípios atendidos")
        df_mun_top = (
            df_f.groupby("nome")["tecnico"]
            .nunique()
            .reset_index()
            .rename(columns={"nome": "Município", "tecnico": "Técnicos"})
            .sort_values("Técnicos", ascending=False)
            .head(10)
        )
        fig_mun = px.bar(
            df_mun_top, x="Município", y="Técnicos",
            color="Técnicos", text="Técnicos",
            color_continuous_scale=["#0B3C5D", "#145374", "#5588A3", "#9BD1E5"],
        )
        fig_mun.update_traces(textposition="outside")
        fig_mun.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=20, b=60),
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-35, showgrid=False, tickfont=dict(size=11), title=None),
            yaxis=dict(showgrid=False, title=dict(text="Técnicos", font=dict(size=12))),
        )
        st.plotly_chart(fig_mun, use_container_width=True)

    with col_d:
        st.subheader("Tempo médio por projeto (meses)")
        df_proj = (
            df_f.groupby("projeto")["tempo_projeto_meses"]
            .mean()
            .reset_index()
            .rename(columns={"projeto": "Projeto", "tempo_projeto_meses": "Média (meses)"})
        )
        df_proj["Média (meses)"] = df_proj["Média (meses)"].round(1)
        df_proj = df_proj.sort_values("Média (meses)", ascending=True)

        fig_proj = px.bar(
            df_proj, x="Média (meses)", y="Projeto", orientation="h",
            color="Média (meses)", color_continuous_scale="Blues",
            text="Média (meses)",
        )
        fig_proj.update_traces(textposition="outside")
        fig_proj.update_layout(
            height=380,
            margin=dict(l=100, r=40, t=20, b=60),
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, title=dict(text="Média (meses)", standoff=15, font=dict(size=12))),
            yaxis=dict(showgrid=False, title=None, automargin=True),
        )
        st.plotly_chart(fig_proj, use_container_width=True)

# ════════════════════════════════════════════
# ABA 2 — MAPA OPERACIONAL
# ════════════════════════════════════════════
with aba_mapa:
    cor_atv_map = {
        atv: CORES[i % len(CORES)]
        for i, atv in enumerate(sorted(df_f["atividade"].dropna().unique()))
    }

    col_map, col_leg = st.columns([4, 1])

    with col_leg:
        st.markdown("### Legenda")
        for atv in sorted(df_f["atividade"].dropna().unique()):
            cor = cor_atv_map.get(atv, "#CCC")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
                f'<div style="width:14px;height:14px;background:{cor};border-radius:50%;flex-shrink:0;"></div>'
                f'<span style="font-size:12px;">{atv}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f"**{df_f.shape[0]}** pontos no mapa")

    with col_map:
        import math

        m = folium.Map(location=[-5.2, -39.5], zoom_start=7, tiles="cartodbpositron")
        if geo_ceara:
            folium.GeoJson(
                geo_ceara,
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#bdc3c7",
                    "weight": 0.8,
                },
            ).add_to(m)

        # Calcular offset circular por município
        # Conta quantos técnicos há em cada coordenada e atribui posição no círculo
        coord_counter = {}
        offsets = []
        RAIO = 0.04  # graus (~4 km) — ajusta o espalhamento

        for _, row in df_f.iterrows():
            key = (round(row["latitude"], 4), round(row["longitude"], 4))
            idx = coord_counter.get(key, 0)
            coord_counter[key] = idx + 1
            offsets.append((key, idx))

        # Pré-calcular total por coordenada para distribuir em círculo
        totais = {}
        for key, _ in offsets:
            totais[key] = totais.get(key, 0) + 1

        coord_counter2 = {}
        for i, (_, row) in enumerate(df_f.iterrows()):
            key = (round(row["latitude"], 4), round(row["longitude"], 4))
            idx = coord_counter2.get(key, 0)
            coord_counter2[key] = idx + 1

            total = totais[key]
            if total == 1:
                lat_off = row["latitude"]
                lon_off = row["longitude"]
            else:
                angulo = (2 * math.pi / total) * idx
                raio   = RAIO * (1 + (total // 8) * 0.3)  # raio maior se muitos técnicos
                lat_off = row["latitude"]  + raio * math.cos(angulo)
                lon_off = row["longitude"] + raio * math.sin(angulo)

            cor_hex  = cor_atv_map.get(row["atividade"], "#1B4332")
            inicial  = str(row["tecnico"]).strip()[0].upper()
            gap_color = (
                "#E24B4A" if row["gap_dias"] > 30
                else ("#BA7517" if row["gap_dias"] > 15 else "#1D9E75")
            )
            gap_label = (
                "🚨 Crítico" if row["gap_dias"] > 30
                else ("⚠️ Atenção" if row["gap_dias"] > 15 else "✅ OK")
            )

            html_icone = (
                f'<div style="width:30px;height:30px;border-radius:50%;background:{cor_hex};'
                f'border:2px solid white;display:flex;align-items:center;justify-content:center;'
                f'color:white;font-weight:bold;font-size:13px;'
                f'box-shadow:0px 2px 5px rgba(0,0,0,0.35);">{inicial}</div>'
            )
            html_tooltip = (
                f'<div style="font-family:sans-serif;background:white;border-radius:10px;'
                f'width:240px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,0.12);border:1px solid #eee;">'
                f'<div style="background:{cor_hex};color:white;padding:10px 14px;">'
                f'<div style="font-size:13px;font-weight:700;text-transform:uppercase;">{row["tecnico"]}</div>'
                f'<div style="font-size:11px;opacity:0.85;">{row["atividade"]}</div></div>'
                f'<div style="padding:10px 14px;font-size:12px;color:#333;line-height:1.6;">'
                f'<div><b>Supervisor:</b> {row["supervisor_atual"]}</div>'
                f'<div><b>Município:</b> {row["nome"]}</div>'
                f'<div><b>Projeto:</b> {row["projeto"]}</div>'
                f'<div><b>Tempo:</b> {int(row["tempo_projeto_meses"])} meses</div>'
                f'<div style="color:{gap_color};font-weight:700;margin-top:4px;">'
                f'<b>GAP:</b> {int(row["gap_dias"])} dias — {gap_label}</div>'
                f'</div></div>'
            )

            folium.Marker(
                [lat_off, lon_off],
                icon=DivIcon(html=html_icone, icon_size=(30, 30), icon_anchor=(15, 15)),
                popup=folium.Popup(html_tooltip, max_width=280),
            ).add_to(m)

        st_folium(m, width="100%", height=620)

# ════════════════════════════════════════════
# ABA 3 — EQUIPE & SUPERVISORES
# ════════════════════════════════════════════
with aba_equipe:

    supervisores_lista = sorted(df_f["supervisor_atual"].dropna().unique())

    sup_escolhido = st.selectbox(
        "👤 Selecione um supervisor para ver sua equipe",
        options=supervisores_lista,
    )

    df_sup_sel = df_f[df_f["supervisor_atual"] == sup_escolhido]

    # KPIs do supervisor selecionado
    n_tec_sup  = df_sup_sel["tecnico"].nunique()
    n_mun_sup  = df_sup_sel["municipio_atual"].nunique()
    n_proj_sup = df_sup_sel["projeto"].nunique()
    n_crit_sup = (df_sup_sel["gap_dias"] > 30).sum()
    gap_medio  = round(df_sup_sel["gap_dias"].mean(), 1) if not df_sup_sel.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("👤 Técnicos",    n_tec_sup)
    k2.metric("🏙️ Municípios",  n_mun_sup)
    k3.metric("📂 Projetos",    n_proj_sup)
    k4.metric("⏱️ Gap Médio",   f"{gap_medio} dias")
    k5.metric("🚨 Críticos",    n_crit_sup)

    st.divider()

    col_l, col_r = st.columns([2, 3])

    # ── Esquerda: lista de técnicos com status ──
    with col_l:
        st.subheader("👥 Técnicos da equipe")
        df_tec_sup = (
            df_sup_sel.groupby("tecnico")
            .agg(
                Atividade=("atividade", "first"),
                Município=("municipio_atual", "first"),
                Gap=("gap_dias", "max"),
            )
            .reset_index()
            .rename(columns={"tecnico": "Técnico"})
            .sort_values("Gap", ascending=False)
        )
        for _, r in df_tec_sup.iterrows():
            if r["Gap"] > 30:
                badge = f'<span class="badge-critico">{int(r["Gap"])} dias</span>'
            elif r["Gap"] > 15:
                badge = f'<span class="badge-atencao">{int(r["Gap"])} dias</span>'
            else:
                badge = f'<span class="badge-ok">{int(r["Gap"])} dias</span>'

            st.markdown(
                f'<div style="padding:8px 12px;margin-bottom:6px;background:white;'
                f'border-radius:8px;border:1px solid #e8f4ee;box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                f'<div style="font-weight:600;font-size:13px;color:#1B4332;">{r["Técnico"]}</div>'
                f'<div style="font-size:11px;color:#666;margin-top:2px;">'
                f'{r["Atividade"]} · {r["Município"]} &nbsp;{badge}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Direita: atividades e total de técnicos ──
    with col_r:
        st.subheader("🌿 Técnicos por atividade")
        df_atv_sup = (
            df_sup_sel.groupby("atividade")["tecnico"]
            .nunique()
            .reset_index()
            .rename(columns={"atividade": "Atividade", "tecnico": "Técnicos"})
            .sort_values("Técnicos", ascending=True)
        )
        fig_atv_sup = px.bar(
            df_atv_sup, x="Técnicos", y="Atividade", orientation="h",
            color="Técnicos",
            color_continuous_scale=["#74C69D", "#1B4332"],
            text="Técnicos",
        )
        fig_atv_sup.update_traces(textposition="outside")
        fig_atv_sup.update_layout(
            height=max(300, len(df_atv_sup) * 56),
            margin=dict(l=0, r=60, t=10, b=10),
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=False, title=None),
        )
        st.plotly_chart(fig_atv_sup, use_container_width=True)



# ════════════════════════════════════════════
# ABA 4 — ALERTAS & ACOMPANHAMENTO
# ════════════════════════════════════════════
with aba_alertas:
    df_critico = df_f[df_f["gap_dias"] > 30].sort_values("gap_dias", ascending=False)
    df_atencao = df_f[(df_f["gap_dias"] > 15) & (df_f["gap_dias"] <= 30)].sort_values("gap_dias", ascending=False)
    df_ok      = df_f[df_f["gap_dias"] <= 15]

    col_al1, col_al2 = st.columns(2)

    with col_al1:
        st.markdown(f"### 🚨 Crítico — Gap > 30 dias ({len(df_critico)} técnicos)")
        if df_critico.empty:
            st.success("Nenhum técnico em situação crítica!")
        else:
            for _, r in df_critico.iterrows():
                st.markdown(
                    f'<div class="alert-card-critico">'
                    f'<b>{r["tecnico"]}</b> &nbsp;'
                    f'<span class="badge-critico">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:12px;color:#666;">'
                    f'{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )

    with col_al2:
        st.markdown(f"### ⚠️ Atenção — Gap 16–30 dias ({len(df_atencao)} técnicos)")
        if df_atencao.empty:
            st.success("Nenhum técnico em atenção!")
        else:
            for _, r in df_atencao.iterrows():
                st.markdown(
                    f'<div class="alert-card-atencao">'
                    f'<b>{r["tecnico"]}</b> &nbsp;'
                    f'<span class="badge-atencao">{int(r["gap_dias"])} dias</span><br>'
                    f'<span style="font-size:12px;color:#666;">'
                    f'{r["atividade"]} · {r["supervisor_atual"]} · {r["nome"]}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("Ranking de gap — top 20 técnicos")
    df_gap_rank = (
        df_f[df_f["gap_dias"] > 0][["tecnico", "gap_dias", "atividade"]]
        .drop_duplicates("tecnico")
        .sort_values("gap_dias", ascending=False)
        .head(20)
    )
    df_gap_rank["cor"] = df_gap_rank["gap_dias"].apply(
        lambda x: "#E24B4A" if x > 30 else ("#BA7517" if x > 15 else "#1D9E75")
    )
    fig_rank = go.Figure(go.Bar(
        x=df_gap_rank["tecnico"], y=df_gap_rank["gap_dias"],
        marker_color=df_gap_rank["cor"],
        text=df_gap_rank["gap_dias"], textposition="outside",
    ))
    fig_rank.add_hline(y=30, line_dash="dash", line_color="#E24B4A")
    fig_rank.add_hline(y=15, line_dash="dot",  line_color="#BA7517")
    fig_rank.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=20, b=80),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickangle=-40, showgrid=False),
        yaxis=dict(title="Gap (dias)", showgrid=True, gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.divider()
    st.subheader("📈 Tendência de gap médio — últimas 8 semanas")
    st.caption("Cálculo baseado em data_ultima_visita vs. data_atualizacao por período.")

    hoje = datetime.now()
    semanas, gaps_medios = [], []
    for i in range(7, -1, -1):
        data_ref = hoje - timedelta(weeks=i)
        df_temp  = df_f[df_f["data_ultima_visita"] <= data_ref].copy()
        if not df_temp.empty:
            df_temp["gap_sim"] = (data_ref - df_temp["data_ultima_visita"]).dt.days
            gaps_medios.append(round(df_temp["gap_sim"].mean(), 1))
        else:
            gaps_medios.append(0)
        semanas.append(f"S{8 - i}")

    df_trend = pd.DataFrame({"Semana": semanas, "Gap médio (dias)": gaps_medios})
    fig_trend = px.line(
        df_trend, x="Semana", y="Gap médio (dias)",
        markers=True, line_shape="spline",
        color_discrete_sequence=["#1D9E75"],
    )
    fig_trend.add_hline(y=30, line_dash="dash", line_color="#E24B4A", annotation_text="Crítico")
    fig_trend.add_hline(y=15, line_dash="dot",  line_color="#BA7517", annotation_text="Atenção")
    fig_trend.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=20, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ════════════════════════════════════════════
# ABA 5 — EXPORTAR DADOS
# ════════════════════════════════════════════
with aba_download:
    st.subheader("📥 Exportação de Dados")
    st.info(f"Exportando **{len(df_f)}** registros conforme filtros aplicados.")

    COLS_EXPORT = [
        "regiao_faec", "supervisor_atual", "projeto", "atividade", "tecnico",
        "municipios", "municipio_atual", "data_primeira_visita", "data_ultima_visita",
        "tempo_projeto_meses", "status_tecnico",
    ]

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        buffer_full = io.BytesIO()
        with pd.ExcelWriter(buffer_full, engine="xlsxwriter") as writer:
            df_f[COLS_EXPORT].to_excel(writer, sheet_name="Base Completa", index=False)
            (
                df_f.groupby("supervisor_atual")
                .agg(
                    Técnicos=("tecnico", "nunique"),
                    Municípios=("municipio_atual", "nunique"),
                    Projetos=("projeto", "nunique"),
                )
                .reset_index()
                .to_excel(writer, sheet_name="Resumo Supervisores", index=False)
            )
        st.download_button(
            label="📊 Exportar Excel Completo",
            data=buffer_full.getvalue(),
            file_name=f"ateg_completo_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_d2:
        st.download_button(
            label="📄 Exportar CSV",
            data=df_f[COLS_EXPORT].to_csv(index=False, sep=";").encode("utf-8"),
            file_name=f"ateg_base_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    with col_d3:
        df_sup_csv = (
            df_f.groupby("supervisor_atual")
            .agg(
                Técnicos=("tecnico", "nunique"),
                Municípios=("municipio_atual", "nunique"),
                Projetos=("projeto", "nunique"),
            )
            .reset_index()
        )
        st.download_button(
            label="👤 Resumo Supervisores",
            data=df_sup_csv.to_csv(index=False, sep=";").encode("utf-8"),
            file_name=f"ateg_supervisores_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    st.divider()
    st.subheader("📋 Prévia dos Dados Exportados")

    df_preview = df_f.copy()
    df_preview["data_primeira_visita"] = pd.to_datetime(df_preview["data_primeira_visita"]).dt.strftime("%d/%m/%Y")
    df_preview["data_ultima_visita"]   = pd.to_datetime(df_preview["data_ultima_visita"]).dt.strftime("%d/%m/%Y")

    st.dataframe(
        df_preview[COLS_EXPORT].sort_values("tempo_projeto_meses", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "regiao_faec":           "Região FAEC",
            "projeto":               "Projeto",
            "atividade":             "Atividade",
            "supervisor_atual":      "Supervisor",
            "tecnico":               "Técnico",
            "municipios":            "Municípios",
            "municipio_atual":       "Município Atual",
            "data_primeira_visita":  "Primeira Visita",
            "data_ultima_visita":    "Última Visita",
            "tempo_projeto_meses":   st.column_config.NumberColumn(
                "Tempo Projeto (Meses)", format="%.0f", width="small"
            ),
            "status_tecnico":        "Status Técnico",
        },
    )

# ════════════════════════════════════════════
# ABA 6 — CONSOLIDADO
# ════════════════════════════════════════════
with aba_consolidado:

    st.subheader("📋 Tabela Consolidada")

    tipo_filtro = st.radio(
        "Filtrar por:",
        ["Região FAEC", "Supervisor"],
        horizontal=True,
    )

    if tipo_filtro == "Região FAEC":
        opcoes = sorted(df_f["regiao_faec"].dropna().unique())
        escolha = st.selectbox("Selecione a Região FAEC", opcoes)
        df_cons = df_f[df_f["regiao_faec"] == escolha]
    else:
        opcoes = sorted(df_f["supervisor_atual"].dropna().unique())
        escolha = st.selectbox("Selecione o Supervisor", opcoes)
        df_cons = df_f[df_f["supervisor_atual"] == escolha]

    st.divider()

    # Tabela consolidada por atividade
    df_tabela = (
        df_cons.groupby("atividade")
        .agg(
            Total_Supervisores=("supervisor_atual", "nunique"),
            Total_Técnicos=("tecnico", "nunique"),
        )
        .reset_index()
        .rename(columns={
            "atividade":          "Atividade",
            "Total_Supervisores": "Supervisores",
            "Total_Técnicos":     "Técnicos",
        })
        .sort_values("Técnicos", ascending=False)
    )

    # Linha de total geral
    total_row = pd.DataFrame([{
        "Atividade":   "**TOTAL GERAL**",
        "Supervisores": df_tabela["Supervisores"].sum(),
        "Técnicos":     df_tabela["Técnicos"].sum(),
    }])
    df_tabela_final = pd.concat([df_tabela, total_row], ignore_index=True)

    # Renderizar como HTML para melhor controle visual
    linhas_html = ""
    for _, r in df_tabela.iterrows():
        linhas_html += (
            f'<tr>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;">{r["Atividade"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{int(r["Supervisores"])}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{int(r["Técnicos"])}</td>'
            f'</tr>'
        )

    total_sup = int(df_tabela["Supervisores"].sum())
    total_tec = int(df_tabela["Técnicos"].sum())

    linhas_html += (
        f'<tr style="background:#1B4332;">'
        f'<td style="padding:10px 14px;font-size:14px;font-weight:800;color:white;">TOTAL GERAL</td>'
        f'<td style="padding:10px 14px;font-size:14px;font-weight:800;color:white;text-align:center;">{total_sup}</td>'
        f'<td style="padding:10px 14px;font-size:14px;font-weight:800;color:white;text-align:center;">{total_tec}</td>'
        f'</tr>'
    )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
        f'<thead><tr style="background:#2D6A4F;">'
        f'<th style="padding:10px 14px;text-align:left;font-size:13px;color:white;font-weight:700;">Atividade</th>'
        f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Total Supervisores</th>'
        f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Total Técnicos</th>'
        f'</tr></thead>'
        f'<tbody>{linhas_html}</tbody>'
        f'</table>',
        unsafe_allow_html=True,
    )