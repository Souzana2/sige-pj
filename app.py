import streamlit as st
import pandas as pd
import subprocess
import sys
import time
import datetime
from conect import get_connection

st.set_page_config(page_title="SIGE Admin", page_icon="⚙️", layout="wide")
st.title("⚙️ SIGE - Painel de Administração")
st.divider()

# ==========================================
# FUNÇÃO DE CARREGAMENTO
# ==========================================

def carregar_funcionarios():
    conn = get_connection()
    # 💡 Repare aqui: Adicionei o fin.custo_turnover_previsto mesmo antes do risco
    query = """
    SELECT f.id, f.nome, f.departamento, f.cargo, f.salario, 
           fin.custo_total_mensal, fin.custo_turnover_previsto, f.risco_saida
    FROM funcionarios f
    LEFT JOIN financeiro_funcionarios fin ON f.id = fin.id_funcionario
    WHERE f.ativo = 1
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if 'risco_saida' in df.columns:
        df['risco_saida'] = df['risco_saida'].fillna(0).round(0).astype(int)
        
    df['Desligar'] = False 
    return df


def carregar_stock():
    conn = get_connection()
    # 💡 Repare aqui: Adicionei a previsao_ruptura no final
    query = """
    SELECT id, produto, categoria, quantidade_atual, vendas_mensais, 
           preco_compra, preco_venda, previsao_ruptura
    FROM stock
    WHERE ativo = 1
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if 'previsao_ruptura' in df.columns:
        df['previsao_ruptura'] = df['previsao_ruptura'].fillna(0).round(0).astype(int)
        
    df['Desligar'] = False 
    return df

