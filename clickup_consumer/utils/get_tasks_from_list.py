import time
import random
import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')

API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
BASE_URL = "https://api.clickup.com/api/v2"

def _paginated_get(url, params):
    """
    Função auxiliar para lidar com a paginação de qualquer endpoint de lista de tarefas.
    """
    headers = {
        "accept": "application/json",
        "Authorization": API_TOKEN
    }
    all_tasks = []
    page = 0
    
    # Adiciona include_timl a todos os parâmetros de busca
    params['include_timl'] = 'true'

    while True:
        try:
            params['page'] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            tasks = data.get("tasks", [])
            all_tasks.extend(tasks)

            if not data.get("tasks"):
                break
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Erro ao conectar com a API do ClickUp: {e}")
            return None
    
    return all_tasks

def get_tasks_with_subtasks(task_id, max_retries=3):
    """
    Busca uma tarefa específica com suas subtasks na API do ClickUp.
    Implementa retry com backoff exponencial para lidar com rate limiting.
    Versão mais conservadora para uso recursivo.
    """
    url = f"{BASE_URL}/task/{task_id}?include_subtasks=true"
    headers = {
        "accept": "application/json",
        "Authorization": API_TOKEN
    }
    
    for attempt in range(max_retries):
        try:
            # Delay progressivo mais agressivo
            if attempt > 0:
                delay = (3 ** attempt) + random.uniform(0.5, 1.5)
                print(f"    Retry {attempt + 1} para tarefa {task_id} após {delay:.2f}s")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, timeout=45)
            
            # Tratamento específico para rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '90')
                try:
                    retry_after = int(retry_after) if retry_after.isdigit() else 90
                except (ValueError, AttributeError):
                    retry_after = 90
                
                # Adiciona buffer maior para rate limiting
                total_wait = retry_after + random.uniform(5, 15)
                print(f"    Rate limit para tarefa {task_id}. Aguardando {total_wait:.1f}s...")
                time.sleep(total_wait)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            # Delay maior entre requests bem-sucedidos
            time.sleep(random.uniform(0.3, 0.8))
            return data
            
        except requests.exceptions.Timeout:
            print(f"    Timeout na tentativa {attempt + 1} para tarefa {task_id}")
            if attempt == max_retries - 1:
                return None
            continue
            
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 429:
                continue
            elif attempt == max_retries - 1:
                print(f"    Erro final para tarefa {task_id}: {e}")
                return None
            else:
                print(f"    Erro na tentativa {attempt + 1} para tarefa {task_id}: {e}")
                time.sleep((2 ** attempt) + random.uniform(1, 3))
    
    return None


def get_tasks_simple(list_id):
    """Busca tarefas abertas sem subtasks, lidando com paginação."""
    url = f"{BASE_URL}/list/{list_id}/task"
    return _paginated_get(url, params={'subtasks': 'false', 'include_closed': 'false'})

def get_tasks_closed(list_id):
    """Busca tarefas fechadas, lidando com paginação."""
    url = f"{BASE_URL}/list/{list_id}/task"
    return _paginated_get(url, params={'include_closed': 'true'})

def get_list_name(list_id):
    """
    Busca o nome de uma lista específica na API do ClickUp.
    Retorna o nome da lista como uma string, ou None em caso de erro.
    """
    url = f"{BASE_URL}/list/{list_id}"
    headers = {
        "accept": "application/json",
        "Authorization": API_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return data.get("name")
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar com a API do ClickUp para a lista {list_id}: {e}")
        return None