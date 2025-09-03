# ClickUp Data Application

Esta aplicação web integra servidores Django e Streamlit para criar uma solução robusta de gerenciamento e visualização de dados. A arquitetura do projeto permite a extração, transformação e carregamento (ETL) de dados da API do ClickUp, sua persistência em um banco de dados e a apresentação em dashboards interativos.

## Arquitetura do Projeto

-   **Backend (Django):** Responsável pela lógica de negócios, autenticação de usuários e uma API interna. A API consome dados da API do ClickUp, aplica processos de ETL e popula as tabelas "gold" em um banco de dados **Supabase**.
-   **Frontend (Streamlit):** Vários aplicativos Streamlit atuam como a interface do usuário. Eles se conectam ao banco de dados Supabase para consumir os dados processados e exibi-los em dashboards e tabelas interativas. A autenticação é gerenciada pelo Django, garantindo que apenas usuários autorizados possam acessar o conteúdo.

## Estrutura de Diretórios

-   `clickup_main`: Contém a configuração principal do projeto Django (settings, wsgi, urls).
-   `clickup_consumer`: Onde se encontra a API interna, que gerencia o consumo da API do ClickUp e o processo de ETL.
-   `clickup_dashboards`: Diretório que hospeda todas as aplicações Streamlit, cada uma funcionando como um dashboard ou uma página de visualização.

## Como Executar Localmente

Para rodar a aplicação em seu ambiente de desenvolvimento, utilize o Poetry para gerenciar as dependências e o script `run_dev.py` para iniciar todos os serviços simultaneamente.

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/BugRed/clickup_application](https://github.com/BugRed/clickup_application)
    cd seu-repositorio
    ```
2.  **Instale as Dependências:**
    ```bash
    poetry install
    ```
3.  **Execute os Servidores:**
    ```bash
    poetry run python run_dev.py
    ```

## Futuras Atualizações

-   Substituir os servidores de front-end Streamlit por uma interface mais moderna e escalável, desenvolvida com **Next.js**.
-   Implementar um sistema de caching mais eficiente para reduzir as chamadas à API do ClickUp.
-   Adicionar recursos de análise preditiva e machine learning para gerar insights a partir dos dados.