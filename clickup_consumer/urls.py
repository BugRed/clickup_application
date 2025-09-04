# clickup_consumer/urls.py

from django.urls import path
from .views import TaskListAPIView

urlpatterns = [
    path('tasks/', TaskListAPIView.as_view(), name='tasks-api'),
]