import * as cheerio from 'cheerio';
import https from 'https';

const agent = new https.Agent({ rejectUnauthorized: false });

export interface EmpenhoContratos {
  numero: string;
  unidade: string;
  fornecedor?: string;
  data?: string;
  quantidade: number;
  valor?: number;
}

export interface SolicitacaoAdesaoContratos {
  unidade: string;
  data: string;
  quantidade: number;
}

export interface ItemContratos {
  itemNum: number;
  numeroItemRaw: string;
  arpId: string;
  numeroAta: string;
  pdfUrl: string;
  linkOlhinho: string;
  fornecedor: string;
  cnpj: string;
  valorUnitario: number;
  qtdRegistrada: number;
  qtdEmpenhada: number;
  saldoEmpenho: number;
  qtdLimiteAdesao?: number;
  saldoAdesao?: number;
  qtdAprovadaAdesao?: number;
  aceitaAdesao?: string;
  solicitacoesAdesao?: SolicitacaoAdesaoContratos[];
  empenhos: EmpenhoContratos[];
}

const cacheContratos = new Map<string, { data: Map<number, ItemContratos>; exp: number }>();

async function fetchWithTimeout(url: string, timeoutMs = 12000): Promise<Response> {
  return (fetch as any)(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    },
    agent,
    signal: AbortSignal.timeout(timeoutMs)
  });
}

