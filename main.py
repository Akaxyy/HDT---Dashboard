import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from muck import MUCK_DATA
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard HDT", layout="wide", initial_sidebar_state="expanded")

# --- FUNÇÕES ---
def clean_currency(value):
    if isinstance(value, str):
        clean = value.replace('R$', '').strip().replace('.', '').replace(',', '.')
        try: return float(clean)
        except: return 0.0
    return value if isinstance(value, (int, float)) else 0.0

# --- CARGA DE DADOS ---
virtual_table = io.StringIO(MUCK_DATA)
df = pd.read_csv(virtual_table, sep=";")

# --- PROCESSAMENTO ---
df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
cols_money = ['Total R$', 'R$ HS1', 'R$ HS2', 'R$ HS3']
for c in cols_money: 
    if c in df.columns: df[c] = df[c].apply(clean_currency)
    else: df[c] = 0.0

# --- LÓGICA DA FLAG (CORRIGIDA) ---
# Se a coluna não existir, cria como RECAP
if 'Flag' not in df.columns:
    df['Flag'] = 'RECAP'
else:
    # Converte para string e trata nulos
    df['Flag'] = df['Flag'].fillna('').astype(str)
    # Aplica a regra: Se for FAFEM mantém, resto vira RECAP
    df['Flag'] = df['Flag'].apply(lambda x: 'FAFEM' if x.strip().upper() == 'FAFEM' else 'RECAP')

# --- FILTROS (SIDEBAR) ---
st.sidebar.markdown("## Filtros")

# 1. Data
min_d, max_d = df['Data'].min().date(), df['Data'].max().date()
date_range = st.sidebar.date_input("Período", [min_d, max_d])

# 2. Equipe
equipes = st.sidebar.multiselect("Equipe", df['Equipe'].unique(), default=df['Equipe'].unique())

# 3. Função
funcoes = st.sidebar.multiselect("Função", options=sorted(df['Função'].unique()))

# 4. Flag (Agora só tem FAFEM ou RECAP)
opcoes_flag = ["FAFEM", "RECAP"]
filtro_flag = st.sidebar.multiselect("Obra", options=opcoes_flag)

# --- APLICANDO FILTROS ---
df_f = df[
    (df['Data'].dt.date >= date_range[0]) & 
    (df['Data'].dt.date <= date_range[1]) & 
    (df['Equipe'].isin(equipes))
]

if funcoes: 
    df_f = df_f[df_f['Função'].isin(funcoes)]

if filtro_flag:
    df_f = df_f[df_f['Flag'].isin(filtro_flag)]

# --- LAYOUT DASHBOARD ---
c_title, c_logo = st.columns([5, 1])
c_title.markdown("### Monitoramento de Receita - HDT")

# 1. KPIs
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
totals = {c: df_f[c].sum() for c in cols_money}
def fmt(v): return f"R$ {v:,.0f}".replace(',', '.')

kpi1.metric("Faturamento Total", fmt(totals['Total R$']))
kpi2.metric("HS1", fmt(totals['R$ HS1']))
kpi3.metric("HS2", fmt(totals['R$ HS2']), delta="Extra" if totals['R$ HS2']>0 else None)
kpi4.metric("HS3", fmt(totals['R$ HS3']), delta="Alto Lucro" if totals['R$ HS3']>0 else None)

st.divider()

# 2. GRÁFICOS LINHA 1
col_g1, col_g2 = st.columns([2, 1])

with col_g1:
    daily = df_f.groupby('Data')[['R$ HS1', 'R$ HS2', 'R$ HS3']].sum().reset_index()
    daily_melt = daily.melt(id_vars='Data', value_vars=['R$ HS1', 'R$ HS2', 'R$ HS3'], var_name='Tipo', value_name='Valor')
    
    fig_line = px.line(
        daily_melt, x='Data', y='Valor', color='Tipo', markers=True,
        title="Evolução Diária (Comparativo HS)", template="plotly_white",
        color_discrete_map={'R$ HS1': '#1f77b4', 'R$ HS2': '#ff7f0e', 'R$ HS3': '#d62728'}
    )
    # FORMATANDO TOOLTIP (MOUSE OVER)
    fig_line.update_traces(
        hovertemplate='<b>Data:</b> %{x|%d/%m/%Y}<br><b>Tipo:</b> %{legendgroup}<br><b>Valor:</b> R$ %{y:,.2f}<extra></extra>'
    )
    fig_line.update_layout(height=320, xaxis_title=None, yaxis_title="Receita (R$)")
    st.plotly_chart(fig_line, use_container_width=True)

with col_g2:
    pie_data = pd.DataFrame({'Tipo': ['HS1', 'HS2', 'HS3'], 'Valor': [totals['R$ HS1'], totals['R$ HS2'], totals['R$ HS3']]})
    fig_pie = px.pie(
        pie_data, values='Valor', names='Tipo', hole=0.6, title="Receita",
        color='Tipo', color_discrete_map={'HS1': '#1f77b4', 'HS2': '#ff7f0e', 'HS3': '#d62728'}
    )
    # FORMATANDO TOOLTIP (MOUSE OVER)
    fig_pie.update_traces(
        textposition='inside', textinfo='percent',
        hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>(%{percent})'
    )
    fig_pie.update_layout(height=380, showlegend=False)
    fig_pie.add_annotation(text=f"Total<br>{fmt(totals['Total R$'])}", x=0.5, y=0.5, showarrow=False, font_size=12)
    st.plotly_chart(fig_pie, use_container_width=True)

# 3. GRÁFICOS LINHA 2
col_g3, col_g4 = st.columns(2)

with col_g3:
    df_team = df_f.groupby('Equipe')['Total R$'].sum().reset_index().sort_values('Total R$', ascending=False)
    fig_team = px.bar(
        df_team, x='Equipe', y='Total R$', 
        title="Receita por Equipe", text_auto='.2s',
        color='Total R$', color_continuous_scale='Blues'
    )
    # FORMATANDO TOOLTIP (MOUSE OVER)
    fig_team.update_traces(
        hovertemplate='<b>%{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>'
    )
    fig_team.update_layout(height=300, coloraxis_showscale=False)
    st.plotly_chart(fig_team, use_container_width=True)

with col_g4:
    df_role = df_f.groupby('Função')['Total R$'].sum().reset_index().sort_values('Total R$', ascending=True).tail(8)
    fig_role = px.bar(
        df_role, y='Função', x='Total R$', orientation='h',
        title="Top 8 Funções", text_auto='.2s',
        color='Total R$', color_continuous_scale='Blues'
    )
    # FORMATANDO TOOLTIP (MOUSE OVER)
    fig_role.update_traces(
        hovertemplate='<b>%{y}</b><br>Faturamento: R$ %{x:,.2f}<extra></extra>'
    )
    fig_role.update_layout(height=400, coloraxis_showscale=False, yaxis_title=None)
    st.plotly_chart(fig_role, use_container_width=True)