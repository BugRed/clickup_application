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

def get_working_days_in_range(start_date, end_date):
    """
    Retorna uma lista de dias úteis (segunda a sexta, excluindo feriados) no período especificado.
    
    Args:
        start_date: Data de início
        end_date: Data de fim
    
    Returns:
        List: Lista de datas dos dias úteis
    """
    # Obtém feriados brasileiros para os anos do período
    years = list(range(start_date.year, end_date.year + 1))
    br_holidays = holidays.country_holidays('BR', years=years)
    
    working_days = []
    current_date = start_date
    
    while current_date <= end_date:
        # Verifica se é dia útil (segunda a sexta) e não é feriado
        if current_date.weekday() < 5 and current_date not in br_holidays:
            working_days.append(current_date)
        current_date += timedelta(days=1)
    
    return working_days

def calculate_period_capacity_data(df_daily_log, start_date, end_date, total_company_responsaveis):
    """
    Calcula os dados de capacidade para o período especificado.
    
    Args:
        df_daily_log: DataFrame com log diário das tarefas
        start_date: Data de início do período
        end_date: Data de fim do período
        total_company_responsaveis: Número total de responsáveis da empresa
    
    Returns:
        DataFrame com dados agregados por dia
    """
    # Filtra dados do período
    df_period = df_daily_log[
        (df_daily_log['registro_data'] >= start_date) &
        (df_daily_log['registro_data'] <= end_date)
    ].copy()
    
    # Obtém todos os dias úteis do período
    working_days = get_working_days_in_range(start_date, end_date)
    
    # Cria DataFrame base com todos os dias úteis
    df_base = pd.DataFrame({
        'data': working_days,
        'dia_semana': [d.strftime('%a %d/%m') for d in working_days],
        'capacidade_maxima_empresa': [total_company_responsaveis * 8] * len(working_days)
    })
    
    # Agrupa dados do período por data, somando todas as horas planejadas
    if not df_period.empty:
        df_aggregated = df_period.groupby(['registro_data'])['registro_horas'].sum().reset_index()
        df_aggregated.columns = ['data', 'horas_planejadas_total']
        
        # Faz merge com o DataFrame base
        df_capacity = pd.merge(df_base, df_aggregated, on='data', how='left')
    else:
        df_capacity = df_base.copy()
        df_capacity['horas_planejadas_total'] = 0
    
    # Preenche valores nulos com 0
    df_capacity['horas_planejadas_total'] = df_capacity['horas_planejadas_total'].fillna(0)
    
    return df_capacity

