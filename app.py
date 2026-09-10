import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import streamlit.components.v1 as components

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Gerenciador de Recursos",
    page_icon="💰",
    layout="wide"
)

# =====================================================================
# 2. CONEXÃO COM O BANCO DE DADOS 
# =====================================================================
URL = "https://oxneqoegehufjksvupji.supabase.co"
KEY = "sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX"
supabase: Client = create_client(URL, KEY)

def extrair_ano(nc_nome):
    if len(nc_nome) >= 4 and nc_nome[:4].isdigit():
        return nc_nome[:4]
    return "Outros/Sem Ano"

# =====================================================================
# 3. TELA DE LOGIN E CADASTRO INICIAL (BLINDAGEM DE ACESSO)
# =====================================================================
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if st.session_state.usuario_logado is None:
    st.title("🖥 Sistema Profissional de Controle de Recursos")
    st.markdown("Bem-vindo! Faça login ou registre a conta Matriz (Fiscal) da sua OM.")
    st.markdown("---")
    
    col_login, col_divisor, col_cadastro = st.columns([4, 1, 4])
    
    with col_login:
        st.subheader("🔑 Fazer Login")
        with st.form("form_login"):
            usuario_login = st.text_input("Usuário:").strip().lower()
            senha_login = st.text_input("Senha:", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            
            if btn_login:
                if not usuario_login or not senha_login:
                    st.warning("Preencha usuário e senha.")
                else:
                    resposta = supabase.table("usuarios").select("*").eq("id", usuario_login).execute()
                    if len(resposta.data) > 0:
                        usuario_db = resposta.data[0]
                        if usuario_db["senha"] == senha_login:
                            st.session_state.usuario_logado = usuario_login
                            st.rerun()
                        else:
                            st.error("Senha incorreta!")
                    else:
                        st.error("Usuário não encontrado!")
                
    with col_divisor:
        st.write("")

    with col_cadastro:
        st.subheader("🛡️ Criar Conta Matriz (Apenas Fiscal)")
        st.info("⚠️ **Acesso Restrito:** Apenas o **Fiscal Administrativo** pode criar a primeira conta da OM. Contas de **Chefe** e **Operador** devem ser criadas pelo Fiscal internamente.")
        with st.form("form_cadastro"):
            novo_user = st.text_input("Escolha um nome de Usuário:").strip().lower()
            nova_senha = st.text_input("Crie uma Senha:", type="password")
            novo_nome = st.text_input("Seu Nome/Posto (Ex: Cap Moura):")
            nova_om = st.text_input("Sua OM (Ex: 23º BI):").strip().upper()
            
            col_cad1, col_cad2 = st.columns(2)
            with col_cad1:
                nova_secao = st.text_input("Sua Seção Primária (Ex: FISCALIZACAO):").strip().upper()
            with col_cad2:
                novo_perfil = st.selectbox("Nível de Acesso Inicial:", ["Fiscal"])
            
            btn_cadastrar = st.form_submit_button("Criar Conta Matriz (Fiscal)", type="secondary", use_container_width=True)
            
            if btn_cadastrar:
                if not novo_user or not nova_senha or not novo_nome or not nova_om or not nova_secao:
                    st.warning("Preencha todos os campos obrigatórios.")
                else:
                    verifica_user = supabase.table("usuarios").select("id").eq("id", novo_user).execute()
                    if len(verifica_user.data) > 0:
                        st.error("Este nome de usuário já está em uso.")
                    else:
                        verifica_fiscal = supabase.table("usuarios").select("id").eq("om", nova_om).eq("perfil", "Fiscal").execute()
                        
                        if len(verifica_fiscal.data) > 0:
                            st.error("⛔ Esta OM já possui um Fiscal cadastrado no sistema. Solicite a ele a criação da sua conta.")
                        else:
                            supabase.table("usuarios").insert({
                                "id": novo_user, "senha": nova_senha, "nome": novo_nome, 
                                "om": nova_om, "secao": nova_secao, "perfil": novo_perfil
                            }).execute()
                            
                            id_secao = f"{nova_om}_{nova_secao}"
                            verifica_banco = supabase.table("dados").select("id").eq("id", id_secao).execute()
                            if len(verifica_banco.data) == 0:
                                supabase.table("dados").insert({"id": id_secao, "ncs": {}}).execute()
                                
                            st.success("✅ Conta de Fiscal criada! Faça o login ao lado.")
    
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 14px;'>"
        "Criado e Desenvolvido por:<br><b>2º Sgt Com Thales Winkler</b><br><br>"
        "<i>Este sistema está em constante evolução. Para suporte ou envio de sugestões, entre em contato: <a href='mailto:thaleswinkler81@gmail.com'>thaleswinkler81@gmail.com</a></i>"
        "</div>", 
        unsafe_allow_html=True
    )
    st.stop() 

# =====================================================================
# 4. CARREGAMENTO DOS DADOS CORPORATIVOS
# =====================================================================
usuario_atual = st.session_state.usuario_logado

resp_perfil = supabase.table("usuarios").select("*").eq("id", usuario_atual).execute()
perfil = resp_perfil.data[0]
om_user = perfil.get("om", "Não informada")
secao_user = perfil.get("secao", "Geral")
tipo_perfil = perfil.get("perfil", "Operador")

