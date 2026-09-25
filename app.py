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
import os
import json
import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple, Optional, List, Dict
import concurrent.futures
import urllib3
import uuid
import time
# =====================================================================
# BANCO DE DADOS E LOGICA DE SUBITENS DA NATUREZA DE DESPESA (ND)
# Baseado no Manual SIAFI / MCASP / Orcamento Federal
# =====================================================================
import re
import unicodedata
from typing import Dict, List, Tuple, Optional

def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    limpo = re.sub(r'[^a-zA-Z0-9\s]', ' ', sem_acento.lower())
    return " ".join(limpo.split())

STOPWORDS_SUBITEM = {
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "para", "pra", "com",
    "sem", "por", "e", "ou", "o", "a", "os", "as", "um", "uma", "uns", "umas", "sob",
    "sobre", "item", "itens", "marca", "marcas", "tipo", "tipos", "modelo", "modelos",
    "unidade", "und", "un", "cx", "pct", "peca", "pecas", "kg", "mm", "cm", "m", "lt", "l", "ml",
    "cor", "tamanho", "padrao", "conf", "conforme", "especificacao", "edital", "objeto",
    "aquisicao", "fornecimento", "valor", "valores", "material", "materiais", "uso", "usos",
    "geral", "gerais", "outros", "outras", "outro", "outra", "artigo", "artigos", "produto",
    "produtos", "registra", "despesas", "despesa", "destinado", "destinados", "destinada",
    "destinadas", "diversos", "diversa", "diversas", "finalidade", "finalidades"
}

def extrair_palavras_chave(texto: str) -> List[str]:
    norm = _normalizar_texto(texto)
    return [p for p in norm.split() if len(p) >= 3 and p not in STOPWORDS_SUBITEM]

def extrair_codigo_subitem(opcao_texto: str) -> str:
    """Extrai os 2 dígitos do subitem a partir do texto formatado da opção."""
    if not opcao_texto:
        return ""
    m = re.search(r'\b(\d{2})\b', str(opcao_texto))
    return m.group(1) if m else ""

