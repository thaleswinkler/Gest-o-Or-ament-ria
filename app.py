import sys
import asyncio
import warnings

warnings.filterwarnings("ignore")

if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import streamlit.components.v1 as components
import hashlib
import re
import io
import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple, Optional, List, Dict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Gerenciador de Recursos & Pregões",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 2. CONSTANTES E CONEXÃO SUPABASE
# =====================================================================
URL = "https://oxneqoegehufjksvupji.supabase.co"
KEY = "sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX"
supabase: Client = create_client(URL, KEY)

SIASG_BASE = "https://www2.comprasnet.gov.br/siasgnet-atasrp/public"
URL_PESQUISA_SIASG = f"{SIASG_BASE}/pesquisarLicitacaoSRP.do"
URL_ITENS_SIASG = f"{SIASG_BASE}/pesquisarItemSRP.do"
BASE_CONTRATOS = "https://contratos.sistema.gov.br"

HEADERS_HTTP = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

# =====================================================================
# 3. FUNÇÕES UTILITÁRIAS DO SISTEMA
# =====================================================================
def hash_senha(senha: str) -> str:
    """Gera hash criptográfico SHA-256 para senhas."""
    if not senha:
        return ""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

def checar_senha(senha_digitada: str, senha_db: str) -> bool:
    """Valida senha suportando hash seguro SHA-256 e texto simples antigo."""
    if not senha_db:
        return False
    if senha_db == senha_digitada:
        return True
    return senha_db == hash_senha(senha_digitada)

def formatar_cnpj(cnpj_raw: str) -> str:
    """Padroniza CNPJ no formato 00.000.000/0000-00."""
    if not cnpj_raw:
        return "NÃO INFORMADO"
    apenas_numeros = re.sub(r"\D", "", str(cnpj_raw))
    if len(apenas_numeros) == 14:
        return f"{apenas_numeros[:2]}.{apenas_numeros[2:5]}.{apenas_numeros[5:8]}/{apenas_numeros[8:12]}-{apenas_numeros[12:]}"
    return cnpj_raw.strip().upper()

def extrair_ano(nc_nome: str) -> str:
    """Extrai os 4 dígitos iniciais se forem ano, senão agrupa como 'Sem Ano' para segurança de abas Excel."""
    if len(nc_nome) >= 4 and nc_nome[:4].isdigit():
        return nc_nome[:4]
    return "Sem Ano"

def limpar_nome_aba(nome: str) -> str:
    """Remove caracteres proibidos pelo Excel em títulos de abas e limita a 30 caracteres."""
    if not nome:
        return "Resumo"
    nome_limpo = re.sub(r"[\/\\:\?\*\[\]]", "-", str(nome)).strip()
    return nome_limpo[:30]

def converter_para_float(val_str: str) -> float:
    """Converte valores em formatos numéricos variados para float com segurança."""
    if not val_str:
        return 0.0
    s = str(val_str).strip()
    s = re.sub(r"[^\d,\.]", "", s)
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.find(".") < s.find(","):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def limpar_descricao_ata(texto: str) -> str:
    """Extrai estritamente a especificação do material, removendo metadados de tabelas e cabeçalhos."""
    if not texto:
        return ""
    
    t = texto.replace("\xa0", " ").strip()
    
    # 1. Divisores de campos do Comprasnet e Contratos.gov.br
    divisores = [
        r"código do item", r"codigo do item",
        r"tipo do item", r"tipo de item",
        r"unidade de fornecimento", r"unidade de medida", r"unidade de compra",
        r"critério de julgamento", r"criterio de julgamento",
        r"critério de valor", r"criterio de valor",
        r"situação", r"situacao",
        r"vigência inicial", r"vigencia inicial",
        r"vigência final", r"vigencia final",
        r"quantidade solicitada", r"quantidade homologada", r"quantidade registrada",
        r"quantidade total", r"quantidade máxima", r"quantidade",
        r"valor estimado", r"valor homologado", r"valor unitário", r"valor unitario",
        r"valor total", r"saldo para empenho", r"saldo a empenhar", r"saldo empenho",
        r"classificação cnpj", r"classificação", r"classificacao",
        r"cnpj", r"fornecedor", r"razão social", r"razao social",
        r"marca/fabricante", r"marca", r"fabricante", r"modelo", r"versão", r"versao",
        r"tratamento diferenciado", r"aplicabilidade margem", r"decreto 7174",
        r"subcontratação", r"subcontratacao",
        r"informações complementares", r"informacoes complementares",
        r"item do tr", r"item da compra", r"item do pregão",
        r"item\s*:\s*\d+", r"grupo\s*:\s*\d+",
        r"benefício", r"beneficio", r"local de entrega", r"prazo de entrega"
    ]
    
    # Corta antes do primeiro divisor de sistema encontrado
    padrao_regex = r"(?:\b(?:" + "|".join(divisores) + r")\s*[:\-])"
    partes = re.split(padrao_regex, t, flags=re.IGNORECASE)
    if partes:
        t = partes[0].strip()

    # 2. Remove prefixos de cabeçalho de descrição
    t = re.sub(r"^(?:especificação|especificacao|descrição detalhada|descrição do item|descrição|descricao|especificação técnica|objeto)\s*[:\-]\s*", "", t, flags=re.IGNORECASE).strip()
    
    # 3. Remove código CATMAT inicial do SIASG (ex: '603635 - Caixa' -> 'Caixa')
    t = re.sub(r"^\d{4,8}\s*[-–]\s*", "", t).strip()

    # 4. Remove numeração de item inicial (ex: 'Item 1 - ' ou '1 - ')
    t = re.sub(r"^(?:item\s*)?\d{1,4}\s*[-–:]\s*", "", t, flags=re.IGNORECASE).strip()

    # 5. Remove pontuações estranhas residuais e normaliza espaços
    t = re.sub(r"\s+", " ", t).strip(" ,;:-")
    return t

