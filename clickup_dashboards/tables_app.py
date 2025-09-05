import streamlit as st
import pandas as pd
import requests
from datetime import timedelta, datetime
import holidays
from utils.api_conection import fetch_tasks_from_api
from utils.calculate_dates import create_daily_log


# --- Configuração da Página ---
st.set_page_config(
    page_title="Visualização de Tabelas",
    layout="wide"
)

# --- Título e Descrição da Página ---
st.title("Tabelas de Tarefas do ClickUp")
st.markdown("Visualize as tarefas em formato de tabela para conferência e análise detalhada.")



# --- Carregar os dados automaticamente ao iniciar a aplicação ---
df_full = fetch_tasks_from_api()
df_full.to_csv("df_full_debug.csv", sep=';')

# --- Layout da Aplicação ---
if not df_full.empty:
    # Cria o DataFrame base com log diário
    df_daily_log = create_daily_log(df_full)
    df_daily_log.to_csv("daily_logo_debug.csv", sep=';')
    
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

    # --- Aplicação dos filtros nas tabelas originais ---
    # Filtra tarefas principais com base nos filtros selecionados
    main_tasks = df_full[df_full['parent_id'].isnull()].copy()
    if selected_list != "Todas":
        main_tasks = main_tasks[main_tasks['lista_origem'] == selected_list]
    if selected_responsible != "Todos":
        main_tasks = main_tasks[main_tasks['responsavel'] == selected_responsible]

    # Filtra log diário com base nos filtros selecionados
    df_daily_log_filtered = df_daily_log.copy()
    if selected_list != "Todas":
        df_daily_log_filtered = df_daily_log_filtered[df_daily_log_filtered['lista_origem'] == selected_list]
    if selected_responsible != "Todos":
        df_daily_log_filtered = df_daily_log_filtered[df_daily_log_filtered['responsavel'] == selected_responsible]

    with st.expander("📁 Tarefas Principais"):
        if not main_tasks.empty:
            # Define as colunas que devem aparecer com seus novos nomes
            columns_to_show = {
                'task_nome': 'Tarefa',
                'status': 'status',
                'data_fechamento': 'Data de Fechamento',
                'arquivado': 'Arquivado',
                'criado_por': 'Criador',
                'responsavel': 'Responsável',
                'tags': 'Projeto',
                'prioridade': 'Prioridade',
                'prazo': 'Data de Vencimento',
                'data_inicio': 'Data Inicial',
                'tempo_estimado': 'Tempo/h',
                'lista_origem': 'Especialidade',
                'data_de_termino_real': 'Data de termino Real',
                'registro': 'Registro/h',
                'registro_data': 'Registro/dia'
            }
            
            # Filtra e renomeia as colunas
            available_columns = {k: v for k, v in columns_to_show.items() if k in main_tasks.columns}
            main_tasks_display = main_tasks[list(available_columns.keys())].rename(columns=available_columns)
            
            st.dataframe(main_tasks_display, use_container_width=True)
        else:
            st.info("Nenhuma tarefa principal foi encontrada com os filtros selecionados.")
            
    st.markdown("---")
    with st.expander("🗓️ Tabela de Registro Diário", expanded=True):
        if not df_daily_log_filtered.empty:
            # Define as colunas que devem aparecer com seus novos nomes
            columns_to_show = {
                'task_nome': 'Tarefa',
                'status': 'status',
                'data_fechamento': 'Data de Fechamento',
                'arquivado': 'Arquivado',
                'criado_por': 'Criador',
                'responsavel': 'Responsável',
                'tags': 'Projeto',
                'prioridade': 'Prioridade',
                'prazo': 'Data de Vencimento',
                'data_inicio': 'Data Inicial',
                'tempo_estimado': 'Tempo/h',
                'lista_origem': 'Especialidade',
                'data_de_termino_real': 'Data de termino Real',
                'registro': 'Registro/h',
                'registro_data': 'Registro/dia'
            }
            
            # A tabela responde apenas aos filtros da seção de Segmentação de Dados
            if date_filter_mode == "Todos os dias":
                # Exibe a tabela completa filtrada apenas pelos filtros de segmentação
                available_columns = {k: v for k, v in columns_to_show.items() if k in df_daily_log_filtered.columns}
                df_display = df_daily_log_filtered[list(available_columns.keys())].rename(columns=available_columns)
                st.dataframe(df_display, use_container_width=True)
            else:
                # Filtra também por data quando o modo "Filtrar por data" está ativo
                if 'df_daily_filtered_for_charts' in locals() and not df_daily_filtered_for_charts.empty:
                    available_columns = {k: v for k, v in columns_to_show.items() if k in df_daily_filtered_for_charts.columns}
                    df_display = df_daily_filtered_for_charts[list(available_columns.keys())].rename(columns=available_columns)
                    st.dataframe(df_display, use_container_width=True)
                else:
                    if selected_date.weekday() >= 5 or selected_date in holidays.country_holidays('BR', years=selected_date.year):
                        st.info("Nenhuma tarefa agendada para este dia.")
                    else:
                        st.info(f"Nenhuma tarefa agendada para o dia {selected_date.strftime('%d/%m/%Y')}.")
        else:
            st.info("Nenhum registro diário foi gerado com os filtros selecionados.")