import { useState, useMemo, type FormEvent } from 'react';
import { 
  FileText, 
  Download, 
  Edit, 
  Trash2, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  Package, 
  Search, 
  Plus, 
  FileSpreadsheet,
  AlertCircle,
  Check,
  ChevronDown,
  Building2,
  Printer,
  ChevronRight
} from 'lucide-react';
import { BancoNCs, NotaCredito, ItemNC, SituacaoItem, PerfilUsuario, ConfigRequisicao } from '../types';
import { SubitemSelector } from './SubitemSelector';
import { RequisicaoModal } from './RequisicaoModal';
import { formatarMoedaBRL, exportarPlanilhaNC } from '../lib/export';
import { obterFuncaoSubitem, obterNomeSubitem, montarOpcoesSubitem, extrairCodigoSubitem } from '../lib/subitens';

interface TabVisualizacaoProps {
  banco: BancoNCs;
  ncSelecionada: string;
  onSelecionarNC: (chave: string) => void;
  anoFiltro: string;
  perfil: PerfilUsuario;
  configRequisicao: ConfigRequisicao;
  onSalvarNC: (chaveNC: string, nc: NotaCredito) => Promise<void>;
  onSalvarConfig: (novaConfig: ConfigRequisicao) => Promise<void>;
}

export function TabVisualizacao({
  banco,
  ncSelecionada,
  onSelecionarNC,
  anoFiltro,
  perfil,
  configRequisicao,
  onSalvarNC,
  onSalvarConfig
}: TabVisualizacaoProps) {
  const isFiscal = perfil === 'Fiscal';

  // Modal de Requisição Oficial
  const [abrirModalRequisicao, setAbrirModalRequisicao] = useState(false);
  const [fornecedorSelecionadoRequisicao, setFornecedorSelecionadoRequisicao] = useState<string>('TODOS');

  // Estado para edição rápida dos dados do DIEx/Documento por Fornecedor
  const [docInfoForm, setDocInfoForm] = useState<Record<string, { diex: string; eb: string; data: string; assunto: string; empenho: string }>>({});

  // Modal de Edição de Dados da NC
  const [modalEditarNC, setModalEditarNC] = useState(false);
  const [editND, setEditND] = useState('');
  const [editPI, setEditPI] = useState('');
  const [editValorRec, setEditValorRec] = useState(0);

  // Modal de Edição de Item
  const [itemParaEditar, setItemParaEditar] = useState<{ index: number; item: ItemNC } | null>(null);

  // Ajustador de Subitem inline/expansível
  const [ajustadorAberto, setAjustadorAberto] = useState(false);
  const [itemIndexAjuste, setItemIndexAjuste] = useState<number>(0);
  const [novoSubitemAjuste, setNovoSubitemAjuste] = useState('');

  // Filtro de busca na tabela
  const [buscaTabela, setBuscaTabela] = useState('');

  const ncsDisponiveis = useMemo(() => {
    return Object.keys(banco).filter(k => {
      if (k === 'CONFIG_REQUISICAO') return false;
      if (anoFiltro && anoFiltro !== 'Todos' && !k.includes(anoFiltro)) return false;
      return true;
    }).sort();
  }, [banco, anoFiltro]);

  const chaveAtual = ncSelecionada || ncsDisponiveis[0] || '';
  const ncAtual = banco[chaveAtual] as NotaCredito | undefined;

  // Totais
  const itens = useMemo(() => ncAtual?.itens || [], [ncAtual]);
  const totalGasto = useMemo(() => itens.reduce((acc, it) => acc + (it.Total || 0), 0), [itens]);
  const valorRecebido = ncAtual?.valor_recebido || 0;
  const saldoDisponivel = valorRecebido - totalGasto;
  const pctExecucao = valorRecebido > 0 ? Math.min(100, Math.round((totalGasto / valorRecebido) * 100)) : 0;

  // Lista de fornecedores únicos desta NC com seus respectivos itens
  const fornecedoresDetalhados = useMemo(() => {
    const mapa = new Map<string, ItemNC[]>();
    itens.forEach(it => {
      const f = (it.Fornecedor || 'NÃO DEFINIDO').trim();
      if (!mapa.has(f)) {
        mapa.set(f, []);
      }
      mapa.get(f)!.push(it);
    });
    return Array.from(mapa.entries()).map(([nome, itensForn]) => {
      const totalForn = itensForn.reduce((acc, it) => acc + (it.Total || 0), 0);
      const todosRecebidos = itensForn.every(it => it.Situação === 'Recebido');
      const cnpj = itensForn[0]?.CNPJ || '';
      const pregao = itensForn[0]?.Pregão || '';
      return {
        nome,
        cnpj,
        pregao,
        itens: itensForn,
        total: totalForn,
        todosRecebidos
      };
    }).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [itens]);
  const itensFiltrados = useMemo(() => {
    if (!buscaTabela.trim()) return itens;
    const t = buscaTabela.toLowerCase();
    return itens.filter(it => 
      String(it.Item).includes(t) ||
      (it.Subitem || '').toLowerCase().includes(t) ||
      (it.Nome || '').toLowerCase().includes(t) ||
      (it.Fornecedor || '').toLowerCase().includes(t) ||
      (it.CNPJ || '').toLowerCase().includes(t) ||
      (it.Situação || '').toLowerCase().includes(t)
    );
  }, [itens, buscaTabela]);

  const handleAbrirEditarNC = () => {
    if (!ncAtual) return;
    setEditND(ncAtual.nd || '339030');
    setEditPI(ncAtual.pi || '');
    setEditValorRec(ncAtual.valor_recebido || 0);
    setModalEditarNC(true);
  };

  const handleSalvarEdicaoNC = async (e: FormEvent) => {
    e.preventDefault();
    if (!ncAtual) return;
    const ncAtualizada: NotaCredito = {
      ...ncAtual,
      nd: editND.trim(),
      pi: editPI.trim(),
      valor_recebido: Number(editValorRec) || 0
    };
    await onSalvarNC(chaveAtual, ncAtualizada);
    setModalEditarNC(false);
  };

  const handleAlterarSituacao = async (indexReal: number, novaSituacao: SituacaoItem) => {
    if (isFiscal || !ncAtual) return;
    const novosItens = [...itens];
    novosItens[indexReal] = {
      ...novosItens[indexReal],
      Situação: novaSituacao
    };
    await onSalvarNC(chaveAtual, { ...ncAtual, itens: novosItens });
  };

  const handleExcluirItem = async (indexReal: number) => {
    if (isFiscal || !ncAtual) return;
    if (!confirm('Deseja realmente remover este material da NC?')) return;
    const novosItens = itens.filter((_, idx) => idx !== indexReal);
    await onSalvarNC(chaveAtual, { ...ncAtual, itens: novosItens });
  };

  const handleSalvarEdicaoItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!itemParaEditar || !ncAtual) return;
    const novosItens = [...itens];
    const totalCalc = Number((itemParaEditar.item.Qtd * itemParaEditar.item['Valor Unitário']).toFixed(2));
    novosItens[itemParaEditar.index] = {
      ...itemParaEditar.item,
      Total: totalCalc
    };
    await onSalvarNC(chaveAtual, { ...ncAtual, itens: novosItens });
    setItemParaEditar(null);
  };

  const handleAplicarSubitemAjuste = async () => {
    if (isFiscal || !ncAtual || !itens[itemIndexAjuste]) return;
    const novosItens = [...itens];
    novosItens[itemIndexAjuste] = {
      ...novosItens[itemIndexAjuste],
      Subitem: novoSubitemAjuste
    };
    await onSalvarNC(chaveAtual, { ...ncAtual, itens: novosItens });
    alert(`Subitem do Item ${novosItens[itemIndexAjuste].Item} atualizado para ${novoSubitemAjuste}!`);
  };

  // Marcar todos os itens de uma determinada empresa como "Recebido" (igual app.py)
  const handleReceberLoteFornecedor = async (fornecedorNome: string) => {
    if (isFiscal || !ncAtual) return;
    const novosItens = itens.map(it => {
      if ((it.Fornecedor || '').trim() === fornecedorNome.trim()) {
        return { ...it, Situação: 'Recebido' as SituacaoItem };
      }
      return it;
    });
    await onSalvarNC(chaveAtual, { ...ncAtual, itens: novosItens });
    alert(`Todos os itens do fornecedor "${fornecedorNome}" foram marcados como Recebidos!`);
  };

  // Salvar metadados de DIEx, EB, Data, Assunto e NE do Fornecedor na NC
  const handleSalvarDocInfo = async (fornecedorNome: string) => {
    if (!ncAtual) return;
    const dadosForm = docInfoForm[fornecedorNome] || { diex: '', eb: '', data: '', assunto: '', empenho: '' };
    const docInfoAtual = { ...(ncAtual.doc_info || {}) };
    docInfoAtual[fornecedorNome] = dadosForm;
    await onSalvarNC(chaveAtual, { ...ncAtual, doc_info: docInfoAtual });
    alert(`Dados do documento para o fornecedor "${fornecedorNome}" salvos com sucesso!`);
  };

  if (!chaveAtual || !ncAtual) {
    return (
      <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
        <Package className="w-12 h-12 text-slate-300 mx-auto" />
        <h3 className="text-sm font-semibold text-slate-800">Nenhuma NC selecionada</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Cadastre ou selecione uma Nota de Crédito para visualizar os itens e gerar os documentos oficiais.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Topo: Seletor de NC e Ações Principais */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-800 text-white flex items-center justify-center font-bold text-sm shadow-xs">
            NC
          </div>
          <div>
            <div className="flex items-center gap-2">
              <select
                value={chaveAtual}
                onChange={e => onSelecionarNC(e.target.value)}
                className="text-base font-bold text-slate-900 bg-transparent border-b border-dashed border-slate-400 focus:outline-none cursor-pointer pr-4"
              >
                {ncsDisponiveis.map(k => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-100 text-emerald-800">
                ND {ncAtual.nd || 'Não def.'}
              </span>
              {ncAtual.pi && (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-700">
                  PI: {ncAtual.pi}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Gestão da Nota de Crédito, acompanhamento orçamentário e emissão de requisições.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isFiscal && (
            <button
              onClick={handleAbrirEditarNC}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Edit className="w-3.5 h-3.5" />
              Editar NC
            </button>
          )}

          <button
            onClick={() => setAbrirModalRequisicao(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
          >
            <FileText className="w-4 h-4" />
            Gerar Requisição Oficial
          </button>
        </div>
      </div>

      {/* Cards de Métricas Orçamentárias */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Valor Recebido */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
            Valor Total Recebido
          </span>
          <div className="text-xl font-bold text-slate-900">
            {formatarMoedaBRL(valorRecebido)}
          </div>
          <span className="text-[10px] text-slate-400 block">
            Limite orçamentário aprovado
          </span>
        </div>

        {/* Total Alocado / Requisitado */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
            Total Requisitado ({itens.length} itens)
          </span>
          <div className="text-xl font-bold text-slate-800">
            {formatarMoedaBRL(totalGasto)}
          </div>
          <span className="text-[10px] text-slate-400 block">
            Soma dos materiais lançados
          </span>
        </div>

        {/* Saldo Disponível */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
            Saldo Disponível
          </span>
          <div className={`text-xl font-bold ${saldoDisponivel < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
            {formatarMoedaBRL(saldoDisponivel)}
          </div>
          <span className="text-[10px] text-slate-400 block">
            {saldoDisponivel < 0 ? '⚠️ Alerta de déficit orçamentário' : 'Margem disponível para novos itens'}
          </span>
        </div>

        {/* Percentual de Execução */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Execução
            </span>
            <span className="text-xs font-bold text-slate-900">{pctExecucao}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-2 rounded-full transition-all ${
                pctExecucao > 100
                  ? 'bg-red-600'
                  : pctExecucao > 85
                  ? 'bg-amber-500'
                  : 'bg-emerald-600'
              }`}
              style={{ width: `${Math.min(100, pctExecucao)}%` }}
            />
          </div>
          <span className="text-[10px] text-slate-400 block">
            {pctExecucao >= 100 ? 'Execução orçamentária total atingida' : 'Dentro do limite'}
          </span>
        </div>
      </div>

      {/* Painel Expansível: Conferência e Ajuste de Subitem por Função Oficial SIAFI */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <button
          onClick={() => setAjustadorAberto(!ajustadorAberto)}
          className="w-full px-5 py-3.5 flex items-center justify-between bg-slate-50/70 hover:bg-slate-100/70 transition-colors text-left"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-700" />
            <span className="text-xs font-bold text-slate-800">
              🎯 Conferir ou Alterar Sub Item de um Material da NC (Pesquisa pela Função Oficial da ND)
            </span>
          </div>
          <ChevronDown
            className={`w-4 h-4 text-slate-400 transition-transform ${ajustadorAberto ? 'rotate-180' : ''}`}
          />
        </button>

        {ajustadorAberto && (
          <div className="p-5 border-t border-slate-200/80 bg-white space-y-4">
            {itens.length === 0 ? (
              <p className="text-xs text-slate-500">Nenhum material cadastrado nesta NC ainda.</p>
            ) : (
              <div className="space-y-3 max-w-3xl">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Selecione o Item da NC para Consultar ou Reclassificar:
                  </label>
                  <select
                    value={itemIndexAjuste}
                    onChange={e => {
                      const idx = Number(e.target.value);
                      setItemIndexAjuste(idx);
                      setNovoSubitemAjuste(itens[idx]?.Subitem || '');
                    }}
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium"
                  >
                    {itens.map((it, idx) => (
                      <option key={idx} value={idx}>
                        Item #{it.Item} - {it.Nome.slice(0, 70)} (Subitem Atual: {it.Subitem || 'S/ Subitem'})
                      </option>
                    ))}
                  </select>
                </div>

                {itens[itemIndexAjuste] && (
                  <div className="space-y-3 pt-2">
                    <SubitemSelector
                      nd={ncAtual.nd || '339030'}
                      descricao={itens[itemIndexAjuste].Nome}
                      value={novoSubitemAjuste || itens[itemIndexAjuste].Subitem || '01'}
                      onChange={setNovoSubitemAjuste}
                      disabled={isFiscal}
                    />

                    {!isFiscal && (
                      <div className="flex justify-end pt-2">
                        <button
                          type="button"
                          onClick={handleAplicarSubitemAjuste}
                          className="px-4 py-2 bg-emerald-700 text-white rounded-lg text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
                        >
                          Salvar Novo Subitem no Item #{itens[itemIndexAjuste].Item}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tabela de Materiais da NC */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        {/* Barra superior da tabela */}
        <div className="p-4 border-b border-slate-200/80 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-emerald-700" />
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Materiais da Nota de Crédito ({itens.length})
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Filtrar por item, nome, fornecedor..."
                value={buscaTabela}
                onChange={e => setBuscaTabela(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none w-64"
              />
            </div>
          </div>
        </div>

        {/* Tabela Responsiva */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/80 text-slate-700 font-semibold border-b border-slate-200">
                <th className="px-3 py-2.5 text-center w-14">Item</th>
                {/* SUB ITEM AO LADO DO ITEM */}
                <th className="px-3 py-2.5 text-center w-20">Sub Item</th>
                <th className="px-3 py-2.5">Descrição do Material</th>
                <th className="px-3 py-2.5 text-center w-16">Qtd</th>
                <th className="px-3 py-2.5 text-right w-24">Vl Unit (R$)</th>
                <th className="px-3 py-2.5 text-right w-24">Total (R$)</th>
                <th className="px-3 py-2.5 w-44">Fornecedor / CNPJ</th>
                <th className="px-3 py-2.5 text-center w-36">Situação</th>
                {!isFiscal && <th className="px-3 py-2.5 text-center w-20">Ações</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70">
              {itensFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={isFiscal ? 8 : 9} className="py-8 text-center text-slate-400 text-xs">
                    {itens.length === 0
                      ? 'Nenhum material lançado nesta NC ainda. Utilize a aba "Cadastro e Gestão" para adicionar.'
                      : 'Nenhum item corresponde ao filtro de busca.'}
                  </td>
                </tr>
              ) : (
                itensFiltrados.map((it, idx) => {
                  const indexReal = itens.indexOf(it);
                  const nomeSub = obterNomeSubitem(ncAtual.nd, it.Subitem);

                  return (
                    <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                      {/* Nº do Item */}
                      <td className="px-3 py-3 text-center font-bold text-slate-900">
                        #{it.Item}
                      </td>

                      {/* Sub Item da ND */}
                      <td className="px-3 py-3 text-center">
                        <span
                          title={nomeSub ? `${it.Subitem} - ${nomeSub}` : `Subitem ${it.Subitem}`}
                          className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-200 cursor-help"
                        >
                          {it.Subitem || '-'}
                        </span>
                      </td>

                      {/* Nome / Descrição */}
                      <td className="px-3 py-3">
                        <div className="font-semibold text-slate-900 leading-tight">{it.Nome}</div>
                        {it.Obs && (
                          <div className="text-[10px] text-slate-500 italic mt-0.5">{it.Obs}</div>
                        )}
                        {it.Pregão && (
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            PE {it.Pregão} {it.Ata ? `• Ata ${it.Ata}` : ''} {it.UASG ? `• UASG ${it.UASG}` : ''}
                          </div>
                        )}
                      </td>

                      {/* Quantidade */}
                      <td className="px-3 py-3 text-center font-medium text-slate-800">
                        {it.Qtd}
                      </td>

                      {/* Valor Unitário */}
                      <td className="px-3 py-3 text-right font-mono text-slate-700">
                        {formatarMoedaBRL(it['Valor Unitário'])}
                      </td>

                      {/* Total */}
                      <td className="px-3 py-3 text-right font-mono font-bold text-slate-900">
                        {formatarMoedaBRL(it.Total)}
                      </td>

                      {/* Fornecedor */}
                      <td className="px-3 py-3 text-[11px]">
                        <div className="font-medium text-slate-800 truncate max-w-[180px]" title={it.Fornecedor}>
                          {it.Fornecedor || 'NÃO INFORMADO'}
                        </div>
                        {it.CNPJ && (
                          <div className="text-[10px] text-slate-400 font-mono">{it.CNPJ}</div>
                        )}
                      </td>

                      {/* Situação com Seletor Rápido */}
                      <td className="px-3 py-3 text-center">
                        {isFiscal ? (
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              it.Situação === 'Recebido'
                                ? 'bg-emerald-100 text-emerald-800'
                                : it.Situação === 'Aguardando entrega'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {it.Situação}
                          </span>
                        ) : (
                          <select
                            value={it.Situação}
                            onChange={e => handleAlterarSituacao(indexReal, e.target.value as SituacaoItem)}
                            className={`text-[11px] font-semibold py-1 px-2 rounded-lg border focus:outline-none cursor-pointer ${
                              it.Situação === 'Recebido'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                : it.Situação === 'Aguardando entrega'
                                ? 'bg-amber-50 text-amber-800 border-amber-200'
                                : 'bg-slate-50 text-slate-700 border-slate-200'
                            }`}
                          >
                            <option value="Planejamento">Planejamento</option>
                            <option value="Aguardando entrega">Aguardando entrega</option>
                            <option value="Recebido">Recebido</option>
                          </select>
                        )}
                      </td>

                      {/* Ações */}
                      {!isFiscal && (
                        <td className="px-3 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => setItemParaEditar({ index: indexReal, item: { ...it } })}
                              title="Editar este item"
                              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleExcluirItem(indexReal)}
                              title="Excluir este item"
                              className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
            <tfoot>
              <tr className="bg-slate-50 font-bold border-t border-slate-300">
                <td colSpan={5} className="px-3 py-3 text-right uppercase text-xs text-slate-600">
                  Total da NC Alocado:
                </td>
                <td className="px-3 py-3 text-right font-mono text-sm text-slate-900">
                  {formatarMoedaBRL(totalGasto)}
                </td>
                <td colSpan={isFiscal ? 2 : 3}></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Módulo Especial: Gestão por Fornecedores e Emissão de Requisições / DIEx por Empresa */}
      {fornecedoresDetalhados.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-700" />
                Fornecedores e Requisições por Empresa ({fornecedoresDetalhados.length})
              </h3>
              <p className="text-xs text-slate-500">
                Gere o Termo de Requisição e DIEx oficial por fornecedor, preencha dados de processo (EB/NE) e dê baixa em lote.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {fornecedoresDetalhados.map(forn => {
              const docInfoForn = (ncAtual.doc_info && ncAtual.doc_info[forn.nome]) || {
                diex: '',
                eb: '',
                data: '',
                assunto: '',
                empenho: ''
              };

              const formAtual = docInfoForm[forn.nome] || { ...docInfoForn };

              return (
                <div
                  key={forn.nome}
                  className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden"
                >
                  <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                        🏢
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900">{forn.nome}</h4>
                          {forn.cnpj && (
                            <span className="text-[11px] font-mono text-slate-500 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                              {forn.cnpj}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500">
                          {forn.itens.length} {forn.itens.length === 1 ? 'item' : 'itens'} • Total: <strong className="text-slate-900 font-mono">{formatarMoedaBRL(forn.total)}</strong>
                          {forn.pregao && ` • ${forn.pregao}`}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {!isFiscal && (
                        <button
                          onClick={() => handleReceberLoteFornecedor(forn.nome)}
                          disabled={forn.todosRecebidos}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                            forn.todosRecebidos
                              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                              : 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100'
                          }`}
                        >
                          <Check className="w-3.5 h-3.5" />
                          {forn.todosRecebidos ? 'Itens Recebidos' : 'Receber Todos os Itens'}
                        </button>
                      )}

                      <button
                        onClick={() => {
                          setFornecedorSelecionadoRequisicao(forn.nome);
                          setAbrirModalRequisicao(true);
                        }}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
                      >
                        <Printer className="w-3.5 h-3.5" />
                        Imprimir DIEx / Requisição
                      </button>
                    </div>
                  </div>

                  {/* Formulário de Metadados do DIEx e Depósito / NE */}
                  <div className="p-4 bg-white space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Nº do DIEx:
                        </label>
                        <input
                          type="text"
                          placeholder="Ex: 123"
                          value={formAtual.diex}
                          onChange={e => {
                            setDocInfoForm({
                              ...docInfoForm,
                              [forn.nome]: { ...formAtual, diex: e.target.value }
                            });
                          }}
                          className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Nº do EB (Processo):
                        </label>
                        <input
                          type="text"
                          placeholder="Ex: 64123.001234/2026-00"
                          value={formAtual.eb}
                          onChange={e => {
                            setDocInfoForm({
                              ...docInfoForm,
                              [forn.nome]: { ...formAtual, eb: e.target.value }
                            });
                          }}
                          className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Data do Documento:
                        </label>
                        <input
                          type="text"
                          placeholder="Ex: 19 de setembro de 2026"
                          value={formAtual.data}
                          onChange={e => {
                            setDocInfoForm({
                              ...docInfoForm,
                              [forn.nome]: { ...formAtual, data: e.target.value }
                            });
                          }}
                          className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Assunto da Requisição:
                        </label>
                        <input
                          type="text"
                          placeholder="Ex: aquisição de material de consumo"
                          value={formAtual.assunto}
                          onChange={e => {
                            setDocInfoForm({
                              ...docInfoForm,
                              [forn.nome]: { ...formAtual, assunto: e.target.value }
                            });
                          }}
                          className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
                      <div className="flex items-center gap-2 max-w-sm w-full">
                        <span className="text-[11px] font-semibold text-slate-700 shrink-0">
                          📦 Nota de Empenho (NE):
                        </span>
                        <input
                          type="text"
                          placeholder="Ex: 2026NE000123"
                          value={formAtual.empenho}
                          onChange={e => {
                            setDocInfoForm({
                              ...docInfoForm,
                              [forn.nome]: { ...formAtual, empenho: e.target.value }
                            });
                          }}
                          className="flex-1 p-1.5 text-xs font-mono border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                        />
                      </div>

                      <button
                        onClick={() => handleSalvarDocInfo(forn.nome)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                      >
                        💾 Salvar Dados deste Fornecedor
                      </button>
                    </div>

                    {formAtual.empenho && (
                      <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded-lg">
                        📦 <strong>Controle de Almoxarifado:</strong> DIEx nº <strong>{formAtual.diex || 'S/N'}</strong> vinculado à Nota de Empenho (NE) <strong>{formAtual.empenho}</strong>.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Modal de Requisição Oficial */}
      {abrirModalRequisicao && (
        <RequisicaoModal
          chaveNC={chaveAtual}
          nc={ncAtual}
          config={configRequisicao}
          fornecedorInicial={fornecedorSelecionadoRequisicao}
          onSalvarConfig={onSalvarConfig}
          onClose={() => setAbrirModalRequisicao(false)}
        />
      )}

      {/* Modal de Edição de Dados da NC */}
      {modalEditarNC && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Editar Dados da Nota de Crédito: {chaveAtual}
            </h3>

            <form onSubmit={handleSalvarEdicaoNC} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Natureza da Despesa (ND):
                </label>
                <input
                  type="text"
                  value={editND}
                  onChange={e => setEditND(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-mono font-semibold"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Programa de Trabalho / PI:
                </label>
                <input
                  type="text"
                  value={editPI}
                  onChange={e => setEditPI(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Valor Recebido da NC (R$):
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editValorRec}
                  onChange={e => setEditValorRec(Number(e.target.value))}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-mono text-right font-bold"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setModalEditarNC(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white font-medium hover:bg-emerald-800"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Edição de Item */}
      {itemParaEditar && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Editar Material: Item #{itemParaEditar.item.Item}
            </h3>

            <form onSubmit={handleSalvarEdicaoItem} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Descrição do Material:
                </label>
                <input
                  type="text"
                  required
                  value={itemParaEditar.item.Nome}
                  onChange={e =>
                    setItemParaEditar({
                      ...itemParaEditar,
                      item: { ...itemParaEditar.item, Nome: e.target.value }
                    })
                  }
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600"
                />
              </div>

              {/* Seletor de Subitem */}
              <SubitemSelector
                nd={ncAtual.nd || '339030'}
                descricao={itemParaEditar.item.Nome}
                value={itemParaEditar.item.Subitem}
                onChange={sub =>
                  setItemParaEditar({
                    ...itemParaEditar,
                    item: { ...itemParaEditar.item, Subitem: sub }
                  })
                }
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Quantidade:
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="any"
                    value={itemParaEditar.item.Qtd}
                    onChange={e =>
                      setItemParaEditar({
                        ...itemParaEditar,
                        item: { ...itemParaEditar.item, Qtd: Number(e.target.value) }
                      })
                    }
                    className="w-full p-2 border border-slate-300 rounded-lg text-right font-medium"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Valor Unitário (R$):
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={itemParaEditar.item['Valor Unitário']}
                    onChange={e =>
                      setItemParaEditar({
                        ...itemParaEditar,
                        item: { ...itemParaEditar.item, 'Valor Unitário': Number(e.target.value) }
                      })
                    }
                    className="w-full p-2 border border-slate-300 rounded-lg text-right font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Fornecedor:
                  </label>
                  <input
                    type="text"
                    value={itemParaEditar.item.Fornecedor || ''}
                    onChange={e =>
                      setItemParaEditar({
                        ...itemParaEditar,
                        item: { ...itemParaEditar.item, Fornecedor: e.target.value }
                      })
                    }
                    className="w-full p-2 border border-slate-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    CNPJ:
                  </label>
                  <input
                    type="text"
                    value={itemParaEditar.item.CNPJ || ''}
                    onChange={e =>
                      setItemParaEditar({
                        ...itemParaEditar,
                        item: { ...itemParaEditar.item, CNPJ: e.target.value }
                      })
                    }
                    className="w-full p-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setItemParaEditar(null)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white font-medium hover:bg-emerald-800"
                >
                  Salvar Material
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
