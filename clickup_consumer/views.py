# clickup_consumer/views.py

from django.http import JsonResponse
from .models import ClickUpTask
import json
import datetime

def task_list_api(request):
    """
    Busca todas as tarefas do modelo ClickUpTask e retorna como JSON.
    """
    # Busca todas as tarefas no banco de dados
    tasks = ClickUpTask.objects.all().values()
    
    # Converte o QuerySet em uma lista de dicionários
    tasks_list = list(tasks)
    
    # Acessa os campos de data e os converte para um formato de string compatível com JSON
    # O JsonResponse não sabe como serializar objetos de data diretamente
    for task in tasks_list:
        for key, value in task.items():
            if isinstance(value, (datetime.date, datetime.datetime)):
                task[key] = value.isoformat()
    
    # Retorna os dados em uma resposta JSON segura
    return JsonResponse({"tasks": tasks_list}, safe=False)
