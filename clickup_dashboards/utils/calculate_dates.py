from datetime import datetime, timedelta
import pandas as pd


def calculate_on_time_delivery_rate(df):
    """
    Calcula o percentual de entregas concluídas no prazo.
    
    Uma entrega é considerada no prazo quando:
    data_fechamento <= prazo
    
    Args:
        df (pd.DataFrame): DataFrame com as tarefas concluídas
        
    Returns:
        tuple: (percentual_no_prazo, quantidade_no_prazo, total_concluidas)
    """
    # Verifica se o DataFrame está vazio
    if df.empty: 
        return 0, 0, 0
    
    # Converte as colunas de data para datetime, tratando erros como NaT
    df['prazo'] = pd.to_datetime(df['prazo'], errors='coerce')
    df['data_fechamento'] = pd.to_datetime(df['data_fechamento'], errors='coerce')
    
    # Conta o total de tarefas concluídas (com data de fechamento preenchida)
    df_completed = df[df['data_fechamento'].notnull()]
    total_completed = len(df_completed)
    
    # Se não há tarefas concluídas, retorna zeros
    if total_completed == 0: 
        return 0, 0, 0
    
    # Filtra tarefas que foram concluídas no prazo
    # (data_fechamento <= prazo)
    df_on_time = df_completed[
        (df_completed['prazo'].notnull()) & 
        (df_completed['data_fechamento'] <= df_completed['prazo'])
    ]
    
    # Conta quantas tarefas foram entregues no prazo
    on_time_count = len(df_on_time)
    
    # Calcula o percentual de entregas no prazo
    on_time_rate = (on_time_count / total_completed) * 100
    
    return on_time_rate, on_time_count, total_completed


def calculate_incident_free_rate(df: pd.DataFrame) -> tuple:
    """
    Calcula a taxa de projetos livres de incidentes.
    
    Um projeto (identificado pela coluna 'tags') é considerado com incidente 
    se qualquer uma de suas tarefas contiver a palavra 'Incidente' na coluna 'lista_origem'.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados das tarefas

    Returns:
        tuple: (taxa_projetos_sem_incidentes, projetos_limpos, total_projetos)
    """
    # Verifica se as colunas necessárias existem no DataFrame
    if 'tags' not in df.columns or 'lista_origem' not in df.columns:
        raise ValueError("O DataFrame deve conter as colunas 'tags' e 'lista_origem'.")
    
    # Garante que as colunas sejam tratadas como strings
    df['tags'] = df['tags'].astype(str)
    df['lista_origem'] = df['lista_origem'].astype(str)
    
    # Para cada projeto (agrupado por 'tags'), verifica se alguma tarefa
    # contém a palavra 'Incidente' na coluna 'lista_origem'
    incident_projects = df.groupby('tags')['lista_origem'].apply(
        lambda x: x.str.contains('Incidente', case=False, na=False).any()
    )
    
    # Conta o número total de projetos únicos
    total_projects = len(incident_projects)
    
    # Conta quantos projetos NÃO têm incidentes
    # (~incident_projects) inverte os valores booleanos
    clean_projects = (~incident_projects).sum()
    
    # Calcula o percentual de projetos livres de incidentes
    if total_projects == 0:
        incident_free_rate = 0.0
    else:
        incident_free_rate = (clean_projects / total_projects) * 100
        
    return incident_free_rate, clean_projects, total_projects


def calculate_total_planned_hours(df):
    """
    Calcula o total de horas previstas considerando apenas tarefas principais.
    
    Tarefas principais são aquelas que não possuem parent_id (valor nulo),
    ou seja, não são subtarefas de outras tarefas.
    
    Args:
        df (pd.DataFrame): DataFrame com as tarefas
        
    Returns:
        float: Total de horas estimadas para tarefas principais
    """
    # Verifica se o DataFrame está vazio
    if df.empty: 
        return 0
    
    # Filtra apenas as tarefas principais (sem parent_id)
    # parent_id nulo indica que a tarefa não é subtarefa de outra
    main_tasks = df[df['parent_id'].isnull()]
    
    # Soma o tempo estimado apenas das tarefas principais
    # Evita duplicação de contagem de horas em subtarefas
    return main_tasks['tempo_estimado'].sum()


