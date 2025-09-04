# clickup_consumer/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ClickUpTask
import datetime

class TaskListAPIView(APIView):
    """
    Busca todas as tarefas do modelo ClickUpTask e retorna como JSON.
    Requer autenticação para acesso, via sessão ou token.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Busca todas as tarefas no banco de dados
        tasks = ClickUpTask.objects.all().values()

        # Converte o QuerySet em uma lista de dicionários
        tasks_list = list(tasks)

        # Converte os campos de data para um formato de string compatível com JSON
        for task in tasks_list:
            for key, value in task.items():
                if isinstance(value, (datetime.date, datetime.datetime)):
                    task[key] = value.isoformat()

        # Retorna os dados usando a classe Response do DRF
        return Response({"tasks": tasks_list})