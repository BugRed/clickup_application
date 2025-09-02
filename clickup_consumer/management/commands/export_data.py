import os
import pandas as pd
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed


# Importa as funções do seu consumidor de API
from clickup_consumer.api_consumer import _fetch_and_transform_single_list, calculate_and_update_main_task_time_estimate


class Command(BaseCommand):
    """
    Comando personalizado para extrair dados da API do ClickUp, processá-los
    e exportar para um arquivo CSV.
    """
    help = 'Extrai dados do ClickUp, processa com Pandas e exporta para um CSV.'

    def handle(self, *args, **options):
        """
        Lógica principal do comando que é executada ao rodar:
        python manage.py export_data
        """
        self.stdout.write("Iniciando a extração e processamento dos dados do ClickUp...")

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
            self.stderr.write(self.style.ERROR("Nenhum dado foi carregado com sucesso."))
            if errors:
                self.stderr.write("\nDetalhes dos erros:")
                for err in errors:
                    self.stderr.write(self.style.ERROR(f"- {err}"))
            return

        # Calcula e atualiza as estimativas de tempo
        final_df = calculate_and_update_main_task_time_estimate(all_lists_df)
        
        # Salva o DataFrame final em um arquivo CSV
        file_path = "data.csv"
        final_df.to_csv(file_path, sep=",", index=False)
        
        self.stdout.write(self.style.SUCCESS(f"Dados extraídos e exportados com sucesso para o arquivo: {file_path}"))
        self.stdout.write(f"Total de linhas no DataFrame: {len(final_df)}")
