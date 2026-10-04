import https from 'https';
import * as cheerio from 'cheerio';
import { scrapeContratosItens, ItemContratos } from './contratosScraper';

const agent = new https.Agent({ rejectUnauthorized: false });

const SIASG_BASE = 'https://www2.comprasnet.gov.br/siasgnet-atasrp/public';
const URL_PESQUISA_SIASG = `${SIASG_BASE}/pesquisarLicitacaoSRP.do`;
const URL_ITENS_SIASG = `${SIASG_BASE}/pesquisarItemSRP.do`;
const BASE_CONTRATOS = 'https://contratos.sistema.gov.br';

const HEADERS_HTTP = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
};

function fetchWithAgent(url: string, options: any = {}): Promise<Response> {
  return (fetch as any)(url, { ...options, agent });
}

export function converterParaFloat(valStr: string | number | undefined | null): number {
  if (valStr === undefined || valStr === null) return 0;
  if (typeof valStr === 'number') return isNaN(valStr) ? 0 : valStr;
  let s = String(valStr).trim();
  s = s.replace(/[^\d,.-]/g, '');
  if (!s) return 0;
  if (s.includes(',') && s.includes('.')) {
    if (s.indexOf('.') < s.indexOf(',')) {
      s = s.replace(/\./g, '').replace(',', '.');
    } else {
      s = s.replace(/,/g, '');
    }
  } else if (s.includes(',')) {
    s = s.replace(',', '.');
  }
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

export function formatarCnpj(val: string | undefined | null): string {
  if (!val) return '';
  const limpo = val.replace(/\D/g, '');
  if (limpo.length === 14) {
    return limpo.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
  }
  if (limpo.length === 11) {
    return limpo.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }
  return val;
}

export function fmtQtd(val: number): string {
  if (val === Math.floor(val)) {
    return String(Math.floor(val));
  }
  return String(parseFloat(val.toFixed(4)));
}

export function limparDescricaoAta(texto: string): string {
  if (!texto) return '';
  let t = texto.replace(/\xa0/g, ' ').trim();
  const divisores = [
    /código do item/i, /codigo do item/i,
    /tipo do item/i, /tipo de item/i,
    /unidade de fornecimento/i, /unidade de medida/i, /unidade de compra/i,
    /critério de julgamento/i, /criterio de julgamento/i,
    /critério de valor/i, /criterio de valor/i,
    /situação/i, /situacao/i,
    /vigência inicial/i, /vigencia inicial/i,
    /vigência final/i, /vigencia final/i,
    /quantidade solicitada/i, /quantidade homologada/i, /quantidade registrada/i,
    /quantidade total/i, /quantidade máxima/i, /quantidade/i,
    /valor estimado/i, /valor homologado/i, /valor unitário/i, /valor unitario/i,
    /valor total/i, /saldo para empenho/i, /saldo a empenhar/i, /saldo empenho/i,
    /classificação cnpj/i, /classificação/i, /classificacao/i,
    /cnpj/i, /fornecedor/i, /razão social/i, /razao social/i,
    /marca\/fabricante/i, /marca/i, /fabricante/i, /modelo/i, /versão/i, /versao/i
  ];
  for (const div of divisores) {
    const match = t.match(div);
    if (match && match.index !== undefined && match.index > 5) {
      t = t.substring(0, match.index);
    }
  }
  t = t.replace(/^(especificação|especificacao|descrição detalhada|descrição do item|descrição|descricao|especificação técnica|objeto)\s*[:\-]\s*/i, '');
  t = t.replace(/^\d{4,8}\s*[-–]\s*/, '');
  t = t.replace(/^(item\s*)?\d{1,4}\s*[-–:]\s*/i, '');
  return t.replace(/\s+/g, ' ').trim().replace(/^[,;:\-\s]+|[,;:\-\s]+$/g, '');
}

export interface PregaoSIASG {
  uasg: string;
  modalidade: string;
  numero_licitacao: string;
  ano: string;
  objeto: string;
  numero_compra: string;
  ano_compra: string;
  codigo_licitacao: string;
  link_contratos: string;
}

export interface ItemPregaoSIASG {
  Item: string;
  Tipo: string;
  Descrição: string;
  Unidade: string;
  'Qtd Registrada': string;
  'Qtd Empenhada': string;
  'Saldo p/ Empenho': string;
  'Ata Vinculada': string;
  Fornecedor: string;
  'Fornecedor Puro'?: string;
  'CNPJ Puro'?: string;
  'Valor Unitario Sugerido'?: number;
  'Valor Unitário'?: number;
  'PDF da Ata': string;
  Deserto?: boolean;
  empenhos?: Array<{
    numero: string;
    unidade: string;
    fornecedor?: string;
    data?: string;
    quantidade: number;
    valor?: number;
  }>;
  'Link Olhinho'?: string;
}

// Cache em memória para acelerar requisições repetidas
const cachePregoes = new Map<string, { data: PregaoSIASG[]; exp: number }>();
const cacheItens = new Map<string, { data: ItemPregaoSIASG[]; exp: number }>();

/**
 * Consulta lista de pregões por UASG e anos no SIASGnet
 */
export async function consultarPregoes(uasg: string, anos: string[]): Promise<PregaoSIASG[]> {
  const uasgLimpa = uasg.trim();
  if (!uasgLimpa) return [];

  const cacheKey = `${uasgLimpa}_${anos.sort().join('-')}`;
  const emCache = cachePregoes.get(cacheKey);
  if (emCache && emCache.exp > Date.now()) {
    return emCache.data;
  }

  const todosPregoes: PregaoSIASG[] = [];

  // Inicia sessão para obter cookies do SIASGnet
  let cookieHeader = '';
  try {
    const initRes = await fetchWithAgent(`${URL_PESQUISA_SIASG}?method=iniciar`, {
      headers: HEADERS_HTTP
    });
    const setCookie = initRes.headers.get('set-cookie');
    if (setCookie) {
      cookieHeader = setCookie.split(',').map(c => c.split(';')[0]).join('; ');
    }
  } catch (e) {
    console.warn('Aviso ao iniciar sessão SIASGnet:', e);
  }

  for (const ano of anos) {
    const anoStr = String(ano).trim();
    if (!anoStr) continue;

    try {
      const params = new URLSearchParams();
      params.append('method', 'pesquisar');
      params.append('parametro.uasg.numeroUasg', uasgLimpa);
      params.append('parametro.codigosModalidadeCompra', '5'); // Pregão
      params.append('parametro.anoLicitacao', anoStr);

      const headers: Record<string, string> = {
        ...HEADERS_HTTP,
        'Content-Type': 'application/x-www-form-urlencoded'
      };
      if (cookieHeader) {
        headers['Cookie'] = cookieHeader;
      }

      const postRes = await fetchWithAgent(URL_PESQUISA_SIASG, {
        method: 'POST',
        headers,
        body: params.toString()
      });

      if (!postRes.ok) {
        console.warn(`Status ${postRes.status} ao consultar ano ${anoStr}`);
        continue;
      }

      const html = await postRes.text();
      const $ = cheerio.load(html);

      const tabela = $('#licitacao, table.dados');
      if (!tabela.length) continue;

      tabela.find('tr').slice(1).each((_, tr) => {
        const tds = $(tr).find('td');
        if (tds.length < 5) return;

        const uasgRow = $(tds[0]).text().trim();
        if ((uasgRow || '').toLowerCase().includes('nenhum')) return;

        const modalidade = $(tds[1]).text().trim();
        const numLicitacao = $(tds[2]).text().trim();
        const objeto = $(tds[3]).text().trim();

        const linkTag = $(tds[4]).find('a');
        const jsCode = linkTag.attr('href') || '';

        const match = jsCode.match(/selecionarLicitacao\s*\(\s*['"]?(\d+)['"]?\s*,\s*['"]?(\d+)['"]?\s*,\s*['"]?(\d+)['"]?\s*,\s*['"]?(\d+)['"]?\s*,\s*(\d+)/);

        let numCompra = '';
        let anoCompra = anoStr;
        let codLicitacao = '';

        if (match) {
          numCompra = match[3];
          anoCompra = match[4];
          codLicitacao = match[5];
        } else if (numLicitacao.includes('/')) {
          const parts = numLicitacao.split('/');
          numCompra = parts[0].replace(/^0+/, '') || parts[0];
          anoCompra = parts[1];
        }

        todosPregoes.push({
          uasg: uasgRow,
          modalidade,
          numero_licitacao: numLicitacao,
          ano: anoCompra,
          objeto,
          numero_compra: numCompra,
          ano_compra: anoCompra,
          codigo_licitacao: codLicitacao,
          link_contratos: `${BASE_CONTRATOS}/transparencia/arp?numeroCompra=${numCompra}&anoCompra=${anoCompra}`
        });
      });
    } catch (err) {
      console.error(`Erro ao consultar pregoes do ano ${anoStr}:`, err);
    }
  }

  // Deduplicar
  const vistos = new Set<string>();
  const pregoesUnicos: PregaoSIASG[] = [];
  for (const p of todosPregoes) {
    const k = `${p.uasg}_${p.numero_licitacao}`;
    if (!vistos.has(k)) {
      vistos.add(k);
      pregoesUnicos.push(p);
    }
  }

  cachePregoes.set(cacheKey, { data: pregoesUnicos, exp: Date.now() + 1000 * 60 * 30 }); // 30 min
  return pregoesUnicos;
}

/**
 * Consulta itens, saldos e valores unitários de um pregão no SIASGnet e Dados Abertos Compras.gov.br
 * Garante fidelidade máxima dos dados: valor unitário, fornecedor real, CNPJ, quantidade registrada,
 * quantidade empenhada e saldo para empenho. Identifica itens desertos/fracassados.
 */
export async function consultarItensPregao(
  uasg: string,
  numCompra: string,
  anoCompra: string
): Promise<ItemPregaoSIASG[]> {
  const uasgLimpa = uasg.trim();
  const numLimpo = numCompra.trim();
  const anoLimpo = anoCompra.trim();

  const cacheKey = `${uasgLimpa}_${numLimpo}_${anoLimpo}`;
  const emCache = cacheItens.get(cacheKey);
  if (emCache && emCache.exp > Date.now()) {
    return emCache.data;
  }

  interface RawSiasgItem {
    num: string;
    tipo: string;
    desc: string;
    qtd: string;
    unid: string;
  }

  const siasgItems: RawSiasgItem[] = [];
  const vistos = new Set<string>();

  const parseTabelaItens = (htmlText: string) => {
    const $ = cheerio.load(htmlText);
    const tabela = $('#item, table.dados');
    if (!tabela.length) return 1;

    tabela.find('tr').slice(1).each((_, tr) => {
      const tds = $(tr).find('td');
      if (tds.length >= 5) {
        const itemNum = $(tds[0]).text().trim();
        const tipo = $(tds[1]).text().trim();
        const desc = limparDescricaoAta($(tds[2]).text().trim());
        const qtdReg = $(tds[3]).text().trim();
        const unid = $(tds[4]).text().trim();

        if (itemNum && !vistos.has(itemNum)) {
          vistos.add(itemNum);
          siasgItems.push({
            num: itemNum,
            tipo,
            desc,
            qtd: qtdReg,
            unid
          });
        }
      }
    });

    const pags: number[] = [];
    const regex = /numeroPagina=(\d+)/g;
    let m;
    while ((m = regex.exec(htmlText)) !== null) {
      pags.push(Number(m[1]));
    }
    return pags.length > 0 ? Math.max(...pags) : 1;
  };

  // 1. Carrega todas as páginas de itens no SIASGnet
  try {
    const urlItens = `${URL_ITENS_SIASG}?method=iniciar&parametro.identificacaoCompra.numeroUasg=${uasgLimpa}&parametro.identificacaoCompra.modalidadeCompra=5&parametro.identificacaoCompra.numeroCompra=${numLimpo}&parametro.identificacaoCompra.anoCompra=${anoLimpo}`;

    const res = await fetchWithAgent(urlItens, {
      headers: HEADERS_HTTP
    });

    if (res.ok) {
      const html = await res.text();
      const maxPags = parseTabelaItens(html);

      // Busca as próximas páginas (2, 3...)
      for (let p = 2; p <= maxPags; p++) {
        const urlP = `${URL_ITENS_SIASG}?parametro.identificacaoCompra.anoCompra=${anoLimpo}&numeroPagina=${p}&parametro.identificacaoCompra.numeroUasg=${uasgLimpa}&parametro.identificacaoCompra.modalidadeCompra=5&method=consultarPorFiltro&parametro.identificacaoCompra.numeroCompra=${numLimpo}`;
        const resP = await fetchWithAgent(urlP, { headers: HEADERS_HTTP });
        if (resP.ok) {
          parseTabelaItens(await resP.text());
        }
      }
    }
  } catch (err) {
    console.error('Erro ao consultar páginas de itens no SIASGnet:', err);
  }

  // 1.5. Consulta dados reais de empenhos e atas no Contratos.gov.br (Transparência)
  let contratosMap = new Map<number, ItemContratos>();
  try {
    contratosMap = await scrapeContratosItens(uasgLimpa, numLimpo, anoLimpo);
  } catch (errContratos) {
    console.warn('Aviso ao consultar Contratos.gov.br:', errContratos);
  }

  // 2. Consulta itens homologados na API oficial de Dados Abertos do Compras.gov.br (apenas para o ano e número exatos)
  interface ArpItemOficial {
    numeroItem: string;
    descricaoItem: string;
    tipoItem?: string;
    quantidadeHomologadaItem: number;
    quantidadeHomologadaVencedor?: number;
    quantidadeEmpenhada: number;
    valorUnitario: number;
    valorTotal?: number;
    niFornecedor: string;
    nomeRazaoSocialFornecedor: string;
    numeroAtaRegistroPreco: string;
    numeroControlePncpAta?: string;
    linkAtaPNCP?: string;
    linkCompraPNCP?: string;
  }

  const arpItensMap = new Map<number, ArpItemOficial>();
  const numLimpoDigitos = numLimpo.replace(/\D/g, '');
  const anoNum = parseInt(anoLimpo.replace(/\D/g, ''), 10) || 2025;

  try {
    const ini = `${anoNum}-01-01`;
    const fim = `${anoNum}-12-31`;
    const url = `https://dadosabertos.compras.gov.br/modulo-arp/2_consultarARPItem?codigoUnidadeGerenciadora=${uasgLimpa}&dataVigenciaInicialMin=${ini}&dataVigenciaInicialMax=${fim}&numeroCompra=${numLimpoDigitos}&pagina=1&tamanhoPagina=100`;
    const res = await fetchWithAgent(url, { headers: HEADERS_HTTP, signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      const data = await res.json();
      if (data.resultado && Array.isArray(data.resultado) && data.resultado.length > 0) {
        const addItems = (arr: any[]) => {
          for (const it of arr) {
            const numIt = parseInt(it.numeroItem, 10);
            if (!isNaN(numIt)) {
              const existente = arpItensMap.get(numIt);
              if (!existente || (!existente.valorUnitario && it.valorUnitario)) {
                arpItensMap.set(numIt, {
                  numeroItem: String(numIt),
                  descricaoItem: it.descricaoItem || '',
                  tipoItem: it.tipoItem || 'Material',
                  quantidadeHomologadaItem: it.quantidadeHomologadaItem ?? it.quantidadeHomologadaVencedor ?? 0,
                  quantidadeHomologadaVencedor: it.quantidadeHomologadaVencedor,
                  quantidadeEmpenhada: it.quantidadeEmpenhada ?? 0,
                  valorUnitario: it.valorUnitario ?? 0,
                  valorTotal: it.valorTotal ?? 0,
                  niFornecedor: it.niFornecedor || '',
                  nomeRazaoSocialFornecedor: it.nomeRazaoSocialFornecedor || '',
                  numeroAtaRegistroPreco: it.numeroAtaRegistroPreco || '',
                  numeroControlePncpAta: it.numeroControlePncpAta || '',
                  linkAtaPNCP: it.linkAtaPNCP || (it.numeroControlePncpAta ? `https://pncp.gov.br/app/atas/${it.numeroControlePncpAta}` : ''),
                  linkCompraPNCP: it.linkCompraPNCP || ''
                });
              }
            }
          }
        };

        addItems(data.resultado);

        const total = data.totalRegistros || 0;
        const totalPags = Math.ceil(total / 100);
        if (totalPags > 1) {
          const paginasPromises = [];
          for (let p = 2; p <= totalPags; p++) {
            const urlP = `https://dadosabertos.compras.gov.br/modulo-arp/2_consultarARPItem?codigoUnidadeGerenciadora=${uasgLimpa}&dataVigenciaInicialMin=${ini}&dataVigenciaInicialMax=${fim}&numeroCompra=${numLimpoDigitos}&pagina=${p}&tamanhoPagina=100`;
            paginasPromises.push(
              fetchWithAgent(urlP, { headers: HEADERS_HTTP, signal: AbortSignal.timeout(8000) })
                .then(r => r.ok ? r.json() : null)
                .then(d => { if (d?.resultado) addItems(d.resultado); })
                .catch(() => {})
            );
          }
          await Promise.all(paginasPromises);
        }
      }
    }
  } catch (errApi) {
    console.warn('Aviso ao consultar API de Dados Abertos do Compras.gov.br:', errApi);
  }

  // 3. Monta lista final cruzando Contratos.gov.br (Transparência), SIASGnet e Dados Abertos
  const itensResultado: ItemPregaoSIASG[] = [];
  const itensProcessados = new Set<number>();

  for (const it of siasgItems) {
    const numInt = parseInt(it.num, 10);
    itensProcessados.add(numInt);
    const itemContratos = contratosMap.get(numInt);
    const arpOficial = arpItensMap.get(numInt);

    if (itemContratos && (itemContratos.qtdRegistrada > 0 || itemContratos.valorUnitario > 0 || itemContratos.numeroAta)) {
      // DADOS REAIS DO PORTAL CONTRATOS.GOV.BR (TRANSPARÊNCIA) COM QUANTIDADE EMPENHADA E SALDO VERDADEIROS
      const regFinal = itemContratos.qtdRegistrada > 0 
        ? itemContratos.qtdRegistrada 
        : (converterParaFloat(it.qtd) || 0);
      const empFinal = itemContratos.qtdEmpenhada;
      const salFinal = itemContratos.saldoEmpenho !== undefined 
        ? itemContratos.saldoEmpenho 
        : Math.max(0, regFinal - empFinal);

      const fornNome = itemContratos.fornecedor || arpOficial?.nomeRazaoSocialFornecedor || '';
      const cnpjFormatado = itemContratos.cnpj 
        ? formatarCnpj(itemContratos.cnpj) 
        : (arpOficial?.niFornecedor ? formatarCnpj(arpOficial.niFornecedor) : '');
      const fornDisplay = fornNome && cnpjFormatado 
        ? `${fornNome} (${cnpjFormatado})` 
        : (fornNome || cnpjFormatado || 'Fornecedor Registrado');

      const vUnit = itemContratos.valorUnitario > 0 
        ? itemContratos.valorUnitario 
        : (arpOficial?.valorUnitario || 0);

      itensResultado.push({
        Item: it.num,
        Tipo: it.tipo || arpOficial?.tipoItem || 'Material',
        Descrição: it.desc || arpOficial?.descricaoItem || `Item ${it.num}`,
        Unidade: it.unid || 'UN',
        'Qtd Registrada': fmtQtd(regFinal),
        'Qtd Empenhada': fmtQtd(empFinal),
        'Saldo p/ Empenho': fmtQtd(salFinal),
        'Ata Vinculada': itemContratos.numeroAta || arpOficial?.numeroAtaRegistroPreco || '-',
        Fornecedor: fornDisplay,
        'Fornecedor Puro': fornNome,
        'CNPJ Puro': cnpjFormatado,
        'Valor Unitario Sugerido': vUnit,
        'Valor Unitário': vUnit,
        'PDF da Ata': itemContratos.pdfUrl || arpOficial?.linkAtaPNCP || '',
        Deserto: false,
        'Link Olhinho': itemContratos.linkOlhinho || `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpoDigitos}&anoCompra=${anoNum}`,
        empenhos: itemContratos.empenhos || []
      });
    } else if (arpOficial && arpOficial.valorUnitario > 0) {
      // ITEM HOMOLOGADO NA API OFICIAL
      const regFinal = arpOficial.quantidadeHomologadaItem > 0 
        ? arpOficial.quantidadeHomologadaItem 
        : (converterParaFloat(it.qtd) || 0);
      const empFinal = arpOficial.quantidadeEmpenhada || 0;
      const salFinal = Math.max(0, regFinal - empFinal);

      const cnpjFormatado = formatarCnpj(arpOficial.niFornecedor);
      const fornNome = arpOficial.nomeRazaoSocialFornecedor;
      const fornDisplay = fornNome && cnpjFormatado 
        ? `${fornNome} (${cnpjFormatado})` 
        : (fornNome || cnpjFormatado || 'Fornecedor Registrado');

      const ataNum = arpOficial.numeroAtaRegistroPreco || '-';
      const linkAta = arpOficial.linkAtaPNCP || '';
      const linkOlhinho = `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpoDigitos}&anoCompra=${anoNum}`;

      itensResultado.push({
        Item: it.num,
        Tipo: it.tipo || arpOficial.tipoItem || 'Material',
        Descrição: it.desc || arpOficial.descricaoItem,
        Unidade: it.unid || 'UN',
        'Qtd Registrada': fmtQtd(regFinal),
        'Qtd Empenhada': fmtQtd(empFinal),
        'Saldo p/ Empenho': fmtQtd(salFinal),
        'Ata Vinculada': ataNum,
        Fornecedor: fornDisplay,
        'Fornecedor Puro': fornNome,
        'CNPJ Puro': cnpjFormatado,
        'Valor Unitario Sugerido': arpOficial.valorUnitario,
        'Valor Unitário': arpOficial.valorUnitario,
        'PDF da Ata': linkAta,
        Deserto: false,
        'Link Olhinho': linkOlhinho
      });
    } else {
      // ITEM DESERTO / FRACASSADO (SEM FORNECEDOR VENCEDOR OU SEM ATA HOMOLOGADA)
      itensResultado.push({
        Item: it.num,
        Tipo: it.tipo || 'Material',
        Descrição: it.desc,
        Unidade: it.unid || 'UN',
        'Qtd Registrada': it.qtd || '0',
        'Qtd Empenhada': '0',
        'Saldo p/ Empenho': '0',
        'Ata Vinculada': '-',
        Fornecedor: 'Deserto / Fracassado',
        'Fornecedor Puro': 'Deserto / Fracassado',
        'CNPJ Puro': '',
        'Valor Unitario Sugerido': 0,
        'Valor Unitário': 0,
        'PDF da Ata': '',
        Deserto: true,
        'Link Olhinho': `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpoDigitos}&anoCompra=${anoNum}`
      });
    }
  }

  // Se houver algum item no Contratos.gov.br que não estava nas páginas do SIASGnet
  contratosMap.forEach((itemContratos, numInt) => {
    if (!itensProcessados.has(numInt) && (itemContratos.qtdRegistrada > 0 || itemContratos.numeroAta)) {
      itensProcessados.add(numInt);
      const regFinal = itemContratos.qtdRegistrada;
      const empFinal = itemContratos.qtdEmpenhada;
      const salFinal = itemContratos.saldoEmpenho !== undefined 
        ? itemContratos.saldoEmpenho 
        : Math.max(0, regFinal - empFinal);

      const fornNome = itemContratos.fornecedor || '';
      const cnpjFormatado = itemContratos.cnpj ? formatarCnpj(itemContratos.cnpj) : '';
      const fornDisplay = fornNome && cnpjFormatado 
        ? `${fornNome} (${cnpjFormatado})` 
        : (fornNome || cnpjFormatado || 'Fornecedor Registrado');

      itensResultado.push({
        Item: String(numInt),
        Tipo: 'Material',
        Descrição: `Item ${numInt}`,
        Unidade: 'UN',
        'Qtd Registrada': fmtQtd(regFinal),
        'Qtd Empenhada': fmtQtd(empFinal),
        'Saldo p/ Empenho': fmtQtd(salFinal),
        'Ata Vinculada': itemContratos.numeroAta || '-',
        Fornecedor: fornDisplay,
        'Fornecedor Puro': fornNome,
        'CNPJ Puro': cnpjFormatado,
        'Valor Unitario Sugerido': itemContratos.valorUnitario || 0,
        'Valor Unitário': itemContratos.valorUnitario || 0,
        'PDF da Ata': itemContratos.pdfUrl || '',
        Deserto: false,
        'Link Olhinho': itemContratos.linkOlhinho || `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpoDigitos}&anoCompra=${anoNum}`,
        empenhos: itemContratos.empenhos || []
      });
    }
  });

  // Se houver algum item homologado na API oficial que não estava nem no SIASGnet nem Contratos
  arpItensMap.forEach((arpOficial, numInt) => {
    if (!itensProcessados.has(numInt) && arpOficial.valorUnitario > 0) {
      itensProcessados.add(numInt);
      const cnpjFormatado = formatarCnpj(arpOficial.niFornecedor);
      const fornNome = arpOficial.nomeRazaoSocialFornecedor;
      const fornDisplay = fornNome && cnpjFormatado 
        ? `${fornNome} (${cnpjFormatado})` 
        : (fornNome || cnpjFormatado || 'Fornecedor Registrado');

      const salFinal = Math.max(0, (arpOficial.quantidadeHomologadaItem || 0) - (arpOficial.quantidadeEmpenhada || 0));

      itensResultado.push({
        Item: String(numInt),
        Tipo: arpOficial.tipoItem || 'Material',
        Descrição: arpOficial.descricaoItem || `Item ${numInt}`,
        Unidade: 'UN',
        'Qtd Registrada': fmtQtd(arpOficial.quantidadeHomologadaItem),
        'Qtd Empenhada': fmtQtd(arpOficial.quantidadeEmpenhada),
        'Saldo p/ Empenho': fmtQtd(salFinal),
        'Ata Vinculada': arpOficial.numeroAtaRegistroPreco || '-',
        Fornecedor: fornDisplay,
        'Fornecedor Puro': fornNome,
        'CNPJ Puro': cnpjFormatado,
        'Valor Unitario Sugerido': arpOficial.valorUnitario,
        'Valor Unitário': arpOficial.valorUnitario,
        'PDF da Ata': arpOficial.linkAtaPNCP || '',
        Deserto: false,
        'Link Olhinho': `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpoDigitos}&anoCompra=${anoNum}`
      });
    }
  });

  // Ordena itens numericamente
  itensResultado.sort((a, b) => {
    const na = parseInt(a.Item, 10);
    const nb = parseInt(b.Item, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.Item.localeCompare(b.Item);
  });

  cacheItens.set(cacheKey, { data: itensResultado, exp: Date.now() + 1000 * 60 * 60 }); // 1 hora de cache
  return itensResultado;
}
