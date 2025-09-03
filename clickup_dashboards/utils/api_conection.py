import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')
# --- Endereço da API ---
API_URL = os.getenv("API_URL") or ""

# --- Funções de Lógica e Cálculo dos KPIs ---
@st.cache_data
def fetch_tasks_from_api():
    """Busca os dados da API e cria um DataFrame com cache."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        tasks = data.get("tasks", [])
        if not tasks:
            st.warning("A API não retornou dados. Verifique se o banco de dados está populado e o servidor do Django está rodando.")
            return pd.DataFrame()
        df = pd.DataFrame(tasks)
        
        # Mapeia as colunas do JSON para os nomes esperados pelas funções
        column_mapping = {
            'clickup_id': 'clickup_id',
            'task_nome': 'task_nome', 
            'status': 'status',
            'data_criacao': 'data_criacao',
            'data_fechamento': 'data_fechamento',
            'responsavel': 'responsavel',
            'tags': 'tags',
            'parent_id': 'parent_id',
            'prioridade': 'prioridade',
            'prazo': 'prazo',
            'time_estimate': 'tempo_estimado',
            'lista_origem': 'lista_origem'
        }
        
        # Renomeia as colunas se necessário
        df = df.rename(columns=column_mapping)
        
        # Converte time_estimate para numérico (assumindo que está em horas)
        df['tempo_estimado'] = pd.to_numeric(df['tempo_estimado'], errors='coerce').fillna(0)
        
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API: {e}")
        st.warning("Verifique se o servidor do Django está rodando em **http://127.0.0.1:8000**.")
        return pd.DataFrame()