def limpar_nome_fornecedor(texto: str, cnpj: str = "") -> str:
    """Extrai estritamente a Razão Social limpa da empresa, eliminando cabeçalhos de tabela colados, CNPJ e valores."""
    if not texto:
        return ""
    t = texto.replace("\xa0", " ").strip()

    # Se o CNPJ estiver no texto, pega o que vem após ele (onde geralmente fica a Razão Social)
    if cnpj and cnpj in t:
        partes = t.split(cnpj)
        if len(partes) > 1 and len(partes[1].strip()) >= 3:
            t = partes[1].strip()
        else:
            t = partes[0].strip()

    # Remove qualquer CNPJ residual do texto
    t = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", " ", t)

    # Remove termos de cabeçalho colados de tabelas do Contratos.gov.br
    cabecalhos_lixo = [
        r"classificação", r"classificacao", r"cnpj", r"fornecedor",
        r"razão social", r"razao social", r"quantidade total", r"quantidade homologada",
        r"quantidade registrada", r"quantidade", r"valor unitário", r"valor unitario",
        r"vlr\. unitário", r"vlr unitário", r"vlr", r"total", r"item", r"marca", r"modelo"
    ]
    padrao_cab = r"\b(?:" + "|".join(cabecalhos_lixo) + r")\b"
    t = re.sub(padrao_cab, " ", t, flags=re.IGNORECASE)

    # Remove sequenciais de classificação no início (ex: '001', '01', '1 -')
    t = re.sub(r"^\s*\d{1,4}\s*[-–]?\s*", "", t)

    # Corta assim que encontra o início de valores/quantidades (ex: '50,0000', 'R$ 157,00')
    t = re.split(r"(?:\d+[\.,]\d+|R\$|\b\d+\s*$)", t)[0].strip()

    # Limpa pontuações nas extremidades e normaliza espaços
    t = re.sub(r"^[\s\-_:.]+|[\s\-_:.]+$", "", t).strip()
    t = re.sub(r"\s+", " ", t).strip()

    # Se o nome ficou vazio ou apenas com números/pontos e temos o CNPJ, consulta a Razão Social oficial
    if (not t or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", t)) == 0) and cnpj:
        nome_oficial = consultar_razao_social_cnpj(cnpj)
        if nome_oficial:
            return nome_oficial

    return t

@st.cache_data(ttl=86400)
def consultar_razao_social_cnpj(cnpj: str) -> str:
    """Consulta a Razão Social oficial da empresa pelo CNPJ via APIs governamentais abertas com cache de 24h."""
    if not cnpj:
        return ""
    clean = "".join(filter(str.isdigit, str(cnpj)))
    if len(clean) != 14:
        return ""

    # 1. BrasilAPI (aberta, ultrarrápida, sem rate limit restritivo)
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{clean}"
        r = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
        if r.ok:
            data = r.json()
            nome = data.get("razao_social") or data.get("nome") or ""
            if nome:
                return nome.strip().upper()
    except Exception:
        pass

    # 2. Minha Receita (fallback rápido)
    try:
        url = f"https://minhareceita.org/{clean}"
        r = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
        if r.ok:
            data = r.json()
            nome = data.get("razao_social") or data.get("nome") or ""
            if nome:
                return nome.strip().upper()
    except Exception:
        pass

    # 3. ReceitaWS (fallback de segurança)
    try:
        url = f"https://receitaws.com.br/v1/cnpj/{clean}"
        r = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
        if r.ok:
            data = r.json()
            nome = data.get("nome") or data.get("razao_social") or ""
            if nome:
                return nome.strip().upper()
    except Exception:
        pass

    return ""

# =====================================================================
# 4. MÓDULO DE RASTREAMENTO E INTEGRAÇÃO SIASG / CONTRATOS.GOV.BR
# =====================================================================
@st.cache_resource
def get_http_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def iniciar_sessao_siasg(session: requests.Session) -> None:
    try:
        session.get(f"{URL_PESQUISA_SIASG}?method=iniciar", headers=HEADERS_HTTP, verify=False, timeout=12)
    except Exception:
        pass

def obter_id_unidade_contratos(session: requests.Session, uasg: str) -> Optional[int]:
    uasg_clean = uasg.strip()
    if 'cache_unidades' not in st.session_state:
        st.session_state['cache_unidades'] = {}
    if uasg_clean in st.session_state['cache_unidades']:
        return st.session_state['cache_unidades'][uasg_clean]

    try:
        url = f"{BASE_CONTRATOS}/arp/ajax-unidade-options?q={uasg_clean}"
        res = session.get(url, headers=HEADERS_HTTP, timeout=10)
        if res.ok:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                match = next((x for x in data if uasg_clean in x.get('nome', '')), data[0])
                uid = match.get('id')
                st.session_state['cache_unidades'][uasg_clean] = uid
                return uid
    except Exception:
        pass
    return None

def buscar_atas_contratos(session: requests.Session, uasg: str, num_compra: str, ano_compra: str) -> List[Dict]:
    if 'cache_atas' not in st.session_state:
        st.session_state['cache_atas'] = {}
    cache_key = f"{uasg}-{num_compra}-{ano_compra}"
    if cache_key in st.session_state['cache_atas']:
        return st.session_state['cache_atas'][cache_key]

    from bs4 import BeautifulSoup
    id_unidade = obter_id_unidade_contratos(session, uasg)
    arp_ids: List[str] = []
    
    page = 1
    has_more = True
    while has_more and page <= 5:
        url = f"{BASE_CONTRATOS}/transparencia/arp?situacao=vigente&numeroCompra={num_compra}&anoCompra={ano_compra}"
        if id_unidade:
            url += f"&unidadesGerenciadoras[]={id_unidade}"
        if page > 1:
            url += f"&page={page}"

        try:
            res = session.get(url, headers=HEADERS_HTTP, timeout=15)
            if not res.ok:
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            novos = 0
            for a in soup.find_all('a', href=True):
                m = re.search(r"/transparencia/arpshow/(\d+)/show", a['href'])
                if m:
                    arp_id = m.group(1)
                    if arp_id not in arp_ids:
                        arp_ids.append(arp_id)
                        novos += 1

            proxima_pag = soup.find('a', href=re.compile(rf"page={page + 1}"))
            if novos == 0 or not proxima_pag:
                has_more = False
            else:
                page += 1
        except Exception:
            break

    atas_detalhadas: List[Dict] = []
    for arp_id in arp_ids:
        try:
            url_arp = f"{BASE_CONTRATOS}/transparencia/arpshow/{arp_id}/show"
            r_arp = session.get(url_arp, headers=HEADERS_HTTP, timeout=12)
            if not r_arp.ok:
                continue
            s_arp = BeautifulSoup(r_arp.text, 'html.parser')
            
            num_ata = ""
            for lbl in s_arp.find_all('label'):
                txt = lbl.get_text(strip=True)
                if re.match(r"\d{5}/\d{4}", txt) and not num_ata:
                    num_ata = txt
            
            pdf_url = ""
            for tbl in s_arp.find_all('table'):
                ths = [th.get_text(strip=True).lower() for th in tbl.find_all('th')]
                if any(h in ['tipo', 'incluído em', 'descrição', 'ação'] for h in ths):
                    for tr in tbl.find_all('tr'):
                        tr_txt = tr.get_text(strip=True).lower()
                        if 'ata de registro de preços' in tr_txt or 'ata' in tr_txt:
                            a_link = tr.find('a', href=True)
                            if a_link:
                                h = a_link['href'].strip()
                                if ('/storage/arp/' in h or h.lower().endswith('.pdf')) and 'manual' not in h.lower():
                                    pdf_url = h if h.startswith('http') else f"{BASE_CONTRATOS}{h}"
                                    break
                    if pdf_url:
                        break

            if not pdf_url:
                for a in s_arp.find_all('a', href=True):
                    h = a['href'].strip()
                    title = a.get('title', '').lower()
                    if 'manual' in h.lower():
                        continue
                    if '/storage/arp/' in h or 'baixar' in title or a.find('i', class_=re.compile(r'download')):
                        pdf_url = h if h.startswith('http') else f"{BASE_CONTRATOS}{h}"
                        break
            
            itens_olho = {}
            for tbl in s_arp.find_all('table'):
                ths = [th.get_text(strip=True) for th in tbl.find_all('th')]
                if any('Item' in h or 'Número' in h for h in ths):
                    for tr in tbl.find_all('tr'):
                        tds = tr.find_all('td')
                        if len(tds) >= 2:
                            raw_num = tds[0].get_text(strip=True)
                            a_eye = tr.find('a', href=re.compile(r"/arpshow/itens/"))
                            if raw_num and a_eye:
                                link_eye = a_eye['href'].strip()
                                link_eye = link_eye if link_eye.startswith('http') else f"{BASE_CONTRATOS}{link_eye}"
                                itens_olho[raw_num] = link_eye

            atas_detalhadas.append({
                "arpId": arp_id,
                "numeroAta": num_ata or f"ARP {arp_id}",
                "pdfUrl": pdf_url,
                "linkAta": url_arp,
                "itensOlho": itens_olho
            })
        except Exception:
            continue

    st.session_state['cache_atas'][cache_key] = atas_detalhadas
    return atas_detalhadas

def obter_saldo_item_contratos(session: requests.Session, uasg: str, num_compra: str, ano_compra: str, num_item: str) -> Dict:
    from bs4 import BeautifulSoup
    atas = buscar_atas_contratos(session, uasg, num_compra, ano_compra)
    num_int = int(num_item) if num_item.isdigit() else 0
    num_5 = str(num_int).zfill(5)

    target_eye_url = ""
    target_ata = None

    for ata in atas:
        for it_key, eye_url in ata.get("itensOlho", {}).items():
            clean_it_key = re.sub(r"\D", "", it_key)
            if clean_it_key and int(clean_it_key) == num_int:
                target_eye_url = re.sub(r"/itens/\d+/", f"/itens/{num_5}/", eye_url.strip())
                target_ata = ata
                break
        if target_eye_url:
            break

    if not target_eye_url and atas:
        target_ata = atas[0]
        target_eye_url = f"{BASE_CONTRATOS}/transparencia/arpshow/itens/{num_5}/{target_ata['arpId']}/show"

    resultado = {
        "qtd_registrada": "0",
        "qtd_empenhada": "0",
        "saldo_empenho": "0",
        "fornecedor": "",
        "fornecedor_puro": "",
        "cnpj_puro": "",
        "valor_unitario_sugerido": 0.0,
        "descricao_detalhada_ata": "",
        "empenhos_resumo": "Nenhum",
        "empenhos_lista": [],
        "numero_ata": target_ata["numeroAta"] if target_ata else "",
        "pdf_ata": target_ata["pdfUrl"] if target_ata else ""
    }

    if not target_eye_url:
        return resultado

    try:
        res = session.get(target_eye_url.strip(), headers=HEADERS_HTTP, timeout=15)
        if not res.ok:
            return resultado

        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Extração Limpa e Específica da Descrição Técnica / Especificação
        for tag in soup.find_all(['div', 'p', 'span', 'td', 'dd', 'li']):
            txt_linhas = tag.get_text(separator='\n', strip=True).split('\n')
            for i_l, linha in enumerate(txt_linhas):
                if re.search(r"^(?:especificação|descrição detalhada|descrição do item)\s*:", linha, re.IGNORECASE):
                    conteudo = re.sub(r"^(?:especificação|descrição detalhada|descrição do item)\s*:\s*", "", linha, flags=re.IGNORECASE).strip()
                    if not conteudo and i_l + 1 < len(txt_linhas):
                        conteudo = txt_linhas[i_l + 1].strip()
                    desc_limpa = limpar_descricao_ata(conteudo)
                    if len(desc_limpa) > 3:
                        resultado["descricao_detalhada_ata"] = desc_limpa
                        break
            if resultado["descricao_detalhada_ata"]:
                break

        if not resultado["descricao_detalhada_ata"]:
            for strong in soup.find_all(['strong', 'b', 'label', 'dt', 'th']):
                if any(w in strong.get_text().lower() for w in ["especificação", "especificacao", "descrição detalhada", "descrição do item"]):
                    prox = strong.find_next_sibling(['span', 'p', 'dd', 'div', 'td'])
                    if prox:
                        desc_limpa = limpar_descricao_ata(prox.get_text(separator=' ', strip=True))
                        if len(desc_limpa) > 3:
                            resultado["descricao_detalhada_ata"] = desc_limpa
                            break
                    pai = strong.parent
                    if pai:
                        desc_limpa = limpar_descricao_ata(pai.get_text(separator='\n', strip=True))
                        if len(desc_limpa) > 3:
                            resultado["descricao_detalhada_ata"] = desc_limpa
                            break

        # 2. Extração do Fornecedor, CNPJ e Valor Unitário Real
        for tbl in soup.find_all('table'):
            tbl_txt = tbl.get_text(" ", strip=True).lower()
            if re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", tbl_txt) or "fornecedor" in tbl_txt or "classificação" in tbl_txt:
                for tr in tbl.find_all('tr'):
                    if tr.find('th') and not tr.find('td'):
                        continue
                    
                    tds_leaf = [td for td in tr.find_all('td') if not td.find('table')]
                    if not tds_leaf:
                        continue
                    
                    linha_txt = " ".join(td.get_text(" ", strip=True) for td in tds_leaf)
                    cnpj_m = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", linha_txt)
                    if cnpj_m:
                        found_cnpj = cnpj_m.group(0)
                        resultado["cnpj_puro"] = found_cnpj
                        
                        candidato_nome = ""
                        for td in tds_leaf:
                            t_c = td.get_text(" ", strip=True)
                            # Remove o CNPJ da célula se presente, para ver se há o nome junto
                            t_sem_cnpj = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", t_c).strip()
                            if any(k in t_sem_cnpj.lower() for k in ['classifica', 'quantidade', 'valor unit', 'total', 'vlr', 'item']):
                                continue
                            if re.search(r"[A-Za-zÀ-ÿ]{3,}", t_sem_cnpj) and not re.match(r"^R?\$?\s*\d+", t_sem_cnpj):
                                candidato_nome = t_sem_cnpj
                                break
                        
                        if not candidato_nome:
                            candidato_nome = linha_txt
                        
                        nome_forn_limpo = limpar_nome_fornecedor(candidato_nome, found_cnpj)
                        # Se o nome capturado for vazio, igual ao CNPJ ou não tiver letras, resolve na base oficial
                        if not nome_forn_limpo or nome_forn_limpo == found_cnpj or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", nome_forn_limpo)) == 0:
                            nome_auto = consultar_razao_social_cnpj(found_cnpj)
                            if nome_auto:
                                nome_forn_limpo = nome_auto

                        resultado["fornecedor_puro"] = nome_forn_limpo or found_cnpj
                        if nome_forn_limpo and nome_forn_limpo != found_cnpj:
                            resultado["fornecedor"] = f"{nome_forn_limpo} ({found_cnpj})"
                        else:
                            resultado["fornecedor"] = found_cnpj
                        
                        # Extrai o valor unitário da linha da classificação
                        valores_linha = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2,4})", linha_txt)
                        if valores_linha:
                            resultado["valor_unitario_sugerido"] = converter_para_float(valores_linha[-1])
                        
                        break
            if resultado["cnpj_puro"]:
                break

        # Fallback de valor unitário pelo texto geral se necessário
        if resultado["valor_unitario_sugerido"] == 0.0:
            texto_pagina = soup.get_text(separator=' ', strip=True)
            m_val = re.search(r"valor\s*unit[áa]rio[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2,4})", texto_pagina, re.IGNORECASE)
            if m_val:
                resultado["valor_unitario_sugerido"] = converter_para_float(m_val.group(1))

        # 3. Varredura da Tabela de Saldos da UASG (Imunização Total contra Códigos de UASG e Nomes de OM)
        uasg_clean = uasg.strip()
        reg_encontrada = ""
        emp_encontrada = ""
        sal_encontrada = ""

        for tbl in soup.find_all('table'):
            tbl_txt = tbl.get_text(" ", strip=True).lower()
            if "cnpj" in tbl_txt and "fornecedor" in tbl_txt:
                continue
            if "nota de empenho" in tbl_txt or "número ne" in tbl_txt or "data emissão" in tbl_txt:
                continue

            # Mapeamento de colunas por cabeçalho
            idx_reg = -1
            idx_emp = -1
            idx_sal = -1
            
            hdr_tr = tbl.find('thead')
            if not hdr_tr:
                hdr_tr = tbl.find('tr')
            if hdr_tr:
                th_list = [th.get_text(" ", strip=True).lower() for th in hdr_tr.find_all(['th', 'td'])]
                for i_col, col_name in enumerate(th_list):
                    if any(k in col_name for k in ['registrad', 'homologad', 'solicitad', 'autorizad']) and not any(s in col_name for s in ['saldo', 'empenh']) and idx_reg == -1:
                        idx_reg = i_col
                    elif any(k in col_name for k in ['empenhad', 'empenho', 'atendid', 'consumid', 'utilizad']) and not any(s in col_name for s in ['saldo', 'remanescente']) and idx_emp == -1:
                        idx_emp = i_col
                    elif any(k in col_name for k in ['saldo', 'remanescente', 'disponív', 'disponiv']) and idx_sal == -1:
                        idx_sal = i_col

            for tr in tbl.find_all('tr'):
                if tr.find('th') and not tr.find('td'):
                    continue
                tds_leaf = [td.get_text(" ", strip=True) for td in tr.find_all('td') if not td.find('table')]
                if len(tds_leaf) < 2:
                    continue

                linha_txt = " ".join(tds_leaf).lower()
                eh_nossa_uasg = uasg_clean in linha_txt
                eh_gerenciadora = "gerenciadora" in linha_txt and not "não" in linha_txt

                if not (eh_nossa_uasg or eh_gerenciadora):
                    continue

                # 1ª Tentativa: usar os índices mapeados pelos cabeçalhos com checagem estrita
                if idx_reg != -1 and idx_reg < len(tds_leaf):
                    c_reg = tds_leaf[idx_reg]
                    if re.match(r"^\d+(?:[.,]\d+)?$", c_reg) and c_reg != uasg_clean:
                        reg_encontrada = c_reg
                        if idx_emp != -1 and idx_emp < len(tds_leaf):
                            c_emp = tds_leaf[idx_emp]
                            if re.match(r"^\d+(?:[.,]\d+)?$", c_emp) and c_emp != uasg_clean:
                                emp_encontrada = c_emp
                        if idx_sal != -1 and idx_sal < len(tds_leaf):
                            c_sal = tds_leaf[idx_sal]
                            if re.match(r"^\d+(?:[.,]\d+)?$", c_sal) and c_sal != uasg_clean:
                                sal_encontrada = c_sal
                        
                        if reg_encontrada and (emp_encontrada or sal_encontrada):
                            if eh_nossa_uasg:
                                break

                # 2ª Tentativa: extração das células puramente numéricas candidatas a quantidade
                qtd_candidatos = []
                for cell in tds_leaf:
                    c_val = cell.strip()
                    # Rejeita texto/letras (ex: '23 B I', 'Gerenciadora', 'Infantaria')
                    if any(ch.isalpha() for ch in c_val):
                        continue
                    # Rejeita o próprio código da UASG (ex: '160440')
                    if c_val == uasg_clean:
                        continue
                    # Rejeita datas ou CNPJs
                    if "/" in c_val or "-" in c_val:
                        continue
                    # Aceita números decimais ou inteiros
                    if re.match(r"^\d+(?:[.,]\d+)?$", c_val):
                        qtd_candidatos.append(c_val)

                if len(qtd_candidatos) >= 3:
                    c0_f = converter_para_float(qtd_candidatos[0])
                    c1_f = converter_para_float(qtd_candidatos[1])
                    c2_f = converter_para_float(qtd_candidatos[2])
                    # Verifica matematicamente a relação: Registrada - Empenhada = Saldo
                    if abs((c0_f - c1_f) - c2_f) < 0.001:
                        reg_encontrada = qtd_candidatos[0]
                        emp_encontrada = qtd_candidatos[1]
                        sal_encontrada = qtd_candidatos[2]
                    elif abs((c0_f - c2_f) - c1_f) < 0.001:
                        reg_encontrada = qtd_candidatos[0]
                        sal_encontrada = qtd_candidatos[1]
                        emp_encontrada = qtd_candidatos[2]
                    else:
                        reg_encontrada = qtd_candidatos[0]
                        emp_encontrada = qtd_candidatos[1]
                        sal_encontrada = qtd_candidatos[2]
                    if eh_nossa_uasg:
                        break
                elif len(qtd_candidatos) == 2:
                    c0_f = converter_para_float(qtd_candidatos[0])
                    c1_f = converter_para_float(qtd_candidatos[1])
                    reg_encontrada = qtd_candidatos[0]
                    # No Contratos.gov.br a tabela padrão de participantes traz Registrada e Saldo para Empenho!
                    # Se idx_sal aponta para a 2ª coluna numérica ou não há coluna explícita de empenho:
                    if idx_sal != -1 or (idx_emp == -1 and c1_f <= c0_f):
                        sal_encontrada = qtd_candidatos[1]
                        diff_emp = max(0.0, c0_f - c1_f)
                        emp_encontrada = f"{diff_emp:.5f}" if "." in qtd_candidatos[0] else f"{diff_emp:g}"
                    else:
                        emp_encontrada = qtd_candidatos[1]
                        diff_sal = max(0.0, c0_f - c1_f)
                        sal_encontrada = f"{diff_sal:.5f}" if "." in qtd_candidatos[0] else f"{diff_sal:g}"
                    if eh_nossa_uasg:
                        break
                elif len(qtd_candidatos) == 1:
                    reg_encontrada = qtd_candidatos[0]
                    emp_encontrada = "0"
                    sal_encontrada = qtd_candidatos[0]
                    if eh_nossa_uasg:
                        break

            if reg_encontrada:
                resultado["qtd_registrada"] = reg_encontrada
                resultado["qtd_empenhada"] = emp_encontrada or "0"
                resultado["saldo_empenho"] = sal_encontrada or reg_encontrada
                break

        # 4. Varredura de Todas as Notas de Empenho (NE) Cadastradas e Soma Total Empenhada
        soma_empenhos_ne = 0.0
        empenhos_list = []
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            linha_tr_txt = " ".join(td.get_text(" ", strip=True) for td in tds)
            m_ne = re.search(r"\b(\d{4}NE\d{4,6})\b", linha_tr_txt, re.IGNORECASE)
            if m_ne:
                ne_num = m_ne.group(1).upper()
                d_ne = ""
                q_ne_val = 0.0
                v_ne_str = ""
                for td in tds:
                    c_txt = td.get_text(strip=True)
                    if re.match(r"^\d{2}/\d{2}/\d{4}$", c_txt):
                        d_ne = c_txt
                    elif re.match(r"^\d+(?:[.,]\d+)?$", c_txt) and c_txt != uasg_clean and not re.match(r"^\d{4}$", c_txt):
                        q_cand = converter_para_float(c_txt)
                        if q_cand > 0 and q_cand < 10000000:
                            q_ne_val = q_cand
                    elif "r$" in c_txt.lower() or re.match(r"^\d{1,3}(?:\.\d{3})*,\d{2}$", c_txt):
                        v_ne_str = c_txt

                if q_ne_val > 0:
                    soma_empenhos_ne += q_ne_val

                emp_str = ne_num
                if d_ne: emp_str += f" ({d_ne})"
                if q_ne_val > 0: emp_str += f": Qtd {q_ne_val:g}"
                if v_ne_str: emp_str += f" [{v_ne_str}]"
                if emp_str not in empenhos_list:
                    empenhos_list.append(emp_str)

        if empenhos_list:
            resultado["empenhos_resumo"] = " | ".join(empenhos_list)
            resultado["empenhos_lista"] = empenhos_list
            f_emp_ant = converter_para_float(resultado["qtd_empenhada"])
            if soma_empenhos_ne > f_emp_ant:
                resultado["qtd_empenhada"] = f"{soma_empenhos_ne:.5f}" if "." in str(resultado["qtd_registrada"]) else f"{soma_empenhos_ne:g}"

        # 5. REGRA DEFINITIVA DE SALDO DO USUÁRIO: SALDO = REGISTRADA - EMPENHADA
        f_reg = converter_para_float(resultado["qtd_registrada"])
        f_emp = converter_para_float(resultado["qtd_empenhada"])
        diff_final = max(0.0, f_reg - f_emp)
        if "." in str(resultado["qtd_registrada"]):
            resultado["saldo_empenho"] = f"{diff_final:.5f}"
        else:
            resultado["saldo_empenho"] = f"{diff_final:g}"

    except Exception:
        pass

    return resultado

