import streamlit as st
import pandas as pd
import requests
from datetime import timedelta, datetime
import holidays # Importa a biblioteca de feriados

# --- Configuração da Página ---
st.set_page_config(
    page_title="Visualização de Tabelas",
    layout="wide"
)

# --- Título e Descrição da Página ---
st.title("Tabelas de Tarefas do ClickUp")
st.markdown("Visualize as tarefas em formato de tabela para conferência e análise detalhada.")

# --- Endereço da API ---
API_URL = "http://127.0.0.1:8000/api/tasks/"

# --- Função de Consumo da API (com cache) ---
@st.cache_data
def fetch_tasks_from_api():
    """Busca os dados da API e cria um DataFrame com cache."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Lança um erro para códigos de status HTTP 4xx ou 5xx
        data = response.json()
        tasks = data.get("tasks", [])
        
        if not tasks:
            st.warning("A API não retornou dados. Verifique se o banco de dados está populado e o servidor do Django está rodando.")
            return pd.DataFrame()
            
        df = pd.DataFrame(tasks)
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API: {e}")
        st.warning("Verifique se o servidor do Django está rodando em **http://127.0.0.1:8000**.")
        return pd.DataFrame()


def create_daily_log(df):
    """
    Cria uma nova tabela de log diário a partir do DataFrame de tarefas.
    
    A função filtra tarefas principais e, para cada uma, calcula o número de
    dias necessários com base no 'tempo_estimado'. Ela gera uma nova linha
    para cada dia, garantindo que o tempo diário não ultrapasse 8 horas.
    Dias de fim de semana (sábado e domingo) são ignorados.

    Args:
        df (pd.DataFrame): O DataFrame de entrada contendo as tarefas.
        
    Returns:
        pd.DataFrame: Um novo DataFrame com a coluna 'registro' detalhando
                      o log diário de cada tarefa.
    """
    # 1 - Filtra apenas as linhas onde 'parent_id' é null (tasks principais)
    main_tasks = df[df['parent_id'].isnull()].copy()
    
    # Converte 'data_criacao' para o tipo datetime e 'tempo_estimado' para numérico (se necessário)
    main_tasks['data_criacao'] = pd.to_datetime(main_tasks['data_criacao'])
    
    # Cria uma lista para armazenar os registros diários
    daily_records = []
    
    # Itera sobre cada tarefa principal para criar o log diário
    for index, row in main_tasks.iterrows():
        # 2 e 3 - Guarda o tempo estimado e a data de criação
        time_to_spend = row['tempo_estimado'] if 'tempo_estimado' in row else 0
        current_date = row['data_criacao'].date()
        
        daily_limit = 8.0  # Limite de horas de trabalho por dia
        
        while time_to_spend > 0:
            # Verifica se o dia atual é um dia útil (segunda a sexta)
            # weekday() retorna 0 para segunda e 6 para domingo
            if current_date.weekday() < 5:  
                # Calcula o tempo a ser alocado para o dia
                time_for_day = min(time_to_spend, daily_limit)
                
                # Adiciona o novo registro na lista
                new_row = row.copy()
                new_row['registro'] = f"{current_date.strftime('%d/%m/%Y')} ({time_for_day:.1f}h)"
                daily_records.append(new_row)
                
                # Reduz o tempo restante para a tarefa
                time_to_spend -= time_for_day
            
            # Avança para o próximo dia, independentemente de ser fim de semana
            current_date += timedelta(days=1)
            
    # Cria o novo DataFrame a partir da lista de registros
    df_daily_log = pd.DataFrame(daily_records)
    
    return df_daily_log

# --- Carregar os dados automaticamente ao iniciar a aplicação ---
df_full = fetch_tasks_from_api()

# --- Layout da Aplicação ---
if not df_full.empty:
    df_daily_log = create_daily_log(df_full)

    with st.expander("📁 Tarefas Principais"):
        main_tasks = df_full[df_full['parent_id'].isnull()]
        if not main_tasks.empty:
            st.dataframe(main_tasks, use_container_width=True)
        else:
            st.info("Nenhuma tarefa principal foi encontrada.")
            
    st.markdown("---")
    with st.expander("🗓️ Tabela de Registro Diário", expanded=True):
        
        # --- NOVO: Seletor de modo de filtro ---
        filter_mode = st.radio(
            "Modo de Visualização",
            ["Todos os dias", "Filtrar por data"],
            index=0 # 'Todos os dias' como padrão
        )

        if not df_daily_log.empty:
            
            if filter_mode == "Todos os dias":
                # Exibe a tabela completa sem filtro de data
                st.dataframe(df_daily_log, use_container_width=True)
            
            else: # filter_mode == "Filtrar por data"
                
                # --- Adiciona o widget de calendário ---
                selected_date = st.date_input(
                    "Selecione a Data para Filtrar",
                    datetime.today().date()
                )
                
                # --- Lógica de validação: verifica se é fim de semana ou feriado ---
                br_holidays = holidays.country_holidays('BR', years=selected_date.year)
                
                if selected_date.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
                    st.warning("⚠️ Selecione apenas dias úteis para visualizar as tarefas.")
                    st.info("Nenhuma tarefa agendada para fins de semana.")
                
                elif selected_date in br_holidays:
                    st.warning(f"⚠️ O dia {selected_date.strftime('%d/%m/%Y')} é um feriado nacional: {br_holidays.get(selected_date)}.")
                    st.info("Nenhuma tarefa agendada para feriados.")
                
                else:
                    # Filtra a tabela de log diário com base na data selecionada
                    date_filter = selected_date.strftime('%d/%m/%Y')
                    df_filtered = df_daily_log[df_daily_log['registro'].str.startswith(date_filter)]
                    
                    if not df_filtered.empty:
                        st.dataframe(df_filtered, use_container_width=True)
                    else:
                        st.info(f"Nenhuma tarefa agendada para o dia {date_filter}.")
        else:
            st.info("Nenhum registro diário foi gerado.")