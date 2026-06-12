# ⚙️ SIGE - Sistema Integrado de Gestão Empresarial

Bem-vindo ao **SIGE (Sistema Integrado de Gestão Empresarial)**, uma plataforma moderna de administração, controlo de stock, gestão de recursos humanos e análise preditiva com Inteligência Artificial. 

Este projeto integra uma base de dados relacional **MySQL**, sincronização automatizada com planilhas **Excel**, modelos de **Machine Learning** para previsões de negócios e um **painel executivo interativo** desenvolvido em Python.

---

## 🚀 Funcionalidades Principais

### 1. 👥 Gestão de Recursos Humanos (RH)
*   **Registo e Atualização:** Ficha completa de colaboradores, incluindo salário, departamento, cargo e histórico.
*   **Avaliações e Notas:** Visualização automatizada de assiduidade, produtividade, satisfação e avaliação geral do gestor.
*   **Gestão de Turnos/Demissões:** Processo simples para desligar colaboradores diretamente do painel de administração.

### 2. 📦 Controlo de Stock e Armazém
*   **Inventário Completo:** Cadastro de produtos por categoria, preço de compra, preço de venda e quantidades em armazém.
*   **Registo de Vendas e Reposições:** Monitorização do giro de capital e vendas mensais.
*   **Definição de Limites:** Alertas visuais integrados para stock mínimo e tempo estimado de reposição.

### 3. 📈 Dashboard Financeiro Executivo
*   **Indicadores de Saúde:** Faturação estimada, custos operacionais detalhados (pessoal vs. mercadoria) e lucro líquido mensal em tempo real.
*   **Giro de Capital:** Análise dos produtos mais rentáveis (Top 3) e capital empatado em stock.
*   **Risco Latente de Turnover:** Cálculo do custo oculto previsto caso colaboradores em risco de saída deixem a empresa.

### 4. 🧠 Inteligência Artificial (Machine Learning)
*   **Previsão de Risco de Saída:** Avalia probabilidade de desligamento voluntário dos funcionários usando Regressão Linear com base em assiduidade, horas extras e satisfação.
*   **Previsão de Ruptura de Stock:** Analisa o histórico de saídas e reposições para identificar dias restantes até a ruptura de cada produto.

---

## 🛠️ Arquitetura do Projeto e Arquivos

O projeto está estruturado nos seguintes módulos:

*   **`app.py`**: A interface visual interativa desenvolvida em **Streamlit**. É o painel onde o utilizador interage com os dados e roda os modelos de IA.
*   **`orq.py`**: O orquestrador central do pipeline. Coordena a execução de todas as etapas (criação do banco, sincronização, recálculo financeiro e execução do machine learning).
*   **`sync.py`**: Realiza a sincronização bidirecional otimizada entre o ficheiro Excel (`dados.xlsx`) e o MySQL.
*   **`setup_db.py`**: Garante que o banco de dados MySQL e todas as tabelas necessárias existam no arranque.
*   **`conect.py`**: Configuração central de ligação ao servidor MySQL.
*   **`ml_funcionarios.py`**: Modelo de machine learning para previsão do turnover da equipa.
*   **`ml_stock.py`**: Modelo de machine learning para previsão de ruptura de inventário.
*   **`dados.xlsx`** / **`dados.xlsm`**: Bases de dados locais utilizadas para alimentar o sistema e sincronizar com o banco de dados relacional.

---

## 📋 Pré-requisitos

Antes de iniciar, certifique-se de que tem o **Python 3.8+** instalado e o servidor **MySQL** a correr localmente.

### Bibliotecas Necessárias
Instale as dependências executando o comando abaixo no terminal:

```bash
pip install streamlit pandas mysql-connector-python scikit-learn openpyxl
```

---

## 🏁 Como Executar o Projeto

### Passo 1: Executar o Pipeline de Dados (Orquestrador)
Execute o script orquestrador para criar a base de dados, sincronizar os dados do Excel e treinar os modelos de Inteligência Artificial pela primeira vez:

```bash
python orq.py
```

*Dica:* O orquestrador aceita parâmetros como `--so-sync` (apenas sincronizar) ou `--so-ml` (apenas rodar os modelos de IA).

### Passo 2: Executar o Painel de Administração (Interface Streamlit)
Com o banco de dados carregado e atualizado, inicie o painel visual no seu navegador:

```bash
streamlit run app.py
```

O painel será aberto automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

---

## 🎨 Tecnologias Utilizadas

*   **Linguagem:** Python
*   **Interface Gráfica:** Streamlit
*   **Base de Dados:** MySQL
*   **Modelagem de IA:** Scikit-Learn (MinMaxScaler & LinearRegression)
*   **Manipulação de Ficheiros:** Pandas & OpenPyxl
