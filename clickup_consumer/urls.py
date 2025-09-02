# clickup_consumer/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Mapeia apenas 'tasks/' para a view da API
    path('tasks/', views.task_list_api, name='task_list_api'),
]
