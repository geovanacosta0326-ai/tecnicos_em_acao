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
[data-testid="stSidebar"] { background-color: #d8eede; }
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
[data-testid="manage-app-button"] { display: none !important; }
.viewerBadge_container__r5tak { display: none !important; }
.stDeployButton { display: none !important; }

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
# 5. SIDEBAR — FILTROS (EM CASCATA / DEPENDENTES)
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filtros")
st.sidebar.markdown("---")

# 1. Filtro de Região FAEC (Esta é a base inicial)
opcoes_regiao = sorted(df_mapa["regiao_faec"].dropna().unique())
regiao_sel = st.sidebar.multiselect("🗺️ Região FAEC", opcoes_regiao)

# Criamos uma cópia temporária que vai afunilar as opções passo a passo
df_sidebar = df_mapa.copy()
if regiao_sel:
    df_sidebar = df_sidebar[df_sidebar["regiao_faec"].isin(regiao_sel)]

# 2. Filtro de Supervisores (Agora lê de df_sidebar, mostrando apenas quem sobrou da Região)
opcoes_sup = sorted(df_sidebar["supervisor_atual"].dropna().unique())
sup_sel = st.sidebar.multiselect("👤 Supervisores", opcoes_sup)

if sup_sel:
    df_sidebar = df_sidebar[df_sidebar["supervisor_atual"].isin(sup_sel)]

# 3. Filtro de Projetos (Lê de df_sidebar, dependendo de Região + Supervisor)
opcoes_projeto = sorted(df_sidebar["projeto"].dropna().unique())
projetos_sel = st.sidebar.multiselect("📂 Projetos", opcoes_projeto)

if projetos_sel:
    df_sidebar = df_sidebar[df_sidebar["projeto"].isin(projetos_sel)]

# 4. Filtro de Atividades (Lê de df_sidebar, dependendo de todos os filtros acima)
options_atividade = sorted(df_sidebar["atividade"].dropna().unique())
atividades_sel = st.sidebar.multiselect("🌿 Atividades", options_atividade)

if atividades_sel:
    df_sidebar = df_sidebar[df_sidebar["atividade"].isin(atividades_sel)]

# 5. Filtro de Status do Gap
status_opcoes = ["Todos", "🔴 Crítico (>30 dias)", "🟡 Atenção (16–30 dias)", "🟢 OK (≤15 dias)"]
status_sel = st.sidebar.selectbox("⚠️ Status do Gap", status_opcoes)

# 6. Filtro do Slider de Tempo de Projeto (Ajustado pela sobra dos filtros)
min_m = int(df_sidebar["tempo_projeto_meses"].min()) if not df_sidebar.empty else 1
max_m = int(df_sidebar["tempo_projeto_meses"].max()) if not df_sidebar.empty else 31
if min_m == max_m:
    max_m += 1
meses_sel = st.sidebar.slider("⏱️ Tempo de Projeto (Meses)", min_m, max_m, (min_m, max_m))

# ─────────────────────────────────────────────
# APLICAÇÃO FINAL DE TODOS OS FILTROS EM df_f
# ─────────────────────────────────────────────
# O df_sidebar já contém os filtros de Região, Supervisor, Projeto e Atividade acumulados
df_f = df_sidebar.copy()

# Filtro de Tempo de Projeto
df_f = df_f[
    (df_f["tempo_projeto_meses"] >= meses_sel[0])
    & (df_f["tempo_projeto_meses"] <= meses_sel[1])
]

# Filtro de Status do Gap
if status_sel == "🔴 Crítico (>30 dias)":
    df_f = df_f[df_f["gap_dias"] > 30]
elif status_sel == "🟡 Atenção (16–30 dias)":
    df_f = df_f[(df_f["gap_dias"] > 15) & (df_f["gap_dias"] <= 30)]
elif status_sel == "🟢 OK (≤15 dias)":
    df_f = df_f[df_f["gap_dias"] <= 15]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(df_f)}** registros no filtro")