# =====================================================================
# 5. ASSINATURA E FILTROS LATERAIS (SIDEBAR)
# =====================================================================
st.sidebar.title("💰 Gestão Orçamentária")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠 Estação de Trabalho")
st.sidebar.info(f"**Militar:** {perfil.get('nome')}\n\n**OM:** {om_user}")

if tipo_perfil == "Fiscal":
    st.sidebar.warning("🛡️ **Perfil: FISCAL (Somente Leitura)**")
    resp_secoes = supabase.table("usuarios").select("secao").eq("om", om_user).execute()
    secoes_da_om = sorted(list(set([r["secao"] for r in resp_secoes.data])))
    if not secoes_da_om: secoes_da_om = [secao_user]
    
    secao_ativa = st.sidebar.selectbox("🔎 Operar dados da Seção:", secoes_da_om, index=secoes_da_om.index(secao_user) if secao_user in secoes_da_om else 0)
elif tipo_perfil == "Chefe":
    st.sidebar.success(f"👑 **Perfil: CHEFE**\n\n**Seção:** {secao_user}")
    secao_ativa = secao_user
else:
    st.sidebar.info(f"👤 **Perfil: OPERADOR**\n\n**Seção:** {secao_user}")
    secao_ativa = secao_user

id_banco = f"{om_user}_{secao_ativa}"

if "banco" not in st.session_state or st.session_state.get("secao_carregada") != id_banco:
    resp_dados = supabase.table("dados").select("ncs").eq("id", id_banco).execute()
    if len(resp_dados.data) > 0:
        st.session_state.banco = resp_dados.data[0].get("ncs", {})
    else:
        st.session_state.banco = {}
    st.session_state.secao_carregada = id_banco

banco_dados = st.session_state.banco

def salvar_dados(dados):
    supabase.table("dados").update({"ncs": dados}).eq("id", id_banco).execute()

st.sidebar.markdown("---")

# =====================================================================
# ALTERAÇÃO DE SENHA
# =====================================================================
with st.sidebar.expander("⚙️ Alterar Minha Senha"):
    with st.form("form_alterar_senha"):
        nova_senha_input = st.text_input("Nova Senha:", type="password")
        confirma_senha_input = st.text_input("Confirmar Nova Senha:", type="password")
        btn_salvar_senha = st.form_submit_button("Atualizar Senha", type="primary", use_container_width=True)
        
        if btn_salvar_senha:
            if not nova_senha_input or not confirma_senha_input:
                st.error("Preencha ambos os campos.")
            elif nova_senha_input != confirma_senha_input:
                st.error("As senhas não coincidem.")
            else:
                supabase.table("usuarios").update({"senha": nova_senha_input}).eq("id", usuario_atual).execute()
                st.success("✅ Senha atualizada com sucesso!")

st.sidebar.markdown("---")
if st.sidebar.button("Sair da Conta (Logout)", use_container_width=True):
    st.session_state.usuario_logado = None
    if "banco" in st.session_state: del st.session_state.banco
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Filtro de Exercício")

anos_disponiveis = set(extrair_ano(nc) for nc in banco_dados.keys() if nc != "CONFIG_REQUISICAO")
lista_anos = sorted(list(anos_disponiveis), reverse=True) if anos_disponiveis else ["2026"]
ano_selecionado = st.sidebar.selectbox("Selecione o Ano de Referência:", lista_anos)
ncs_do_ano = [nc for nc in banco_dados.keys() if nc != "CONFIG_REQUISICAO" and extrair_ano(nc) == ano_selecionado]

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Criado e Desenvolvido por:<br><b>2º Sgt Com Thales Winkler</b><br><br>"
    "<i>Sistema em constante evolução. Sugestões e suporte:<br>"
    "<a href='mailto:thaleswinkler81@gmail.com'>thaleswinkler81@gmail.com</a></i>"
    "</div>", 
    unsafe_allow_html=True
)

# =====================================================================
# 6. TÍTULO PRINCIPAL E ABAS 
# =====================================================================
st.title(f"🖥 Sistema de Controle de Recursos - {om_user}")
st.markdown(f"**Área de Trabalho Ativa:** {secao_ativa}")
st.markdown("---")

menu_cadastro, menu_visualizacao, menu_visao_global, menu_acessos = st.tabs([
    "📝 Cadastrar e Lançar Compras",
    "📊 Controle Individual por NC",
    "📈 Visão Global do Ano",
    "👥 Gerenciar Acessos"
])

