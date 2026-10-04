import React, { useState } from 'react';
import { 
  Search, 
  Package, 
  ExternalLink, 
  FileText, 
  Download, 
  Plus, 
  Check, 
  AlertCircle, 
  Loader2, 
  Building, 
  ChevronDown, 
  ChevronUp, 
  ArrowRight,
  RefreshCw,
  ShoppingBag,
  Eye,
  FileDown
} from 'lucide-react';
import { PregaoLicitacao, ItemPregao, BancoNCs, NotaCredito, SituacaoItem } from '../types';
import { formatarMoedaBRL } from '../lib/export';
import { buscarCorrespondenciasSubitens, obterFuncaoSubitem, extrairCodigoSubitem } from '../lib/subitens';

interface TabPregoesProps {
  banco: BancoNCs;
  anoFiltro: string;
  isFiscal: boolean;
  onSalvarNC: (chaveNC: string, nc: NotaCredito) => Promise<void>;
}

export function TabPregoes({
  banco,
  anoFiltro,
  isFiscal,
  onSalvarNC
}: TabPregoesProps) {
  const [uasg, setUasg] = useState('');
  const [anos, setAnos] = useState<string[]>([anoFiltro, String(Number(anoFiltro) - 1)]);
  const [pregoes, setPregoes] = useState<PregaoLicitacao[]>([]);
  const [carregandoPregoes, setCarregandoPregoes] = useState(false);
  const [erro, setErro] = useState('');
  const [sucessoMsg, setSucessoMsg] = useState('');

  // Itens em cache por pregão
  const [itensPregao, setItensPregao] = useState<Record<string, ItemPregao[]>>({});
  const [carregandoItens, setCarregandoItens] = useState<Record<string, boolean>>({});
  const [pregaoAberto, setPregaoAberto] = useState<string | null>(null);

  // Modal / Importação de Item para NC
  const [itemImportando, setItemImportando] = useState<ItemPregao | null>(null);
  const [pregaoOrigem, setPregaoOrigem] = useState<PregaoLicitacao | null>(null);
  const [ncDestino, setNcDestino] = useState('');
  const [qtdImportar, setQtdImportar] = useState(1);
  const [valorUnitario, setValorUnitario] = useState(0);
  const [subitemImportar, setSubitemImportar] = useState('');
  const [situacaoImportar, setSituacaoImportar] = useState<SituacaoItem>('Planejamento');
  const [salvandoImportacao, setSalvandoImportacao] = useState(false);

  // Lista de NCs disponíveis para vínculo
  const ncsDisponiveis = Object.keys(banco).filter(k => k !== 'CONFIG_REQUISICAO');

  const handleBuscarPregoes = async () => {
    if (!uasg.trim()) {
      setErro('Por favor, informe o código da UASG (6 dígitos) para pesquisar.');
      return;
    }
    setCarregandoPregoes(true);
    setErro('');
    setSucessoMsg('');
    try {
      const resp = await fetch(`/api/pregoes?uasg=${encodeURIComponent(uasg.trim())}&anos=${encodeURIComponent(anos.join(','))}`);
      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.details || errJson.error || 'Falha ao consultar SIASGnet.');
      }
      const data: PregaoLicitacao[] = await resp.json();
      setPregoes(data);
      if (data.length === 0) {
        setErro(`Nenhum pregão localizado para a UASG ${uasg}.`);
      } else {
        setSucessoMsg(`Foram encontrados ${data.length} pregões para a UASG ${uasg}!`);
      }
    } catch (e: any) {
      setErro(e.message || 'Erro ao conectar ao serviço de pregões do SIASG.');
    } finally {
      setCarregandoPregoes(false);
    }
  };

  const handleCarregarItens = async (pregao: PregaoLicitacao) => {
    const chave = `${pregao.uasg}_${pregao.numero_licitacao}`;
    if (pregaoAberto === chave) {
      setPregaoAberto(null);
      return;
    }
    setPregaoAberto(chave);

    if (itensPregao[chave]) {
      return; // Já em cache
    }

    setCarregandoItens(prev => ({ ...prev, [chave]: true }));
    try {
      const numCompra = pregao.numero_compra || pregao.numero_licitacao.split('/')[0];
      const anoCompra = pregao.ano_compra || pregao.ano;

      const resp = await fetch(`/api/pregao-itens?uasg=${encodeURIComponent(pregao.uasg)}&numCompra=${encodeURIComponent(numCompra)}&anoCompra=${encodeURIComponent(anoCompra)}`);
      if (!resp.ok) {
        throw new Error('Não foi possível carregar os itens deste pregão.');
      }
      const itens: ItemPregao[] = await resp.json();
      setItensPregao(prev => ({ ...prev, [chave]: itens }));
    } catch (e: any) {
      alert(e.message || 'Erro ao carregar itens.');
    } finally {
      setCarregandoItens(prev => ({ ...prev, [chave]: false }));
    }
  };

  const handleAbrirModalImportar = (item: ItemPregao, pregao: PregaoLicitacao) => {
    if (item.Deserto) {
      alert('Este item é Deserto / Fracassado (não possui ata homologada vigente) e não pode ser empenhado.');
      return;
    }
    setItemImportando(item);
    setPregaoOrigem(pregao);
    const primNC = ncsDisponiveis[0] || '';
    setNcDestino(primNC);

    // Converte saldo
    const saldoNum = Number(String(item['Saldo p/ Empenho'] || '0').replace(/\./g, '').replace(',', '.')) || 0;
    setQtdImportar(saldoNum > 0 ? Math.max(1, Math.floor(saldoNum)) : 1);
    
    const vUnit = item['Valor Unitario Sugerido'] || item['Valor Unitário'] || 0;
    setValorUnitario(vUnit);

    // Sugestão de subitem pela ND da primeira NC
    const ndDaNC = banco[primNC]?.nd || '339030';
    const corresp = buscarCorrespondenciasSubitens(ndDaNC, item.Descrição);
    setSubitemImportar(corresp[0]?.subitem || '30');
  };

  const handleConfirmarImportacao = async () => {
    if (!itemImportando || !pregaoOrigem || !ncDestino) return;

    const ncAtual = banco[ncDestino] as NotaCredito;
    if (!ncAtual) {
      alert('Nota de Crédito de destino não encontrada.');
      return;
    }

    setSalvandoImportacao(true);
    try {
      const numItem = parseInt(itemImportando.Item, 10) || ((ncAtual.itens || []).length + 1);
      const totalItem = valorUnitario * qtdImportar;

      const novoItem = {
        Item: numItem,
        Subitem: subitemImportar,
        Nome: itemImportando.Descrição,
        Qtd: qtdImportar,
        'Valor Unitário': valorUnitario,
        Total: totalItem,
        Fornecedor: itemImportando.Fornecedor || 'FORNECEDOR REGISTRADO',
        CNPJ: itemImportando['CNPJ Puro'] || '',
        Pregão: pregaoOrigem.numero_licitacao,
        UASG: pregaoOrigem.uasg,
        Ata: itemImportando['Ata Vinculada'] || '',
        Situação: situacaoImportar,
        'PDF da Ata': itemImportando['PDF da Ata'] || ''
      };

      const novosItens = [...(ncAtual.itens || []), novoItem];
      await onSalvarNC(ncDestino, {
        ...ncAtual,
        itens: novosItens
      });

      setItemImportando(null);
      setSucessoMsg(`Item ${numItem} importado com sucesso para a NC ${ncDestino}!`);
      setTimeout(() => setSucessoMsg(''), 4000);
    } catch (e: any) {
      alert(e.message || 'Erro ao importar item.');
    } finally {
      setSalvandoImportacao(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Topo / Filtro de Consulta */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Search className="w-5 h-5 text-emerald-700" />
            Pesquisa Oficial de Pregões e Atas do SIASG
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Consulte diretamente o SIASGnet e o Contratos.gov.br por UASG e ano para apurar itens registrados, atas vigentes e importar itens com 1 clique.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end pt-2 border-t border-slate-100">
          <div className="sm:col-span-4">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Código da UASG:
            </label>
            <input
              type="text"
              value={uasg}
              onChange={e => setUasg(e.target.value)}
              placeholder="Ex: 160001 (6 dígitos)"
              maxLength={6}
              className="w-full text-xs p-2.5 font-mono font-bold border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
            />
          </div>

          <div className="sm:col-span-5">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Exercícios (Anos):
            </label>
            <div className="flex gap-2">
              {['2026', '2025', '2024', '2023'].map(ano => {
                const ativo = anos.includes(ano);
                return (
                  <button
                    key={ano}
                    type="button"
                    onClick={() => {
                      if (ativo) {
                        if (anos.length > 1) setAnos(anos.filter(a => a !== ano));
                      } else {
                        setAnos([...anos, ano]);
                      }
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                      ativo
                        ? 'bg-emerald-700 text-white border-emerald-700'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {ano}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="sm:col-span-3">
            <button
              onClick={handleBuscarPregoes}
              disabled={carregandoPregoes || !uasg}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
            >
              {carregandoPregoes ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Consultando SIASG...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Buscar Pregões</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {sucessoMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{sucessoMsg}</span>
        </div>
      )}

      {erro && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{erro}</span>
        </div>
      )}

      {/* Lista de Pregões Localizados */}
      {pregoes.length > 0 && (
        <div className="space-y-4">
          <div className="text-xs font-semibold text-slate-700 flex items-center justify-between">
            <span>Pregões Localizados ({pregoes.length})</span>
            <span className="text-slate-400 font-normal">Clique no pregão para expandir e carregar os itens e saldos reais</span>
          </div>

          <div className="space-y-3">
            {pregoes.map(pregao => {
              const chave = `${pregao.uasg}_${pregao.numero_licitacao}`;
              const aberto = pregaoAberto === chave;
              const itens = itensPregao[chave] || [];
              const carregando = carregandoItens[chave];

              return (
                <div
                  key={chave}
                  className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden transition-all"
                >
                  {/* Cabeçalho do Card */}
                  <div
                    onClick={() => handleCarregarItens(pregao)}
                    className="p-4 cursor-pointer hover:bg-slate-50/80 transition-colors flex items-start justify-between gap-4 select-none"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 font-mono">
                          Pregão {pregao.numero_licitacao}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-700">
                          Ano {pregao.ano}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-700">
                          UASG {pregao.uasg}
                        </span>
                        {itens.length > 0 && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700">
                            {itens.length} itens carregados
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-700 font-medium line-clamp-2">
                        {pregao.objeto}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 pt-1">
                      {pregao.link_contratos && (
                        <a
                          href={pregao.link_contratos}
                          target="_blank"
                          rel="noreferrer"
                          onClick={e => e.stopPropagation()}
                          title="Abrir no Contratos.gov.br"
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-emerald-700 hover:border-emerald-300 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                      <div className="text-slate-400">
                        {aberto ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>

                  {/* Detalhes / Tabela de Itens */}
                  {aberto && (
                    <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-4">
                      {carregando ? (
                        <div className="flex items-center justify-center py-8 space-y-2 flex-col">
                          <Loader2 className="w-6 h-6 text-emerald-700 animate-spin" />
                          <span className="text-xs text-slate-500">
                            Apurando itens, atas e saldos no Contratos.gov.br...
                          </span>
                        </div>
                      ) : itens.length === 0 ? (
                        <div className="text-center py-6 text-xs text-slate-400">
                          Nenhum item localizado ou o pregão não possui atas homologadas no período.
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                              <tr>
                                <th className="p-2.5 w-12 text-center">Item</th>
                                <th className="p-2.5 min-w-[220px]">Descrição do Material / Serviço</th>
                                <th className="p-2.5 w-14 text-center">Und</th>
                                <th className="p-2.5 w-24 text-right">Valor Unitário</th>
                                <th className="p-2.5 w-20 text-right">Qtd Reg.</th>
                                <th className="p-2.5 w-20 text-right">Qtd Emp.</th>
                                <th className="p-2.5 w-20 text-right">Saldo</th>
                                <th className="p-2.5 min-w-[180px]">Fornecedor / Status</th>
                                <th className="p-2.5 w-36 min-w-[130px] text-center font-bold text-slate-800">Ação / NC</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200/80 bg-white">
                              {itens.map(item => {
                                const vUnit = item['Valor Unitario Sugerido'] || item['Valor Unitário'] || 0;
                                const saldoNum = Number(String(item['Saldo p/ Empenho'] || '0').replace(/\./g, '').replace(',', '.')) || 0;
                                const isDeserto = item.Deserto || (item.Fornecedor || '').toLowerCase().includes('deserto') || item['Ata Vinculada'] === '-';

                                return (
                                  <tr
                                    key={item.Item}
                                    className={`transition-colors ${isDeserto ? 'bg-slate-50/60 text-slate-500' : 'hover:bg-slate-50/80'}`}
                                  >
                                    <td className="p-2.5 font-mono text-center font-bold text-slate-700">
                                      {item.Item}
                                    </td>
                                    <td className="p-2.5 font-medium text-slate-900">
                                      <div className="line-clamp-2" title={item.Descrição}>
                                        {item.Descrição}
                                      </div>
                                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                                        {item['Ata Vinculada'] && item['Ata Vinculada'] !== '-' ? (
                                          <span className="text-[10px] text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded font-mono font-medium border border-slate-200">
                                            Ata: {item['Ata Vinculada']}
                                          </span>
                                        ) : (
                                          <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-medium border border-amber-200">
                                            Sem ata vinculada
                                          </span>
                                        )}
                                        {item['PDF da Ata'] && (
                                          <a
                                            href={item['PDF da Ata']}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 px-2 py-0.5 rounded transition-colors shadow-2xs"
                                            title="Baixar PDF da Ata de Registro de Preços deste item"
                                          >
                                            <FileDown className="w-3 h-3 text-emerald-700" />
                                            <span>Baixar Ata</span>
                                          </a>
                                        )}
                                        {item['Link Olhinho'] && (
                                          <a
                                            href={item['Link Olhinho']}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1 text-[10px] font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors"
                                            title="Abrir página oficial do pregão no Contratos.gov.br (Transparência)"
                                          >
                                            <Eye className="w-3 h-3 text-blue-600" />
                                            <span>Transparência</span>
                                          </a>
                                        )}
                                      </div>
                                    </td>
                                    <td className="p-2.5 text-center text-slate-600 font-mono">
                                      {item.Unidade || 'UN'}
                                    </td>
                                    <td className="p-2.5 text-right font-mono font-medium text-slate-900">
                                      {vUnit > 0 ? formatarMoedaBRL(vUnit) : isDeserto ? '-' : 'R$ 0,00'}
                                    </td>
                                    <td className="p-2.5 text-right font-mono text-slate-700">
                                      {item['Qtd Registrada'] || '0'}
                                    </td>
                                    <td className="p-2.5 text-right font-mono text-slate-700">
                                      {item['Qtd Empenhada'] || '0'}
                                    </td>
                                    <td className="p-2.5 text-right font-mono">
                                      {saldoNum > 0 ? (
                                        <span className="font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                                          {item['Saldo p/ Empenho']}
                                        </span>
                                      ) : (
                                        <span className="text-slate-400">
                                          {item['Saldo p/ Empenho'] || '0'}
                                        </span>
                                      )}
                                    </td>
                                    <td className="p-2.5">
                                      {isDeserto ? (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-900">
                                          <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                                          Deserto / Fracassado
                                        </span>
                                      ) : (
                                        <div className="truncate max-w-[200px]" title={item.Fornecedor}>
                                          <span className="text-slate-800 font-medium">{item['Fornecedor Puro'] || item.Fornecedor}</span>
                                          {item['CNPJ Puro'] && (
                                            <span className="text-[10px] text-slate-400 block font-mono">{item['CNPJ Puro']}</span>
                                          )}
                                        </div>
                                      )}
                                    </td>
                                    <td className="p-2.5 text-center">
                                      {isDeserto ? (
                                        <span className="inline-flex items-center px-2 py-1 rounded bg-slate-100 text-slate-400 text-[11px] font-medium italic">
                                          Sem ata
                                        </span>
                                      ) : (
                                        <button
                                          type="button"
                                          onClick={() => handleAbrirModalImportar(item, pregao)}
                                          className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700 text-white font-semibold text-xs hover:bg-emerald-800 active:scale-95 transition-all shadow-xs w-full cursor-pointer"
                                          title="Importar este item para uma Nota de Crédito com valor e saldo pré-preenchidos"
                                        >
                                          <Plus className="w-3.5 h-3.5 shrink-0" />
                                          <span>Importar p/ NC</span>
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Modal: Importar Item para Nota de Crédito */}
      {itemImportando && pregaoOrigem && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-emerald-700" />
                Importar Item do Pregão para a NC
              </h3>
              <button
                onClick={() => setItemImportando(null)}
                className="text-slate-400 hover:text-slate-700 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="font-bold text-slate-900 flex items-center justify-between">
                <span>Item #{itemImportando.Item} — Pregão {pregaoOrigem.numero_licitacao} (UASG {pregaoOrigem.uasg})</span>
                {itemImportando['Ata Vinculada'] && itemImportando['Ata Vinculada'] !== '-' && (
                  <span className="text-[11px] font-mono text-slate-500 font-normal">Ata: {itemImportando['Ata Vinculada']}</span>
                )}
              </div>
              <div className="text-slate-700 font-medium">
                {itemImportando.Descrição}
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/80 text-[11px]">
                <div className="bg-white p-2 rounded-lg border border-slate-100">
                  <span className="text-slate-500 block">Qtd Registrada:</span>
                  <strong className="font-mono text-slate-800 text-xs">{itemImportando['Qtd Registrada'] || '0'} {itemImportando.Unidade || 'UN'}</strong>
                </div>
                <div className="bg-white p-2 rounded-lg border border-slate-100">
                  <span className="text-slate-500 block">Qtd Empenhada:</span>
                  <strong className="font-mono text-slate-800 text-xs">{itemImportando['Qtd Empenhada'] || '0'} {itemImportando.Unidade || 'UN'}</strong>
                </div>
                <div className="bg-emerald-50/60 p-2 rounded-lg border border-emerald-100">
                  <span className="text-emerald-700 block font-semibold">Saldo Disponível:</span>
                  <strong className="font-mono text-emerald-800 text-xs font-bold">{itemImportando['Saldo p/ Empenho'] || '0'} {itemImportando.Unidade || 'UN'}</strong>
                </div>
              </div>
              <div className="text-[11px] text-slate-600 pt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <span>Fornecedor: <strong className="text-slate-900">{itemImportando['Fornecedor Puro'] || itemImportando.Fornecedor}</strong></span>
                <span>Valor Unitário da Ata: <strong className="text-emerald-800 font-mono text-xs">{formatarMoedaBRL(itemImportando['Valor Unitario Sugerido'] || itemImportando['Valor Unitário'] || 0)}</strong></span>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Nota de Crédito (NC) de Destino:
                </label>
                {ncsDisponiveis.length === 0 ? (
                  <div className="text-amber-700 p-2 bg-amber-50 rounded border border-amber-200">
                    Você ainda não cadastrou nenhuma NC. Cadastre uma NC na primeira aba antes de puxar itens.
                  </div>
                ) : (
                  <select
                    value={ncDestino}
                    onChange={e => {
                      const novaNC = e.target.value;
                      setNcDestino(novaNC);
                      const nd = banco[novaNC]?.nd || '339030';
                      const corresp = buscarCorrespondenciasSubitens(nd, itemImportando.Descrição);
                      setSubitemImportar(corresp[0]?.subitem || '30');
                    }}
                    className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-semibold text-slate-800"
                  >
                    {ncsDisponiveis.map(ncKey => (
                      <option key={ncKey} value={ncKey}>
                        {ncKey} (ND {banco[ncKey]?.nd})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Quantidade a Empenhar / Comprar:
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={qtdImportar}
                    onChange={e => setQtdImportar(Math.max(1, parseInt(e.target.value, 10) || 1))}
                    className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Valor Unitário (R$):
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={valorUnitario}
                    onChange={e => setValorUnitario(parseFloat(e.target.value) || 0)}
                    className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-mono text-right"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Subitem (2 Dígitos):
                  </label>
                  <input
                    type="text"
                    maxLength={2}
                    value={subitemImportar}
                    onChange={e => setSubitemImportar(e.target.value.replace(/\D/g, ''))}
                    placeholder="Ex: 30"
                    className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-mono font-bold text-center"
                  />
                  {ncDestino && (
                    <span className="text-[10px] text-slate-500 mt-0.5 block truncate">
                      {obterFuncaoSubitem(banco[ncDestino]?.nd || '339030', subitemImportar) || 'Subitem da ND'}
                    </span>
                  )}
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Situação Inicial:
                  </label>
                  <select
                    value={situacaoImportar}
                    onChange={e => setSituacaoImportar(e.target.value as SituacaoItem)}
                    className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600"
                  >
                    <option value="Planejamento">Planejamento</option>
                    <option value="Aguardando entrega">Aguardando entrega</option>
                    <option value="Recebido">Recebido</option>
                  </select>
                </div>
              </div>

              <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-xs flex items-center justify-between">
                <span className="text-emerald-800 font-medium">Total Calculado:</span>
                <span className="text-sm font-bold text-emerald-900 font-mono">
                  {formatarMoedaBRL(qtdImportar * valorUnitario)}
                </span>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setItemImportando(null)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={salvandoImportacao || ncsDisponiveis.length === 0}
                  onClick={handleConfirmarImportacao}
                  className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
                >
                  {salvandoImportacao ? 'Importando...' : 'Confirmar Importação'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
