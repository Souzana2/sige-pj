# SIGE — Sistema Integrado de Gestão Empresarial

> Projeto Final de Curso · Ciência de Dados

**SIGE** é uma plataforma local de administração empresarial que integra gestão de recursos humanos, controlo de inventário, análise financeira e modelos de Inteligência Artificial preditiva, tudo num painel interativo desenvolvido em Python.

O sistema combina um pipeline automatizado de dados (Excel → MySQL → ML → Portal) com uma interface web construída em Streamlit.

> **Nota sobre sincronização:** o ficheiro `dados.xlsx` é a **fonte de entrada única** — o pipeline flui apenas no sentido **Excel → MySQL**. O ficheiro está organizado exclusivamente com os campos de preenchimento do gestor (sem colunas calculadas). O Excel com fórmulas avançadas é mantido em separado (`dados.xlsm`) como documento de análise e protótipo da fase 1 do projeto.

---

## Funcionalidades Principais

### 1. Gestão de Recursos Humanos (RH)
- **Registo completo de colaboradores** — nome, cargo, departamento, salário, datas e histórico.
- **Avaliações de desempenho** — assiduidade, produtividade, satisfação e avaliação do gestor (escala 0–100 %).
- **Pagamentos e lançamentos** — registo de salários, bónus e adiantamentos com histórico mensal.
- **Desligamento** — processo seguro de inativação de colaboradores sem apagar dados históricos.

### 2. Controlo de Stock e Armazém
- **Inventário completo** — cadastro de produtos por categoria, preço de compra/venda e lead time de reposição.
- **Movimentações em tempo real** — registo de entradas (compras) e saídas (vendas) com atualização automática de saldos, vendas mensais e stock mínimo.
- **Alertas de ruptura** — cálculo automático de "Dias até Ruptura" por produto, com semáforo de risco (🔴/🟡/🟢) baseado no lead time individual de cada produto.

### 3. Dashboard Financeiro Executivo

O dashboard apresenta **duas perspetivas financeiras independentes**, cada uma com os seus próprios KPIs de Faturação, Custos Operacionais, Resultado Líquido e Receita por Colaborador — todos formatados no padrão português (`1.234.567,89 €`).

#### Visão Real (mês em curso)
Reflete o dinheiro **efetivamente movimentado** no mês atual:

| Componente | Cálculo |
|---|---|
| Faturação Real | Soma das saídas de stock × preço de venda registadas no mês |
| Custo de Pessoal | `salário + encargos (23,75%) + horas extra (× 1,5)` por colaborador |
| Custo de Mercadoria | Soma das entradas de stock × preço de compra registadas no mês |
| Resultado Líquido | `Faturação − Custo Pessoal − Custo Mercadoria` |

> ⚠️ **Por que o Resultado Real pode aparecer negativo?**  
> Num mês em que a empresa faz grandes compras de stock (reposição de armazém), o custo de mercadoria registado é elevado, mas as vendas correspondentes só se materializam nos meses seguintes. É um fenómeno contabilístico normal em gestão de inventário: o dinheiro foi investido em stock, não perdido. O sistema inclui um aviso explicativo diretamente no painel.

#### Visão Estimada (projeção mensal estável)
Reflete o **potencial de receita** esperado com base no ritmo regular de vendas cadastrado:

| Componente | Cálculo |
|---|---|
| Faturação Estimada | `vendas_mensais × preço_venda` por produto |
| Custo de Pessoal | Igual à Visão Real (custo fixo mensal calculado) |
| Custo de Mercadoria | `vendas_mensais × preço_compra` por produto |
| Resultado Líquido | `Faturação − Custo Pessoal − Custo Mercadoria` |

> 💡 **Como interpretar as duas visões em conjunto?**  
> Se a Visão Real mostra prejuízo mas a Visão Estimada mostra lucro, a empresa está saudável: apenas realizou compras de stock acima do normal neste mês. O gestor deve comparar as duas para distinguir entre **problema real de margem** (ambas negativas) e **investimento pontual em inventário** (só a Real negativa).

**Outros indicadores do dashboard:**
- **Giro de Capital** — valor total empatado em armazém (`quantidade × preço_compra`) e Top 3 produtos mais rentáveis por margem.
- **Risco de Turnover** — custo latente total previsto (`salário × 2` por colaborador em risco), representando o custo estimado de substituição se esses colaboradores saírem.

### 4. Inteligência Artificial (Machine Learning)

#### Modelo 1 — Risco de Saída de Funcionários (`ml_funcionarios.py`)

Calcula um **índice de risco contínuo** (0–100) para cada colaborador ativo. A variável‑alvo é determinada pela seguinte fórmula de negócio:

```
risco_real = (100 − assiduidade)   × 0.30
           + (100 − produtividade) × 0.30
           + (100 − satisfação)    × 0.30
           + horas_extra           × 0.10
```

Onde cada métrica é calculada da seguinte forma:

| Métrica | Fórmula |
|---|---|
| Assiduidade (%) | `(dias_úteis − faltas) / dias_úteis × 100` |
| Produtividade (%) | `metas_concluídas / metas_atribuídas × 100` |
| Satisfação (%) | `nota_satisfação / 5 × 100` |
| Horas Extra | Valor absoluto mensal declarado |

