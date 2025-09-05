# clickup_consumer/api_consumer.py
# Importa as funções auxiliares que você criará na pasta 'utils'
# Certifique-se de que a estrutura de importação esteja correta
from .utils.get_tasks_from_list import get_tasks_simple, get_tasks_with_subtasks, get_tasks_closed, get_list_name
from .utils.transform_list_data import transform_list_data

import pandas as pd
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def _iterative_subtask_processing(df: pd.DataFrame, max_iterations=5, max_workers=2) -> pd.DataFrame:
    """
    Processa de forma iterativa um DataFrame para buscar subtasks aninhadas.

    A função busca por tasks que ainda têm 'subtasks' aninhadas na coluna,
    realiza a busca na API para essas subtasks e as adiciona ao DataFrame.
    O processo se repete até que não haja mais subtasks a serem buscadas ou
    o número máximo de iterações seja atingido.
    
    Args:
        df (pd.DataFrame): DataFrame com as tarefas já processadas
        max_iterations (int): Número máximo de iterações para buscar subtasks
        max_workers (int): Número máximo de workers para processamento paralelo
    
    Returns:
        pd.DataFrame: DataFrame final com todas as subtasks processadas
    """
    from .utils.get_tasks_from_list import get_tasks_with_subtasks
    from .utils.transform_list_data import transform_list_data
    
    # Certifique-se de que a coluna 'subtasks' existe
    if 'subtasks' not in df.columns:
        print("Coluna 'subtasks' não encontrada no DataFrame.")
        return df

    all_tasks = df.copy()
    iteration = 0
    
    print(f"Iniciando processamento iterativo de subtasks. DataFrame inicial: {len(all_tasks)} tarefas")

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteração {iteration} de {max_iterations} ---")

        # 1. Filtra as linhas que ainda têm subtasks aninhadas (não vazias e não None)
        def has_valid_subtasks(subtasks_value):
            """Verifica se o valor da coluna subtasks contém dados válidos"""
            if pd.isna(subtasks_value):
                return False
            
            # Se for string, tenta converter para lista
            if isinstance(subtasks_value, str):
                try:
                    # Remove espaços e verifica se não está vazio
                    if subtasks_value.strip() in ['', '[]', 'null', 'None']:
                        return False
                    parsed = json.loads(subtasks_value)
                    return isinstance(parsed, list) and len(parsed) > 0
                except (json.JSONDecodeError, ValueError):
                    return False
            
            # Se já for lista
            elif isinstance(subtasks_value, list):
                return len(subtasks_value) > 0
            
            return False

        # Aplica o filtro
        tasks_with_nested_subtasks = all_tasks[
            all_tasks['subtasks'].apply(has_valid_subtasks)
        ].copy()

        if tasks_with_nested_subtasks.empty:
            print("Nenhuma subtask aninhada encontrada. Processamento concluído.")
            break

        print(f"  Encontradas {len(tasks_with_nested_subtasks)} tarefas com subtasks aninhadas")

        # 2. Extrai os IDs das subtasks a serem buscadas
        new_task_ids_to_fetch = set()
        
        for idx, row in tasks_with_nested_subtasks.iterrows():
            subtasks_value = row['subtasks']
            
            # Converte string para lista se necessário
            if isinstance(subtasks_value, str):
                try:
                    subtask_list = json.loads(subtasks_value)
                except (json.JSONDecodeError, ValueError):
                    continue
            elif isinstance(subtasks_value, list):
                subtask_list = subtasks_value
            else:
                continue
            
            # Extrai IDs das subtasks
            for subtask in subtask_list:
                if isinstance(subtask, dict) and 'id' in subtask:
                    new_task_ids_to_fetch.add(subtask['id'])

        print(f"  IDs únicos de subtasks para buscar: {len(new_task_ids_to_fetch)}")

        if not new_task_ids_to_fetch:
            print("  Nenhuma nova subtask encontrada. Processamento concluído.")
            break

        # 3. Busca as novas tarefas (incluindo subtasks) em paralelo com rate limiting
        new_tasks_data = []
        task_ids_list = list(new_task_ids_to_fetch)
        
        def fetch_single_task_safe(task_id):
            """Wrapper seguro para busca de tarefa individual"""
            try:
                return get_tasks_with_subtasks(task_id)
            except Exception as e:
                print(f"    Erro ao buscar tarefa {task_id}: {e}")
                return None

        # Processa em lotes menores para evitar rate limiting
        batch_size = max_workers
        for i in range(0, len(task_ids_list), batch_size):
            batch_ids = task_ids_list[i:i + batch_size]
            print(f"  Processando lote {i//batch_size + 1}/{(len(task_ids_list) + batch_size - 1)//batch_size} ({len(batch_ids)} tarefas)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task_id = {
                    executor.submit(fetch_single_task_safe, task_id): task_id 
                    for task_id in batch_ids
                }
                
                for future in as_completed(future_to_task_id):
                    task_id = future_to_task_id[future]
                    try:
                        task_data = future.result()
                        if task_data:
                            # Achata a estrutura de tarefa principal + subtasks
                            flattened_tasks = _flatten_task_with_subtasks(task_data)
                            new_tasks_data.extend(flattened_tasks)
                    except Exception as exc:
                        print(f"    Erro ao processar resultado para tarefa {task_id}: {exc}")
            
            # Delay entre lotes para evitar rate limiting
            if i + batch_size < len(task_ids_list):
                print(f"    Aguardando 2s antes do próximo lote...")
                time.sleep(2)
        
        print(f"  Total de novas tarefas recuperadas: {len(new_tasks_data)}")
        
        if not new_tasks_data:
            print("  Nenhum dado recuperado para as novas subtasks.")
            break

        # 4. Converte para DataFrame e adiciona informações necessárias
        new_df = pd.DataFrame(new_tasks_data)
        
        # Adiciona a coluna List_Origem se não existir
        if 'List_Origem' not in new_df.columns:
            # Pega o valor da primeira tarefa do DataFrame original como referência
            if 'List_Origem' in all_tasks.columns:
                list_origem_ref = all_tasks['List_Origem'].iloc[0] if not all_tasks['List_Origem'].empty else 'Desconhecido'
                new_df['List_Origem'] = list_origem_ref
        
        # 5. Transforma os novos dados usando a mesma função de transformação
        try:
            transformed_new_df = transform_list_data(new_df)
        except Exception as e:
            print(f"    Erro na transformação dos dados: {e}")
            # Em caso de erro, usa os dados sem transformação
            transformed_new_df = new_df
        
        # 6. Remove a coluna 'subtasks' das novas tarefas para evitar problemas na concatenação
        if 'subtasks' in transformed_new_df.columns:
            transformed_new_df = transformed_new_df.drop(columns=['subtasks'])
        
        # 7. Concatena os novos dados com o DataFrame principal
        all_tasks = pd.concat([all_tasks, transformed_new_df], ignore_index=True)
        
        # 8. Remove duplicatas baseadas no ID (ou clickup_id se transformado)
        id_column = 'clickup_id' if 'clickup_id' in all_tasks.columns else 'ID'
        if id_column in all_tasks.columns:
            initial_count = len(all_tasks)
            all_tasks = all_tasks.drop_duplicates(subset=[id_column], keep='first')
            print(f"    Removidas {initial_count - len(all_tasks)} duplicatas baseadas em {id_column}")
        
        # 9. Limpa a coluna subtasks das tarefas que já foram processadas
        # Marca como processadas as tarefas cujos IDs foram buscados nesta iteração
        def clean_processed_subtasks(row):
            if not has_valid_subtasks(row['subtasks']):
                return row['subtasks']
            
            subtasks_value = row['subtasks']
            if isinstance(subtasks_value, str):
                try:
                    subtask_list = json.loads(subtasks_value)
                except (json.JSONDecodeError, ValueError):
                    return row['subtasks']
            elif isinstance(subtasks_value, list):
                subtask_list = subtasks_value
            else:
                return row['subtasks']
            
            # Remove subtasks que já foram processadas
            remaining_subtasks = [
                subtask for subtask in subtask_list
                if subtask.get('id') not in new_task_ids_to_fetch
            ]
            
            return remaining_subtasks if remaining_subtasks else None
        
        all_tasks['subtasks'] = all_tasks.apply(clean_processed_subtasks, axis=1)
        
        print(f"    DataFrame agora possui {len(all_tasks)} tarefas únicas.")
        
    print(f"\nProcessamento iterativo de subtasks finalizado após {iteration} iterações.")
    print(f"Total final: {len(all_tasks)} tarefas")
    
    # 10. Remove completamente a coluna 'subtasks' do DataFrame final
    if 'subtasks' in all_tasks.columns:
        all_tasks = all_tasks.drop(columns=['subtasks'])
        print("Coluna 'subtasks' removida do DataFrame final.")
    
    return all_tasks


