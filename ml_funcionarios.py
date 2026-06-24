import sys
import warnings
import numpy as np
warnings.filterwarnings("ignore")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from conect import get_connection
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler


print("A iniciar IA: Previsão de Saída de Funcionários...")

# 1. Ler dados do MySQL
conn = get_connection()
query = "SELECT id, nome, assiduidade, produtividade, satisfacao, horas_extra FROM funcionarios WHERE ativo = 1"
df = pd.read_sql(query, conn)

if df.empty:
    print("⚠️  Sem funcionários ativos. Nada a fazer.")
    conn.close()
    sys.exit(0)

# 2. Limpeza robusta de NaN:
#    - horas_extra NULL → 0 (funcionário sem horas extra registadas)
#    - restantes → 100 (valor padrão máximo, sem falta de dados)
df["horas_extra"]   = pd.to_numeric(df["horas_extra"],   errors="coerce").fillna(0.0)
df["assiduidade"]   = pd.to_numeric(df["assiduidade"],   errors="coerce").fillna(100.0)
df["produtividade"] = pd.to_numeric(df["produtividade"], errors="coerce").fillna(100.0)
df["satisfacao"]    = pd.to_numeric(df["satisfacao"],    errors="coerce").fillna(100.0)

# 3. Cálculo analítico do risco real (escala 0-100)
#    100% em tudo e 0 horas extra → risco = 0
#    0% em tudo e 100 horas extra → risco = 100
df["risco_real"] = (
    (100 - df["assiduidade"])   * 0.3 +
    (100 - df["produtividade"]) * 0.3 +
    (100 - df["satisfacao"])    * 0.3 +
    df["horas_extra"].clip(upper=100) * 0.1
).clip(0, 100)

# 4. Verificar se há variação suficiente para usar ML
#    (se todos os funcionários têm métricas iguais, o MinMaxScaler divide por zero)
features = ["assiduidade", "produtividade", "satisfacao", "horas_extra"]
X = df[features].copy()
variancia_total = float(X.std().fillna(0).sum())

if variancia_total < 1e-6:
    # Todos iguais → usa directamente o valor analítico (correcto e limpo)
    print("ℹ️  Todos os funcionários têm métricas iguais. A usar fórmula directa (sem ML).")
    predicoes = df["risco_real"].values
else:
    # Dados variados → treinar e prever com ML
    scaler    = MinMaxScaler()
    X_scaled  = scaler.fit_transform(X)
    model     = LinearRegression()
    model.fit(X_scaled, df["risco_real"])
    predicoes = model.predict(X_scaled)

# 5. Garantir intervalo [0, 100]
predicoes = np.clip(predicoes, 0, 100)

# 6. Atualizar o MySQL
cursor = conn.cursor()
for funcionario_id, risco in zip(df["id"], predicoes):
    cursor.execute(
        "UPDATE funcionarios SET risco_saida = %s WHERE id = %s",
        (float(round(risco, 2)), int(funcionario_id))
    )
conn.commit()
cursor.close()
conn.close()
print("✅ SQL atualizado.")
