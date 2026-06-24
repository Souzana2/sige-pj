import sys
import warnings
warnings.filterwarnings("ignore")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from conect import get_connection
import pandas as pd


print("A iniciar IA: Previsão de Ruptura de Stock...")

# 1. Ler dados incluindo tempo_reposicao
conn = get_connection()
query = "SELECT id, produto, quantidade_atual, vendas_mensais, tempo_reposicao FROM stock WHERE ativo = 1"
df = pd.read_sql(query, conn)

# Preencher NaN com 0
df = df.fillna(0)

# 2. Calcular dias de stock disponível
#    dias_stock = quanto tempo o stock atual dura com o ritmo de vendas atual
df["vendas_diarias"] = df["vendas_mensais"] / 30.0
df["dias_stock"] = df.apply(
    lambda r: r["quantidade_atual"] / r["vendas_diarias"] if r["vendas_diarias"] > 0 else 999.0,
    axis=1
)

# 3. Margem = dias_stock - tempo_reposicao
#    Positivo: ainda há margem antes de precisar repor
#    Zero ou negativo: já está em ruptura ou iminente
df["margem_dias"] = df["dias_stock"] - df["tempo_reposicao"]

# 4. Cálculo do risco (0=seguro, 100=ruptura certa)
#    Baseia-se em quantas vezes o lead time cabe na margem disponível
def calc_risco(row):
    margem = row["margem_dias"]
    lead   = max(float(row["tempo_reposicao"]), 1.0)
    if margem <= 0:
        return 100.0                                              # Em ruptura
    elif margem <= lead:
        return round(75.0 + (1.0 - margem / lead) * 25.0, 2)    # 75-100: alto
    elif margem <= 2 * lead:
        return round(40.0 + (1.0 - (margem - lead) / lead) * 35.0, 2)  # 40-75: médio
    else:
        return round(max(0.0, 40.0 - (margem - 2 * lead) / lead * 20.0), 2)  # 0-40: baixo

df["risco_real"] = df.apply(calc_risco, axis=1).clip(0, 100)
predicoes = df["risco_real"].values

# 5. Atualizar MySQL
cursor = conn.cursor()
for produto_id, risco in zip(df["id"], predicoes):
    query = "UPDATE stock SET previsao_ruptura = %s WHERE id = %s"
    cursor.execute(query, (float(risco), int(produto_id)))
conn.commit()
cursor.close()
conn.close()
print("✅ SQL atualizado.")