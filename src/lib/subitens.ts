import catalogoData from '../data/catalogo_subitens.json';
import { SubitemCatalogoItem, SubitemCorrespondencia } from '../types';

export const CATALOGO_SUBITENS: Record<string, SubitemCatalogoItem[]> = catalogoData as Record<string, SubitemCatalogoItem[]>;

const STOPWORDS_SUBITEM = new Set([
  'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'para', 'pra', 'com',
  'sem', 'por', 'e', 'ou', 'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'sob',
  'sobre', 'item', 'marca', 'tipo', 'modelo', 'unidade', 'und', 'un', 'cx', 'pct',
  'peca', 'pecas', 'kg', 'mm', 'cm', 'm', 'lt', 'l', 'ml', 'cor', 'tamanho', 'padrao',
  'conf', 'conforme', 'especificacao', 'edital', 'objeto', 'aquisicao', 'fornecimento', 'valor'
]);

export function normalizarTexto(texto: string): string {
  if (!texto) return '';
  return texto
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9\s]/g, ' ')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

export function extrairPalavrasChave(texto: string): string[] {
  const norm = normalizarTexto(texto);
  return norm
    .split(' ')
    .filter(p => p.length >= 3 && !STOPWORDS_SUBITEM.has(p));
}

export function extrairCodigoSubitem(opcaoTexto: string): string {
  if (!opcaoTexto) return '';
  const m = String(opcaoTexto).match(/\b(\d{2})\b/);
  return m ? m[1] : '';
}

export function identificarGrupoND(nd: string): string {
  if (!nd) return '339030';
  const limpa = String(nd).replace(/\D/g, '');
  for (const g of ['339030', '449052', '339039']) {
    if (limpa.includes(g)) return g;
  }
  if (limpa.includes('30') && (limpa.includes('3390') || limpa.includes('9030'))) return '339030';
  if (limpa.includes('52') && (limpa.includes('4490') || limpa.includes('9052'))) return '449052';
  if (limpa.includes('39') && (limpa.includes('3390') || limpa.includes('9039'))) return '339039';
  return '339030';
}

export function buscarCorrespondenciasSubitens(nd: string, descricaoItem: string): SubitemCorrespondencia[] {
  if (!descricaoItem || !descricaoItem.trim()) return [];

  let grupo = identificarGrupoND(nd);
  if (!CATALOGO_SUBITENS[grupo]) {
    const descNorm = normalizarTexto(descricaoItem);
    if (['armario', 'cadeira', 'mesa', 'computador', 'notebook', 'estante', 'servidor'].some(w => descNorm.includes(w))) {
      grupo = '449052';
    } else if (['servico', 'manutencao preventiva', 'reparo em', 'locacao'].some(w => descNorm.includes(w))) {
      grupo = '339039';
    } else {
      grupo = '339030';
    }
  }

  const descNorm = normalizarTexto(descricaoItem);
  let palavrasDesc = extrairPalavrasChave(descricaoItem);
  if (palavrasDesc.length === 0) {
    palavrasDesc = descNorm.split(' ').filter(p => p.length >= 2);
  }

  const correspondencias: SubitemCorrespondencia[] = [];
  const listaSubitens = CATALOGO_SUBITENS[grupo] || [];

  for (const item of listaSubitens) {
    const funcaoNorm = normalizarTexto(item.funcao || '');
    const nomeNorm = normalizarTexto(item.nome || '');
    const keywordsNorm = (item.keywords || []).map(k => normalizarTexto(k));

    let score = 0;
    const termosCoincidentes: string[] = [];

    // 1. Frase inteira
    if (descNorm.length > 4) {
      if (funcaoNorm.includes(descNorm)) {
        score += 35;
        termosCoincidentes.push(descricaoItem.slice(0, 35));
      } else if (nomeNorm.includes(descNorm)) {
        score += 30;
        termosCoincidentes.push(descricaoItem.slice(0, 30));
      }
    }

    // 2. N-grams (pares consecutivos)
    const tokens = descNorm.split(' ');
    for (let i = 0; i < tokens.length - 1; i++) {
      const par = `${tokens[i]} ${tokens[i + 1]}`;
      if (par.length >= 6 && (!STOPWORDS_SUBITEM.has(tokens[i]) || !STOPWORDS_SUBITEM.has(tokens[i + 1]))) {
        if (funcaoNorm.includes(par)) {
          score += 18;
          if (!termosCoincidentes.includes(par)) termosCoincidentes.push(par);
        } else if (nomeNorm.includes(par)) {
          score += 15;
          if (!termosCoincidentes.includes(par)) termosCoincidentes.push(par);
        }
      }
    }

    // 3. Palavras individuais na FUNÇÃO
    for (const p of palavrasDesc) {
      const regexPalavra = new RegExp(`\\b${p}\\b`, 'i');
      if (regexPalavra.test(funcaoNorm)) {
        score += 8;
        if (!termosCoincidentes.includes(p)) termosCoincidentes.push(p);
      } else if (funcaoNorm.includes(p)) {
        score += 4;
        if (!termosCoincidentes.includes(p)) termosCoincidentes.push(p);
      }

      // Palavra no NOME
      if (regexPalavra.test(nomeNorm)) {
        score += 7;
        if (!termosCoincidentes.includes(p)) termosCoincidentes.push(p);
      }

      // Palavra nas keywords
      for (const kw of keywordsNorm) {
        if (p === kw || (p.length >= 4 && kw.includes(p))) {
          score += 6;
          if (!termosCoincidentes.includes(p)) termosCoincidentes.push(p);
          break;
        }
      }
    }

    if (score > 0) {
      correspondencias.push({
        subitem: item.subitem,
        nd_completa: item.nd_completa,
        nome: item.nome,
        funcao: item.funcao || '',
        score,
        termos: termosCoincidentes
      });
    }
  }

  correspondencias.sort((a, b) => b.score - a.score);
  return correspondencias;
}