tab_func, tab_stock, tab_dash = st.tabs(["👥 Funcionários", "📦 Stock", "📈 Dashboard Financeiro"])
with tab_func:
    
    # ==========================================
    # 1º ANDAR: REGISTAR (Mantido limpo como gostou)
    # ==========================================
    with st.expander("➕ Registar Novo Funcionário"):
        with st.form("form_novo_func", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome = st.text_input("Nome Completo *")
                data_nascimento = st.date_input(
                    "Data de Nascimento",
                    min_value=datetime.date(1930, 1, 1),
                    max_value=datetime.date.today(),
                    value=datetime.date(1995, 1, 1)
                )
                data_admissao = st.date_input("Data de Admissão *", format="DD/MM/YYYY")
            with col2:
                departamento = st.text_input("Departamento")
                cargo = st.text_input("Cargo")
                salario = st.number_input("Salário Mensal (€) *", min_value=0.0, step=50.0)
                horas_extra = st.number_input("Horas Extra (mensais)", min_value=0.0, step=1.0, value=0.0)
            with col3:
                st.caption("📋 Avaliação de Desempenho")
                st.caption("Os % são calculados automaticamente.")
                reg_dias   = st.number_input("Dias Úteis no Mês",      min_value=1,  max_value=31, step=1, value=22)
                reg_faltas = st.number_input("Faltas",                  min_value=0,  max_value=31, step=1, value=0)
                reg_m_atr  = st.number_input("Metas Atribuídas",        min_value=1,  step=1, value=10)
                reg_m_con  = st.number_input("Metas Concluídas",        min_value=0,  step=1, value=10)
                reg_nota   = st.select_slider("Nota Satisfação (1-5)",  options=[1,2,3,4,5], value=5)
                reg_gest   = st.select_slider("Avaliação Gestor (1-5)", options=[1,2,3,4,5], value=5)

            if st.form_submit_button("✅ Guardar Novo Funcionário"):
                if nome == "" or salario <= 0:
                    st.warning("⚠️ O Nome e o Salário são obrigatórios!")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()

                        # Calcula percentagens a partir dos dados brutos do guia
                        assiduidade          = round(max(0.0, (reg_dias - reg_faltas) / reg_dias * 100), 2) if reg_dias > 0 else 100.0
                        produtividade        = round(reg_m_con / reg_m_atr * 100, 2) if reg_m_atr > 0 else 100.0
                        satisfacao           = round(reg_nota / 5 * 100, 2)
                        avaliacao_desempenho = round(reg_gest / 5 * 100, 2)

                        sql_func = """INSERT INTO funcionarios
                                      (nome, data_nascimento, data_admissao, departamento, cargo,
                                       salario, horas_extra, assiduidade, produtividade, satisfacao,
                                       avaliacao_desempenho, ativo)
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)"""
                        cursor.execute(sql_func, (nome, data_nascimento, data_admissao, departamento, cargo,
                                                  salario, horas_extra, assiduidade, produtividade, satisfacao,
                                                  avaliacao_desempenho))

                        novo_id = cursor.lastrowid
                        valor_hora = salario / 160
                        custo_he   = horas_extra * valor_hora * 1.5
                        encargos   = round(salario * 0.2375, 2)
                        custo_total = round(salario + encargos + custo_he, 2)
                        turnover    = round(salario * 2, 2)

                        sql_fin = """INSERT INTO financeiro_funcionarios
                                     (id_funcionario, salario, custo_horas_extra, encargos,
                                      custo_total_mensal, custo_turnover_previsto)
                                     VALUES (%s, %s, %s, %s, %s, %s)"""
                        cursor.execute(sql_fin, (novo_id, salario, custo_he, encargos, custo_total, turnover))
                        conn.commit()
                        st.success("✅ Guardado com sucesso!")
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

    # ==========================================
    # NOVO ANDAR: AVALIAÇÕES E NOTAS OBTIDAS
    # ==========================================
    st.subheader("📊 Notas e Avaliações Obtidas")
    try:
        conn = get_connection()
        df_av = pd.read_sql("""
            SELECT nome, assiduidade, produtividade, satisfacao, avaliacao_desempenho, risco_saida
            FROM funcionarios WHERE ativo = 1
        """, conn)
        conn.close()
        
        if not df_av.empty:
            df_av_display = pd.DataFrame()
            df_av_display["Nome do Funcionário"] = df_av["nome"]
            df_av_display["Assiduidade"] = df_av["assiduidade"].map(lambda x: f"{x:.0f}%" if pd.notna(x) else "100%")
            df_av_display["Produtividade"] = df_av["produtividade"].map(lambda x: f"{x:.0f}%" if pd.notna(x) else "100%")
            df_av_display["Satisfação"] = df_av["satisfacao"].map(lambda x: f"{x:.0f}%" if pd.notna(x) else "100%")
            df_av_display["Avaliação Desempenho"] = df_av["avaliacao_desempenho"].map(lambda x: f"{x:.0f}%" if pd.notna(x) else "100%")
            
            def map_estado(risco):
                r = float(risco or 0)
                if r >= 75:
                    return "🔴 Em Risco"
                elif r >= 40:
                    return "🟡 Avaliar"
                else:
                    return "🟢 Seguro"
            
            df_av_display["Estado do Risco"] = df_av["risco_saida"].apply(map_estado)
            
            st.dataframe(df_av_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sem funcionários ativos registados.")
    except Exception as e:
        st.error(f"Erro ao carregar avaliações: {e}")

    st.write("---")
    
    # ==========================================
    # 2º ANDAR: PESQUISA E TABELA (Só de Leitura e Desligar)
    # ==========================================
    
    st.subheader("🔍 Tabela Resumo da Equipa")

    # ==========================================
    # BOTÃO DA INTELIGÊNCIA ARTIFICIAL
    # ==========================================
    if st.button("🧠 Rodar Inteligência Artificial (Recalcular Riscos)", type="primary", use_container_width=True):
        with st.spinner("A Inteligência Artificial está a analisar o comportamento da equipa... Aguarde."):
            try:
                # O Python vai rodar o seu ficheiro de ML nos bastidores!
                # Certifique-se de que o nome do ficheiro aqui está IGUAL ao que você tem no VS Code
                result = subprocess.run(
                    [sys.executable, "ml_funcionarios.py"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("✅ Previsões concluídas! A base de dados foi atualizada pela IA.")
                else:
                    st.warning(f"⚠️ ML terminou com avisos:\n{result.stderr[-300:] if result.stderr else ''}")
                time.sleep(1.5)
                st.rerun()

            except subprocess.CalledProcessError:
                st.error("❌ O ficheiro de ML deu um erro. Verifique se o código no 'ml_funcionarios.py' está a rodar bem sozinho.")
            except FileNotFoundError:
                st.error("❌ Ficheiro 'ml_funcionarios.py' não encontrado. Verifique o nome!")
    
    df_func = carregar_funcionarios()
    termo_pesquisa = st.text_input("Buscar funcionário globalmente (Nome, Cargo, etc):")
    
    if termo_pesquisa:
        filtro_global = (
            df_func['nome'].astype(str).str.contains(termo_pesquisa, case=False, na=False) |
            df_func['departamento'].astype(str).str.contains(termo_pesquisa, case=False, na=False) |
            df_func['cargo'].astype(str).str.contains(termo_pesquisa, case=False, na=False)
        )
        df_func = df_func[filtro_global]
    
    # 💡 TRANCAR TUDO EXCETO O "DESLIGAR"
    colunas_trancadas = [col for col in df_func.columns if col != 'Desligar']

    
    df_func_editado = st.data_editor(
        df_func, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="fixed",            
        disabled=colunas_trancadas,  
        key="edit_func"
    )
    
    if st.button("💾 Executar Desligamentos Selecionados", type="primary"):
        conn = get_connection()
        cursor = conn.cursor()
        for index, row in df_func_editado.iterrows():
            if row['Desligar'] == True:
                cursor.execute("UPDATE funcionarios SET ativo = 0 WHERE id = %s", (int(row['id']),))
        conn.commit()
        st.success("✅ Guardado com sucesso!")
        time.sleep(1.2) # 💡 O ecrã congela por 1.2 segundos para a pessoa ler a mensagem
        st.rerun()

    st.write("---")

    # 3º ANDAR: EDIÇÃO COMPLETA
    st.subheader("✏️ Ficha de Edição Completa")
    lista_funcionarios = df_func['id'].astype(str) + " - " + df_func['nome']
    
    # Caixa de seleção simples (sem o key=session_state)
    escolha = st.selectbox("Escolha quem deseja editar:", ["(Selecione um funcionário)"] + lista_funcionarios.tolist())

    # Só abre a janela se alguém estiver selecionado
    if escolha != "(Selecione um funcionário)":
        id_selecionado = int(escolha.split(" - ")[0])
        
        # Vai ao SQL buscar TUDO o que existe sobre esta pessoa
        conn = get_connection()
        df_perfil = pd.read_sql(f"SELECT * FROM funcionarios WHERE id = {id_selecionado}", conn)
        conn.close()
        
        if not df_perfil.empty:
            dados = df_perfil.iloc[0]
            
            with st.form("form_edicao_completa"):
                st.write(f"A editar ficha completa de: **{dados['nome']}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    novo_nome = st.text_input("Nome", value=dados['nome'])
                    # Atenção: O Python precisa de converter a data que vem do MySQL para mostrar no calendário
                    # Forma clássica, limpa e sem erros de sintaxe!
                    try:
                        if pd.notna(dados['data_nascimento']):
                            data_nasc_atual = pd.to_datetime(dados['data_nascimento']).date()
                        else:
                            data_nasc_atual = datetime.date(1995, 1, 1)
                    except:
                        data_nasc_atual = datetime.date(1995, 1, 1)
                    
                    nova_data_nasc = st.date_input(
                        "Data de Nasc.", 
                        value=data_nasc_atual,
                        min_value=datetime.date(1930, 1, 1), 
                        max_value=datetime.date.today()
                    )
                    nova_data_adm = st.date_input("Data Admissão", value=dados['data_admissao'])
                with col2:
                    novo_dep    = st.text_input("Departamento", value=dados['departamento'] if dados['departamento'] else "")
                    novo_cargo  = st.text_input("Cargo",        value=dados['cargo'] if dados['cargo'] else "")
                    novo_salario = st.number_input("Salário", value=float(dados['salario']), step=50.0)
                    novas_horas  = st.number_input("Horas Extra", min_value=0.0, value=float(dados['horas_extra'] or 0))
                with col3:
                    st.caption("📋 Avaliação de Desempenho")

                    # Percentagens actuais (para pré-calcular os campos brutos)
                    _ass = float(dados.get('assiduidade') or 100)
                    _pro = float(dados.get('produtividade') or 100)
                    _sat = float(dados.get('satisfacao') or 100)
                    _ava = float(dados.get('avaliacao_desempenho') or 100)
                    _ris = float(dados.get('risco_saida') or 0)
                    alerta_emoji = "🔴" if _ris >= 75 else ("🟡" if _ris >= 40 else "🟢")
                    alerta_txt   = "ALTO" if _ris >= 75 else ("MÉDIO" if _ris >= 40 else "BAIXO")
                    st.caption(f"{alerta_emoji} Risco de Saída (IA): **{_ris:.0f}%** — {alerta_txt}")

                    # Valores brutos inferidos a partir dos % actuais
                    _dias = 22
                    ed_dias   = st.number_input("Dias Úteis no Mês",      min_value=1, max_value=31, step=1, value=_dias)
                    ed_faltas = st.number_input("Faltas",                  min_value=0, max_value=31, step=1,
                                                value=max(0, round((1 - _ass/100) * _dias)))
                    ed_m_atr  = st.number_input("Metas Atribuídas",        min_value=1, step=1, value=10)
                    ed_m_con  = st.number_input("Metas Concluídas",        min_value=0, step=1,
                                                value=max(0, min(10, round(_pro/100 * 10))))
                    ed_nota   = st.select_slider("Nota Satisfação (1-5)",  options=[1,2,3,4,5],
                                                 value=max(1, min(5, round(_sat/100 * 5))))
                    ed_gest   = st.select_slider("Avaliação Gestor (1-5)", options=[1,2,3,4,5],
                                                 value=max(1, min(5, round(_ava/100 * 5))))

                if st.form_submit_button("💾 Guardar Todas as Alterações", type="primary"):
                    conn = get_connection()
                    cursor = conn.cursor()

                    # Calcula percentagens a partir dos dados brutos
                    nova_assiduidade   = round(max(0.0, (ed_dias - ed_faltas) / ed_dias * 100), 2) if ed_dias > 0 else 100.0
                    nova_produtividade = round(ed_m_con / ed_m_atr * 100, 2) if ed_m_atr > 0 else 100.0
                    nova_satisfacao    = round(ed_nota / 5 * 100, 2)
                    nova_avaliacao     = round(ed_gest / 5 * 100, 2)

                    sql_update = """UPDATE funcionarios
                                    SET nome=%s, data_nascimento=%s, data_admissao=%s, departamento=%s, cargo=%s,
                                        salario=%s, horas_extra=%s, assiduidade=%s, produtividade=%s,
                                        satisfacao=%s, avaliacao_desempenho=%s
                                    WHERE id=%s"""
                    cursor.execute(sql_update, (novo_nome, nova_data_nasc, nova_data_adm, novo_dep, novo_cargo,
                                                novo_salario, novas_horas, nova_assiduidade, nova_produtividade,
                                                nova_satisfacao, nova_avaliacao, id_selecionado))

                    # Recalcula Finanças
                    valor_hora  = novo_salario / 160
                    custo_he    = novas_horas * valor_hora * 1.5
                    encargos    = round(novo_salario * 0.2375, 2)
                    custo_total = round(novo_salario + encargos + custo_he, 2)
                    turnover    = round(novo_salario * 2, 2)

                    sql_fin = """UPDATE financeiro_funcionarios
                                 SET salario=%s, custo_horas_extra=%s, encargos=%s,
                                     custo_total_mensal=%s, custo_turnover_previsto=%s
                                 WHERE id_funcionario=%s"""
                    cursor.execute(sql_fin, (novo_salario, custo_he, encargos, custo_total, turnover, id_selecionado))

                    conn.commit()
                    st.session_state.id_selecionado_edit = "(Selecione um funcionário)"
                    st.success("✅ Guardado com sucesso!")
                    time.sleep(1.2)
                    st.rerun()

# --- ABA: STOCK ---
with tab_stock:
    
    # ==========================================
    # 1º ANDAR: REGISTAR NOVO PRODUTO
    # ==========================================
    with st.expander("➕ Registar Novo Produto"):

        with st.form("form_novo_stock", clear_on_submit=True):
            st.write("Introduza o novo produto. Preços e quantidades podem ficar a 0 para já.")
            col1, col2, col3 = st.columns(3)
            with col1:
                produto      = st.text_input("Nome do Produto *")
                categoria    = st.text_input("Categoria")
                preco_compra = st.number_input("Preço Compra (€)", min_value=0.0, step=0.01, value=0.0)
                preco_venda  = st.number_input("Preço Venda (€)",  min_value=0.0, step=0.01, value=0.0)
            with col2:
                st.caption("Movimentações")
                qtd_atual      = st.number_input("Quantidade em Armazém", min_value=0, step=1, value=0)
                vendas_mensais = st.number_input("Vendas Mensais (unid.)", min_value=0, step=1, value=0)
                reposicoes     = st.number_input("Reposições (unid.)",     min_value=0, step=1, value=0)
            with col3:
                st.caption("Controlo de Stock")
                stock_minimo    = st.number_input("Stock Mínimo (unid.)",       min_value=0, step=1, value=0)
                tempo_reposicao = st.number_input("Tempo Reposição (dias)",      min_value=0, step=1, value=0)

            if st.form_submit_button("✅ Adicionar ao Armazém"):
                if produto == "":
                    st.warning("⚠️ O Nome do Produto é obrigatório!")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        sql_stock = """INSERT INTO stock
                                       (produto, categoria, quantidade_atual, vendas_mensais,
                                        reposicoes, preco_compra, preco_venda,
                                        stock_minimo, tempo_reposicao, ativo)
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)"""
                        cursor.execute(sql_stock, (produto, categoria, qtd_atual, vendas_mensais,
                                                   reposicoes, preco_compra, preco_venda,
                                                   stock_minimo, tempo_reposicao))
                        conn.commit()
                        st.success("✅ Guardado com sucesso!")
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao registar: {e}")
                    finally:
                        if 'cursor' in locals(): cursor.close()
                        if 'conn' in locals(): conn.close()

    # ==========================================
    # NOVO ANDAR: ALERTAS DE RUPTURA DE STOCK
    # ==========================================
    st.subheader("📊 Alertas de Ruptura de Stock")
    try:
        conn = get_connection()
        df_stock_av = pd.read_sql("""
            SELECT produto, quantidade_atual, vendas_mensais, tempo_reposicao, previsao_ruptura
            FROM stock WHERE ativo = 1
        """, conn)
        conn.close()
        
        if not df_stock_av.empty:
            # Calcula os dias até ruptura
            def calc_dias(row):
                vendas = float(row['vendas_mensais'] or 0)
                qtd = float(row['quantidade_atual'] or 0)
                lead_time = float(row['tempo_reposicao'] or 0)
                
                vendas_diarias = vendas / 30.0
                if vendas_diarias > 0:
                    return int(round((qtd / vendas_diarias) - lead_time))
                else:
                    return 999
            
            df_stock_av["Dias até Ruptura"] = df_stock_av.apply(calc_dias, axis=1)
            
            # Mapeia o estado de risco
            def map_estado_stock(risco):
                r = float(risco or 0)
                if r >= 75:
                    return "🔴 Em Risco"
                elif r >= 40:
                    return "🟡 Avaliar"
                else:
                    return "🟢 Seguro"
            
            df_stock_av["Estado do Risco"] = df_stock_av["previsao_ruptura"].apply(map_estado_stock)
            
            # Ordena por risco descendente (mais crítico primeiro) e dias até ruptura ascendente
            df_stock_av = df_stock_av.sort_values(by=["previsao_ruptura", "Dias até Ruptura"], ascending=[False, True])
            
            # Seleciona apenas as colunas pedidas
            df_stock_display = df_stock_av[["produto", "Dias até Ruptura", "Estado do Risco"]].copy()
            df_stock_display.columns = ["Nome do Produto", "Dias até Ruptura", "Estado do Risco"]
            
            # Coloração vermelha para dias negativos usando Pandas Styler
            def color_dias_negativos(val):
                if isinstance(val, (int, float)) and val < 0:
                    return 'color: red; font-weight: bold;'
                return ''
            
            st.dataframe(
                df_stock_display.style.map(color_dias_negativos, subset=["Dias até Ruptura"]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem produtos ativos no inventário.")
    except Exception as e:
        st.error(f"Erro ao carregar alertas de stock: {e}")

    st.write("---")
    
    # ==========================================
    # 2º ANDAR: PESQUISA E TABELA RESUMO
    # ==========================================
    st.subheader("📦 Visão Geral do Armazém")
    # ==========================================
    # BOTÃO DA INTELIGÊNCIA ARTIFICIAL (STOCK)
    # ==========================================
    if st.button("🧠 Rodar Inteligência Artificial (Prever Rupturas)", type="primary", use_container_width=True, key="btn_ml_stock"):
        with st.spinner("A Inteligência Artificial está a analisar as vendas e quantidades no armazém... Aguarde."):
            try:
                # ⚠️ ATENÇÃO AQUI: Substitua "ml_stock.py" pelo nome exato do seu ficheiro Python de IA do Stock!
                result_ml = subprocess.run(
                    [sys.executable, "ml_stock.py"],
                    capture_output=True, text=True
                )
                if result_ml.returncode == 0:
                    st.success("✅ Previsões de Ruptura atualizadas com sucesso na base de dados!")
                else:
                    st.warning(f"⚠️ ML Stock terminou com avisos:\n{result_ml.stderr[-300:] if result_ml.stderr else ''}")
                time.sleep(1.5)
                st.rerun()

            except subprocess.CalledProcessError:
                st.error("❌ O modelo de IA do Stock deu um erro interno. Verifique se ele roda bem sozinho.")
            except FileNotFoundError:
                st.error("❌ Ficheiro não encontrado! Escreveu o nome correto dentro do comando subprocess.run?")
    
    try:
        df_stock = carregar_stock()
        termo_pesquisa_stock = st.text_input("Buscar produto (Nome ou Categoria):")
        
        if termo_pesquisa_stock:
            filtro_stock = (
                df_stock['produto'].astype(str).str.contains(termo_pesquisa_stock, case=False, na=False) |
                df_stock['categoria'].astype(str).str.contains(termo_pesquisa_stock, case=False, na=False)
            )
            df_stock = df_stock[filtro_stock]
        
        colunas_trancadas_stock = [col for col in df_stock.columns if col != 'Desligar']
        
        df_stock_editado = st.data_editor(
            df_stock, 
            use_container_width=True, 
            hide_index=True, 
            num_rows="fixed",            
            disabled=colunas_trancadas_stock,  
            key="edit_stock"
        )
        
        if st.button("💾 Executar Remoções de Catálogo", type="primary"):
            conn = get_connection()
            cursor = conn.cursor()
            for index, row in df_stock_editado.iterrows():
                if row['Desligar'] == True:
                    cursor.execute("UPDATE stock SET ativo = 0 WHERE id = %s", (int(row['id']),))
            conn.commit()
            st.success("✅ Guardado com sucesso!")
            time.sleep(1.2) # 💡 O ecrã congela por 1.2 segundos para a pessoa ler a mensagem
            st.rerun()
            
    except Exception as e:
        st.error(f"Erro na tabela: {e}")

    st.write("---")

    # ==========================================
    # 3º ANDAR: EDIÇÃO COMPLETA DE PRODUTO
    # ==========================================
    st.subheader("✏️ Atualizar Ficha do Produto")
    
    try:
        lista_produtos = df_stock['id'].astype(str) + " - " + df_stock['produto']
        escolha_prod = st.selectbox("Escolha o produto para atualizar:", ["(Selecione um produto)"] + lista_produtos.tolist())

        if escolha_prod != "(Selecione um produto)":
            id_prod_selecionado = int(escolha_prod.split(" - ")[0])

            # Vai buscar todos os campos do produto directamente à BD
            conn_ed = get_connection()
            df_perfil_prod = pd.read_sql(
                f"SELECT * FROM stock WHERE id = {id_prod_selecionado}", conn_ed
            )
            conn_ed.close()

            if not df_perfil_prod.empty:
                dados_prod = df_perfil_prod.iloc[0]

                with st.form("form_edicao_stock"):
                    st.write(f"A atualizar: **{dados_prod['produto']}**")

                    colA, colB, colC = st.columns(3)
                    with colA:
                        novo_nome_prod = st.text_input("Nome", value=str(dados_prod['produto']))
                        nova_cat       = st.text_input("Categoria", value=str(dados_prod['categoria']) if pd.notna(dados_prod['categoria']) else "")
                        novo_preco_c   = st.number_input("Preço Compra (€)", min_value=0.0, step=0.01, value=float(dados_prod['preco_compra'] or 0))
                        novo_preco_v   = st.number_input("Preço Venda (€)",  min_value=0.0, step=0.01, value=float(dados_prod['preco_venda'] or 0))
                    with colB:
                        st.caption("Movimentações")
                        nova_qtd      = st.number_input("Qtd Atual",            min_value=0, step=1, value=int(dados_prod['quantidade_atual'] or 0))
                        novas_vendas  = st.number_input("Vendas Mensais",       min_value=0, step=1, value=int(dados_prod['vendas_mensais'] or 0))
                        novas_repos   = st.number_input("Reposições (unid.)",   min_value=0, step=1, value=int(dados_prod['reposicoes'] or 0))
                    with colC:
                        st.caption("Controlo de Stock")
                        novo_stock_min  = st.number_input("Stock Mínimo (unid.)",   min_value=0, step=1, value=int(dados_prod['stock_minimo'] or 0))
                        novo_tempo_rep  = st.number_input("Tempo Reposição (dias)", min_value=0, step=1, value=int(dados_prod['tempo_reposicao'] or 0))

                    if st.form_submit_button("💾 Guardar e Atualizar Stock", type="primary"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        sql_upd_stock = """UPDATE stock
                                           SET produto=%s, categoria=%s, quantidade_atual=%s,
                                               vendas_mensais=%s, reposicoes=%s,
                                               preco_compra=%s, preco_venda=%s,
                                               stock_minimo=%s, tempo_reposicao=%s
                                           WHERE id=%s"""
                        cursor.execute(sql_upd_stock, (
                            novo_nome_prod, nova_cat, nova_qtd,
                            novas_vendas, novas_repos,
                            novo_preco_c, novo_preco_v,
                            novo_stock_min, novo_tempo_rep,
                            id_prod_selecionado
                        ))
                        conn.commit()
                        st.success("✅ Guardado com sucesso!")
                        time.sleep(1.2)
                        st.rerun()
    except Exception as e:
        st.error(f"Erro ao processar edição: {e}")

# ==========================================
# --- ABA: DASHBOARD FINANCEIRO ---
# ==========================================
with tab_dash:
    st.header("📈 Saúde Financeira e Dashboard Executivo")
    st.write("Visão global cruzando os Custos de Recursos Humanos com a Faturação de Armazém.")
    
    try:
        # 1. Carregar as duas tabelas
        df_f = carregar_funcionarios()
        df_s = carregar_stock()
        
        # 2. Limpar valores nulos para as contas não darem erro
        df_s.fillna(0, inplace=True)
        df_f.fillna(0, inplace=True)
        
        # 3. A MATEMÁTICA FINANCEIRA
        # -- Receitas --
        faturacao_mensal = (df_s['vendas_mensais'] * df_s['preco_venda']).sum()
        
        # -- Custos --
        custo_mercadoria = (df_s['vendas_mensais'] * df_s['preco_compra']).sum()
        custo_pessoal = df_f['custo_total_mensal'].sum()
        custo_total = custo_mercadoria + custo_pessoal
        
        # -- Lucro e Capital --
        lucro_estimado = faturacao_mensal - custo_total
        # Impede divisão por zero caso apague todos os funcionários
        receita_por_funcionario = faturacao_mensal / len(df_f) if len(df_f) > 0 else 0
        capital_empatado = (df_s['quantidade_atual'] * df_s['preco_compra']).sum()
        risco_turnover_total = df_f['custo_turnover_previsto'].sum()

        # 4. DESENHAR OS CARTÕES (KPIs)
        st.subheader("📊 Indicadores Principais (Mensais)")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Faturação Estimada", f"{faturacao_mensal:,.2f} €")
        col2.metric("Custos Operacionais", f"{custo_total:,.2f} €", f"Pessoal: {custo_pessoal:,.0f}€ | Matéria: {custo_mercadoria:,.0f}€", delta_color="inverse")
        col3.metric("Lucro Liquido Estimado", f"{lucro_estimado:,.2f} €", f"{'✅ Lucro' if lucro_estimado >= 0 else '🚨 Prejuízo'}")
        col4.metric("Receita per Capita", f"{receita_por_funcionario:,.2f} €", "Faturação gerada por empregado")
        
        st.write("---")

        # 5. GRÁFICOS E DETALHES
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("💰 Distribuição de Custos Reais")
            # REMOVEMOS O TURNOVER DAQUI! Fica apenas o dinheiro que sai da conta.
            df_grafico = pd.DataFrame({
                "Categoria": ["Pessoal (Salários)", "Mercadoria (Compras)"],
                "Valor (€)": [custo_pessoal, custo_mercadoria]
            }).set_index("Categoria")
            
            # Gráfico de barras simples
            st.bar_chart(df_grafico, color="#ff4b4b")
            
            # Novo bloco de Alerta de Risco para o Turnover
            st.warning(f"⚠️ **Risco Latente (Turnover):** Se os funcionários atualmente em risco de saída abandonarem a empresa, estima-se um impacto oculto de **{risco_turnover_total:,.2f} €** (Indemnizações, novas contratações e quebra de produtividade).")
            
        with colB:
            st.subheader("📦 Giro de Capital")
            st.metric("Capital Empatado em Armazém", f"{capital_empatado:,.2f} €", "Dinheiro investido no Stock atual", delta_color="off")
            
            st.write("**Top 3 Produtos que mais faturam:**")
            # Calcula quem dá mais dinheiro e mostra o Top 3
            df_s['Receita_Mensal'] = df_s['vendas_mensais'] * df_s['preco_venda']
            top_produtos = df_s.nlargest(3, 'Receita_Mensal')[['produto', 'Receita_Mensal']]
            st.dataframe(top_produtos, hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Ainda não há dados suficientes para gerar o Dashboard ou ocorreu um erro: {e}")