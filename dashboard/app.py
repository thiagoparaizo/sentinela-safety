#!/usr/bin/env python3
"""
DASHBOARD STREAMLIT - SISTEMA WEARABLE DE SEGURANÇA
Sprint 4 - Challenge Reply

Executar: streamlit run dashboard/app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import joblib
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Sistema Wearable - Segurança Industrial",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .big-metric {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .alert-critical {
        background-color: #ff4444;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .alert-warning {
        background-color: #ffaa00;
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .status-normal {
        background-color: #00C851;
        color: white;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def carregar_modelo():
    """Carrega modelo ML treinado"""
    try:
        model = joblib.load('ml/fall_detection_model.pkl')
        scaler = joblib.load('ml/scaler.pkl')
        return model, scaler
    except:
        return None, None

@st.cache_data(ttl=30)
def carregar_dados_db():
    """Carrega dados do banco SQLite"""
    conn = sqlite3.connect('sentinela.db')
    
    # Leituras recentes
    df_leituras = pd.read_sql_query("""
        SELECT * FROM leituras_sensores 
        ORDER BY timestamp_ms DESC 
        LIMIT 1000
    """, conn)
    
    # Eventos de queda
    df_quedas = pd.read_sql_query("""
        SELECT e.*, t.nome, t.setor
        FROM eventos_queda e
        JOIN trabalhadores t ON e.id_trabalhador = t.id_trabalhador
        ORDER BY e.timestamp_queda DESC
    """, conn)
    
    # Alertas
    df_alertas = pd.read_sql_query("""
        SELECT a.*, e.magnitude_impacto, t.nome
        FROM alertas a
        JOIN eventos_queda e ON a.id_evento = e.id_evento
        JOIN trabalhadores t ON e.id_trabalhador = t.id_trabalhador
        WHERE a.enviado = FALSE
        ORDER BY a.data_alerta DESC
    """, conn)
    
    conn.close()
    return df_leituras, df_quedas, df_alertas

def main():
    # Header
    st.title("🦺 Sistema Wearable de Segurança Industrial")
    st.markdown("**Challenge Reply - Fase 5 | Sistema Integrado de Monitoramento**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Threshold de alerta
        threshold_magnitude = st.slider(
            "Threshold de Magnitude (g)",
            min_value=1.5,
            max_value=3.0,
            value=1.8,
            step=0.1
        )
        
        st.divider()
        
        # Status do sistema
        st.subheader("📊 Status do Sistema")
        model, scaler = carregar_modelo()
        
        if model:
            st.success("✅ Modelo ML Ativo")
        else:
            st.error("❌ Modelo ML Indisponível")
        
        st.info("🔄 Atualização: Tempo Real")
        
        # Botão de refresh
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Carregar dados
    df_leituras, df_quedas, df_alertas = carregar_dados_db()
    
    # ====== ALERTAS CRÍTICOS ======
    if len(df_alertas) > 0:
        st.markdown("---")
        st.subheader("🚨 ALERTAS ATIVOS")
        
        for idx, alerta in df_alertas.iterrows():
            cor = "critical" if alerta['nivel_prioridade'] == 'critica' else "warning"
            st.markdown(f"""
            <div class="alert-{cor}">
                <h3>⚠️ {alerta['tipo_alerta'].upper()} - Prioridade: {alerta['nivel_prioridade'].upper()}</h3>
                <p><strong>Trabalhador:</strong> {alerta['nome']}</p>
                <p><strong>Magnitude do Impacto:</strong> {alerta['magnitude_impacto']:.2f}g</p>
                <p><strong>Mensagem:</strong> {alerta['mensagem']}</p>
                <p><strong>Data/Hora:</strong> {alerta['data_alerta']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Nenhum alerta ativo no momento")
    
    st.markdown("---")
    
    # ====== KPIs PRINCIPAIS ======
    st.subheader("📊 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Leituras",
            value=f"{len(df_leituras):,}",
            delta=f"+{len(df_leituras[df_leituras['timestamp_ms'] > df_leituras['timestamp_ms'].max() - 10000])}"
        )
    
    with col2:
        total_quedas = len(df_quedas)
        st.metric(
            label="Quedas Detectadas",
            value=total_quedas,
            delta=f"{total_quedas} eventos",
            delta_color="inverse"
        )
    
    with col3:
        mag_max = df_leituras['magnitude'].max()
        st.metric(
            label="Magnitude Máxima",
            value=f"{mag_max:.2f}g",
            delta="Pico registrado"
        )
    
    with col4:
        alertas_criticos = len(df_alertas[df_alertas['nivel_prioridade'] == 'critica'])
        st.metric(
            label="Alertas Críticos",
            value=alertas_criticos,
            delta="Pendentes",
            delta_color="inverse"
        )
    
    st.markdown("---")
    
    # ====== GRÁFICOS ======
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 Magnitude da Aceleração em Tempo Real")
        
        # Últimas 200 leituras
        df_recent = df_leituras.tail(200).copy()
        df_recent['tempo_s'] = (df_recent['timestamp_ms'] - df_recent['timestamp_ms'].min()) / 1000
        
        fig_timeline = go.Figure()
        
        # Linha de magnitude
        fig_timeline.add_trace(go.Scatter(
            x=df_recent['tempo_s'],
            y=df_recent['magnitude'],
            mode='lines',
            name='Magnitude',
            line=dict(color='blue', width=2)
        ))
        
        # Threshold
        fig_timeline.add_hline(
            y=threshold_magnitude, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Threshold: {threshold_magnitude}g"
        )
        
        # Quedas detectadas
        quedas_recent = df_recent[df_recent['queda_detectada'] == 1]
        if len(quedas_recent) > 0:
            fig_timeline.add_trace(go.Scatter(
                x=quedas_recent['tempo_s'],
                y=quedas_recent['magnitude'],
                mode='markers',
                name='Quedas',
                marker=dict(color='red', size=12, symbol='x')
            ))
        
        fig_timeline.update_layout(
            xaxis_title="Tempo (segundos)",
            yaxis_title="Magnitude (g)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    with col_right:
        st.subheader("🎯 Distribuição de Status")
        
        status_counts = df_leituras['status_movimento'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Quantidade']
        
        fig_status = px.pie(
            status_counts,
            values='Quantidade',
            names='Status',
            color='Status',
            color_discrete_map={
                'NORMAL': '#00C851',
                'MOVIMENTO': '#33b5e5',
                'QUEDA_LIVRE': '#ffbb33',
                'QUEDA_DETECTADA': '#ff4444'
            },
            height=400
        )
        
        st.plotly_chart(fig_status, use_container_width=True)
    
    st.markdown("---")
    
    # ====== EVENTOS DE QUEDA ======
    st.subheader("📋 Histórico de Eventos de Queda")
    
    if len(df_quedas) > 0:
        # Filtros
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            gravidades = ['Todas'] + df_quedas['gravidade'].unique().tolist()
            filtro_gravidade = st.selectbox("Filtrar por Gravidade", gravidades)
        
        with col_f2:
            filtro_status = st.selectbox(
                "Filtrar por Status", 
                ['Todos'] + df_quedas['status_atendimento'].unique().tolist()
            )
        
        # Aplicar filtros
        df_filtrado = df_quedas.copy()
        if filtro_gravidade != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['gravidade'] == filtro_gravidade]
        if filtro_status != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['status_atendimento'] == filtro_status]
        
        # Tabela
        st.dataframe(
            df_filtrado[[
                'id_evento', 'nome', 'setor', 'magnitude_impacto', 
                'gravidade', 'status_atendimento', 'tempo_resposta_segundos', 'data_evento'
            ]].rename(columns={
                'id_evento': 'ID',
                'nome': 'Trabalhador',
                'setor': 'Setor',
                'magnitude_impacto': 'Magnitude (g)',
                'gravidade': 'Gravidade',
                'status_atendimento': 'Status',
                'tempo_resposta_segundos': 'Tempo Resposta (s)',
                'data_evento': 'Data/Hora'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de quedas por gravidade
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            fig_grav = px.bar(
                df_quedas['gravidade'].value_counts().reset_index(),
                x='gravidade',
                y='count',
                title="Quedas por Gravidade",
                labels={'gravidade': 'Gravidade', 'count': 'Quantidade'},
                color='gravidade',
                color_discrete_map={
                    'leve': '#00C851',
                    'moderada': '#ffbb33',
                    'grave': '#ff4444'
                }
            )
            st.plotly_chart(fig_grav, use_container_width=True)
        
        with col_g2:
            fig_tempo = px.box(
                df_quedas,
                y='tempo_resposta_segundos',
                x='gravidade',
                title="Tempo de Resposta por Gravidade",
                labels={'tempo_resposta_segundos': 'Tempo (s)', 'gravidade': 'Gravidade'},
                color='gravidade',
                color_discrete_map={
                    'leve': '#00C851',
                    'moderada': '#ffbb33',
                    'grave': '#ff4444'
                }
            )
            st.plotly_chart(fig_tempo, use_container_width=True)
    else:
        st.info("Nenhum evento de queda registrado")
    
    st.markdown("---")
    
    # ====== SIMULADOR DE PREDIÇÃO ML ======
    st.subheader("🤖 Simulador de Predição ML")
    
    model, scaler = carregar_modelo()
    
    if model and scaler:
        col_ml1, col_ml2, col_ml3, col_ml4 = st.columns(4)
        
        with col_ml1:
            ax = st.number_input("Aceleração X (g)", -3.0, 3.0, 0.0, 0.1)
        with col_ml2:
            ay = st.number_input("Aceleração Y (g)", -3.0, 3.0, 0.0, 0.1)
        with col_ml3:
            az = st.number_input("Aceleração Z (g)", -3.0, 3.0, 1.0, 0.1)
        with col_ml4:
            st.write("")
            st.write("")
            if st.button("🔮 Prever", use_container_width=True):
                # Calcular magnitude
                magnitude = np.sqrt(ax**2 + ay**2 + az**2)
                
                # Criar features
                features = np.array([[
                    ax, ay, az, magnitude,
                    0, 0, magnitude, magnitude,
                    np.arctan2(ay, ax),
                    np.arctan2(az, ax)
                ]])
                
                features_scaled = scaler.transform(features)
                pred = model.predict(features_scaled)[0]
                proba = model.predict_proba(features_scaled)[0]
                
                # Resultado
                if pred == 1:
                    st.error(f"⚠️ QUEDA DETECTADA! (Probabilidade: {proba[1]:.1%})")
                else:
                    st.success(f"✅ Normal (Probabilidade queda: {proba[1]:.1%})")
                
                st.metric("Magnitude Calculada", f"{magnitude:.3f}g")
    else:
        st.warning("⚠️ Modelo ML não disponível. Execute o treinamento primeiro.")
    
    # Footer
    st.markdown("---")
    st.caption("🏭 Sistema Wearable de Segurança Industrial | Challenge Reply - Fase 5 | FIAP 2025")

if __name__ == "__main__":
    main()