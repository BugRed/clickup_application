from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt

@login_required
def index_view(request):
    """
    Renderiza a página principal (index.html) apenas para usuários logados.
    """
    return render(request, 'index.html')

@login_required
@xframe_options_exempt
def graphics_dashboard(request):
    """
    Retorna o HTML do iframe para o dashboard de gráficos.
    Protegido por login.
    """
    iframe_html = """
    <div class="iframe-container">
        <iframe src="http://localhost:8501"></iframe>
    </div>
    """
    return HttpResponse(iframe_html)

@login_required
@xframe_options_exempt
def tables_dashboard(request):
    """
    Retorna o HTML do iframe para o dashboard de tabelas.
    Protegido por login.
    """
    iframe_html = """
    <div class="iframe-container">
        <iframe src="http://localhost:8502"></iframe>
    </div>
    """
    return HttpResponse(iframe_html)

@login_required
@xframe_options_exempt
def projecao_dashboard(request):
    """
    Retorna o HTML do iframe para o dashboard de projeção.
    Protegido por login.
    """
    iframe_html = """
    <div class="iframe-container">
        <iframe src="http://localhost:8503"></iframe>
    </div>
    """
    return HttpResponse(iframe_html)
