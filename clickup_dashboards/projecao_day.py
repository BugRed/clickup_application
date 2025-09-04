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
    Cria um gráfico de velocímetro para a capacidade, com zonas de cor e estilo unificado.
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

def calculate_weekly_capacity_data(df_daily_log, selected_date=None):
    """
    Calcula os dados de capacidade semanal para os gráficos.
    
    Args:
        df_daily_log: DataFrame com log diário das tarefas
        selected_date: Data selecionada (se None, usa a data atual)
    
    Returns:
        DataFrame com dados agregados por dia e responsável
    """
    if selected_date is None:
        selected_date = datetime.today().date()
    
    # Define o início e fim da semana (segunda a sexta)
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)  # Sexta-feira
    
    # Filtra dados da semana
    df_week = df_daily_log[
        (df_daily_log['registro_data'] >= start_of_week) &
        (df_daily_log['registro_data'] <= end_of_week)
    ].copy()
    
    # Agrupa por data e responsável, somando as horas
    df_capacity = df_week.groupby(['registro_data', 'responsavel'])['registro_horas'].sum().reset_index()
    df_capacity.columns = ['data', 'responsavel', 'horas_planejadas']
    
    # Adiciona o dia da semana para melhor visualização
    df_capacity['dia_semana'] = pd.to_datetime(df_capacity['data']).dt.strftime('%a %d/%m')
    
    return df_capacity, start_of_week, end_of_week

def create_total_capacity_chart(df_capacity, start_of_week, end_of_week):
    """
    Cria o gráfico de capacidade total da semana.
    
    Args:
        df_capacity: DataFrame com dados de capacidade
        start_of_week: Início da semana
        end_of_week: Fim da semana
    
    Returns:
        Figura Plotly do gráfico de barras
    """
    # Calcula o número de dias úteis na semana (excluindo feriados e fins de semana)
    br_holidays = holidays.country_holidays('BR', years=start_of_week.year)
    dias_uteis = 0
    current_date = start_of_week
    
    while current_date <= end_of_week:
        if current_date.weekday() < 5 and current_date not in br_holidays:
            dias_uteis += 1
        current_date += timedelta(days=1)
    
    # Número único de responsáveis
    num_responsaveis = df_capacity['responsavel'].nunique()
    
    # Capacidade total da semana (8h * dias úteis * número de responsáveis)
    capacidade_total_semana = 8 * dias_uteis * num_responsaveis
    
    # Cria o gráfico de barras agrupadas
    fig = px.bar(
        df_capacity,
        x='dia_semana',
        y='horas_planejadas',
        color='responsavel',
        labels={
            'horas_planejadas': 'Horas Planejadas',
            'dia_semana': 'Dia da Semana',
            'responsavel': 'Responsável'
        },
        color_discrete_sequence=px.colors.qualitative.Set3,
        barmode='group'
    )
    
    # Adiciona linha horizontal de capacidade máxima
    fig.add_hline(
        y=capacidade_total_semana / dias_uteis,  # Média diária da capacidade total
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"Capacidade Média Diária: {capacidade_total_semana/dias_uteis:.0f}h",
        annotation_position="top right"
    )
    
    # Configurações do layout com fundo escuro
    fig.update_layout(
        height=400,
        showlegend=True,
        hovermode='x unified',
        xaxis_title="Dia da Semana",
        yaxis_title="Horas",
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(size=14, color='white'),
        xaxis=dict(color='white', gridcolor='#444444'),
        yaxis=dict(color='white', gridcolor='#444444'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",  # Mudado para left
            x=0,  # Mudado para 0
            font=dict(color='white', size=12)
        ),
    )
    
    # Adiciona anotação com informações da capacidade
    fig.add_annotation(
        text=f"Capacidade Total Semanal: {capacidade_total_semana}h | Dias Úteis: {dias_uteis} | Responsáveis: {num_responsaveis}",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.15,
        showarrow=False,
        font=dict(size=12, color="white")
    )
    
    return fig

def create_individual_capacity_chart(df_capacity):
    """
    Cria o gráfico de capacidade individual diária.
    
    Args:
        df_capacity: DataFrame com dados de capacidade
    
    Returns:
        Figura Plotly do gráfico de barras
    """
    # Cria o gráfico de barras agrupadas
    fig = px.bar(
        df_capacity,
        x='dia_semana',
        y='horas_planejadas',
        color='responsavel',
        labels={
            'horas_planejadas': 'Horas Planejadas',
            'dia_semana': 'Dia da Semana',
            'responsavel': 'Responsável'
        },
        color_discrete_sequence=px.colors.qualitative.Set3,
        barmode='group'
    )
    
    # Adiciona linha horizontal de 8 horas (capacidade individual diária)
    fig.add_hline(
        y=8,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text="Capacidade Individual: 8h/dia",
        annotation_position="top right"
    )
    
    # Configurações do layout com fundo escuro
    fig.update_layout(
        height=400,
        showlegend=True,
        hovermode='x unified',
        xaxis_title="Dia da Semana",
        yaxis_title="Horas",
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(size=14, color='white'),
        xaxis=dict(color='white', gridcolor='#444444'),
        yaxis=dict(color='white', gridcolor='#444444'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",  # Mudado para left
            x=0,  # Mudado para 0
            font=dict(color='white', size=12)
        ),
    )
    
    # Adiciona anotação explicativa
    fig.add_annotation(
        text="🟢 Dentro do limite (≤8h) | 🟡 Próximo ao limite (6-8h) | 🔴 Acima do limite (>8h)",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.15,
        showarrow=False,
        font=dict(size=12, color="white")
    )
    
    return fig