# ─────────────────────────────────────────────
# 6. KPIs — SEQUÊNCIA E DESIGN OTIMIZADOS (COMPLETO)
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 6. KPIs — DESIGN COMPACTO E MÁSCARAS CORRIGIDAS
# ─────────────────────────────────────────────
n_sup = df_f["supervisor_atual"].nunique() if "supervisor_atual" in df_f.columns else 0
n_tec = df_f["tecnico"].nunique()
n_proj = df_f["projeto"].nunique()
n_atv = df_f["atividade"].nunique()
n_mun = df_f["nome"].nunique()

t_propriedades = df_f["total_propriedades"].sum()
p_ativas = df_f["propriedades_ativas"].sum()
p_inativas = df_f["propriedades_inativas"].sum()

t_visitas = df_f["total_visitas"].sum()
v_validas = df_f["visitas_validas"].sum()
v_invalidas = df_f["visitas_invalidas"].sum()

pct_ativas = round((p_ativas / t_propriedades * 100), 1) if t_propriedades > 0 else 0
pct_inativas = round((p_inativas / t_propriedades * 100), 1) if t_propriedades > 0 else 0
pct_aproveitamento = round((v_validas / t_visitas * 100), 1) if t_visitas > 0 else 0

# Formatação correta dos milhares para o padrão brasileiro (Ponto como separador)
txt_propriedades = f"{t_propriedades:,}".replace(",", ".")
txt_ativas = f"{p_ativas:,}".replace(",", ".")
txt_inativas = f"{p_inativas:,}".replace(",", ".")
txt_visitas = f"{t_visitas:,}".replace(",", ".")
txt_validas = f"{v_validas:,}".replace(",", ".")
txt_invalidas = f"{v_invalidas:,}".replace(",", ".")

st.markdown("### 📊 Indicadores Consolidados")

# Estilo inline modificado para reduzir a altura e o padding dos cards (deixando-os menores)
style_kpi = "background:white; border-radius:8px; padding:10px 14px; border:1px solid #e8f4ee; box-shadow:0 1px 3px rgba(0,0,0,0.04);"