# =====================================================================
# BANCO DE DADOS OFICIAL DE SUBITENS COM FUNCAO SIAFI, PALAVRAS-CHAVE E EMENTAS
# =====================================================================
CATALOGO_SUBITENS: Dict[str, List[Dict]] = {   '339030': [   {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM COMBUSTIVEIS PARA MOTORES A COMBUSTAO INTERNA DE '
                                'VEICULOS RODOVIARIOS, TRATORES EM GERAL, EMBARCACOES DIVERSAS E GRUPOS GERADORES '
                                'ESTACIONADOS OU TRANSPORTAVEIS, E TODOS OS OLEOS LUBRIFICANTES DESTINADOS AOS '
                                'SISTEMAS HIDRAULICOS, HIDRAMATICOS, DE CAIXA DE TRANSMISSAO DE FORCA E GRAXAS '
                                'GRAFITADAS PARA ALTAS E BAIXAS TEMPERATURAS. ADITIVOS - ALCOOL HIDRATADO - FLUIDO '
                                'PARA AMORTECEDOR - FLUIDO PARA TRANSMISSAO HIDRAULICA - GASOLINA - GRAXAS - OLEO '
                                'DIESEL - OLEO PARA CARTER - OLEO PARA FREIO HIDRAULICO E OUTROS.',
                      'keywords': [   'combustivel',
                                      'gasolina',
                                      'diesel',
                                      'oleo diesel',
                                      'alcool hidratado',
                                      'etanol',
                                      'lubrificante',
                                      'oleo lubrificante',
                                      'graxa',
                                      'fluido freio',
                                      'oleo carter',
                                      'fluido transmissao',
                                      'fluido amortecedor',
                                      'aditivo radiador',
                                      'aditivo'],
                      'nd_completa': '33903001',
                      'nome': 'COMBUSTIVEIS E LUBRIFICANTES AUTOMOTIVOS',
                      'subitem': '01'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM COMBUSTIVEIS E LUBRIFICANTES DESTINADOS A QUALQUER '
                                'TIPO DE AERONAVE. ADITIVOS - GASOLINA - GRAXAS - OLEOS E FLUIDOS EM GERAL - QUEROSENE '
                                'E OUTROS.',
                      'keywords': ['aviacao', 'aeronave', 'querosene aviacao', 'gasolina aviacao', 'oleo aviacao'],
                      'nd_completa': '33903002',
                      'nome': 'COMBUSTIVEIS E LUBRIFICANTES DE AVIACAO',
                      'subitem': '02'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM COMBUSTIVEIS E LUBRIFICANTES PARA OUTRAS '
                                'FINALIDADES QUE NAO SE ENQUADRAM EM ITENS ANTERIORES. CARBURETO - CARVAO MINERAL - '
                                'CARVAO VEGETAL - LENHA - QUEROSENE COMUM - COMBUSTIVEIS E LUBRIFICANTES DE USO '
                                'FERROVIARIO E OUTROS.',
                      'keywords': [   'carbureto',
                                      'carvao mineral',
                                      'carvao vegetal',
                                      'lenha',
                                      'querosene comum',
                                      'ferroviario'],
                      'nd_completa': '33903003',
                      'nome': 'COMBUSTIVEIS E LUBRIF. P/ OUTRAS FINALIDADES',
                      'subitem': '03'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM GAS LIQUEFEITO DE PETROLEO (GLP), GAS DE COZINHA, '
                                'ACETILENO, OXIGENIO, NITROGENIO, HELIO, FREON, GAS CARBONICO, RECARGA DE EXTINTORES '
                                'DE INCENDIO E PO QUIMICO.',
                      'keywords': [   'gas',
                                      'glp',
                                      'gas liquefeito',
                                      'botijao',
                                      'gas de cozinha',
                                      'acetileno',
                                      'oxigenio',
                                      'nitrogenio',
                                      'helio',
                                      'argon',
                                      'freon',
                                      'gas carbico',
                                      'extintor',
                                      'recarga extintor',
                                      'po quimico'],
                      'nd_completa': '33903004',
                      'nome': 'GAS E OUTROS MATERIAIS ENGARRAFADOS',
                      'subitem': '04'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ARTEFATOS EXPLOSIVOS E MUNICOES. BALAS, PROJETEIS, '
                                'CAPSULAS, ESTOPINS, ESPOLETAS, DINAMITES, GRANADAS, POLVORA E ARTIGOS PIROTECNICOS.',
                      'keywords': [   'municao',
                                      'bala',
                                      'projetil',
                                      'capsula',
                                      'estopim',
                                      'espoleta',
                                      'explosivo',
                                      'dinamite',
                                      'granada',
                                      'polvora',
                                      'fogos artificio',
                                      'artigo pirotecnico'],
                      'nd_completa': '33903005',
                      'nome': 'EXPLOSIVOS E MUNICOES',
                      'subitem': '05'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ALIMENTOS PARA ANIMAIS. RACOES CANINAS, RACOES '
                                'EQUINAS, ALFAFA, ALPISTE, FARELO, FUBA, MILHO EM GRAO, SAL MINERAL E SUPLEMENTOS '
                                'ANIMAIS.',
                      'keywords': [   'racao',
                                      'racao canina',
                                      'racao equina',
                                      'alfafa',
                                      'alpiste',
                                      'capim',
                                      'farelo',
                                      'fuba',
                                      'milho grao',
                                      'sal mineral',
                                      'suplemento animal',
                                      'alimento animal'],
                      'nd_completa': '33903006',
                      'nome': 'ALIMENTOS PARA ANIMAIS',
                      'subitem': '06'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM GENEROS DE ALIMENTACAO. ACUCAR, ADOCANTE, AGUA '
                                'MINERAL, CAFE, CARNE, FRANGO, BOVINO, SUINO, PEIXE, CEREAL, ARROZ, FEIJAO, CHA, '
                                'CONDIMENTOS, FRUTAS, GELO, LEGUMES, REFRIGERANTES, SUCOS, TEMPEROS, VERDURAS, LEITE, '
                                'PAO, QUEIJO, MANTEIGA, BISCOITOS, BOLACHAS, FARINHA, MACARRAO, MASSA, OLEO DE SOJA, '
                                'VINAGRE, SAL E ALIMENTOS EM GERAL.',
                      'keywords': [   'acucar',
                                      'adocante',
                                      'agua mineral',
                                      'cafe',
                                      'carne',
                                      'frango',
                                      'bovino',
                                      'suino',
                                      'peixe',
                                      'cereal',
                                      'arroz',
                                      'feijao',
                                      'cha',
                                      'condimento',
                                      'fruta',
                                      'gelo',
                                      'legume',
                                      'refrigerante',
                                      'suco',
                                      'tempero',
                                      'verdura',
                                      'leite',
                                      'pao',
                                      'queijo',
                                      'manteiga',
                                      'biscoito',
                                      'bolacha',
                                      'farinha',
                                      'macarrao',
                                      'massa',
                                      'oleo soja',
                                      'vinagre',
                                      'sal',
                                      'molho',
                                      'achocolatado',
                                      'iogurte',
                                      'generos alimenticios',
                                      'alimento'],
                      'nd_completa': '33903007',
                      'nome': 'GENEROS DE ALIMENTACAO',
                      'subitem': '07'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ANIMAIS PARA PESQUISA E ABATE. ITENS E EXEMPLOS: '
                                'COBAIA, CAMUNDONGO, RATO, PEIXE VIVO, ABELHA, BOI ABATE.',
                      'keywords': ['cobaia', 'camundongo', 'rato', 'peixe vivo', 'abelha', 'boi abate'],
                      'nd_completa': '33903008',
                      'nome': 'ANIMAIS PARA PESQUISA E ABATE',
                      'subitem': '08'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MEDICAMENTOS, REMEDIOS, DROGAS, SOROS FISIOLOGICOS, '
                                'VACINAS, FARMACOS, ANTIBIOTICOS, ANALGESICOS, ANTI-INFLAMATORIOS, ANTISEPTICOS E '
                                'POMADAS.',
                      'keywords': [   'medicamento',
                                      'remedio',
                                      'droga',
                                      'soro fisiologico',
                                      'vacina',
                                      'farmaco',
                                      'antibiotico',
                                      'analgesico',
                                      'antiinflamatorio',
                                      'antisseptico',
                                      'pomada'],
                      'nd_completa': '33903009',
                      'nome': 'MATERIAL FARMACOLOGICO',
                      'subitem': '09'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS PARA ATENDIMENTO DENTARIO. RESINAS, '
                                'AMALGAMAS, ANESTESICOS ODONTOLOGICOS, BROCAS DENTARIAS, AGULHAS GENGIVAIS, DENTES '
                                'ARTIFICIAIS, MOLDEIRAS E MATERIAIS ODONTOLOGICOS.',
                      'keywords': [   'odontologico',
                                      'dente',
                                      'dentista',
                                      'amalgama',
                                      'anestesico dental',
                                      'broca dental',
                                      'cimento odontologico',
                                      'espatula odontologica',
                                      'filme raio x dental',
                                      'sugador cirurgico'],
                      'nd_completa': '33903010',
                      'nome': 'MATERIAL ODONTOLOGICO',
                      'subitem': '10'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PRODUTOS QUIMICOS PARA LABORATORIOS, ANALISES, '
                                'TRATAMENTO DE AGUA E PISCINAS. ACIDOS, BASES, REAGENTES, CLORO, SOLVENTES E '
                                'TAMPONADORES.',
                      'keywords': [   'quimico',
                                      'acido',
                                      'inseticida',
                                      'reagente quimico',
                                      'solvente',
                                      'sulfato',
                                      'cloreto',
                                      'hidroxido',
                                      'formol',
                                      'formicida',
                                      'raticida'],
                      'nd_completa': '33903011',
                      'nome': 'MATERIAL QUIMICO',
                      'subitem': '11'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL DE COUDELARIA OU DE USO ZOOTECNICO. ITENS '
                                'E EXEMPLOS: COUDELARIA, ARREAMETO, CABRESTO, FERRADURA, ESTRIBO, BRIDAO, ESPORA, '
                                'MANTA CAVALO, CINCHA, ADESTRAMENTO, COLEIRA CAO.',
                      'keywords': [   'coudelaria',
                                      'arreameto',
                                      'cabresto',
                                      'ferradura',
                                      'estribo',
                                      'bridao',
                                      'espora',
                                      'manta cavalo',
                                      'cincha',
                                      'adestramento',
                                      'coleira cao'],
                      'nd_completa': '33903012',
                      'nome': 'MATERIAL DE COUDELARIA OU DE USO ZOOTECNICO',
                      'subitem': '12'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL DE CACA E PESCA. ITENS E EXEMPLOS: PESCA, '
                                'ANZOL, REDE PESCA, ISCA, LINHA NYLON PESCA, MOLINETE, VARA PESCA, MERGULHO.',
                      'keywords': [   'pesca',
                                      'anzol',
                                      'rede pesca',
                                      'isca',
                                      'linha nylon pesca',
                                      'molinete',
                                      'vara pesca',
                                      'mergulho'],
                      'nd_completa': '33903013',
                      'nome': 'MATERIAL DE CACA E PESCA',
                      'subitem': '13'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS PARA EDUCACAO FISICA, TREINAMENTO E '
                                'PRATICA DE ESPORTES. BOLAS, REDES, CONES, TATAMES, COLETES, CRONOMETROS, TROFEUS, '
                                'MEDALHAS E ARTIGOS ESPORTIVOS.',
                      'keywords': [   'esportivo',
                                      'educativo',
                                      'bola',
                                      'bola futebol',
                                      'bola volei',
                                      'bola basquete',
                                      'apito',
                                      'chuteira',
                                      'tenis esporte',
                                      'quimono',
                                      'rede volei',
                                      'rede futebol',
                                      'raquete',
                                      'patins',
                                      'joelheira',
                                      'caneleira',
                                      'esteira yoga',
                                      'bone esporte',
                                      'trofeu',
                                      'medalha',
                                      'jogo educativo',
                                      'brinquedo',
                                      'tatame'],
                      'nd_completa': '33903014',
                      'nome': 'MATERIAL EDUCATIVO E ESPORTIVO',
                      'subitem': '14'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL P/ FESTIVIDADES E HOMENAGENS. ITENS E '
                                'EXEMPLOS: FESTIVIDADE, HOMENAGEM, ARRANJO FLORES, COROA FLORES, BUFFET, DOCES FESTA, '
                                'SALGADOS FESTA, PLACA COMEMORATIVA, DECORACAO EVENTO.',
                      'keywords': [   'festividade',
                                      'homenagem',
                                      'arranjo flores',
                                      'coroa flores',
                                      'buffet',
                                      'doces festa',
                                      'salgados festa',
                                      'placa comemorativa',
                                      'decoracao evento'],
                      'nd_completa': '33903015',
                      'nome': 'MATERIAL P/ FESTIVIDADES E HOMENAGENS',
                      'subitem': '15'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL DE ESCRITORIO E EXPEDIENTE EM GERAL. PAPEL '
                                'A4, SULFITE, CANETAS ESFEROGRAFICAS, LAPIS, BORRACHAS, CLIPS, GRAMPOS, GRAMPEADORES, '
                                'PERFURADORES, ENVELOPES, PASTAS, BLOCOS DE NOTAS, FITAS ADESIVAS, COLA, CORRETIVOS, '
                                'TESOURAS E ARTIGOS DE PAPELARIA.',
                      'keywords': [   'expediente',
                                      'papel',
                                      'papel a4',
                                      'sulfite',
                                      'resma',
                                      'caneta',
                                      'lapis',
                                      'borracha',
                                      'apontador',
                                      'caderno',
                                      'bloco',
                                      'bloco rascunho',
                                      'pasta',
                                      'pasta a-z',
                                      'pasta suspensa',
                                      'pasta aba',
                                      'pasta canaleta',
                                      'pasta plastico',
                                      'envelope',
                                      'clipe',
                                      'grampo',
                                      'grampeador',
                                      'extrator grampo',
                                      'perfurador',
                                      'fita adesiva',
                                      'durex',
                                      'fita crepe',
                                      'fita dupla face',
                                      'corretivo',
                                      'tesoura',
                                      'estilete',
                                      'regua',
                                      'carimbo',
                                      'almofada carimbo',
                                      'tinta carimbo',
                                      'cola bastao',
                                      'cola branca',
                                      'grafite',
                                      'lapiseira',
                                      'porta lapis',
                                      'organizador mesa',
                                      'envelope pardo',
                                      'etiqueta',
                                      'etiqueta adesiva',
                                      'marcador texto',
                                      'pincel atomico',
                                      'quadro branco',
                                      'apagador quadro',
                                      'post-it',
                                      'bloco adesivo'],
                      'nd_completa': '33903016',
                      'nome': 'MATERIAL DE EXPEDIENTE',
                      'subitem': '16'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SUPRIMENTOS DE INFORMATICA E PROCESSAMENTO DE '
                                'DADOS. CARTUCHOS DE TINTA, TONERS PARA IMPRESSORA, PENDRIVES, MIDIAS GRAVAVEIS, '
                                'FITAS, ETIQUETAS, CABOS USB, FILTROS DE LINHA E COMPONENTES DE CONSUMO DE TIC.',
                      'keywords': [   'toner',
                                      'cartucho',
                                      'cartucho tinta',
                                      'tinta impressora',
                                      'fita impressora',
                                      'mouse',
                                      'mouse pad',
                                      'teclado',
                                      'pendrive',
                                      'pen drive',
                                      'cabo rede',
                                      'cabo patch',
                                      'rj45',
                                      'conector rj',
                                      'filtro linha',
                                      'cd',
                                      'dvd',
                                      'midia',
                                      'pilha recarregavel'],
                      'nd_completa': '33903017',
                      'nome': 'MATERIAL DE TIC - MATERIAL DE CONSUMO',
                      'subitem': '17'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS E MEDICAMENTOS P/ USO VETERINARIO. ITENS '
                                'E EXEMPLOS: VETERINARIO, MEDICAMENTO VETERINARIO, VACINA VETERINARIA, VERMIFUGO, '
                                'ANTIPARASITARIO.',
                      'keywords': [   'veterinario',
                                      'medicamento veterinario',
                                      'vacina veterinaria',
                                      'vermifugo',
                                      'antiparasitario'],
                      'nd_completa': '33903018',
                      'nome': 'MATERIAIS E MEDICAMENTOS P/ USO VETERINARIO',
                      'subitem': '18'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS DE EMBALAGEM, EMPACOTAMENTO E LACRACAO. '
                                'CAIXAS DE PAPELAO, SACOS PLASTICOS, FITAS ADESIVAS, PLASTICO BOLHA, CORDOES, '
                                'BARBANTES, FITAS GOMADAS E LACRES.',
                      'keywords': [   'embalagem',
                                      'acondicionamento',
                                      'caixa papelao',
                                      'caixa plastica',
                                      'isopor',
                                      'caixa isopor',
                                      'papel bolha',
                                      'plastico bolha',
                                      'filme stretch',
                                      'fitilho',
                                      'fita gomada',
                                      'arame',
                                      'barbante',
                                      'saco plastico',
                                      'sacola',
                                      'corda amarracao'],
                      'nd_completa': '33903019',
                      'nome': 'MATERIAL DE ACONDICIONAMENTO E EMBALAGEM',
                      'subitem': '19'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ROUPARIA DE CONSUMO PARA ALOJAMENTOS E HOTÉIS DE '
                                'TRANSITO. LENCOIS, FRONHAS, COBERTORES, COLCHAS, TOALHAS DE BANHO, TOALHAS DE ROSTO, '
                                'TOALHAS DE MESA E TRAVESSEIROS.',
                      'keywords': [   'cama',
                                      'mesa e banho',
                                      'lencol',
                                      'fronha',
                                      'cobertor',
                                      'colcha',
                                      'travesseiro',
                                      'toalha banho',
                                      'toalha rosto',
                                      'toalha mesa',
                                      'guardanapo tecido',
                                      'capa colchao'],
                      'nd_completa': '33903020',
                      'nome': 'MATERIAL DE CAMA, MESA E BANHO',
                      'subitem': '20'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM UTENSILIOS E ARTIGOS DESCARTAVEIS OU DE CONSUMO '
                                'PARA COPA E COZINHA. COPOS DESCARTAVEIS, PRATOS, TALHERES, GUARDANAPOS, PANELAS, '
                                'BACIAS, JARRAS, GARRAFAS TERMICAS, ESPONJAS E ARTIGOS CULINARIOS.',
                      'keywords': [   'copa',
                                      'cozinha',
                                      'copo',
                                      'copo descartavel',
                                      'prato',
                                      'prato descartavel',
                                      'talher',
                                      'garfo',
                                      'faca',
                                      'colher',
                                      'xicara',
                                      'pires',
                                      'garrafa termica',
                                      'bule',
                                      'panela',
                                      'frigideira',
                                      'assadeira',
                                      'bandeja',
                                      'filme aluminio',
                                      'papel aluminio',
                                      'filme pvc',
                                      'coador cafe',
                                      'filtro cafe',
                                      'pano prato',
                                      'pano copa',
                                      'tigela',
                                      'refratario',
                                      'abridor lata',
                                      'concha cozinha',
                                      'escumadeira'],
                      'nd_completa': '33903021',
                      'nome': 'MATERIAL DE COPA E COZINHA',
                      'subitem': '21'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PRODUTOS E MATERIAIS DE LIMPEZA E HIGIENE. AGUA '
                                'SANITARIA, DESINFETANTE, SABAO EM PO, SABAO EM BARRA, DETERGENTE, AMACIANTE, CERA, '
                                'DESENGORDURANTE, VASSOURAS, RODOS, PANOS DE CHAO, BALDES, PAPEL HIGIENICO, SABONETE E '
                                'ALCOOL 70%.',
                      'keywords': [   'limpeza',
                                      'higienizacao',
                                      'sabao',
                                      'sabao po',
                                      'sabao barra',
                                      'sabonete',
                                      'sabonete liquido',
                                      'detergente',
                                      'desinfetante',
                                      'agua sanitaria',
                                      'cloro',
                                      'alcool',
                                      'alcool 70',
                                      'alcool em gel',
                                      'vassoura',
                                      'rodo',
                                      'pa lixo',
                                      'saco lixo',
                                      'saco para lixo',
                                      'palha aco',
                                      'bombril',
                                      'esponja',
                                      'esponja dupla face',
                                      'pano chao',
                                      'pano limpeza',
                                      'flanela',
                                      'papel higienico',
                                      'papel toalha',
                                      'toalha papel',
                                      'creme dental',
                                      'pasta dente',
                                      'escova dente',
                                      'lustra moveis',
                                      'multiuso',
                                      'limpa vidro',
                                      'cera',
                                      'desodorizador',
                                      'aromatizador',
                                      'odorizador',
                                      'soda caustica'],
                      'nd_completa': '33903022',
                      'nome': 'MATERIAL DE LIMPEZA E PROD. DE HIGIENIZACAO',
                      'subitem': '22'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM FARDAMENTOS, UNIFORMES MILITARES, ROUPAS CIVIS, '
                                'TECIDOS E AVIAMENTOS. FARDAS, CAMISAS, CALCAS, GANDOLAS, COBERTURAS, BONES, BOINAS, '
                                'GORROS, MEIAS, BOTOES, ZIPERES, LINHAS E VELCROS.',
                      'keywords': [   'uniforme',
                                      'farda',
                                      'fardamento',
                                      'gandola',
                                      'camuflado',
                                      'tecido',
                                      'costura',
                                      'linha costura',
                                      'ziper',
                                      'botao',
                                      'cadarco',
                                      'elastico',
                                      'camisa',
                                      'camiseta',
                                      'calca',
                                      'agasalho',
                                      'avental',
                                      'chapeu',
                                      'bone farda',
                                      'boina',
                                      'cinto',
                                      'gavata',
                                      'meia',
                                      'coturno',
                                      'bota militar',
                                      'sapato militar'],
                      'nd_completa': '33903023',
                      'nome': 'UNIFORMES, TECIDOS E AVIAMENTOS',
                      'subitem': '23'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS DE CONSTRUCAO CIVIL E MANUTENCAO PREDIAL '
                                'DE IMOVEIS. CIMENTO, AREIA, BRITA, TIJOLOS, TINTAS, SELADORES, VERNIZES, SOLVENTES, '
                                'CAL, PISOS, AZULEJOS, TELHAS, PORTAS, FECHADURAS, TORNEIRAS, TUBOS E CONEXOES DE PVC '
                                'E VALVULAS.',
                      'keywords': [   'manutencao imovel',
                                      'construcao',
                                      'construcao civil',
                                      'vergalhao',
                                      'armacao',
                                      'concreto',
                                      'ferro',
                                      'aco',
                                      'alvenaria',
                                      'estrutura',
                                      'viga',
                                      'coluna',
                                      'trelica',
                                      'cimento',
                                      'areia',
                                      'brita',
                                      'cal',
                                      'tijolo',
                                      'telha',
                                      'tinta',
                                      'tinta acrilica',
                                      'tinta latex',
                                      'esmalte sintetico',
                                      'verniz',
                                      'massa corrida',
                                      'selador',
                                      'trincha',
                                      'pincel',
                                      'rolo la',
                                      'rolo pintura',
                                      'lixa massa',
                                      'lixa ferro',
                                      'tubo pvc',
                                      'cano pvc',
                                      'conexao pvc',
                                      'joelho pvc',
                                      'curva pvc',
                                      'luva pvc',
                                      'registro',
                                      'valvula descarga',
                                      'sifao',
                                      'torneira',
                                      'piso',
                                      'ceramica',
                                      'azulejo',
                                      'argamassa',
                                      'rejunte',
                                      'porta',
                                      'fechadura',
                                      'dobradica',
                                      'parafuso',
                                      'bucha',
                                      'prego',
                                      'arame liso',
                                      'arame farpado',
                                      'impermeabilizante',
                                      'vidro',
                                      'silicone'],
                      'nd_completa': '33903024',
                      'nome': 'MATERIAL P/ MANUT.DE BENS IMOVEIS/INSTALACOES',
                      'subitem': '24'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PECAS, COMPONENTES E INSUMOS PARA REPARO DE MOVEIS, '
                                'ELETRODOMESTICOS E MAQUINAS EM GERAL. PARAFUSOS, PORCAS, ARRUELAS, DOBRADICAS, '
                                'CORREDICAS, PUXADORES, RODINHAS, RESISTENCIAS E BORRACHAS DE VEDACAO.',
                      'keywords': [   'peca reposicao movel',
                                      'cilindro maquina',
                                      'peca compressor',
                                      'mola movel',
                                      'rodizio cadeira'],
                      'nd_completa': '33903025',
                      'nome': 'MATERIAL P/ MANUTENCAO DE BENS MOVEIS',
                      'subitem': '25'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM COMPONENTES, FIOS E MATERIAIS PARA INSTALACOES '
                                'ELETRICAS E ELETRONICAS. LAMPADAS LED, REATORES, DISJUNTORES, FIOS E CABOS ELETRICOS, '
                                'TOMADAS, INTERRUPTORES, FITAS ISOLANTES, FUSIVEIS, SENSORES, CONDULETES E CANALETAS.',
                      'keywords': [   'eletrico',
                                      'lampada',
                                      'lampada led',
                                      'luminaria',
                                      'painel led',
                                      'refletor led',
                                      'disjuntor',
                                      'fio',
                                      'fio eletrico',
                                      'cabo flexivel',
                                      'cabo eletrico',
                                      'tomada',
                                      'interruptor',
                                      'espelho tomada',
                                      'placa cega',
                                      'fita isolante',
                                      'reator',
                                      'sensor presenca',
                                      'canaleta',
                                      'fusivel',
                                      'benjamim',
                                      'adaptador tomada',
                                      'bocal',
                                      'soquete',
                                      'calha eletrica',
                                      'chave teste',
                                      'conector eletrico'],
                      'nd_completa': '33903026',
                      'nome': 'MATERIAL ELETRICO E ELETRONICO',
                      'subitem': '26'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL DE MANOBRA E PATRULHAMENTO. ITENS E '
                                'EXEMPLOS: MANOBRA, PATRULHAMENTO, BINOCULO, CANTIL, MARMITA MILITAR, LANTERNA '
                                'MILITAR, MOCHILA MILITAR, SACO DORMIR, FLAMULA, PIQUETE, CARTA NAUTICA.',
                      'keywords': [   'manobra',
                                      'patrulhamento',
                                      'binoculo',
                                      'cantil',
                                      'marmita militar',
                                      'lanterna militar',
                                      'mochila militar',
                                      'saco dormir',
                                      'flamula',
                                      'piquete',
                                      'carta nautica'],
                      'nd_completa': '33903027',
                      'nome': 'MATERIAL DE MANOBRA E PATRULHAMENTO',
                      'subitem': '27'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE PROTECAO INDIVIDUAL (EPI) E '
                                'SEGURANCA. CAPACETES DE PROTECAO, LUVAS DE VAQUETA OU LATEX, OCULOS DE PROTECAO, '
                                'MASCARAS RESPIRATORIAS, PROTETORES AURICULARES, BOTAS DE BORRACHA E CINTOS DE '
                                'SEGURANCA.',
                      'keywords': [   'epi',
                                      'protecao',
                                      'seguranca',
                                      'capacete',
                                      'oculos protecao',
                                      'luva protecao',
                                      'luva vaqueta',
                                      'luva pigmentada',
                                      'bota borracha',
                                      'bota pvc',
                                      'mascara protecao',
                                      'protetor auricular',
                                      'abafador',
                                      'cinto seguranca',
                                      'trava quedas',
                                      'cadeado',
                                      'lona',
                                      'capa chuva',
                                      'colete reflexivo'],
                      'nd_completa': '33903028',
                      'nome': 'MATERIAL DE PROTECAO E SEGURANCA',
                      'subitem': '28'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL P/ AUDIO, VIDEO E FOTO. ITENS E EXEMPLOS: '
                                'AUDIO, VIDEO, FOTO, FILME FOTO, PAPEL FOTOGRAFICO, PILHA AUDIO, MOLDURA.',
                      'keywords': [   'audio',
                                      'video',
                                      'foto',
                                      'filme foto',
                                      'papel fotografico',
                                      'pilha audio',
                                      'moldura'],
                      'nd_completa': '33903029',
                      'nome': 'MATERIAL P/ AUDIO, VIDEO E FOTO',
                      'subitem': '29'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS E INSUMOS PARA TELECOMUNICACOES E RADIOS. '
                                'ANTENAS, CABOS COAXIAIS, CONECTORES, HEADSETS, BATERIAS DE RADIO TRANSMISSOR E '
                                'ACESSORIOS DE COMUNICACAO.',
                      'keywords': [   'comunicacao',
                                      'antena radio',
                                      'conector bnc',
                                      'circuito impresso',
                                      'fio telefonico'],
                      'nd_completa': '33903030',
                      'nome': 'MATERIAL PARA COMUNICACOES',
                      'subitem': '30'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAIS PARA JARDINAGEM E AGRICULTURA. SEMENTES, '
                                'MUDAS, ADUBOS, FERTILIZANTES, DEFENSIVOS AGRICOLAS, TERRA VEGETAL E VASOS.',
                      'keywords': [   'semente',
                                      'muda',
                                      'planta',
                                      'adubo',
                                      'fertilizante',
                                      'terra vegetal',
                                      'substrato',
                                      'jardinagem'],
                      'nd_completa': '33903031',
                      'nome': 'SEMENTES, MUDAS DE PLANTAS E INSUMOS',
                      'subitem': '31'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL LABORATORIAL. ITENS E EXEMPLOS: '
                                'LABORATORIO, LABORATORIAL, TUBO ENSAIO, BEQUER, PIPETA, PROVETA, LAMINA MICROSCOPIO, '
                                'PLACA PETRI, VIDRARIA LABORATORIO.',
                      'keywords': [   'laboratorio',
                                      'laboratorial',
                                      'tubo ensaio',
                                      'bequer',
                                      'pipeta',
                                      'proveta',
                                      'lamina microscopio',
                                      'placa petri',
                                      'vidraria laboratorio'],
                      'nd_completa': '33903035',
                      'nome': 'MATERIAL LABORATORIAL',
                      'subitem': '35'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL HOSPITALAR. ITENS E EXEMPLOS: HOSPITALAR, '
                                'SAUDE, AGULHA, SERINGA, GAZE, COMPRESSA, ESPARADRAPO, ALGODAO, FIO SUTURA, CATETER, '
                                'LUVA PROCEDIMENTO, LUVA CIRURGICA, LAMINA BISTURI, TERMOMETRO CLINICO, MASCARA '
                                'DESCARTAVEL.',
                      'keywords': [   'hospitalar',
                                      'saude',
                                      'agulha',
                                      'seringa',
                                      'gaze',
                                      'compressa',
                                      'esparadrapo',
                                      'algodao',
                                      'fio sutura',
                                      'cateter',
                                      'luva procedimento',
                                      'luva cirurgica',
                                      'lamina bisturi',
                                      'termometro clinico',
                                      'mascara descartavel'],
                      'nd_completa': '33903036',
                      'nome': 'MATERIAL HOSPITALAR',
                      'subitem': '36'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SOBRESSALENTES E PECAS EXCLUSIVAS PARA ARMAS E '
                                'ARMAMENTOS. PERCURSORES, MOLAS DE RECUO, CARREGADORES, EXTRATORES, CANOS DE REPOSICAO '
                                'E OLEO PARA ARMAS.',
                      'keywords': [   'sobressalente armamento',
                                      'peca fuzil',
                                      'peca pistola',
                                      'carregador fuzil',
                                      'mola armamento'],
                      'nd_completa': '33903037',
                      'nome': 'SOBRESSALENTES DE ARMAMENTO',
                      'subitem': '37'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PECAS, PNEUS E COMPONENTES PARA CONSERTO E '
                                'MANUTENCAO DE VEICULOS E VIATURAS AUTOMOTORAS. PNEUS, CAMARAS DE AR, FILTROS DE OLEO, '
                                'FILTROS DE AR, FILTROS DE COMBUSTIVEL, PASTILHAS DE FREIO, DISCOS DE FREIO, '
                                'AMORTECEDORES, BATERIAS AUTOMOTIVAS, VELAS DE IGNICAO, CORREIAS, JUNTAS, FAROIS E '
                                'LANTERNAS.',
                      'keywords': [   'veiculo',
                                      'viatura',
                                      'automotivo',
                                      'pneu',
                                      'camara ar',
                                      'bateria veiculo',
                                      'bateria automotiva',
                                      'amortecedor',
                                      'pastilha freio',
                                      'disco freio',
                                      'filtro oleo',
                                      'filtro ar',
                                      'filtro combustivel',
                                      'palheta parabrisa',
                                      'vela ignicao',
                                      'correia dentada',
                                      'lampada automotiva',
                                      'farol veiculo'],
                      'nd_completa': '33903039',
                      'nome': 'MATERIAL P/ MANUTENCAO DE VEICULOS',
                      'subitem': '39'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM FERRAMENTAS MANUAIS E DE DESGASTE RAPIDO. ALICATES, '
                                'CHAVES DE FENDA, CHAVES PHILIPS, CHAVES DE BOCA, MARTELOS, SERRAS, BROCAS, DISCOS DE '
                                'CORTE E DESBASTE, LIXAS E ESCOVAS DE ACO.',
                      'keywords': [   'ferramenta',
                                      'alicate',
                                      'chave fenda',
                                      'chave philips',
                                      'chave combinada',
                                      'chave biela',
                                      'chave inglesa',
                                      'martelo',
                                      'marreta',
                                      'serrote',
                                      'arco serra',
                                      'lamina serra',
                                      'trena',
                                      'nivel',
                                      'lima',
                                      'torques',
                                      'pa',
                                      'enxada',
                                      'picareta',
                                      'machado',
                                      'foice',
                                      'ferro solda'],
                      'nd_completa': '33903042',
                      'nome': 'FERRAMENTAS',
                      'subitem': '42'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PLACAS DE SINALIZACAO, CAVALETES, FITAS ZEBRADAS, '
                                'CONES DE TRANSITO, ADESIVOS REFLETIVOS E MATERIAIS DE SINALIZACAO VISUAL.',
                      'keywords': [   'sinalizacao',
                                      'placa sinalizacao',
                                      'cone transito',
                                      'fita zebrada',
                                      'cracha',
                                      'cordao cracha'],
                      'nd_completa': '33903044',
                      'nome': 'MATERIAL DE SINALIZACAO VISUAL E OUTROS',
                      'subitem': '44'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM BANDEIRAS, FLAMULAS E INSIGNIAS. ITENS E EXEMPLOS: '
                                'BANDEIRA, BANDEIRA BRASIL, FLAMULA, INSIGNIA, BRASAO.',
                      'keywords': ['bandeira', 'bandeira brasil', 'flamula', 'insignia', 'brasao'],
                      'nd_completa': '33903050',
                      'nome': 'BANDEIRAS, FLAMULAS E INSIGNIAS',
                      'subitem': '50'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MATERIAL PARA DIVULGACAO. ITENS E EXEMPLOS: BANNER, '
                                'FAIXA DIVULGACAO, CARTAZ, PAINEL INFORMATIVO.',
                      'keywords': ['banner', 'faixa divulgacao', 'cartaz', 'painel informativo'],
                      'nd_completa': '33903059',
                      'nome': 'MATERIAL PARA DIVULGACAO',
                      'subitem': '59'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM OUTROS MATERIAIS DE CONSUMO QUE NAO POSSUEM '
                                'CLASSIFICACAO ESPECIFICA NOS ITENS ANTERIORES.',
                      'keywords': ['outro material consumo', 'consumo diverso'],
                      'nd_completa': '33903099',
                      'nome': 'OUTROS MATERIAIS DE CONSUMO',
                      'subitem': '99'}],
    '339039': [   {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ASSINATURAS DE PERIODICOS E ANUIDADES. ITENS E '
                                'EXEMPLOS: ASSINATURA JORNAL, ASSINATURA REVISTA, TV CABO, ANUIDADE.',
                      'keywords': ['assinatura jornal', 'assinatura revista', 'tv cabo', 'anuidade'],
                      'nd_completa': '33903901',
                      'nome': 'ASSINATURAS DE PERIODICOS E ANUIDADES',
                      'subitem': '01'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS GRAFICOS, IMPRESSAO, REPROGRAFIA, '
                                'PLOTAGEM, ENCADERNACAO E COPIAS.',
                      'keywords': [   'servico advocacia',
                                      'servico engenharia',
                                      'servico arquitetura',
                                      'servico contabilidade',
                                      'laudo pericial'],
                      'nd_completa': '33903905',
                      'nome': 'SERVICOS TECNICOS PROFISSIONAIS',
                      'subitem': '05'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MANUTENCAO DE SOFTWARE. ITENS E EXEMPLOS: '
                                'MANUTENCAO SOFTWARE, SUPORTE SOFTWARE, SUSTENTACAO SOFTWARE.',
                      'keywords': ['manutencao software', 'suporte software', 'sustentacao software'],
                      'nd_completa': '33903908',
                      'nome': 'MANUTENCAO DE SOFTWARE',
                      'subitem': '08'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM LOCACAO DE MAQUINAS E EQUIPAMENTOS. ITENS E '
                                'EXEMPLOS: LOCACAO MAQUINA, ALUGUEL GERADOR, ALUGUEL MAQUINA, ALUGUEL EQUIPAMENTO.',
                      'keywords': ['locacao maquina', 'aluguel gerador', 'aluguel maquina', 'aluguel equipamento'],
                      'nd_completa': '33903912',
                      'nome': 'LOCACAO DE MAQUINAS E EQUIPAMENTOS',
                      'subitem': '12'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE MANUTENCAO E CONSERVACAO PREDIAL E DE '
                                'BENS IMOVEIS. PINTURA, REPAROS ELETRICOS, HIDRAULICOS, ALVENARIA E REFORMAS.',
                      'keywords': [   'servico reforma',
                                      'pintura predial',
                                      'servico pedreiro',
                                      'manutencao eletrica predial',
                                      'manutencao hidraulica predial',
                                      'conserto telhado',
                                      'limpeza fossa',
                                      'manutencao elevador'],
                      'nd_completa': '33903916',
                      'nome': 'MANUTENCAO E CONSERV. DE BENS IMOVEIS',
                      'subitem': '16'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE MANUTENCAO E CONSERVACAO DE MAQUINAS E '
                                'EQUIPAMENTOS INDUSTRIAIS OU DE OFICINA.',
                      'keywords': [   'conserto maquina',
                                      'manutencao ar condicionado',
                                      'instalacao ar condicionado',
                                      'manutencao gerador',
                                      'revisao equipamento',
                                      'calibracao balanca'],
                      'nd_completa': '33903917',
                      'nome': 'MANUT. E CONSERV. DE MAQUINAS E EQUIPAMENTOS',
                      'subitem': '17'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE MANUTENCAO E CONSERVACAO DE VEICULOS E '
                                'VIATURAS. MECANICA, ELETRICA AUTOMOTIVA, LATARIA, PINTURA, ALINHAMENTO E '
                                'BALANCEAMENTO.',
                      'keywords': [   'manutencao viatura',
                                      'manutencao veiculo',
                                      'revisao veicular',
                                      'revisao viatura',
                                      'funilaria',
                                      'lanternagem',
                                      'pintura veiculo',
                                      'mecanica veiculo',
                                      'mecanica viatura',
                                      'viatura',
                                      'veiculo',
                                      'alinhamento balanceamento',
                                      'troca pneus servico',
                                      'eletrica automotiva'],
                      'nd_completa': '33903919',
                      'nome': 'MANUTENCAO E CONSERV. DE VEICULOS',
                      'subitem': '19'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE MANUTENCAO DE MOVEIS, ESTOFADOS, '
                                'CADEIRAS E BENS MOVEIS.',
                      'keywords': ['reforma cadeira', 'estofamento', 'conserto movel', 'reforma estofado'],
                      'nd_completa': '33903920',
                      'nome': 'MANUT.E CONS.DE B.MOVEIS DE OUTRAS NATUREZAS',
                      'subitem': '20'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM FORNECIMENTO DE ALIMENTACAO PREPARADA, BUFFET, '
                                'REFEICOES COLETIVAS E LANCHES.',
                      'keywords': ['fornecimento alimentacao', 'refeicao pronta', 'buffet', 'coffee break', 'lanche'],
                      'nd_completa': '33903941',
                      'nome': 'FORNECIMENTO DE ALIMENTACAO',
                      'subitem': '41'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICO DE SELECAO E TREINAMENTO. ITENS E EXEMPLOS: '
                                'CURSO, TREINAMENTO, CAPACITACAO, PALESTRA, SEMINARIO, WORKSHOP.',
                      'keywords': ['curso', 'treinamento', 'capacitacao', 'palestra', 'seminario', 'workshop'],
                      'nd_completa': '33903948',
                      'nome': 'SERVICO DE SELECAO E TREINAMENTO',
                      'subitem': '48'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE TELECOMUNICACOES. ITENS E EXEMPLOS: '
                                'TELEFONIA, TELEFONIA CELULAR, TELEFONIA FIXA, LINK INTERNET.',
                      'keywords': ['telefonia', 'telefonia celular', 'telefonia fixa', 'link internet'],
                      'nd_completa': '33903958',
                      'nome': 'SERVICOS DE TELECOMUNICACOES',
                      'subitem': '58'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS GRAFICOS E EDITORIAIS. ITENS E EXEMPLOS: '
                                'SERVICO GRAFICO, IMPRESSAO BANNER, IMPRESSAO FOLDER, ENCADERNACAO, CONFECCAO CRACHA.',
                      'keywords': [   'servico grafico',
                                      'impressao banner',
                                      'impressao folder',
                                      'encadernacao',
                                      'confeccao cracha'],
                      'nd_completa': '33903963',
                      'nome': 'SERVICOS GRAFICOS E EDITORIAIS',
                      'subitem': '63'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM CONFECCAO DE UNIFORMES, BANDEIRAS E FLAMULAS. ITENS '
                                'E EXEMPLOS: CONFECCAO UNIFORME, CONFECCAO FARDA, BORDADO, CONFECCAO BANDEIRA.',
                      'keywords': ['confeccao uniforme', 'confeccao farda', 'bordado', 'confeccao bandeira'],
                      'nd_completa': '33903970',
                      'nome': 'CONFECCAO DE UNIFORMES, BANDEIRAS E FLAMULAS',
                      'subitem': '70'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM FRETES E TRANSPORTES DE ENCOMENDAS. ITENS E '
                                'EXEMPLOS: FRETE, TRANSPORTE ENCOMENDA, CARRETO, MUDANCA, TRANSPORTADORA.',
                      'keywords': ['frete', 'transporte encomenda', 'carreto', 'mudanca', 'transportadora'],
                      'nd_completa': '33903974',
                      'nome': 'FRETES E TRANSPORTES DE ENCOMENDAS',
                      'subitem': '74'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM VIGILANCIA OSTENSIVA/MONITORADA/RASTREAMENTO. ITENS '
                                'E EXEMPLOS: VIGILANCIA, SEGURANCA ARMADA, MONITORAMENTO ALARME, RASTREAMENTO '
                                'VEICULAR.',
                      'keywords': ['vigilancia', 'seguranca armada', 'monitoramento alarme', 'rastreamento veicular'],
                      'nd_completa': '33903977',
                      'nome': 'VIGILANCIA OSTENSIVA/MONITORADA/RASTREAMENTO',
                      'subitem': '77'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE LIMPEZA, CONSERVACAO E HIGIENIZACAO COM '
                                'FORNECIMENTO DE MAO DE OBRA.',
                      'keywords': [   'servico limpeza',
                                      'asseio e conservacao',
                                      'dedetizacao',
                                      'desinsetizacao',
                                      'desratizacao',
                                      'coleta lixo',
                                      'lavagem veiculo'],
                      'nd_completa': '33903978',
                      'nome': 'LIMPEZA E CONSERVACAO',
                      'subitem': '78'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM SERVICOS DE VIGILANCIA OSTENSIVA, SEGURANCA PRIVADA '
                                'E MONITORAMENTO ELETRONICO.',
                      'keywords': [   'apoio administrativo',
                                      'recepcionista',
                                      'portaria',
                                      'copeiragem',
                                      'jardinagem servico',
                                      'motorista terceirizado'],
                      'nd_completa': '33903979',
                      'nome': 'SERV. DE APOIO ADMIN., TECNICO E OPERACIONAL',
                      'subitem': '79'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM HOSPEDAGENS. ITENS E EXEMPLOS: HOSPEDAGEM, HOTEL, '
                                'DIARIA HOTEL, POUSADA.',
                      'keywords': ['hospedagem', 'hotel', 'diaria hotel', 'pousada'],
                      'nd_completa': '33903980',
                      'nome': 'HOSPEDAGENS',
                      'subitem': '80'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MANUT.CONS.EQUIP. DE PROCESSAMENTO DE DADOS. ITENS '
                                'E EXEMPLOS: MANUTENCAO COMPUTADOR, MANUTENCAO IMPRESSORA, MANUTENCAO SERVIDOR, REPARO '
                                'PLACA MAE.',
                      'keywords': [   'manutencao computador',
                                      'manutencao impressora',
                                      'manutencao servidor',
                                      'reparo placa mae'],
                      'nd_completa': '33903995',
                      'nome': 'MANUT.CONS.EQUIP. DE PROCESSAMENTO DE DADOS',
                      'subitem': '95'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM OUTROS SERVICOS DE TERCEIROS - PESSOA JURIDICA.',
                      'keywords': ['outro servico terceiro', 'servico pessoa juridica'],
                      'nd_completa': '33903999',
                      'nome': 'OUTROS SERVICOS DE TERCEIROS-PESSOA JURIDICA',
                      'subitem': '99'}],
    '449052': [   {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ARMAS DE FOGO E ARMAMENTOS DE CARATER PERMANENTE. '
                                'FUZIS, PISTOLAS, METRALHADORAS, CANHOES E CARABINAS.',
                      'keywords': [   'medicao',
                                      'balanca',
                                      'balanca digital',
                                      'bussola',
                                      'cronometro',
                                      'gps',
                                      'navegador gps',
                                      'paquimetro digital',
                                      'osciloscopio',
                                      'multimetro',
                                      'amperimetro'],
                      'nd_completa': '44905204',
                      'nome': 'APARELHOS DE MEDICAO E ORIENTACAO',
                      'subitem': '04'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM APARELHOS E EQUIPAMENTOS PERMANENTES DE '
                                'COMUNICACAO. RADIOS TRANSCEPTORES, ESTACOES DE RADIO, ANTENAS FIXAS E REPETIDORAS.',
                      'keywords': [   'comunicacao',
                                      'radio amador',
                                      'radio comunicador',
                                      'transmissor',
                                      'receptor',
                                      'pabx',
                                      'interfone',
                                      'central telefonica'],
                      'nd_completa': '44905206',
                      'nome': 'APARELHOS E EQUIPAMENTOS DE COMUNICACAO',
                      'subitem': '06'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM APARELHOS DE MEDICAO E ORIENTACAO. GPS, BUSSOLAS, '
                                'TEODOLITOS, MULTIMETROS, TRENAS A LASER E BALANCAS.',
                      'keywords': [   'aparelho medico',
                                      'raio x',
                                      'cadeira dentista',
                                      'maca hospitalar',
                                      'autoclave',
                                      'estufa hospitalar',
                                      'desfibrilador',
                                      'microscopio',
                                      'esfigmomanometro pedestal'],
                      'nd_completa': '44905208',
                      'nome': 'APAR.EQUIP.UTENS.MED.,ODONT,LABOR.HOSPIT.',
                      'subitem': '08'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM APARELHOS E EQUIP. P/ ESPORTES E DIVERSOES. ITENS E '
                                'EXEMPLOS: APARELHO ESPORTE, BICICLETA ERGOMETRICA, ESTEIRA ERGOMETRICA, MESA TENIS, '
                                'MESA PING PONG, HALTERES PERMANENTE, TRAVE FUTEBOL, TABELA BASQUETE.',
                      'keywords': [   'aparelho esporte',
                                      'bicicleta ergometrica',
                                      'esteira ergometrica',
                                      'mesa tenis',
                                      'mesa ping pong',
                                      'halteres permanente',
                                      'trave futebol',
                                      'tabela basquete'],
                      'nd_completa': '44905210',
                      'nome': 'APARELHOS E EQUIP. P/ ESPORTES E DIVERSOES',
                      'subitem': '10'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM APARELHOS ELETRODOMESTICOS E UTENSILIOS '
                                'PERMANENTES. GELADEIRAS, FOGOES, FORNOS MICRO-ONDAS, LIQUIDIFICADORES INDUSTRIAIS, '
                                'BEBEDOUROS E FREEZERS.',
                      'keywords': [   'eletrodomestico',
                                      'ar condicionado',
                                      'split',
                                      'geladeira',
                                      'refrigerador',
                                      'freezer',
                                      'fogao',
                                      'fogao industrial',
                                      'forno microondas',
                                      'microondas',
                                      'lavadora roupa',
                                      'maquina lavar',
                                      'secadora roupa',
                                      'aspirador po',
                                      'liquidificador industrial',
                                      'batedeira',
                                      'cafeteira eletrica',
                                      'ventilador',
                                      'ventilador parede',
                                      'ventilador teto',
                                      'circulador ar',
                                      'bebedouro',
                                      'purificador agua'],
                      'nd_completa': '44905212',
                      'nome': 'APARELHOS E UTENSILIOS DOMESTICOS',
                      'subitem': '12'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM ARMAMENTOS. ITENS E EXEMPLOS: ARMA, ARMAMENTO, '
                                'FUZIL, PISTOLA, REVOLVER, METRALHADORA.',
                      'keywords': ['arma', 'armamento', 'fuzil', 'pistola', 'revolver', 'metralhadora'],
                      'nd_completa': '44905214',
                      'nome': 'ARMAMENTOS',
                      'subitem': '14'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM COLECOES E MATERIAIS BIBLIOGRAFICOS. ITENS E '
                                'EXEMPLOS: LIVRO PERMANENTE, ENCICLOPEDIA, DICIONARIO BIBLIOTECA, COLECAO '
                                'BIBLIOGRAFICA.',
                      'keywords': [   'livro permanente',
                                      'enciclopedia',
                                      'dicionario biblioteca',
                                      'colecao bibliografica'],
                      'nd_completa': '44905218',
                      'nome': 'COLECOES E MATERIAIS BIBLIOGRAFICOS',
                      'subitem': '18'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EMBARCACOES. ITENS E EXEMPLOS: EMBARCACAO, BARCO, '
                                'LANCHA, BOTE, CANOA, MOTOR POPA.',
                      'keywords': ['embarcacao', 'barco', 'lancha', 'bote', 'canoa', 'motor popa'],
                      'nd_completa': '44905220',
                      'nome': 'EMBARCACOES',
                      'subitem': '20'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE MANOBRA E PATRULHAMENTO. ITENS E '
                                'EXEMPLOS: BARRACA CAMPANHA, CAMA CAMPANHA, FAROL BUSCA, SIRENE VIATURA.',
                      'keywords': ['barraca campanha', 'cama campanha', 'farol busca', 'sirene viatura'],
                      'nd_completa': '44905222',
                      'nome': 'EQUIPAMENTOS DE MANOBRA E PATRULHAMENTO',
                      'subitem': '22'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS PERMANENTES DE PROTECAO, SEGURANCA E '
                                'SOCORRO. EXTINTORES DE INCENDIO PERMANENTES, COLETES BALISTICOS, ESCADAS E SISTEMAS '
                                'DE ALARME.',
                      'keywords': [   'cofre',
                                      'cofre aco',
                                      'extintor permanente',
                                      'catraca',
                                      'camera seguranca',
                                      'cftv',
                                      'alarme seguranca',
                                      'sistema alarme',
                                      'cerca eletrica'],
                      'nd_completa': '44905224',
                      'nome': 'EQUIPAMENTO DE PROTECAO, SEGURANCA E SOCORRO',
                      'subitem': '24'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM INSTRUMENTOS MUSICAIS E ARTISTICOS. ITENS E '
                                'EXEMPLOS: INSTRUMENTO MUSICAL, VIOLAO, GUITARRA, TECLADO MUSICAL, SAXOFONE, TROMPETE, '
                                'BATERIA MUSICAL, CAIXA FANFARRA, CLARINETE.',
                      'keywords': [   'instrumento musical',
                                      'violao',
                                      'guitarra',
                                      'teclado musical',
                                      'saxofone',
                                      'trompete',
                                      'bateria musical',
                                      'caixa fanfarra',
                                      'clarinete'],
                      'nd_completa': '44905226',
                      'nome': 'INSTRUMENTOS MUSICAIS E ARTISTICOS',
                      'subitem': '26'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS E EQUIPAMENTOS DE NATUREZA INDUSTRIAL. '
                                'ITENS E EXEMPLOS: MAQUINA INDUSTRIAL, BETONEIRA, TORNO MECANICO, PRENSA INDUSTRIAL.',
                      'keywords': ['maquina industrial', 'betoneira', 'torno mecanico', 'prensa industrial'],
                      'nd_completa': '44905228',
                      'nome': 'MAQUINAS E EQUIPAMENTOS DE NATUREZA INDUSTRIAL',
                      'subitem': '28'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS E EQUIPAMENTOS ENERGETICOS. GRUPOS '
                                'GERADORES DE ENERGIA, TRANSFORMADORES ELETRICOS, PAINEIS SOLARES E NOBREAKS DE GRANDE '
                                'PORTE.',
                      'keywords': [   'gerador',
                                      'gerador energia',
                                      'gerador diesel',
                                      'nobreak',
                                      'no-break',
                                      'transformador',
                                      'estabilizador industrial'],
                      'nd_completa': '44905230',
                      'nome': 'MAQUINAS E EQUIPAMENTOS ENERGETICOS',
                      'subitem': '30'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS E EQUIPAMENTOS GRAFICOS. ITENS E EXEMPLOS: '
                                'GUILHOTINA PAPEL, PLASTIFICADORA, ENCADERNADORA, COPIADORA.',
                      'keywords': ['guilhotina papel', 'plastificadora', 'encadernadora', 'copiadora'],
                      'nd_completa': '44905232',
                      'nome': 'MAQUINAS E EQUIPAMENTOS GRAFICOS',
                      'subitem': '32'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE AUDIO, VIDEO E FOTO. CAMERAS '
                                'FOTOGRAFICAS, FILMADORAS, CAIXAS DE SOM ACUSTICAS, PROJETORES MULTIMIDIA E MESAS DE '
                                'SOM.',
                      'keywords': [   'camera',
                                      'camera digital',
                                      'camera fotografica',
                                      'filmadora',
                                      'projetor',
                                      'projetor multimidia',
                                      'datashow',
                                      'data show',
                                      'tela projecao',
                                      'caixa som',
                                      'caixa acustica',
                                      'amplificador som',
                                      'microfone sem fio',
                                      'televisor',
                                      'tv led',
                                      'smart tv',
                                      'mesa som'],
                      'nd_completa': '44905233',
                      'nome': 'EQUIPAMENTOS PARA AUDIO, VIDEO E FOTO',
                      'subitem': '33'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS E EQUIPAMENTOS DIVERSOS. COMPRESSORES DE '
                                'AR, LAVADORAS DE ALTA PRESSAO, BETONEIRAS E MOTORES ESTACIONARIOS.',
                      'keywords': [   'lavadora alta pressao',
                                      'vap',
                                      'furadeira bancada',
                                      'cortador grama',
                                      'aparador grama'],
                      'nd_completa': '44905234',
                      'nome': 'MAQUINAS, UTENSILIOS E EQUIPAMENTOS DIVERSOS',
                      'subitem': '34'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE PROCESSAMENTO DE DADOS. '
                                'COMPUTADORES DESKTOP, NOTEBOOKS, SERVIDORES, IMPRESSORAS A LASER, SCANNERS E '
                                'MONITORES.',
                      'keywords': ['material tic permanente', 'equipamento informatica'],
                      'nd_completa': '44905235',
                      'nome': 'MATERIAL DE TIC (PERMANENTE)',
                      'subitem': '35'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS, INSTALACOES E UTENS. DE ESCRITORIO. ITENS '
                                'E EXEMPLOS: RELOGIO PONTO, CALCULADORA MESA, ROTULADOR ELETRONICO, FRAGMENTADORA '
                                'PAPEL.',
                      'keywords': ['relogio ponto', 'calculadora mesa', 'rotulador eletronico', 'fragmentadora papel'],
                      'nd_completa': '44905236',
                      'nome': 'MAQUINAS, INSTALACOES E UTENS. DE ESCRITORIO',
                      'subitem': '36'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE TIC - ATIVOS DE REDE. ITENS E '
                                'EXEMPLOS: SWITCH, SWITCH REDE, ROTEADOR, FIREWALL, ACCESS POINT, RACK SERVIDOR.',
                      'keywords': ['switch', 'switch rede', 'roteador', 'firewall', 'access point', 'rack servidor'],
                      'nd_completa': '44905237',
                      'nome': 'EQUIPAMENTOS DE TIC - ATIVOS DE REDE',
                      'subitem': '37'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQ., FERRAMENTAS E UTENSILIOS DE OFICINA. ITENS E '
                                'EXEMPLOS: COMPRESSOR AR, COMPRESSOR, ESMERIL, MOTOESMERIL, MACACO JACARE, ELEVADOR '
                                'VEICULAR, FURADEIRA IMPACTO, LIXADEIRA ANGULAR, SERRA CIRCULAR, SERRA FITA, MAQUINA '
                                'SOLDA.',
                      'keywords': [   'compressor ar',
                                      'compressor',
                                      'esmeril',
                                      'motoesmeril',
                                      'macaco jacare',
                                      'elevador veicular',
                                      'furadeira impacto',
                                      'lixadeira angular',
                                      'serra circular',
                                      'serra fita',
                                      'maquina solda'],
                      'nd_completa': '44905238',
                      'nome': 'MAQ., FERRAMENTAS E UTENSILIOS DE OFICINA',
                      'subitem': '38'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIP. E UTENSILIOS HIDRAULICOS E ELETRICOS. ITENS '
                                'E EXEMPLOS: BOMBA DAGUA, MOTOBOMBA, BOMBA POCO, BOMBA SUBMERSA.',
                      'keywords': ['bomba dagua', 'motobomba', 'bomba poco', 'bomba submersa'],
                      'nd_completa': '44905239',
                      'nome': 'EQUIP. E UTENSILIOS HIDRAULICOS E ELETRICOS',
                      'subitem': '39'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MAQUINAS E EQUIPAMENTOS AGRIC. E RODOVIARIOS. ITENS '
                                'E EXEMPLOS: TRATOR, ROCADEIRA, ROCADEIRA GASOLINA, MOTOSSERRA, MOTO SERRA.',
                      'keywords': ['trator', 'rocadeira', 'rocadeira gasolina', 'motosserra', 'moto serra'],
                      'nd_completa': '44905240',
                      'nome': 'MAQUINAS E EQUIPAMENTOS AGRIC. E RODOVIARIOS',
                      'subitem': '40'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE TIC - COMPUTADORES, NOTEBOOKS, '
                                'TERMINAIS E ESTACOES DE TRABALHO.',
                      'keywords': ['computador', 'desktop', 'notebook', 'laptop', 'monitor', 'monitor led', 'tablet'],
                      'nd_completa': '44905241',
                      'nome': 'EQUIPAMENTOS DE TIC - COMPUTADORES',
                      'subitem': '41'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM MOBILIARIO EM GERAL. ARMARIOS DE ACO, MESAS DE '
                                'ESCRITORIO, CADEIRAS ERGONOMICAS, ESTANTES DE ACO, ARQUIVOS DESLIZANTES, BALCOES E '
                                'POLTRONAS.',
                      'keywords': [   'mobiliario',
                                      'movel',
                                      'moveis',
                                      'armario',
                                      'armario aco',
                                      'armario madeira',
                                      'arquivo aco',
                                      'cadeira',
                                      'cadeira giratoria',
                                      'cadeira fixa',
                                      'cadeira escritorio',
                                      'cadeira presidente',
                                      'cadeira diretor',
                                      'poltrona',
                                      'mesa',
                                      'mesa escritorio',
                                      'mesa reuniao',
                                      'mesa l',
                                      'mesa computador',
                                      'estante',
                                      'estante aco',
                                      'estante madeira',
                                      'gaveteiro',
                                      'gaveteiro volante',
                                      'sofa',
                                      'balcao',
                                      'banco',
                                      'banqueta',
                                      'beliche',
                                      'cama',
                                      'colchao',
                                      'escrivaninha',
                                      'roupeiro aco',
                                      'vestiario',
                                      'prateleira aco',
                                      'prancheta desenho',
                                      'mapoteca',
                                      'criado mudo'],
                      'nd_completa': '44905242',
                      'nome': 'MOBILIARIO EM GERAL',
                      'subitem': '42'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE TIC - SERVIDORES/STORAGE. ITENS E '
                                'EXEMPLOS: SERVIDOR, SERVIDOR REDE, STORAGE, NAS STORAGE.',
                      'keywords': ['servidor', 'servidor rede', 'storage', 'nas storage'],
                      'nd_completa': '44905243',
                      'nome': 'EQUIPAMENTOS DE TIC - SERVIDORES/STORAGE',
                      'subitem': '43'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE TIC - IMPRESSORAS. ITENS E '
                                'EXEMPLOS: IMPRESSORA, MULTIFUNCIONAL, IMPRESSORA LASER, IMPRESSORA TERMICA, SCANNER, '
                                'PLOTTER.',
                      'keywords': [   'impressora',
                                      'multifuncional',
                                      'impressora laser',
                                      'impressora termica',
                                      'scanner',
                                      'plotter'],
                      'nd_completa': '44905245',
                      'nome': 'EQUIPAMENTOS DE TIC - IMPRESSORAS',
                      'subitem': '45'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM EQUIPAMENTOS DE TIC - TELEFONIA. ITENS E EXEMPLOS: '
                                'APARELHO TELEFONICO, TELEFONE IP, TERMINAL TELEFONICO, VIDEOCONFERENCIA.',
                      'keywords': ['aparelho telefonico', 'telefone ip', 'terminal telefonico', 'videoconferencia'],
                      'nd_completa': '44905247',
                      'nome': 'EQUIPAMENTOS DE TIC - TELEFONIA',
                      'subitem': '47'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM VEICULOS DIVERSOS. AUTOMOVEIS, CAMINHOES, VIATURAS '
                                'OPERACIONAIS, MOTOCICLETAS, AMBULANCIAS E ONIBUS.',
                      'keywords': ['bicicleta', 'carrinho mao', 'empilhadeira', 'paleteira'],
                      'nd_completa': '44905248',
                      'nome': 'VEICULOS DIVERSOS',
                      'subitem': '48'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM PECAS E EQUIPAMENTOS NAO INCORPORAVEIS A IMOVEIS. '
                                'APARELHOS DE AR CONDICIONADO SPLIT, VENTILADORES DE TETO E CORTINAS DE AR.',
                      'keywords': ['persiana', 'cortina', 'tapete', 'toldos', 'biombo', 'divisoria removivel'],
                      'nd_completa': '44905251',
                      'nome': 'PECAS NAO INCORPORAVEIS A IMOVEIS',
                      'subitem': '51'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM VEICULOS DE TRACAO MECANICA. ITENS E EXEMPLOS: '
                                'VIATURA, AUTOMOVEL, CARRO, CAMINHAO, ONIBUS, MICROONIBUS, AMBULANCIA, CAMIONETE, VAN.',
                      'keywords': [   'viatura',
                                      'automovel',
                                      'carro',
                                      'caminhao',
                                      'onibus',
                                      'microonibus',
                                      'ambulancia',
                                      'camionete',
                                      'van'],
                      'nd_completa': '44905252',
                      'nome': 'VEICULOS DE TRACAO MECANICA',
                      'subitem': '52'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM AQUISICAO DE SOFTWARE PRONTO. ITENS E EXEMPLOS: '
                                'SOFTWARE, LICENCA SOFTWARE, LICENCA PERPETUA, SISTEMA OPERACIONAL.',
                      'keywords': ['software', 'licenca software', 'licenca perpetua', 'sistema operacional'],
                      'nd_completa': '44905255',
                      'nome': 'AQUISICAO DE SOFTWARE PRONTO',
                      'subitem': '55'},
                  {   'funcao': 'REGISTRA O VALOR DAS DESPESAS COM OUTROS EQUIPAMENTOS E MATERIAL PERMANENTE NAO '
                                'ESPECIFICADOS.',
                      'keywords': ['outro material permanente', 'equipamento permanente diverso'],
                      'nd_completa': '44905299',
                      'nome': 'OUTROS MATERIAIS PERMANENTES',
                      'subitem': '99'}]}

