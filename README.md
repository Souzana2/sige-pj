# SIGE — Sistema Integrado de Gestão Empresarial

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?logo=streamlit&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange?logo=mysql&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-green?logo=scikit-learn&logoColor=white)
![License](https://img.shields.io/badge/Licença-MIT-lightgrey)

> Projeto Final de Curso · Ciência de Dados

**SIGE** é uma plataforma local de administração empresarial que integra gestão de recursos humanos, controlo de inventário, análise financeira e modelos de Inteligência Artificial preditiva, desenvolvida inteiramente em Python com interface web interativa em Streamlit.

O sistema opera sobre um pipeline automatizado de dados no sentido **Excel → MySQL → ML → Portal**, garantindo que o gestor trabalha sempre sobre dados consistentes e atualizados.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Configuração](#instalação-e-configuração)
- [Como Executar](#como-executar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Tecnologias](#tecnologias)
- [Nota sobre o Ficheiro de Dados](#nota-sobre-o-ficheiro-de-dados)
- [Licença](#licença)

---

## Funcionalidades

### Gestão de Recursos Humanos

- Registo completo de colaboradores: nome, cargo, departamento, salário, datas e histórico
- Avaliações de desempenho: assiduidade, produtividade, satisfação e nota do gestor (escala 0–100 %)
- Pagamentos e lançamentos: salários, bónus e adiantamentos com histórico mensal
- Processo de desligamento seguro: inativação de colaboradores sem perda de dados históricos

### Controlo de Stock e Armazém

- Inventário completo com cadastro de produtos por categoria, preço de compra/venda e lead time de reposição
- Movimentações em tempo real: entradas (compras) e saídas (vendas) com atualização automática de saldos
- Alertas de ruptura: cálculo de "Dias até Ruptura" por produto com classificação de risco (crítico / atenção / confortável) baseada no lead time individual

### Dashboard Financeiro Executivo

O dashboard apresenta duas perspetivas financeiras independentes, cada uma com os seus próprios KPIs (Faturação, Custos Operacionais, Resultado Líquido e Receita por Colaborador), formatados no padrão português (`1.234.567,89 €`).

**Visão Real (mês em curso)** — reflete o dinheiro efetivamente movimentado:

| Componente | Cálculo |
|---|---|
| Faturação Real | Soma das saídas de stock × preço de venda registadas no mês |
| Custo de Pessoal | `salário + encargos (23,75 %) + horas extra (× 1,5)` por colaborador |
| Custo de Mercadoria | Soma das entradas de stock × preço de compra registadas no mês |
| Resultado Líquido | `Faturação − Custo Pessoal − Custo Mercadoria` |

**Visão Estimada (projeção mensal estável)** — reflete o potencial de receita com base no ritmo regular de vendas:

| Componente | Cálculo |
|---|---|
| Faturação Estimada | `vendas_mensais × preço_venda` por produto |
| Custo de Pessoal | Igual à Visão Real (custo fixo mensal calculado) |
| Custo de Mercadoria | `vendas_mensais × preço_compra` por produto |
| Resultado Líquido | `Faturação − Custo Pessoal − Custo Mercadoria` |

> **Nota:** Um Resultado Real negativo com Visão Estimada positiva indica investimento pontual em stock, não prejuízo operacional. O sistema inclui um aviso explicativo diretamente no painel.

**Indicadores adicionais:**

- **Giro de Capital** — valor total empatado em armazém e Top 3 produtos mais rentáveis por margem
- **Risco de Turnover** — custo latente estimado de substituição para colaboradores em risco (`salário × 2` por colaborador)

### Inteligência Artificial

**Modelo 1 — Risco de Saída de Colaboradores** (`ml_funcionarios.py`)

Calcula um índice de risco contínuo (0–100) por colaborador ativo com base na seguinte fórmula de negócio:

```
risco_real = (100 − assiduidade)   × 0.30
           + (100 − produtividade) × 0.30
           + (100 − satisfação)    × 0.30
           + horas_extra           × 0.10
```

| Métrica | Fórmula |
|---|---|
| Assiduidade (%) | `(dias_úteis − faltas) / dias_úteis × 100` |
| Produtividade (%) | `metas_concluídas / metas_atribuídas × 100` |
| Satisfação (%) | `nota_satisfação / 5 × 100` |
| Horas Extra | Valor absoluto mensal declarado |

O modelo usa Regressão Linear (`scikit-learn`) com `MinMaxScaler`. Caso os dados não apresentem variação suficiente entre colaboradores, o valor direto da fórmula é utilizado sem ML, evitando instabilidade numérica. O resultado é gravado no campo `risco_saida` na base de dados.

---

**Modelo 2 — Previsão de Ruptura de Stock** (`ml_stock.py`)

Utiliza uma lógica determinística baseada no lead time real de cada produto:

```
vendas_diárias = vendas_mensais / 30
dias_stock     = quantidade_atual / vendas_diárias
margem         = dias_stock − tempo_reposicao
```

| Condição | Risco Previsto |
|---|---|
| `margem ≤ 0` | 100 % — ruptura iminente ou já em falta |
| `0 < margem ≤ tempo_reposicao` | 75 % a 100 % — stock insuficiente para cobrir encomenda |
| `tempo_reposicao < margem ≤ 2× tempo_reposicao` | 40 % a 75 % — margem de segurança reduzida |
| `margem > 2× tempo_reposicao` | 0 % a 40 % — situação confortável |

> A abordagem determinística é intencional: a ruptura de stock tem uma resposta física exata, pelo que um modelo estatístico introduziria ruído sem aumentar a fiabilidade dos alertas.

---

## Arquitetura

```
dados.xlsx
    │
    ▼
[setup_db.py]          →  Garante que a BD MySQL e todas as tabelas existem
    │
    ▼
[sync.py]              →  Excel → MySQL (modo streaming, só insere/atualiza o necessário)
    │
    ▼
[orq.py]               →  Recalcula métricas financeiras de RH e Stock
    │
    ▼
[ml_funcionarios.py]   →  IA: índice de risco de saída → atualiza funcionarios.risco_saida
[ml_stock.py]          →  IA: previsão de ruptura      → atualiza stock.previsao_ruptura
    │
    ▼
[app.py]               →  Portal Streamlit (painel interativo do gestor)
```

---

## Pré-requisitos

- **Python 3.8** ou superior
- **MySQL Server** a correr localmente (XAMPP, WAMP ou instalação nativa)
- Gestor de pacotes `pip`

---

## Instalação e Configuração

**1. Clonar o repositório**

```bash
git clone https://github.com/Souzana2/sige-projeto.git
cd sige-projeto
```

**2. Instalar as dependências**

```bash
pip install streamlit pandas mysql-connector-python scikit-learn openpyxl
```

**3. Configurar a ligação à base de dados**

Edite o ficheiro `conect.py` com as suas credenciais MySQL:

```python
DB_CONFIG = dict(
    host="localhost",
    user="root",
    password="SUA_SENHA_AQUI",
    database="sige_db"
)
```

> A base de dados e todas as tabelas são criadas automaticamente na primeira execução pelo `setup_db.py`.

---

## Como Executar

### Opção A — Pipeline Completo (recomendado)

Executa setup da BD, sincronização, recálculo financeiro, modelos de IA e abre o portal:

```bash
python orq.py
```

### Opção B — Apenas o Portal (BD já atualizada)

```bash
streamlit run app.py
```

### Flags do Orquestrador

| Comando | Ação |
|---|---|
| `python orq.py` | Pipeline completo + abre o portal |
| `python orq.py --sem-portal` | Atualiza tudo mas não abre o portal |
| `python orq.py --so-sync` | Apenas sincroniza Excel → MySQL |
| `python orq.py --so-ml` | Apenas corre os dois modelos de IA |
| `python orq.py --so-ml-func` | Apenas IA de colaboradores |
| `python orq.py --so-ml-stock` | Apenas IA de stock |

O portal fica disponível em **http://localhost:8501**.

---

## Estrutura do Projeto

```
.
├── app.py               # Interface web interativa (Streamlit)
├── orq.py               # Orquestrador do pipeline completo
├── sync.py              # Sincronização Excel → MySQL
├── setup_db.py          # Criação/verificação automática da base de dados
├── conect.py            # Configuração centralizada da ligação MySQL
├── ml_funcionarios.py   # Modelo ML — risco de saída de colaboradores
├── ml_stock.py          # Modelo ML — previsão de ruptura de inventário
├── dados.xlsx           # Fonte de dados de entrada (alimenta o pipeline)
└── dados.xlsm           # Versão com fórmulas Excel (protótipo da fase 1)
```

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3 | Linguagem principal |
| Streamlit | Interface web interativa |
| MySQL | Base de dados relacional |
| Pandas | Manipulação e análise de dados |
| scikit-learn | Modelos de Machine Learning |
| OpenPyXL | Leitura/escrita de ficheiros Excel |
| Excel (xlsm) | Fase 1 — protótipo com fórmulas automáticas |

---

## Nota sobre o Ficheiro de Dados

O ficheiro `dados.xlsx` é a **fonte de entrada única** do sistema. O pipeline opera exclusivamente no sentido **Excel → MySQL** — não há escrita de volta ao Excel.

O ficheiro está estruturado apenas com os campos de preenchimento do gestor, sem colunas calculadas. A versão `dados.xlsm` é mantida separadamente como documento de análise e protótipo da fase 1 do projeto, com fórmulas avançadas ligadas à base de dados.

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).