def _flatten_task_with_subtasks(task_data):
    """
    Extrai a tarefa principal e suas subtasks de uma resposta da API,
    retornando uma lista de tarefas individuais.
    """
    if not task_data:
        return []
    
    tasks_list = []
    
    # Adiciona a tarefa principal
    main_task = task_data.copy()
    # Remove subtasks da tarefa principal para evitar duplicação
    if 'subtasks' in main_task:
        del main_task['subtasks']
    tasks_list.append(main_task)
    
    # Adiciona as subtasks se existirem
    subtasks = task_data.get('subtasks', [])
    for subtask in subtasks:
        tasks_list.append(subtask)
    
    return tasks_list


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


def _fetch_tasks_with_subtasks_parallel(task_ids, max_workers=10):
    """
    Busca tarefas com subtasks em paralelo usando ThreadPoolExecutor.
    """
    all_tasks_with_subtasks = []
    
    def fetch_single_task(task_id):
        return get_tasks_with_subtasks(task_id)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submete todas as tarefas para execução paralela
        future_to_task_id = {executor.submit(fetch_single_task, task_id): task_id for task_id in task_ids}
        
        for future in as_completed(future_to_task_id):
            task_id = future_to_task_id[future]
            try:
                task_data = future.result()
                if task_data:
                    # Achata a estrutura de tarefa principal + subtasks
                    flattened_tasks = _flatten_task_with_subtasks(task_data)
                    all_tasks_with_subtasks.extend(flattened_tasks)
            except Exception as exc:
                print(f"Erro ao buscar subtasks para a tarefa {task_id}: {exc}")
    
    return all_tasks_with_subtasks



