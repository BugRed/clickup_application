from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Adiciona a URL de login.
    # O Django já vem com a view `LoginView` pronta para usar.
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login'), name='login'),
    
    # Suas outras URLs aqui
    path('', views.index_view, name='index'),
    path('graphics/', views.graphics_dashboard, name='graphics_dashboard'),
    path('tables/', views.tables_dashboard, name='tables_dashboard'),
    path('projecao/', views.projecao_dashboard, name='projecao_dashboard'),
]
