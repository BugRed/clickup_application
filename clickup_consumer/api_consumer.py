# clickup_consumer/api_consumer.py

import pandas as pd
import requests

# Importa as funções auxiliares que você criará na pasta 'utils'
# Certifique-se de que a estrutura de importação esteja correta
from .utils.get_tasks_from_list import get_tasks_simple, get_tasks_with_subtasks, get_tasks_closed, get_list_name
from .utils.transform_list_data import transform_list_data


def calculate_and_update_main_task_time_estimate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a soma dos 'time_estimate' das subtasks e atualiza
    o 'time_estimate' das tasks principais correspondentes.
    """
    # 1. Certifique-se de que as colunas necessárias existem
    if 'parent_id' not in df.columns or 'ID' not in df.columns or 'time_estimate' not in df.columns:
        return df
    
    # 2. Filtra apenas as subtasks (aquelas com um parent_id definido)
    subtasks_df = df[df['parent_id'].notna()].copy()
    
    if subtasks_df.empty:
        return df
    
    # 3. Agrupa as subtasks por 'parent_id' e soma o 'time_estimate'
    # O resultado é uma Series, onde o índice é o parent_id e o valor é a soma
    time_estimate_sum = subtasks_df.groupby('parent_id')['time_estimate'].sum()
    
    # 4. Encontra as tasks principais que correspondem aos IDs dos pais
    # Isso evita a atualização de tasks que não possuem subtasks
    main_tasks_to_update = df[df['ID'].isin(time_estimate_sum.index) & df['parent_id'].isna()]
    
    # 5. Atualiza o time_estimate das tasks principais
    # Acessa os índices das tasks principais a serem atualizadas
    # e mapeia os valores da soma para elas
    df.loc[main_tasks_to_update.index, 'time_estimate'] = main_tasks_to_update['ID'].map(time_estimate_sum)
    
    return df


def _fetch_and_transform_single_list(list_id):
    """
    Busca dados de uma única lista a partir de três fontes, combina-os,
    deduplica e retorna um DataFrame transformado.
    """
    list_id = list_id.strip()
    
    list_name = get_list_name(list_id)
    if not list_name:
        return None, f"Não foi possível obter o nome da lista {list_id}."
        
    tasks_with_subtasks = get_tasks_with_subtasks(list_id)
    tasks_simple = get_tasks_simple(list_id)
    tasks_closed = get_tasks_closed(list_id)
    
    all_tasks = (tasks_with_subtasks if tasks_with_subtasks else []) + \
                (tasks_simple if tasks_simple else []) + \
                (tasks_closed if tasks_closed else [])
    
    if not all_tasks:
        return None, f"Nenhuma tarefa encontrada para a lista {list_name}."
    
    unique_tasks_dict = {task['id']: task for task in all_tasks}
    unique_tasks_list = list(unique_tasks_dict.values())
    
    current_df = pd.DataFrame(unique_tasks_list)
    current_df['List_Origem'] = list_name
    
    transformed_df = transform_list_data(current_df)
    
    return transformed_df, None