def extrair_pregoes_por_ano(session: requests.Session, uasg: str, ano: str) -> List[Dict]:
    from bs4 import BeautifulSoup
    payload = {
        'method': 'pesquisar',
        'parametro.uasg.numeroUasg': uasg.strip(),
        'parametro.codigosModalidadeCompra': '5',
        'parametro.anoLicitacao': str(ano).strip(),
    }

    response = session.post(URL_PESQUISA_SIASG, data=payload, headers=HEADERS_HTTP, verify=False, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    tabela = soup.find('table', {'id': 'licitacao'}) or soup.find('table', {'class': 'dados'})
    if not tabela:
        return []

    dados = []
    for linha in tabela.find_all('tr')[1:]:
        colunas = linha.find_all('td')
        if len(colunas) < 5:
            continue

        uasg_row = colunas[0].get_text(strip=True)
        if "nenhum" in uasg_row.lower():
            continue

        modalidade = colunas[1].get_text(strip=True)
        num_licitacao = colunas[2].get_text(strip=True)
        objeto = colunas[3].get_text(strip=True)

        link_tag = colunas[4].find('a')
        js_code = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
        match = re.search(r"selecionarLicitacao\s*\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?(\d+)['\"]?\s*,\s*(\d+)", js_code)

        num_compra = ""
        ano_compra = str(ano)
        cod_licitacao = ""

        if match:
            num_compra = match.group(3)
            ano_compra = match.group(4)
            cod_licitacao = match.group(5)
        elif "/" in num_licitacao:
            parts = num_licitacao.split("/")
            num_compra = parts[0]
            ano_compra = parts[1]

        dados.append({
            "UASG": uasg_row,
            "Modalidade": modalidade,
            "Nº da Licitação": num_licitacao,
            "Ano": ano_compra,
            "Objeto": objeto,
            "Nº Compra": num_compra,
            "Ano Compra": ano_compra,
            "Código Licitação": cod_licitacao,
            "Link Contratos": f"{BASE_CONTRATOS}/transparencia/arp?numeroCompra={num_compra}&anoCompra={ano_compra}"
        })

    return dados

def extrair_pregoes_siasg(uasg: str, anos: List[str]) -> Tuple[pd.DataFrame, Optional[str]]:
    session = get_http_session()
    iniciar_sessao_siasg(session)

    todos_dados = []
    erros = []

    for ano in anos:
        try:
            dados_ano = extrair_pregoes_por_ano(session, uasg, ano)
            todos_dados.extend(dados_ano)
        except Exception as e:
            erros.append(f"Ano {ano}: {str(e)}")

    if not todos_dados and erros:
        return pd.DataFrame(), f"Falha na consulta: {'; '.join(erros)}"

    df = pd.DataFrame(todos_dados)
    if not df.empty:
        df.drop_duplicates(subset=["Nº da Licitação"], inplace=True)
        df.sort_values(by=["Ano", "Nº da Licitação"], ascending=[False, False], inplace=True)

    return df, None

def buscar_itens_com_saldo_real(uasg: str, num_compra: str, ano_compra: str) -> List[Dict]:
    from bs4 import BeautifulSoup
    session = get_http_session()
    iniciar_sessao_siasg(session)

    itens_detectados = []
    vistos = set()

    def parsear_pagina_itens(html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        tabela = soup.find('table', {'id': 'item'}) or soup.find('table', {'class': 'dados'})
        if not tabela:
            return 1

        for tr in tabela.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) < 5:
                continue

            num_item = tds[0].get_text(strip=True)
            tipo_item = tds[1].get_text(strip=True)
            desc_item = tds[2].get_text(strip=True)
            qtd_item = tds[3].get_text(strip=True)
            unidade = tds[4].get_text(strip=True)

            if num_item not in vistos:
                vistos.add(num_item)
                itens_detectados.append({
                    "Item": num_item,
                    "Tipo": tipo_item,
                    "Descrição": desc_item,
                    "Qtd SIASG": qtd_item,
                    "Unidade": unidade
                })

        pags = re.findall(r"numeroPagina=(\d+)", html)
        return max([int(p) for p in pags], default=1)

    try:
        url_itens = (
            f"{URL_ITENS_SIASG}?method=iniciar"
            f"&parametro.identificacaoCompra.numeroUasg={uasg.strip()}"
            f"&parametro.identificacaoCompra.modalidadeCompra=5"
            f"&parametro.identificacaoCompra.numeroCompra={num_compra}"
            f"&parametro.identificacaoCompra.anoCompra={ano_compra}"
        )
        res = session.get(url_itens, headers=HEADERS_HTTP, verify=False, timeout=15)
        max_pags = parsear_pagina_itens(res.text)

        for p in range(2, max_pags + 1):
            url_p = (
                f"{URL_ITENS_SIASG}?parametro.identificacaoCompra.anoCompra={ano_compra}"
                f"&numeroPagina={p}&parametro.identificacaoCompra.numeroUasg={uasg.strip()}"
                f"&parametro.identificacaoCompra.modalidadeCompra=5&method=consultarPorFiltro"
                f"&parametro.identificacaoCompra.numeroCompra={num_compra}"
            )
            r_p = session.get(url_p, headers=HEADERS_HTTP, verify=False, timeout=12)
            if r_p.ok:
                parsear_pagina_itens(r_p.text)

        if not itens_detectados:
            return []

        itens_detectados.sort(key=lambda x: int(x["Item"]) if x["Item"].isdigit() else 9999)

        dados_finais = []
        prog_bar = st.progress(0)
        status_txt = st.empty()

        for idx, it in enumerate(itens_detectados):
            status_txt.text(f"Consultando Contratos.gov.br: Item {it['Item']} de {len(itens_detectados)}...")
            saldo_info = obter_saldo_item_contratos(session, uasg, num_compra, ano_compra, it["Item"])

            # Validação rigorosa das quantidades
            raw_reg = str(saldo_info.get("qtd_registrada", "0")).strip()
            if raw_reg == uasg.strip() or any(c.isalpha() for c in raw_reg) or raw_reg == "0":
                qtd_registrada_final = it["Qtd SIASG"]
            else:
                qtd_registrada_final = raw_reg

            raw_emp = str(saldo_info.get("qtd_empenhada", "0")).strip()
            if raw_emp == uasg.strip() or any(c.isalpha() for c in raw_emp):
                qtd_empenhada_final = "0"
            else:
                qtd_empenhada_final = raw_emp

            # Aplicação direta da regra solicitada: Saldo = Registrada - Empenhada
            f_reg = converter_para_float(qtd_registrada_final)
            f_emp = converter_para_float(qtd_empenhada_final)
            diff_saldo = max(0.0, f_reg - f_emp)
            if "." in str(qtd_registrada_final):
                saldo_empenho_calc = f"{diff_saldo:.5f}"
            else:
                saldo_empenho_calc = f"{diff_saldo:g}"

            # Resolução garantida do Nome do Fornecedor e CNPJ
            cnpj_puro = str(saldo_info.get("cnpj_puro", "")).strip()
            forn_puro = str(saldo_info.get("fornecedor_puro", "")).strip()

            # Se temos CNPJ mas o nome está vazio, igual ao CNPJ ou sem letras
            if cnpj_puro and (not forn_puro or forn_puro == cnpj_puro or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", forn_puro)) == 0):
                nome_api = consultar_razao_social_cnpj(cnpj_puro)
                if nome_api:
                    forn_puro = nome_api
                    saldo_info["fornecedor_puro"] = forn_puro

            # Montagem do fornecedor_display (Nome do Fornecedor e CNPJ)
            if forn_puro and cnpj_puro and forn_puro != cnpj_puro:
                fornecedor_display = f"{forn_puro} ({cnpj_puro})"
            elif forn_puro and not cnpj_puro:
                fornecedor_display = forn_puro
            elif cnpj_puro and not forn_puro:
                fornecedor_display = cnpj_puro
            else:
                fornecedor_display = "Deserto / Fracassado"

            # Descrição limpa da ata
            desc_final = saldo_info["descricao_detalhada_ata"] if saldo_info["descricao_detalhada_ata"] else it["Descrição"]
            desc_final = limpar_descricao_ata(desc_final)

            dados_finais.append({
                "Item": it["Item"],
                "Tipo": it["Tipo"],
                "Descrição": desc_final,
                "Descrição Curta SIASG": limpar_descricao_ata(it["Descrição"]),
                "Unidade": it["Unidade"],
                "Qtd Registrada": qtd_registrada_final,
                "Qtd Empenhada": qtd_empenhada_final,
                "Saldo p/ Empenho": saldo_empenho_calc,
                "Ata Vinculada": saldo_info["numero_ata"] or "Não identificada",
                "Fornecedor": fornecedor_display,
                "Fornecedor Puro": saldo_info["fornecedor_puro"],
                "CNPJ Puro": saldo_info["cnpj_puro"],
                "Valor Unitario Sugerido": saldo_info["valor_unitario_sugerido"],
                "PDF da Ata": saldo_info["pdf_ata"],
                "Empenhos": saldo_info["empenhos_resumo"],
                "empenhos_lista": saldo_info.get("empenhos_lista", [])
            })
            prog_bar.progress((idx + 1) / len(itens_detectados))

        status_txt.empty()
        prog_bar.empty()
        return dados_finais

    except Exception as e:
        st.error(f"Erro ao obter itens: {str(e)}")
        return []

# =====================================================================
# 5. GERADORES DE PLANILHAS COMPLETAS (OPENPYXL COM FORMATAÇÃO COMPLETA)
# =====================================================================
def gerar_planilha_nc_completa(nc_nome: str, dados_nc: dict, om_nome: str, secao_nome: str):
    itens = dados_nc.get("itens", [])
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        
        # ABA 1: RESUMO EXECUTIVO
        ws_resumo = wb.active
        ws_resumo.title = limpar_nome_aba("Resumo Executivo")
        ws_resumo.views.sheetView[0].showGridLines = True
        
        ws_resumo.merge_cells("A1:F1")
        ws_resumo["A1"] = f"RELATÓRIO GERENCIAL - NOTA DE CRÉDITO {nc_nome}"
        ws_resumo["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        ws_resumo["A1"].fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        ws_resumo["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws_resumo.row_dimensions[1].height = 35

        ws_resumo["A3"] = "Organização Militar:"; ws_resumo["B3"] = om_nome
        ws_resumo["A4"] = "Seção Responsável:"; ws_resumo["B4"] = secao_nome
        ws_resumo["A5"] = "Nota de Crédito:"; ws_resumo["B5"] = nc_nome
        ws_resumo["A6"] = "Plano Interno (PI):"; ws_resumo["B6"] = dados_nc.get("pi", "Não informado")
        ws_resumo["A7"] = "Natureza Despesa (ND):"; ws_resumo["B7"] = dados_nc.get("nd", "Não informada")
        
        v_rec = float(dados_nc.get("valor_recebido", 0.0))
        v_gasto = sum(float(it.get("Valor Unitário", 0.0)) * int(it.get("Qtd", 0)) for it in itens)
        v_saldo = v_rec - v_gasto
        
        ws_resumo["D3"] = "Valor Total Recebido:"; ws_resumo["E3"] = v_rec; ws_resumo["E3"].number_format = "R$ #,##0.00"
        ws_resumo["D4"] = "Total Comprometido:"; ws_resumo["E4"] = v_gasto; ws_resumo["E4"].number_format = "R$ #,##0.00"
        ws_resumo["D5"] = "Saldo Disponível:"; ws_resumo["E5"] = v_saldo; ws_resumo["E5"].number_format = "R$ #,##0.00"
        
        for row in range(3, 8):
            ws_resumo[f"A{row}"].font = Font(bold=True)
        for row in range(3, 6):
            ws_resumo[f"D{row}"].font = Font(bold=True)

        # ABA 2: ITENS DETALHADOS
        ws_itens = wb.create_sheet(title=limpar_nome_aba("Itens Detalhados"))
        ws_itens.views.sheetView[0].showGridLines = True
        cab_it = ["Item", "Material", "Qtd", "Valor Unitário", "Valor Total", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"]
        for c_idx, h in enumerate(cab_it, 1):
            cell = ws_itens.cell(row=1, column=c_idx, value=h)
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_itens.row_dimensions[1].height = 25

        thin = Side(border_style="thin", color="D3D3D3")
        borda = Border(left=thin, right=thin, top=thin, bottom=thin)

        for r_idx, it in enumerate(itens, start=2):
            q = int(it.get("Qtd", 0))
            vu = float(it.get("Valor Unitário", 0.0))
            vt = q * vu
            
            ws_itens.cell(row=r_idx, column=1, value=it.get("Item")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=2, value=it.get("Nome"))
            ws_itens.cell(row=r_idx, column=3, value=q).alignment = Alignment(horizontal="center")
            
            c_u = ws_itens.cell(row=r_idx, column=4, value=vu)
            c_u.number_format = "R$ #,##0.00"
            c_u.alignment = Alignment(horizontal="right")
            
            c_t = ws_itens.cell(row=r_idx, column=5, value=vt)
            c_t.number_format = "R$ #,##0.00"
            c_t.alignment = Alignment(horizontal="right")
            
            ws_itens.cell(row=r_idx, column=6, value=it.get("Situação")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=7, value=it.get("Fornecedor"))
            ws_itens.cell(row=r_idx, column=8, value=formatar_cnpj(it.get("CNPJ", ""))).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=9, value=it.get("Pregão")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=10, value=it.get("Ata")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=11, value=it.get("UASG")).alignment = Alignment(horizontal="center")
            
            for col_idx in range(1, 12):
                ws_itens.cell(row=r_idx, column=col_idx).border = borda

        for ws in [ws_resumo, ws_itens]:
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"

    except Exception:
        df_exp = pd.DataFrame(itens)
        csv_str = df_exp.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
        return csv_str.encode("utf-8-sig"), "text/csv", "csv"

def gerar_planilha_global_ano_completa(ano: str, banco_dados: dict, om_nome: str, secao_nome: str):
    ncs_do_ano = [nc for nc in banco_dados.keys() if nc != "CONFIG_REQUISICAO" and extrair_ano(nc) == ano]
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws_resumo = wb.active
        ws_resumo.title = limpar_nome_aba(f"Consolidado {ano}")
        ws_resumo.views.sheetView[0].showGridLines = True
        
        ws_resumo.merge_cells("A1:G1")
        ws_resumo["A1"] = f"EXÉRCITO BRASILEIRO - {om_nome} - GESTÃO ORÇAMENTÁRIA {ano}"
        ws_resumo["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        ws_resumo["A1"].fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        ws_resumo["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws_resumo.row_dimensions[1].height = 35

        ws_it_ano = wb.create_sheet(title=limpar_nome_aba(f"Itens {ano}"))
        ws_it_ano.views.sheetView[0].showGridLines = True
        cab_todos = ["NC de Origem", "PI", "ND", "Item", "Nomenclatura", "Qtd", "Valor Unitário", "Valor Total", "Situação", "Fornecedor", "CNPJ", "Pregão"]
        for c_i, h in enumerate(cab_todos, 1):
            cell = ws_it_ano.cell(row=1, column=c_i, value=h)
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_it_ano.row_dimensions[1].height = 25

        thin = Side(border_style="thin", color="D3D3D3")
        borda = Border(left=thin, right=thin, top=thin, bottom=thin)

        row_it = 2
        for nc in ncs_do_ano:
            d_nc = banco_dados[nc]
            for it in d_nc.get("itens", []):
                q = int(it.get("Qtd", 0))
                vu = float(it.get("Valor Unitário", 0.0))
                vt = q * vu
                
                ws_it_ano.cell(row=row_it, column=1, value=nc).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=2, value=d_nc.get("pi", "")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=3, value=d_nc.get("nd", "")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=4, value=it.get("Item")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=5, value=it.get("Nome"))
                ws_it_ano.cell(row=row_it, column=6, value=q).alignment = Alignment(horizontal="center")
                
                c_u = ws_it_ano.cell(row=row_it, column=7, value=vu)
                c_u.number_format = "R$ #,##0.00"
                c_u.alignment = Alignment(horizontal="right")
                
                c_t = ws_it_ano.cell(row=row_it, column=8, value=vt)
                c_t.number_format = "R$ #,##0.00"
                c_t.alignment = Alignment(horizontal="right")
                
                ws_it_ano.cell(row=row_it, column=9, value=it.get("Situação")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=10, value=it.get("Fornecedor"))
                ws_it_ano.cell(row=row_it, column=11, value=formatar_cnpj(it.get("CNPJ", ""))).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=12, value=it.get("Pregão")).alignment = Alignment(horizontal="center")
                
                for col_idx in range(1, 13):
                    ws_it_ano.cell(row=row_it, column=col_idx).border = borda
                row_it += 1

        for ws in [ws_resumo, ws_it_ano]:
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"

    except Exception:
        todos_itens = []
        for nc in ncs_do_ano:
            for it in banco_dados[nc].get("itens", []):
                it_c = it.copy()
                it_c["NC_Origem"] = nc
                todos_itens.append(it_c)
        df_exp = pd.DataFrame(todos_itens)
        csv_str = df_exp.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
        return csv_str.encode("utf-8-sig"), "text/csv", "csv"

# =====================================================================
# 6. TELA DE LOGIN E CADASTRO INICIAL
# =====================================================================
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if st.session_state.usuario_logado is None:
    st.title("🖥 Sistema Profissional de Controle de Recursos & Pregões")
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
                        if checar_senha(senha_login, usuario_db.get("senha", "")):
                            if usuario_db.get("senha") == senha_login:
                                supabase.table("usuarios").update({"senha": hash_senha(senha_login)}).eq("id", usuario_login).execute()
                            
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
                                "id": novo_user, 
                                "senha": hash_senha(nova_senha), 
                                "nome": novo_nome, 
                                "om": nova_om, 
                                "secao": nova_secao, 
                                "perfil": novo_perfil
                            }).execute()
                            
                            id_secao = f"{nova_om}_{nova_secao}"
                            verifica_banco = supabase.table("dados").select("id").eq("id", id_secao).execute()
                            if len(verifica_banco.data) == 0:
                                supabase.table("dados").insert({"id": id_secao, "ncs": {}}).execute()
                                
                            st.success("✅ Conta de Fiscal criada com sucesso! Faça o login ao lado.")
    
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
# 7. CARREGAMENTO DOS DADOS DO MILITAR LOGADO
# =====================================================================
usuario_atual = st.session_state.usuario_logado

