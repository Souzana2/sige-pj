"""
setup_db.py - GARANTIA DE BASE DE DADOS E TABELAS
Verifica se a base de dados 'sige_db' existe e, caso nao exista,
cria-a do zero com todas as tabelas necessarias, assim como as 
colunas pertencentes.
"""

import mysql.connector
from conect import BASE_DB_CONFIG, DB_NAME

# ──────────────────────────────────────────────────────────────
# DDL DE CADA TABELA  (CREATE TABLE IF NOT EXISTS)
# ──────────────────────────────────────────────────────────────
TABELAS = {
    # ── 1. Funcionários ────────────────────────────────────────
    "funcionarios": """
        CREATE TABLE IF NOT EXISTS funcionarios (
            id                   INT AUTO_INCREMENT PRIMARY KEY,
            nome                 VARCHAR(255),
            data_nascimento      DATE,
            departamento         VARCHAR(100),
            cargo                VARCHAR(100),
            data_admissao        DATE,
            salario              FLOAT DEFAULT 0,
            horas_extra          FLOAT DEFAULT 0,
            assiduidade          FLOAT DEFAULT 100,
            produtividade        FLOAT DEFAULT 100,
            satisfacao           FLOAT DEFAULT 100,
            avaliacao_desempenho FLOAT DEFAULT 100,
            ativo                TINYINT DEFAULT 1,
            risco_saida          FLOAT DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # ── 2. Financeiro dos Funcionários ─────────────────────────
    "financeiro_funcionarios": """
        CREATE TABLE IF NOT EXISTS financeiro_funcionarios (
            id                      INT AUTO_INCREMENT PRIMARY KEY,
            id_funcionario          INT,
            salario                 FLOAT DEFAULT 0,
            custo_horas_extra       FLOAT DEFAULT 0,
            encargos                FLOAT DEFAULT 0,
            custo_total_mensal      FLOAT DEFAULT 0,
            custo_turnover_previsto FLOAT DEFAULT 0,
            UNIQUE KEY uq_funcionario (id_funcionario),
            FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # ── 3. Stock ───────────────────────────────────────────────
    "stock": """
        CREATE TABLE IF NOT EXISTS stock (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            produto          VARCHAR(255),
            categoria        VARCHAR(100),
            quantidade_atual INT DEFAULT 0,
            vendas_mensais   INT DEFAULT 0,
            reposicoes       INT DEFAULT 0,
            preco_compra     FLOAT DEFAULT 0,
            preco_venda      FLOAT DEFAULT 0,
            stock_minimo     INT DEFAULT 0,
            tempo_reposicao  INT DEFAULT 0,
            previsao_ruptura FLOAT DEFAULT 0,
            ativo            TINYINT DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # ── 4. Financeiro do Stock ─────────────────────────────────
    "financeiro": """
        CREATE TABLE IF NOT EXISTS financeiro (
            id                 INT AUTO_INCREMENT PRIMARY KEY,
            id_produto         INT UNIQUE,
            preco_compra       FLOAT DEFAULT 0,
            preco_venda        FLOAT DEFAULT 0,
            vendas_mensais     INT DEFAULT 0,
            faturamento_mensal FLOAT DEFAULT 0,
            custo_mensal       FLOAT DEFAULT 0,
            lucro_mensal       FLOAT DEFAULT 0,
            margem_lucro       FLOAT DEFAULT 0,
            giro_capital       FLOAT DEFAULT 0,
            FOREIGN KEY (id_produto) REFERENCES stock(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # ── 5. Movimentações (Histórico de Stock) ──────────────────
    "movimentacoes": """
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            id_produto INT,
            tipo_movimento ENUM('Entrada', 'Saída') NOT NULL,
            quantidade INT NOT NULL,
            preco_unitario FLOAT NOT NULL,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            observacao VARCHAR(255),
            FOREIGN KEY (id_produto) REFERENCES stock(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # ── 6. Pagamentos a Funcionários ──────────────────────────
    "pagamentos_funcionarios": """
        CREATE TABLE IF NOT EXISTS pagamentos_funcionarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            id_funcionario INT,
            tipo_pagamento ENUM('Salário', 'Bónus', 'Adiantamento', 'Outro') NOT NULL,
            valor FLOAT NOT NULL,
            data_pagamento DATE NOT NULL,
            observacao VARCHAR(255),
            FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
}

# Ordem de criação respeita as FK (pai antes de filho)
ORDEM_CRIACAO = ["funcionarios", "financeiro_funcionarios", "stock", "financeiro", "movimentacoes", "pagamentos_funcionarios"]

# ──────────────────────────────────────────────────────────────
# COLUNAS OBRIGATÓRIAS POR TABELA
# Formato: { "tabela": [("coluna", "definicao_sql"), ...] }
# Usado para corrigir tabelas já existentes que estejam incompletas.
# ──────────────────────────────────────────────────────────────
COLUNAS_OBRIGATORIAS = {
    "funcionarios": [
        ("ativo",                "TINYINT DEFAULT 1"),
        ("risco_saida",          "FLOAT DEFAULT 0"),
        ("avaliacao_desempenho", "FLOAT DEFAULT 100"),
        ("horas_extra",          "FLOAT DEFAULT 0"),
        ("assiduidade",          "FLOAT DEFAULT 100"),
        ("produtividade",        "FLOAT DEFAULT 100"),
        ("satisfacao",           "FLOAT DEFAULT 100"),
    ],
    "stock": [
        ("ativo",            "TINYINT DEFAULT 1"),
        ("previsao_ruptura", "FLOAT DEFAULT 0"),
        ("reposicoes",       "INT DEFAULT 0"),
        ("stock_minimo",     "INT DEFAULT 0"),
        ("tempo_reposicao",  "INT DEFAULT 0"),
        ("preco_compra",     "FLOAT DEFAULT 0"),
        ("preco_venda",      "FLOAT DEFAULT 0"),
    ],
    "financeiro_funcionarios": [
        ("custo_turnover_previsto", "FLOAT DEFAULT 0"),
        ("custo_total_mensal",      "FLOAT DEFAULT 0"),
        ("encargos",                "FLOAT DEFAULT 0"),
        ("custo_horas_extra",       "FLOAT DEFAULT 0"),
    ],
}


# ──────────────────────────────────────────────────────────────
# HELPER: verificar e adicionar colunas em falta
# ──────────────────────────────────────────────────────────────
def _migrar_colunas(cursor, db_name):
    """
    Para cada tabela em COLUNAS_OBRIGATORIAS, verifica se as colunas
    existem e, se nao existirem, adiciona-as via ALTER TABLE.
    """
    for tabela, colunas in COLUNAS_OBRIGATORIAS.items():
        for coluna, definicao in colunas:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME   = %s
                  AND COLUMN_NAME  = %s
            """, (db_name, tabela, coluna))
            existe = cursor.fetchone()[0]

            if not existe:
                sql_alter = f"ALTER TABLE `{tabela}` ADD COLUMN `{coluna}` {definicao};"
                cursor.execute(sql_alter)
                print(f"   [MIGR] Coluna '{coluna}' adicionada a '{tabela}'.")


# ──────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ──────────────────────────────────────────────────────────────
def garantir_db():
    """
    Garante que a base de dados e todas as tabelas existem,
    e que as colunas obrigatorias estao presentes.
    Retorna True se tudo ok, False se houve erro.
    """
    try:
        # 1. Liga SEM especificar base de dados (para poder cria-la)
        conn = mysql.connector.connect(**BASE_DB_CONFIG)
        cursor = conn.cursor()

        # 2. Cria a BD se nao existir
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        print(f"   [DB] Base de dados '{DB_NAME}' verificada/criada com sucesso.")

        # 3. Selecciona a BD
        cursor.execute(f"USE `{DB_NAME}`;")

        # 4. Cria cada tabela se nao existir
        for nome_tabela in ORDEM_CRIACAO:
            ddl = TABELAS[nome_tabela]
            cursor.execute(ddl)
            print(f"   [DB] Tabela '{nome_tabela}' verificada/criada com sucesso.")

        # 5. Migra colunas em falta em tabelas ja existentes
        _migrar_colunas(cursor, DB_NAME)

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"   [ERRO CRITICO] Nao foi possivel garantir a base de dados: {e}")
        return False


# Permite correr directamente para teste
if __name__ == "__main__":
    ok = garantir_db()
    if ok:
        print("\n[OK] Setup da base de dados concluido!")
    else:
        print("\n[ERRO] Falha no setup. Verifica as credenciais em setup_db.py.")