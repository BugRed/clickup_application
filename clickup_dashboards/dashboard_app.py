import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, datetime
import holidays
from utils.api_conection import fetch_tasks_from_api

# Importa as funções de cálculo refatoradas do módulo 'utils.calculate_dates'
from utils.calculate_dates import (
    calculate_incident_free_rate, 
    calculate_lead_time, 
    calculate_on_time_delivery_rate, 
    calculate_operational_capacity, 
    calculate_total_planned_hours,
    create_daily_log,
    calculate_daily_capacity_for_person_list
)

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Tarefas ClickUp",
    layout="wide"
)

# --- CSS Personalizado para os Cards e Gráficos ---
st.markdown("""
<style>
    /* Container unificado para todos os KPIs */
    .kpi-container {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    
    /* Estilo base para todos os cards de KPIs (incluindo gauge) */
    .kpi-card, .gauge-card {
        background: linear-gradient(to bottom, rgba(127, 255, 0, 0.5), rgba(0, 0, 0, 0.7));
        border-radius: 10px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        flex: 1;
        width: 100%;
    }
    
    .kpi-card h3 {
        color: white;
        font-size: 16px;
        margin: 0;
        padding-bottom: 5px;
    }
    
    .kpi-card h1 {
        color: white;
        font-size: 32px;
        font-weight: bold;
        margin: 0;
    }
    
    /* Estilo para o container do gauge chart */
    .gauge-container {
        background: linear-gradient(to bottom, rgba(127, 255, 0, 0.5), rgba(0, 0, 0, 0.7));
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        height: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    
    /* Ajuste do plotly chart dentro do container */
    .gauge-container > div {
        width: 100% !important;
        height: 100% !important;
    }
    
    /* Estilo para os cartões de gráfico */
    .chart-card-container {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 20px;
        height: auto;
        display: flex;
        flex-direction: column;
        background-color: #1e1e1e;
    }
    
    .chart-card-container h5 {
        color: white;
        margin-top: 0;
        margin-bottom: 15px;
    }

    /* Oculta os botões de menu do Streamlit nos gráficos */
    .modebar {
        display: none;
    }
    
    /* Centraliza os títulos dos cards de gráfico */
    .chart-card-container .st-emotion-cache-1r6ilaq, .st-emotion-cache-1om0r6w {
        text-align: center;
    }

    /* Estilo para o card dentro do gráfico de lead time */
    .simple-kpi-card {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px 15px;
        text-align: center;
        margin-bottom: 15px;
        border: 1px solid #d3d3d3;
    }
    
    .simple-kpi-card h4 {
        margin: 0;
        font-size: 14px;
        color: #555555;
    }
    
    .simple-kpi-card h2 {
        margin: 5px 0 0;
        font-size: 24px;
        color: #333333;
        font-weight: bold;
    }

    /* Estilo para o mini card com cor verde */
    .mini-kpi-card {
        background: linear-gradient(to bottom, rgba(127, 255, 0, 0.5), rgba(0, 0, 0, 0.7));
        border-radius: 8px;
        padding: 10px 15px;
        color: white;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        display: inline-block;
        margin-bottom: 15px;
    }
    
    .mini-kpi-card h4 {
        color: white;
        margin: 0;
        font-size: 14px;
        font-weight: normal;
    }
    
    .mini-kpi-card h2 {
        color: white;
        margin: 5px 0 0;
        font-size: 24px;
        font-weight: bold;
    }
    
    /* Tooltip para os gráficos */
    .chart-header {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        margin-bottom: 15px;
    }
    
    .help-tooltip {
        position: relative;
        display: inline-block;
    }
    
    .help-tooltip .tooltiptext {
        visibility: hidden;
        width: 300px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -150px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .help-tooltip .tooltiptext::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #555 transparent transparent transparent;
    }
    
    .help-tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

def create_kpi_card(title, value, help_text):
    """Cria um card de KPI com HTML e CSS."""
    html_string = f"""
    <div class="kpi-card">
        <h3>{title}</h3>
        <h1>{value}</h1>
        <div style="
            position: absolute;
            top: 10px;
            right: 10px;
            cursor: pointer;
            color: white;
            font-size: 18px;
            opacity: 0.8;
        " title="{help_text}">
            ⓘ
        </div>
    </div>
    """
    st.markdown(html_string, unsafe_allow_html=True)

def create_gauge_chart(value, title, help_text):
    """
    Cria um gráfico de velocímetro para a capacidade, com zonas de cor.
    0% - 69%: Amarelo
    70% - 100%: Verde
    < 0% ou > 100%: Vermelho
    """
    # Garante que o valor esteja entre 0 e 150 para a escala do velocímetro
    display_value = max(0, min(value, 150))
    
    # Define a cor da agulha baseado no valor
    if value < 70 or value > 100:
        gauge_color = "#E50000"  # Vermelho
    elif 70 <= value <= 100:
        gauge_color = "#00B050"  # Verde
    else:
        gauge_color = "#FFC000"  # Amarelo

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=display_value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 14, 'color': 'white'}},
        number={'suffix': "%", 'font': {'size': 32, 'color': 'white'}},
        gauge={
            'axis': {'range': [None, 150], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': gauge_color, 'thickness': 0.8},
            'bgcolor': "rgba(255, 255, 255, 0.1)",
            'borderwidth': 2,
            'bordercolor': "rgba(255, 255, 255, 0.3)",
            'steps': [
                {'range': [0, 70], 'color': "rgba(255, 192, 0, 0.3)"},  # Amarelo transparente
                {'range': [70, 100], 'color': "rgba(0, 176, 80, 0.3)"},  # Verde transparente
                {'range': [100, 150], 'color': "rgba(229, 0, 0, 0.3)"}  # Vermelho transparente
            ],
            'threshold': {
                'line': {'color': "white", 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))

    # Configuração do layout com fundo transparente
    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, b=10, t=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )

    return fig

# --- Carregar e processar os dados automaticamente ao iniciar a aplicação ---
df_full = fetch_tasks_from_api()

# --- Layout da Aplicação ---
if not df_full.empty:
    # Cria o DataFrame base com log diário
    df_daily_log = create_daily_log(df_full)
    
    # --- Seção de Filtros ---
    st.subheader("🔍 Segmentação de Dados")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    # --- Filtro de Lista de Origem ---
    with filter_col1:
        # Tabela base para filtros, já filtrando por parent_id
        df_unique_base = df_full[df_full['parent_id'].isnull()].drop_duplicates(subset=['clickup_id'], keep='first')
        unique_lists_filter = ["Todas"] + sorted(df_unique_base['lista_origem'].unique().tolist())
        selected_list = st.selectbox("📁 Filtrar por Lista de Origem:", unique_lists_filter)

    # --- Filtro de Responsável ---
    with filter_col2:
        if selected_list != "Todas":
            df_temp = df_unique_base[df_unique_base['lista_origem'] == selected_list]
        else:
            df_temp = df_unique_base
        
        # Filtra 'None' para a exibição no selectbox
        df_temp_filtered_responsible = df_temp[df_temp['responsavel'].notna()]
        unique_responsibles = ["Todos"] + sorted(df_temp_filtered_responsible['responsavel'].unique().tolist())
        selected_responsible = st.selectbox("👤 Filtrar por Responsável:", unique_responsibles)

    # --- Seletor de modo de filtro de data ---
    with filter_col3:
        date_filter_mode = st.radio(
            "📅 Modo de Visualização",
            ["Todos os dias", "Filtrar por data"],
            index=0
        )
        
        if date_filter_mode == "Filtrar por data":
            selected_date = st.date_input(
                "Selecione a Data:",
                datetime.today().date()
            )

    # --- Aplicação dos Filtros ---
    if date_filter_mode == "Todos os dias":
        df_unique_filtered = df_unique_base.copy()
        
        if selected_list != "Todas":
            df_unique_filtered = df_unique_filtered[df_unique_filtered['lista_origem'] == selected_list]
        
        if selected_responsible != "Todos":
            df_unique_filtered = df_unique_filtered[df_unique_filtered['responsavel'] == selected_responsible]
        
        # DataFrame único de tasks principais para KPIs e gráficos
        df_for_kpis_and_charts = df_unique_filtered
        
        # Para os gráficos de capacidade, usa todos os dados do log diário com filtros
        df_daily_for_capacity = df_daily_log.copy()
        if selected_list != "Todas":
            df_daily_for_capacity = df_daily_for_capacity[df_daily_for_capacity['lista_origem'] == selected_list]
        if selected_responsible != "Todos":
            df_daily_for_capacity = df_daily_for_capacity[df_daily_for_capacity['responsavel'] == selected_responsible]
        
        # Data para cálculo da semana (usa hoje)
        reference_date = datetime.today().date()
        
    else:
        br_holidays = holidays.country_holidays('BR', years=selected_date.year)
        
        if selected_date.weekday() >= 5:
            st.warning("⚠️ Selecione apenas dias úteis para visualizar as tarefas.")
            df_for_kpis_and_charts = pd.DataFrame()
            df_daily_filtered_for_charts = pd.DataFrame()
            df_daily_for_capacity = pd.DataFrame()
            reference_date = selected_date
        elif selected_date in br_holidays:
            st.warning(f"⚠️ O dia {selected_date.strftime('%d/%m/%Y')} é um feriado nacional: {br_holidays.get(selected_date)}.")
            df_for_kpis_and_charts = pd.DataFrame()
            df_daily_filtered_for_charts = pd.DataFrame()
            df_daily_for_capacity = pd.DataFrame()
            reference_date = selected_date
        else:
            # Filtra a tabela de log diário
            df_daily_filtered_for_charts = df_daily_log[df_daily_log['registro_data'] == selected_date].copy()
            
            if selected_list != "Todas":
                df_daily_filtered_for_charts = df_daily_filtered_for_charts[df_daily_filtered_for_charts['lista_origem'] == selected_list]
            
            if selected_responsible != "Todos":
                df_daily_filtered_for_charts = df_daily_filtered_for_charts[df_daily_filtered_for_charts['responsavel'] == selected_responsible]
            
            # DataFrame único para KPIs (drop_duplicates para contar por tarefa principal)
            df_for_kpis_and_charts = df_daily_filtered_for_charts.drop_duplicates(subset=['clickup_id'], keep='first')
            
            # Para os gráficos de capacidade, usa a semana da data selecionada
            df_daily_for_capacity = df_daily_log.copy()
            if selected_list != "Todas":
                df_daily_for_capacity = df_daily_for_capacity[df_daily_for_capacity['lista_origem'] == selected_list]
            if selected_responsible != "Todos":
                df_daily_for_capacity = df_daily_for_capacity[df_daily_for_capacity['responsavel'] == selected_responsible]
            
            reference_date = selected_date
    
    st.markdown("---")

    # --- Seção de KPIs ---
    if not df_for_kpis_and_charts.empty:
        # Criação dos 4 KPIs em colunas com tamanhos iguais
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        with kpi_col1:
            on_time_rate, on_time_count, total_completed = calculate_on_time_delivery_rate(df_for_kpis_and_charts)
            create_kpi_card(
                "Entrega no Prazo",
                f"{on_time_rate:.1f}%",
                help_text=f"Taxa de tarefas concluídas no prazo. {on_time_count} de {total_completed} tarefas concluídas foram entregues no prazo."
            )

        with kpi_col2:
            incident_free_rate, clean_projects, total_projects = calculate_incident_free_rate(df_for_kpis_and_charts)
            create_kpi_card(
                "Qualidade",
                f"{incident_free_rate:.1f}%",
                help_text=f"Taxa de projetos sem incidentes. {clean_projects} de {total_projects} projetos não têm incidentes."
            )

        with kpi_col3:
            if date_filter_mode == "Filtrar por data":
                total_hours = df_daily_filtered_for_charts['registro_horas'].sum() if 'registro_horas' in df_daily_filtered_for_charts.columns else 0
                help_text = f"Total de horas planejadas para {selected_date.strftime('%d/%m/%Y')} (filtros aplicados)."
            else:
                total_hours = calculate_total_planned_hours(df_for_kpis_and_charts)
                help_text = "Soma total de horas estimadas para tarefas principais (sem parent_id) nos filtros selecionados."
            
            create_kpi_card(
                "Horas Previstas",
                f"{total_hours:.0f}h",
                help_text=help_text
            )

        with kpi_col4:
            with st.container():               
                if date_filter_mode == "Filtrar por data":
                    capacity_rate, daily_hours, daily_capacity = calculate_daily_capacity_for_person_list(
                        df_daily_filtered_for_charts, selected_responsible, selected_list
                    )
                    help_text = f"Capacidade operacional para {selected_date.strftime('%d/%m/%Y')}: {daily_hours:.0f}h de {daily_capacity:.0f}h disponíveis (filtros aplicados)."
                else:
                    capacity_rate, planned_hours, max_capacity = calculate_operational_capacity(df_for_kpis_and_charts)
                    help_text = f"Capacidade operacional semanal: {planned_hours:.0f}h planejadas de {max_capacity:.0f}h disponíveis (filtros aplicados)."
                
                gauge_fig = create_gauge_chart(capacity_rate, "Capacidade", help_text)
                
                st.plotly_chart(gauge_fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("---")
        
        # --- Gráfico de Tarefas por Responsável (Linha Completa) ---
        chart_col_full = st.columns(1)[0]
        with chart_col_full:
            with st.container(border=True):
                st.markdown("##### 👩‍💻 Distribuição de Tarefas por Responsável")
                if date_filter_mode == "Todos os dias":
                    df_to_use = df_for_kpis_and_charts
                else:
                    df_to_use = df_daily_filtered_for_charts

                if not df_to_use.empty:
                    # Filtra linhas onde 'responsavel' não é 'None'
                    df_filtered_for_chart = df_to_use[df_to_use['responsavel'].notna()]
                    
                    if date_filter_mode == "Filtrar por data":
                        task_counts = df_filtered_for_chart.groupby('responsavel')['registro_horas'].sum().reset_index()
                        task_counts.columns = ['Responsavel', 'Horas']
                        y_label = 'Horas Planejadas'
                        title = f"Horas por responsável em {selected_date.strftime('%d/%m/%Y')}"
                    else:
                        task_counts = df_filtered_for_chart['responsavel'].value_counts().reset_index()
                        task_counts.columns = ['Responsavel', 'Contagem']
                        y_label = 'Número de Tarefas'
                        title = "Contagem de tarefas por responsável"
                    
                    fig = px.bar(
                        task_counts,
                        x='Responsavel',
                        y=task_counts.columns[1],
                        color='Responsavel',
                        labels={'Responsavel': 'Responsável', task_counts.columns[1]: y_label},
                        title=title
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum dado para este filtro.")
        
        st.markdown("---")

        # --- Gráficos em Layout 2x2 ---
        chart_row1_col1, chart_row1_col2 = st.columns(2)

        # Gráfico 1: % de Tarefas com Prazo
        with chart_row1_col1:
            with st.container(border=True):
                st.markdown("##### 📅 % de Tarefas com Prazo Definido")
                if not df_for_kpis_and_charts.empty:
                    tasks_with_deadline = df_for_kpis_and_charts['prazo'].notnull().sum()
                    tasks_without_deadline = len(df_for_kpis_and_charts) - tasks_with_deadline
                    
                    data = pd.DataFrame({
                        'Categoria': ['Com Prazo', 'Sem Prazo'],
                        'Contagem': [tasks_with_deadline, tasks_without_deadline]
                    })
                    
                    fig = px.pie(
                        data,
                        values='Contagem',
                        names='Categoria',
                        title="Proporção de tarefas com prazo definido",
                        color_discrete_sequence=['#80FF00', '#FF5733']
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum dado para este filtro.")

        # Gráfico 2: Distribuição de Prioridade
        with chart_row1_col2:
            with st.container(border=True):
                st.markdown("##### ⚠️ Distribuição de Prioridade de Tarefas")
                if not df_for_kpis_and_charts.empty:
                    priority_counts = df_for_kpis_and_charts['prioridade'].value_counts().reset_index()
                    priority_counts.columns = ['Prioridade', 'Contagem']

                    color_map = {
                        'urgent': '#E37373',
                        'high': '#E3A773',
                        'normal': '#73E373',
                        'low': '#73A7E3'
                    }

                    fig = px.pie(
                        priority_counts,
                        values='Contagem',
                        names='Prioridade',
                        title="Proporção de prioridades na seleção atual",
                        color='Prioridade',
                        color_discrete_map=color_map
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum dado para este filtro.")
    
    else:
        st.info("Nenhum dado para este filtro. Tente selecionar outros critérios ou verifique se a API está funcionando.")
else:
    st.info("Carregando dados ou a API está offline. Por favor, aguarde ou verifique a conexão com a API.")