def identificar_grupo_nd(nd: str) -> str:
    """Identifica se a ND pertence ao grupo 339030, 449052 ou 339039."""
    if not nd:
        return "339030"
    nd_limpa = re.sub(r'\D', '', str(nd))
    for grupo in ["339030", "449052", "339039"]:
        if grupo in nd_limpa:
            return grupo
    if "30" in nd_limpa and ("3390" in nd_limpa or "9030" in nd_limpa):
        return "339030"
    if "52" in nd_limpa and ("4490" in nd_limpa or "9052" in nd_limpa):
        return "449052"
    if "39" in nd_limpa and ("3390" in nd_limpa or "9039" in nd_limpa):
        return "339039"
    return "339030"

def buscar_correspondencias_subitens(nd: str, descricao_item: str) -> List[Dict]:
    """
    Busca todas as correspondências de subitens para uma dada ND com base na FUNÇÃO oficial
    e no nome do subitem, extraindo os termos coincidentes.
    Retorna uma lista de dicionários ordenada por relevância (score decrescente).
    """
    if not descricao_item:
        return []

    grupo = identificar_grupo_nd(nd)
    if not grupo or grupo not in CATALOGO_SUBITENS:
        desc_norm = _normalizar_texto(descricao_item)
        if any(w in desc_norm for w in ["armario", "cadeira", "mesa", "computador", "notebook", "estante", "servidor"]):
            grupo = "449052"
        elif any(w in desc_norm for w in ["servico", "manutencao preventiva", "reparo em", "locacao"]):
            grupo = "339039"
        else:
            grupo = "339030"

    desc_norm = _normalizar_texto(descricao_item)
    palavras_desc = extrair_palavras_chave(descricao_item)
    if not palavras_desc:
        palavras_desc = [p for p in desc_norm.split() if len(p) >= 2]

    correspondencias = []

    for item in CATALOGO_SUBITENS[grupo]:
        funcao_norm = _normalizar_texto(item.get("funcao", ""))
        nome_norm = _normalizar_texto(item.get("nome", ""))
        keywords_norm = [_normalizar_texto(k) for k in item.get("keywords", [])]

        score = 0
        termos_coincidentes = []

        # 1. Match de frase inteira na FUNCAO ou NOME
        if len(desc_norm) > 4:
            if desc_norm in funcao_norm:
                score += 35
                termos_coincidentes.append(descricao_item[:35])
            elif desc_norm in nome_norm:
                score += 30
                termos_coincidentes.append(descricao_item[:30])

        # 2. Match de n-grams (pares de palavras consecutivas)
        tokens_desc = desc_norm.split()
        for i in range(len(tokens_desc) - 1):
            par = f"{tokens_desc[i]} {tokens_desc[i+1]}"
            if len(par) >= 6 and (tokens_desc[i] not in STOPWORDS_SUBITEM or tokens_desc[i+1] not in STOPWORDS_SUBITEM):
                if par in funcao_norm:
                    score += 18
                    if par not in termos_coincidentes:
                        termos_coincidentes.append(par)
                elif par in nome_norm:
                    score += 15
                    if par not in termos_coincidentes:
                        termos_coincidentes.append(par)

        # 3. Match de termos individuais na FUNÇÃO
        for p in palavras_desc:
            # Palavra inteira na FUNÇÃO
            if re.search(r'\b' + re.escape(p) + r'\b', funcao_norm):
                score += 8
                if p not in termos_coincidentes:
                    termos_coincidentes.append(p)
            elif p in funcao_norm:
                score += 4
                if p not in termos_coincidentes:
                    termos_coincidentes.append(p)

            # Palavra no NOME
            if re.search(r'\b' + re.escape(p) + r'\b', nome_norm):
                score += 7
                if p not in termos_coincidentes:
                    termos_coincidentes.append(p)

            # Palavra nas keywords
            for kw in keywords_norm:
                if p == kw or (len(p) >= 4 and p in kw):
                    score += 6
                    if p not in termos_coincidentes:
                        termos_coincidentes.append(p)
                    break

        if score >= 8:
            correspondencias.append({
                "subitem": item["subitem"],
                "nd_completa": item["nd_completa"],
                "nome": item["nome"],
                "funcao": item.get("funcao", ""),
                "score": score,
                "termos": termos_coincidentes
            })

    correspondencias.sort(key=lambda x: x["score"], reverse=True)
    # Se nenhuma atingiu 8 pontos mas houve match, pega a melhor correspondência
    if not correspondencias:
        for item in CATALOGO_SUBITENS[grupo]:
            # repete checagem mínima
            pass
    return correspondencias[:5]

_cache_classificacao_ia: Dict[str, Dict] = {}

def classificar_subitem_com_ia(nd: str, descricao_item: str) -> Optional[Dict]:
    """
    Utiliza IA (Gemini) para analisar a essência e finalidade do item e apontar
    com precisão o subitem correspondente da Natureza de Despesa (ND).
    Retorna dict com 'subitem', 'nome', 'justificativa' ou None.
    """
    if not descricao_item or not nd:
        return None
    
    chave_cache = f"{nd}_{descricao_item.strip().lower()}"
    if chave_cache in _cache_classificacao_ia:
        return _cache_classificacao_ia[chave_cache]
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    grupo = identificar_grupo_nd(nd)
    subitens_disponiveis = CATALOGO_SUBITENS.get(grupo, [])
    if not subitens_disponiveis:
        return None

    lista_subitens_txt = "\n".join([
        f"- {s['subitem']} ({s['nome']}): {s.get('funcao', '')[:140]}..."
        for s in subitens_disponiveis
    ])

    prompt = f"""Você é um auditor e especialista em Contabilidade Pública, SIAFI e Execução Orçamentária das Forças Armadas brasileiras.
Classifique com máxima exatidão o item abaixo no subitem mais apropriado da Natureza de Despesa {nd}.

Item: "{descricao_item}"

Subitens oficiais da ND {nd}:
{lista_subitens_txt}

Regras:
1. Avalie a finalidade e emprego real do material ou serviço (ex: vergalhão, ferro armado, cimento, areia e tijolo são materiais de construção civil e alvenaria para manutenção de bens imóveis, subitem 24 na ND 339030).
2. Selecione apenas 1 subitem da lista oficial.
3. Responda ESTRITAMENTE em formato JSON com:
{{
  "subitem": "código de 2 dígitos",
  "nome": "nome oficial do subitem",
  "justificativa": "explicação técnica sucinta (1 a 2 frases) justificando o enquadramento"
}}
"""

    models_to_try = ["gemini-3.8-flash", "gemini-3.6-flash"]
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aistudio-build"
    }

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 400,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                texto_resp = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if texto_resp:
                    texto_limpo = re.sub(r'^```json\s*', '', texto_resp.strip())
                    texto_limpo = re.sub(r'\s*```$', '', texto_limpo.strip())
                    res_json = json.loads(texto_limpo)
                    
                    sub_cod = str(res_json.get("subitem", "")).strip().zfill(2)
                    cand_nome = obter_nome_subitem(nd, sub_cod)
                    resultado = {
                        "subitem": sub_cod,
                        "nome": cand_nome or res_json.get("nome", ""),
                        "justificativa": res_json.get("justificativa", ""),
                        "modelo": model_name
                    }
                    _cache_classificacao_ia[chave_cache] = resultado
                    return resultado
        except Exception:
            continue

    return None

def determinar_subitem(nd: str, descricao_item: str) -> str:
    """Retorna o código de 2 dígitos do subitem de maior pontuação ou vazio."""
    # Tenta usar cache de IA se disponível
    chave_cache = f"{nd}_{str(descricao_item).strip().lower()}"
    if chave_cache in _cache_classificacao_ia:
        return _cache_classificacao_ia[chave_cache]["subitem"]
    corrs = buscar_correspondencias_subitens(nd, descricao_item)
    if corrs:
        return corrs[0]["subitem"]
    return ""

def obter_nome_subitem(nd: str, subitem: str) -> str:
    """Retorna o nome por extenso do subitem."""
    if not subitem:
        return ""
    grupo = identificar_grupo_nd(nd)
    if grupo in CATALOGO_SUBITENS:
        sub_busca = str(subitem).strip().zfill(2)
        for cand in CATALOGO_SUBITENS[grupo]:
            if cand["subitem"] == sub_busca:
                return cand["nome"]
    return ""

def obter_funcao_subitem(nd: str, subitem: str) -> str:
    """Retorna a redação oficial da FUNÇÃO do subitem (SIAFI/MCASP)."""
    if not subitem:
        return ""
    grupo = identificar_grupo_nd(nd)
    if grupo in CATALOGO_SUBITENS:
        sub_busca = str(subitem).strip().zfill(2)
        for cand in CATALOGO_SUBITENS[grupo]:
            if cand["subitem"] == sub_busca:
                return cand.get("funcao", "")
    return ""

def listar_subitens_por_nd(nd: str) -> List[Dict]:
    """Retorna a lista completa de subitens de uma determinada ND."""
    grupo = identificar_grupo_nd(nd)
    return CATALOGO_SUBITENS.get(grupo, [])

def montar_opcoes_subitem(nd: str, descricao_item: str, subitem_atual: str = "", sugestao_ia: Optional[Dict] = None) -> Tuple[List[str], int, Dict[str, str]]:
    """
    Gera a lista completa de opções para o selectbox, colocando as correspondências
    encontradas na FUNÇÃO e pela IA no topo.
    Retorna: (opcoes, index_padrao, mapa_opcao_para_codigo)
    """
    correspondencias = buscar_correspondencias_subitens(nd, descricao_item)
    todos_subitens = listar_subitens_por_nd(nd)

    opcoes = []
    mapa_codigos = {}
    subitens_incluidos = set()

    # 0. Sugestão da IA (Gemini) se fornecida
    if sugestao_ia and sugestao_ia.get("subitem"):
        sub_ia = str(sugestao_ia["subitem"]).strip().zfill(2)
        nome_ia = sugestao_ia.get("nome") or obter_nome_subitem(nd, sub_ia)
        rotulo_ia = f"✨ {sub_ia} - {nome_ia} [Recomendação IA - Gemini]"
        opcoes.append(rotulo_ia)
        mapa_codigos[rotulo_ia] = sub_ia
        subitens_incluidos.add(sub_ia)

    # 1. Correspondências identificadas por palavras-chave na FUNÇÃO oficial
    for c in correspondencias:
        sub = c["subitem"]
        if sub in subitens_incluidos:
            continue
        nome = c["nome"]
        termos_str = ", ".join(c.get("termos", [])[:3])
        if termos_str:
            rotulo = f"🎯 {sub} - {nome} [Correspondência na Função: {termos_str}]"
        else:
            rotulo = f"🎯 {sub} - {nome}"
        opcoes.append(rotulo)
        mapa_codigos[rotulo] = sub
        subitens_incluidos.add(sub)

    # 2. Outros subitens da ND para seleção livre
    for s in todos_subitens:
        sub = s["subitem"]
        if sub not in subitens_incluidos:
            rotulo = f"📋 {sub} - {s['nome']}"
            opcoes.append(rotulo)
            mapa_codigos[rotulo] = sub
            subitens_incluidos.add(sub)

    # 3. Opção manual
    rotulo_manual = "✏️ Digitar outro código manualmente..."
    opcoes.append(rotulo_manual)
    mapa_codigos[rotulo_manual] = ""

    # Determina o índice padrão
    idx_selecionado = 0
    if subitem_atual:
        sub_alvo = str(subitem_atual).strip().zfill(2)
        for i, op in enumerate(opcoes):
            if mapa_codigos.get(op) == sub_alvo:
                idx_selecionado = i
                break
    elif sugestao_ia and sugestao_ia.get("subitem"):
        idx_selecionado = 0

    return opcoes, idx_selecionado, mapa_codigos

