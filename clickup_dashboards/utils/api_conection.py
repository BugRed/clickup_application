import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env.local em ambiente de desenvolvimento
load_dotenv(dotenv_path='.env.local')

# --- Endereço e Token da API ---
API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("DJANGO_API_TOKEN") # Carrega o token

# --- Funções de Lógica e Cálculo dos KPIs ---
@st.cache_data
def fetch_tasks_from_api():
    """Busca os dados da API com autenticação e cria um DataFrame com cache."""
    if not API_URL:
        st.error("Variável de ambiente 'API_URL' não configurada.")
        return pd.DataFrame()
        
    # Adiciona o token de autenticação nos headers da requisição
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status() # Lança um erro para status 4xx ou 5xx
        
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
        st.warning("Verifique a URL da API e se o servidor do Django está rodando.")
        return pd.DataFrame()