# --- LINHA 1: ESTRUTURA OPERACIONAL ---
col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.markdown(f'<div style="{style_kpi}"><div style="font-size:11px;color:#52796f;font-weight:600;text-transform:uppercase;">Supervisores</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{n_sup}</div><div style="font-size:10px;color:#74C69D;">👥 Gestores</div></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div style="{style_kpi}"><div style="font-size:11px;color:#52796f;font-weight:600;text-transform:uppercase;">Técnicos</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{n_tec}</div><div style="font-size:10px;color:#74C69D;">👤 Em campo</div></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div style="{style_kpi}"><div style="font-size:11px;color:#52796f;font-weight:600;text-transform:uppercase;">Projetos</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{n_proj}</div><div style="font-size:10px;color:#74C69D;">📂 Ativos</div></div>', unsafe_allow_html=True)
with col4: st.markdown(f'<div style="{style_kpi}"><div style="font-size:11px;color:#52796f;font-weight:600;text-transform:uppercase;">Atividades</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{n_atv}</div><div style="font-size:10px;color:#74C69D;">🌿 Cadeias</div></div>', unsafe_allow_html=True)
with col5: st.markdown(f'<div style="{style_kpi}"><div style="font-size:11px;color:#52796f;font-weight:600;text-transform:uppercase;">Municípios</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{n_mun}</div><div style="font-size:10px;color:#74C69D;">🏙️ Cobertura</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

# --- LINHA 2: PROPRIEDADES ---
col_p1, col_p2, col_p3 = st.columns(3)
with col_p1: st.markdown(f'<div style="{style_kpi} border-left:4px solid #2D6A4F;"><div style="font-size:11px;color:#2D6A4F;font-weight:700;text-transform:uppercase;">Total de Propriedades</div><div style="font-size:26px;font-weight:800;color:#0F6E56;margin-top:2px;">{txt_propriedades}</div><div style="font-size:10px;color:#666;">🏡 Mapeadas</div></div>', unsafe_allow_html=True)
with col_p2: st.markdown(f'<div style="{style_kpi} border-left:4px solid #1D9E75;"><div style="font-size:11px;color:#1D9E75;font-weight:700;text-transform:uppercase;">Propriedades Ativas</div><div style="font-size:26px;font-weight:800;color:#1D9E75;margin-top:2px;">{txt_ativas}</div><div style="font-size:10px;color:#1D9E75;font-weight:bold;">📈 {pct_ativas}% do total</div></div>', unsafe_allow_html=True)
with col_p3: st.markdown(f'<div style="{style_kpi} border-left:4px solid #E24B4A;"><div style="font-size:11px;color:#E24B4A;font-weight:700;text-transform:uppercase;">Propriedades Inativas</div><div style="font-size:26px;font-weight:800;color:#E24B4A;margin-top:2px;">{txt_inativas}</div><div style="font-size:10px;color:#E24B4A;font-weight:bold;">📉 {pct_inativas}% desativadas</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)


# --- LINHA 3: AUDITORIA DE VISITAS ---
col_v1, col_v2, col_v3, col_v4 = st.columns(4)
with col_v1: 
    st.markdown(f'<div style="{style_kpi} border-left:4px solid #40916C;"><div style="font-size:11px;color:#40916C;font-weight:700;text-transform:uppercase;">Total de Visitas</div><div style="font-size:24px;font-weight:800;color:#1B4332;margin-top:2px;">{txt_visitas}</div><div style="font-size:10px;color:#666;">📊 Realizadas</div></div>', unsafe_allow_html=True)

with col_v2: 
    st.markdown(f'<div style="{style_kpi} border-left:4px solid #1D9E75;"><div style="font-size:11px;color:#1D9E75;font-weight:700;text-transform:uppercase;">Visitas Válidas</div><div style="font-size:24px;font-weight:800;color:#1D9E75;margin-top:2px;">{txt_validas}</div><div style="font-size:10px;color:#1D9E75;">✅ Conformidade OK</div></div>', unsafe_allow_html=True)

with col_v3: 
    st.markdown(f'<div style="{style_kpi} border-left:4px solid #E24B4A;"><div style="font-size:11px;color:#E24B4A;font-weight:700;text-transform:uppercase;">Visitas Inválidas</div><div style="font-size:24px;font-weight:800;color:#E24B4A;margin-top:2px;">{txt_invalidas}</div><div style="font-size:10px;color:#E24B4A;">⚠️ Visitas inválidas</div></div>', unsafe_allow_html=True)

with col_v4: 
    st.markdown(f'<div style="{style_kpi} border-left:4px solid #52B788;background:linear-gradient(135deg,#fff 0%,#f4fbf7 100%);"><div style="font-size:11px;color:#0F6E56;font-weight:700;text-transform:uppercase;">Taxa de Aproveitamento</div><div style="font-size:24px;font-weight:800;color:#0F6E56;margin-top:2px;">{pct_aproveitamento}%</div><div style="font-size:10px;color:#2D6A4F;font-weight:bold;">🎯 Eficiência</div></div>', unsafe_allow_html=True)
st.divider()
# ─────────────────────────────────────────────
# 7. ABAS PRINCIPAIS
# ─────────────────────────────────────────────
aba_visao, aba_mapa, aba_equipe, aba_alertas, aba_download, aba_consolidado, aba_historico = st.tabs([
    "📊 Visão Geral",
    "🗺️ Mapa Operacional",
    "👥 Equipe & Supervisores",
    "🚨 Alertas & Acompanhamento",
    "📥 Exportar Dados",
    "📋 Consolidado",
    "🔄 Histórico de Trocas",
])

CORES = [
    "#E63946",  # vermelho vivo
    "#1D9E75",  # verde
    "#FFB703",  # amarelo
    "#7B2D8B",  # roxo
    "#FB8500",  # laranja
    "#1D3557",  # azul escuro
    "#06D6A0",  # verde água
    "#EF476F",  # rosa
    "#118AB2",  # azul médio
    "#8B4513",  # marrom
    "#2EC4B6",  # ciano
    "#FF6B6B",  # salmão
    "#6A0572",  # roxo escuro
    "#F77F00",  # laranja escuro
    "#4CC9F0",  # azul claro
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
                f'<div style="font-family:\'Segoe UI\',sans-serif;background:white;border-radius:10px;'
                f'width:230px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.18);">'
                f'<div style="background:{cor_hex};padding:10px 14px;">'
                f'<div style="font-size:12px;font-weight:800;color:white;text-transform:uppercase;letter-spacing:0.3px;line-height:1.3;">{row["tecnico"]}</div>'
                f'<div style="font-size:10px;color:rgba(255,255,255,0.85);margin-top:2px;">{row["atividade"]}</div>'
                f'</div>'
                f'<div style="padding:10px 14px 4px 14px;">'
                f'<div style="font-size:11px;color:#555;margin-bottom:5px;"><b style="color:#1B4332;">👤</b> {row["supervisor_atual"]}</div>'
                f'<div style="font-size:11px;color:#555;margin-bottom:5px;"><b style="color:#1B4332;">📍</b> {row["nome"]}</div>'
                f'<div style="font-size:11px;color:#555;margin-bottom:5px;"><b style="color:#1B4332;">📂</b> {row["projeto"]}</div>'
                f'<div style="font-size:11px;color:#555;margin-bottom:8px;"><b style="color:#1B4332;">⏱️</b> {int(row["tempo_projeto_meses"])} meses</div>'
                f'</div>'
                f'<div style="margin:0 14px 12px 14px;padding:6px 10px;background:{gap_color}20;'
                f'border-radius:6px;border-left:3px solid {gap_color};">'
                f'<span style="font-size:11px;font-weight:700;color:{gap_color};">{int(row["gap_dias"])} dias — {gap_label}</span>'
                f'</div>'
                f'</div>'
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

    # O radio agora analisa o 'df_f' que já veio filtrado da Barra Lateral
    tipo_filtro = st.radio(
        "Visualizar por:",
        ["Todos", "Região FAEC", "Supervisor", "Projeto"],
        horizontal=True,
        key="radio_filtro_consolidado_unificado"
    )

    if tipo_filtro == "Todos":
        df_cons = df_f.copy()  # <--- Aqui ele herda diretamente o filtro da sidebar
        escolha = "Todos"

    elif tipo_filtro == "Região FAEC":
        # Extrai apenas as regiões que restaram após o filtro da sidebar
        opcoes = sorted(df_f["regiao_faec"].dropna().unique())
        if opcoes:
            escolha = st.selectbox("Selecione a Região FAEC", opcoes, key="sb_regiao_cons")
            df_cons = df_f[df_f["regiao_faec"] == escolha]
        else:
            st.warning("Nenhuma Região FAEC disponível com os filtros atuais.")
            df_cons = pd.DataFrame()

    elif tipo_filtro == "Supervisor":
        # Extrai apenas os supervisores que restaram após o filtro da sidebar
        opcoes = sorted(df_f["supervisor_atual"].dropna().unique())
        if opcoes:
            escolha = st.selectbox("Selecione o Supervisor", opcoes, key="sb_supervisor_cons")
            df_cons = df_f[df_f["supervisor_atual"] == escolha]
        else:
            st.warning("Nenhum Supervisor disponível com os filtros atuais.")
            df_cons = pd.DataFrame()

    elif tipo_filtro == "Projeto":
        # Extrai apenas os projetos que restaram após o filtro da sidebar
        opcoes = sorted(df_f["projeto"].dropna().unique())
        if opcoes:
            escolha = st.selectbox("Selecione o Projeto", opcoes, key="sb_projeto_cons")
            df_cons = df_f[df_f["projeto"] == escolha]
        else:
            st.warning("Nenhum Projeto disponível com os filtros atuais.")
            df_cons = pd.DataFrame()

    st.divider()

    # Se o dataframe resultante não estiver vazio, executa seus agrupamentos e HTMLs exatamente como você fez
    if not df_cons.empty:
        # 1. Agrupamento focado em Propriedades (Tabela Superior)
        df_tabela = (
            df_cons.groupby("atividade")
            .agg(
                Supervisores=("supervisor_atual", "nunique"),
                Tecnicos=("tecnico", "nunique"),
                Ativas=("propriedades_ativas", "sum"),
                Inativas=("propriedades_inativas", "sum"),
                Total=("total_propriedades", "sum")
            )
            .reset_index()
            .sort_values("Total", ascending=False)
        )

        with st.container(key=f"container_tabela_sup_{tipo_filtro}_{escolha.replace(' ', '_')}"):
            linhas_html = ""
            for _, r in df_tabela.iterrows():
                total_prop = r["Total"] if r["Total"] > 0 else 1
                pct_atv = (r["Ativas"] / total_prop) * 100
                pct_ina = (r["Inativas"] / total_prop) * 100

                txt_ativas = f"{int(r['Ativas']):,}".replace(",", ".")
                txt_inativas = f"{int(r['Inativas']):,}".replace(",", ".")
                txt_total = f"{int(r['Total']):,}".replace(",", ".")
                
                linhas_html += (
                    f'<tr>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;">{r["atividade"]}</td>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{int(r["Supervisores"])}</td>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{int(r["Tecnicos"])}</td>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#1D9E75;font-weight:600;">{txt_ativas} <span style="font-size:11px;color:#52B788;font-weight:normal;">({pct_atv:.1f}%)</span></td>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#E24B4A;font-weight:600;">{txt_inativas} <span style="font-size:11px;color:#f3a5a5;font-weight:normal;">({pct_ina:.1f}%)</span></td>'
                    f'<td style="padding:8px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#1B4332;font-weight:700;">{txt_total}</td>'
                    f'</tr>'
                )

            sum_sup = int(df_tabela["Supervisores"].sum())
            sum_tec = int(df_tabela["Tecnicos"].sum())
            sum_atv = int(df_tabela["Ativas"].sum())
            sum_ina = int(df_tabela["Inativas"].sum())
            sum_tot = int(df_tabela["Total"].sum())
            
            tot_geral = sum_tot if sum_tot > 0 else 1
            pct_atv_g = (sum_atv / tot_geral) * 100
            pct_ina_g = (sum_ina / tot_geral) * 100

            linhas_html += (
                f'<tr style="background:#1B4332;">'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;">TOTAL GERAL</td>'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;text-align:center;">{sum_sup}</td>'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;text-align:center;">{sum_tec}</td>'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:#95d5b2;text-align:center;">{sum_atv:,}'.replace(",", ".") + f' ({pct_atv_g:.1f}%)</td>'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:#f3a5a5;text-align:center;">{sum_ina:,}'.replace(",", ".") + f' ({pct_ina_g:.1f}%)</td>'
                f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;text-align:center;">{sum_tot:,}'.replace(",", ".") + f'</td>'
                f'</tr>'
            )

            st.markdown(
                f'<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
                f'<thead><tr style="background:#2D6A4F;">'
                f'<th style="padding:10px 14px;text-align:left;font-size:13px;color:white;font-weight:700;">Atividade</th>'
                f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Supervisores</th>'
                f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Técnicos</th>'
                f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Propriedades Ativas (%)</th>'
                f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Propriedades Inativas (%)</th>'
                f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Total Propriedades</th>'
                f'</tr></thead>'
                f'<tbody>{linhas_html}</tbody>'
                f'</table>',
                unsafe_allow_html=True,
            )

        # 2. TABELA SECUNDÁRIA: Detalhe do Técnico
        if tipo_filtro == "Supervisor":
            st.divider()
            st.subheader(f"👥 Técnicos de {escolha}")

            df_tec_detalhe = (
                df_cons.groupby("tecnico")
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

            with st.container(key=f"container_tabela_tec_{escolha.replace(' ', '_')}"):
                linhas_tec = ""
                for _, r in df_tec_detalhe.iterrows():
                    t_prop = r["Total"] if r["Total"] > 0 else 1
                    p_atv = (r["Ativas"] / t_prop) * 100
                    p_ina = (r["Inativas"] / t_prop) * 100

                    p_visita = pd.to_datetime(r["Primeira_Visita"], errors='coerce').strftime("%d/%m/%Y") if pd.notnull(r["Primeira_Visita"]) else "—"
                    u_visita = pd.to_datetime(r["Ultima_Visita"], errors='coerce').strftime("%d/%m/%Y") if pd.notnull(r["Ultima_Visita"]) else "—"
                    meses = int(round(r["Tempo_Meses"])) if pd.notnull(r["Tempo_Meses"]) else 0

                    txt_atv_t = f"{int(r['Ativas']):,}".replace(",", ".")
                    txt_ina_t = f"{int(r['Inativas']):,}".replace(",", ".")
                    txt_tot_t = f"{int(r['Total']):,}".replace(",", ".")

                    linhas_tec += (
                        f'<tr>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;">{r["tecnico"]}</td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;">{r["Atividade"]}</td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{p_visita}</td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{u_visita}</td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;color:#1B4332;text-align:center;">{meses}</td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#1D9E75;font-weight:600;">{txt_atv_t} <span style="font-size:11px;color:#52B788;font-weight:normal;">({p_atv:.1f}%)</span></td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#E24B4A;font-weight:600;">{txt_ina_t} <span style="font-size:11px;color:#f3a5a5;font-weight:normal;">({p_ina:.1f}%)</span></td>'
                        f'<td style="padding:7px 14px;border-bottom:1px solid #e8f4ee;font-size:13px;text-align:center;color:#1B4332;font-weight:700;">{txt_tot_t}</td>'
                        f'</tr>'
                    )

                t_atv_tec = int(df_tec_detalhe["Ativas"].sum())
                t_ina_tec = int(df_tec_detalhe["Inativas"].sum())
                t_tot_tec = int(df_tec_detalhe["Total"].sum())
                div_tot = t_tot_tec if t_tot_tec > 0 else 1
                
                pct_atv_tec_g = (t_atv_tec / div_tot) * 100
                pct_ina_tec_g = (t_ina_tec / div_tot) * 100

                linhas_tec += (
                    f'<tr style="background:#1B4332;">'
                    f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;">TOTAL</td>'
                    f'<td style="padding:10px 14px;color:white;">—</td>'
                    f'<td style="padding:10px 14px;color:white;text-align:center;">—</td>'
                    f'<td style="padding:10px 14px;color:white;text-align:center;">—</td>'
                    f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;text-align:center;">{len(df_tec_detalhe)} técnicos</td>'
                    f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:#95d5b2;text-align:center;">{t_atv_tec:,}'.replace(",", ".") + f' ({pct_atv_tec_g:.1f}%)</td>'
                    f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:#f3a5a5;text-align:center;">{t_ina_tec:,}'.replace(",", ".") + f' ({pct_ina_tec_g:.1f}%)</td>'
                    f'<td style="padding:10px 14px;font-size:13px;font-weight:800;color:white;text-align:center;">{t_tot_tec:,}'.replace(",", ".") + f'</td>'
                    f'</tr>'
                )

                st.markdown(
                    f'<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
                    f'<thead><tr style="background:#2D6A4F;">'
                    f'<th style="padding:10px 14px;text-align:left;font-size:13px;color:white;font-weight:700;">Técnico</th>'
                    f'<th style="padding:10px 14px;text-align:left;font-size:13px;color:white;font-weight:700;">Atividade</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Primeira Visita</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Última Visita</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Tempo (meses)</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Propriedades Ativas (%)</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Propriedades Inativas (%)</th>'
                    f'<th style="padding:10px 14px;text-align:center;font-size:13px;color:white;font-weight:700;">Total Propriedades</th>'              
                    f'</tr></thead>'
                    f'<tbody>{linhas_tec}</tbody>'
                    f'</table>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Altere os filtros da barra lateral para exibir os dados combinados nesta visão.")
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
                "id", "data_troca", "tipo_troca", "projeto", "atividade",
                "regiao_faec", "pessoa_saindo", "pessoa_entrando",
                "motivo", "observacao", "registrado_por", "data_registro"
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

    # ── KPIs do histórico ──
    df_hist = carregar_historico()

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    col_h1.metric("🔄 Total de Trocas",    len(df_hist))
    col_h2.metric("👤 Trocas de Técnico",  len(df_hist[df_hist["tipo_troca"] == "Técnico"])  if not df_hist.empty else 0)
    col_h3.metric("🧑‍💼 Trocas de Supervisor", len(df_hist[df_hist["tipo_troca"] == "Supervisor"]) if not df_hist.empty else 0)
    col_h4.metric("📅 Último Registro",
        df_hist["data_troca"].max().strftime("%d/%m/%Y") if not df_hist.empty and pd.notna(df_hist["data_troca"].max()) else "—"
    )

    st.divider()

    col_form, col_tabela = st.columns([1, 2])

    # ── Formulário de registro ──
    with col_form:
        st.subheader("➕ Registrar Troca")

        supervisor_sel = st.selectbox(
            "🧑‍💼 Supervisor",
            sorted(df_f["supervisor_atual"].dropna().unique()),
            key="sup_form_sel",
        )

        tecnicos_sup = sorted(
            df_f[df_f["supervisor_atual"] == supervisor_sel]["tecnico"].dropna().unique()
        )
        st.caption(f"{len(tecnicos_sup)} técnicos vinculados")

        acao = st.radio(
            "Ação",
            ["➕ Vincular técnico", "➖ Desvincular técnico"],
            horizontal=True,
            key="acao_troca",
        )

        # Checkbox FORA do form para funcionar dinamicamente
        tecnico_novo = False
        supervisor_destino_ext = supervisor_sel
        if acao == "➕ Vincular técnico":
            supervisor_destino_ext = st.selectbox(
                "🧑‍💼 Vincular para qual supervisor",
                sorted(df_f["supervisor_atual"].dropna().unique()),
                key="sup_dest_ext",
            )
            tecnico_novo = st.checkbox("É um técnico novo (não está na lista)?", key="chk_novo")

        with st.form("form_troca", clear_on_submit=True):
            data_troca = st.date_input("📅 Data", value=datetime.now().date())

            if acao == "➕ Vincular técnico":
                if tecnico_novo:
                    novo_tecnico = st.text_input("👤 Nome do novo técnico")
                else:
                    novo_tecnico = st.selectbox("👤 Técnico a vincular", sorted(df_f["tecnico"].dropna().unique()))
                pessoa_saindo     = "—"
                supervisor_destino = supervisor_destino_ext
                tipo_registro     = "Vínculo"
                motivo_label      = "❓ Motivo da entrada"

            else:
                supervisor_destino = supervisor_sel
                pessoa_saindo = st.selectbox("👤 Técnico a desvincular", tecnicos_sup)
                novo_tecnico  = "—"
                tipo_registro = "Desvinculo"
                motivo_label  = "❓ Motivo do desvinculo"

            motivo = st.selectbox(motivo_label, [
                "Desligamento", "Transferência", "Licença", "Promoção",
                "Aprovado pelo Credenciamento", "Outro"
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
                        (df_f["supervisor_atual"] == supervisor_sel) &
                        (df_f["tecnico"] == pessoa_saindo)
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

    # ── Tabela de histórico ──
    with col_tabela:
        st.subheader("📋 Histórico de Trocas")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos", "Técnico", "Supervisor"], key="hist_tipo")
        with col_f2:
            filtro_proj = st.selectbox("Filtrar por projeto", ["Todos"] + sorted(df_f["projeto"].dropna().unique()), key="hist_proj")

        df_hist_f = df_hist.copy()
        if filtro_tipo != "Todos":
            df_hist_f = df_hist_f[df_hist_f["tipo_troca"] == filtro_tipo]
        if filtro_proj != "Todos":
            df_hist_f = df_hist_f[df_hist_f["projeto"] == filtro_proj]

        if df_hist_f.empty:
            st.info("Nenhuma troca registrada ainda.")
        else:
            df_hist_f["data_troca"] = pd.to_datetime(df_hist_f["data_troca"]).dt.strftime("%d/%m/%Y")

            # Extrair campos da observação
            def extrair_campo(obs, campo):
                if pd.isna(obs):
                    return "—"
                for part in str(obs).split("|"):
                    if f"{campo}:" in part:
                        return part.split(":", 1)[1].strip()
                return "—"

            df_hist_f["acao"]            = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Ação"))
            df_hist_f["sup_origem"]      = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Supervisor origem"))
            df_hist_f["sup_destino"]     = df_hist_f["observacao"].apply(lambda x: extrair_campo(x, "Supervisor destino"))

            linhas_hist = ""
            for _, r in df_hist_f.iterrows():
                cor_acao = "#1D9E75" if "Vínculo" in str(r["acao"]) else "#E24B4A"
                linhas_hist += (
                    f'<tr>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#333;white-space:nowrap;">{r["data_troca"]}</td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;"><span style="background:{cor_acao}22;color:{cor_acao};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{r["acao"]}</span></td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#555;">{r["sup_origem"]}</td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#1B4332;font-weight:600;">{r["sup_destino"]}</td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#E24B4A;">{r["pessoa_saindo"]}</td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#1D9E75;font-weight:600;">{r["pessoa_entrando"]}</td>'
                    f'<td style="padding:7px 12px;border-bottom:1px solid #e8f4ee;font-size:12px;color:#333;">{r["motivo"]}</td>'
                    f'</tr>'
                )

            st.markdown(
                f'<div style="overflow-x:auto;">'
                f'<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
                f'<thead><tr style="background:#2D6A4F;">'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Data</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Ação</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Sup. Origem</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Sup. Destino</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Saiu</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Entrou</th>'
                f'<th style="padding:9px 12px;text-align:left;font-size:12px;color:white;font-weight:700;">Motivo</th>'
                f'</tr></thead>'
                f'<tbody>{linhas_hist}</tbody>'
                f'</table></div>',
                unsafe_allow_html=True,
            )

            # Download Excel
            st.markdown("<br>", unsafe_allow_html=True)
            df_export_hist = df_hist_f[["data_troca", "acao", "sup_origem", "sup_destino", "pessoa_saindo", "pessoa_entrando", "motivo"]].copy()
            df_export_hist.columns = ["Data", "Ação", "Sup. Origem", "Sup. Destino", "Saiu", "Entrou", "Motivo"]
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df_export_hist.to_excel(writer, sheet_name="Histórico Trocas", index=False)
            st.download_button(
                label="📥 Baixar Excel",
                data=buf.getvalue(),
                file_name=f"historico_trocas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # Excluir registro
            st.divider()
            st.markdown("**🗑️ Excluir registro**")
            ids_disp = df_hist_f["id"].tolist()
            id_excluir = st.selectbox(
                "Selecione o ID para excluir",
                ids_disp,
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

        # Projetos com mais trocas (alerta de instabilidade)
        if not df_hist.empty:
            st.subheader("⚠️ Projetos com mais trocas")
            df_instavel = (
                df_hist.groupby("projeto")
                .size()
                .reset_index(name="Trocas")
                .sort_values("Trocas", ascending=False)
                .head(8)
            )
            fig_inst = px.bar(
                df_instavel, x="Trocas", y="projeto", orientation="h",
                color="Trocas",
                color_continuous_scale=["#74C69D", "#E24B4A"],
                text="Trocas",
            )
            fig_inst.update_traces(textposition="outside")
            fig_inst.update_layout(
                height=300,
                margin=dict(l=0, r=40, t=10, b=10),
                coloraxis_showscale=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, title=None),
                yaxis=dict(showgrid=False, title=None),
            )
            st.plotly_chart(fig_inst, use_container_width=True)