# =====================================================================


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & DESIGN SYSTEM
# =====================================================================
st.set_page_config(
    page_title="Sistema Integrado de Gestão Orçamentária & Pregões",
    page_icon="🇧🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

def injetar_estilos_customizados():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* =========================================================================
       COMPATIBILIDADE UNIVERSAL DE CORES (MOZILLA FIREFOX, CHROME, OPERA, SAFARI)
       Previne que temas escuros do navegador ou SO deixem textos e inputs apagados
       ========================================================================= */
    :root, html, body, .stApp {
        color-scheme: light !important;
        background-color: #f8fafc !important;
        color: #0f172a !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
        --text-color: #0f172a !important;
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --primary-color: #2d6a4f !important;
    }

    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, input, select, textarea, button {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Botão de abrir/fechar a barra lateral (Sidebar) visível e destacado no desktop e mobile */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    button[aria-label*="sidebar" i],
    button[data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: inline-flex !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebarCollapsedControl"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
        padding: 4px !important;
        margin: 6px 0 0 10px !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: #1b4332 !important;
    }
    
    .stApp {
        background-color: #f8fafc !important;
    }

    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        max-width: 96% !important;
    }

    /* Sidebar estilizada */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.03);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
    }
    section[data-testid="stSidebar"] * {
        color: #1e293b;
    }

    /* Abas Modernas Executivas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 22px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13.5px;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        -moz-text-fill-color: #64748b !important;
        border: none !important;
        background-color: transparent;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        background-color: rgba(255, 255, 255, 0.8);
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #1b4332 !important;
        -webkit-text-fill-color: #1b4332 !important;
        -moz-text-fill-color: #1b4332 !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.07);
        border-bottom: 2.5px solid #2d6a4f !important;
    }

    /* Cartões de Métricas */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.08);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 11.5px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        -moz-text-fill-color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        letter-spacing: -0.5px !important;
    }

    /* Botões Primários - Verde Exército */
    .stButton button[kind="primary"], .stButton button[data-testid="baseButton-primary"] {
        background: linear-gradient(180deg, #2d6a4f 0%, #1b4332 100%) !important;
        border: 1px solid #143527 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        -moz-text-fill-color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 9px 20px !important;
        font-size: 14px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.15s ease !important;
    }
    .stButton button[kind="primary"]:hover, .stButton button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(180deg, #387c5d 0%, #24553f 100%) !important;
        box-shadow: 0 4px 12px -1px rgba(27, 67, 50, 0.3) !important;
        transform: translateY(-1px);
    }

    /* Botões Secundários */
    .stButton button[kind="secondary"], .stButton button[data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
        -moz-text-fill-color: #334155 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 9px 20px !important;
        font-size: 14px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.15s ease !important;
    }
    .stButton button[kind="secondary"]:hover, .stButton button[data-testid="baseButton-secondary"]:hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06) !important;
    }

    /* Formulários e Containers */
    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }

    /* =========================================================================
       BLINDAGEM TOTAL DE ENTRADAS DE TEXTO (INPUTS, TEXTAREAS, SENHAS, SELECTS)
       Garante visibilidade máxima e alto contraste ao digitar no Mozilla Firefox e demais navegadores
       ========================================================================= */
    input,
    textarea,
    select,
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stTextArea textarea,
    [data-baseweb="input"] input,
    [data-baseweb="base-input"] input,
    [data-baseweb="input"] textarea,
    [data-baseweb="base-input"] textarea,
    input[type="text"],
    input[type="password"],
    input[type="number"],
    input[type="search"],
    input[type="email"] {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        caret-color: #1b4332 !important;
        opacity: 1 !important;
    }

    /* Efeito de foco nítido ao digitar */
    input:focus,
    textarea:focus,
    select:focus,
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    [data-baseweb="input"]:focus-within,
    [data-baseweb="base-input"]:focus-within {
        border-color: #2d6a4f !important;
        box-shadow: 0 0 0 3px rgba(45, 106, 79, 0.15) !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        background-color: #ffffff !important;
    }

    /* Autofill compatível em Mozilla Firefox, Chrome, Opera, Safari */
    input:-webkit-autofill,
    input:-webkit-autofill:hover,
    input:-webkit-autofill:focus,
    input:-webkit-autofill:active {
        -webkit-box-shadow: 0 0 0 30px #ffffff inset !important;
        -webkit-text-fill-color: #0f172a !important;
        caret-color: #1b4332 !important;
        transition: background-color 5000s ease-in-out 0s !important;
    }
    input:-moz-autofill,
    input:-moz-autofill:hover,
    input:-moz-autofill:focus {
        filter: none !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
    }

    /* Placeholders visíveis e legíveis (sem esmaecimento excessivo) */
    ::placeholder,
    ::-webkit-input-placeholder,
    ::-moz-placeholder,
    :-moz-placeholder,
    :-ms-input-placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        -moz-text-fill-color: #64748b !important;
        opacity: 1 !important;
        font-weight: 400 !important;
    }

    /* Rótulos de campos (Labels) escuros e nítidos */
    label,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
        -moz-text-fill-color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        opacity: 1 !important;
    }

    /* Menus suspensos (Selectbox / Multiselect) */
    .stSelectbox [data-baseweb="select"],
    .stMultiselect [data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
    }
    .stSelectbox [data-baseweb="select"] *,
    .stMultiselect [data-baseweb="select"] *,
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* Lista suspensa de opções (Popover) */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    div[role="listbox"],
    ul[role="listbox"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }
    li[role="option"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    li[role="option"] span,
    li[role="option"] div,
    li[role="option"] * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #f1f5f9 !important;
        color: #1b4332 !important;
    }
    li[role="option"][aria-selected="true"] * {
        color: #1b4332 !important;
        -webkit-text-fill-color: #1b4332 !important;
        -moz-text-fill-color: #1b4332 !important;
        font-weight: 700 !important;
    }

    /* Tipografia geral, títulos, parágrafos e markdown legíveis */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
    }

    p, span, li,
    .stMarkdown p, .stMarkdown span, .stMarkdown li,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] li {
        color: #1e293b;
        opacity: 1 !important;
    }

    strong, b,
    .stMarkdown strong, .stMarkdown b,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] b {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        -moz-text-fill-color: #0f172a !important;
        font-weight: 700 !important;
    }

    .stCaption, [data-testid="stCaptionContainer"], small {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        -moz-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }

    /* Radio buttons e Checkboxes */
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label span,
    [data-testid="stCheckbox"] label span {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
        -moz-text-fill-color: #1e293b !important;
        font-weight: 500 !important;
    }

    /* Expander estilizado */
    div[data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary span,
    div[data-testid="stExpander"] summary p {
        font-weight: 600 !important;
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
        -moz-text-fill-color: #1e293b !important;
        font-size: 14.5px !important;
    }
    div[data-testid="stExpander"] summary svg {
        fill: #1e293b !important;
    }

    /* Alertas */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
    }

    /* Tabelas e Dataframes */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    }
    [data-testid="stDataFrame"] canvas,
    [data-testid="stDataEditor"] canvas {
        color-scheme: light !important;
    }
    table, th, td {
        color: #0f172a !important;
    }
    </style>
    """, unsafe_allow_html=True)

injetar_estilos_customizados()

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
    while page <= 10:
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

            if novos == 0:
                break
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
            for a_eye in s_arp.find_all('a', href=True):
                h = a_eye['href'].strip()
                m_it = re.search(r"/transparencia/arpshow/itens/(\d+)/", h)
                if m_it:
                    it_num_int = str(int(m_it.group(1)))
                    link_eye = h if h.startswith('http') else f"{BASE_CONTRATOS}{h}"
                    itens_olho[it_num_int] = link_eye
                    itens_olho[m_it.group(1)] = link_eye

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

def obter_saldo_item_contratos(session: requests.Session, uasg: str, num_compra: str, ano_compra: str, num_item: str, atas: Optional[List[Dict]] = None) -> Dict:
    from bs4 import BeautifulSoup
    if atas is None:
        atas = buscar_atas_contratos(session, uasg, num_compra, ano_compra)
    num_int = int(num_item) if str(num_item).isdigit() else 0
    num_str = str(num_int)
    num_5 = str(num_int).zfill(5)

    target_eye_url = ""
    target_ata = None

    for ata in atas:
        itens_map = ata.get("itensOlho", {})
        if num_str in itens_map:
            target_eye_url = itens_map[num_str]
            target_ata = ata
            break
        elif num_5 in itens_map:
            target_eye_url = itens_map[num_5]
            target_ata = ata
            break

    # Se o item NÃO existe em nenhuma ARP homologada: é Deserto, Fracassado ou Cancelado
    if not target_eye_url or not target_ata:
        return {
            "qtd_registrada": "0",
            "qtd_empenhada": "0",
            "saldo_empenho": "0",
            "fornecedor": "Deserto / Fracassado",
            "fornecedor_puro": "Deserto / Fracassado",
            "cnpj_puro": "",
            "valor_unitario_sugerido": 0.0,
            "descricao_detalhada_ata": "",
            "empenhos_resumo": "Nenhum (Item Deserto)",
            "empenhos_lista": [],
            "numero_ata": "-",
            "pdf_ata": "",
            "deserto": True
        }

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
        "numero_ata": target_ata["numeroAta"] if target_ata else "-",
        "pdf_ata": target_ata["pdfUrl"] if target_ata else "",
        "deserto": False
    }

    try:
        res = session.get(target_eye_url.strip(), headers=HEADERS_HTTP, timeout=12)
        if not res.ok or "não encontrada" in res.text.lower() or "erro interno" in res.text.lower():
            resultado["deserto"] = True
            resultado["fornecedor"] = "Deserto / Fracassado"
            resultado["fornecedor_puro"] = "Deserto / Fracassado"
            return resultado

        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Extração da Descrição Técnica / Especificação
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

        # 2. Fornecedor, CNPJ e Valor Unitário
        found_cnpj = ""
        candidato_nome = ""
        vlr_unit = 0.0

        for tbl in soup.find_all('table'):
            txt_tbl = tbl.get_text(" ", strip=True)
            m_cnpj = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", txt_tbl)
            if m_cnpj:
                found_cnpj = m_cnpj.group(0)
                for tr in tbl.find_all('tr'):
                    if found_cnpj in tr.get_text():
                        tds = [td.get_text(" ", strip=True) for td in tr.find_all('td')]
                        for c in tds:
                            c_sem = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", c).strip()
                            if re.search(r"[A-Za-zÀ-ÿ]{3,}", c_sem) and not any(k in c_sem.lower() for k in ['classifica', 'quantidade', 'valor unit', 'total', 'vlr', 'r$']):
                                candidato_nome = c_sem
                                break
                        for c in reversed(tds):
                            if "r$" in c.lower() or re.search(r"\d+,\d{2,4}", c):
                                vlr_unit = converter_para_float(c)
                                break
                        break
                if found_cnpj:
                    break

        nome_forn_limpo = limpar_nome_fornecedor(candidato_nome, found_cnpj)
        if not nome_forn_limpo or nome_forn_limpo == found_cnpj or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", nome_forn_limpo)) == 0:
            if found_cnpj:
                nome_auto = consultar_razao_social_cnpj(found_cnpj)
                if nome_auto:
                    nome_forn_limpo = nome_auto

        fornecedor_puro = nome_forn_limpo or found_cnpj
        if nome_forn_limpo and found_cnpj and nome_forn_limpo != found_cnpj:
            fornecedor_display = f"{nome_forn_limpo} ({found_cnpj})"
        else:
            fornecedor_display = fornecedor_puro or found_cnpj or "Não informado"

        resultado["cnpj_puro"] = found_cnpj
        resultado["fornecedor_puro"] = fornecedor_puro
        resultado["fornecedor"] = fornecedor_display
        resultado["valor_unitario_sugerido"] = vlr_unit

        # 3. Varredura Oficial de Saldos da UASG no Detalhamento do Item
        uasg_clean = uasg.strip()

        # Isolar tabelas folha (que não contêm <table> interno) para evitar interferência de tabelas aninhadas
        all_soup_tables = soup.find_all('table')
        leaf_tables = [t for t in all_soup_tables if not t.find('table')]
        if not leaf_tables:
            leaf_tables = all_soup_tables

        # A) Notas de Empenho (NE) emitidas para esta UASG
        soma_empenhos_nes = 0.0
        empenhos_list = []
        tem_ne_uasg = False

        for tbl in leaf_tables:
            hdr_ths = []
            thead = tbl.find('thead')
            if thead:
                hdr_ths = [th.get_text(" ", strip=True).lower() for th in thead.find_all(['th', 'td'])]
            if not hdr_ths:
                first_tr = tbl.find('tr')
                if first_tr:
                    hdr_ths = [th.get_text(" ", strip=True).lower() for th in first_tr.find_all(['th', 'td'])]

            if any("número de empenho" in h or "numero de empenho" in h or "nota de empenho" in h for h in hdr_ths):
                idx_ne_col = -1
                idx_u_col = -1
                idx_data_col = -1
                idx_qtd_col = -1
                idx_val_col = -1
                for i_c, c_name in enumerate(hdr_ths):
                    if ("número" in c_name or "numero" in c_name or "empenho" in c_name) and "quantidade" not in c_name and "data" not in c_name and idx_ne_col == -1:
                        idx_ne_col = i_c
                    elif "unidade" in c_name and idx_u_col == -1:
                        idx_u_col = i_c
                    elif "data" in c_name and idx_data_col == -1:
                        idx_data_col = i_c
                    elif ("quantidade empenhada" in c_name) or ("quantidade" in c_name and "empenh" in c_name):
                        idx_qtd_col = i_c
                    elif "valor" in c_name and idx_val_col == -1:
                        idx_val_col = i_c

                for tr in tbl.find_all('tr'):
                    tds = [td.get_text(" ", strip=True) for td in tr.find_all(['td', 'th'], recursive=False)]
                    if len(tds) < 5:
                        continue
                    if any("número de empenho" in td.lower() for td in tds):
                        continue

                    col_u = tds[idx_u_col].lower() if idx_u_col != -1 and idx_u_col < len(tds) else ""
                    linha_tr_txt = " ".join(tds).lower()

                    is_match_ne = (uasg_clean in col_u) or (uasg_clean in linha_tr_txt) or (
                        ("gerenciadora" in col_u or "gerenciadora" in linha_tr_txt) and ("não" not in col_u and "nao" not in col_u)
                    )

                    if is_match_ne:
                        m_ne = re.search(r"\b(\d{4}NE\d{4,6})\b", linha_tr_txt, re.IGNORECASE)
                        ne_num = m_ne.group(1).upper() if m_ne else (tds[idx_ne_col] if idx_ne_col != -1 and idx_ne_col < len(tds) else "")
                        d_ne = tds[idx_data_col] if idx_data_col != -1 and idx_data_col < len(tds) else ""
                        q_str = tds[idx_qtd_col] if idx_qtd_col != -1 and idx_qtd_col < len(tds) else "0"
                        v_str = tds[idx_val_col] if idx_val_col != -1 and idx_val_col < len(tds) else ""

                        q_f = converter_para_float(q_str)
                        if q_f > 0:
                            tem_ne_uasg = True
                            soma_empenhos_nes += q_f

                        emp_entry = ne_num or "NE"
                        if d_ne: emp_entry += f" ({d_ne})"
                        if q_str: emp_entry += f": Qtd {q_str}"
                        if v_str: emp_entry += f" [R$ {v_str}]"
                        if emp_entry not in empenhos_list:
                            empenhos_list.append(emp_entry)

        # B) Tabela de Saldos por Unidade no Item (Unidade, Tipo, Qtd Registrada, Qtd Empenhada, Saldo p/ Empenho)
        reg_t3 = None
        emp_t3 = None
        sal_t3 = None

        for tbl in leaf_tables:
            hdr_ths = []
            thead = tbl.find('thead')
            if thead:
                hdr_ths = [th.get_text(" ", strip=True).lower() for th in thead.find_all(['th', 'td'])]
            if not hdr_ths:
                first_tr = tbl.find('tr')
                if first_tr:
                    hdr_ths = [th.get_text(" ", strip=True).lower() for th in first_tr.find_all(['th', 'td'])]

            if any("quantidade empenhada" in h for h in hdr_ths) and any("saldo" in h for h in hdr_ths) and any("unidade" in h for h in hdr_ths):
                idx_u = -1
                idx_tipo = -1
                idx_r = -1
                idx_e = -1
                idx_s = -1
                for i_c, c_name in enumerate(hdr_ths):
                    if "unidade" in c_name and idx_u == -1:
                        idx_u = i_c
                    elif "tipo" in c_name and idx_tipo == -1:
                        idx_tipo = i_c
                    elif ("registrada" in c_name or "homologada" in c_name or "autorizada" in c_name) and idx_r == -1:
                        idx_r = i_c
                    elif "empenhada" in c_name and not any(k in c_name for k in ["saldo", "dispon", "reforço", "anulação"]) and idx_e == -1:
                        idx_e = i_c
                    elif "saldo" in c_name and idx_s == -1:
                        idx_s = i_c

                for tr in tbl.find_all('tr'):
                    tds = [td.get_text(" ", strip=True) for td in tr.find_all(['td', 'th'], recursive=False)]
                    if len(tds) < 4:
                        continue
                    if any("quantidade registrada" in td.lower() for td in tds):
                        continue

                    col_u = tds[idx_u].lower() if idx_u != -1 and idx_u < len(tds) else ""
                    col_tipo = tds[idx_tipo].lower() if idx_tipo != -1 and idx_tipo < len(tds) else ""
                    linha_txt = " ".join(tds).lower()

                    is_uasg = (uasg_clean in col_u) or (uasg_clean in linha_txt)
                    is_gerenciadora = ("gerenciadora" in col_tipo or "gerenciadora" in col_u or "gerenciadora" in linha_txt) and ("não" not in col_tipo and "nao" not in col_tipo)

                    if is_uasg or is_gerenciadora:
                        if idx_r != -1 and idx_r < len(tds):
                            reg_t3 = converter_para_float(tds[idx_r])
                        if idx_e != -1 and idx_e < len(tds):
                            emp_t3 = converter_para_float(tds[idx_e])
                        if idx_s != -1 and idx_s < len(tds):
                            sal_t3 = converter_para_float(tds[idx_s])

                        if is_uasg:
                            break

                if reg_t3 is not None and emp_t3 is not None:
                    break

        # C) Tabela de Unidades do Item (Código, Unidade, Tipo da unidade, Qtd Registrada, Qtd Disponível para remanejamento/empenho)
        reg_t1 = None
        disp_t1 = None
        for tbl in leaf_tables:
            hdr_ths = []
            thead = tbl.find('thead')
            if thead:
                hdr_ths = [th.get_text(" ", strip=True).lower() for th in thead.find_all(['th', 'td'])]
            if not hdr_ths:
                first_tr = tbl.find('tr')
                if first_tr:
                    hdr_ths = [th.get_text(" ", strip=True).lower() for th in first_tr.find_all(['th', 'td'])]

            if any("remanejamento" in c or "disponível" in c or "disponiv" in c for c in hdr_ths):
                idx_r = -1
                idx_disp = -1
                for i_c, c_name in enumerate(hdr_ths):
                    if ("registrada" in c_name or "homologada" in c_name) and idx_r == -1:
                        idx_r = i_c
                    elif ("disponível" in c_name or "disponiv" in c_name or "remanejamento" in c_name) and idx_disp == -1:
                        idx_disp = i_c

                for tr in tbl.find_all('tr'):
                    tds = [td.get_text(" ", strip=True) for td in tr.find_all(['td', 'th'], recursive=False)]
                    if len(tds) < 3:
                        continue
                    if any("quantidade registrada" in td.lower() for td in tds):
                        continue

                    r_txt = " ".join(tds).lower()
                    if uasg_clean in r_txt or ("gerenciadora" in r_txt and "não" not in r_txt and "nao" not in r_txt):
                        if idx_r != -1 and idx_r < len(tds):
                            reg_t1 = converter_para_float(tds[idx_r])
                        if idx_disp != -1 and idx_disp < len(tds):
                            disp_t1 = converter_para_float(tds[idx_disp])
                        break

            if reg_t1 is not None:
                break

        # D) Consolidação Matemática das Quantidades: Saldo = Registrada - Empenhada
        # Prioridade máxima para os dados da tabela da Unidade e Empenhos do item da ARP
        if emp_t3 is not None and emp_t3 >= 0:
            final_emp = emp_t3
            final_reg = reg_t3 if (reg_t3 is not None and reg_t3 > 0) else (reg_t1 if (reg_t1 is not None and reg_t1 > 0) else final_emp)
            final_sal = sal_t3 if sal_t3 is not None else max(0.0, final_reg - final_emp)
        elif tem_ne_uasg and soma_empenhos_nes > 0:
            final_emp = soma_empenhos_nes
            final_reg = reg_t3 if (reg_t3 is not None and reg_t3 > 0) else (reg_t1 if (reg_t1 is not None and reg_t1 > 0) else final_emp)
            final_sal = max(0.0, final_reg - final_emp)
        elif reg_t1 is not None and disp_t1 is not None:
            final_reg = reg_t1
            final_sal = disp_t1
            final_emp = max(0.0, final_reg - final_sal)
        else:
            final_reg = 0.0
            final_emp = 0.0
            final_sal = 0.0

        # Garantia matemática estrita: Quantidade empenhada não pode ultrapassar a registrada
        if final_reg > 0 and final_emp > final_reg:
            final_emp = final_reg
        if final_reg > 0:
            final_sal = max(0.0, final_reg - final_emp)

        def fmt_qtd(val: float) -> str:
            if val == int(val):
                return str(int(val))
            return f"{val:g}"

        resultado["qtd_registrada"] = fmt_qtd(final_reg)
        resultado["qtd_empenhada"] = fmt_qtd(final_emp)
        resultado["saldo_empenho"] = fmt_qtd(final_sal)
        resultado["empenhos_resumo"] = " | ".join(empenhos_list) if empenhos_list else "Nenhum"
        resultado["empenhos_lista"] = empenhos_list

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

        total_it = len(itens_detectados)
        prog_bar = st.progress(0.0)
        status_txt = st.empty()

        status_txt.text(f"Mapeando Atas de Registro de Preços no Contratos.gov.br ({total_it} itens detectados)...")
        atas_pregao = buscar_atas_contratos(session, uasg, num_compra, ano_compra)

        def processar_item_individual(it: Dict) -> Dict:
            try:
                # Cada thread de scraping usa uma sessão HTTP dedicada com timeout ágil
                thread_sess = get_http_session()
                saldo_info = obter_saldo_item_contratos(thread_sess, uasg, num_compra, ano_compra, it["Item"], atas=atas_pregao)

                # Se o item é deserto/fracassado:
                if saldo_info.get("deserto", False):
                    qtd_registrada_final = "0"
                    qtd_empenhada_final = "0"
                    saldo_empenho_calc = "0"
                    fornecedor_display = "Deserto / Fracassado"
                    ata_vinculada = "-"
                    pdf_ata = ""
                else:
                    raw_reg = str(saldo_info.get("qtd_registrada", "0")).strip()
                    if raw_reg == "0" or raw_reg == uasg.strip() or any(c.isalpha() for c in raw_reg):
                        qtd_registrada_final = it.get("Qtd SIASG", "0")
                    else:
                        qtd_registrada_final = raw_reg

                    qtd_empenhada_final = str(saldo_info.get("qtd_empenhada", "0")).strip()
                    saldo_empenho_calc = str(saldo_info.get("saldo_empenho", "0")).strip()

                    # Aplicação rigorosa da fórmula oficial: Saldo = Registrada - Empenhada
                    f_reg = converter_para_float(qtd_registrada_final)
                    f_emp = converter_para_float(qtd_empenhada_final)
                    f_sal = converter_para_float(saldo_empenho_calc)

                    # Se a quantidade empenhada exceder a registrada (anomalia de scraping), limita ao teto registrado
                    if f_reg > 0 and f_emp > f_reg:
                        f_emp = f_reg
                        qtd_empenhada_final = f"{f_emp:g}"

                    # Se saldo oficial da unidade foi capturado e empenho direto estava 0
                    if f_sal > 0 and f_emp == 0 and f_reg > f_sal:
                        f_emp = max(0.0, f_reg - f_sal)
                        qtd_empenhada_final = f"{f_emp:g}"
                    else:
                        f_sal = max(0.0, f_reg - f_emp)
                        saldo_empenho_calc = f"{f_sal:g}"

                    # Resolução do Fornecedor e CNPJ
                    cnpj_puro = str(saldo_info.get("cnpj_puro", "")).strip()
                    forn_puro = str(saldo_info.get("fornecedor_puro", "")).strip()

                    if forn_puro and cnpj_puro and forn_puro != cnpj_puro:
                        fornecedor_display = f"{forn_puro} ({cnpj_puro})"
                    elif forn_puro and not cnpj_puro:
                        fornecedor_display = forn_puro
                    elif cnpj_puro and not forn_puro:
                        fornecedor_display = cnpj_puro
                    else:
                        fornecedor_display = saldo_info.get("fornecedor") or "Deserto / Fracassado"

                    ata_vinculada = saldo_info.get("numero_ata") or "Não identificada"
                    pdf_ata = saldo_info.get("pdf_ata", "")

                desc_final = saldo_info.get("descricao_detalhada_ata") or it.get("Descrição", "")
                desc_final = limpar_descricao_ata(desc_final)

                return {
                    "Item": it["Item"],
                    "Tipo": it.get("Tipo", "Material"),
                    "Descrição": desc_final,
                    "Descrição Curta SIASG": limpar_descricao_ata(it.get("Descrição", "")),
                    "Unidade": it.get("Unidade", ""),
                    "Qtd Registrada": qtd_registrada_final,
                    "Qtd Empenhada": qtd_empenhada_final,
                    "Saldo p/ Empenho": saldo_empenho_calc,
                    "Ata Vinculada": ata_vinculada,
                    "Fornecedor": fornecedor_display,
                    "Fornecedor Puro": saldo_info.get("fornecedor_puro", ""),
                    "CNPJ Puro": saldo_info.get("cnpj_puro", ""),
                    "Valor Unitario Sugerido": saldo_info.get("valor_unitario_sugerido", 0.0),
                    "PDF da Ata": pdf_ata,
                    "Empenhos": saldo_info.get("empenhos_resumo", "Nenhum"),
                    "empenhos_lista": saldo_info.get("empenhos_lista", [])
                }
            except Exception:
                # Fallback resiliente: falhas pontuais de rede nunca derrubam a lista geral
                return {
                    "Item": it["Item"],
                    "Tipo": it.get("Tipo", "Material"),
                    "Descrição": limpar_descricao_ata(it.get("Descrição", "")),
                    "Descrição Curta SIASG": limpar_descricao_ata(it.get("Descrição", "")),
                    "Unidade": it.get("Unidade", ""),
                    "Qtd Registrada": it.get("Qtd SIASG", "0"),
                    "Qtd Empenhada": "0",
                    "Saldo p/ Empenho": it.get("Qtd SIASG", "0"),
                    "Ata Vinculada": "Não identificada",
                    "Fornecedor": "Em apuração",
                    "Fornecedor Puro": "",
                    "CNPJ Puro": "",
                    "Valor Unitario Sugerido": 0.0,
                    "PDF da Ata": "",
                    "Empenhos": "Nenhum",
                    "empenhos_lista": []
                }

        # Execução concorrente com ThreadPoolExecutor: 60 itens passam de ~90s para ~12s
        max_workers = min(6, total_it)
        resultados_map = {}
        concluidos = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(processar_item_individual, it): it["Item"] for it in itens_detectados}
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    res_item = future.result()
                    if res_item:
                        resultados_map[res_item["Item"]] = res_item
                except Exception:
                    pass

                concluidos += 1
                progresso = min(1.0, concluidos / max(1, total_it))
                prog_bar.progress(progresso)
                status_txt.text(f"Consultando Contratos.gov.br: {concluidos} de {total_it} itens apurados...")

        # Reordenar mantendo a ordem numérica original dos itens
        dados_finais = [resultados_map[it["Item"]] for it in itens_detectados if it["Item"] in resultados_map]

        status_txt.empty()
        prog_bar.empty()
        return dados_finais

    except Exception as e:
        st.error(f"Erro ao obter itens do pregão: {str(e)}")
        if 'resultados_map' in locals() and resultados_map:
            return [resultados_map[it["Item"]] for it in itens_detectados if it["Item"] in resultados_map]
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
        cab_it = ["Item", "Sub Item", "Material", "Qtd", "Valor Unitário", "Valor Total", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"]
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
            sub_val = str(it.get("Subitem", "") or "").strip()
            if not sub_val:
                sub_val = determinar_subitem(dados_nc.get("nd", ""), it.get("Nome", ""))
            
            ws_itens.cell(row=r_idx, column=1, value=it.get("Item")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=2, value=sub_val).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=3, value=it.get("Nome"))
            ws_itens.cell(row=r_idx, column=4, value=q).alignment = Alignment(horizontal="center")
            
            c_u = ws_itens.cell(row=r_idx, column=5, value=vu)
            c_u.number_format = "R$ #,##0.00"
            c_u.alignment = Alignment(horizontal="right")
            
            c_t = ws_itens.cell(row=r_idx, column=6, value=vt)
            c_t.number_format = "R$ #,##0.00"
            c_t.alignment = Alignment(horizontal="right")
            
            ws_itens.cell(row=r_idx, column=7, value=it.get("Situação")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=8, value=it.get("Fornecedor"))
            ws_itens.cell(row=r_idx, column=9, value=formatar_cnpj(it.get("CNPJ", ""))).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=10, value=it.get("Pregão")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=11, value=it.get("Ata")).alignment = Alignment(horizontal="center")
            ws_itens.cell(row=r_idx, column=12, value=it.get("UASG")).alignment = Alignment(horizontal="center")
            
            for col_idx in range(1, 13):
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
        cab_todos = ["NC de Origem", "PI", "ND", "Item", "Sub Item", "Nomenclatura", "Qtd", "Valor Unitário", "Valor Total", "Situação", "Fornecedor", "CNPJ", "Pregão"]
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
            nd_orig = d_nc.get("nd", "")
            for it in d_nc.get("itens", []):
                q = int(it.get("Qtd", 0))
                vu = float(it.get("Valor Unitário", 0.0))
                vt = q * vu
                sub_val = str(it.get("Subitem", "") or "").strip()
                if not sub_val:
                    sub_val = determinar_subitem(nd_orig, it.get("Nome", ""))
                
                ws_it_ano.cell(row=row_it, column=1, value=nc).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=2, value=d_nc.get("pi", "")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=3, value=nd_orig).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=4, value=it.get("Item")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=5, value=sub_val).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=6, value=it.get("Nome"))
                ws_it_ano.cell(row=row_it, column=7, value=q).alignment = Alignment(horizontal="center")
                
                c_u = ws_it_ano.cell(row=row_it, column=8, value=vu)
                c_u.number_format = "R$ #,##0.00"
                c_u.alignment = Alignment(horizontal="right")
                
                c_t = ws_it_ano.cell(row=row_it, column=9, value=vt)
                c_t.number_format = "R$ #,##0.00"
                c_t.alignment = Alignment(horizontal="right")
                
                ws_it_ano.cell(row=row_it, column=10, value=it.get("Situação")).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=11, value=it.get("Fornecedor"))
                ws_it_ano.cell(row=row_it, column=12, value=formatar_cnpj(it.get("CNPJ", ""))).alignment = Alignment(horizontal="center")
                ws_it_ano.cell(row=row_it, column=13, value=it.get("Pregão")).alignment = Alignment(horizontal="center")
                
                for col_idx in range(1, 14):
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
    st.markdown("""
    <div style="text-align: center; margin-top: 15px; margin-bottom: 30px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 16px; background: linear-gradient(135deg, #1e3a29 0%, #2d6a4f 100%); box-shadow: 0 4px 12px rgba(27, 67, 50, 0.25); font-size: 32px; margin-bottom: 12px;">🇧🇷</div>
        <div style="font-size: 11px; font-weight: 800; letter-spacing: 2px; color: #64748b; text-transform: uppercase;">Exército Brasileiro • Comando Militar</div>
        <h1 style="font-size: 28px; font-weight: 800; color: #0f172a; margin-top: 6px; margin-bottom: 6px; letter-spacing: -0.5px;">Sistema Integrado de Gestão Orçamentária & Pregões</h1>
        <p style="color: #64748b; font-size: 15px; margin: 0; max-width: 600px; margin-left: auto; margin-right: auto;">Controle de Recursos, Notas de Crédito, Aquisições e Atas de Registro de Preços</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_login, col_divisor, col_cadastro = st.columns([4.2, 0.6, 4.2])
    
    with col_login:
        st.markdown("""
        <div style="margin-bottom: 12px;">
            <h3 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;">🔑 Acesso ao Sistema</h3>
            <p style="font-size: 13px; color: #64748b; margin: 2px 0 0 0;">Informe suas credenciais autorizadas para ingressar</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("form_login"):
            usuario_login = st.text_input("Usuário de Acesso:").strip().lower()
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
        st.markdown("""
        <div style="margin-bottom: 12px;">
            <h3 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;">🛡️ Cadastrar Conta Matriz da OM</h3>
            <p style="font-size: 13px; color: #64748b; margin: 2px 0 0 0;">Apenas para o Fiscal Administrativo da Organização Militar</p>
        </div>
        """, unsafe_allow_html=True)
        st.info("⚠️ **Acesso Restrito:** Apenas o **Fiscal Administrativo** pode criar a primeira conta da OM. Contas de **Chefe** e **Operador** devem ser criadas pelo Fiscal internamente.")
        with st.form("form_cadastro"):
            novo_user = st.text_input("Escolha um nome de Usuário:").strip().lower()
            nova_senha = st.text_input("Crie uma Senha:", type="password")
            novo_nome = st.text_input("Seu Nome/Posto (Ex: Cap Silva):")
            nova_om = st.text_input("Sua OM (Ex: 1º Btl):").strip().upper()
            
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
        "Criado e Desenvolvido por:<br><b>2º Sgt Com Equipe Técnica</b><br><br>"
        "<i>Este sistema está em constante evolução. Para suporte ou envio de sugestões, entre em contato: <a href='mailto:suporte@eb.mil.br'>suporte@eb.mil.br</a></i>"
        "</div>", 
        unsafe_allow_html=True
    )
    st.stop() 

# =====================================================================
# 7. CARREGAMENTO DOS DADOS DO MILITAR LOGADO
# =====================================================================
usuario_atual = st.session_state.usuario_logado

resp_perfil = supabase.table("usuarios").select("*").eq("id", usuario_atual).execute()
if not resp_perfil.data:
    st.session_state.usuario_logado = None
    st.rerun()
    st.stop()
    perfil = {}
else:
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
st.sidebar.info(f"**Militar:** {perfil.get('nome')}\n\n**OM:** {om_user}\n\n**Seção Primária:** {secao_user}")

if tipo_perfil == "Fiscal":
    st.sidebar.warning("🛡️ **Perfil: FISCAL (Somente Leitura / Auditoria Global)**")
elif tipo_perfil == "Chefe":
    st.sidebar.success(f"👑 **Perfil: CHEFE**\n\n**Seção:** {secao_user}")
else:
    st.sidebar.info(f"👤 **Perfil: OPERADOR**\n\n**Seção:** {secao_user}")

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
st.sidebar.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Criado e Desenvolvido por:<br><b>2º Sgt Com Thales Winkler</b><br><br>"
    "<i>Sistema em constante evolução. Sugestões e suporte:<br>"
    "<a href='mailto:winkler.thales@eb.mil.br'>winkler.thales@eb.mil.br</a></i>"
    "</div>", 
    unsafe_allow_html=True
)

# =====================================================================
# 9. FILTROS SUPERIORES NO TOPO DA PÁGINA (MAIS ESPAÇO ÚTIL)
# =====================================================================
OPCAO_TODAS_SECOES = "🌟 TODAS AS SEÇÕES DA OM"

# Recupera as seções cadastradas da OM
resp_secoes = supabase.table("usuarios").select("secao").eq("om", om_user).execute()
secoes_da_om = sorted(list(set([r["secao"] for r in resp_secoes.data if r.get("secao")])))
if not secoes_da_om:
    secoes_da_om = [secao_user]

# Linha de filtros no topo acima do conteúdo
col_topo_ano, col_topo_sec = st.columns([1.5, 3.5])

with col_topo_sec:
    if tipo_perfil == "Fiscal":
        opcoes_secao = [OPCAO_TODAS_SECOES] + secoes_da_om
        idx_sec_ini = 0
        if "filtro_secao_topo" in st.session_state and st.session_state["filtro_secao_topo"] in opcoes_secao:
            idx_sec_ini = opcoes_secao.index(st.session_state["filtro_secao_topo"])
        secao_ativa = st.selectbox(
            "🏢 Seção da OM para Análise / Operação:",
            opcoes_secao,
            index=idx_sec_ini,
            key="filtro_secao_topo",
            help="Como Fiscal, selecione uma seção específica ou visualize toda a OM unificada."
        )
    else:
        secao_ativa = secao_user
        st.text_input("🏢 Seção Ativa:", value=f"{secao_user} (Sua Seção)", disabled=True)

# Definição e carregamento do cofre de dados conforme Seção Ativa
if tipo_perfil == "Fiscal" and secao_ativa == OPCAO_TODAS_SECOES:
    id_banco = f"{om_user}_TODAS"
    def carregar_dados_banco():
        resp = supabase.table("dados").select("*").like("id", f"{om_user}_%").execute()
        banco_unificado = {}
        for linha in resp.data:
            ncs_sec = linha.get("ncs", {})
            if isinstance(ncs_sec, dict):
                for nc, val in ncs_sec.items():
                    if nc != "CONFIG_REQUISICAO":
                        banco_unificado[nc] = val
                    else:
                        if "CONFIG_REQUISICAO" not in banco_unificado:
                            banco_unificado["CONFIG_REQUISICAO"] = val
        return banco_unificado
else:
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
    if tipo_perfil == "Fiscal" and secao_ativa == OPCAO_TODAS_SECOES:
        return
    supabase.table("dados").update({"ncs": dados_para_salvar}).eq("id", id_banco).execute()

# Abertura inicial garantida no ano corrente
ano_atual_sistema = str(datetime.datetime.now().year)
anos_disponiveis = set(extrair_ano(nc) for nc in banco_dados.keys() if nc != "CONFIG_REQUISICAO" and extrair_ano(nc))
anos_disponiveis.add(ano_atual_sistema)
lista_anos = sorted(list(anos_disponiveis), reverse=True)
idx_ano_padrao = lista_anos.index(ano_atual_sistema) if ano_atual_sistema in lista_anos else 0

with col_topo_ano:
    idx_ano_sel = idx_ano_padrao
    if "filtro_ano_topo" in st.session_state and st.session_state["filtro_ano_topo"] in lista_anos:
        idx_ano_sel = lista_anos.index(st.session_state["filtro_ano_topo"])
    ano_selecionado = st.selectbox("📅 Exercício (Ano):", lista_anos, index=idx_ano_sel, key="filtro_ano_topo")

ncs_do_ano = [nc for nc in banco_dados.keys() if nc != "CONFIG_REQUISICAO" and extrair_ano(nc) == ano_selecionado]

# Título Principal e Banner
st.markdown(f"""
<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 16px 22px; border-radius: 12px; color: white; display: flex; align-items: center; justify-content: space-between; margin-top: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); flex-wrap: wrap; gap: 12px;">
  <div style="display: flex; align-items: center; gap: 14px;">
    <div style="font-size: 28px;">🇧🇷</div>
    <div>
      <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: #94a3b8; text-transform: uppercase;">Exército Brasileiro • Gestão Orçamentária</div>
      <div style="font-size: 20px; font-weight: 800; color: #f8fafc; letter-spacing: -0.3px;">Controle de Recursos, NCs & Pregões</div>
    </div>
  </div>
  <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
    <span style="background: rgba(180, 83, 9, 0.5); color: #fef3c7; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid rgba(245, 158, 11, 0.3);">ANO: {ano_selecionado}</span>
    <span style="background: rgba(30, 58, 138, 0.5); color: #bfdbfe; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid rgba(59, 130, 246, 0.3);">OM: {om_user}</span>
    <span style="background: rgba(20, 83, 45, 0.5); color: #bbf7d0; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid rgba(34, 197, 94, 0.3);">SEÇÃO: {secao_ativa}</span>
    <span style="background: rgba(51, 65, 85, 0.8); color: #e2e8f0; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid rgba(148, 163, 184, 0.2);">{tipo_perfil.upper()}</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_cadastro, tab_visualizacao, tab_visao_global, tab_consulta_pregoes, tab_acessos = st.tabs([
    "📝 Cadastrar e Lançar Compras",
    "📊 Controle Individual por NC",
    "📈 Visão Global do Ano",
    "🔎 Consultar Pregões & Importar para NC",
    "👥 Gerenciar Acessos"
])