resp_perfil = supabase.table("usuarios").select("*").eq("id", usuario_atual).execute()
perfil = resp_perfil.data[0]
om_user = perfil.get("om", "Não informada")
secao_user = perfil.get("secao", "Geral")
tipo_perfil = perfil.get("perfil", "Operador")

# =====================================================================
# 8. BARRA LATERAL (SIDEBAR)
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

def carregar_dados_banco():
    resp_dados = supabase.table("dados").select("ncs").eq("id", id_banco).execute()
    if len(resp_dados.data) > 0:
        return resp_dados.data[0].get("ncs", {})
    return {}

if "banco" not in st.session_state or st.session_state.get("secao_carregada") != id_banco:
    st.session_state.banco = carregar_dados_banco()
    st.session_state.secao_carregada = id_banco

banco_dados = st.session_state.banco

def salvar_dados(dados_para_salvar):
    supabase.table("dados").update({"ncs": dados_para_salvar}).eq("id", id_banco).execute()

st.sidebar.markdown("---")

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
                supabase.table("usuarios").update({"senha": hash_senha(nova_senha_input)}).eq("id", usuario_atual).execute()
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
# 9. TÍTULO PRINCIPAL E NAVEGAÇÃO POR ABAS
# =====================================================================
st.title(f"🖥 Sistema de Controle de Recursos & Pregões - {om_user}")
st.markdown(f"**Área de Trabalho Ativa:** {secao_ativa}")
st.markdown("---")

