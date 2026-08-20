import os
os.environ["GRPC_DNS_RESOLVER"] = "native"  # ESTA É A VACINA QUE IMPEDE O FIREBASE DE TRAVAR NA NUVEM!

import streamlit as st
import pandas as pd
import altair as alt
import firebase_admin
from firebase_admin import credentials, firestore

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Gerenciador de Recursos",
    page_icon="💰",
    layout="wide"
)

# =====================================================================
# 2. CONEXÃO COM O FIREBASE (BLINDADA CONTRA TRAVAMENTOS DE REDE)
# =====================================================================
@st.cache_resource
def inicializar_banco():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"⚠️ Erro no arquivo da chave: {e}")
            st.stop()
    return firestore.client()

db = inicializar_banco()

def extrair_ano(nc_nome):
    if len(nc_nome) >= 4 and nc_nome[:4].isdigit():
        return nc_nome[:4]
    return "Outros/Sem Ano"

# Inicializa o estado da sessão do usuário
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# =====================================================================
# TELA DE LOGIN E CADASTRO (LADO A LADO - COM FORMULÁRIOS SEGUROS)
# =====================================================================
if st.session_state.usuario_logado is None:
    st.title("🖥 Sistema Profissional de Controle de Recursos")
    st.markdown("Bem-vindo! Faça login ou crie sua conta para acessar o sistema na nuvem.")
    st.markdown("---")
    
    col_login, col_divisor, col_cadastro = st.columns([4, 1, 4])
    
    with col_login:
        st.subheader("🔑 Fazer Login")
        with st.form("form_login_oficial"):
            usuario_login = st.text_input("Usuário:").strip().lower()
            senha_login = st.text_input("Senha:", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            
            if btn_login:
                if not usuario_login or not senha_login:
                    st.warning("Preencha usuário e senha.")
                else:
                    try:
                        doc = db.collection("usuarios").document(usuario_login).get()
                        if doc.exists:
                            if doc.to_dict().get("senha") == senha_login:
                                st.session_state.usuario_logado = usuario_login
                                st.success("Login realizado com sucesso! Entrando...")
                                st.rerun()
                            else:
                                st.error("Senha incorreta!")
                        else:
                            st.error("Usuário não encontrado!")
                    except Exception as e:
                        st.error(f"Erro ao conectar com o banco: {e}")
                
    with col_divisor:
        st.write("")

    with col_cadastro:
        st.subheader("📝 Criar Nova Conta")
        with st.form("form_cadastro_oficial"):
            novo_user = st.text_input("Escolha um nome de Usuário:").strip().lower()
            nova_senha = st.text_input("Crie uma Senha:", type="password")
            novo_nome = st.text_input("Seu Nome/Posto (Ex: 3º Sgt João):")
            nova_om = st.text_input("Sua Organização Militar (Ex: 23º BI):")
            
            btn_cadastrar = st.form_submit_button("Criar Conta", type="secondary", use_container_width=True)
            
            if btn_cadastrar:
                if not novo_user or not nova_senha or not novo_nome:
                    st.warning("Preencha os campos obrigatórios (Usuário, Senha e Nome).")
                else:
                    try:
                        if db.collection("usuarios").document(novo_user).get().exists:
                            st.error("Este nome de usuário já está em uso. Escolha outro.")
                        else:
                            db.collection("usuarios").document(novo_user).set({
                                "senha": nova_senha,
                                "nome": novo_nome,
                                "om": nova_om
                            })
                            db.collection("dados").document(novo_user).set({"ncs": {}})
                            st.success("✅ Conta criada com sucesso! Você já pode fazer o login ao lado.")
                    except Exception as e:
                        st.error(f"🚨 Erro de Conexão com o Firebase: {e}")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; font-size: 14px;'>Criado e Desenvolvido por:<br><b>2º Sgt Winkler</b></div>", unsafe_allow_html=True)
    st.stop()  # Impede o carregamento do resto se não estiver logado

# =====================================================================
# SISTEMA PRINCIPAL (PÓS-LOGIN)
# =====================================================================
usuario_atual = st.session_state.usuario_logado

try:
    user_doc_ref = db.collection("usuarios").document(usuario_atual).get()
    user_doc = user_doc_ref.to_dict() if user_doc_ref.exists else {}
    
    dados_doc_ref = db.collection("dados").document(usuario_atual)
    dados_banco_val = dados_doc_ref.get()
    banco_dados = dados_banco_val.to_dict().get("ncs", {}) if dados_banco_val.exists else {}
except Exception as e:
    st.error(f"Erro ao carregar dados do usuário na nuvem: {e}")
    banco_dados = {}
    user_doc = {}

def salvar_na_nuvem(novos_dados):
    try:
        db.collection("dados").document(usuario_atual).update({"ncs": novos_dados})
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")

# Sidebar
st.sidebar.title("💰 Gestão Orçamentária")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠 Estação de Trabalho")

nome_atual = st.sidebar.text_input("Nome do Gestor:", value=user_doc.get("nome", ""))
om_atual = st.sidebar.text_input("Organização Militar (OM):", value=user_doc.get("om", ""))

if nome_atual != user_doc.get("nome", "") or om_atual != user_doc.get("om", ""):
    db.collection("usuarios").document(usuario_atual).update({"nome": nome_atual, "om": om_atual})
    st.toast("Dados do perfil atualizados na nuvem!")

st.sidebar.write("")
if st.sidebar.button("Sair (Logout)"):
    st.session_state.usuario_logado = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Filtro de Exercício")
anos_disponiveis = set(extrair_ano(nc) for nc in banco_dados.keys())
lista_anos = sorted(list(anos_disponiveis), reverse=True) if anos_disponiveis else ["2026"]
ano_selecionado = st.sidebar.selectbox("Selecione o Ano de Referência:", lista_anos)
ncs_do_ano = [nc for nc in banco_dados.keys() if extrair_ano(nc) == ano_selecionado]

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>Criado e Desenvolvido por:<br><b>2º Sgt Winkler</b></div>", unsafe_allow_html=True)

# Título Principal
st.title("🖥 Sistema Profissional de Controle de Recursos e Aquisições")
st.markdown("Substitua o Excel por uma interface robusta para gerenciar Notas de Crédito (NC), planejar compras e monitorar o fluxo de entregas.")
st.markdown("---")

menu_cadastro, menu_visualizacao, menu_visao_global = st.tabs([
    "📝 Cadastrar e Lançar Compras",
    "📊 Controle Individual por NC",
    "📈 Visão Global do Ano"
])

# =====================================================================
# ABA 1: CADASTRO
# =====================================================================
with menu_cadastro:
    st.subheader("1. Cadastrar Nova Nota de Crédito (NC)")
    
    col_nc1, col_nc2, col_nc3 = st.columns(3)
    with col_nc1:
        nova_nc = st.text_input("Número da NC (Comece com o ano, ex: 2026NC000511):", "", key="cad_numero_nc").strip()
    with col_nc2:
        nova_nd = st.text_input("Natureza de Despesa (ND):", "", key="cad_nd_nc").strip()
    with col_nc3:
        valor_nc = st.number_input("Valor Total Recebido na NC (R$):", min_value=0.0, step=100.0, key="cad_valor_nc")
    
    if st.button("💾 Registrar Nova Nota de Crédito", type="primary", key="btn_cad_nc"):
        if nova_nc:
            if nova_nc not in banco_dados:
                banco_dados[nova_nc] = {"valor_recebido": valor_nc, "nd": nova_nd, "itens": []}
                salvar_na_nuvem(banco_dados)
                st.success(f"NC {nova_nc} salva com sucesso!")
                st.rerun()
            else:
                st.warning("Esta NC já existe. Use a seção abaixo para alterá-la.")
        else:
            st.warning("Por favor, digite o número da NC.")
    
    if ncs_do_ano:
        st.markdown("---")
        st.subheader("✏ Alterar Dados de uma NC Existente")
        
        nc_para_editar = st.selectbox(f"Selecione a NC ({ano_selecionado}) para alterar:", ncs_do_ano, key="editar_select_nc")
        
        dados_atuais = banco_dados[nc_para_editar]
        valor_atual = dados_atuais.get("valor_recebido", 0.0)
        nd_atual = dados_atuais.get("nd", "")
        
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            nome_editado = st.text_input("Número da NC:", value=nc_para_editar, key=f"edit_numero_nc_{nc_para_editar}").strip()
        with col_ed2:
            nd_editada = st.text_input("Natureza de Despesa (ND):", value=nd_atual, key=f"edit_nd_nc_{nc_para_editar}").strip()
        with col_ed3:
            valor_editado = st.number_input("Valor Total (R$):", value=float(valor_atual), min_value=0.0, step=100.0, key=f"edit_valor_nc_{nc_para_editar}")
        
        if st.button("🔄 Confirmar Alterações da NC", type="secondary", key="btn_edit_nc"):
            if nome_editado:
                if nome_editado != nc_para_editar and nome_editado in banco_dados:
                    st.error("Erro: Já existe outra NC cadastrada com esse novo número.")
                else:
                    dados_preservados = banco_dados.pop(nc_para_editar)
                    dados_preservados["valor_recebido"] = valor_editado
                    dados_preservados["nd"] = nd_editada
                    banco_dados[nome_editado] = dados_preservados
                    salvar_na_nuvem(banco_dados)
                    st.success(f"Dados da NC '{nome_editado}' atualizados com sucesso!")
                    st.rerun()
            else:
                st.warning("O número da NC não pode ficar em branco.")

        st.markdown("---")
        st.subheader("🚨 Deletar Nota de Crédito Inteira")
        nc_para_deletar_toda = st.selectbox(f"Selecione a NC ({ano_selecionado}) para APAGAR:", ncs_do_ano, key="nc_del_toda")
        if st.button("💥 DELETAR NC E TODOS OS ITENS", type="primary", key="btn_del_nc"):
            banco_dados.pop(nc_para_deletar_toda)
            salvar_na_nuvem(banco_dados)
            st.success(f"NC {nc_para_deletar_toda} excluída com sucesso!")
            st.rerun()

    st.markdown("---")
    st.subheader("2. Lançar Itens e Planejar Aquisição")
    
    if ncs_do_ano:
        nc_selecionada_cad = st.selectbox("Selecione a NC para vincular este item:", ncs_do_ano, key="cad_item_select_nc")
        
        col_it1, col_it2, col_it3 = st.columns(3)
        with col_it1:
            nr_item = st.number_input("Nº do Item:", min_value=1, step=1, key="item_nr")
            nome_resumido = st.text_input("Nome do Material:", "", key="item_nome").strip()
            valor_unitario = st.number_input("Valor Unitário (R$):", min_value=0.0, step=0.01, key="item_valor")
            quantidade = st.number_input("Quantidade:", min_value=0, step=1, key="item_qtd")
        with col_it2:
            nr_uasg = st.text_input("Nº da UASG:", "160440", key="item_uasg").strip()
            nr_pregao = st.text_input("Nº do Pregão / Processo:", "", key="item_pregao").strip()
            nr_ata = st.text_input("Nº da Ata:", "", key="item_ata").strip()
        with col_it3:
            fornecedor = st.text_input("Nome do Fornecedor / Empresa:", "", key="item_forn").strip()
            cnpj = st.text_input("CNPJ do Fornecedor:", "", key="item_cnpj").strip()
            situacao = st.selectbox("Situação Atual do Recurso:", [
                "Aguardando NC para chegar",
                "Aguardando entrega",
                "Recebido"
            ], key="item_sit")
        
        if st.button("➕ Adicionar Item ao Planejamento", type="primary", key="btn_add_item"):
            if nome_resumido:
                novo_item = {
                    "Item": int(nr_item), "Nome": nome_resumido, "Valor Unitário": float(valor_unitario),
                    "Qtd": int(quantidade), "Total": float(valor_unitario * quantidade), "UASG": nr_uasg,
                    "Pregão": nr_pregao, "Ata": nr_ata, "Fornecedor": fornecedor.strip().upper() if fornecedor else "NÃO INFORMADO",
                    "CNPJ": cnpj, "Situação": situacao
                }
                banco_dados[nc_selecionada_cad]["itens"].append(novo_item)
                salvar_na_nuvem(banco_dados)
                st.success("Item adicionado com sucesso!")
                st.rerun()
            else:
                st.error("Preencha o Nome do Material.")
    else:
        st.info("Cadastre uma Nota de Crédito (NC) para este ano primeiro.")

# =====================================================================
# ABA 2: VISUALIZAÇÃO E EDIÇÃO POR NC
# =====================================================================
with menu_visualizacao:
    if ncs_do_ano:
        nc_selecionada_vis = st.selectbox("Selecione a NC para Gerenciamento e Análise:", ncs_do_ano, key="vis_item_select_nc")
        
        dados_nc = banco_dados[nc_selecionada_vis]
        total_recebido = dados_nc.get("valor_recebido", 0.0)
        nd_vinculada = dados_nc.get("nd", "Não informada")
        
        st.markdown(f"**Natureza de Despesa (ND):** {nd_vinculada}")
        
        if dados_nc["itens"]:
            for it in dados_nc["itens"]:
                it["Total"] = float(it.get("Valor Unitário", 0.0)) * int(it.get("Qtd", 0))
            
            df_base_mestre = pd.DataFrame(dados_nc["itens"])
            
            if not df_base_mestre.empty:
                df_base_mestre["Valor Unitário"] = df_base_mestre["Valor Unitário"].astype(float)
                df_base_mestre["Qtd"] = df_base_mestre["Qtd"].astype(int)
                df_base_mestre["Total"] = df_base_mestre["Valor Unitário"] * df_base_mestre["Qtd"]
                total_gasto_geral = df_base_mestre["Total"].sum()
            else:
                total_gasto_geral = 0.0
            
            saldo_disponivel = total_recebido - total_gasto_geral
            
            st.write("")
            card1, card2, card3 = st.columns(3)
            card1.metric("Total Recebido na NC", f"R$ {total_recebido:,.2f}")
            card2.metric("Total Planejado / Gasto", f"R$ {total_gasto_geral:,.2f}", delta=f"R$ {total_gasto_geral:,.2f}", delta_color="inverse")
            card3.metric("Saldo Restante Disponível", f"R$ {saldo_disponivel:,.2f}")
            
            if not df_base_mestre.empty:
                st.markdown("---")
                st.markdown("### 📈 Resumo Gráfico das Aquisições")
                col_graf1, col_graf2 = st.columns(2)
                
                with col_graf1:
                    st.markdown("**Valores Comprometidos por Fornecedor (R$)**")
                    gasto_fornecedor = df_base_mestre.groupby("Fornecedor")["Total"].sum().reset_index()
                    grafico_forn = alt.Chart(gasto_fornecedor).mark_bar(color='#1E88E5').encode(
                        x=alt.X('Fornecedor', sort='-y'), y='Total', tooltip=['Fornecedor', 'Total']
                    ).properties(height=300)
                    st.altair_chart(grafico_forn, use_container_width=True)
                
                with col_graf2:
                    st.markdown("**Status Atual das Entregas (Qtd. Itens)**")
                    status_contagem = df_base_mestre["Situação"].value_counts().reset_index()
                    status_contagem.columns = ["Situação", "Quantidade"]
                    escala_cores = alt.Scale(domain=["Recebido", "Aguardando NC para chegar", "Aguardando entrega"], range=["#28a745", "#007bff", "#dc3545"])
                    grafico_status = alt.Chart(status_contagem).mark_bar().encode(
                        x=alt.X("Situação", sort="-y"), y="Quantidade",
                        color=alt.Color("Situação", scale=escala_cores, legend=None), tooltip=["Situação", "Quantidade"]
                    ).properties(height=300)
                    st.altair_chart(grafico_status, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 Planilhas de Acompanhamento Separadas por Fornecedor")
            
            if not df_base_mestre.empty:
                lista_fornecedores = sorted(df_base_mestre["Fornecedor"].unique())
                houve_alteracao = False
                df_atualizado_acumulado = []
                
                for i, forn in enumerate(lista_fornecedores):
                    col_titulo, col_btn_baixa = st.columns([3, 1])
                    with col_titulo:
                        st.markdown(f"### 🏢 Fornecedor: **{forn}**")
                    with col_btn_baixa:
                        st.write("") 
                        if st.button(f"✅ Receber todos os itens", key=f"btn_lote_{nc_selecionada_vis}_{i}", use_container_width=True):
                            for it_bd in banco_dados[nc_selecionada_vis]["itens"]:
                                if it_bd.get("Fornecedor") == forn:
                                    it_bd["Situação"] = "Recebido"
                            salvar_na_nuvem(banco_dados)
                            st.toast(f"Itens de {forn} marcados como Recebidos!")
                            st.rerun()
                    
                    df_forn_atual = df_base_mestre[df_base_mestre["Fornecedor"] == forn].sort_values(by="Item").reset_index(drop=True)
                    
                    df_editado_forn = st.data_editor(
                        df_forn_atual,
                        column_config={
                            "Item": st.column_config.NumberColumn("Item", min_value=1, step=1, required=True),
                            "Nome": st.column_config.TextColumn("Nome", required=True),
                            "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, step=1, required=True),
                            "Valor Unitário": st.column_config.NumberColumn("Valor Unitário", min_value=0.0, step=0.01, format="R$ %.2f", required=True),
                            "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                            "UASG": st.column_config.TextColumn("UASG"),
                            "Pregão": st.column_config.TextColumn("Pregão"),
                            "Ata": st.column_config.TextColumn("Ata"),
                            "Fornecedor": st.column_config.TextColumn("Fornecedor"),
                            "CNPJ": st.column_config.TextColumn("CNPJ"),
                            "Situação": st.column_config.SelectboxColumn("Situação", options=["Aguardando NC para chegar", "Aguardando entrega", "Recebido"], required=True)
                        },
                        disabled=["Total"], 
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        key=f"editor_forn_{nc_selecionada_vis}_{forn.replace(' ', '_')}_{i}"
                    )
                    
                    dict_antigo = df_forn_atual.drop(columns=["Total"]).to_dict("records")
                    dict_novo = df_editado_forn.drop(columns=["Total"]).to_dict("records")
                    
                    if dict_antigo != dict_novo:
                        houve_alteracao = True
                    
                    df_editado_forn["Total"] = df_editado_forn["Valor Unitário"].astype(float) * df_editado_forn["Qtd"].astype(int)
                    total_desse_forn = df_editado_forn["Total"].sum()
                    
                    st.markdown(f"<h4 style='text-align: right; color: #1E88E5;'>Total {forn}: R$ {total_desse_forn:,.2f}</h4>", unsafe_allow_html=True)
                    st.write("") 
                    
                    df_atualizado_acumulado.append(df_editado_forn)
                
                if houve_alteracao:
                    df_final_para_salvar = pd.concat(df_atualizado_acumulado, ignore_index=True)
                    df_final_para_salvar["Total"] = df_final_para_salvar["Valor Unitário"].astype(float) * df_final_para_salvar["Qtd"].astype(int)
                    
                    banco_dados[nc_selecionada_vis]["itens"] = df_final_para_salvar.to_dict(orient="records")
                    salvar_na_nuvem(banco_dados)
                    
                    st.toast("✅ Alteração salva na nuvem com sucesso!")
                    st.rerun()
    else:
         st.info("Nenhuma NC cadastrada para este ano.")

# =====================================================================
# ABA 3: VISÃO GLOBAL ANUAL
# =====================================================================
with menu_visao_global:
    st.subheader(f"Resumo Geral de Empenhos e Aquisições - Ano {ano_selecionado}")
    st.markdown("Este gráfico consolida os valores agrupados por **Natureza de Despesa (ND)** e empilhados pela sua respectiva **Situação Atual** (Planejamento, Entrega ou Recebido).")
    
    dados_anuais = []
    
    if ncs_do_ano:
        for nc in ncs_do_ano:
            nd_atual = banco_dados[nc].get("nd", "Não informada")
            if not nd_atual.strip():
                nd_atual = "Não informada"
                
            itens_da_nc = banco_dados[nc].get("itens", [])
            for item in itens_da_nc:
                valor_total_item = float(item.get("Valor Unitário", 0.0)) * int(item.get("Qtd", 0))
                situacao = item.get("Situação", "Situação Indefinida")
                
                dados_anuais.append({"ND": nd_atual, "Situação": situacao, "Valor Total": valor_total_item})
        
        if dados_anuais:
            df_anual = pd.DataFrame(dados_anuais)
            df_agrupado = df_anual.groupby(["ND", "Situação"])["Valor Total"].sum().reset_index()
            
            escala_cores = alt.Scale(domain=["Recebido", "Aguardando NC para chegar", "Aguardando entrega"], range=["#28a745", "#007bff", "#dc3545"])
            
            grafico_anual = alt.Chart(df_agrupado).mark_bar().encode(
                x=alt.X("ND:N", title="Natureza de Despesa (ND)"),
                y=alt.Y("Valor Total:Q", title="Total (R$)"),
                color=alt.Color("Situação:N", scale=escala_cores, title="Status do Recurso"),
                tooltip=[alt.Tooltip("ND:N", title="ND"), alt.Tooltip("Situação:N", title="Status"), alt.Tooltip("Valor Total:Q", title="Valor Calculado (R$)", format=",.2f")]
            ).properties(height=450)
            
            st.altair_chart(grafico_anual, use_container_width=True)
            
            total_geral_ano = df_agrupado["Valor Total"].sum()
            st.markdown(f"<h3 style='text-align: right;'>Total Geral Cadastrado em {ano_selecionado}: <span style='color: #1E88E5;'>R$ {total_geral_ano:,.2f}</span></h3>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("#### Detalhamento de Valores por ND e Status")
            
            df_pivot = df_agrupado.pivot(index="ND", columns="Situação", values="Valor Total").fillna(0)
            df_pivot["Total Geral por ND"] = df_pivot.sum(axis=1)
            
            for col in df_pivot.columns:
                df_pivot[col] = df_pivot[col].apply(lambda x: f"R$ {x:,.2f}")
                
            st.dataframe(df_pivot, use_container_width=True)
        else:
            st.info("Não há itens registrados nas Notas de Crédito deste ano.")
    else:
        st.info("Nenhuma NC registrada para este ano.")
