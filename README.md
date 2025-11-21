# Dashboard de Análise Preditiva em Saúde

## Descrição do Projeto

Este projeto consiste em um **Dashboard de Análise Preditiva em Saúde** focado em doenças brasileiras (Dengue, Chikungunya, Coqueluche, Zika e Rotavírus). O objetivo é fornecer uma plataforma robusta para visualização e análise de dados epidemiológicos, com um sistema de autenticação de usuários para diferentes níveis de acesso.

O backend é construído com **Flask** e **SQLAlchemy**, oferecendo uma API RESTful segura com autenticação **JWT**. O frontend é um dashboard moderno desenvolvido em **React** com **Vite**, utilizando **Tailwind CSS** e a biblioteca de componentes **shadcn/ui**, com design inspirado no **Material Dashboard React**.

## Funcionalidades Implementadas

*   **Autenticação de Usuários (JWT):** Sistema de login e registro com proteção de rotas por perfil (`admin` e `guest`).
*   **Visualização de Dados:** Gráficos interativos (Recharts) para análise da evolução temporal e distribuição de casos.
*   **Análise Geográfica:** Visualizações de dados por localidade (UF e Município).
*   **Ingestão de Dados:** Script para carregamento de dados de arquivos CSV para o banco de dados.
*   **APIs RESTful:** Endpoints para acesso a dados de casos de saúde, usuários e autenticação.
*   **Design Responsivo:** Interface moderna e adaptável a diferentes tamanhos de tela.

## Tecnologias Utilizadas

| Componente | Tecnologia | Descrição |
| :--- | :--- | :--- |
| **Backend** | Python, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS | Servidor API RESTful e ORM para banco de dados. |
| **Frontend** | React, Vite, JavaScript, Tailwind CSS, shadcn/ui, Recharts | Interface de usuário moderna e rápida. |
| **Banco de Dados** | SQLite (padrão, fácil migração para MySQL) | Armazenamento de dados de usuários e casos de saúde. |
| **Gerenciador de Pacotes** | `pip` (Backend), `pnpm` (Frontend) | Gerenciamento de dependências. |

## Estrutura de Arquivos

### Backend (`health-dashboard-backend`)

```
health-dashboard-backend/
├── src/
│   ├── main.py             # Aplicação principal Flask
│   ├── models/             # Modelos de dados (user.py, health_data.py)
│   ├── routes/             # Blueprints de rotas (auth.py, health_data.py)
│   └── database/           # Diretório para o arquivo app.db (SQLite)
├── data_ingestion.py       # Script para carregar dados dos CSVs
├── data_ingestion_sample.py# Script para carregar dados de amostra
├── requirements.txt        # Dependências Python
└── README.md               # Este arquivo
```

### Frontend (`health-dashboard-frontend`)

```
health-dashboard-frontend/
├── src/
│   ├── components/         # Componentes reutilizáveis (shadcn/ui, Layout)
│   ├── contexts/           # Contextos React (AuthContext)
│   ├── pages/              # Páginas da aplicação (Login, Dashboard, etc.)
│   ├── services/           # Configuração da API (healthApi.js)
│   └── main.jsx            # Ponto de entrada da aplicação
├── public/
├── package.json
└── vite.config.js
```

## Instruções de Instalação e Execução

### 1. Backend (API Flask)

1.  **Navegue até o diretório do backend:**
    ```bash
    cd health-dashboard-backend/home/ubuntu/dashboard-saude-backend/
    ```

2.  **Crie e ative um ambiente virtual (opcional, mas recomendado):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute o script de ingestão de dados de amostra:**
    *   O banco de dados será criado e populado com 1.000 registros de amostra.
    ```bash
    python3 data_ingestion_sample.py
    ```

5.  **Inicie o servidor Flask:**
    ```bash
    python3 src/main.py
    ```
    O servidor estará rodando em `http://0.0.0.0:5000`.

### 2. Frontend (React Dashboard)

1.  **Navegue até o diretório do frontend:**
    ```bash
    cd ../../../health-dashboard-frontend/dashboard-saude/
    ```

2.  **Instale as dependências com pnpm:**
    ```bash
    pnpm install
    ```

3.  **Inicie a aplicação React:**
    ```bash
    pnpm run dev
    ```
    A aplicação estará disponível em `http://localhost:5173`.

## Credenciais de Usuários Demo

Use as seguintes credenciais para testar o sistema de autenticação:

| Perfil | E-mail | Senha |
| :--- | :--- | :--- |
| **Administrador** | `admin@saude.gov.br` | `admin123` |
| **Convidado** | `guest@saude.gov.br` | `guest123` |

## Próximos Passos (Desenvolvimento Futuro)

*   Implementação de mapas interativos com Leaflet para visualização de dados geográficos.
*   Desenvolvimento de modelos de Machine Learning para análise preditiva.
*   Criação de páginas de administração para gerenciamento de usuários e dados.
*   Funcionalidade de exportação de relatórios em PDF/CSV.
*   Migração do banco de dados de SQLite para MySQL.
*   Refatoração para utilizar o Material Dashboard React como base de componentes (atualmente usando shadcn/ui com inspiração Material).
