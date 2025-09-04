import pandas as pd
import pytz

def get_task_status(status_obj):
    if isinstance(status_obj, dict):
        return status_obj.get('status')
    return None

def get_task_creator(creator_obj):
    if isinstance(creator_obj, dict):
        return creator_obj.get('username')
    return None

def get_single_assignee_email(assignees_list):
    """
    Extrai o e-mail do primeiro assignee em uma lista.
    Retorna None se a lista for vazia ou se não houver um e-mail.
    """
    if isinstance(assignees_list, list) and len(assignees_list) > 0:
        first_assignee = assignees_list[0]
        return first_assignee.get('email')
    return None

def get_space_id(space_obj):
    if isinstance(space_obj, dict):
        return space_obj.get("id")
    return None

def get_task_priority(priority_obj):
    if isinstance(priority_obj, dict):
        return priority_obj.get('priority')
    return None

def get_task_priority_color(priority_obj):
    if isinstance(priority_obj, dict):
        return priority_obj.get('color')
    return None

def get_task_tags(tags_list):
    if isinstance(tags_list, list) and len(tags_list) > 0:
        first_tag = tags_list[0]
        return first_tag.get('name')
    return None

def get_name_from_nome_da_entrega(custom_fields_list, key):
    """
    Procura o campo 'Nome da Entrega', extrai o ID e retorna a propriedade
    (label, color, etc.) correspondente.
    Retorna None se o campo não for encontrado ou se o valor for inválido.
    """
    if not isinstance(custom_fields_list, list):
        return None

    delivery_value_id = None
    options_list = None
    
    for field in custom_fields_list:
        if isinstance(field, dict) and field.get('name') == "Nome da Entrega":
            # Extrai o ID do valor
            value = field.get('value')
            if isinstance(value, list) and len(value) > 0:
                delivery_value_id = value[0]
            
            # Extrai a lista de opções do 'type_config'
            type_config = field.get('type_config', {})
            options_list = type_config.get('options')
            break

    # Se o ID e as opções forem encontrados, mapeia o ID para a propriedade
    if delivery_value_id and isinstance(options_list, list):
        for option in options_list:
            if isinstance(option, dict) and option.get('id') == delivery_value_id:
                return option.get(key)
    return None

def get_real_end_date_value(custom_fields_list):
    """
    Busca o valor do campo customizado 'Data de término real'.
    Lida com a ausência do campo.
    """
    if isinstance(custom_fields_list, list):
        for field in custom_fields_list:
            if isinstance(field, dict) and field.get('name') == "Data de término real":
                return field.get('value')
    return None

def convert_unix_timestamp_to_date(timestamp_ms, timezone_str='America/Sao_Paulo'):
    """
    Converte um timestamp Unix em milissegundos para uma string de data (YYYY-MM-DD) localizada.
    """
    if pd.isna(timestamp_ms) or timestamp_ms is None:
        return None
    try:
        timestamp_s = int(timestamp_ms) / 1000
    except (ValueError, TypeError):
        return None
    
    try:
        timezone = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.utc
    
    utc_dt = pd.to_datetime(timestamp_s, unit='s', utc=True)
    local_dt = utc_dt.tz_convert(timezone)
    
    return local_dt.strftime('%Y-%m-%d')


def convert_estimate_to_hours(milliseconds):
    if pd.isna(milliseconds) or milliseconds is None:
        return 0
    try:
        return int(milliseconds) / 3600000
    except (ValueError, TypeError):
        return 0


def transform_list_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma um DataFrame de tarefas do ClickUp para um formato amigável.
    """
    try: 
        # Extração de objetos
        df['status'] = df['status'].apply(get_task_status)
        df['creator'] = df['creator'].apply(get_task_creator)
        df['assignees'] = df['assignees'].apply(get_single_assignee_email)
        df['priority_color'] = df['priority'].apply(get_task_priority_color)
        df['priority'] = df['priority'].apply(get_task_priority)
        df['tags'] = df['tags'].apply(get_task_tags)
        df['space'] = df['space'].apply(get_space_id)

        # Extração de campos customizados, com tratamento de exceção
        df['Nome da Entrega'] = df['custom_fields'].apply(lambda x: get_name_from_nome_da_entrega(x, "label"))        
        df['entrega_color'] = df['custom_fields'].apply(lambda x: get_name_from_nome_da_entrega(x, "color")) 
        df['Data de término real'] = df['custom_fields'].apply(get_real_end_date_value)

        # Tratamento das datas
        df['Data de término real'] = df['Data de término real'].apply(convert_unix_timestamp_to_date)
        df['start_date'] = df['start_date'].apply(convert_unix_timestamp_to_date)
        df['due_date'] = df['due_date'].apply(convert_unix_timestamp_to_date)
        df['date_updated'] = df['date_updated'].apply(convert_unix_timestamp_to_date)
        df['date_closed'] = df['date_closed'].apply(convert_unix_timestamp_to_date)
        df['date_done'] = df['date_done'].apply(convert_unix_timestamp_to_date)
        df['date_created'] = df['date_created'].apply(convert_unix_timestamp_to_date)

        # Converte para segundos e horas
        df['time_estimate'] = df['time_estimate'].apply(convert_estimate_to_hours)

        
        # Criação da coluna registro
        # df['Registro'] = 
        
        
        # Limpeza e seleção de colunas
        columns_to_drop = [
            'watchers', 'custom_id', 'custom_item_id', 'description', 'text_content', 
            'orderindex', 'group_assignees', 'top_level_parent', 'url',
            'project', 'list', 'folder', 'dependencies', 'linked_tasks', 
            'locations', 'sharing', 'checklists', 'custom_fields', 'Tempo_Estimado_s',
        ]
        
        # Filtra as colunas a serem removidas que realmente existem no DataFrame
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        df.drop(columns=existing_columns_to_drop, inplace=True)
        
        # Renomeia e reordena colunas para melhor clareza
        df.rename(columns={
            'id': 'ID',
            'name': 'Task_Nome',
            'status': 'Status',
            'creator': 'Criado_por',
            'assignees': 'Responsavel',
            'priority': 'Prioridade',
            'priority_color': 'Cor_Prioridade',
            'tags': 'Tags',
            'space': 'Espaço',
            'date_created': 'Data_Criacao', # colocar start_date
            'due_date': 'Prazo',
            'date_closed': 'Data_Fechamento',
            'time_estimate': 'time_estimate',
            'date_done': 'Data_Done',
            'parent': 'parent_id'
        }, inplace=True)

        return df
    
    except Exception as e:
        print(f"Erro na transformação de dados: {e}")
        return pd.DataFrame()