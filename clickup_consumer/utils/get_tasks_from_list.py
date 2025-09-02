import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')

API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
BASE_URL = "https://api.clickup.com/api/v2/"

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

def get_tasks_with_subtasks(list_id):
    """Busca tarefas com subtasks, lidando com paginação."""
    url = f"{BASE_URL}list/{list_id}/task"
    return _paginated_get(url, params={'subtasks': 'true'})

def get_tasks_simple(list_id):
    """Busca tarefas abertas sem subtasks, lidando com paginação."""
    url = f"{BASE_URL}list/{list_id}/task"
    return _paginated_get(url, params={'subtasks': 'false', 'include_closed': 'false'})

def get_tasks_closed(list_id):
    """Busca tarefas fechadas, lidando com paginação."""
    url = f"{BASE_URL}list/{list_id}/task"
    return _paginated_get(url, params={'include_closed': 'true'})

import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')

API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
BASE_URL = "https://api.clickup.com/api/v2/"

def get_list_name(LIST_ID):
    """
    Busca o nome de uma lista específica na API do ClickUp.
    Retorna o nome da lista como uma string, ou None em caso de erro.
    """
    url = f"{BASE_URL}list/{LIST_ID}"
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
        print(f"Erro ao conectar com a API do ClickUp para a lista {LIST_ID}: {e}")
        return None