def calculate_operational_capacity(df, hours_per_week=40):
    """
    Calcula a capacidade operacional para a semana atual.
    
    Fórmula: (Total de horas previstas da semana / Capacidade máxima da equipe) * 100
    
    Capacidade máxima = Número de responsáveis únicos * 40h semanais
    
    Args:
        df (pd.DataFrame): DataFrame de tarefas
        hours_per_week (int): Horas de trabalho por semana por pessoa (padrão: 40h)

    Returns:
        tuple: (taxa_capacidade_operacional, horas_planejadas, capacidade_maxima)
    """
    # Verifica se o DataFrame está vazio
    if df.empty:
        return 0, 0, 0
    
    # Converte a coluna prazo para datetime
    df['prazo'] = pd.to_datetime(df['prazo'], errors='coerce')
    
    # Remove tarefas sem prazo definido
    df_with_deadline = df[df['prazo'].notnull()]
    
    if df_with_deadline.empty:
        return 0, 0, 0
    
    # Obtém a data atual
    today = datetime.now().date()
    
    # Calcula o início da semana atual (segunda-feira)
    # weekday() retorna 0=segunda, 1=terça, ..., 6=domingo
    start_of_week = today - timedelta(days=today.weekday())
    
    # Calcula o fim da semana atual (sexta-feira)
    end_of_week = start_of_week + timedelta(days=4)  # +4 dias = sexta-feira
    
    # Filtra tarefas principais que vencem na semana atual (segunda a sexta)
    df_current_week = df_with_deadline[
        (df_with_deadline['parent_id'].isnull()) &  # Apenas tarefas principais
        (df_with_deadline['prazo'].dt.date >= start_of_week) &  # A partir de segunda
        (df_with_deadline['prazo'].dt.date <= end_of_week)      # Até sexta-feira
    ]
    
    # Soma as horas estimadas das tarefas da semana atual
    planned_hours = df_current_week['tempo_estimado'].sum()
    
    # Conta o número de responsáveis únicos em todo o DataFrame
    # Isso representa o tamanho da equipe disponível
    unique_members = df['responsavel'].nunique()
    
    if unique_members == 0:
        return 0, planned_hours, 0
    
    # Calcula a capacidade máxima da equipe
    # Número de pessoas * 40 horas semanais (segunda a sexta)
    max_capacity = unique_members * hours_per_week
    
    if max_capacity == 0:
        return 0, planned_hours, max_capacity
    
    # Calcula a taxa de capacidade operacional
    # (horas planejadas / capacidade máxima) * 100
    operational_capacity_rate = (planned_hours / max_capacity) * 100
    
    return operational_capacity_rate, planned_hours, max_capacity


def calculate_lead_time(df):
    """
    Calcula o tempo médio de fechamento (lead time) das tarefas concluídas.
    
    Lead time = diferença entre data_fechamento e data_criacao
    
    Args:
        df (pd.DataFrame): DataFrame com as tarefas
        
    Returns:
        tuple: (lead_time_medio, dataframe_com_lead_time)
    """
    # Verifica se o DataFrame está vazio
    if df.empty: 
        return None, pd.DataFrame()
    
    # Converte as colunas de data para datetime
    df['data_fechamento'] = pd.to_datetime(df['data_fechamento'], errors='coerce')
    df['data_criacao'] = pd.to_datetime(df['data_criacao'], errors='coerce')
    
    # Filtra apenas tarefas que foram concluídas (têm data de fechamento)
    df_completed = df[df['data_fechamento'].notnull()]
    
    if df_completed.empty: 
        return 0, pd.DataFrame()
    
    # Calcula o lead time em dias para cada tarefa concluída
    # dt.days extrai apenas os dias da diferença entre datas
    df_completed['lead_time'] = (
        df_completed['data_fechamento'] - df_completed['data_criacao']
    ).dt.days
    
    # Calcula a média do lead time
    avg_lead_time = df_completed['lead_time'].mean()
    
    return avg_lead_time, df_completed


