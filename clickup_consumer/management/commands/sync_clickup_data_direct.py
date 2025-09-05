# clickup_consumer/management/commands/sync_clickup_data_direct.py

import os
import pandas as pd
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Importa as funções do consumidor de API e o modelo
from clickup_consumer.api_consumer import _fetch_and_transform_single_list
from clickup_consumer.models import ClickUpTask

class Command(BaseCommand):
    """
    Comando personalizado para buscar dados da API do ClickUp, processá-los
    e sincronizá-los diretamente com o banco de dados.
    """
    help = 'Sincroniza os dados do ClickUp diretamente para o banco de dados.'

    def calculate_and_update_main_task_time_estimate_transformed(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula a soma dos 'tempo_estimado' das subtasks e atualiza
        o 'tempo_estimado' das tasks principais correspondentes.
        Esta versão trabalha com as colunas após a transformação.
        """
        # 1. Certifique-se de que as colunas necessárias existem (nomes após transformação)
        if 'parent_id' not in df.columns or 'clickup_id' not in df.columns or 'tempo_estimado' not in df.columns:
            self.stdout.write(self.style.WARNING("Colunas necessárias para cálculo de tempo estimado não encontradas"))
            return df
        
        # 2. Filtra apenas as subtasks (aquelas com um parent_id definido)
        subtasks_df = df[df['parent_id'].notna()].copy()
        
        if subtasks_df.empty:
            self.stdout.write("Nenhuma subtask encontrada para cálculo de tempo estimado")
            return df
        
        # 3. Agrupa as subtasks por 'parent_id' e soma o 'tempo_estimado'
        # Converte valores NaN para 0 antes da soma
        subtasks_df['tempo_estimado'] = pd.to_numeric(subtasks_df['tempo_estimado'], errors='coerce').fillna(0)
        time_estimate_sum = subtasks_df.groupby('parent_id')['tempo_estimado'].sum()
        
        # 4. Encontra as tasks principais que correspondem aos IDs dos pais
        # Isso evita a atualização de tasks que não possuem subtasks
        main_tasks_to_update = df[df['clickup_id'].isin(time_estimate_sum.index) & df['parent_id'].isna()]
        
        if not main_tasks_to_update.empty:
            # 5. Atualiza o tempo_estimado das tasks principais
            df.loc[main_tasks_to_update.index, 'tempo_estimado'] = main_tasks_to_update['clickup_id'].map(time_estimate_sum)
            self.stdout.write(f"Tempo estimado atualizado para {len(main_tasks_to_update)} tarefas principais")
        else:
            self.stdout.write("Nenhuma tarefa principal encontrada para atualização de tempo estimado")
        
        return df

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

        self.stdout.write(f"Processando {len(list_ids)} listas: {', '.join(list_ids)}")

        # Processa uma lista por vez para evitar sobrecarga da API
        # (o processamento interno já é paralelo com subtasks)
        for list_id in list_ids:
            self.stdout.write(f"\n--- Processando lista {list_id} ---")
            try:
                transformed_df, error = _fetch_and_transform_single_list(list_id)
                if error:
                    self.stdout.write(self.style.WARNING(f"Aviso para a lista {list_id}: {error}"))
                    errors.append(error)
                elif transformed_df is not None and not transformed_df.empty:
                    self.stdout.write(f"Lista {list_id}: {len(transformed_df)} tarefas processadas")
                    all_lists_df = pd.concat([all_lists_df, transformed_df], ignore_index=True)
                else:
                    self.stdout.write(f"Lista {list_id}: Nenhuma tarefa encontrada")
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Erro ao processar lista {list_id}: {exc}"))
                errors.append(f"Exceção na lista {list_id}: {exc}")

        if all_lists_df.empty:
            self.stderr.write(self.style.ERROR("Nenhum dado foi carregado com sucesso da API."))
            if errors:
                self.stderr.write("\nDetalhes dos erros:")
                for err in errors:
                    self.stderr.write(self.style.ERROR(f"- {err}"))
            return

        self.stdout.write(f"\nTotal de tarefas coletadas de todas as listas: {len(all_lists_df)}")

        # Aplica o cálculo da estimativa de tempo usando a versão corrigida
        self.stdout.write("Calculando estimativas de tempo para tarefas principais...")
        final_df = self.calculate_and_update_main_task_time_estimate_transformed(all_lists_df)
        
        # Salva CSV para debug
        try:
            final_df.to_csv('debug_final_data.csv', sep=',', index=False)
            self.stdout.write("Arquivo debug_final_data.csv salvo")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Erro ao salvar CSV de debug: {e}"))

        self.stdout.write(f"Iniciando a população do banco de dados com {len(final_df)} registros...")
        
        # Passo 1: Limpa a tabela antes de popular
        self.stdout.write("Apagando registros antigos...")
        deleted_count = ClickUpTask.objects.count()
        ClickUpTask.objects.all().delete()
        self.stdout.write(f"Apagados {deleted_count} registros antigos.")
        
        # Passo 2: Salvar todas as tarefas
        successful_inserts = 0
        failed_inserts = 0
        
        for index, row in final_df.iterrows():
            try:
                # Mapeamento corrigido para corresponder aos nomes de campo após a transformação
                task_data = {
                    'clickup_id': str(row.get('clickup_id', '')),
                    'task_nome': str(row.get('task_nome', 'N/A')),
                    'status': str(row.get('status', 'N/A')),
                    'data_criacao': pd.to_datetime(row.get('data_criacao'), errors='coerce'),
                    'data_atualizacao': pd.to_datetime(row.get('data_atualizacao'), errors='coerce'),
                    'data_fechamento': pd.to_datetime(row.get('data_fechamento'), errors='coerce'),
                    'data_done': pd.to_datetime(row.get('data_done'), errors='coerce'),
                    'arquivado': bool(row.get('arquivado', False)),
                    'criado_por': str(row.get('criado_por', 'N/A')),
                    'responsavel': str(row.get('responsavel', 'N/A')),
                    'tags': str(row.get('tags', '')) if not pd.isna(row.get('tags')) else None,
                    'parent_id': str(row.get('parent_id')) if not pd.isna(row.get('parent_id')) else None,
                    'prioridade': str(row.get('prioridade', 'N/A')),
                    'prazo': pd.to_datetime(row.get('prazo'), errors='coerce'),
                    'data_inicio': pd.to_datetime(row.get('data_inicio'), errors='coerce'),
                    'pontos': float(row.get('pontos')) if not pd.isna(row.get('pontos')) else None,
                    'tempo_estimado': float(row.get('tempo_estimado')) if not pd.isna(row.get('tempo_estimado')) else None,
                    'id_equipe': str(row.get('id_equipe', '')),
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
                successful_inserts += 1
                
                # Log de progresso a cada 100 registros
                if successful_inserts % 100 == 0:
                    self.stdout.write(f"  Processados {successful_inserts} registros...")
                
            except Exception as e:
                failed_inserts += 1
                self.stderr.write(self.style.ERROR(f"Erro ao processar registro {index} (ID: {row.get('clickup_id', 'N/A')}): {e}"))
                
        self.stdout.write(self.style.SUCCESS("Sincronização com o banco de dados concluída!"))
        self.stdout.write(f"Registros inseridos com sucesso: {successful_inserts}")
        if failed_inserts > 0:
            self.stdout.write(self.style.WARNING(f"Registros com falha: {failed_inserts}"))