# =====================================================================
# ABA 1: CADASTRO
# =====================================================================
with menu_cadastro:
    if tipo_perfil == "Fiscal":
        st.error("🛡️ **Acesso Negado:** O perfil de Fiscal possui acesso de Auditoria e Visualização. Você não pode cadastrar, alterar ou deletar Notas de Crédito. Retorne para as Abas de Análise e Visão Global.")
    else:
        st.subheader("1. Cadastrar Nova Nota de Crédito (NC)")
        
        lista_nds = list(set([dados.get("nd", "") for nc, dados in banco_dados.items() if nc != "CONFIG_REQUISICAO" and isinstance(dados, dict) and dados.get("nd", "").strip()]))
        lista_pis = list(set([dados.get("pi", "") for nc, dados in banco_dados.items() if nc != "CONFIG_REQUISICAO" and isinstance(dados, dict) and dados.get("pi", "").strip()]))
        
        opcoes_nd = ["➕ Digitar Nova ND..."] + sorted(lista_nds)
        opcoes_pi = ["➕ Digitar Novo PI..."] + sorted(lista_pis)
        
        col_nc1, col_nc2, col_nc3 = st.columns(3)
        with col_nc1:
            nova_nc = st.text_input("Número da NC (Comece com o ano, ex: 2026NC000511):", "", key="cad_numero_nc").strip()
            valor_nc = st.number_input("Valor Total Recebido na NC (R$):", min_value=0.0, step=100.0, key="cad_valor_nc")
        
        with col_nc2:
            pi_selecionado = st.selectbox("Plano Interno (PI):", opcoes_pi)
            if pi_selecionado == "➕ Digitar Novo PI...":
                novo_pi = st.text_input("Digite o PI:").strip()
            else:
                novo_pi = pi_selecionado
                
        with col_nc3:
            nd_selecionada = st.selectbox("Natureza de Despesa (ND):", opcoes_nd)
            if nd_selecionada == "➕ Digitar Nova ND...":
                nova_nd = st.text_input("Digite a ND:").strip()
            else:
                nova_nd = nd_selecionada
        
        if st.button("💾 Registrar Nova Nota de Crédito", type="primary", key="btn_cad_nc"):
            if nova_nc:
                if nova_nc != "CONFIG_REQUISICAO" and nova_nc not in banco_dados:
                    banco_dados[nova_nc] = {"valor_recebido": valor_nc, "nd": nova_nd, "pi": novo_pi, "itens": []}
                    salvar_dados(banco_dados)
                    st.session_state.banco = banco_dados
                    st.success(f"NC {nova_nc} salva com sucesso na seção {secao_ativa}!")
                    st.rerun()
                else:
                    st.warning("Esta NC já existe ou o nome é inválido.")
            else:
                st.warning("Por favor, digite o número da NC.")
        
        if ncs_do_ano:
            st.markdown("---")
            st.subheader("✏ Alterar Dados de uma NC Existente")
            
            nc_para_editar = st.selectbox(f"Selecione a NC ({ano_selecionado}) para alterar:", ncs_do_ano, key="editar_select_nc")
            
            dados_atuais = banco_dados[nc_para_editar]
            valor_atual = dados_atuais.get("valor_recebido", 0.0)
            nd_atual = dados_atuais.get("nd", "")
            pi_atual = dados_atuais.get("pi", "")
            
            col_ed1, col_ed2, col_ed3, col_ed4 = st.columns(4)
            with col_ed1:
                nome_editado = st.text_input("Número da NC:", value=nc_para_editar, key=f"edit_numero_nc_{nc_para_editar}").strip()
            with col_ed2:
                pi_editado = st.text_input("Plano Interno (PI):", value=pi_atual, key=f"edit_pi_nc_{nc_para_editar}").strip()
            with col_ed3:
                nd_editada = st.text_input("Natureza de Despesa (ND):", value=nd_atual, key=f"edit_nd_nc_{nc_para_editar}").strip()
            with col_ed4:
                valor_editado = st.number_input("Valor Total (R$):", value=float(valor_atual), min_value=0.0, step=100.0, key=f"edit_valor_nc_{nc_para_editar}")
            
            if st.button("🔄 Confirmar Alterações da NC", type="secondary", key="btn_edit_nc"):
                if nome_editado:
                    if nome_editado != nc_para_editar and nome_editado in banco_dados:
                        st.error("Erro: Já existe outra NC cadastrada com esse novo número.")
                    else:
                        dados_preservados = banco_dados.pop(nc_para_editar)
                        dados_preservados["valor_recebido"] = valor_editado
                        dados_preservados["nd"] = nd_editada
                        dados_preservados["pi"] = pi_editado
                        banco_dados[nome_editado] = dados_preservados
                        salvar_dados(banco_dados)
                        st.session_state.banco = banco_dados
                        st.success(f"Dados da NC '{nome_editado}' atualizados com sucesso!")
                        st.rerun()
                else:
                    st.warning("O número da NC não pode ficar em branco.")

            st.markdown("---")
            st.subheader("🚨 Deletar Nota de Crédito Inteira")
            nc_para_deletar_toda = st.selectbox(f"Selecione a NC ({ano_selecionado}) para APAGAR:", ncs_do_ano, key="nc_del_toda")
            if st.button("💥 DELETAR NC E TODOS OS ITENS", type="primary", key="btn_del_nc"):
                banco_dados.pop(nc_para_deletar_toda)
                salvar_dados(banco_dados)
                st.session_state.banco = banco_dados
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
                
                opcoes_sit = ["Planejamento", "Aguardando entrega", "Recebido", "➕ Outra (Digitar)..."]
                sit_selecionada = st.selectbox("Situação Atual do Recurso:", opcoes_sit, key="item_sit")
                if sit_selecionada == "➕ Outra (Digitar)...":
                    situacao = st.text_input("Digite a Situação:").strip()
                else:
                    situacao = sit_selecionada
            
            if st.button("➕ Adicionar Item ao Planejamento", type="primary", key="btn_add_item"):
                if nome_resumido:
                    novo_item = {
                        "Item": int(nr_item), "Nome": nome_resumido, "Valor Unitário": float(valor_unitario),
                        "Qtd": int(quantidade), "Total": float(valor_unitario * quantidade), "UASG": nr_uasg,
                        "Pregão": nr_pregao, "Ata": nr_ata, "Fornecedor": fornecedor.strip().upper() if fornecedor else "NÃO INFORMADO",
                        "CNPJ": cnpj, "Situação": situacao
                    }
                    banco_dados[nc_selecionada_cad]["itens"].append(novo_item)
                    salvar_dados(banco_dados)
                    st.session_state.banco = banco_dados
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
        
        pis_disponiveis = list(set([banco_dados[nc].get("pi", "Não informado") for nc in ncs_do_ano if isinstance(banco_dados[nc], dict) and banco_dados[nc].get("pi", "Não informado").strip()]))
        opcoes_filtro_pi = ["TODOS OS PIs"] + sorted(pis_disponiveis)
        
        filtro_pi = st.selectbox("📌 Filtrar por PI:", opcoes_filtro_pi)
        
        if filtro_pi == "TODOS OS PIs":
            ncs_filtradas = ncs_do_ano
        else:
            ncs_filtradas = [nc for nc in ncs_do_ano if banco_dados[nc].get("pi", "Não informado") == filtro_pi]
            
        if not ncs_filtradas:
            st.warning("Nenhuma NC encontrada para o PI selecionado.")
        else:
            nc_selecionada_vis = st.selectbox("Selecione a NC para Gerenciamento e Análise:", ncs_filtradas, key="vis_item_select_nc")
            
            dados_nc = banco_dados[nc_selecionada_vis]
            total_recebido = dados_nc.get("valor_recebido", 0.0)
            nd_vinculada = dados_nc.get("nd", "Não informada")
            pi_vinculado = dados_nc.get("pi", "Não informado")
            
            st.markdown(f"**PI:** {pi_vinculado} &nbsp;&nbsp;|&nbsp;&nbsp; **ND:** {nd_vinculada}")
            
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
                with card1:
                    st.metric("Total Recebido na NC", f"R$ {total_recebido:,.2f}")
                with card2:
                    st.metric("Total Planejado / Gasto", f"R$ {total_gasto_geral:,.2f}", delta=f"R$ {total_gasto_geral:,.2f}", delta_color="inverse")
                with card3:
                    st.metric("Saldo Restante Disponível", f"R$ {saldo_disponivel:,.2f}")
                
                if not df_base_mestre.empty:
                    st.markdown("---")
                    st.markdown("### 📈 Resumo Gráfico das Aquisições")
                    col_graf1, col_graf2 = st.columns(2)
                    
                    with col_graf1:
                        st.markdown("**Valores Comprometidos por Fornecedor (R$)**")
                        gasto_fornecedor = df_base_mestre.groupby("Fornecedor")["Total"].sum().reset_index()
                        grafico_forn = alt.Chart(gasto_fornecedor).mark_bar(color='#1E88E5').encode(
                            x=alt.X('Fornecedor', sort='-y'),
                            y='Total',
                            tooltip=['Fornecedor', 'Total']
                        ).properties(height=300)
                        st.altair_chart(grafico_forn, use_container_width=True)
                    
                    with col_graf2:
                        st.markdown("**Status Atual das Entregas (Qtd. Itens)**")
                        status_contagem = df_base_mestre["Situação"].value_counts().reset_index()
                        status_contagem.columns = ["Situação", "Quantidade"]
                        
                        grafico_status = alt.Chart(status_contagem).mark_bar(color="#28a745").encode(
                            x=alt.X("Situação", sort="-y"),
                            y="Quantidade",
                            tooltip=["Situação", "Quantidade"]
                        ).properties(height=300)
                        st.altair_chart(grafico_status, use_container_width=True)
                
                st.markdown("---")
                st.subheader("📋 Planilhas de Acompanhamento Separadas por Fornecedor")
                
                # -------------------------------------------------------------
                # CONFIGURAÇÃO DE TIMBRE E ASSINATURAS POR SEÇÃO (PRÉ-CADASTRO)
                # -------------------------------------------------------------
                config_req = banco_dados.get("CONFIG_REQUISICAO", {})
                pre_cadastro_pendente = not bool(config_req)
                
                if pre_cadastro_pendente:
                    st.warning("⚠️ **Atenção:** O cabeçalho padrão da sua Seção ainda não foi configurado. Preencha os dados abaixo uma única vez para liberar a emissão padronizada de requisições.")
                
                with st.expander("⚙️ Personalizar Cabeçalho, Local e Assinaturas (Padrão da sua Seção)", expanded=pre_cadastro_pendente):
                    st.info("Preencha estes dados uma única vez. Eles ficarão salvos no banco de dados e padronizarão automaticamente todas as requisições impressas por esta Seção.")
                    with st.form("form_config_req"):
                        c1, c2 = st.columns(2)
                        with c1:
                            cfg_om = st.text_area("Nome da OM (Pode usar 2 linhas):", value=config_req.get("cabecalho_om", f"{om_user}\n(NOME HISTÓRICO DA OM)"))
                            cfg_ind = st.text_input("Indicativo do DIEx (Ex: CFGS/23ºBI):", value=config_req.get("indicativo_diex", f"SEÇÃO/{om_user}"))
                            cfg_remetente = st.text_input("Remetente (Campo 'Do:'):", value=config_req.get("remetente_do", "Chefe da Seção"))
                            cfg_cidade = st.text_input("Cidade/UF da OM (Ex: Blumenau-SC):", value=config_req.get("cidade_om", "Blumenau-SC"))
                        with c2:
                            cfg_ass_nome = st.text_input("Sua Assinatura (Ex: FLÁVIO - Cap):", value=config_req.get("assinatura_nome", "NOME - Posto"))
                            cfg_ass_func = st.text_input("Função de quem Assina:", value=config_req.get("assinatura_funcao", "Chefe da Seção"))
                            cfg_od_nome = st.text_input("Nome do OD (Ex: SILVA - Cel):", value=config_req.get("od_nome", "NOME DO OD - Posto"))
                            cfg_od_func = st.text_input("Função do OD:", value=config_req.get("od_funcao", f"Ordenador de Despesas do {om_user}"))
                        
                        if st.form_submit_button("💾 Salvar Novo Padrão da Seção", type="primary"):
                            banco_dados["CONFIG_REQUISICAO"] = {
                                "cabecalho_om": cfg_om,
                                "indicativo_diex": cfg_ind,
                                "remetente_do": cfg_remetente,
                                "cidade_om": cfg_cidade,
                                "assinatura_nome": cfg_ass_nome,
                                "assinatura_funcao": cfg_ass_func,
                                "od_nome": cfg_od_nome,
                                "od_funcao": cfg_od_func
                            }
                            salvar_dados(banco_dados)
                            st.session_state.banco = banco_dados
                            st.success("Configuração padrão da seção atualizada com sucesso!")
                            st.rerun()
                
                def format_html_var(val, default):
                    return str(val).strip() if val else default

                html_cabecalho_om = format_html_var(config_req.get("cabecalho_om"), f"{om_user}<br>(NOME HISTÓRICO)").replace("\n", "<br>")
                html_ind = format_html_var(config_req.get("indicativo_diex"), f"SEÇÃO/{om_user}")
                html_rem = format_html_var(config_req.get("remetente_do"), "Função do Remetente")
                html_cidade = format_html_var(config_req.get("cidade_om"), "Cidade-UF")
                html_ass_nome = format_html_var(config_req.get("assinatura_nome"), "NOME DO MILITAR - Posto")
                html_ass_func = format_html_var(config_req.get("assinatura_funcao"), "Função do Remetente")
                html_od_nome = format_html_var(config_req.get("od_nome"), "NOME DO OD - Posto")
                html_od_func = format_html_var(config_req.get("od_funcao"), "Ordenador de Despesas da OM")
                # -------------------------------------------------------------

                if not df_base_mestre.empty:
                    lista_fornecedores = sorted(df_base_mestre["Fornecedor"].unique())
                    houve_alteracao = False
                    df_atualizado_acumulado = []
                    
                    for i, forn in enumerate(lista_fornecedores):
                        
                        col_titulo, col_btn_baixa = st.columns([3, 1])
                        with col_titulo:
                            st.markdown(f"### 🏢 Fornecedor: **{forn}**")
                        
                        if tipo_perfil != "Fiscal":
                            with col_btn_baixa:
                                st.write("") 
                                if st.button(f"✅ Receber todos os itens", key=f"btn_lote_{nc_selecionada_vis}_{i}", use_container_width=True):
                                    for it_bd in banco_dados[nc_selecionada_vis]["itens"]:
                                        if it_bd.get("Fornecedor") == forn:
                                            it_bd["Situação"] = "Recebido"
                                    salvar_dados(banco_dados)
                                    st.session_state.banco = banco_dados
                                    st.toast(f"Itens de {forn} marcados como Recebidos!")
                                    st.rerun()
                                    
                        df_forn_atual = df_base_mestre[df_base_mestre["Fornecedor"] == forn].sort_values(by="Item").reset_index(drop=True)
                        
                        with st.expander(f"📄 GERAR REQUISIÇÃO: {forn} (Preencher Documento)", expanded=False):
                            st.info("💡 Preencha os dados e clique em Salvar. O documento carregará automaticamente o timbre da sua seção e salvará o número do EB desta requisição.")
                            
                            doc_info = banco_dados[nc_selecionada_vis].get("doc_info", {})
                            info_forn = doc_info.get(forn, {"diex": "", "eb": "", "data": "", "assunto": "", "empenho": ""})
                            
                            with st.form(f"form_req_{forn}_{i}"):
                                col_req1, col_req2 = st.columns(2)
                                with col_req1:
                                    diex_val = st.text_input("Nº do DIEx:", value=info_forn.get("diex", ""))
                                    eb_val = st.text_input("Nº do EB (Processo/Documento):", value=info_forn.get("eb", ""))
                                    data_val = st.text_input("Data (Ex: 08 de setembro de 2026):", value=info_forn.get("data", ""))
                                with col_req2:
                                    assunto_val = st.text_input("Assunto (Ex: materiais de construção):", value=info_forn.get("assunto", ""))
                                    empenho_val = st.text_input("Nota de Empenho:", value=info_forn.get("empenho", ""))
                                
                                btn_salvar_req = st.form_submit_button("💾 Salvar Dados da Requisição", type="primary")
                                
                                if btn_salvar_req:
                                    if "doc_info" not in banco_dados[nc_selecionada_vis]:
                                        banco_dados[nc_selecionada_vis]["doc_info"] = {}
                                    banco_dados[nc_selecionada_vis]["doc_info"][forn] = {
                                        "diex": diex_val,
                                        "eb": eb_val,
                                        "data": data_val,
                                        "assunto": assunto_val,
                                        "empenho": empenho_val
                                    }
                                    salvar_dados(banco_dados)
                                    st.session_state.banco = banco_dados
                                    st.success("Dados salvos e documento atualizado!")
                                    st.rerun()
                            
                            diex_display = info_forn.get("diex", "") if info_forn.get("diex", "") else "______"
                            eb_display = info_forn.get("eb", "") if info_forn.get("eb", "") else "_________________"
                            data_display = info_forn.get("data", "") if info_forn.get("data", "") else "____ de _______________ de 2026"
                            assunto_display = info_forn.get("assunto", "") if info_forn.get("assunto", "") else "______________________"
                            empenho_display = info_forn.get("empenho", "") if info_forn.get("empenho", "") else "______________________"
                            local_display = html_cidade
                            
                            linhas_tabela_html = ""
                            soma_total_forn = 0.0
                            pregao_atual = df_forn_atual["Pregão"].iloc[0] if not df_forn_atual.empty else ""
                            uasg_atual = df_forn_atual["UASG"].iloc[0] if not df_forn_atual.empty else ""
                            cnpj_atual = df_forn_atual["CNPJ"].iloc[0] if not df_forn_atual.empty else ""
                            
                            for _, row in df_forn_atual.iterrows():
                                v_unit = float(row['Valor Unitário'])
                                qtd = int(row['Qtd'])
                                v_total = v_unit * qtd
                                soma_total_forn += v_total
                                
                                v_unit_str = f"R$ {v_unit:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                v_total_str = f"R$ {v_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                
                                linhas_tabela_html += f"""
                                <tr>
                                    <td>{row['Item']}</td>
                                    <td style="text-align: left; padding-left: 5px;">{row['Nome']}</td>
                                    <td>{qtd}</td>
                                    <td>{v_unit_str}</td>
                                    <td>{v_total_str}</td>
                                </tr>
                                """
                                
                            total_geral_str = f"R$ {soma_total_forn:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            
                            html_template = f"""
                            <html>
                            <head>
                            <style>
                                @media print {{
                                    @page {{ margin: 0; }} 
                                    body {{ padding: 2cm; background-color: white; }} 
                                    .no-print {{ display: none !important; }}
                                    .editable-doc {{ box-shadow: none !important; border: none !important; padding: 0 !important; max-width: 100%; margin: 0 !important; }}
                                    .quebra-pagina {{ page-break-before: always; }}
                                }}
                                body {{ font-family: 'Times New Roman', Times, serif; color: black; background-color: #f8f9fa; margin: 0; }}
                                .editable-doc {{
                                    padding: 40px; 
                                    background-color: white; 
                                    max-width: 800px; 
                                    margin: 20px auto; 
                                    border: 1px solid #ccc; 
                                    box-shadow: 2px 2px 10px #aaa;
                                }}
                                table.borda, .borda th, .borda td {{
                                    border: 1px solid black;
                                    border-collapse: collapse;
                                }}
                                .borda th, .borda td {{ padding: 5px; text-align: center; }}
                                .separador-tela {{
                                    border-top: 2px dashed #ccc;
                                    color: #999;
                                    text-align: center;
                                    margin: 40px 0;
                                    padding-top: 10px;
                                    font-size: 12px;
                                    font-family: Arial, sans-serif;
                                    user-select: none;
                                }}
                            </style>
                            </head>
                            <body>
                            <div class="no-print" style="text-align: center; margin-bottom: 20px; padding-top: 20px;">
                                <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px; font-weight: bold; box-shadow: 1px 1px 5px #888;">
                                    🖨️ Imprimir / Salvar como PDF
                                </button>
                            </div>
                        
                            <div class="editable-doc" contenteditable="true">
                                
                                <table style="width: 100%; border: none; margin-bottom: 0;">
                                    <tr style="border: none;">
                                        <td style="width: 30%; border: none;"></td>
                                        <td style="width: 40%; border: none; text-align: center; vertical-align: top;">
                                            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Coat_of_arms_of_Brazil.svg" width="80">
                                        </td>
                                        <td style="width: 30%; border: none; text-align: center; vertical-align: top; font-weight: bold; font-size: 14px; line-height: 1.2;">
                                            VISTO<br><br>_________________<br>Fisc Adm
                                        </td>
                                    </tr>
                                </table>
                                
                                <div style="text-align: center; line-height: 1.2;">
                                    <b>MINISTÉRIO DA DEFESA</b><br>
                                    <b>EXÉRCITO BRASILEIRO</b><br>
                                    <b>{html_cabecalho_om}</b>
                                </div>
                                <br>
                                
                                <table style="width: 100%; border: none;">
                                    <tr style="border: none;">
                                        <td style="border: none; text-align: left; padding: 0;">DIEx nº {diex_display} - {html_ind}<br>EB: {eb_display}</td>
                                        <td style="border: none; text-align: right; padding: 0;">{local_display}, {data_display}.</td>
                                    </tr>
                                </table>
                                <br>
                                <div style="line-height: 1.5;">
                                    <b>Do:</b> {html_rem}<br>
                                    <b>Ao:</b> Sr Fiscal Administrativo<br>
                                    <b>Assunto:</b> aquisição de {assunto_display}
                                </div>
                                <br>
                                <div style="text-align: justify; text-indent: 30px; line-height: 1.5;">
                                    1. Nos termos contidos na lei 14.133/2021, solicito-vos providências junto ao Ordenador de Despesas no sentido de aprovar o empenho da despesa para aquisição de material, com os respectivos recursos e destinos:
                                </div>
                                <div style="margin-left: 30px; line-height: 1.5; margin-top: 10px;">
                                    a) <b>Nota de crédito:</b> {nc_selecionada_vis} &nbsp;&nbsp;&nbsp; b) <b>PI:</b> {pi_vinculado}; <b>ND:</b> {nd_vinculada}<br>
                                    <b>Edital de Pregão:</b> {pregao_atual} / <b>UASG:</b> {uasg_atual} / <b>Tipo de Empenho:</b> Ordinário<br>
                                    <b>Nota de Empenho:</b> {empenho_display}<br>
                                    <b>Empresa:</b> {cnpj_atual} – {forn}
                                </div>
                                <br>
                                <table class="borda" style="width: 100%;">
                                    <tr style="font-weight: bold; background-color: #f2f2f2;">
                                        <td>Item</td><td>Nomenclatura</td><td>Qtd</td><td>Valor Unitário</td><td>Valor Total</td>
                                    </tr>
                                    {linhas_tabela_html}
                                    <tr style="font-weight: bold;">
                                        <td colspan="4">TOTAL</td><td>{total_geral_str}</td>
                                    </tr>
                                </table>
                                <br>
                                <div style="text-align: justify; text-indent: 30px; line-height: 1.5;">
                                    2. O material solicitado deverá ser empenhado na empresa vencedora do item acima citado, proveniente de seu respectivo Pregão Eletrônico.
                                </div>
                                <br><br>
                                <div style="text-align: center; line-height: 1.2;">
                                    <b>{html_ass_nome}</b><br>
                                    {html_ass_func}
                                </div>
                                
                                <div class="separador-tela no-print" contenteditable="false">
                                    ✂️ --- QUEBRA DE PÁGINA (Na impressão o Despacho do OD sairá em folha exclusiva) --- ✂️
                                </div>
                                
                                <div class="quebra-pagina" style="padding-top: 10px; line-height: 1.5; font-size: 14px;">
                                    <b>DESPACHO DO OD:</b><br>
                                    1. Autorizo a aquisição do material relacionado na letra b) do número 1);<br>
                                    2. Empregar os recursos provenientes da nota de crédito relacionado na letra a);<br>
                                    3. A SALC inicie os procedimentos legais, conforme legislação em vigor para empenho da despesa.<br>
                                    <br><br>
                                    <div style="text-align: center; line-height: 1.2;">
                                        <b>{html_od_nome}</b><br>
                                        {html_od_func}
                                    </div>
                                </div>
                            </div>
                            </body>
                            </html>
                            """
                            
                            components.html(html_template, height=800, scrolling=True)
                        
                        cfg_colunas = {
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
                            "Situação": st.column_config.TextColumn("Situação", required=True) 
                        }
                        ordem_col = ["Item", "Nome", "Qtd", "Valor Unitário", "Total", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"]
                        
                        if tipo_perfil == "Fiscal":
                            st.dataframe(df_forn_atual, column_order=ordem_col, column_config=cfg_colunas, hide_index=True, use_container_width=True)
                            total_desse_forn = df_forn_atual["Total"].sum()
                            st.markdown(f"<h4 style='text-align: right; color: #1E88E5;'>Total {forn}: R$ {total_desse_forn:,.2f}</h4>", unsafe_allow_html=True)
                        
                        else:
                            df_editado_forn = st.data_editor(
                                df_forn_atual, column_order=ordem_col, column_config=cfg_colunas, disabled=["Total"], 
                                num_rows="dynamic", use_container_width=True, hide_index=True,
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
                    
                    if tipo_perfil != "Fiscal" and houve_alteracao:
                        df_final_para_salvar = pd.concat(df_atualizado_acumulado, ignore_index=True)
                        df_final_para_salvar["Total"] = df_final_para_salvar["Valor Unitário"].astype(float) * df_final_para_salvar["Qtd"].astype(int)
                        
                        banco_dados[nc_selecionada_vis]["itens"] = df_final_para_salvar.to_dict(orient="records")
                        salvar_dados(banco_dados)
                        st.session_state.banco = banco_dados
                        st.toast("✅ Alteração salva automaticamente!")
                        st.rerun()
    else:
         st.info("Nenhuma NC cadastrada para este ano nesta seção.")

# =====================================================================
# ABA 3: VISÃO GLOBAL ANUAL (Diferente para Operador e Fiscal)
# =====================================================================
with menu_visao_global:
    
    dados_anuais = []
    
    if tipo_perfil == "Fiscal":
        st.subheader(f"🌐 Visão Corporativa da OM ({om_user}) - Todas as Seções")
        st.markdown("Este gráfico consolida e cruza as planilhas de **todas as seções** do Batalhão de forma automatizada.")
        
        resp_todas_secoes = supabase.table("dados").select("*").like("id", f"{om_user}_%").execute()
        
        for linha in resp_todas_secoes.data:
            banco_secao_laco = linha.get("ncs", {})
            for nc in banco_secao_laco.keys():
                if nc != "CONFIG_REQUISICAO" and extrair_ano(nc) == ano_selecionado:
                    nd_atual = banco_secao_laco[nc].get("nd", "Não informada")
                    for item in banco_secao_laco[nc].get("itens", []):
                        valor_total_item = float(item.get("Valor Unitário", 0.0)) * int(item.get("Qtd", 0))
                        dados_anuais.append({
                            "ND": nd_atual,
                            "Situação": item.get("Situação", "Situação Indefinida"),
                            "Valor Total": valor_total_item
                        })
    else:
        st.subheader(f"📊 Resumo Geral de Empenhos e Aquisições - Seção: {secao_ativa}")
        st.markdown("Este gráfico consolida os valores agrupados por **Natureza de Despesa (ND)** e empilhados pela sua respectiva **Situação Atual**.")
        
        if ncs_do_ano:
            for nc in ncs_do_ano:
                nd_atual = banco_dados[nc].get("nd", "Não informada")
                if not nd_atual.strip(): nd_atual = "Não informada"
                    
                itens_da_nc = banco_dados[nc].get("itens", [])
                for item in itens_da_nc:
                    valor_total_item = float(item.get("Valor Unitário", 0.0)) * int(item.get("Qtd", 0))
                    situacao = item.get("Situação", "Situação Indefinida")
                    
                    dados_anuais.append({
                        "ND": nd_atual,
                        "Situação": situacao,
                        "Valor Total": valor_total_item
                    })
                    
    if dados_anuais:
        df_anual = pd.DataFrame(dados_anuais)
        df_agrupado = df_anual.groupby(["ND", "Situação"])["Valor Total"].sum().reset_index()
        
        escala_cores = alt.Scale(
            domain=["Recebido", "Planejamento", "Aguardando entrega"],
            range=["#28a745", "#007bff", "#dc3545"]
        )
        
        grafico_anual = alt.Chart(df_agrupado).mark_bar().encode(
            x=alt.X("ND:N", title="Natureza de Despesa (ND)"),
            y=alt.Y("Valor Total:Q", title="Total (R$)"),
            color=alt.Color("Situação:N", scale=escala_cores, title="Status do Recurso"),
            tooltip=[
                alt.Tooltip("ND:N", title="ND"),
                alt.Tooltip("Situação:N", title="Status"),
                alt.Tooltip("Valor Total:Q", title="Valor Calculado (R$)", format=",.2f")
            ]
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
        st.info("Não há itens registrados para exibição no painel global.")

# =====================================================================
# ABA 4: GERENCIAR ACESSOS E EQUIPE (Apenas Chefe e Fiscal)
# =====================================================================
with menu_acessos:
    if tipo_perfil == "Operador":
        st.warning("⚠️ **Acesso Restrito:** O seu perfil de Operador não tem permissão para cadastrar novos usuários. Solicite ao Chefe da sua Seção.")
    else:
        st.subheader("👥 Painel de Controle de Usuários")
        if tipo_perfil == "Chefe":
            st.info(f"Como **Chefe**, você pode criar contas de novos **Operadores** para a seção {secao_user}.")
            opcoes_perfil_novo = ["Operador"]
            secoes_permitidas = [secao_user]
        else:
            st.info(f"Como **Fiscal**, você pode cadastrar os **Chefes** e **Operadores** de qualquer seção do {om_user}.")
            opcoes_perfil_novo = ["Chefe", "Operador"]
            
            resp_secoes_gerais = supabase.table("usuarios").select("secao").eq("om", om_user).execute()
            secoes_permitidas = sorted(list(set([r["secao"] for r in resp_secoes_gerais.data])))
            secoes_permitidas.append("NOVA SEÇÃO...")
            
        with st.form("form_novo_usuario_interno"):
            col_add1, col_add2 = st.columns(2)
            with col_add1:
                novo_int_user = st.text_input("Usuário de Login:").strip().lower()
                novo_int_nome = st.text_input("Nome/Posto (Ex: Cb Silva):")
            with col_add2:
                novo_int_senha = st.text_input("Definir Senha Temporária:", type="password")
                novo_int_perfil = st.selectbox("Nível de Acesso:", opcoes_perfil_novo)
                
            if tipo_perfil == "Fiscal":
                secao_selecionada = st.selectbox("Vincular à Seção:", secoes_permitidas)
                if secao_selecionada == "NOVA SEÇÃO...":
                    secao_final = st.text_input("Digite o nome da Nova Seção (Ex: ALMOX):").strip().upper()
                else:
                    secao_final = secao_selecionada
            else:
                secao_final = secao_user
                
            if st.form_submit_button("Cadastrar Novo Militar", type="primary", use_container_width=True):
                if not novo_int_user or not novo_int_senha or not novo_int_nome or not secao_final:
                    st.warning("Preencha todos os campos para cadastrar o militar.")
                else:
                    verifica_existencia = supabase.table("usuarios").select("id").eq("id", novo_int_user).execute()
                    if len(verifica_existencia.data) > 0:
                        st.error("Este usuário já existe no sistema.")
                    else:
                        supabase.table("usuarios").insert({
                            "id": novo_int_user, "senha": novo_int_senha, "nome": novo_int_nome,
                            "om": om_user, "secao": secao_final, "perfil": novo_int_perfil
                        }).execute()
                        
                        id_cofre = f"{om_user}_{secao_final}"
                        verifica_cofre = supabase.table("dados").select("id").eq("id", id_cofre).execute()
                        if len(verifica_cofre.data) == 0:
                            supabase.table("dados").insert({"id": id_cofre, "ncs": {}}).execute()
                        
                        st.success(f"✅ Conta criada com sucesso para {novo_int_nome} na Seção {secao_final}!")