tab_cadastro, tab_visualizacao, tab_visao_global, tab_consulta_pregoes, tab_acessos = st.tabs([
    "📝 Cadastrar e Lançar Compras",
    "📊 Controle Individual por NC",
    "📈 Visão Global do Ano",
    "🔎 Consultar Pregões & Importar para NC",
    "👥 Gerenciar Acessos"
])

# =====================================================================
# ABA 1: CADASTRO MANUAL
# =====================================================================
with tab_cadastro:
    if tipo_perfil == "Fiscal":
        st.error("🛡️ **Acesso Negado:** O perfil de Fiscal possui acesso de Auditoria e Visualização.")
    else:
        st.subheader("1. Cadastrar Nova Nota de Crédito (NC)")
        
        lista_nds = list(set([dados.get("nd", "") for nc, dados in banco_dados.items() if nc != "CONFIG_REQUISICAO" and isinstance(dados, dict) and dados.get("nd", "").strip()]))
        lista_pis = list(set([dados.get("pi", "") for nc, dados in banco_dados.items() if nc != "CONFIG_REQUISICAO" and isinstance(dados, dict) and dados.get("pi", "").strip()]))
        
        opcoes_nd = ["➕ Digitar Nova ND..."] + sorted(lista_nds)
        opcoes_pi = ["➕ Digitar Novo PI..."] + sorted(lista_pis)
        
        col_nc1, col_nc2, col_nc3 = st.columns(3)
        with col_nc1:
            nova_nc = st.text_input("Número da NC (Ex: 2026NC000511):", "", key="cad_numero_nc").strip().upper()
            valor_nc = st.number_input("Valor Total Recebido na NC (R$):", min_value=0.0, step=100.0, key="cad_valor_nc")
        
        with col_nc2:
            pi_selecionado = st.selectbox("Plano Interno (PI):", opcoes_pi)
            if pi_selecionado == "➕ Digitar Novo PI...":
                novo_pi = st.text_input("Digite o PI:").strip().upper()
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
                nome_editado = st.text_input("Número da NC:", value=nc_para_editar, key=f"edit_numero_nc_{nc_para_editar}").strip().upper()
            with col_ed2:
                pi_editado = st.text_input("Plano Interno (PI):", value=pi_atual, key=f"edit_pi_nc_{nc_para_editar}").strip().upper()
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
        st.subheader("2. Lançar Itens Manualmente")
        
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
                fornecedor = st.text_input("Nome do Fornecedor / Empresa:", "", key="item_forn").strip().upper()
                cnpj = st.text_input("CNPJ do Fornecedor:", "", key="item_cnpj").strip()
                
                opcoes_sit = ["Planejamento", "Aguardando entrega", "Recebido", "➕ Outra (Digitar)..."]
                sit_selecionada = st.selectbox("Situação Atual do Recurso:", opcoes_sit, key="item_sit")
                if sit_selecionada == "➕ Outra (Digitar)...":
                    situacao = st.text_input("Digite a Situação:").strip()
                else:
                    situacao = sit_selecionada
            
            if st.button("➕ Adicionar Item ao Planejamento", type="primary", key="btn_add_item"):
                if nome_resumido:
                    cnpj_formatado = formatar_cnpj(cnpj)
                    novo_item = {
                        "Item": int(nr_item), "Nome": nome_resumido, "Valor Unitário": float(valor_unitario),
                        "Qtd": int(quantidade), "Total": float(valor_unitario * quantidade), "UASG": nr_uasg,
                        "Pregão": nr_pregao, "Ata": nr_ata, "Fornecedor": fornecedor if fornecedor else "NÃO INFORMADO",
                        "CNPJ": cnpj_formatado, "Situação": situacao
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
# ABA 2: VISUALIZAÇÃO E CONTROLE POR NC
# =====================================================================
with tab_visualizacao:
    if ncs_do_ano:
        with st.expander("🔍 Pesquisa Rápida de Materiais no Ano (Localizar Item e NC)", expanded=False):
            termo_busca = st.text_input("Digite o nome do material, fornecedor, pregão ou CNPJ:").strip().lower()
            if termo_busca:
                resultados_busca = []
                for nc_chave in ncs_do_ano:
                    itens_nc = banco_dados[nc_chave].get("itens", [])
                    pi_nc = banco_dados[nc_chave].get("pi", "S/PI")
                    nd_nc = banco_dados[nc_chave].get("nd", "S/ND")
                    for it in itens_nc:
                        texto_completo = f"{it.get('Nome', '')} {it.get('Fornecedor', '')} {it.get('Pregão', '')} {it.get('CNPJ', '')}".lower()
                        if termo_busca in texto_completo:
                            qtd_item = int(it.get("Qtd", 0))
                            v_unit_item = float(it.get("Valor Unitário", 0.0))
                            resultados_busca.append({
                                "NC Vinculada": nc_chave,
                                "PI / ND": f"{pi_nc} / {nd_nc}",
                                "Item": it.get("Item"),
                                "Material": it.get("Nome"),
                                "Qtd": qtd_item,
                                "Valor Unitário": f"R$ {v_unit_item:,.2f}",
                                "Valor Total": f"R$ {(qtd_item * v_unit_item):,.2f}",
                                "Fornecedor": it.get("Fornecedor"),
                                "Pregão": it.get("Pregão", "N/I"),
                                "Situação": it.get("Situação")
                            })
                if resultados_busca:
                    st.success(f"🎯 Encontrado(s) **{len(resultados_busca)}** registro(s). A coluna **NC Vinculada** indica a qual NC o item pertence:")
                    st.dataframe(pd.DataFrame(resultados_busca), use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum material encontrado com os termos digitados.")

        pis_disponiveis = list(set([banco_dados[nc].get("pi", "Não informado") for nc in ncs_do_ano if isinstance(banco_dados[nc], dict) and banco_dados[nc].get("pi", "Não informado").strip()]))
        opcoes_filtro_pi = ["TODOS OS PIs"] + sorted(pis_disponiveis)
        
        col_filtro1, col_filtro2 = st.columns([2, 2])
        with col_filtro1:
            filtro_pi = st.selectbox("📌 Filtrar por PI:", opcoes_filtro_pi)
        
        if filtro_pi == "TODOS OS PIs":
            ncs_filtradas = ncs_do_ano
        else:
            ncs_filtradas = [nc for nc in ncs_do_ano if banco_dados[nc].get("pi", "Não informado") == filtro_pi]
            
        if not ncs_filtradas:
            st.warning("Nenhuma NC encontrada para o PI selecionado.")
        else:
            with col_filtro2:
                nc_selecionada_vis = st.selectbox("Selecione a NC para Gerenciamento e Análise:", ncs_filtradas, key="vis_item_select_nc")
            
            dados_nc = banco_dados[nc_selecionada_vis]
            total_recebido = dados_nc.get("valor_recebido", 0.0)
            nd_vinculada = dados_nc.get("nd", "Não informada")
            pi_vinculado = dados_nc.get("pi", "Não informado")
            
            st.markdown(f"**PI:** `{pi_vinculado}` &nbsp;&nbsp;|&nbsp;&nbsp; **ND:** `{nd_vinculada}`")
            
            if dados_nc["itens"]:
                for it in dados_nc["itens"]:
                    it["Total"] = float(it.get("Valor Unitário", 0.0)) * int(it.get("Qtd", 0))
                    it["CNPJ"] = formatar_cnpj(it.get("CNPJ", ""))
                
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
                
                st.write("")
                try:
                    excel_nc_bytes, mime_nc, ext_nc = gerar_planilha_nc_completa(nc_selecionada_vis, dados_nc, om_user, secao_ativa)
                    st.download_button(
                        label=f"📥 Baixar Planilha Executiva da NC {nc_selecionada_vis} ({ext_nc.upper()})",
                        data=excel_nc_bytes,
                        file_name=f"Relatorio_NC_{nc_selecionada_vis}_{om_user}.{ext_nc}",
                        mime=mime_nc,
                        use_container_width=False,
                        type="secondary"
                    )
                except Exception as e_nc_plan:
                    st.caption(f"Aviso de download: {e_nc_plan}")

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
                st.subheader("📋 Planilhas de Acompanhamento e Requisições por Fornecedor")
                
                config_req = banco_dados.get("CONFIG_REQUISICAO", {})
                pre_cadastro_pendente = not bool(config_req)
                
                if pre_cadastro_pendente:
                    st.warning("⚠️ **Atenção:** O cabeçalho padrão da sua Seção ainda não foi configurado.")
                
                with st.expander("⚙️ Personalizar Cabeçalho, Cidade e Assinaturas (Padrão da sua Seção)", expanded=pre_cadastro_pendente):
                    st.info("Preencha estes dados uma única vez para padronizar as requisições impressas.")
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
                                "cabecalho_om": cfg_om, "indicativo_diex": cfg_ind, "remetente_do": cfg_remetente,
                                "cidade_om": cfg_cidade, "assinatura_nome": cfg_ass_nome, "assinatura_funcao": cfg_ass_func,
                                "od_nome": cfg_od_nome, "od_funcao": cfg_od_func
                            }
                            salvar_dados(banco_dados)
                            st.session_state.banco = banco_dados
                            st.success("Configuração atualizada com sucesso!")
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
                        
                        doc_info = banco_dados[nc_selecionada_vis].get("doc_info", {})
                        info_forn = doc_info.get(forn, {"diex": "", "eb": "", "data": "", "assunto": "", "empenho": ""})

                        with st.expander(f"📄 GERAR REQUISIÇÃO: {forn} (Preencher e Imprimir)", expanded=False):
                            with st.form(f"form_req_{forn}_{i}"):
                                col_req1, col_req2 = st.columns(2)
                                with col_req1:
                                    diex_val = st.text_input("Nº do DIEx:", value=info_forn.get("diex", ""))
                                    eb_val = st.text_input("Nº do EB (Processo/Documento):", value=info_forn.get("eb", ""))
                                with col_req2:
                                    data_val = st.text_input("Data (Ex: 08 de setembro de 2026):", value=info_forn.get("data", ""))
                                    assunto_val = st.text_input("Assunto (Ex: materiais de construção):", value=info_forn.get("assunto", ""))
                                
                                st.markdown("---")
                                st.markdown("##### 📦 Controle de Depósito e Almoxarifado (Pós-Empenho)")
                                empenho_val = st.text_input("Nº da Nota de Empenho (NE):", value=info_forn.get("empenho", ""), key=f"ne_deposito_{forn}_{i}")
                                
                                btn_salvar_req = st.form_submit_button("💾 Salvar Dados da Requisição e Depósito", type="primary")
                                
                                if btn_salvar_req:
                                    if "doc_info" not in banco_dados[nc_selecionada_vis]:
                                        banco_dados[nc_selecionada_vis]["doc_info"] = {}
                                    banco_dados[nc_selecionada_vis]["doc_info"][forn] = {
                                        "diex": diex_val, "eb": eb_val, "data": data_val, "assunto": assunto_val, "empenho": empenho_val
                                    }
                                    salvar_dados(banco_dados)
                                    st.session_state.banco = banco_dados
                                    st.success("Dados salvos e atualizados!")
                                    st.rerun()
                            
                            if info_forn.get("empenho"):
                                st.success(f"📦 **Depósito Vinculado:** DIEx nº **{info_forn.get('diex', 'S/N')}** ➔ NE: **{info_forn.get('empenho')}**")

                            diex_display = info_forn.get("diex", "") if info_forn.get("diex", "") else "______"
                            eb_display = info_forn.get("eb", "") if info_forn.get("eb", "") else "_________________"
                            data_display = info_forn.get("data", "") if info_forn.get("data", "") else "____ de _______________ de 2026"
                            assunto_display = info_forn.get("assunto", "") if info_forn.get("assunto", "") else "______________________"
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
                                    padding: 40px; background-color: white; max-width: 800px; margin: 20px auto; 
                                    border: 1px solid #ccc; box-shadow: 2px 2px 10px #aaa;
                                }}
                                table.borda, .borda th, .borda td {{
                                    border: 1px solid black; border-collapse: collapse;
                                }}
                                .borda th, .borda td {{ padding: 5px; text-align: center; }}
                                .separador-tela {{
                                    border-top: 2px dashed #ccc; color: #999; text-align: center; margin: 40px 0;
                                    padding-top: 10px; font-size: 12px; font-family: Arial, sans-serif;
                                }}
                            </style>
                            </head>
                            <body>
                            <div class="no-print" style="text-align: center; margin-bottom: 20px; padding-top: 20px;">
                                <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px; font-weight: bold;">
                                    🖨️ Imprimir / Salvar como PDF
                                </button>
                            </div>
                        
                            <div class="editable-doc">
                                <table style="width: 100%; border: none;">
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
                                
                                <div class="separador-tela no-print">
                                    ✂️ --- QUEBRA DE PÁGINA --- ✂️
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
# ABA 3: VISÃO GLOBAL ANUAL
# =====================================================================
with tab_visao_global:
    dados_anuais = []
    
    if tipo_perfil == "Fiscal":
        st.subheader(f"🌐 Visão Corporativa da OM ({om_user}) - Todas as Seções")
        resp_todas_secoes = supabase.table("dados").select("*").like("id", f"{om_user}_%").execute()
        for linha in resp_todas_secoes.data:
            banco_secao_laco = linha.get("ncs", {})
            for nc in banco_secao_laco.keys():
                if nc != "CONFIG_REQUISICAO" and extrair_ano(nc) == ano_selecionado:
                    nd_atual = banco_secao_laco[nc].get("nd", "Não informada")
                    for item in banco_secao_laco[nc].get("itens", []):
                        valor_total_item = float(item.get("Valor Unitário", 0.0)) * int(item.get("Qtd", 0))
                        dados_anuais.append({
                            "ND": nd_atual, "Situação": item.get("Situação", "Situação Indefinida"), "Valor Total": valor_total_item
                        })
    else:
        st.subheader(f"📊 Resumo Geral de Empenhos e Aquisições - Seção: {secao_ativa}")
        if ncs_do_ano:
            for nc in ncs_do_ano:
                nd_atual = banco_dados[nc].get("nd", "Não informada")
                if not nd_atual.strip(): nd_atual = "Não informada"
                for item in banco_dados[nc].get("itens", []):
                    valor_total_item = float(item.get("Valor Unitário", 0.0)) * int(item.get("Qtd", 0))
                    dados_anuais.append({
                        "ND": nd_atual, "Situação": item.get("Situação", "Situação Indefinida"), "Valor Total": valor_total_item
                    })
                    
    if dados_anuais:
        try:
            planilha_anual_bytes, mime_anual, ext_anual = gerar_planilha_global_ano_completa(ano_selecionado, banco_dados, om_user, secao_ativa)
            st.download_button(
                label=f"📥 Baixar Relatório Anual Consolidado do Ano {ano_selecionado} ({ext_anual.upper()})",
                data=planilha_anual_bytes,
                file_name=f"Relatorio_Anual_Geral_{limpar_nome_aba(ano_selecionado)}_{om_user}.{ext_anual}",
                mime=mime_anual,
                type="primary"
            )
        except Exception as e_glob_plan:
            st.caption(f"Aviso de download: {e_glob_plan}")

        st.write("")

        df_anual = pd.DataFrame(dados_anuais)
        df_agrupado = df_anual.groupby(["ND", "Situação"])["Valor Total"].sum().reset_index()
        
        escala_cores = alt.Scale(domain=["Recebido", "Planejamento", "Aguardando entrega"], range=["#28a745", "#007bff", "#dc3545"])
        grafico_anual = alt.Chart(df_agrupado).mark_bar().encode(
            x=alt.X("ND:N", title="Natureza de Despesa (ND)"),
            y=alt.Y("Valor Total:Q", title="Total (R$)"),
            color=alt.Color("Situação:N", scale=escala_cores, title="Status do Recurso"),
            tooltip=[alt.Tooltip("ND:N"), alt.Tooltip("Situação:N"), alt.Tooltip("Valor Total:Q", format=",.2f")]
        ).properties(height=450)
        st.altair_chart(grafico_anual, use_container_width=True)
        
        total_geral_ano = df_agrupado["Valor Total"].sum()
        st.markdown(f"<h3 style='text-align: right;'>Total Geral Cadastrado em {ano_selecionado}: <span style='color: #1E88E5;'>R$ {total_geral_ano:,.2f}</span></h3>", unsafe_allow_html=True)
        
        st.markdown("---")
        df_pivot = df_agrupado.pivot(index="ND", columns="Situação", values="Valor Total").fillna(0)
        df_pivot["Total Geral por ND"] = df_pivot.sum(axis=1)
        for col in df_pivot.columns:
            df_pivot[col] = df_pivot[col].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_pivot, use_container_width=True)
    else:
        st.info("Não há itens registrados para exibição no painel global.")