Antes de aplicar a regressão, o script verifica se os dados têm variação suficiente:
- Se todas as métricas forem iguais entre colaboradores, usa o **valor direto** (sem ML, evitando divisão por zero no escalonamento).
- Se há variação, a **Regressão Linear** (scikit-learn) com `MinMaxScaler` aprende a mapear as 4 features normalizadas para o índice de risco, suavizando o resultado.

O valor final é gravado no campo `risco_saida` na base de dados.

#### Modelo 2 — Previsão de Ruptura de Stock (`ml_stock.py`)

Utiliza uma lógica determinística de gestão de inventário (sem regressão estatística), baseada no **lead time real** de cada produto:

```
vendas_diárias  = vendas_mensais / 30
dias_stock      = quantidade_atual / vendas_diárias
margem          = dias_stock − tempo_reposicao
```

A escala de risco é mapeada pela margem disponível face ao lead time:

| Condição | Risco Previsto |
|---|---|---|
| `margem ≤ 0` | 100 % — ruptura iminente ou já em falta |
| `0 < margem ≤ tempo_reposicao` | 75 % a 100 % — stock insuficiente para cobrir a encomenda |
| `tempo_reposicao < margem ≤ 2× tempo_reposicao` | 40 % a 75 % — margem de segurança reduzida |
| `margem > 2× tempo_reposicao` | 0 % a 40 % — situação confortável |

> Esta abordagem determinística é propositada: a ruptura de stock tem uma resposta física exata (o stock acaba quando o consumo o esgota), pelo que um modelo estatístico introduziria ruído desnecessário em vez de aumentar a fiabilidade dos alertas.

---

## Arquitetura do Pipeline

```
dados.xlsx
    │
    ▼
[setup_db.py]   ─── Garante que a BD MySQL e todas as tabelas existem
    │
    ▼
[sync.py]       ─── Excel → MySQL, sentido único (modo streaming read-only, só insere/atualiza o necessário)
    │
    ▼
[orq.py: recalcular_financeiros()]   ─── Garante consistência financeira (RH)
[orq.py: recalcular_financeiros_stock()] ─── Garante consistência financeira (Stock)
    │
    ▼
[ml_funcionarios.py]   ─── IA: Risco de saída → atualiza funcionarios.risco_saida
[ml_stock.py]          ─── IA: Ruptura de stock → atualiza stock.previsao_ruptura
    │
    ▼
[app.py]   ─── Portal Streamlit (painel interativo do utilizador)
```

### Ficheiros do Projeto

| Ficheiro | Função |
|---|---|
| `app.py` | Interface visual interativa (Streamlit) |
| `orq.py` | Orquestrador do pipeline completo |
| `sync.py` | Sincronização Excel -> MySQL |
| `setup_db.py` | Criação/verificação automática da base de dados |
| `conect.py` | Configuração centralizada da ligação MySQL |
| `ml_funcionarios.py` | Modelo ML — risco de saída de colaboradores |
| `ml_stock.py` | Modelo ML — previsão de ruptura de inventário |
| `dados.xlsx` | Fonte de dados inicial (alimenta o pipeline) |
| `dados.xlsm` | Versão ligada ao MySQL |

---

## Pré-requisitos

- **Python 3.8+**
- **MySQL Server** a correr localmente (XAMPP, WAMP ou instalação nativa)

### Instalar Dependências

```bash
pip install streamlit pandas mysql-connector-python scikit-learn openpyxl
```

### Configurar a Ligação à Base de Dados

Edite o ficheiro `conect.py` com as suas credenciais MySQL:

```python
DB_CONFIG = dict(
    host="localhost",
    user="root",
    password="SUA_SENHA_AQUI",
    database="sige_db"
)
```

---

## Como Executar

### Opção A — Pipeline Completo (Recomendado)

Executa setup da BD, sincronização, recálculo financeiro, modelos de IA e abre o portal:

```bash
python orq.py
```

### Opção B — Apenas o Portal (sem re-sincronizar)

Se a BD já estiver atualizada:

```bash
streamlit run app.py
```

### Flags do Orquestrador

| Flag | Ação |
|---|---|
| `python orq.py` | Pipeline completo + abre portal |
| `python orq.py --sem-portal` | Atualiza tudo mas não abre o portal |
| `python orq.py --so-sync` | Apenas sincroniza Excel → MySQL |
| `python orq.py --so-ml` | Apenas corre os dois modelos de IA |
| `python orq.py --so-ml-func` | Apenas IA de funcionários |
| `python orq.py --so-ml-stock` | Apenas IA de stock |

O portal fica disponível em: **http://localhost:8501**

---

## Tecnologias Utilizadas

| Tecnologia | Uso |
|---|---|
| Python 3 | Linguagem principal |
| Streamlit | Interface web interativa |
| MySQL | Base de dados relacional |
| Pandas | Manipulação e análise de dados |
| scikit-learn | Modelos de Machine Learning |
| OpenPyXL | Leitura/escrita de ficheiros Excel |
| Excel (xlsm) | Fase 1 — protótipo com fórmulas automáticas |