# Função auxiliar para validar o DataFrame de entrada
def validate_dataframe(df, required_columns):
    """
    Valida se o DataFrame contém todas as colunas necessárias.
    
    Args:
        df (pd.DataFrame): DataFrame a ser validado
        required_columns (list): Lista de colunas obrigatórias
        
    Raises:
        ValueError: Se alguma coluna obrigatória estiver faltando
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias faltando: {missing_columns}")


# Função principal para calcular todas as métricas
def calculate_all_metrics(df):
    """
    Calcula todas as métricas de uma só vez.
    
    Args:
        df (pd.DataFrame): DataFrame com os dados das tarefas
        
    Returns:
        dict: Dicionário com todas as métricas calculadas
    """
    # Lista das colunas obrigatórias para os cálculos
    required_columns = [
        'prazo', 'data_fechamento', 'data_criacao', 'tempo_estimado',
        'parent_id', 'responsavel', 'tags', 'lista_origem'
    ]
    
    # Valida se todas as colunas necessárias estão presentes
    validate_dataframe(df, required_columns)
    
    # Calcula todas as métricas
    on_time_rate, on_time_count, total_completed = calculate_on_time_delivery_rate(df)
    incident_free_rate, clean_projects, total_projects = calculate_incident_free_rate(df)
    total_planned_hours = calculate_total_planned_hours(df)
    capacity_rate, planned_hours, max_capacity = calculate_operational_capacity(df)
    avg_lead_time, lead_time_df = calculate_lead_time(df)
    
    # Retorna um dicionário com todas as métricas
    return {
        'delivery_performance': {
            'on_time_rate': round(on_time_rate, 2),
            'on_time_count': on_time_count,
            'total_completed': total_completed
        },
        'quality': {
            'incident_free_rate': round(incident_free_rate, 2),
            'clean_projects': clean_projects,
            'total_projects': total_projects
        },
        'planning': {
            'total_planned_hours': round(total_planned_hours, 2)
        },
        'capacity': {
            'operational_capacity_rate': round(capacity_rate, 2),
            'planned_hours_week': round(planned_hours, 2),
            'max_capacity_week': max_capacity
        },
        'efficiency': {
            'average_lead_time': round(avg_lead_time, 2) if avg_lead_time else 0
        }
    }
    
    
import pandas as pd
import holidays
from datetime import datetime, timedelta

def create_daily_log(df):
    """
    Cria uma nova tabela de log diário a partir do DataFrame de tarefas.
    
    A função calcula as horas diárias baseado na duração real da tarefa
    (data_criacao até data_fechamento), distribuindo o tempo_estimado
    uniformemente pelos dias úteis disponíveis.

    Args:
        df (pd.DataFrame): O DataFrame de entrada contendo as tarefas.
        
    Returns:
        pd.DataFrame: Um novo DataFrame com a coluna 'registro' detalhando
                      o log diário de cada tarefa.
    """
    # Filtra apenas as linhas onde 'parent_id' é null (tasks principais)
    main_tasks = df[df['parent_id'].isnull()].copy()
    
    # Converte colunas para os tipos adequados
    main_tasks['data_criacao'] = pd.to_datetime(main_tasks['data_criacao'], errors='coerce')
    main_tasks['data_fechamento'] = pd.to_datetime(main_tasks['data_fechamento'], errors='coerce')
    main_tasks['tempo_estimado'] = pd.to_numeric(main_tasks['tempo_estimado'], errors='coerce').fillna(0)
    
    # Obtém feriados brasileiros para os anos relevantes
    years = []
    for col in ['data_criacao', 'data_fechamento']:
        years.extend(main_tasks[col].dropna().dt.year.unique())
    
    br_holidays = holidays.country_holidays('BR', years=list(set(years)))
    
    # Cria uma lista para armazenar os registros diários
    daily_records = []
    
    # Itera sobre cada tarefa principal para criar o log diário
    for index, row in main_tasks.iterrows():
        tempo_estimado = row['tempo_estimado']
        data_criacao = row['data_criacao']
        data_fechamento = row['data_fechamento']
        
        # Pula tarefas sem tempo estimado ou datas inválidas
        if tempo_estimado <= 0 or pd.isna(data_criacao):
            continue
        
        # Define data de início
        start_date = data_criacao.date()
        
        # Define data de fim baseado na data_fechamento ou calcula automaticamente
        if pd.notna(data_fechamento):
            end_date = data_fechamento.date()
        else:
            # Se não há data de fechamento, usa a data atual como referência
            end_date = datetime.today().date()
        
        # Garante que a data de fim seja pelo menos igual à data de início
        if end_date < start_date:
            end_date = start_date
        
        # Calcula o número de dias úteis entre as datas
        current_date = start_date
        working_days = []
        
        while current_date <= end_date:
            # Verifica se é dia útil (segunda a sexta) e não é feriado
            if current_date.weekday() < 5 and current_date not in br_holidays:
                working_days.append(current_date)
            current_date += timedelta(days=1)
        
        # Se não há dias úteis, usa pelo menos 1 dia (o dia de criação)
        if not working_days:
            working_days = [start_date]
        
        # Calcula as horas por dia útil
        total_working_days = len(working_days)
        horas_por_dia = tempo_estimado / total_working_days
        
        # Cria um registro para cada dia útil
        for working_day in working_days:
            # Cria uma cópia da linha original
            new_row = row.copy()
            new_row['registro'] = f"{working_day.strftime('%d/%m/%Y')} ({horas_por_dia:.3f}h)"
            new_row['registro_data'] = working_day  # Data para facilitar filtros
            new_row['registro_horas'] = horas_por_dia  # Horas para facilitar cálculos
            daily_records.append(new_row)
    
    # Cria o novo DataFrame a partir da lista de registros
    df_daily_log = pd.DataFrame(daily_records)
    
    df_daily_log.to_csv("daily-debug.csv", sep=',')
    
    return df_daily_log


# Exemplo de uso e teste da função
if __name__ == "__main__":
    # Criar dados de exemplo para testar
    data_exemplo = {
        'clickup_id': ['TASK01', 'TASK02', 'TASK03'],
        'parent_id': [None, None, None],  # Todas são tasks principais
        'tempo_estimado': [16, 24, 8],
        'data_criacao': ['2024-09-08', '2024-09-09', '2024-09-10'],
        'data_fechamento': ['2024-09-15', '2024-09-20', '2024-09-10'],
        'nome': ['Task 01', 'Task 02', 'Task 03'],
        'responsavel': ['João', 'Maria', 'Pedro']
    }
    
    df_exemplo = pd.DataFrame(data_exemplo)
    
    # Testa a função
    resultado = create_daily_log(df_exemplo)
    
    print("Resultado do teste:")
    print(resultado[['nome', 'registro', 'registro_data', 'registro_horas']].to_string())
    
    # Exemplo específico mencionado:
    # TASK01: 16h, criada 08/09, termina 15/09
    # Dias úteis: 08/09, 09/09, 10/09, 11/09, 12/09 (pula 13 e 14), 15/09 = 6 dias
    # Horas por dia: 16h / 6 dias = 2,667h por dia



def calculate_daily_capacity_for_person_list(df_day_filtered, selected_responsible, selected_list):
    """
    Calcula a capacidade diária para uma pessoa específica em uma lista específica.
    """
    if df_day_filtered.empty:
        return 0, 0, 0
    
    # Filtra por responsável se especificado
    if selected_responsible != "Todos":
        df_person = df_day_filtered[df_day_filtered['responsavel'] == selected_responsible]
    else:
        df_person = df_day_filtered
        
    # Filtra por lista se especificado  
    if selected_list != "Todas":
        df_person = df_person[df_person['lista_origem'] == selected_list]
    
    # Soma as horas do dia para a pessoa/lista
    daily_hours = df_person['registro_horas'].sum() if 'registro_horas' in df_person.columns else 0
    
    # Conta quantas pessoas únicas estão trabalhando nesse dia/filtro
    unique_members = df_person['responsavel'].nunique() if not df_person.empty else 0
    
    # Capacidade diária: 8h por pessoa
    daily_capacity = unique_members * 8
    
    # Taxa de capacidade
    capacity_rate = (daily_hours / daily_capacity * 100) if daily_capacity > 0 else 0
    
    return capacity_rate, daily_hours, daily_capacity