function parseNumeroBR(valStr: string | number | undefined | null): number {
  if (valStr === undefined || valStr === null) return 0;
  if (typeof valStr === 'number') return isNaN(valStr) ? 0 : valStr;
  let s = String(valStr).trim().replace('R$', '').trim();
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

/**
 * Realiza o scrape no Contratos.gov.br (transparência de ARPs)
 * Seguindo o fluxo exato:
 * 1. Filtra pelo pregão no Contratos.gov.br
 * 2. Identifica todas as Atas vinculadas (arpshow)
 * 3. Abre cada ata para obter o link direto de download do PDF e os itens
 * 4. Clica no 'olhinho' de cada item para extrair fornecedor, valor unitário,
 *    quantidade registrada, quantidade empenhada da UASG e lista de empenhos.
 */
export async function scrapeContratosItens(
  uasg: string,
  numCompra: string,
  anoCompra: string
): Promise<Map<number, ItemContratos>> {
  const uasgLimpa = uasg.trim();
  const numLimpo = numCompra.replace(/\D/g, '');
  const anoLimpo = anoCompra.replace(/\D/g, '');

  const cacheKey = `${uasgLimpa}_${numLimpo}_${anoLimpo}`;
  const emCache = cacheContratos.get(cacheKey);
  if (emCache && emCache.exp > Date.now()) {
    return emCache.data;
  }

  const itensMap = new Map<number, ItemContratos>();

  try {
    // 1. Obter ID interno da UASG no Contratos.gov.br
    let uId = '';
    try {
      const uRes = await fetchWithTimeout(`https://contratos.sistema.gov.br/arp/ajax-unidade-options?q=${uasgLimpa}`, 6000);
      if (uRes.ok) {
        const uData = await uRes.json();
        if (Array.isArray(uData) && uData[0]?.id) {
          uId = String(uData[0].id);
        }
      }
    } catch (e) {
      console.warn('Aviso ao consultar ID da UASG no Contratos.gov.br:', e);
    }

    // 2. Buscar atas apenas com o numeroCompra exato e anoCompra exato
    const situacoes = ['vigente', 'nao_vigente'];
    const arpIds = new Set<string>();

    // Consultar páginas de listagem de atas para as situações vigentes e não vigentes
    const urlsConsultaListagem: string[] = [];
    for (const sit of situacoes) {
      let baseUrl = `https://contratos.sistema.gov.br/transparencia/arp?numeroCompra=${numLimpo}&anoCompra=${anoLimpo}&situacao=${sit}`;
      if (uId) {
        baseUrl += `&unidadesGerenciadoras%5B%5D=${uId}`;
      }
      urlsConsultaListagem.push(`${baseUrl}&page=1`);
    }

    // Executa as consultas de página 1 em paralelo
    const resultadosListagem = await Promise.all(
      urlsConsultaListagem.map(async (url) => {
        try {
          const res = await fetchWithTimeout(url, 8000);
          if (!res.ok) return { ids: [], extraPages: [] };
          const html = await res.text();
          const $ = cheerio.load(html);

          const ids: string[] = [];
          $('a[href*="/transparencia/arpshow/"]').each((_, a) => {
            const m = ($(a).attr('href') || '').match(/\/transparencia\/arpshow\/(\d+)\/show/);
            if (m) ids.push(m[1]);
          });

          const extraPages: string[] = [];
          $('a[href*="page="]').each((_, a) => {
            const m = ($(a).attr('href') || '').match(/page=(\d+)/);
            if (m && parseInt(m[1], 10) > 1) {
              const pNum = m[1];
              const pUrl = url.replace(/page=\d+/, `page=${pNum}`);
              if (!extraPages.includes(pUrl)) extraPages.push(pUrl);
            }
          });

          return { ids, extraPages };
        } catch (e) {
          return { ids: [], extraPages: [] };
        }
      })
    );

    for (const r of resultadosListagem) {
      r.ids.forEach(id => arpIds.add(id));
    }

    // Se houver páginas extras (ex: página 2), busca-as
    const todasPagsExtras = Array.from(new Set(resultadosListagem.flatMap(r => r.extraPages)));
    if (todasPagsExtras.length > 0) {
      const extraRes = await Promise.all(
        todasPagsExtras.map(async (url) => {
          try {
            const res = await fetchWithTimeout(url, 8000);
            if (!res.ok) return [];
            const html = await res.text();
            const $ = cheerio.load(html);
            const ids: string[] = [];
            $('a[href*="/transparencia/arpshow/"]').each((_, a) => {
              const m = ($(a).attr('href') || '').match(/\/transparencia\/arpshow\/(\d+)\/show/);
              if (m) ids.push(m[1]);
            });
            return ids;
          } catch (e) {
            return [];
          }
        })
      );
      extraRes.flat().forEach(id => arpIds.add(id));
    }

    console.log(`[Contratos.gov.br] Encontradas ${arpIds.size} atas para a compra ${numCompra}/${anoCompra} (UASG ${uasgLimpa})`);

    // 3. Para cada Ata, carregar a página principal e identificar itens e PDF
    interface ItemLinkInfo {
      arpId: string;
      itemNum: number;
      itemNumRaw: string;
      url: string;
      numeroAta: string;
      pdfUrl: string;
    }

    const todosItensParaBuscar: ItemLinkInfo[] = [];

    // Busca as páginas de Ata em paralelo (máximo 12 por vez)
    const arpIdList = Array.from(arpIds);
    const chunkArps: string[][] = [];
    for (let i = 0; i < arpIdList.length; i += 12) {
      chunkArps.push(arpIdList.slice(i, i + 12));
    }

    for (const chunk of chunkArps) {
      await Promise.all(
        chunk.map(async (arpId) => {
          try {
            const ataUrl = `https://contratos.sistema.gov.br/transparencia/arpshow/${arpId}/show`;
            const resAta = await fetchWithTimeout(ataUrl, 8000);
            if (!resAta.ok) return;
            const htmlAta = await resAta.text();
            const $ata = cheerio.load(htmlAta);

            // Validação de segurança: verificar se a ata pertence à compra e UASG solicitadas
            let pertence = false;
            $ata('*').each((_, el) => {
              const t = $ata(el).text();
              if (t.includes(`${numLimpo}/${anoLimpo}`) && t.includes(uasgLimpa)) pertence = true;
            });
            if (!pertence && $ata('*').text().includes(numLimpo)) pertence = true;
            if (!pertence) return;

            // Obter Número da Ata
            let numeroAta = '';
            $ata('*').each((_, el) => {
              const t = $ata(el).text().trim();
              const m = t.match(/Número da ata de registro de preços:\s*(\d{5}\/\d{4})/i) ||
                        t.match(/Ata\s+n[ºo°]?\s*(\d{5}\/\d{4})/i);
              if (m && !numeroAta) {
                numeroAta = m[1];
              }
            });
            if (!numeroAta) {
              numeroAta = `Ata ${arpId}`;
            }

            // Obter link direto de download do PDF da ata
            let pdfUrl = '';
            $ata('a[href]').each((_, el) => {
              const h = $ata(el).attr('href') || '';
              if (h.includes('/storage/arp/') || (h.toLowerCase().endsWith('.pdf') && !h.toLowerCase().includes('manual'))) {
                pdfUrl = h.startsWith('http') ? h : `https://contratos.sistema.gov.br${h}`;
              }
            });

            // Encontrar links do "olhinho" dos itens desta ata
            $ata('a[href*="/transparencia/arpshow/itens/"]').each((_, el) => {
              const h = $ata(el).attr('href') || '';
              const m = h.match(/\/transparencia\/arpshow\/itens\/(\d+)\/(\d+)\/show/);
              if (m) {
                const itemNum = parseInt(m[1], 10);
                const itemNumRaw = m[1];
                const fullUrl = h.startsWith('http') ? h : `https://contratos.sistema.gov.br${h.trim()}`;
                todosItensParaBuscar.push({
                  arpId,
                  itemNum,
                  itemNumRaw,
                  url: fullUrl,
                  numeroAta,
                  pdfUrl
                });
              }
            });
          } catch (eAta) {
            console.warn(`Erro ao carregar ata ${arpId}:`, eAta);
          }
        })
      );
    }

    console.log(`[Contratos.gov.br] Total de ${todosItensParaBuscar.length} itens a detalhar via 'olhinho'`);

    // 4. Detalhar cada item clicando no 'olhinho' (com concorrência controlada de 14 por vez)
    const chunkItens: ItemLinkInfo[][] = [];
    for (let i = 0; i < todosItensParaBuscar.length; i += 14) {
      chunkItens.push(todosItensParaBuscar.slice(i, i + 14));
    }

    for (const chunk of chunkItens) {
      await Promise.all(
        chunk.map(async (itInfo) => {
          try {
            const resIt = await fetchWithTimeout(itInfo.url, 10000);
            if (!resIt.ok) return;
            const htmlIt = await resIt.text();
            const $it = cheerio.load(htmlIt);

            let fornecedor = '';
            let cnpj = '';
            let valorUnitario = 0;

            let uasgRegistrada = 0;
            let uasgEmpenhada = 0;
            let uasgSaldo = 0;
            let hasUasgRow = false;

            let totalRegistrada = 0;
            let totalEmpenhada = 0;
            let totalSaldo = 0;

            const empenhosMap = new Map<string, EmpenhoContratos>();

            $it('table').each((_, tbl) => {
              const ths = $it(tbl).find('th').map((_, th) => $it(th).text().trim().toLowerCase()).get();

              // Tabela de Fornecedor e Valor Unitário
              if (ths.some(h => h.includes('fornecedor')) && ths.some(h => h.includes('cnpj'))) {
                $it(tbl).find('tbody tr, tr').each((_, tr) => {
                  const tds = $it(tr).find('td');
                  if (tds.length >= 3) {
                    const cTxt = $it(tds[1]).text().trim();
                    const fTxt = $it(tds[2]).text().trim();
                    if (/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/.test(cTxt) && !cnpj) {
                      cnpj = cTxt;
                      fornecedor = fTxt;
                    }
                    tds.each((_, td) => {
                      const txt = $it(td).text().trim();
                      if (txt.includes('R$')) {
                        const val = parseNumeroBR(txt);
                        if (val > 0 && !valorUnitario) valorUnitario = val;
                      }
                    });
                  }
                });
              }

              // Tabela de Unidades (Quantidade Registrada, Empenhada e Saldo)
              if (ths.some(h => h.includes('unidade')) && ths.some(h => h.includes('empenhada')) && ths.some(h => h.includes('saldo'))) {
                $it(tbl).find('tbody > tr, tbody tr').each((_, tr) => {
                  const tds = $it(tr).children('td');
                  if (tds.length >= 5) {
                    const uText = $it(tds[0]).text().trim();
                    const tipoText = $it(tds[1]).text().trim().toLowerCase();
                    const rVal = parseNumeroBR($it(tds[2]).text().trim());
                    const eVal = parseNumeroBR($it(tds[3]).text().trim());
                    const sVal = parseNumeroBR($it(tds[4]).text().trim());

                    totalRegistrada += rVal;
                    totalEmpenhada += eVal;
                    totalSaldo += sVal;

                    if (uText.toLowerCase().includes(uasgLimpa.toLowerCase()) || tipoText.includes('gerenciadora')) {
                      hasUasgRow = true;
                      uasgRegistrada = rVal;
                      uasgEmpenhada = eVal;
                      uasgSaldo = sVal;
                    }
                  }
                });
              }

              // Tabela de Empenhos
              if (ths.some(h => h.includes('empenho')) && ths.some(h => h.includes('data'))) {
                $it(tbl).find('tbody > tr').each((_, tr) => {
                  const tds = $it(tr).children('td');
                  if (tds.length >= 6) {
                    const numNE = $it(tds[0]).text().trim();
                    const uNE = $it(tds[1]).text().trim();
                    const fornNE = $it(tds[2]).text().trim();
                    const dataNE = $it(tds[3]).text().trim();
                    const qtdNE = parseNumeroBR($it(tds[tds.length - 2]).text().trim());
                    const valNE = parseNumeroBR($it(tds[tds.length - 1]).text().trim());

                    if (/^\d{4}NE\d{6}$/i.test(numNE)) {
                      const k = `${numNE}_${dataNE}_${qtdNE}`;
                      if (!empenhosMap.has(k)) {
                        empenhosMap.set(k, {
                          numero: numNE,
                          unidade: uNE,
                          fornecedor: fornNE,
                          data: dataNE,
                          quantidade: qtdNE,
                          valor: valNE
                        });
                      }
                    }
                  }
                });
              }
            });

            // Extração da Aba Adesões (Carona)
            let qtdLimiteAdesao = 0;
            let saldoAdesao = 0;
            let qtdAprovadaAdesao = 0;
            let aceitaAdesao = 'Não';
            const solicitacoesAdesao: SolicitacaoAdesaoContratos[] = [];

            const textoCompletoIt = $it.text();
            const mAc = textoCompletoIt.match(/aceita\s*ades[aã]o\s*:\s*(sim|n[aã]o)/i);
            if (mAc) {
              aceitaAdesao = mAc[1].toLowerCase() === 'sim' ? 'Sim' : 'Não';
            }

            const mLim = textoCompletoIt.match(/(?:qtd\.?\s*limite\s*(?:informado\s*na\s*compra\s*)?(?:para)?\s*ades[aã]o|limite\s*para\s*ades[aã]o|quantidade\s*limite\s*para\s*ades[aã]o)\s*:\s*([\d\.,]+)/i);
            if (mLim) {
              qtdLimiteAdesao = parseNumeroBR(mLim[1]);
            }

            const mDisp = textoCompletoIt.match(/(?:quantidade\s*dispon[ií]vel\s*para\s*ades[aã]o|quantidade\s*disponivel\s*para\s*ades[aã]o|saldo\s*(?:dispon[ií]vel\s*)?(?:para|de)\s*ades[aã]o)\s*:\s*([\d\.,]+)/i);
            if (mDisp) {
              saldoAdesao = parseNumeroBR(mDisp[1]);
            }

            $it('table').each((_, tbl) => {
              const ths = $it(tbl).find('th').map((_, th) => $it(th).text().trim().toLowerCase()).get();
              if (ths.some(h => h.includes('quantidade aprovada') || h.includes('aprovação') || h.includes('aprovacao') || h.includes('solicitações aprovadas'))) {
                $it(tbl).find('tbody > tr, tr').each((_, tr) => {
                  const tds = $it(tr).find('td');
                  if (tds.length >= 2) {
                    const uSol = $it(tds[0]).text().trim();
                    const dtSol = tds.length >= 3 ? $it(tds[1]).text().trim() : '';
                    const qSol = parseNumeroBR($it(tds[tds.length - 1]).text().trim());
                    if (qSol > 0 && uSol && !uSol.toLowerCase().includes('unidade')) {
                      qtdAprovadaAdesao += qSol;
                      solicitacoesAdesao.push({
                        unidade: uSol,
                        data: dtSol,
                        quantidade: qSol
                      });
                    }
                  }
                });
              }
            });

            if (qtdLimiteAdesao > 0) {
              aceitaAdesao = 'Sim';
              if (saldoAdesao === 0) {
                saldoAdesao = Math.max(0, qtdLimiteAdesao - qtdAprovadaAdesao);
              }
            } else if (saldoAdesao > 0) {
              aceitaAdesao = 'Sim';
              qtdLimiteAdesao = saldoAdesao + qtdAprovadaAdesao;
            }

            const todosEmpenhos = Array.from(empenhosMap.values());
            const empenhosUasg = todosEmpenhos.filter(e => (e.unidade || '').toLowerCase().includes((uasgLimpa || '').toLowerCase()));

            // Se encontrou a linha da UASG com quantidade registrada > 0, usa ela
            let regFinal = uasgRegistrada;
            let empFinal = uasgEmpenhada;
            let salFinal = uasgSaldo;

            // Se não tinha linha específica da UASG ou se ela estava 0 mas há dados no total
            if (!hasUasgRow || regFinal === 0) {
              if (totalRegistrada > 0) {
                regFinal = totalRegistrada;
                empFinal = totalEmpenhada;
                salFinal = totalSaldo;
              }
            }

            // Garante consistência com os empenhos da UASG se calculados
            if (empenhosUasg.length > 0) {
              const somaQtdEmpenhosUasg = empenhosUasg.reduce((acc, e) => acc + e.quantidade, 0);
              if (somaQtdEmpenhosUasg > 0) {
                empFinal = somaQtdEmpenhosUasg;
                salFinal = Math.max(0, regFinal - empFinal);
              }
            }

            itensMap.set(itInfo.itemNum, {
              itemNum: itInfo.itemNum,
              numeroItemRaw: itInfo.itemNumRaw,
              arpId: itInfo.arpId,
              numeroAta: itInfo.numeroAta,
              pdfUrl: itInfo.pdfUrl,
              linkOlhinho: itInfo.url,
              fornecedor,
              cnpj,
              valorUnitario,
              qtdRegistrada: regFinal,
              qtdEmpenhada: empFinal,
              saldoEmpenho: salFinal,
              qtdLimiteAdesao,
              saldoAdesao,
              qtdAprovadaAdesao,
              aceitaAdesao,
              solicitacoesAdesao,
              empenhos: todosEmpenhos
            });
          } catch (eItem) {
            console.warn(`Erro ao detalhar item ${itInfo.itemNum}:`, eItem);
          }
        })
      );
    }
  } catch (err) {
    console.error('Erro global ao executar scrapeContratosItens:', err);
  }

  cacheContratos.set(cacheKey, { data: itensMap, exp: Date.now() + 1000 * 60 * 30 }); // 30 min
  return itensMap;
}