# =====================================================================
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
                nd_nc_selecionada = banco_dados[nc_selecionada_cad].get("nd", "")
                opcoes_sub_cad, idx_sub_cad, mapa_sub_cad = montar_opcoes_subitem(nd_nc_selecionada, nome_resumido)
                sub_sel_cad = st.selectbox(
                    "Sub Item (Correspondências na Função da ND):",
                    opcoes_sub_cad,
                    index=idx_sub_cad,
                    help=f"Pesquisa realizada na FUNÇÃO oficial do SIAFI da ND {nd_nc_selecionada}. Selecione entre as correspondências identificadas ou escolha outro subitem.",
                    key="cad_item_subitem_select"
                )
                if sub_sel_cad == "✏️ Digitar outro código manualmente...":
                    subitem_digitado = st.text_input("Digite o Subitem (2 dígitos):", max_chars=2, key="item_subitem_manual").strip()
                else:
                    subitem_digitado = mapa_sub_cad.get(sub_sel_cad, extrair_codigo_subitem(sub_sel_cad))
                
                funcao_cad_txt = obter_funcao_subitem(nd_nc_selecionada, subitem_digitado)
                if funcao_cad_txt:
                    st.caption(f"📖 **Função do Subitem {subitem_digitado}:** {funcao_cad_txt}")
                valor_unitario = st.number_input("Valor Unitário (R$):", min_value=0.0, step=0.01, key="item_valor")
                quantidade = st.number_input("Quantidade:", min_value=0, step=1, key="item_qtd")
            with col_it2:
                nr_uasg = st.text_input("Nº da UASG:", "160001", key="item_uasg").strip()
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
                    sub_final = subitem_digitado if subitem_digitado else determinar_subitem(nd_nc_selecionada, nome_resumido)
                    novo_item = {
                        "Item": int(nr_item), "Subitem": sub_final, "Nome": nome_resumido, "Valor Unitário": float(valor_unitario),
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
                            sub_it = it.get("Subitem", "") or determinar_subitem(nd_nc, it.get("Nome", ""))
                            resultados_busca.append({
                                "NC Vinculada": nc_chave,
                                "PI / ND": f"{pi_nc} / {nd_nc}",
                                "Item": it.get("Item"),
                                "Sub Item": sub_it,
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
                    
                    st.markdown("##### 🚀 Acesso Direto à Nota de Crédito:")
                    for idx_b, res_it in enumerate(resultados_busca[:20]):
                        c_info, c_btn = st.columns([3.5, 1.5])
                        with c_info:
                            st.markdown(f"**Item {res_it['Item']}:** {res_it['Material']} — *Fornecedor:* {res_it['Fornecedor']} — *Status:* `{res_it['Situação']}`")
                        with c_btn:
                            nc_alvo = res_it['NC Vinculada']
                            if st.button(f"👉 Ir para NC {nc_alvo}", key=f"btn_ir_nc_res_{idx_b}_{nc_alvo}", use_container_width=True):
                                st.session_state["vis_item_select_nc"] = nc_alvo
                                st.session_state["filtro_pi_tab2"] = "TODOS OS PIs"
                                st.rerun()
                else:
                    st.warning("Nenhum material encontrado com os termos digitados.")

        pis_disponiveis = list(set([banco_dados[nc].get("pi", "Não informado") for nc in ncs_do_ano if isinstance(banco_dados[nc], dict) and banco_dados[nc].get("pi", "Não informado").strip()]))
        opcoes_filtro_pi = ["TODOS OS PIs"] + sorted(pis_disponiveis)
        
        col_filtro1, col_filtro_sit, col_filtro2 = st.columns([1.5, 1.8, 2.0])
        with col_filtro1:
            filtro_pi = st.selectbox("📌 Filtrar por PI:", opcoes_filtro_pi, key="filtro_pi_tab2")
        
        with col_filtro_sit:
            filtro_situacao_tab2 = st.multiselect(
                "🚦 Filtrar Itens por Situação:",
                ["Planejamento", "Aguardando entrega", "Recebido"],
                default=["Planejamento", "Aguardando entrega", "Recebido"],
                help="Desmarque 'Recebido' para ocultar itens já recebidos ou fornecedores já finalizados.",
                key="filtro_sit_tab2"
            )
        
        if not filtro_situacao_tab2:
            ncs_filtradas = []
            msg_aviso_filtro = "⚠️ Nenhuma Situação selecionada no filtro acima. Selecione ao menos uma opção (ex: 'Planejamento', 'Aguardando entrega' ou 'Recebido') para visualizar as NCs."
        else:
            ncs_candidatas = ncs_do_ano if filtro_pi == "TODOS OS PIs" else [nc for nc in ncs_do_ano if banco_dados[nc].get("pi", "Não informado") == filtro_pi]
            ncs_filtradas = []
            for nc in ncs_candidatas:
                itens_nc = banco_dados[nc].get("itens", [])
                if not itens_nc:
                    if "Planejamento" in filtro_situacao_tab2:
                        ncs_filtradas.append(nc)
                else:
                    tem_item = any(
                        (str(it.get("Situação", "Planejamento") or "Planejamento").strip() in filtro_situacao_tab2)
                        for it in itens_nc
                    )
                    if tem_item:
                        ncs_filtradas.append(nc)
            msg_aviso_filtro = "Nenhuma NC encontrada para os filtros selecionados (PI e Situação)."
            
        with col_filtro2:
            if ncs_filtradas:
                if "vis_item_select_nc" in st.session_state and st.session_state["vis_item_select_nc"] not in ncs_filtradas:
                    del st.session_state["vis_item_select_nc"]
                nc_selecionada_vis = st.selectbox("Selecione a NC para Gerenciamento e Análise:", ncs_filtradas, key="vis_item_select_nc")
            else:
                nc_selecionada_vis = None
                if "vis_item_select_nc" in st.session_state:
                    del st.session_state["vis_item_select_nc"]
                st.selectbox("Selecione a NC para Gerenciamento e Análise:", ["Nenhuma NC com estes filtros"], disabled=True, key="vis_item_select_nc_disabled")
            
        if not nc_selecionada_vis:
            st.warning(msg_aviso_filtro)
        else:
            dados_nc = banco_dados.get(nc_selecionada_vis, {})
            total_recebido = dados_nc.get("valor_recebido", 0.0)
            nd_vinculada = dados_nc.get("nd", "Não informada")
            pi_vinculado = dados_nc.get("pi", "Não informado")
            
            st.markdown(f"**PI:** `{pi_vinculado}` &nbsp;&nbsp;|&nbsp;&nbsp; **ND:** `{nd_vinculada}`")
            
            itens_nc_lista = dados_nc.get("itens", [])
            if itens_nc_lista:
                precisa_salvar_subitens = False
                for idx_i, it in enumerate(itens_nc_lista):
                    if not it.get("_uid"):
                        it["_uid"] = f"it_{nc_selecionada_vis}_{idx_i}_{uuid.uuid4().hex[:6]}"
                        precisa_salvar_subitens = True
                    try:
                        v_u = float(pd.to_numeric(it.get("Valor Unitário", 0.0), errors="coerce") or 0.0)
                    except Exception:
                        v_u = 0.0
                    try:
                        q_u = int(pd.to_numeric(it.get("Qtd", 0), errors="coerce") or 0)
                    except Exception:
                        q_u = 0
                    it["Total"] = v_u * q_u
                    it["CNPJ"] = formatar_cnpj(it.get("CNPJ", ""))
                    if not str(it.get("Subitem", "") or "").strip():
                        it["Subitem"] = determinar_subitem(nd_vinculada, it.get("Nome", ""))
                        precisa_salvar_subitens = True
                
                if precisa_salvar_subitens and tipo_perfil != "Fiscal":
                    salvar_dados(banco_dados)
                    st.session_state.banco = banco_dados
                
                df_base_mestre = pd.DataFrame(itens_nc_lista)
            else:
                df_base_mestre = pd.DataFrame(columns=[
                    "Item", "Subitem", "Nome", "Qtd", "Valor Unitário", "Total", 
                    "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"
                ])
                
            if not df_base_mestre.empty:
                if "Situação" not in df_base_mestre.columns:
                    df_base_mestre["Situação"] = "Planejamento"
                else:
                    df_base_mestre["Situação"] = df_base_mestre["Situação"].fillna("Planejamento").astype(str).str.strip()
                    df_base_mestre["Situação"] = df_base_mestre["Situação"].apply(
                        lambda s: s if s in ["Planejamento", "Aguardando entrega", "Recebido"] else "Planejamento"
                    )
                if "Subitem" not in df_base_mestre.columns:
                    df_base_mestre["Subitem"] = [determinar_subitem(nd_vinculada, n) for n in df_base_mestre["Nome"]]
                else:
                    df_base_mestre["Subitem"] = df_base_mestre.apply(
                        lambda r: str(r["Subitem"]).strip() if str(r.get("Subitem", "") or "").strip() else determinar_subitem(nd_vinculada, r.get("Nome", "")),
                        axis=1
                    )
                df_base_mestre["Valor Unitário"] = pd.to_numeric(df_base_mestre["Valor Unitário"], errors="coerce").fillna(0.0)
                df_base_mestre["Qtd"] = pd.to_numeric(df_base_mestre["Qtd"], errors="coerce").fillna(0).astype(int)
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
            st.subheader("📋 Controle de Itens e Requisições por Fornecedor")

            with st.expander("🎯 Conferir ou Alterar Sub Item de um Material da NC (Classificação Inteligente com IA)", expanded=False):
                itens_nc_ajuste = banco_dados[nc_selecionada_vis].get("itens", [])
                if itens_nc_ajuste:
                    opcoes_itens_nc = [f"Item {it.get('Item', 1)} - {it.get('Nome', '')[:50]} (Subitem Atual: {it.get('Subitem', 'S/ Subitem')})" for it in itens_nc_ajuste]
                    it_selecionado_para_ajuste = st.selectbox("Selecione o Item da NC para Consultar / Ajustar:", opcoes_itens_nc, key=f"sel_it_ajuste_{nc_selecionada_vis}")
                    
                    idx_it_ajuste = opcoes_itens_nc.index(it_selecionado_para_ajuste)
                    item_obj_ajuste = itens_nc_ajuste[idx_it_ajuste]
                    nome_item_alvo = item_obj_ajuste.get('Nome', '')
                    
                    # Painel de IA (Gemini)
                    chave_ia_sessao = f"ia_sub_{nc_selecionada_vis}_{idx_it_ajuste}"
                    sugestao_ia_atual = st.session_state.get(chave_ia_sessao) or _cache_classificacao_ia.get(f"{nd_vinculada}_{nome_item_alvo.strip().lower()}")
                    
                    c_ia1, c_ia2 = st.columns([1, 2])
                    with c_ia1:
                        if st.button("✨ Sugerir com IA (Gemini)", key=f"btn_ia_sub_{nc_selecionada_vis}_{idx_it_ajuste}", use_container_width=True, help="Usa a inteligência artificial Gemini para analisar a finalidade contábil do item e sugerir o subitem exato do SIAFI"):
                            with st.spinner("Classificando com Inteligência Artificial (Gemini)..."):
                                res_ia = classificar_subitem_com_ia(nd_vinculada, nome_item_alvo)
                                if res_ia:
                                    st.session_state[chave_ia_sessao] = res_ia
                                    st.toast(f"IA recomendou o Subitem {res_ia['subitem']}!")
                                    st.rerun()
                                else:
                                    st.warning("Não foi possível conectar à IA no momento. Usando correspondências por regras.")
                    
                    with c_ia2:
                        if sugestao_ia_atual:
                            st.info(f"🤖 **Sugestão da IA (Gemini):** Subitem **{sugestao_ia_atual['subitem']} - {sugestao_ia_atual['nome']}**\n\n💡 *{sugestao_ia_atual.get('justificativa', '')}*")
                    
                    c_aj1, c_aj2 = st.columns([3, 1])
                    with c_aj1:
                        opcoes_sub_aj, idx_sub_aj, mapa_sub_aj = montar_opcoes_subitem(
                            nd_vinculada, 
                            nome_item_alvo, 
                            item_obj_ajuste.get('Subitem', ''),
                            sugestao_ia=sugestao_ia_atual
                        )
                        sub_sel_aj = st.selectbox(
                            "Sub Item Correspondente na Função da ND:",
                            opcoes_sub_aj,
                            index=idx_sub_aj,
                            key=f"sel_sub_aj_{nc_selecionada_vis}_{idx_it_ajuste}"
                        )
                        if sub_sel_aj == "✏️ Digitar outro código manualmente...":
                            cod_sub_novo = st.text_input("Código do Subitem (2 dígitos):", max_chars=2, key=f"man_sub_aj_{nc_selecionada_vis}_{idx_it_ajuste}").strip()
                        else:
                            cod_sub_novo = mapa_sub_aj.get(sub_sel_aj, extrair_codigo_subitem(sub_sel_aj))
                        
                        funcao_aj_txt = obter_funcao_subitem(nd_vinculada, cod_sub_novo)
                        if funcao_aj_txt:
                            st.caption(f"📖 **Função do Subitem {cod_sub_novo}:** {funcao_aj_txt}")
                    
                    with c_aj2:
                        st.write("")
                        st.write("")
                        if st.button("💾 Aplicar Subitem", type="primary", key=f"btn_salvar_sub_aj_{nc_selecionada_vis}_{idx_it_ajuste}", use_container_width=True):
                            if tipo_perfil == "Fiscal":
                                st.error("Fiscal não tem permissão para alterar itens.")
                            else:
                                item_obj_ajuste["Subitem"] = cod_sub_novo
                                salvar_dados(banco_dados)
                                st.session_state.banco = banco_dados
                                st.toast(f"Subitem do Item {item_obj_ajuste.get('Item')} atualizado para {cod_sub_novo}!")
                                st.rerun()
                else:
                    st.info("Nenhum item cadastrado nesta NC ainda.")

            if itens_nc_lista and tipo_perfil != "Fiscal":
                with st.expander("🛠️ Ações Rápidas: Excluir ou Mover Item desta NC", expanded=False):
                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        st.markdown("##### 🗑️ Excluir Item desta NC")
                        opcoes_itens_del = {
                            f"Item {it.get('Item', 1)} - {it.get('Nome', '')[:35]} ({it.get('Fornecedor', 'N/I')}) | R$ {float(it.get('Total', 0.0)):,.2f}": it.get('_uid')
                            for it in itens_nc_lista
                        }
                        item_para_excluir_label = st.selectbox(
                            "Selecione o item que deseja excluir:",
                            list(opcoes_itens_del.keys()),
                            key=f"sel_item_del_{nc_selecionada_vis}"
                        )
                        uid_para_excluir = opcoes_itens_del.get(item_para_excluir_label)
                        confirma_del_item = st.checkbox("Confirmo a exclusão definitiva deste item", key=f"chk_del_item_{uid_para_excluir}")
                        if st.button("🗑️ Excluir Item Permanentemente", type="secondary", key=f"btn_del_item_{uid_para_excluir}"):
                            if not confirma_del_item:
                                st.error("Marque a caixa de confirmação para autorizar a exclusão.")
                            else:
                                banco_dados[nc_selecionada_vis]["itens"] = [
                                    it for it in banco_dados[nc_selecionada_vis]["itens"]
                                    if it.get("_uid") != uid_para_excluir
                                ]
                                salvar_dados(banco_dados)
                                st.session_state.banco = banco_dados
                                st.success("Item excluído com sucesso da Nota de Crédito!")
                                st.toast("Item excluído!")
                                st.rerun()

                    with c_act2:
                        st.markdown("##### 🔁 Mover Item para Outra NC")
                        outras_ncs = [k for k in banco_dados.keys() if k != "CONFIG_REQUISICAO" and k != nc_selecionada_vis and extrair_ano(k) == ano_selecionado]
                        if not outras_ncs:
                            st.caption("ℹ️ Não há outras NCs cadastradas neste ano para onde mover itens.")
                        else:
                            opcoes_itens_mover = {
                                f"Item {it.get('Item', 1)} - {it.get('Nome', '')[:35]} ({it.get('Fornecedor', 'N/I')}) | R$ {float(it.get('Total', 0.0)):,.2f}": it
                                for it in itens_nc_lista
                            }
                            item_para_mover_label = st.selectbox(
                                "Selecione o item para transferir:",
                                list(opcoes_itens_mover.keys()),
                                key=f"sel_item_mover_{nc_selecionada_vis}"
                            )
                            nc_destino_mover = st.selectbox(
                                "Selecione a NC de Destino:",
                                outras_ncs,
                                key=f"sel_nc_dest_mover_{nc_selecionada_vis}"
                            )
                            if st.button("🔁 Transferir Item para a NC Selecionada", type="primary", key=f"btn_mover_item_{nc_selecionada_vis}"):
                                item_obj = opcoes_itens_mover[item_para_mover_label]
                                banco_dados[nc_selecionada_vis]["itens"] = [
                                    it for it in banco_dados[nc_selecionada_vis]["itens"]
                                    if it.get("_uid") != item_obj.get("_uid")
                                ]
                                if "itens" not in banco_dados[nc_destino_mover]:
                                    banco_dados[nc_destino_mover]["itens"] = []
                                nd_nova = banco_dados[nc_destino_mover].get("nd", "")
                                item_obj_copia = dict(item_obj)
                                if nd_nova:
                                    item_obj_copia["Subitem"] = determinar_subitem(nd_nova, item_obj_copia.get("Nome", ""))
                                banco_dados[nc_destino_mover]["itens"].append(item_obj_copia)
                                
                                salvar_dados(banco_dados)
                                st.session_state.banco = banco_dados
                                st.success(f"Item transferido com sucesso para **{nc_destino_mover}**!")
                                st.toast(f"Item transferido para {nc_destino_mover}!")
                                st.rerun()

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
                        cfg_ind = st.text_input("Indicativo do DIEx (Ex: SALC/1ºBtl):", value=config_req.get("indicativo_diex", f"SEÇÃO/{om_user}"))
                        cfg_remetente = st.text_input("Remetente (Campo 'Do:'):", value=config_req.get("remetente_do", "Chefe da Seção"))
                        cfg_cidade = st.text_input("Cidade/UF da OM (Ex: Brasília-DF):", value=config_req.get("cidade_om", "Brasília-DF"))
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
                # Aplicação do filtro de Situação dos Itens na Tab 2
                if filtro_situacao_tab2:
                    df_base_filtrada = df_base_mestre[df_base_mestre["Situação"].isin(filtro_situacao_tab2)].copy()
                else:
                    df_base_filtrada = df_base_mestre.iloc[0:0].copy()
                
                lista_fornecedores = sorted(df_base_filtrada["Fornecedor"].unique()) if not df_base_filtrada.empty else []
                houve_alteracao = False
                df_atualizado_acumulado = []
                
                if not lista_fornecedores and not df_base_mestre.empty:
                    st.info("ℹ️ Nenhum item para exibir nesta NC com o filtro de Situação selecionado (por exemplo, todos os itens já constam como 'Recebido'). Altere as opções no filtro de Situação acima para visualizá-los.")
                
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
                                
                    df_forn_atual = df_base_filtrada[df_base_filtrada["Fornecedor"] == forn].sort_values(by="Item").reset_index(drop=True)
                    for col_str in ["Nome", "Subitem", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"]:
                        if col_str in df_forn_atual.columns:
                            df_forn_atual[col_str] = df_forn_atual[col_str].fillna("").astype(str)
                    if "Situação" in df_forn_atual.columns:
                        df_forn_atual["Situação"] = df_forn_atual["Situação"].fillna("Planejamento").astype(str).str.strip()
                        df_forn_atual["Situação"] = df_forn_atual["Situação"].apply(
                            lambda s: s if s in ["Planejamento", "Aguardando entrega", "Recebido"] else "Planejamento"
                        )
                    
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
                            
                            subitem_val = str(row.get('Subitem', '') or '').strip()
                            if not subitem_val:
                                subitem_val = determinar_subitem(nd_vinculada, row.get('Nome', ''))
                            
                            linhas_tabela_html += f"""
                            <tr>
                                <td>{row['Item']}</td>
                                <td>{subitem_val}</td>
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
                                    <td>Item</td><td>Sub Item</td><td>Nomenclatura</td><td>Qtd</td><td>Valor Unitário</td><td>Valor Total</td>
                                </tr>
                                {linhas_tabela_html}
                                <tr style="font-weight: bold;">
                                    <td colspan="5">TOTAL</td><td>{total_geral_str}</td>
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
                        "Subitem": st.column_config.TextColumn("Sub Item", help="Subitem da despesa (2 últimos dígitos da ND)", max_chars=10),
                        "Nome": st.column_config.TextColumn("Nome", required=True),
                        "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, step=1, required=True),
                        "Valor Unitário": st.column_config.NumberColumn("Valor Unitário", min_value=0.0, step=0.01, format="R$ %.2f", required=True),
                        "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                        "UASG": st.column_config.TextColumn("UASG"),
                        "Pregão": st.column_config.TextColumn("Pregão"),
                        "Ata": st.column_config.TextColumn("Ata"),
                        "Fornecedor": st.column_config.TextColumn("Fornecedor"),
                        "CNPJ": st.column_config.TextColumn("CNPJ"),
                        "Situação": st.column_config.SelectboxColumn(
                            "Situação",
                            options=["Planejamento", "Aguardando entrega", "Recebido"],
                            required=True,
                            help="Clique para selecionar a Situação do Item"
                        )
                    }
                    ordem_col = ["Item", "Subitem", "Nome", "Qtd", "Valor Unitário", "Total", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG"]
                    
                    if tipo_perfil == "Fiscal":
                        st.dataframe(df_forn_atual, column_order=ordem_col, column_config=cfg_colunas, hide_index=True, use_container_width=True)
                        total_desse_forn = df_forn_atual["Total"].sum()
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-end; margin-top: 8px; margin-bottom: 16px;">
                            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; gap: 10px; align-items: baseline;">
                                <span style="font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total {forn}:</span>
                                <span style="font-size: 18px; font-weight: 800; color: #1e3a29;">R$ {total_desse_forn:,.2f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    else:
                        df_editado_forn = st.data_editor(
                            df_forn_atual, column_order=ordem_col, column_config=cfg_colunas, disabled=["Total"], 
                            num_rows="dynamic", use_container_width=True, hide_index=True,
                            key=f"editor_forn_{nc_selecionada_vis}_{forn.replace(' ', '_')}_{i}"
                        )
                        
                        cols_cmp = [c for c in df_forn_atual.columns if c not in ["Total", "_uid"]]
                        dict_antigo = df_forn_atual[cols_cmp].fillna("").to_dict("records")
                        dict_novo = df_editado_forn[cols_cmp].fillna("").to_dict("records")
                        
                        if dict_antigo != dict_novo:
                            houve_alteracao = True
                        
                        v_unit_num = pd.to_numeric(df_editado_forn["Valor Unitário"], errors="coerce").fillna(0.0)
                        qtd_num = pd.to_numeric(df_editado_forn["Qtd"], errors="coerce").fillna(0).astype(int)
                        df_editado_forn["Total"] = v_unit_num * qtd_num
                        total_desse_forn = df_editado_forn["Total"].sum()
                        
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-end; margin-top: 8px; margin-bottom: 16px;">
                            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; gap: 10px; align-items: baseline;">
                                <span style="font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total {forn}:</span>
                                <span style="font-size: 18px; font-weight: 800; color: #1e3a29;">R$ {total_desse_forn:,.2f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("") 
                        
                        df_atualizado_acumulado.append((forn, df_forn_atual, df_editado_forn))
                
                if tipo_perfil != "Fiscal" and houve_alteracao:
                    uids_excluidos = set()
                    uids_adicionados_ou_atualizados = {}
                    
                    for forn_nome, df_original, df_edit in df_atualizado_acumulado:
                        uids_orig = set(df_original["_uid"].dropna().unique()) if "_uid" in df_original.columns else set()
                        uids_novos = set(df_edit["_uid"].dropna().unique()) if "_uid" in df_edit.columns else set()
                        
                        uids_excluidos.update(uids_orig - uids_novos)
                        
                        for r in df_edit.to_dict(orient="records"):
                            uid_item = r.get("_uid")
                            if not uid_item or pd.isna(uid_item) or str(uid_item).strip() == "":
                                uid_item = f"it_{nc_selecionada_vis}_{uuid.uuid4().hex[:8]}"
                            
                            qtd_val = int(pd.to_numeric(r.get("Qtd", 0), errors="coerce") or 0)
                            v_unit_val = float(pd.to_numeric(r.get("Valor Unitário", 0.0), errors="coerce") or 0.0)
                            total_val = qtd_val * v_unit_val
                            
                            dados_salvar = {
                                "_uid": uid_item,
                                "Item": int(pd.to_numeric(r.get("Item", 1), errors="coerce") or 1),
                                "Subitem": str(r.get("Subitem", "") or "").strip(),
                                "Nome": str(r.get("Nome", "") or "").strip(),
                                "Qtd": qtd_val,
                                "Valor Unitário": v_unit_val,
                                "Total": total_val,
                                "Situação": str(r.get("Situação", "Planejamento") or "Planejamento"),
                                "Fornecedor": str(r.get("Fornecedor", forn_nome) or forn_nome).strip().upper(),
                                "CNPJ": formatar_cnpj(str(r.get("CNPJ", "") or "")),
                                "Pregão": str(r.get("Pregão", "") or ""),
                                "Ata": str(r.get("Ata", "") or ""),
                                "UASG": str(r.get("UASG", "") or "")
                            }
                            uids_adicionados_ou_atualizados[uid_item] = dados_salvar
                    
                    nova_lista_itens = []
                    for it_bd in banco_dados[nc_selecionada_vis]["itens"]:
                        uid_bd = it_bd.get("_uid")
                        if uid_bd in uids_excluidos:
                            continue
                        if uid_bd in uids_adicionados_ou_atualizados:
                            nova_lista_itens.append(uids_adicionados_ou_atualizados.pop(uid_bd))
                        else:
                            nova_lista_itens.append(it_bd)
                    
                    for novo_uid, novo_obj in uids_adicionados_ou_atualizados.items():
                        nova_lista_itens.append(novo_obj)
                    
                    banco_dados[nc_selecionada_vis]["itens"] = nova_lista_itens
                    salvar_dados(banco_dados)
                    st.session_state.banco = banco_dados
                    st.toast("✅ Alterações salvas com sucesso!")
                    st.rerun()
    else:
         st.info("Nenhuma NC cadastrada para este ano nesta seção.")

# =====================================================================
# ABA 3: VISÃO GLOBAL ANUAL
# =====================================================================
with tab_visao_global:
    # Estado da sessão para controlar exibição do relatório anual oficial
    if "exibir_relatorio_anual" not in st.session_state:
        st.session_state["exibir_relatorio_anual"] = False

    # 1. Coleta e consolidação de dados orçamentários do ano selecionado
    lista_ncs_ano = []
    lista_itens_ano = []
    
    if tipo_perfil == "Fiscal" and secao_ativa == OPCAO_TODAS_SECOES:
        sub_titulo_vg = f"🌐 Visão Corporativa da OM ({om_user}) - Todas as Seções • Exercício {ano_selecionado}"
        try:
            resp_todas_secoes = supabase.table("dados").select("*").like("id", f"{om_user}_%").execute()
            for linha in (resp_todas_secoes.data or []):
                sec_id = str(linha.get("id", "")).replace(f"{om_user}_", "")
                banco_secao_laco = linha.get("ncs", {})
                if isinstance(banco_secao_laco, dict):
                    for nc, dados_nc in banco_secao_laco.items():
                        if nc != "CONFIG_REQUISICAO" and isinstance(dados_nc, dict) and extrair_ano(nc) == ano_selecionado:
                            v_rec = float(dados_nc.get("valor_recebido") or 0.0)
                            nd_nc = str(dados_nc.get("nd") or "Não informada").strip()
                            pi_nc = str(dados_nc.get("pi") or "-").strip()
                            itens_nc = dados_nc.get("itens", []) or []
                            
                            tot_gasto_nc = 0.0
                            for idx_it, item in enumerate(itens_nc):
                                try:
                                    qtd_it = int(float(item.get("Qtd") or 0))
                                except Exception:
                                    qtd_it = 0
                                try:
                                    v_unit_it = float(item.get("Valor Unitário") or 0.0)
                                except Exception:
                                    v_unit_it = 0.0
                                try:
                                    tot_it = float(item.get("Total") or (qtd_it * v_unit_it))
                                except Exception:
                                    tot_it = qtd_it * v_unit_it
                                
                                tot_gasto_nc += tot_it
                                sub_it = str(item.get("Subitem") or "").strip()
                                if not sub_it:
                                    sub_it = determinar_subitem(nd_nc, str(item.get("Nome") or ""))
                                
                                sit_it = str(item.get("Situação") or "Planejamento").strip()
                                if sit_it not in ["Recebido", "Aguardando entrega", "Planejamento"]:
                                    sit_it = "Planejamento"
                                
                                lista_itens_ano.append({
                                    "Item": int(item.get("Item") or (idx_it + 1)),
                                    "NC": nc,
                                    "ND": nd_nc,
                                    "PI": pi_nc,
                                    "Subitem": sub_it,
                                    "Nome": str(item.get("Nome") or "Item sem nome").strip(),
                                    "Qtd": qtd_it,
                                    "Valor Unitário": v_unit_it,
                                    "Total": tot_it,
                                    "Situação": sit_it,
                                    "Fornecedor": str(item.get("Fornecedor") or "-").strip(),
                                    "CNPJ": str(item.get("CNPJ") or "-").strip(),
                                    "Pregão": str(item.get("Pregão") or "-").strip(),
                                    "Ata": str(item.get("Ata") or "-").strip(),
                                    "UASG": str(item.get("UASG") or "-").strip(),
                                    "Seção": sec_id
                                })
                            
                            lista_ncs_ano.append({
                                "NC": nc,
                                "ND": nd_nc,
                                "PI": pi_nc,
                                "Valor Recebido": v_rec,
                                "Total Empenhado": tot_gasto_nc,
                                "Saldo": v_rec - tot_gasto_nc,
                                "Qtd Itens": len(itens_nc),
                                "Seção": sec_id
                            })
        except Exception as e_coleta:
            st.error(f"Erro ao consolidar dados da OM: {e_coleta}")
    else:
        sub_titulo_vg = f"📊 Painel Gerencial de Recursos e Aquisições - Seção: {secao_ativa} • Exercício {ano_selecionado}"
        if ncs_do_ano:
            for nc in ncs_do_ano:
                dados_nc = banco_dados.get(nc, {})
                if isinstance(dados_nc, dict):
                    v_rec = float(dados_nc.get("valor_recebido") or 0.0)
                    nd_nc = str(dados_nc.get("nd") or "Não informada").strip()
                    pi_nc = str(dados_nc.get("pi") or "-").strip()
                    itens_nc = dados_nc.get("itens", []) or []
                    
                    tot_gasto_nc = 0.0
                    for idx_it, item in enumerate(itens_nc):
                        try:
                            qtd_it = int(float(item.get("Qtd") or 0))
                        except Exception:
                            qtd_it = 0
                        try:
                            v_unit_it = float(item.get("Valor Unitário") or 0.0)
                        except Exception:
                            v_unit_it = 0.0
                        try:
                            tot_it = float(item.get("Total") or (qtd_it * v_unit_it))
                        except Exception:
                            tot_it = qtd_it * v_unit_it
                        
                        tot_gasto_nc += tot_it
                        sub_it = str(item.get("Subitem") or "").strip()
                        if not sub_it:
                            sub_it = determinar_subitem(nd_nc, str(item.get("Nome") or ""))
                        
                        sit_it = str(item.get("Situação") or "Planejamento").strip()
                        if sit_it not in ["Recebido", "Aguardando entrega", "Planejamento"]:
                            sit_it = "Planejamento"
                        
                        lista_itens_ano.append({
                            "Item": int(item.get("Item") or (idx_it + 1)),
                            "NC": nc,
                            "ND": nd_nc,
                            "PI": pi_nc,
                            "Subitem": sub_it,
                            "Nome": str(item.get("Nome") or "Item sem nome").strip(),
                            "Qtd": qtd_it,
                            "Valor Unitário": v_unit_it,
                            "Total": tot_it,
                            "Situação": sit_it,
                            "Fornecedor": str(item.get("Fornecedor") or "-").strip(),
                            "CNPJ": str(item.get("CNPJ") or "-").strip(),
                            "Pregão": str(item.get("Pregão") or "-").strip(),
                            "Ata": str(item.get("Ata") or "-").strip(),
                            "UASG": str(item.get("UASG") or "-").strip(),
                            "Seção": secao_ativa
                        })
                    
                    lista_ncs_ano.append({
                        "NC": nc,
                        "ND": nd_nc,
                        "PI": pi_nc,
                        "Valor Recebido": v_rec,
                        "Total Empenhado": tot_gasto_nc,
                        "Saldo": v_rec - tot_gasto_nc,
                        "Qtd Itens": len(itens_nc),
                        "Seção": secao_ativa
                    })

    df_ncs_ano = pd.DataFrame(lista_ncs_ano) if lista_ncs_ano else pd.DataFrame(columns=["NC", "ND", "PI", "Valor Recebido", "Total Empenhado", "Saldo", "Qtd Itens", "Seção"])
    df_itens_ano = pd.DataFrame(lista_itens_ano) if lista_itens_ano else pd.DataFrame(columns=["Item", "NC", "ND", "PI", "Subitem", "Nome", "Qtd", "Valor Unitário", "Total", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata", "UASG", "Seção"])

    # Cálculos estatísticos consolidados
    total_recebido_ano = float(df_ncs_ano["Valor Recebido"].sum()) if not df_ncs_ano.empty else 0.0
    total_empenhado_ano = float(df_itens_ano["Total"].sum()) if not df_itens_ano.empty else 0.0
    saldo_ano = total_recebido_ano - total_empenhado_ano
    pct_exec = (total_empenhado_ano / total_recebido_ano * 100) if total_recebido_ano > 0 else 0.0
    total_itens_cadastrados = len(df_itens_ano)
    total_qtd_unidades = int(df_itens_ano["Qtd"].sum()) if not df_itens_ano.empty else 0

    # Funções para Geração Oficial de Documentos (Excel com Itens e PDF A4 Paisagem)
    def gerar_excel_anual_completo(om_nome, secao_nome, ano_exercicio, ncs_lista, itens_lista, total_rec, total_emp, saldo_disp, pct_e, tot_itens, tot_qtd):
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Itens Adquiridos"
        ws.views.sheetView[0].showGridLines = True

        cor_militar = "1E3A29"
        cor_militar_claro = "E8F5E9"
        cor_cinza_claro = "F8FAFC"
        
        font_titulo = Font(name="Arial", size=13, bold=True, color=cor_militar)
        font_subtitulo = Font(name="Arial", size=11, bold=True, color="1E293B")
        font_meta = Font(name="Arial", size=9, italic=True, color="475569")
        font_card_rotulo = Font(name="Arial", size=8, bold=True, color="64748B")
        font_card_valor = Font(name="Arial", size=11, bold=True, color=cor_militar)
        font_header_tab = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        font_item_qtd = Font(name="Arial", size=9, bold=True, color="0F5132")
        font_total = Font(name="Arial", size=10, bold=True, color="000000")

        fill_header = PatternFill(start_color=cor_militar, end_color=cor_militar, fill_type="solid")
        fill_zebrado = PatternFill(start_color=cor_cinza_claro, end_color=cor_cinza_claro, fill_type="solid")
        fill_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        fill_qtd = PatternFill(start_color=cor_militar_claro, end_color=cor_militar_claro, fill_type="solid")

        border_thin = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )
        border_total = Border(
            top=Side(style="thin", color="000000"),
            bottom=Side(style="double", color="000000")
        )

        # 1. Cabeçalho Oficial no topo da Aba Principal
        ws["A1"] = "MINISTÉRIO DA DEFESA - EXÉRCITO BRASILEIRO"
        ws["A1"].font = font_titulo
        ws["A2"] = f"RELATÓRIO ANUAL DE AQUISIÇÕES E MATERIAIS ADQUIRIDOS - EXERCÍCIO {ano_exercicio}"
        ws["A2"].font = font_subtitulo
        ws["A3"] = f"Organização Militar: {om_nome} | Seção: {secao_nome} | NCs: {len(ncs_lista)} | Total de Itens: {tot_itens} ({tot_qtd:,} unidades)"
        ws["A3"].font = font_meta

        # 2. Cartões de Resumo Executivo
        cards = [
            ("TOTAL CONCEDIDO (R$)", f"R$ {total_rec:,.2f}"),
            ("TOTAL EMPENHADO (R$)", f"R$ {total_emp:,.2f}"),
            ("SALDO DISPONÍVEL (R$)", f"R$ {saldo_disp:,.2f}"),
            ("TAXA DE EXECUÇÃO", f"{pct_e:.1f}%"),
            ("TOTAL DE ITENS", f"{tot_itens}"),
            ("UNIDADES ADQUIRIDAS", f"{tot_qtd:,}")
        ]
        for idx_c, (rot, val) in enumerate(cards, 1):
            col_let = get_column_letter(idx_c)
            c_rot = ws[f"{col_let}5"]
            c_rot.value = rot
            c_rot.font = font_card_rotulo
            c_rot.fill = fill_card
            c_rot.alignment = Alignment(horizontal="center", vertical="center")
            c_rot.border = border_thin

            c_val = ws[f"{col_let}6"]
            c_val.value = val
            c_val.font = font_card_valor
            c_val.fill = fill_card
            c_val.alignment = Alignment(horizontal="center", vertical="center")
            c_val.border = border_thin

        # 3. Cabeçalho da Tabela de Itens
        colunas_itens = [
            "Item", "Nota de Crédito", "ND", "PI", "Subitem",
            "Descrição do Material / Serviço", "Quantidade (Qtd)",
            "Valor Unitário (R$)", "Valor Total (R$)", "Situação",
            "Fornecedor", "CNPJ", "Pregão", "Ata", "Seção"
        ]
        for idx_col, col_nome in enumerate(colunas_itens, 1):
            c = ws.cell(row=8, column=idx_col, value=col_nome)
            c.font = font_header_tab
            c.fill = fill_header
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = border_thin
        ws.row_dimensions[8].height = 28

        # 4. Inserção de todos os itens adquiridos no ano
        linha_atual = 9
        for idx_it, it in enumerate(itens_lista, 1):
            ws.cell(row=linha_atual, column=1, value=it.get("Item", idx_it)).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=2, value=str(it.get("NC", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=3, value=str(it.get("ND", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=4, value=str(it.get("PI", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=5, value=str(it.get("Subitem", ""))).alignment = Alignment(horizontal="center", vertical="center")
            
            c_nome = ws.cell(row=linha_atual, column=6, value=str(it.get("Nome", "")))
            c_nome.alignment = Alignment(horizontal="left", vertical="center")

            c_qtd = ws.cell(row=linha_atual, column=7, value=int(it.get("Qtd", 0)))
            c_qtd.font = font_item_qtd
            c_qtd.fill = fill_qtd
            c_qtd.alignment = Alignment(horizontal="center", vertical="center")
            c_qtd.number_format = "#,##0"

            c_vu = ws.cell(row=linha_atual, column=8, value=float(it.get("Valor Unitário", 0.0)))
            c_vu.alignment = Alignment(horizontal="right", vertical="center")
            c_vu.number_format = "R$ #,##0.00"

            c_tot = ws.cell(row=linha_atual, column=9, value=float(it.get("Total", 0.0)))
            c_tot.font = Font(name="Arial", size=9, bold=True)
            c_tot.alignment = Alignment(horizontal="right", vertical="center")
            c_tot.number_format = "R$ #,##0.00"

            ws.cell(row=linha_atual, column=10, value=str(it.get("Situação", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=11, value=str(it.get("Fornecedor", ""))).alignment = Alignment(horizontal="left", vertical="center")
            ws.cell(row=linha_atual, column=12, value=str(it.get("CNPJ", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=13, value=str(it.get("Pregão", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=14, value=str(it.get("Ata", ""))).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=linha_atual, column=15, value=str(it.get("Seção", ""))).alignment = Alignment(horizontal="center", vertical="center")

            for col_i in range(1, 16):
                cell_i = ws.cell(row=linha_atual, column=col_i)
                cell_i.border = border_thin
                if idx_it % 2 == 0 and col_i != 7:
                    cell_i.fill = fill_zebrado

            linha_atual += 1

        # 5. Linha de Totais da Lista de Itens
        ws.cell(row=linha_atual, column=1, value="TOTAL CONSOLIDADO").alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=linha_atual, column=6, value=f"{len(itens_lista)} Itens Adquiridos").font = font_total

        c_sum_qtd = ws.cell(row=linha_atual, column=7, value=f"=SUM(G9:G{linha_atual-1})" if linha_atual > 9 else 0)
        c_sum_qtd.font = Font(name="Arial", size=10, bold=True, color="0F5132")
        c_sum_qtd.alignment = Alignment(horizontal="center", vertical="center")
        c_sum_qtd.number_format = "#,##0"

        c_sum_tot = ws.cell(row=linha_atual, column=9, value=f"=SUM(I9:I{linha_atual-1})" if linha_atual > 9 else 0)
        c_sum_tot.font = Font(name="Arial", size=10, bold=True, color=cor_militar)
        c_sum_tot.alignment = Alignment(horizontal="right", vertical="center")
        c_sum_tot.number_format = "R$ #,##0.00"

        for col_i in range(1, 16):
            cell_tot = ws.cell(row=linha_atual, column=col_i)
            cell_tot.font = font_total
            cell_tot.border = border_total

        larguras = {
            "A": 8, "B": 17, "C": 12, "D": 12, "E": 12,
            "F": 45, "G": 18, "H": 18, "I": 18, "J": 18,
            "K": 28, "L": 20, "M": 14, "N": 14, "O": 14
        }
        for col_l, w in larguras.items():
            ws.column_dimensions[col_l].width = w

        # Aba 2: Relação de Notas de Crédito
        ws2 = wb.create_sheet(title="Notas de Crédito")
        ws2.views.sheetView[0].showGridLines = True
        ws2["A1"] = f"Relação de Notas de Crédito - Exercício {ano_exercicio}"
        ws2["A1"].font = font_titulo
        colunas_nc = ["Nota de Crédito", "ND", "PI", "Qtd Itens", "Valor Recebido (R$)", "Total Empenhado (R$)", "Saldo (R$)", "% Execução", "Seção"]
        for idx_col, h in enumerate(colunas_nc, 1):
            cell_h = ws2.cell(row=3, column=idx_col, value=h)
            cell_h.font = font_header_tab
            cell_h.fill = fill_header
            cell_h.alignment = Alignment(horizontal="center", vertical="center")
            cell_h.border = border_thin
        
        for idx_nc, nc_obj in enumerate(ncs_lista, 4):
            ws2.cell(row=idx_nc, column=1, value=str(nc_obj.get("NC", ""))).alignment = Alignment(horizontal="center")
            ws2.cell(row=idx_nc, column=2, value=str(nc_obj.get("ND", ""))).alignment = Alignment(horizontal="center")
            ws2.cell(row=idx_nc, column=3, value=str(nc_obj.get("PI", ""))).alignment = Alignment(horizontal="center")
            ws2.cell(row=idx_nc, column=4, value=int(nc_obj.get("Qtd Itens", 0))).alignment = Alignment(horizontal="center")
            
            c_rec = ws2.cell(row=idx_nc, column=5, value=float(nc_obj.get("Valor Recebido", 0.0)))
            c_rec.number_format = "R$ #,##0.00"
            c_rec.alignment = Alignment(horizontal="right")

            c_emp = ws2.cell(row=idx_nc, column=6, value=float(nc_obj.get("Total Empenhado", 0.0)))
            c_emp.number_format = "R$ #,##0.00"
            c_emp.alignment = Alignment(horizontal="right")

            c_sal = ws2.cell(row=idx_nc, column=7, value=float(nc_obj.get("Saldo", 0.0)))
            c_sal.number_format = "R$ #,##0.00"
            c_sal.alignment = Alignment(horizontal="right")

            v_rec_n = float(nc_obj.get("Valor Recebido", 0.0))
            v_emp_n = float(nc_obj.get("Total Empenhado", 0.0))
            pct_n = (v_emp_n / v_rec_n * 100) if v_rec_n > 0 else 0.0
            ws2.cell(row=idx_nc, column=8, value=f"{pct_n:.1f}%").alignment = Alignment(horizontal="center")
            ws2.cell(row=idx_nc, column=9, value=str(nc_obj.get("Seção", ""))).alignment = Alignment(horizontal="center")
            
            for col_i in range(1, 10):
                ws2.cell(row=idx_nc, column=col_i).border = border_thin

        for col_l in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
            ws2.column_dimensions[col_l].width = 18

        buf_excel_out = io.BytesIO()
        wb.save(buf_excel_out)
        buf_excel_out.seek(0)
        return buf_excel_out.getvalue()

    def gerar_pdf_anual_completo(om_nome, secao_nome, ano_exercicio, ncs_lista, itens_lista, total_rec, total_emp, saldo_disp, pct_e, tot_itens, tot_qtd, cfg_req):
        import io, html, datetime
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buf_pdf_out = io.BytesIO()
        doc = SimpleDocTemplate(
            buf_pdf_out,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        styles = getSampleStyleSheet()
        cor_primaria = colors.HexColor("#1E3A29")
        cor_fundo_cinza = colors.HexColor("#F8FAFC")
        cor_linha = colors.HexColor("#CBD5E1")

        style_top1 = ParagraphStyle('Top1', parent=styles['Normal'], fontSize=8.5, fontName='Helvetica-Bold', alignment=1, textColor=colors.HexColor('#475569'))
        style_top2 = ParagraphStyle('Top2', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', alignment=1, textColor=colors.black)
        style_top3 = ParagraphStyle('Top3', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.HexColor('#64748B'))
        style_titulo = ParagraphStyle('Tit', parent=styles['Heading1'], fontSize=13, fontName='Helvetica-Bold', alignment=1, textColor=cor_primaria, spaceAfter=3)
        style_sub = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.HexColor('#475569'), spaceAfter=8)

        style_sec_tit = ParagraphStyle('SecTit', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=cor_primaria, spaceAfter=4)
        
        style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', alignment=1, textColor=colors.white)
        style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.black)
        style_td_c = ParagraphStyle('TDC', parent=styles['Normal'], fontSize=7, leading=9, alignment=1, textColor=colors.black)
        style_td_r = ParagraphStyle('TDR', parent=styles['Normal'], fontSize=7, leading=9, alignment=2, textColor=colors.black)
        style_td_b_r = ParagraphStyle('TDBR', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', alignment=2, textColor=cor_primaria)
        style_td_b_c = ParagraphStyle('TDBC', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', alignment=1, textColor=colors.HexColor('#0F5132'))

        story = []

        # 1. Cabeçalho Militar
        story.append(Paragraph("MINISTÉRIO DA DEFESA", style_top1))
        story.append(Paragraph("EXÉRCITO BRASILEIRO", style_top2))
        story.append(Paragraph(html.escape(f"{om_nome} • {secao_nome}"), style_top3))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"RELATÓRIO ANUAL DE GESTÃO ORÇAMENTÁRIA E AQUISIÇÕES - EXERCÍCIO {ano_exercicio}", style_titulo))
        data_emissao = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
        story.append(Paragraph(f"Documento Consolidado emitido em {data_emissao}", style_sub))

        # 2. Resumo de Recursos
        story.append(Paragraph("1. BALANÇO DE RECURSOS ORÇAMENTÁRIOS CONCEDIDOS E EXECUTADOS", style_sec_tit))
        resumo_data = [
            [
                Paragraph("Total Concedido em NCs", style_top1),
                Paragraph("Total Empenhado / Alocado", style_top1),
                Paragraph("Saldo Disponível", style_top1),
                Paragraph("Taxa de Execução", style_top1),
                Paragraph("Itens / Descrições", style_top1),
                Paragraph("Unidades Adquiridas", style_top1)
            ],
            [
                Paragraph(f"R$ {total_rec:,.2f}", style_td_b_c),
                Paragraph(f"R$ {total_emp:,.2f}", style_td_b_c),
                Paragraph(f"R$ {saldo_disp:,.2f}", style_td_b_c),
                Paragraph(f"{pct_e:.1f}%", style_td_b_c),
                Paragraph(f"{tot_itens}", style_td_b_c),
                Paragraph(f"{tot_qtd:,} unid.", style_td_b_c)
            ]
        ]
        t_resumo = Table(resumo_data, colWidths=[133, 133, 133, 133, 133, 133])
        t_resumo.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,1), (-1,1), cor_fundo_cinza),
            ('GRID', (0,0), (-1,-1), 0.5, cor_linha),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_resumo)
        story.append(Spacer(1, 8))

        # 3. Tabela de Notas de Crédito
        if ncs_lista:
            story.append(Paragraph(f"2. NOTAS DE CRÉDITO DO EXERCÍCIO ({len(ncs_lista)} NCs)", style_sec_tit))
            nc_rows = [[
                Paragraph("Nota de Crédito", style_th),
                Paragraph("ND", style_th),
                Paragraph("PI", style_th),
                Paragraph("Qtd Itens", style_th),
                Paragraph("Valor Concedido", style_th),
                Paragraph("Total Empenhado", style_th),
                Paragraph("Saldo Disponível", style_th),
                Paragraph("Execução", style_th),
                Paragraph("Seção", style_th)
            ]]
            for nc_o in ncs_lista:
                v_r = float(nc_o.get("Valor Recebido", 0.0))
                v_e = float(nc_o.get("Total Empenhado", 0.0))
                v_s = float(nc_o.get("Saldo", 0.0))
                p_e = (v_e / v_r * 100) if v_r > 0 else 0.0
                nc_rows.append([
                    Paragraph(html.escape(str(nc_o.get("NC", ""))), style_td_c),
                    Paragraph(html.escape(str(nc_o.get("ND", ""))), style_td_c),
                    Paragraph(html.escape(str(nc_o.get("PI", ""))), style_td_c),
                    Paragraph(str(nc_o.get("Qtd Itens", 0)), style_td_c),
                    Paragraph(f"R$ {v_r:,.2f}", style_td_r),
                    Paragraph(f"R$ {v_e:,.2f}", style_td_r),
                    Paragraph(f"R$ {v_s:,.2f}", style_td_r),
                    Paragraph(f"{p_e:.1f}%", style_td_c),
                    Paragraph(html.escape(str(nc_o.get("Seção", ""))), style_td_c)
                ])
            t_ncs = Table(nc_rows, colWidths=[95, 60, 60, 50, 110, 110, 110, 60, 125])
            t_ncs.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), cor_primaria),
                ('GRID', (0,0), (-1,-1), 0.5, cor_linha),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, cor_fundo_cinza]),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(t_ncs)
            story.append(Spacer(1, 8))

        # 4. Tabela Completa de Itens Adquiridos no Ano (com Quantidades)
        story.append(Paragraph(f"3. LISTAGEM COMPLETA DE TODOS OS ITENS ADQUIRIDOS NO ANO ({len(itens_lista)} ITENS • {tot_qtd:,} UNIDADES)", style_sec_tit))
        itens_rows = [[
            Paragraph("Item", style_th),
            Paragraph("NC", style_th),
            Paragraph("ND", style_th),
            Paragraph("Subitem", style_th),
            Paragraph("Descrição do Material / Serviço", style_th),
            Paragraph("Qtd", style_th),
            Paragraph("Valor Unit.", style_th),
            Paragraph("Total (R$)", style_th),
            Paragraph("Situação", style_th),
            Paragraph("Fornecedor", style_th),
            Paragraph("Pregão / Ata", style_th)
        ]]
        for it_o in itens_lista:
            vu = float(it_o.get("Valor Unitário", 0.0))
            tot = float(it_o.get("Total", 0.0))
            qtd = int(it_o.get("Qtd", 0))
            itens_rows.append([
                Paragraph(str(it_o.get("Item", "")), style_td_c),
                Paragraph(html.escape(str(it_o.get("NC", ""))), style_td_c),
                Paragraph(html.escape(str(it_o.get("ND", ""))), style_td_c),
                Paragraph(html.escape(str(it_o.get("Subitem", ""))), style_td_c),
                Paragraph(html.escape(str(it_o.get("Nome", ""))), style_td),
                Paragraph(f"<b>{qtd}</b>", style_td_b_c),
                Paragraph(f"R$ {vu:,.2f}", style_td_r),
                Paragraph(f"R$ {tot:,.2f}", style_td_b_r),
                Paragraph(html.escape(str(it_o.get("Situação", ""))), style_td_c),
                Paragraph(html.escape(str(it_o.get("Fornecedor", ""))), style_td),
                Paragraph(html.escape(str(it_o.get("Pregão", ""))), style_td_c)
            ])
        
        # Linha de total geral dos itens
        itens_rows.append([
            Paragraph("TOTAL", style_th),
            Paragraph("", style_th),
            Paragraph("", style_th),
            Paragraph("", style_th),
            Paragraph(f"<b>Total Consolidado ({len(itens_lista)} Itens)</b>", style_th),
            Paragraph(f"<b>{tot_qtd:,}</b>", style_th),
            Paragraph("", style_th),
            Paragraph(f"<b>R$ {total_emp:,.2f}</b>", style_th),
            Paragraph("", style_th),
            Paragraph("", style_th),
            Paragraph("", style_th)
        ])

        t_itens = Table(itens_rows, colWidths=[25, 65, 55, 50, 215, 42, 65, 75, 60, 95, 55], repeatRows=1)
        t_itens.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), cor_primaria),
            ('BACKGROUND', (0,-1), (-1,-1), cor_primaria),
            ('GRID', (0,0), (-1,-1), 0.5, cor_linha),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, cor_fundo_cinza]),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_itens)
        story.append(Spacer(1, 14))

        # 5. Assinaturas
        n_chefe = cfg_req.get("assinatura_nome", "Chefe da Seção")
        f_chefe = cfg_req.get("assinatura_funcao", f"Chefe da {secao_nome}")
        n_od = cfg_req.get("od_nome", "Ordenador de Despesas")
        f_od = cfg_req.get("od_funcao", "Ordenador de Despesas")

        t_ass = Table([
            [
                Paragraph(f"<br/><br/>________________________________________<br/><b>{html.escape(n_chefe)}</b><br/>{html.escape(f_chefe)}", style_td_c),
                Paragraph(f"<br/><br/>________________________________________<br/><b>{html.escape(n_od)}</b><br/>{html.escape(f_od)}", style_td_c)
            ]
        ], colWidths=[400, 400])
        story.append(KeepTogether([
            Paragraph("Certifico a exatidão das informações financeiras e das quantidades adquiridas deste relatório anual.", style_sub),
            t_ass
        ]))

        doc.build(story)
        buf_pdf_out.seek(0)
        return buf_pdf_out.getvalue()

    # Prepara arquivos para download imediato em Base64 (imunes a bloqueios de cookies e proxies)
    import base64
    bytes_excel_anual = None
    bytes_pdf_anual = None
    b64_pdf = ""
    b64_excel = ""
    nome_arquivo_pdf = f"Relatorio_Anual_{ano_selecionado}_{om_user}_{secao_ativa}.pdf".replace(" ", "_").replace("º", "o").replace("/", "_")
    nome_arquivo_excel = f"Relatorio_Anual_Itens_{ano_selecionado}_{om_user}_{secao_ativa}.xlsx".replace(" ", "_").replace("º", "o").replace("/", "_")

    if lista_itens_ano or lista_ncs_ano:
        try:
            bytes_excel_anual = gerar_excel_anual_completo(
                om_user, secao_ativa, ano_selecionado,
                lista_ncs_ano, lista_itens_ano,
                total_recebido_ano, total_empenhado_ano, saldo_ano, pct_exec,
                total_itens_cadastrados, total_qtd_unidades
            )
            if bytes_excel_anual:
                b64_excel = base64.b64encode(bytes_excel_anual).decode("utf-8")
        except Exception as e_xls:
            print("Erro ao gerar Excel anual:", e_xls)

        try:
            cfg_req_atual = banco_dados.get("CONFIG_REQUISICAO", {}) if isinstance(banco_dados, dict) else {}
            bytes_pdf_anual = gerar_pdf_anual_completo(
                om_user, secao_ativa, ano_selecionado,
                lista_ncs_ano, lista_itens_ano,
                total_recebido_ano, total_empenhado_ano, saldo_ano, pct_exec,
                total_itens_cadastrados, total_qtd_unidades,
                cfg_req_atual
            )
            if bytes_pdf_anual:
                b64_pdf = base64.b64encode(bytes_pdf_anual).decode("utf-8")
        except Exception as e_pdf:
            print("Erro ao gerar PDF anual:", e_pdf)

    # Cabeçalho da Visão Global e Botões Principais de Ação
    col_vg1, col_vg2, col_vg3, col_vg4 = st.columns([2.6, 1.2, 1.1, 1.1])
    with col_vg1:
        st.subheader(sub_titulo_vg)
        st.caption(f"Exercício de **{ano_selecionado}** • **{len(df_ncs_ano)}** Notas de Crédito ativas • **{total_itens_cadastrados}** itens cadastrados ({total_qtd_unidades} unidades adquiridas)")
    
    with col_vg2:
        rotulo_btn_rel = "❌ Fechar Relatório" if st.session_state.get("exibir_relatorio_anual", False) else "📑 Ver Relatório Anual"
        if st.button(rotulo_btn_rel, type="primary", use_container_width=True, key="btn_toggle_relatorio_anual"):
            st.session_state["exibir_relatorio_anual"] = not st.session_state.get("exibir_relatorio_anual", False)
            st.rerun()

    with col_vg3:
        if b64_pdf:
            st.markdown(f"""
            <a href="data:application/pdf;base64,{b64_pdf}" download="{nome_arquivo_pdf}"
               style="display: flex; align-items: center; justify-content: center; gap: 6px; background-color: #1e3a29; color: #ffffff !important; font-weight: 700; font-size: 13px; padding: 0 12px; height: 38px; border-radius: 8px; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid #14271c; width: 100%; box-sizing: border-box; text-align: center; cursor: pointer;">
               📥 Baixar PDF
            </a>
            """, unsafe_allow_html=True)

    with col_vg4:
        if b64_excel:
            st.markdown(f"""
            <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{nome_arquivo_excel}"
               style="display: flex; align-items: center; justify-content: center; gap: 6px; background-color: #2563eb; color: #ffffff !important; font-weight: 700; font-size: 13px; padding: 0 12px; height: 38px; border-radius: 8px; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid #1d4ed8; width: 100%; box-sizing: border-box; text-align: center; cursor: pointer;">
               📊 Baixar Excel
            </a>
            """, unsafe_allow_html=True)

    # =========================================================================
    # VISUALIZAÇÃO DO RELATÓRIO ANUAL OFICIAL (DOCUMENTO EXECUTIVO / IMPRESSÃO)
    # =========================================================================
    if st.session_state.get("exibir_relatorio_anual", False):
        import datetime
        data_hora_emissao = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        # Banner executivo (sem nenhum onclick inline no HTML para evitar erro #231 do React)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a29 0%, #15291d 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.12);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; background: rgba(255,255,255,0.18); padding: 4px 10px; border-radius: 4px; font-weight: 700;">Documento Oficial Consolidado</span>
                    <h2 style="margin: 8px 0 4px 0; font-size: 21px; font-weight: 800; color: #ffffff;">RELATÓRIO ANUAL DE EXECUÇÃO ORÇAMENTÁRIA E AQUISIÇÕES</h2>
                    <p style="margin: 0; font-size: 13px; color: #d1fae5;">Exercício Financeiro: <b>{ano_selecionado}</b> • OM: <b>{om_user}</b> • Seção: <b>{secao_ativa}</b> • Emissão: {data_hora_emissao}</p>
                </div>
                <div style="background: rgba(255,255,255,0.15); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 700; color: #ffffff;">
                    {total_itens_cadastrados} itens • {total_qtd_unidades} unidades
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Barra de Ações (Download Direto de PDF e Excel via Base64 + Impressão no Navegador)
        col_act1, col_act2, col_act3 = st.columns([1.2, 1.2, 1])
        with col_act1:
            if b64_pdf:
                st.markdown(f"""
                <a href="data:application/pdf;base64,{b64_pdf}" download="{nome_arquivo_pdf}"
                   style="display: flex; align-items: center; justify-content: center; gap: 8px; background-color: #1e3a29; color: #ffffff !important; font-weight: 700; font-size: 13px; padding: 0 16px; height: 42px; border-radius: 8px; text-decoration: none; box-shadow: 0 2px 5px rgba(0,0,0,0.15); border: 1px solid #14271c; width: 100%; box-sizing: border-box; text-align: center; cursor: pointer;">
                   📥 Baixar Documento em PDF (A4 Paisagem)
                </a>
                """, unsafe_allow_html=True)
        with col_act2:
            if b64_excel:
                st.markdown(f"""
                <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{nome_arquivo_excel}"
                   style="display: flex; align-items: center; justify-content: center; gap: 8px; background-color: #2563eb; color: #ffffff !important; font-weight: 700; font-size: 13px; padding: 0 16px; height: 42px; border-radius: 8px; text-decoration: none; box-shadow: 0 2px 5px rgba(0,0,0,0.15); border: 1px solid #1d4ed8; width: 100%; box-sizing: border-box; text-align: center; cursor: pointer;">
                   📊 Baixar Planilha com Todos os Itens (.xlsx)
                </a>
                """, unsafe_allow_html=True)
        with col_act3:
            # Botão de impressão isolado em iframe nativo (seguro contra erro do React)
            st.components.v1.html("""
            <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                <button onclick="window.parent.print()" style="background: #475569; color: white; border: none; padding: 0 16px; height: 42px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; font-family: sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.15); width: 100%;">
                    🖨️ Imprimir Página
                </button>
            </div>
            """, height=44)

        # Visualizador direto do PDF na tela (Preview embutido)
        if b64_pdf:
            with st.expander("👁️ Visualizar PDF Formatado Diretamente na Tela (Preview)", expanded=False):
                st.markdown(f"""
                <div style="border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; margin-top: 8px;">
                    <iframe src="data:application/pdf;base64,{b64_pdf}#view=FitH" width="100%" height="600px" style="border: none;"></iframe>
                </div>
                """, unsafe_allow_html=True)

        # Quadro 1: Indicadores e Recursos Concedidos
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="border-bottom: 2px solid #1e3a29; padding-bottom: 10px; margin-bottom: 18px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 800; color: #1e3a29; text-transform: uppercase; letter-spacing: 0.5px;">
                    1. Balanço de Recursos Orçamentários e Créditos Concedidos ({ano_selecionado})
                </h3>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total Concedido em NCs</span>
                    <div style="font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 4px;">R$ {total_recebido_ano:,.2f}</div>
                    <span style="font-size: 11px; color: #64748b;">{len(df_ncs_ano)} Notas de Crédito</span>
                </div>
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total Empenhado / Alocado</span>
                    <div style="font-size: 20px; font-weight: 800; color: #1e3a29; margin-top: 4px;">R$ {total_empenhado_ano:,.2f}</div>
                    <span style="font-size: 11px; color: #64748b;">{total_itens_cadastrados} itens adquiridos</span>
                </div>
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Saldo Global Disponível</span>
                    <div style="font-size: 20px; font-weight: 800; color: {'#dc2626' if saldo_ano < 0 else '#15803d'}; margin-top: 4px;">R$ {saldo_ano:,.2f}</div>
                    <span style="font-size: 11px; color: #64748b;">Remanescente para empenho</span>
                </div>
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Taxa de Execução</span>
                    <div style="font-size: 20px; font-weight: 800; color: #0284c7; margin-top: 4px;">{pct_exec:.1f}%</div>
                    <span style="font-size: 11px; color: #64748b;">Índice de aproveitamento orçamentário</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tabela Detalhada das Notas de Crédito
        if not df_ncs_ano.empty:
            st.markdown("##### 📋 Tabela Discriminativa de Notas de Crédito do Exercício")
            df_ncs_exibir = df_ncs_ano.copy()
            df_ncs_exibir["% Exec."] = df_ncs_exibir.apply(lambda r: f"{(r['Total Empenhado'] / r['Valor Recebido'] * 100):.1f}%" if r["Valor Recebido"] > 0 else "0.0%", axis=1)
            df_ncs_exibir["Valor Recebido (R$)"] = df_ncs_exibir["Valor Recebido"].apply(lambda x: f"R$ {x:,.2f}")
            df_ncs_exibir["Total Empenhado (R$)"] = df_ncs_exibir["Total Empenhado"].apply(lambda x: f"R$ {x:,.2f}")
            df_ncs_exibir["Saldo (R$)"] = df_ncs_exibir["Saldo"].apply(lambda x: f"R$ {x:,.2f}")
            cols_nc_view = ["NC", "ND", "PI", "Qtd Itens", "Valor Recebido (R$)", "Total Empenhado (R$)", "Saldo (R$)", "% Exec."]
            if "Seção" in df_ncs_exibir.columns and tipo_perfil == "Fiscal":
                cols_nc_view.insert(1, "Seção")
            st.dataframe(df_ncs_exibir[cols_nc_view], use_container_width=True, hide_index=True)

        # Quadro 2: Gráficos e Distribuição de Recursos
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-top: 24px; margin-bottom: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="border-bottom: 2px solid #1e3a29; padding-bottom: 10px; margin-bottom: 18px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 800; color: #1e3a29; text-transform: uppercase; letter-spacing: 0.5px;">
                    2. Gráficos e Distribuição dos Recursos do Exercício ({ano_selecionado})
                </h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([1, 1])
        if not df_itens_ano.empty:
            with col_g1:
                st.markdown("###### 📊 Alocação por Natureza de Despesa (ND) e Status")
                df_agrup_nd = df_itens_ano.groupby(["ND", "Situação"])["Total"].sum().reset_index()
                escala_cores_rel = alt.Scale(domain=["Recebido", "Planejamento", "Aguardando entrega"], range=["#28a745", "#007bff", "#dc3545"])
                graf_nd = alt.Chart(df_agrup_nd).mark_bar().encode(
                    x=alt.X("ND:N", title="Natureza de Despesa"),
                    y=alt.Y("Total:Q", title="Total Alocado (R$)"),
                    color=alt.Color("Situação:N", scale=escala_cores_rel, title="Situação"),
                    tooltip=[alt.Tooltip("ND:N"), alt.Tooltip("Situação:N"), alt.Tooltip("Total:Q", format=",.2f")]
                ).properties(height=340)
                st.altair_chart(graf_nd, use_container_width=True)
            
            with col_g2:
                st.markdown("###### 🏢 Top Fornecedores / Credores por Volume Financeiro")
                df_forn = df_itens_ano.groupby("Fornecedor")["Total"].sum().reset_index().sort_values("Total", ascending=False).head(8)
                graf_forn = alt.Chart(df_forn).mark_bar(color="#1e3a29").encode(
                    x=alt.X("Total:Q", title="Valor Total (R$)"),
                    y=alt.Y("Fornecedor:N", sort="-x", title="Fornecedor"),
                    tooltip=[alt.Tooltip("Fornecedor:N"), alt.Tooltip("Total:Q", format=",.2f")]
                ).properties(height=340)
                st.altair_chart(graf_forn, use_container_width=True)

        # Quadro 3: Listagem Completa de Todos os Itens Adquiridos no Ano (com Quantidades)
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-top: 24px; margin-bottom: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="border-bottom: 2px solid #1e3a29; padding-bottom: 10px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 800; color: #1e3a29; text-transform: uppercase; letter-spacing: 0.5px;">
                    3. Listagem Geral de Todos os Itens Adquiridos no Ano ({total_itens_cadastrados} itens • {total_qtd_unidades} unidades)
                </h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not df_itens_ano.empty:
            filtro_busca_item = st.text_input("🔍 Filtrar itens do relatório anual por nome, fornecedor ou pregão:", placeholder="Digite para filtrar itens...", key="busca_itens_relatorio_anual")
            
            df_itens_filtrado = df_itens_ano.copy()
            if filtro_busca_item.strip():
                termo = filtro_busca_item.strip().lower()
                df_itens_filtrado = df_itens_filtrado[
                    df_itens_filtrado["Nome"].astype(str).str.lower().str.contains(termo) |
                    df_itens_filtrado["Fornecedor"].astype(str).str.lower().str.contains(termo) |
                    df_itens_filtrado["NC"].astype(str).str.lower().str.contains(termo) |
                    df_itens_filtrado["Pregão"].astype(str).str.lower().str.contains(termo)
                ]

            df_itens_exibir = df_itens_filtrado.copy()
            df_itens_exibir["Valor Unitário (R$)"] = df_itens_exibir["Valor Unitário"].apply(lambda x: f"R$ {x:,.2f}")
            df_itens_exibir["Total (R$)"] = df_itens_exibir["Total"].apply(lambda x: f"R$ {x:,.2f}")
            
            colunas_itens_view = ["Item", "NC", "ND", "Subitem", "Nome", "Qtd", "Valor Unitário (R$)", "Total (R$)", "Situação", "Fornecedor", "CNPJ", "Pregão", "Ata"]
            if "Seção" in df_itens_exibir.columns and tipo_perfil == "Fiscal":
                colunas_itens_view.insert(2, "Seção")
            
            st.dataframe(df_itens_exibir[colunas_itens_view], use_container_width=True, hide_index=True)

            # Totalizador de quantidades e valores
            qtd_filtrada = int(df_itens_filtrado["Qtd"].sum())
            total_filtrado = float(df_itens_filtrado["Total"].sum())
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; gap: 24px; background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 12px 20px; margin-top: 10px; margin-bottom: 20px;">
                <div><span style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total de Itens:</span> <span style="font-size: 16px; font-weight: 800; color: #0f172a;">{len(df_itens_filtrado)} itens</span></div>
                <div><span style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total de Quantidades (Unidades):</span> <span style="font-size: 16px; font-weight: 800; color: #0f172a;">{qtd_filtrada:,} unid.</span></div>
                <div><span style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase;">Valor Total Financeiro:</span> <span style="font-size: 16px; font-weight: 800; color: #1e3a29;">R$ {total_filtrado:,.2f}</span></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Nenhum item adquirido foi lançado para o exercício selecionado.")

        # Quadro 4: Termo de Encerramento e Assinaturas Oficiais
        config_req_atual = banco_dados.get("CONFIG_REQUISICAO", {}) if isinstance(banco_dados, dict) else {}
        nome_chefe = config_req_atual.get("assinatura_nome", "Chefe da Seção")
        funcao_chefe = config_req_atual.get("assinatura_funcao", f"Chefe da {secao_ativa}")
        nome_od = config_req_atual.get("od_nome", "Ordenador de Despesas")
        funcao_od = config_req_atual.get("od_funcao", "Ordenador de Despesas")

        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 30px; margin-top: 25px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="text-align: center; margin-bottom: 40px;">
                <p style="font-size: 13px; color: #475569; margin: 0;">Certifico que as informações financeiras e a listagem de materiais/serviços acima consolidados refletem fielmente a execução dos créditos orçamentários do Exercício {ano_selecionado}.</p>
                <p style="font-size: 12px; color: #64748b; margin-top: 6px;">Quartel em {config_req_atual.get('cidade_om', 'Sede da OM')}, em {data_hora_emissao}.</p>
            </div>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 40px; margin-top: 50px;">
                <div style="text-align: center; min-width: 250px;">
                    <div style="border-top: 1.5px solid #0f172a; width: 260px; margin: 0 auto 8px auto;"></div>
                    <div style="font-weight: 700; font-size: 13px; color: #0f172a;">{nome_chefe}</div>
                    <div style="font-size: 11px; color: #64748b;">{funcao_chefe}</div>
                </div>
                <div style="text-align: center; min-width: 250px;">
                    <div style="border-top: 1.5px solid #0f172a; width: 260px; margin: 0 auto 8px auto;"></div>
                    <div style="font-weight: 700; font-size: 13px; color: #0f172a;">{nome_od}</div>
                    <div style="font-size: 11px; color: #64748b;">{funcao_od}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

    # =========================================================================
    # PAINEL GERAL (CARDS, GRÁFICOS E TABELAS EXECUTIVAS)
    # =========================================================================
    if not df_itens_ano.empty or not df_ncs_ano.empty:
        # Cards de Indicadores
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Concedido em NCs", f"R$ {total_recebido_ano:,.2f}", f"{len(df_ncs_ano)} NCs ativas")
        with c2:
            st.metric("Total Empenhado / Requisitado", f"R$ {total_empenhado_ano:,.2f}", f"{total_itens_cadastrados} itens lançados")
        with c3:
            st.metric("Saldo Remanescente", f"R$ {saldo_ano:,.2f}", f"{pct_exec:.1f}% executado", delta_color="normal" if saldo_ano >= 0 else "inverse")
        with c4:
            st.metric("Unidades Físicas Adquiridas", f"{total_qtd_unidades:,}", f"{total_itens_cadastrados} descrições distintas")

        st.markdown("---")

        # Gráfico por Natureza de Despesa
        st.markdown("#### 📊 Distribuição Orçamentária por Natureza de Despesa (ND)")
        df_agrupado = df_itens_ano.groupby(["ND", "Situação"])["Total"].sum().reset_index()
        
        escala_cores = alt.Scale(domain=["Recebido", "Planejamento", "Aguardando entrega"], range=["#28a745", "#007bff", "#dc3545"])
        grafico_anual = alt.Chart(df_agrupado).mark_bar().encode(
            x=alt.X("ND:N", title="Natureza de Despesa (ND)"),
            y=alt.Y("Total:Q", title="Total (R$)"),
            color=alt.Color("Situação:N", scale=escala_cores, title="Status do Recurso"),
            tooltip=[alt.Tooltip("ND:N"), alt.Tooltip("Situação:N"), alt.Tooltip("Total:Q", format=",.2f")]
        ).properties(height=380)
        st.altair_chart(grafico_anual, use_container_width=True)

        # Tabela consolidada de Notas de Crédito
        st.markdown("#### 📑 Notas de Crédito do Exercício")
        if not df_ncs_ano.empty:
            df_nc_tab = df_ncs_ano.copy()
            df_nc_tab["% Exec."] = df_nc_tab.apply(lambda r: f"{(r['Total Empenhado'] / r['Valor Recebido'] * 100):.1f}%" if r["Valor Recebido"] > 0 else "0.0%", axis=1)
            df_nc_tab["Valor Recebido"] = df_nc_tab["Valor Recebido"].apply(lambda x: f"R$ {x:,.2f}")
            df_nc_tab["Total Empenhado"] = df_nc_tab["Total Empenhado"].apply(lambda x: f"R$ {x:,.2f}")
            df_nc_tab["Saldo"] = df_nc_tab["Saldo"].apply(lambda x: f"R$ {x:,.2f}")
            cols_show = ["NC", "ND", "PI", "Qtd Itens", "Valor Recebido", "Total Empenhado", "Saldo", "% Exec."]
            if tipo_perfil == "Fiscal" and "Seção" in df_nc_tab.columns:
                cols_show.insert(1, "Seção")
            st.dataframe(df_nc_tab[cols_show], use_container_width=True, hide_index=True)

        # Listagem Completa de Itens Adquiridos no Ano
        st.markdown(f"#### 📦 Todos os Itens Adquiridos no Ano ({total_itens_cadastrados} itens • {total_qtd_unidades} unidades)")
        filtro_item_painel = st.text_input("Filtrar itens adquiridos (nome, fornecedor, CNPJ, ata):", key="busca_itens_painel_global")
        
        df_itens_view_painel = df_itens_ano.copy()
        if filtro_item_painel.strip():
            t = filtro_item_painel.strip().lower()
            df_itens_view_painel = df_itens_view_painel[
                df_itens_view_painel["Nome"].astype(str).str.lower().str.contains(t) |
                df_itens_view_painel["Fornecedor"].astype(str).str.lower().str.contains(t) |
                df_itens_view_painel["NC"].astype(str).str.lower().str.contains(t)
            ]

        df_itens_view_painel["Valor Unitário"] = df_itens_view_painel["Valor Unitário"].apply(lambda x: f"R$ {x:,.2f}")
        df_itens_view_painel["Total"] = df_itens_view_painel["Total"].apply(lambda x: f"R$ {x:,.2f}")
        
        cols_it_show = ["Item", "NC", "ND", "Subitem", "Nome", "Qtd", "Valor Unitário", "Total", "Situação", "Fornecedor", "Pregão", "Ata"]
        if tipo_perfil == "Fiscal" and "Seção" in df_itens_view_painel.columns:
            cols_it_show.insert(2, "Seção")
        
        st.dataframe(df_itens_view_painel[cols_it_show], use_container_width=True, hide_index=True)
    else:
        st.info(f"Nenhum item ou Nota de Crédito registrados para exibição no exercício {ano_selecionado}.")

# =====================================================================
# ABA 4: CONSULTA DE PREGÕES & IMPORTAÇÃO DIRETA PARA NOTA DE CRÉDITO
# =====================================================================
with tab_consulta_pregoes:
    st.subheader("🔎 Consulta de Pregões no SIASGnet e Contratos.gov.br")
    st.caption("Consulte os pregões da UASG, veja saldos reais de empenho e **importe itens diretamente para suas Notas de Crédito** em 1 clique!")

    col_u1, col_u2, col_u3 = st.columns([2, 3, 2])
    with col_u1:
        uasg_busca = st.text_input("Código da UASG:", value="160001", max_chars=6, key="input_uasg_pregoes")
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
                    itens_existentes = st.session_state['itens_carregados_pregoes'].get(chave_p, [])
                    btn_rotulo = f"🔄 Recarregar Itens ({len(itens_existentes)} carregados)" if itens_existentes else "🔍 Carregar Itens e Saldos Reais"
                    btn_itens_p = st.button(btn_rotulo, key=f"btn_it_{chave_p}", type="primary" if not itens_existentes else "secondary")
                with c_p2:
                    st.markdown(f"[📋 Acessar no Contratos.gov.br]({row_p['Link Contratos']})")

                if btn_itens_p:
                    with st.spinner("Varrendo itens e apurando saldos no Contratos.gov.br (processamento acelerado)..."):
                        itens_det = buscar_itens_com_saldo_real(st.session_state.get('uasg_pesquisada', uasg_busca), row_p['Nº Compra'], row_p['Ano Compra'])
                        if itens_det:
                            st.session_state['itens_carregados_pregoes'][chave_p] = itens_det
                            st.rerun()

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

                            ncs_do_ano = [k for k in banco_dados.keys() if k != "CONFIG_REQUISICAO" and extrair_ano(k) == ano_selecionado]
                            ncs_disponiveis = sorted(ncs_do_ano) if ncs_do_ano else sorted([k for k in banco_dados.keys() if k != "CONFIG_REQUISICAO"])
                            
                            if not ncs_disponiveis:
                                st.warning("⚠️ Você ainda não tem nenhuma Nota de Crédito cadastrada. Cadastre uma NC na aba '1. Cadastrar e Lançar Compras' antes de importar itens.")
                            else:
                                idx_nc_ini = 0
                                nc_ativa_ctx = st.session_state.get("vis_item_select_nc", "")
                                if nc_ativa_ctx in ncs_disponiveis:
                                    idx_nc_ini = ncs_disponiveis.index(nc_ativa_ctx)
                                
                                nc_destino = st.selectbox(
                                    "🎯 Selecione a Nota de Crédito (NC) de Destino para este Item:",
                                    ncs_disponiveis,
                                    index=idx_nc_ini,
                                    key=f"sel_nc_dest_{chave_p}_{item_alvo['Item']}"
                                )
                                nd_dest = banco_dados.get(nc_destino, {}).get("nd", "") if nc_destino in banco_dados else ""
                                pi_dest = banco_dados.get(nc_destino, {}).get("pi", "") if nc_destino in banco_dados else ""
                                st.caption(f"📌 **Destino Selecionado:** `{nc_destino}` | **ND:** `{nd_dest or 'Não informada'}` | **PI:** `{pi_dest or 'Não informado'}`")

                                with st.form(f"form_importar_item_{chave_p}_{item_alvo['Item']}_{nc_destino}"):
                                    st.markdown(f"**Item Selecionado:** `{item_alvo['Item']}` - {item_alvo['Descrição']}")
                                    st.markdown(f"• **Fornecedor Identificado:** `{item_alvo['Fornecedor']}`")
                                    st.markdown(f"• **Ata Vinculada:** `{item_alvo['Ata Vinculada']}` | **Pregão:** `{row_p['Nº da Licitação']}`")

                                    c_imp1, c_imp2, c_imp3 = st.columns(3)
                                    with c_imp1:
                                        st.text_input("NC de Destino (Confirmada):", value=nc_destino, disabled=True)
                                    with c_imp2:
                                        saldo_num = int(converter_para_float(item_alvo.get("Saldo p/ Empenho", "0")))
                                        if saldo_num <= 0:
                                            st.caption("⚠️ Item com Saldo 0 (Totalmente Empenhado)")
                                            qtd_para_importar = st.number_input("Quantidade a Empenhar / Comprar:", min_value=0, value=0, step=1)
                                        else:
                                            qtd_para_importar = st.number_input("Quantidade a Empenhar / Comprar:", min_value=1, value=saldo_num, step=1)
                                    with c_imp3:
                                        v_sug = float(item_alvo.get("Valor Unitario Sugerido", 0.0))
                                        valor_unit_imp = st.number_input("Valor Unitário (R$):", min_value=0.0, value=v_sug, step=0.01)

                                    sugestao_ia_imp = _cache_classificacao_ia.get(f"{nd_dest}_{item_alvo.get('Descrição', '').strip().lower()}")
                                    opcoes_sub_imp, idx_sub_imp, mapa_sub_imp = montar_opcoes_subitem(
                                        nd_dest, 
                                        item_alvo.get("Descrição", ""),
                                        sugestao_ia=sugestao_ia_imp
                                    )

                                    c_imp4, c_imp5, c_imp6 = st.columns(3)
                                    with c_imp4:
                                        sub_sel_imp = st.selectbox(
                                            "Sub Item Correspondente (da Função da ND):",
                                            opcoes_sub_imp,
                                            index=idx_sub_imp,
                                            help=f"Correspondências identificadas na FUNÇÃO oficial do SIAFI da ND {nd_dest}. Você pode escolher qualquer opção da lista.",
                                            key=f"sel_sub_imp_{chave_p}_{item_alvo['Item']}"
                                        )
                                        if sub_sel_imp == "✏️ Digitar outro código manualmente...":
                                            subitem_imp_final = st.text_input("Código do Subitem (2 dígitos):", max_chars=2, key=f"sub_man_{chave_p}_{item_alvo['Item']}").strip()
                                        else:
                                            subitem_imp_final = mapa_sub_imp.get(sub_sel_imp, extrair_codigo_subitem(sub_sel_imp))
                                    with c_imp5:
                                        sit_imp = st.selectbox("Situação Inicial:", ["Planejamento", "Aguardando entrega", "Recebido"])
                                    with c_imp6:
                                        pdf_link = item_alvo.get("PDF da Ata")
                                        if pdf_link:
                                            st.markdown(f"[📥 Visualizar Ata Original (PDF)]({pdf_link})")

                                    func_imp_txt = obter_funcao_subitem(nd_dest, subitem_imp_final)
                                    if func_imp_txt:
                                        st.caption(f"📖 **Função do Subitem {subitem_imp_final}:** {func_imp_txt}")

                                    btn_confirmar_import = st.form_submit_button("🚀 Confirmar Importação deste Item para a NC", type="primary", use_container_width=True)

                                    if btn_confirmar_import:
                                        if tipo_perfil == "Fiscal":
                                            st.error("O perfil de Fiscal não possui permissão para incluir itens.")
                                        else:
                                            cnpj_puro = item_alvo.get("CNPJ Puro", "")
                                            forn_puro = item_alvo.get("Fornecedor Puro", "")
                                            
                                            if cnpj_puro and (not forn_puro or forn_puro == cnpj_puro or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", forn_puro)) == 0):
                                                nome_rec = consultar_razao_social_cnpj(cnpj_puro)
                                                if nome_rec:
                                                    forn_puro = nome_rec
                                            
                                            if not forn_puro:
                                                forn_puro = item_alvo.get("Fornecedor", "NÃO INFORMADO")

                                            sub_final_imp = subitem_imp_final if subitem_imp_final else determinar_subitem(nd_dest, item_alvo.get("Descrição", ""))

                                            novo_item_nc = {
                                                "_uid": f"it_{nc_destino}_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                                                "Item": int(item_alvo["Item"]) if str(item_alvo["Item"]).isdigit() else 1,
                                                "Subitem": sub_final_imp,
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
                                                if "itens" not in banco_dados[nc_destino]:
                                                    banco_dados[nc_destino]["itens"] = []
                                                banco_dados[nc_destino]["itens"].append(novo_item_nc)
                                                salvar_dados(banco_dados)
                                                st.session_state.banco = banco_dados
                                                st.session_state["vis_item_select_nc"] = nc_destino
                                                st.success(f"🎉 Item nº {item_alvo['Item']} importado com sucesso para a NC **{nc_destino}** com valor de R$ {valor_unit_imp:,.2f}!")
                                                st.toast(f"Item {item_alvo['Item']} adicionado à NC {nc_destino}!")
                                                st.rerun()
                    else:
                        st.warning("Nenhum item localizado no pregão.")

# =====================================================================
# ABA 5: GERENCIAR ACESSOS E EQUIPE
# =====================================================================
with tab_acessos:
    if tipo_perfil == "Operador":
        st.warning("⚠️ **Acesso Restrito:** O seu perfil de Operador não tem permissão para gerenciar usuários ou transferir perfis.")
    else:
        st.subheader("👥 Gestão de Acessos, Equipe e Transferência de Funções")
        
        # Recupera usuários do Supabase de acordo com a hierarquia
        if tipo_perfil == "Chefe":
            st.info(f"👑 **Painel do Chefe de Seção ({secao_user}):** Você visualiza os integrantes da sua seção, pode cadastrar novos Operadores e transferir a Chefia da Seção.")
            resp_membros = supabase.table("usuarios").select("id, nome, perfil, secao, om").eq("om", om_user).eq("secao", secao_user).execute()
        else:
            st.info(f"🛡️ **Painel do Fiscal da OM ({om_user}):** Você tem visão corporativa completa de todas as seções, pode cadastrar Chefes/Operadores e transferir a função de Fiscal Administrativo.")
            resp_membros = supabase.table("usuarios").select("id, nome, perfil, secao, om").eq("om", om_user).execute()
        
        membros_raw = resp_membros.data if resp_membros.data else []
        
        # Abas internas para organização exemplar
        aba_equipe_vis, aba_transferir, aba_cadastrar_user = st.tabs([
            "📋 Integrantes Cadastrados",
            "🔄 Transferência de Perfil / Função",
            "➕ Cadastrar Novo Militar"
        ])
        
        # -------------------------------------------------------------
        # 1. INTEGRANTES CADASTRADOS (VISUALIZAÇÃO DE SUBORDINADOS)
        # -------------------------------------------------------------
        with aba_equipe_vis:
            st.markdown("#### 📋 Militares Cadastrados na sua Esfera de Gestão")
            
            if tipo_perfil == "Fiscal":
                secoes_encontradas = sorted(list(set([m["secao"] for m in membros_raw if m.get("secao")])))
                col_f_sec, col_f_busca = st.columns([1, 2])
                with col_f_sec:
                    filtro_sec_view = st.selectbox("Filtrar por Seção:", ["Todas as Seções"] + secoes_encontradas)
                with col_f_busca:
                    termo_busca_user = st.text_input("Buscar por Nome ou Login:", placeholder="Digite para filtrar...").strip().lower()
                
                membros_filtrados = [
                    m for m in membros_raw 
                    if (filtro_sec_view == "Todas as Seções" or m.get("secao") == filtro_sec_view)
                    and (not termo_busca_user or termo_busca_user in (m.get("nome") or "").lower() or termo_busca_user in (m.get("id") or "").lower())
                ]
            else:
                termo_busca_user = st.text_input("Buscar militar na seção:", placeholder="Digite o nome ou login...").strip().lower()
                membros_filtrados = [
                    m for m in membros_raw 
                    if not termo_busca_user or termo_busca_user in (m.get("nome") or "").lower() or termo_busca_user in (m.get("id") or "").lower()
                ]
            
            # Métricas da equipe
            total_integrantes = len(membros_filtrados)
            qtd_chefes = len([m for m in membros_filtrados if m.get("perfil") == "Chefe"])
            qtd_operadores = len([m for m in membros_filtrados if m.get("perfil") == "Operador"])
            qtd_fiscais = len([m for m in membros_filtrados if m.get("perfil") == "Fiscal"])
            
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            with m_c1:
                st.metric("Total de Integrantes", total_integrantes)
            with m_c2:
                st.metric("Chefes de Seção", qtd_chefes)
            with m_c3:
                st.metric("Operadores", qtd_operadores)
            with m_c4:
                st.metric("Fiscais", qtd_fiscais)
                
            st.write("")
            
            if membros_filtrados:
                dados_tabela_equipe = []
                for m in membros_filtrados:
                    eh_voce = " (Você)" if m["id"] == usuario_atual else ""
                    dados_tabela_equipe.append({
                        "Login / ID": m.get("id"),
                        "Nome / Posto": m.get("nome"),
                        "Perfil": m.get("perfil"),
                        "Seção": m.get("secao"),
                        "Situação": f"Ativo{eh_voce}"
                    })
                df_equipe = pd.DataFrame(dados_tabela_equipe)
                st.dataframe(df_equipe, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum militar localizado com os filtros informados.")

            st.write("")
            st.markdown("##### 🗑️ Excluir Operador")
            if tipo_perfil == "Chefe":
                ops_disponiveis_del = [m for m in membros_raw if m.get("secao") == secao_user and m.get("perfil") == "Operador" and m.get("id") != usuario_atual]
            else:
                ops_disponiveis_del = [m for m in membros_raw if m.get("perfil") == "Operador" and m.get("id") != usuario_atual]

            if not ops_disponiveis_del:
                st.caption("ℹ️ Nenhum operador disponível para exclusão nesta seção/OM.")
            else:
                with st.expander("🗑️ Excluir Operador do Sistema", expanded=False):
                    st.caption("Remova permanentemente o acesso de um Operador à sua seção/OM.")
                    mapa_del = {
                        f"{op.get('nome')} (login: {op.get('id')}) — Seção: {op.get('secao')}": op 
                        for op in ops_disponiveis_del
                    }
                    sel_del_label = st.selectbox("Selecione o Operador para remover:", list(mapa_del.keys()), key="sel_op_para_excluir")
                    op_del_obj = mapa_del[sel_del_label]
                    
                    st.warning(f"Atenção: O operador **{op_del_obj.get('nome')}** (login: `{op_del_obj.get('id')}`) perderá totalmente o acesso ao sistema.")
                    conf_del = st.checkbox(
                        f"Declaro que confirmo a exclusão definitiva do operador {op_del_obj.get('nome')}.", 
                        key=f"chk_del_{op_del_obj.get('id')}"
                    )
                    
                    if st.button("🗑️ Excluir Operador Definitivamente", type="secondary", key=f"btn_del_{op_del_obj.get('id')}"):
                        if not conf_del:
                            st.error("Marque a caixa de confirmação para autorizar a exclusão.")
                        else:
                            try:
                                supabase.table("usuarios").delete().eq("id", op_del_obj["id"]).execute()
                                st.success(f"Operador **{op_del_obj.get('nome')}** excluído com sucesso!")
                                st.toast("Operador excluído com sucesso!")
                                st.rerun()
                            except Exception as e_del:
                                st.error(f"Erro ao excluir operador: {e_del}")

        # -------------------------------------------------------------
        # 2. TRANSFERÊNCIA DE PERFIL / FUNÇÃO (PASSAGEM DE COMANDO/CHEFIA)
        # -------------------------------------------------------------
        with aba_transferir:
            st.markdown("#### 🔄 Passagem e Transferência de Função")
            
            if tipo_perfil == "Chefe":
                st.markdown(f"""
                Você está conectado como **Chefe da Seção {secao_user}**.  
                Neste painel, você pode transferir a Chefia da Seção para um dos **Operadores** cadastrados na sua seção.  
                **Atenção às regras:**
                - O Operador selecionado será promovido a **Chefe** da Seção **{secao_user}**.
                - O seu usuário atual (`{usuario_atual}`) continuará acessando normalmente o sistema, mas passará a ter o perfil de **Operador**.
                """)
                
                operadores_secao = [
                    m for m in membros_raw 
                    if m.get("secao") == secao_user and m.get("perfil") == "Operador" and m.get("id") != usuario_atual
                ]
                
                if not operadores_secao:
                    st.warning(f"⚠️ Não há nenhum **Operador** cadastrado na seção **{secao_user}** para o qual transferir a chefia. Cadastre um operador na aba 'Cadastrar Novo Militar' antes de realizar a transferência.")
                else:
                    mapa_op_chefe = {
                        f"{op['nome']} (login: {op['id']})": op
                        for op in operadores_secao
                    }
                    
                    op_sel_label = st.selectbox(
                        "Selecione o militar para assumir a Chefia da Seção:",
                        list(mapa_op_chefe.keys()),
                        key="sel_transf_chefe_box"
                    )
                    candidato_chefe = mapa_op_chefe[op_sel_label]
                    
                    st.info(f"O militar **{candidato_chefe['nome']}** passará a ser o novo Chefe da Seção {secao_user}.")
                    confirma_chefe = st.checkbox(
                        f"Declaro que estou ciente da passagem da Chefia para {candidato_chefe['nome']} e que meu perfil passará a ser Operador.",
                        key=f"chk_transf_chefe_{candidato_chefe['id']}"
                    )
                    
                    btn_transf_chefe = st.button("🔄 Confirmar Transferência de Chefia", type="primary", use_container_width=True, key="btn_transf_chefia_act")
                    if btn_transf_chefe:
                        if not confirma_chefe:
                            st.error("Você deve marcar a caixa de confirmação para efetivar a transferência.")
                        else:
                            try:
                                # Promove o operador a Chefe
                                supabase.table("usuarios").update({"perfil": "Chefe"}).eq("id", candidato_chefe["id"]).execute()
                                # Atualiza o perfil do chefe atual para Operador
                                supabase.table("usuarios").update({"perfil": "Operador"}).eq("id", usuario_atual).execute()
                                
                                st.success(f"🎉 Chefia da Seção {secao_user} transferida com sucesso para {candidato_chefe['nome']}! Seu perfil foi alterado para Operador.")
                                st.toast("Transferência concluída com sucesso!")
                                st.rerun()
                            except Exception as e_transf:
                                st.error(f"Erro ao processar transferência: {e_transf}")
            
            elif tipo_perfil == "Fiscal":
                st.markdown(f"""
                Você está conectado como **Fiscal Administrativo Geral do {om_user}**.  
                Neste painel, você pode transferir a função de Fiscal da OM para qualquer outro militar cadastrado na OM (seja ele Chefe ou Operador de qualquer seção).  
                **Atenção às regras:**
                - O militar selecionado assumirá o perfil de **Fiscal** geral da OM **{om_user}**.
                - O seu perfil atual passará a ser **Chefe** da sua seção (`{secao_user}`).
                """)
                
                outros_militares_om = [
                    m for m in membros_raw 
                    if m.get("id") != usuario_atual
                ]
                
                if not outros_militares_om:
                    st.warning(f"⚠️ Não há outros militares cadastrados no **{om_user}**. Cadastre novos militares antes de transferir a função de Fiscal.")
                else:
                    mapa_mil_fiscal = {
                        f"{m['nome']} — Seção: {m['secao']} (Perfil atual: {m['perfil']}) [login: {m['id']}]": m
                        for m in outros_militares_om
                    }
                    
                    m_sel_label = st.selectbox(
                        "Selecione o militar para assumir a função de Fiscal da OM:",
                        list(mapa_mil_fiscal.keys()),
                        key="sel_transf_fiscal_box"
                    )
                    candidato_fiscal = mapa_mil_fiscal[m_sel_label]
                    
                    perfil_destino_antigo = st.selectbox(
                        "Definir o seu novo perfil após a transferência:",
                        ["Chefe", "Operador"],
                        help="Qual perfil você passará a ter na sua seção.",
                        key="sel_perfil_antigo_fiscal_box"
                    )
                    
                    st.info(f"O militar **{candidato_fiscal['nome']}** ({candidato_fiscal['secao']}) passará a ser o novo Fiscal da OM. Seu perfil será alterado para **{perfil_destino_antigo}** da seção {secao_user}.")
                    confirma_fiscal = st.checkbox(
                        f"Declaro que estou ciente da transferência da função de Fiscal da OM para {candidato_fiscal['nome']}.",
                        key=f"chk_transf_fisc_{candidato_fiscal['id']}"
                    )
                    
                    btn_transf_fiscal = st.button("🔄 Confirmar Transferência de Fiscal da OM", type="primary", use_container_width=True, key="btn_transf_fiscal_act")
                    if btn_transf_fiscal:
                        if not confirma_fiscal:
                            st.error("Você deve marcar a caixa de confirmação para efetivar a transferência.")
                        else:
                            try:
                                # Promove o militar selecionado a Fiscal
                                supabase.table("usuarios").update({"perfil": "Fiscal"}).eq("id", candidato_fiscal["id"]).execute()
                                # Atualiza o fiscal atual para Chefe ou Operador
                                supabase.table("usuarios").update({"perfil": perfil_destino_antigo}).eq("id", usuario_atual).execute()
                                
                                st.success(f"🎉 Função de Fiscal da OM transferida com sucesso para {candidato_fiscal['nome']}! Seu perfil foi atualizado para {perfil_destino_antigo}.")
                                st.toast("Transferência de Fiscal concluída com sucesso!")
                                st.rerun()
                            except Exception as e_fisc:
                                st.error(f"Erro ao processar transferência de Fiscal: {e_fisc}")


        # -------------------------------------------------------------
        # 3. CADASTRAR NOVO MILITAR NA EQUIPE
        # -------------------------------------------------------------
        with aba_cadastrar_user:
            st.markdown("#### ➕ Cadastro de Novo Integrante")
            if tipo_perfil == "Chefe":
                st.info(f"Como **Chefe**, você cadastra novos **Operadores** diretamente para a seção **{secao_user}**.")
                opcoes_perfil_novo = ["Operador"]
                secoes_permitidas = [secao_user]
            else:
                st.info(f"Como **Fiscal**, você pode cadastrar **Chefes** e **Operadores** para qualquer seção do **{om_user}**.")
                opcoes_perfil_novo = ["Chefe", "Operador"]
                
                resp_secoes_gerais = supabase.table("usuarios").select("secao").eq("om", om_user).execute()
                secoes_permitidas = sorted(list(set([r["secao"] for r in resp_secoes_gerais.data if r.get("secao")])))
                if not secoes_permitidas:
                    secoes_permitidas = [secao_user]
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
                            st.toast("Militar cadastrado com sucesso!")
                            st.rerun()