def _fetch_and_transform_single_list(list_id):
    """
    Busca dados de uma única lista a partir de três fontes, combina-os,
    deduplica e retorna um DataFrame transformado.
    """
    list_id = list_id.strip()
    
    list_name = get_list_name(list_id)
    if not list_name:
        return None, f"Não foi possível obter o nome da lista {list_id}."
    
    print(f"Processando lista: {list_name}")
    
    # Passo 1: Buscar tarefas simples e fechadas em paralelo
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_simple = executor.submit(get_tasks_simple, list_id)
        future_closed = executor.submit(get_tasks_closed, list_id)
        
        tasks_simple = future_simple.result() or []
        tasks_closed = future_closed.result() or []
    
    print(f"Lista {list_name}: {len(tasks_simple)} tarefas simples, {len(tasks_closed)} tarefas fechadas")
    
    # Passo 2: Concatenar tasks simples e fechadas
    all_basic_tasks = tasks_simple + tasks_closed
    
    if not all_basic_tasks:
        return None, f"Nenhuma tarefa encontrada para a lista {list_name}."
    
    # Passo 3: Extrair IDs únicos das tarefas
    task_ids = list({task['id'] for task in all_basic_tasks})
    print(f"Lista {list_name}: Buscando detalhes com subtasks para {len(task_ids)} tarefas únicas")
    
    # Passo 4: Buscar tarefas com subtasks recursivamente (incluindo subtasks das subtasks)
    tasks_with_subtasks = _fetch_tasks_with_subtasks_parallel(task_ids, max_workers=2)
    
    print(f"Lista {list_name}: {len(tasks_with_subtasks)} tarefas (incluindo subtasks) recuperadas")
    
    # Passo 5: Concatenar todas as tarefas
    all_tasks = all_basic_tasks + tasks_with_subtasks
    
    # Passo 6: Remover duplicatas baseado no ID
    unique_tasks_dict = {task['id']: task for task in all_tasks}
    unique_tasks_list = list(unique_tasks_dict.values())
    
    print(f"Lista {list_name}: {len(unique_tasks_list)} tarefas únicas após deduplicação")
    
    # Passo 7: Converter para DataFrame e adicionar origem
    current_df = pd.DataFrame(unique_tasks_list)
    current_df['List_Origem'] = list_name
    
    # Passo 8: Transformar os dados
    transformed_df = transform_list_data(current_df)
    
    return transformed_df, None