def create_chart_card_with_help(title, help_text, chart_figure):
    """
    Cria um container de gráfico com um título e um tooltip de ajuda.
    """
    st.markdown(f"""
    <div class="chart-header">
        <h5 style="color:white; margin:0;">{title}</h5>
        <div class="help-tooltip">
            ⓘ
            <span class="tooltiptext">{help_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(chart_figure, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# --- Carregar e processar os dados automaticamente ao iniciar a aplicação ---
df_full = fetch_tasks_from_api()

# --- Layout da Aplicação ---
if not df_full.empty:
    # Cria o DataFrame base com log diário
    df_daily_log = create_daily_log(df_full)
    
    # df_daily_log.to_csv('df_debug.csv', sep=',')
    
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
        
        # --- Seção de Gráficos de Capacidade ---
        st.subheader("📊 Análise de Capacidade Semanal")
        
        # Prepara os dados de capacidade se houver dados disponíveis
        if not df_daily_for_capacity.empty and 'df_daily_for_capacity' in locals():
            # Calcula os dados de capacidade para a semana
            df_capacity_data, start_week, end_week = calculate_weekly_capacity_data(
                df_daily_for_capacity, 
                reference_date
            )
            
            if not df_capacity_data.empty:
                # Gráfico de Capacidade Individual usando st.container
                fig_individual = create_individual_capacity_chart(df_capacity_data)
                individual_help_text = "Este gráfico mostra a distribuição de horas planejadas por dia para cada responsável. A linha tracejada vermelha representa a capacidade individual de 8 horas por dia."
                create_chart_card_with_help("📋 Capacidade Individual Diária", individual_help_text, fig_individual)

                # Gráfico de Capacidade Total usando st.container
                fig_total = create_total_capacity_chart(df_capacity_data, start_week, end_week)
                total_help_text = "Este gráfico mostra a soma total de horas planejadas por dia para a equipe. A linha tracejada vermelha representa a capacidade média diária total, calculada com base no número de dias úteis e de responsáveis."
                create_chart_card_with_help(f"📊 Capacidade Total da Semana ({start_week.strftime('%d/%m')} - {end_week.strftime('%d/%m')})", total_help_text, fig_total)

                # --- Tabela Resumo de Capacidade ---
                st.subheader("📋 Resumo Detalhado de Capacidade")
                
                # Cria tabela pivot para melhor visualização
                df_pivot = df_capacity_data.pivot_table(
                    index='responsavel',
                    columns='dia_semana',
                    values='horas_planejadas',
                    fill_value=0,
                    aggfunc='sum'
                )
                
                # Adiciona coluna de total por pessoa
                df_pivot['Total Semana'] = df_pivot.sum(axis=1)
                
                # Adiciona linha de total por dia
                df_pivot.loc['Total Diário'] = df_pivot.sum()
                
                # Função para aplicar cores à tabela
                def highlight_overload(val):
                    """Aplica cor vermelha para valores > 8h, exceto na linha/coluna de totais"""
                    if isinstance(val, (int, float)):
                        # Não aplica cor na célula do total geral (última linha, última coluna)
                        if val > 8 and val != df_pivot.loc['Total Diário', 'Total Semana']:
                            return 'background-color: #ffcccc; color: #d63384; font-weight: bold;'
                    return ''
                
                # Formata os valores como horas
                df_formatted = df_pivot.copy()
                for col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.1f}h" if isinstance(x, (int, float)) else x)
                
                # Aplica o estilo e exibe a tabela
                styled_df = df_formatted.style.applymap(highlight_overload)
                st.dataframe(styled_df, use_container_width=True)
                
                # Adiciona legenda da tabela
                st.caption("💡 **Legenda**: Valores em vermelho indicam sobrecarga (>8h/dia). A linha 'Total Diário' mostra a soma de horas de todos os responsáveis por dia.")
                
            else:
                st.info("📊 Não há dados de capacidade disponíveis para a semana selecionada com os filtros aplicados.")
        else:
            st.info("📊 Selecione filtros válidos para visualizar os gráficos de capacidade.")
            
else:
    st.error("❌ Não foi possível carregar os dados. Verifique a conexão com a API.")