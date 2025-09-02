# run_dev.py

import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# --- Configurações dos Processos ---

# Usa pathlib para criar um caminho de raiz mais robusto
PROJECT_ROOT = Path(__file__).parent

# Constrói o caminho completo para os arquivos dos dashboards
DASHBOARD_FILE_PATH = PROJECT_ROOT / 'clickup_dashboards' / 'dashboard_app.py'
TABLES_FILE_PATH = PROJECT_ROOT / 'clickup_dashboards' / 'tables_app.py'
PROJECAO_FILE_PATH = PROJECT_ROOT / 'clickup_dashboards' / 'projecao_day.py'
PROJECAO_WEEK_FILE_PATH = PROJECT_ROOT / 'clickup_dashboards' / 'projecao_week.py'


PROCESSES_TO_RUN = [
    {
        "name": "Django Server",
        "command": "poetry run python manage.py runserver",
        "cwd": PROJECT_ROOT
    },
    {
        "name": "Streamlit Dashboard",
        # Use o caminho absoluto para o comando do Streamlit
        "command": f"poetry run streamlit run {DASHBOARD_FILE_PATH}",
        "cwd": PROJECT_ROOT
    },
    {
        "name": "Streamlit Tables",
        # Adicionado o comando para o app de tabelas na porta 8502
        "command": f"poetry run streamlit run {TABLES_FILE_PATH} --server.port 8502",
        "cwd": PROJECT_ROOT
    },
    {
        "name": "Streamlit Projeção",
        # Use o caminho absoluto para o comando do Streamlit
        "command": f"poetry run streamlit run {PROJECAO_FILE_PATH} --server.port 8503",
        "cwd": PROJECT_ROOT
    },
        {
        "name": "Streamlit Projeção Week",
        # Use o caminho absoluto para o comando do Streamlit
        "command": f"poetry run streamlit run {PROJECAO_WEEK_FILE_PATH} --server.port 8504",
        "cwd": PROJECT_ROOT
    }
]

# --- Funções de Gerenciamento de Processos ---
active_processes = {}

def start_all_processes():
    """Inicia todos os processos definidos em PROCESSES_TO_RUN."""
    print("Iniciando todos os serviços...\n")
    for proc_info in PROCESSES_TO_RUN:
        name = proc_info["name"]
        command = proc_info["command"]
        cwd = proc_info["cwd"]
        
        print(f"-> Iniciando {name} com o comando: '{command}'")
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            active_processes[name] = process
            print(f"   {name} iniciado com PID: {process.pid}")
        except Exception as e:
            print(f"   Erro ao iniciar {name}: {e}")

def stop_all_processes(signum, frame):
    """Termina todos os processos ativos de forma segura."""
    print("\n\nRecebido sinal de interrupção. Encerrando todos os processos...")
    for name, process in active_processes.items():
        if process.poll() is None:
            print(f"-> Encerrando {name} (PID: {process.pid})...")
            try:
                process.terminate()
                process.wait(timeout=5)
                if process.poll() is None:
                    print(f"   Forçando o encerramento de {name}...")
                    process.kill()
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"   Não foi possível encerrar {name}: {e}")
    print("Todos os processos foram encerrados.")
    sys.exit(0)

def main():
    """Função principal que orquestra o início e o monitoramento."""
    
    signal.signal(signal.SIGINT, stop_all_processes)
    
    start_all_processes()
    
    print("\nAguardando 10 segundos para os serviços subirem...")
    time.sleep(10)

    print("\nServiços rodando! Acesse as URLs abaixo:")
    print("Dashboard Django: http://127.0.0.1:8000/dashboard/")
    print("Dashboard Projeção semana (Streamlit direto): http://localhost:8504")
    print("Dashboard Projeção dia (Streamlit direto): http://localhost:8503")
    print("Dashboard de Tabelas (Streamlit direto): http://localhost:8502")
    print("Dashboard Principal (Streamlit direto): http://localhost:8501")
    
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()