# clickup_consumer/models.py
from django.db import models

class ClickUpTask(models.Model):
    """
    Este modelo representa a tabela denormalizada
    com os dados transformados da API do ClickUp.
    """
    clickup_id = models.CharField(
        max_length=255, 
        unique=True,
        verbose_name="ID da Tarefa ClickUp"
    )
    
    task_nome = models.CharField(
        max_length=255,
        verbose_name="Nome da Tarefa"
    )
    
    status = models.CharField(
        max_length=50,
        verbose_name="Status"
    )
    
    data_criacao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Criação"
    )
    
    data_atualizacao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Atualização"
    )
    
    data_fechamento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Fechamento"
    )
    
    data_done = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Done"
    )
    
    arquivado = models.BooleanField(
        default=False,
        verbose_name="Arquivado"
    )
    
    criado_por = models.CharField(
        max_length=255,
        verbose_name="Criado por"
    )
    
    responsavel = models.CharField(
        max_length=255,
        verbose_name="Responsável"
    )
    
    tags = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Tags"
    )
    
    parent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Parent ID"
    )
    
    prioridade = models.CharField(
        max_length=50,
        verbose_name="Prioridade"
    )
    
    prazo = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prazo"
    )
    
    data_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Início"
    )
    
    pontos = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Pontos"
    )
    
    tempo_estimado = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tempo Estimado"
    )
    
    id_equipe = models.CharField(
        max_length=255,
        verbose_name="ID da Equipe"
    )
    
    nivel_permissao = models.CharField(
        max_length=50,
        verbose_name="Nível de Permissão"
    )
    
    espaco = models.CharField(
        max_length=255,
        verbose_name="Espaço"
    )
    
    lista_origem = models.CharField(
        max_length=255,
        verbose_name="Lista de Origem"
    )
    
    cor_prioridade = models.CharField(
        max_length=50,
        verbose_name="Cor da Prioridade"
    )
    
    nome_da_entrega = models.CharField(
        max_length=255,
        verbose_name="Nome da Entrega"
    )
    
    cor_entrega = models.CharField(
        max_length=50,
        verbose_name="Cor da Entrega"
    )
    
    data_de_termino_real = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Término Real"
    )
    
    class Meta:
        db_table = 'clickup_consumer_clickuptask'

    def __str__(self):
        return self.task_nome