def create_period_capacity_chart(df_capacity, start_date, end_date, total_company_responsaveis):
    """
    Cria o gráfico de capacidade para o período especificado.
    
    Args:
        df_capacity: DataFrame com dados de capacidade
        start_date: Data de início
        end_date: Data de fim
        total_company_responsaveis: Número total de responsáveis da empresa
    
    Returns:
        Figura Plotly do gráfico de barras
    """
    # Capacidade máxima diária da empresa
    capacidade_maxima_diaria = total_company_responsaveis * 8
    
    # Cria o gráfico de barras
    fig = px.bar(
        df_capacity,
        x='dia_semana',
        y='horas_planejadas_total',
        labels={
            'horas_planejadas_total': 'Horas Planejadas Total da Empresa',
            'dia_semana': 'Dia'
        },
        color_discrete_sequence=['#7FFF00'],  # Verde lima
        title=f"Capacidade da Empresa - Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    )
    
    # Adiciona linha horizontal de capacidade máxima da empresa
    fig.add_hline(
        y=capacidade_maxima_diaria,
        line_dash="dash",
        line_color="red",
        line_width=3,
        annotation_text=f"Capacidade Máxima: {capacidade_maxima_diaria}h/dia",
        annotation_position="top right"
    )
    
    # Configurações do layout
    fig.update_layout(
        height=500,
        showlegend=False,
        hovermode='x unified',
        xaxis_title="Dias do Período",
        yaxis_title="Horas",
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(size=12, color='white'),
        xaxis=dict(
            color='white', 
            gridcolor='#444444',
            tickangle=45  # Rotaciona os labels do eixo x para melhor visualização
        ),
        yaxis=dict(color='white', gridcolor='#444444'),
        title=dict(font=dict(color='white', size=16), x=0.5)
    )
    
    # Adiciona informações do período
    total_days = len(df_capacity)
    total_capacity_period = capacidade_maxima_diaria * total_days
    total_planned_period = df_capacity['horas_planejadas_total'].sum()
    utilization_rate = (total_planned_period / total_capacity_period * 100) if total_capacity_period > 0 else 0
    
    fig.add_annotation(
        text=f"Período: {total_days} dias úteis | Capacidade Total: {total_capacity_period}h | Planejado: {total_planned_period:.0f}h | Utilização: {utilization_rate:.1f}%",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.25,
        showarrow=False,
        font=dict(size=11, color="white")
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

# --- Carregar e processar os dados automaticamente ao iniciar a aplicação ---
df_full = fetch_tasks_from_api()

# --- Layout da Aplicação ---
if not df_full.empty:
    # IMPORTANTE: Calcula o número total de responsáveis únicos da empresa ANTES dos filtros
    total_company_responsaveis = df_full['responsavel'].nunique()
    
    # Cria o DataFrame base com log diário
    df_daily_log = create_daily_log(df_full)
        
    # --- Seção de Gráficos de Capacidade com Filtro de Período ---
    st.subheader("📊 Análise de Capacidade por Período")
    
    # Filtro de período flexível
    period_col1, period_col2 = st.columns(2)
    
    with period_col1:
        # Define período padrão (início do mês atual)
        today = datetime.today().date()
        start_of_month = today.replace(day=1)
        
        period_start = st.date_input(
            "📅 Data de Início:",
            value=start_of_month,
            help="Selecione a data de início do período para análise"
        )
    
    with period_col2:
        # Data de fim padrão (fim do mês atual)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        period_end = st.date_input(
            "📅 Data de Fim:",
            value=min(end_of_month, today + timedelta(days=30)),  # Máximo 30 dias à frente
            help="Selecione a data de fim do período para análise"
        )
    
    # Validação do período
    if period_start > period_end:
        st.error("❌ A data de início deve ser anterior à data de fim!")
    elif (period_end - period_start).days > 90:
        st.warning("⚠️ Período muito longo (>90 dias). Para melhor visualização, recomenda-se períodos menores.")
    else:
        # Prepara os dados de capacidade para o período
        if not df_daily_log.empty:
            df_period_capacity = calculate_period_capacity_data(
                df_daily_log, 
                period_start, 
                period_end,
                total_company_responsaveis
            )
            
            if not df_period_capacity.empty:
                # Calcula KPIs baseados no período selecionado
                total_planned_period = df_period_capacity['horas_planejadas_total'].sum()
                working_days = len(df_period_capacity)
                total_capacity_period = working_days * total_company_responsaveis * 8
                overall_utilization = (total_planned_period / total_capacity_period * 100) if total_capacity_period > 0 else 0
                avg_daily_planned = total_planned_period / working_days if working_days > 0 else 0
                
                # --- Seção de KPIs para o período ---
                st.subheader("📊 KPIs do Período Selecionado")
                
                # Criação dos 2 KPIs em colunas
                kpi_col1, kpi_col2 = st.columns(2)

                with kpi_col1:
                    create_kpi_card(
                        "Horas Previstas",
                        f"{total_planned_period:.1f}h",
                        help_text=f"Total de horas planejadas para o período de {period_start.strftime('%d/%m/%Y')} a {period_end.strftime('%d/%m/%Y')} ({working_days} dias úteis)."
                    )

                with kpi_col2:
                    gauge_fig = create_gauge_chart(
                        overall_utilization, 
                        "Capacidade", 
                        f"Capacidade operacional do período: {total_planned_period:.0f}h de {total_capacity_period:.0f}h disponíveis ({overall_utilization:.1f}% de utilização)."
                    )
                    st.plotly_chart(gauge_fig, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown("---")
                
                # Gráfico de Capacidade do Período
                fig_period = create_period_capacity_chart(
                    df_period_capacity, 
                    period_start, 
                    period_end, 
                    total_company_responsaveis
                )
                
                period_help_text = f"Este gráfico mostra a capacidade total da empresa por dia útil no período selecionado. Cada barra representa um dia útil (segunda a sexta, excluindo feriados). A linha vermelha marca a capacidade máxima diária de {total_company_responsaveis * 8}h ({total_company_responsaveis} responsáveis × 8h)."
                
                create_chart_card_with_help(
                    "📈 Capacidade da Empresa por Período", 
                    period_help_text, 
                    fig_period
                )
                
                # Resumo estatístico do período
                st.subheader("📋 Resumo do Período")
                
                # Métricas do período
                metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                
                with metrics_col1:
                    st.metric(
                        "🗓️ Dias Úteis",
                        f"{working_days}",
                        help="Total de dias úteis no período (excluindo fins de semana e feriados)"
                    )
                
                with metrics_col2:
                    st.metric(
                        "⚡ Capacidade Total",
                        f"{total_capacity_period}h",
                        help=f"Capacidade total da empresa no período ({total_company_responsaveis} responsáveis × 8h × {working_days} dias)"
                    )
                
                with metrics_col3:
                    st.metric(
                        "📊 Horas Planejadas",
                        f"{total_planned_period:.1f}h",
                        help="Total de horas planejadas para o período"
                    )
                
                with metrics_col4:
                    delta_color = "normal"
                    if overall_utilization > 100:
                        delta_color = "inverse"
                    elif overall_utilization < 70:
                        delta_color = "off"
                    
                    st.metric(
                        "📈 Taxa de Utilização",
                        f"{overall_utilization:.1f}%",
                        delta=f"{overall_utilization - 85:.1f}%" if overall_utilization != 85 else None,
                        help="Percentual de utilização da capacidade total da empresa"
                    )
                
                # Tabela detalhada por dia
                st.subheader("📋 Detalhes Diários")
                
                # Cria tabela formatada
                df_detail_display = df_period_capacity.copy()
                # Converte para datetime se necessário e formata a data
                if not pd.api.types.is_datetime64_any_dtype(df_detail_display['data']):
                    df_detail_display['data'] = pd.to_datetime(df_detail_display['data'])
                df_detail_display['Data'] = df_detail_display['data'].dt.strftime('%d/%m/%Y (%a)')
                df_detail_display['Horas Planejadas'] = df_detail_display['horas_planejadas_total'].apply(lambda x: f"{x:.1f}h")
                df_detail_display['Capacidade Máxima'] = df_detail_display['capacidade_maxima_empresa'].apply(lambda x: f"{x}h")
                df_detail_display['Utilização (%)'] = (df_detail_display['horas_planejadas_total'] / df_detail_display['capacidade_maxima_empresa'] * 100).apply(lambda x: f"{x:.1f}%")
                
                # Define status baseado na utilização
                def get_status(row):
                    util_rate = row['horas_planejadas_total'] / row['capacidade_maxima_empresa'] * 100
                    if util_rate == 0:
                        return "⚪ Sem Planejamento"
                    elif util_rate <= 70:
                        return "🟢 Baixa Utilização"
                    elif util_rate <= 100:
                        return "🟡 Utilização Normal"
                    else:
                        return "🔴 Sobrecarga"
                
                df_detail_display['Status'] = df_detail_display.apply(get_status, axis=1)
                
                # Exibe apenas as colunas relevantes
                display_columns = ['Data', 'Horas Planejadas', 'Capacidade Máxima', 'Utilização (%)', 'Status']
                st.dataframe(
                    df_detail_display[display_columns], 
                    use_container_width=True,
                    hide_index=True
                )
                
                # Legenda
                st.caption("""
                **Legenda de Status:**
                - ⚪ **Sem Planejamento**: Nenhuma hora planejada para o dia
                - 🟢 **Baixa Utilização**: ≤ 70% da capacidade
                - 🟡 **Utilização Normal**: 71% - 100% da capacidade
                - 🔴 **Sobrecarga**: > 100% da capacidade
                """)
                
                # Tabela de Tarefas Principais do Período
                st.subheader("📋 Tarefas Principais do Período")
                
                # Filtra tarefas principais (sem parent_id) que têm atividade no período
                df_tasks_period = df_daily_log[
                    (df_daily_log['registro_data'] >= period_start) &
                    (df_daily_log['registro_data'] <= period_end) &
                    (df_daily_log['parent_id'].isnull())
                ].copy()
                
                if not df_tasks_period.empty:
                    # Remove duplicatas para mostrar cada tarefa apenas uma vez
                    df_tasks_display = df_tasks_period.drop_duplicates(subset=['clickup_id'], keep='first').copy()
                    
                    # Calcula total de horas por tarefa no período
                    df_hours_summary = df_tasks_period.groupby(['clickup_id'])['registro_horas'].sum().reset_index()
                    df_hours_summary.columns = ['clickup_id', 'total_horas_periodo']
                    
                    # Faz merge com os dados principais
                    df_tasks_display = pd.merge(df_tasks_display, df_hours_summary, on='clickup_id', how='left')
                    
                    # Prepara colunas para exibição
                    df_tasks_display['ID ClickUp'] = df_tasks_display['clickup_id']
                    df_tasks_display['Nome da Tarefa'] = df_tasks_display['task_nome'].apply(lambda x: x[:50] + "..." if len(str(x)) > 50 else str(x))
                    df_tasks_display['Lista'] = df_tasks_display['lista_origem']
                    df_tasks_display['Responsável'] = df_tasks_display['responsavel'].fillna('Não atribuído')
                    df_tasks_display['Status'] = df_tasks_display['status']
                    df_tasks_display['Prioridade'] = df_tasks_display['prioridade'].fillna('Sem prioridade')
                    df_tasks_display['Horas no Período'] = df_tasks_display['total_horas_periodo'].apply(lambda x: f"{x:.1f}h")
                    
                    # Formata datas
                    df_tasks_display['Data Início'] = pd.to_datetime(df_tasks_display['data_inicio']).dt.strftime('%d/%m/%Y')
                    df_tasks_display['Prazo'] = pd.to_datetime(df_tasks_display['due_date']).dt.strftime('%d/%m/%Y') if 'due_date' in df_tasks_display.columns else 'N/A'
                    
                    # Define cor de status baseado na situação da tarefa
                    def get_task_status_emoji(row):
                        status = str(row['status']).lower()
                        if 'concluí' in status or 'complete' in status or 'done' in status:
                            return f"✅ {row['status']}"
                        elif 'progress' in status or 'andamento' in status or 'doing' in status:
                            return f"🔄 {row['status']}"
                        elif 'review' in status or 'revisão' in status:
                            return f"🔍 {row['status']}"
                        elif 'blocked' in status or 'bloqueado' in status:
                            return f"🚫 {row['status']}"
                        else:
                            return f"⏳ {row['status']}"
                    
                    df_tasks_display['Status Emoji'] = df_tasks_display.apply(get_task_status_emoji, axis=1)
                    
                    # Define prioridade com emojis
                    def get_priority_emoji(priority):
                        priority_str = str(priority).lower()
                        if 'urgent' in priority_str or 'alta' in priority_str or 'high' in priority_str:
                            return f"🔴 {priority}"
                        elif 'normal' in priority_str or 'média' in priority_str or 'medium' in priority_str:
                            return f"🟡 {priority}"
                        elif 'low' in priority_str or 'baixa' in priority_str:
                            return f"🟢 {priority}"
                        else:
                            return f"⚪ {priority}"
                    
                    df_tasks_display['Prioridade Emoji'] = df_tasks_display['Prioridade'].apply(get_priority_emoji)
                    
                    # Colunas para exibição na tabela
                    display_columns = [
                        'ID ClickUp', 'Nome da Tarefa', 'Lista', 'Responsável', 
                        'Status Emoji', 'Prioridade Emoji', 'Horas no Período',
                        'Data Início', 'Prazo'
                    ]
                    
                    # Renomeia colunas para exibição final
                    column_mapping = {
                        'Status Emoji': 'Status',
                        'Prioridade Emoji': 'Prioridade'
                    }
                    
                    df_final_display = df_tasks_display[display_columns].copy()
                    df_final_display = df_final_display.rename(columns=column_mapping)
                    
                    # Ordena por horas no período (decrescente) e depois por data de criação
                    # Primeiro ordena o DataFrame original antes de selecionar as colunas
                    df_tasks_display_sorted = df_tasks_display.sort_values(
                        ['total_horas_periodo', 'data_criacao'], 
                        ascending=[False, False]
                    )
                    
                    # Agora seleciona as colunas para exibição do DataFrame já ordenado
                    df_final_display = df_tasks_display_sorted[display_columns].copy()
                    df_final_display = df_final_display.rename(columns=column_mapping)
                    
                    # Colunas finais para exibição
                    display_columns_final = [col for col in df_final_display.columns]
                    
                    # Exibe a tabela
                    st.dataframe(
                        df_final_display[display_columns_final], 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Informações adicionais sobre a tabela
                    total_tasks = len(df_final_display)
                    total_hours_all_tasks = df_tasks_display['total_horas_periodo'].sum()
                    
                    st.caption(f"""
                    **Resumo da Tabela:**
                    - 📊 **Total de Tarefas Principais**: {total_tasks}
                    - ⏱️ **Total de Horas**: {total_hours_all_tasks:.1f}h
                    - 📅 **Período**: {period_start.strftime('%d/%m/%Y')} a {period_end.strftime('%d/%m/%Y')}
                    - 📝 **Observação**: Mostra apenas tarefas principais (sem subtarefas) que tiveram atividade no período selecionado
                    """)
                    
                else:
                    st.info("📊 Não há tarefas principais com atividade no período selecionado.")
            
            else:
                st.info("📊 Não há dados de capacidade disponíveis para o período selecionado.")
        else:
            st.info("📊 Não há dados disponíveis para análise de capacidade.")
            
else:
    st.error("❌ Não foi possível carregar os dados. Verifique a conexão com a API.")