# =====================================================================
# ABA 4: CONSULTA DE PREGÕES & IMPORTAÇÃO DIRETA PARA NOTA DE CRÉDITO
# =====================================================================
with tab_consulta_pregoes:
    st.subheader("🔎 Consulta de Pregões no SIASGnet e Contratos.gov.br")
    st.caption("Consulte os pregões da UASG, veja saldos reais de empenho e **importe itens diretamente para suas Notas de Crédito** em 1 clique!")

    col_u1, col_u2, col_u3 = st.columns([2, 3, 2])
    with col_u1:
        uasg_busca = st.text_input("Código da UASG:", value="160440", max_chars=6, key="input_uasg_pregoes")
    with col_u2:
        ano_now = datetime.datetime.now().year
        lista_exercicios = [str(ano_now + 1)] + [str(ano_now - i) for i in range(6)]
        anos_pregoes = st.multiselect(
            "Exercícios (Anos):",
            options=lista_exercicios,
            default=[str(ano_now), str(ano_now - 1)],
            key="multisel_anos_pregoes"
        )
    with col_u3:
        st.write("")
        st.write("")
        btn_rodar_busca = st.button("🔍 Buscar Pregões da UASG", type="primary", use_container_width=True)

    if 'df_pregoes_busca' not in st.session_state:
        st.session_state['df_pregoes_busca'] = pd.DataFrame()
    if 'itens_carregados_pregoes' not in st.session_state:
        st.session_state['itens_carregados_pregoes'] = {}

    if btn_rodar_busca:
        with st.spinner(f"Consultando SIASGnet para a UASG {uasg_busca}..."):
            df_pregoes_res, err_msg = extrair_pregoes_siasg(uasg_busca, anos_pregoes)
            if err_msg:
                st.error(err_msg)
            elif df_pregoes_res.empty:
                st.warning(f"Nenhum pregão encontrado para a UASG {uasg_busca}.")
                st.session_state['df_pregoes_busca'] = pd.DataFrame()
            else:
                st.session_state['df_pregoes_busca'] = df_pregoes_res
                st.session_state['itens_carregados_pregoes'] = {}
                st.session_state['uasg_pesquisada'] = uasg_busca

    df_pregoes_atual = st.session_state.get('df_pregoes_busca', pd.DataFrame())

    if not df_pregoes_atual.empty:
        st.success(f"Foram encontrados **{len(df_pregoes_atual)} pregões** para a UASG **{st.session_state.get('uasg_pesquisada', uasg_busca)}**.")

        for idx_p, row_p in df_pregoes_atual.iterrows():
            chave_p = f"{row_p['UASG']}_{row_p['Nº da Licitação']}"
            with st.expander(f"📦 Pregão {row_p['Nº da Licitação']} ({row_p['Ano']}) — {row_p['Objeto'][:100]}..."):
                st.write(f"**Objeto Completo:** {row_p['Objeto']}")
                
                c_p1, c_p2 = st.columns([3, 4])
                with c_p1:
                    btn_itens_p = st.button("🔍 Carregar Itens e Saldos Reais", key=f"btn_it_{chave_p}", type="primary")
                with c_p2:
                    st.markdown(f"[📋 Acessar no Contratos.gov.br]({row_p['Link Contratos']})")

                if btn_itens_p:
                    with st.spinner("Varrendo itens e apurando saldos no Contratos.gov.br..."):
                        itens_det = buscar_itens_com_saldo_real(st.session_state.get('uasg_pesquisada', uasg_busca), row_p['Nº Compra'], row_p['Ano Compra'])
                        st.session_state['itens_carregados_pregoes'][chave_p] = itens_det

                if chave_p in st.session_state['itens_carregados_pregoes']:
                    itens_pr = st.session_state['itens_carregados_pregoes'][chave_p]
                    if itens_pr:
                        st.markdown("---")
                        st.markdown("#### 📊 Itens Disponíveis e Saldos Reais da UASG")
                        df_it_view = pd.DataFrame(itens_pr)
                        
                        cols_v = ["Item", "Descrição", "Unidade", "Qtd Registrada", "Qtd Empenhada", "Saldo p/ Empenho", "Ata Vinculada", "Fornecedor", "PDF da Ata"]
                        st.dataframe(
                            df_it_view[[c for c in cols_v if c in df_it_view.columns]],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "PDF da Ata": st.column_config.LinkColumn(
                                    "Ata Oficial (PDF)",
                                    display_text="📥 Abrir Ata (PDF)"
                                )
                            }
                        )

                        st.markdown("---")
                        st.markdown("### 📥 Importar Item Selecionado Diretamente para uma Nota de Crédito")
                        
                        opcoes_import = [f"Item {it['Item']} - {it['Descrição'][:65]}... (Saldo: {it['Saldo p/ Empenho']})" for it in itens_pr]
                        it_escolhido_str = st.selectbox("Selecione o Item para Puxar para a NC:", opcoes_import, key=f"sel_import_{chave_p}")
                        
                        if it_escolhido_str:
                            idx_it_sel = opcoes_import.index(it_escolhido_str)
                            item_alvo = itens_pr[idx_it_sel]

                            ncs_disponiveis = [k for k in banco_dados.keys() if k != "CONFIG_REQUISICAO"]
                            
                            if not ncs_disponiveis:
                                st.warning("⚠️ Você ainda não tem nenhuma Nota de Crédito cadastrada. Cadastre uma NC na aba '1. Cadastrar e Lançar Compras' antes de importar itens.")
                            else:
                                with st.form(f"form_importar_item_{chave_p}_{item_alvo['Item']}"):
                                    st.markdown(f"**Item Selecionado:** `{item_alvo['Item']}` - {item_alvo['Descrição']}")
                                    st.markdown(f"• **Fornecedor Identificado:** `{item_alvo['Fornecedor']}`")
                                    st.markdown(f"• **Ata Vinculada:** `{item_alvo['Ata Vinculada']}` | **Pregão:** `{row_p['Nº da Licitação']}`")

                                    c_imp1, c_imp2, c_imp3 = st.columns(3)
                                    with c_imp1:
                                        nc_destino = st.selectbox("Vincular à Nota de Crédito (NC):", ncs_disponiveis)
                                    with c_imp2:
                                        # Puxa o saldo real garantido (Fórmula: Registrada - Empenhada)
                                        saldo_num = int(converter_para_float(item_alvo.get("Saldo p/ Empenho", "0")))
                                        if saldo_num <= 0:
                                            st.caption("⚠️ Item com Saldo 0 (Totalmente Empenhado)")
                                            qtd_para_importar = st.number_input("Quantidade a Empenhar / Comprar:", min_value=0, value=0, step=1)
                                        else:
                                            qtd_para_importar = st.number_input("Quantidade a Empenhar / Comprar:", min_value=1, value=saldo_num, step=1)
                                    with c_imp3:
                                        # Puxa o Valor Unitário real sugerido já preenchido
                                        v_sug = float(item_alvo.get("Valor Unitario Sugerido", 0.0))
                                        valor_unit_imp = st.number_input("Valor Unitário (R$):", min_value=0.0, value=v_sug, step=0.01)

                                    c_imp4, c_imp5 = st.columns(2)
                                    with c_imp4:
                                        sit_imp = st.selectbox("Situação Inicial:", ["Planejamento", "Aguardando entrega", "Recebido"])
                                    with c_imp5:
                                        pdf_link = item_alvo.get("PDF da Ata")
                                        if pdf_link:
                                            st.markdown(f"[📥 Visualizar Ata Original (PDF)]({pdf_link})")

                                    btn_confirmar_import = st.form_submit_button("🚀 Confirmar Importação deste Item para a NC", type="primary", use_container_width=True)

                                    if btn_confirmar_import:
                                        if tipo_perfil == "Fiscal":
                                            st.error("O perfil de Fiscal não possui permissão para incluir itens.")
                                        else:
                                            cnpj_puro = item_alvo.get("CNPJ Puro", "")
                                            forn_puro = item_alvo.get("Fornecedor Puro", "")
                                            
                                            # Garante a resolução da Razão Social do Fornecedor e CNPJ
                                            if cnpj_puro and (not forn_puro or forn_puro == cnpj_puro or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", forn_puro)) == 0):
                                                nome_rec = consultar_razao_social_cnpj(cnpj_puro)
                                                if nome_rec:
                                                    forn_puro = nome_rec
                                            
                                            if not forn_puro:
                                                forn_puro = item_alvo.get("Fornecedor", "NÃO INFORMADO")

                                            novo_item_nc = {
                                                "Item": int(item_alvo["Item"]) if str(item_alvo["Item"]).isdigit() else 1,
                                                "Nome": item_alvo["Descrição"].strip(),
                                                "Valor Unitário": float(valor_unit_imp),
                                                "Qtd": int(qtd_para_importar),
                                                "Total": float(valor_unit_imp * qtd_para_importar),
                                                "UASG": str(row_p["UASG"]),
                                                "Pregão": str(row_p["Nº da Licitação"]),
                                                "Ata": str(item_alvo["Ata Vinculada"]),
                                                "Fornecedor": forn_puro.strip().upper(),
                                                "CNPJ": formatar_cnpj(cnpj_puro),
                                                "Situação": sit_imp
                                            }

                                            if nc_destino not in banco_dados:
                                                st.error("Nota de Crédito não encontrada.")
                                            else:
                                                banco_dados[nc_destino]["itens"].append(novo_item_nc)
                                                salvar_dados(banco_dados)
                                                st.session_state.banco = banco_dados
                                                st.success(f"🎉 Item nº {item_alvo['Item']} importado com sucesso para a NC **{nc_destino}** com valor de R$ {valor_unit_imp:,.2f}!")
                                                st.toast(f"Item {item_alvo['Item']} adicionado à NC {nc_destino}!")
                    else:
                        st.warning("Nenhum item localizado no pregão.")

# =====================================================================
# ABA 5: GERENCIAR ACESSOS E EQUIPE
# =====================================================================
with tab_acessos:
    if tipo_perfil == "Operador":
        st.warning("⚠️ **Acesso Restrito:** O seu perfil de Operador não tem permissão para cadastrar novos usuários.")
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
                            "id": novo_int_user, 
                            "senha": hash_senha(novo_int_senha), 
                            "nome": novo_int_nome, 
                            "om": om_user, 
                            "secao": secao_final, 
                            "perfil": novo_int_perfil
                        }).execute()
                        
                        id_cofre = f"{om_user}_{secao_final}"
                        verifica_cofre = supabase.table("dados").select("id").eq("id", id_cofre).execute()
                        if len(verifica_cofre.data) == 0:
                            supabase.table("dados").insert({"id": id_cofre, "ncs": {}}).execute()
                        
                        st.success(f"✅ Conta criada com senha criptografada para {novo_int_nome} na Seção {secao_final}!")
