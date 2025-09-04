# clickup_consumer/management/commands/sync_clickup_data_direct.py

import os
import pandas as pd
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Importa as funções do consumidor de API e o modelo
from clickup_consumer.api_consumer import _fetch_and_transform_single_list, calculate_and_update_main_task_time_estimate
from clickup_consumer.models import ClickUpTask
from clickup_consumer.utils.transform_list_data import transform_list_data

class Command(BaseCommand):
    """
    Comando personalizado para buscar dados da API do ClickUp, processá-los
    e sincronizá-los diretamente com o banco de dados.
    """
    help = 'Sincroniza os dados do ClickUp diretamente para o banco de dados.'

    def handle(self, *args, **options):
        """
        Lógica principal do comando que é executada.
        """
        self.stdout.write("Iniciando a sincronização dos dados do ClickUp com o banco de dados...")
        
        # Carrega as variáveis de ambiente
        load_dotenv(dotenv_path='.env.local')
        LIST_IDS_STR = os.getenv("LISTS_IDS")

        if not LIST_IDS_STR:
            self.stderr.write(self.style.ERROR("Erro: A variável de ambiente 'LISTS_IDS' não foi encontrada."))
            return

        list_ids = [id.strip() for id in LIST_IDS_STR.split(',') if id.strip()]
        all_lists_df = pd.DataFrame()
        errors = []

        # Utiliza ThreadPoolExecutor para buscas paralelas, melhorando o desempenho
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_list = {executor.submit(_fetch_and_transform_single_list, list_id): list_id for list_id in list_ids}
            
            for future in as_completed(future_to_list):
                list_id = future_to_list[future]
                try:
                    transformed_df, error = future.result()
                    if error:
                        self.stdout.write(self.style.WARNING(f"Aviso para a lista {list_id}: {error}"))
                        errors.append(error)
                    elif transformed_df is not None and not transformed_df.empty:
                        all_lists_df = pd.concat([all_lists_df, transformed_df], ignore_index=True)
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"A busca para a lista {list_id} gerou uma exceção: {exc}"))
                    errors.append(f"Exceção na lista {list_id}: {exc}")

        if all_lists_df.empty:
            self.stderr.write(self.style.ERROR("Nenhum dado foi carregado com sucesso da API."))
            if errors:
                self.stderr.write("\nDetalhes dos erros:")
                for err in errors:
                    self.stderr.write(self.style.ERROR(f"- {err}"))
            return

        # Aplica a única transformação necessária: o cálculo da estimativa de tempo
        final_df = calculate_and_update_main_task_time_estimate(all_lists_df)
        final_df.to_csv('debug.csv', sep=',')

        self.stdout.write(f"Iniciando a população do banco de dados com {len(final_df)} registros...")
        
        # Passo 1: Limpa a tabela antes de popular
        self.stdout.write("Apagando registros antigos...")
        ClickUpTask.objects.all().delete()
        self.stdout.write("Registros antigos apagados.")
        
        # Passo 2: Salvar todas as tarefas
        for index, row in final_df.iterrows():
            try:
                # O mapeamento do dicionário foi refeito para corresponder
                # aos nomes de campo exatos no models.py
                task_data = {
                    'clickup_id': str(row.get('clickup_id')),
                    'task_nome': str(row.get('task_nome', 'N/A')),
                    'status': str(row.get('status', 'N/A')),
                    'data_criacao': pd.to_datetime(row.get('data_criacao'), errors='coerce'),
                    'data_atualizacao': pd.to_datetime(row.get('data_atualizacao'), errors='coerce'),
                    'data_fechamento': pd.to_datetime(row.get('data_fechamento'), errors='coerce'),
                    'data_done': pd.to_datetime(row.get('data_done'), errors='coerce'),
                    'arquivado': bool(row.get('arquivado')),
                    'criado_por': str(row.get('criado_por', 'N/A')),
                    'responsavel': str(row.get('responsavel', 'N/A')),
                    'tags': str(row.get('tags', 'N/A')) if not pd.isna(row.get('tags')) else None,
                    'parent_id': str(row.get('parent_id')) if not pd.isna(row.get('parent_id')) else None,
                    'prioridade': str(row.get('prioridade', 'N/A')),
                    'prazo': pd.to_datetime(row.get('prazo'), errors='coerce'),
                    'data_inicio': pd.to_datetime(row.get('data_inicio'), errors='coerce'),
                    'pontos': float(row.get('pontos')) if not pd.isna(row.get('pontos')) else None,
                    'tempo_estimado': float(row.get('tempo_estimado')) if not pd.isna(row.get('tempo_estimado')) else None,
                    'id_equipe': str(row.get('id_equipe')),
                    'nivel_permissao': str(row.get('nivel_permissao', 'N/A')),
                    'espaco': str(row.get('espaco', 'N/A')),
                    'lista_origem': str(row.get('List_Origem', 'N/A')),
                    'cor_prioridade': str(row.get('cor_prioridade', 'N/A')),
                    'nome_da_entrega': str(row.get('nome_da_entrega', 'N/A')),
                    'cor_entrega': str(row.get('cor_entrega', 'N/A')),
                    'data_de_termino_real': pd.to_datetime(row.get('data_de_termino_real'), errors='coerce')
                }
            
                # Cria o registro no banco de dados
                ClickUpTask.objects.create(**task_data)
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Erro ao processar o registro na linha {index}: {e}"))
                
        self.stdout.write(self.style.SUCCESS("Sincronização com o banco de dados concluída com sucesso!"))
        self.stdout.write(f"Total de registros processados: {len(final_df)}")