export function determinarSubitem(nd: string, descricaoItem: string): string {
  const corrs = buscarCorrespondenciasSubitens(nd, descricaoItem);
  return corrs.length > 0 ? corrs[0].subitem : '';
}

export function obterNomeSubitem(nd: string, subitem: string): string {
  if (!subitem) return '';
  const grupo = identificarGrupoND(nd);
  const lista = CATALOGO_SUBITENS[grupo] || [];
  const subBusca = String(subitem).trim().padStart(2, '0');
  const found = lista.find(s => s.subitem === subBusca);
  return found ? found.nome : '';
}

export function obterFuncaoSubitem(nd: string, subitem: string): string {
  if (!subitem) return '';
  const grupo = identificarGrupoND(nd);
  const lista = CATALOGO_SUBITENS[grupo] || [];
  const subBusca = String(subitem).trim().padStart(2, '0');
  const found = lista.find(s => s.subitem === subBusca);
  return found ? found.funcao : '';
}

export function listarSubitensPorND(nd: string): SubitemCatalogoItem[] {
  const grupo = identificarGrupoND(nd);
  return CATALOGO_SUBITENS[grupo] || [];
}

export interface OpcaoSelectSubitem {
  label: string;
  codigo: string;
  isMatch: boolean;
  termos?: string[];
  funcao?: string;
  nome: string;
}

export function montarOpcoesSubitem(nd: string, descricaoItem: string, subitemAtual: string = ''): {
  opcoes: OpcaoSelectSubitem[];
  defaultCodigo: string;
} {
  const correspondencias = buscarCorrespondenciasSubitens(nd, descricaoItem);
  const todosSubitens = listarSubitensPorND(nd);

  const opcoes: OpcaoSelectSubitem[] = [];
  const subitensIncluidos = new Set<string>();

  // 1. Correspondências na função
  for (const c of correspondencias) {
    const termosStr = c.termos.slice(0, 3).join(', ');
    const label = termosStr
      ? `🎯 ${c.subitem} - ${c.nome} [Função: ${termosStr}]`
      : `🎯 ${c.subitem} - ${c.nome}`;

    opcoes.push({
      label,
      codigo: c.subitem,
      isMatch: true,
      termos: c.termos,
      funcao: c.funcao,
      nome: c.nome
    });
    subitensIncluidos.add(c.subitem);
  }

  // 2. Outros subitens da ND
  for (const s of todosSubitens) {
    if (!subitensIncluidos.has(s.subitem)) {
      opcoes.push({
        label: `📋 ${s.subitem} - ${s.nome}`,
        codigo: s.subitem,
        isMatch: false,
        funcao: s.funcao,
        nome: s.nome
      });
      subitensIncluidos.add(s.subitem);
    }
  }

  // Determinar código padrão
  let defaultCodigo = '';
  if (subitemAtual) {
    defaultCodigo = String(subitemAtual).trim().padStart(2, '0');
  } else if (correspondencias.length > 0) {
    defaultCodigo = correspondencias[0].subitem;
  }

  return { opcoes, defaultCodigo };
}
