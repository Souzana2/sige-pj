from conect import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Adicionamos as duas colunas diretamente à tabela stock!
    cursor.execute("ALTER TABLE stock ADD COLUMN preco_compra FLOAT DEFAULT 0.0;")
    cursor.execute("ALTER TABLE stock ADD COLUMN preco_venda FLOAT DEFAULT 0.0;")
    conn.commit()
    
    print("✅ Sucesso! Colunas 'preco_compra' e 'preco_venda' adicionadas ao Stock.")
    
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()