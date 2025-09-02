"""
URLs do projeto clickup_main.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('clickup_consumer.urls')),
    
    # Inclui todas as URLs do dashboard com o prefixo 'dashboard/'
    path('dashboard/', include('clickup_dashboards.urls')), 
    
    # Inclui as URLs padrão de autenticação do Django
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
