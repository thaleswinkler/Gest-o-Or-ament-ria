import { useState, useMemo, type FormEvent } from 'react';
import { Plus, CreditCard, PackagePlus, Trash2, Edit2, Search, Check, AlertCircle, Building2 } from 'lucide-react';
import { BancoNCs, NotaCredito, ItemNC, SituacaoItem, PerfilUsuario } from '../types';
import { SubitemSelector } from './SubitemSelector';
import { consultarCNPJ, formatarCNPJ } from '../lib/cnpj';
import { formatarMoedaBRL } from '../lib/export';

interface TabCadastroProps {
  banco: BancoNCs;
  anoFiltro: string;
  perfil: PerfilUsuario;
  onSalvarNC: (chaveNC: string, nc: NotaCredito) => Promise<void>;
  onExcluirNC: (chaveNC: string) => Promise<void>;
  onSelecionarNCParaVisualizar: (chaveNC: string) => void;
}

export function TabCadastro({
  banco,
  anoFiltro,
  perfil,
  onSalvarNC,
  onExcluirNC,
  onSelecionarNCParaVisualizar
}: TabCadastroProps) {
  const isFiscal = perfil === 'Fiscal';

  // Estados de Nova NC
  const [modalNovaNC, setModalNovaNC] = useState(false);
  const [novaNCNumero, setNovaNCNumero] = useState('');
  const [novaNCND, setNovaNCND] = useState('339030');
  const [novaNCPI, setNovaNCPI] = useState('');
  const [novaNCValor, setNovaNCValor] = useState<number>(0);
  const [salvandoNC, setSalvandoNC] = useState(false);

  // Estados de Cadastro de Material
  const [ncAlvoMaterial, setNcAlvoMaterial] = useState<string>('');
  const [itemNome, setItemNome] = useState('');
  const [itemSubitem, setItemSubitem] = useState('');
  const [itemQtd, setItemQtd] = useState<number>(1);
  const [itemValorUnit, setItemValorUnit] = useState<number>(0);
  const [itemFornecedor, setItemFornecedor] = useState('');
  const [itemCNPJ, setItemCNPJ] = useState('');
  const [itemPregao, setItemPregao] = useState('');
  const [itemUASG, setItemUASG] = useState('');
  const [itemAta, setItemAta] = useState('');
  const [itemSituacao, setItemSituacao] = useState<SituacaoItem>('Planejamento');
  const [itemObs, setItemObs] = useState('');
  const [buscandoCNPJ, setBuscandoCNPJ] = useState(false);
  const [salvandoItem, setSalvandoItem] = useState(false);
  const [sucessoMsg, setSucessoMsg] = useState('');

  // Lista de NCs disponíveis para o ano
  const ncsDisponiveis = useMemo(() => {
    return Object.keys(banco).filter(k => {
      if (k === 'CONFIG_REQUISICAO') return false;
      if (anoFiltro && anoFiltro !== 'Todos' && !k.includes(anoFiltro)) return false;
      return true;
    }).sort();
  }, [banco, anoFiltro]);

  // Define NC selecionada padrão para cadastro de item
  const ncAtualObj = useMemo(() => {
    const chave = ncAlvoMaterial || ncsDisponiveis[0];
    if (chave && banco[chave]) {
      return { chave, dados: banco[chave] as NotaCredito };
    }
    return null;
  }, [ncAlvoMaterial, ncsDisponiveis, banco]);

  const proximoNumeroItem = useMemo(() => {
    if (!ncAtualObj?.dados?.itens) return 1;
    const max = ncAtualObj.dados.itens.reduce((acc, it) => Math.max(acc, it.Item || 0), 0);
    return max + 1;
  }, [ncAtualObj]);

  const handleCriarNC = async (e: FormEvent) => {
    e.preventDefault();
    if (!novaNCNumero.trim()) {
      alert('Informe o número da Nota de Crédito.');
      return;
    }
    setSalvandoNC(true);
    try {
      const chaveFinal = novaNCNumero.trim().toUpperCase();
      const nova: NotaCredito = {
        nd: novaNCND.trim(),
        pi: novaNCPI.trim(),
        valor_recebido: Number(novaNCValor) || 0,
        itens: []
      };
      await onSalvarNC(chaveFinal, nova);
      setModalNovaNC(false);
      setNovaNCNumero('');
      setNovaNCValor(0);
      setNovaNCPI('');
      setNcAlvoMaterial(chaveFinal);
    } catch (err: any) {
      alert(err.message || 'Erro ao criar NC');
    } finally {
      setSalvandoNC(false);
    }
  };

  const handleBuscarCNPJ = async () => {
    if (!itemCNPJ) return;
    setBuscandoCNPJ(true);
    try {
      const res = await consultarCNPJ(itemCNPJ);
      if (res) {
        setItemCNPJ(res.cnpj);
        if (res.razao_social) {
          setItemFornecedor(res.razao_social);
        }
      } else {
        alert('CNPJ não localizado na Receita.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setBuscandoCNPJ(false);
    }
  };

  const handleCadastrarItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!ncAtualObj) {
      alert('Selecione uma Nota de Crédito primeiro.');
      return;
    }
    if (!itemNome.trim()) {
      alert('Informe o nome/descrição do material.');
      return;
    }

    setSalvandoItem(true);
    try {
      const valorTotal = Number((itemQtd * itemValorUnit).toFixed(2));
      const novoItem: ItemNC = {
        Item: proximoNumeroItem,
        Subitem: itemSubitem || '01',
        Nome: itemNome.trim(),
        Qtd: Number(itemQtd) || 1,
        'Valor Unitário': Number(itemValorUnit) || 0,
        Total: valorTotal,
        Fornecedor: itemFornecedor.trim() || 'NÃO INFORMADO',
        CNPJ: itemCNPJ.trim() || '',
        Pregão: itemPregao.trim() || '',
        UASG: itemUASG.trim() || '',
        Ata: itemAta.trim() || '',
        Situação: itemSituacao,
        Obs: itemObs.trim() || ''
      };

      const ncAtualizada: NotaCredito = {
        ...ncAtualObj.dados,
        itens: [...(ncAtualObj.dados.itens || []), novoItem]
      };

      await onSalvarNC(ncAtualObj.chave, ncAtualizada);

      // Limpa formulário
      setItemNome('');
      setItemSubitem('');
      setItemQtd(1);
      setItemValorUnit(0);
      setItemFornecedor('');
      setItemCNPJ('');
      setItemObs('');

      setSucessoMsg(`Item nº ${novoItem.Item} cadastrado com sucesso na ${ncAtualObj.chave}!`);
      setTimeout(() => setSucessoMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Erro ao adicionar item.');
    } finally {
      setSalvandoItem(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Barra de Ações Rápidas */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Cadastro e Administração de Recursos
          </h2>
          <p className="text-xs text-slate-500">
            Cadastre novas Notas de Crédito (NCs) e lance materiais com classificação inteligente por função da ND.
          </p>
        </div>

        {!isFiscal && (
          <button
            onClick={() => setModalNovaNC(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            Nova Nota de Crédito (NC)
          </button>
        )}
      </div>

      {sucessoMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{sucessoMsg}</span>
        </div>
      )}

      {/* Grid Principal: Cadastro de Material + Lista de NCs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Formulário de Cadastro de Material (Coluna Esquerda/Principal) */}
        <div className="lg:col-span-7 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <PackagePlus className="w-5 h-5 text-emerald-700" />
              <h3 className="text-sm font-semibold text-slate-900">
                Lançamento de Material na NC
              </h3>
            </div>
            {ncAtualObj && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
                Próximo Item: #{proximoNumeroItem}
              </span>
            )}
          </div>

          {isFiscal ? (
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <strong>Acesso de Fiscalização:</strong> Seu perfil possui permissão somente de leitura. O cadastro e a alteração de materiais estão desabilitados.
              </div>
            </div>
          ) : ncsDisponiveis.length === 0 ? (
            <div className="text-center py-10 space-y-3">
              <CreditCard className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Nenhuma Nota de Crédito cadastrada para o ano selecionado ({anoFiltro}). Clique no botão "Nova Nota de Crédito" acima para começar.
              </p>
            </div>
          ) : (
            <form onSubmit={handleCadastrarItem} className="space-y-4">
              {/* Seletor da NC Alvo */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Nota de Crédito de Destino:
                </label>
                <select
                  value={ncAlvoMaterial || ncsDisponiveis[0]}
                  onChange={e => setNcAlvoMaterial(e.target.value)}
                  className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none font-semibold text-slate-800"
                >
                  {ncsDisponiveis.map(ncKey => {
                    const nc = banco[ncKey] as NotaCredito;
                    const totalItens = (nc.itens || []).length;
                    return (
                      <option key={ncKey} value={ncKey}>
                        {ncKey} — ND {nc.nd} (Rec: {formatarMoedaBRL(nc.valor_recebido)}) [{totalItens} itens]
                      </option>
                    );
                  })}
                </select>
              </div>

              {/* Descrição do Material */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Nome / Descrição Completa do Material:
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Óleo lubrificante SAE 15W40 para motores a diesel de viaturas"
                  value={itemNome}
                  onChange={e => setItemNome(e.target.value)}
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">
                  💡 Conforme você digita a descrição, o sistema analisa a FUNÇÃO oficial do SIAFI e sugere o subitem correspondente.
                </span>
              </div>

              {/* Seletor Inteligente de Subitem */}
              <SubitemSelector
                nd={ncAtualObj?.dados?.nd || '339030'}
                descricao={itemNome}
                value={itemSubitem}
                onChange={setItemSubitem}
              />

              {/* Quantidade e Valor Unitário */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Quantidade:
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="any"
                    required
                    value={itemQtd}
                    onChange={e => setItemQtd(Number(e.target.value))}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none text-right font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Valor Unitário (R$):
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    value={itemValorUnit}
                    onChange={e => setItemValorUnit(Number(e.target.value))}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none text-right font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Valor Total (R$):
                  </label>
                  <div className="w-full text-xs p-2 bg-slate-100 border border-slate-200 rounded-lg text-right font-bold text-slate-900">
                    {formatarMoedaBRL(itemQtd * itemValorUnit)}
                  </div>
                </div>
              </div>

              {/* Fornecedor e CNPJ */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    CNPJ do Fornecedor:
                  </label>
                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      placeholder="00.000.000/0000-00"
                      value={itemCNPJ}
                      onChange={e => setItemCNPJ(e.target.value)}
                      className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-mono"
                    />
                    <button
                      type="button"
                      onClick={handleBuscarCNPJ}
                      disabled={buscandoCNPJ || !itemCNPJ}
                      title="Consultar Razão Social na Receita Federal"
                      className="px-2.5 py-2 bg-slate-100 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-200 disabled:opacity-50 transition-colors"
                    >
                      <Search className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Nome / Razão Social do Fornecedor:
                  </label>
                  <input
                    type="text"
                    placeholder="Nome da empresa"
                    value={itemFornecedor}
                    onChange={e => setItemFornecedor(e.target.value)}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              {/* Pregão, UASG, Ata e Situação */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-[11px] font-medium text-slate-600 mb-1">
                    Pregão:
                  </label>
                  <input
                    type="text"
                    placeholder="Ex: 90012/2024"
                    value={itemPregao}
                    onChange={e => setItemPregao(e.target.value)}
                    className="w-full text-xs p-1.5 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-600 mb-1">
                    UASG:
                  </label>
                  <input
                    type="text"
                    placeholder="Ex: 160001 (6 dígitos)"
                    value={itemUASG}
                    onChange={e => setItemUASG(e.target.value)}
                    className="w-full text-xs p-1.5 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-600 mb-1">
                    Ata SRP:
                  </label>
                  <input
                    type="text"
                    placeholder="Ex: 15/2024"
                    value={itemAta}
                    onChange={e => setItemAta(e.target.value)}
                    className="w-full text-xs p-1.5 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-600 mb-1">
                    Situação:
                  </label>
                  <select
                    value={itemSituacao}
                    onChange={e => setItemSituacao(e.target.value as SituacaoItem)}
                    className="w-full text-xs p-1.5 bg-white border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium"
                  >
                    <option value="Planejamento">Planejamento</option>
                    <option value="Aguardando entrega">Aguardando entrega</option>
                    <option value="Recebido">Recebido</option>
                  </select>
                </div>
              </div>

              {/* Botão de Lançar Item */}
              <div className="pt-3 flex justify-end">
                <button
                  type="submit"
                  disabled={salvandoItem}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
                >
                  <PackagePlus className="w-4 h-4" />
                  {salvandoItem ? 'Salvando...' : 'Adicionar Material à NC'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Lista de NCs Cadastradas (Coluna Direita) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-emerald-700" />
                Notas de Crédito ({ncsDisponiveis.length})
              </h3>
              <span className="text-[11px] text-slate-500 font-medium">
                Ano: {anoFiltro}
              </span>
            </div>

            {ncsDisponiveis.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">
                Nenhuma NC encontrada.
              </p>
            ) : (
              <div className="space-y-3 max-h-[580px] overflow-y-auto pr-1">
                {ncsDisponiveis.map(chaveNC => {
                  const nc = banco[chaveNC] as NotaCredito;
                  const itens = nc.itens || [];
                  const totalGasto = itens.reduce((acc, it) => acc + (it.Total || 0), 0);
                  const saldo = (nc.valor_recebido || 0) - totalGasto;
                  const pctExec = nc.valor_recebido > 0
                    ? Math.min(100, Math.round((totalGasto / nc.valor_recebido) * 100))
                    : 0;

                  return (
                    <div
                      key={chaveNC}
                      className="p-3.5 rounded-lg border border-slate-200 hover:border-emerald-300 transition-colors bg-slate-50/60 space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold text-xs text-slate-900 flex items-center gap-1.5">
                            <span>{chaveNC}</span>
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-100 text-emerald-800">
                              ND {nc.nd}
                            </span>
                          </div>
                          {nc.pi && (
                            <p className="text-[10px] text-slate-500">PI: {nc.pi}</p>
                          )}
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => onSelecionarNCParaVisualizar(chaveNC)}
                            title="Abrir detalhes e emitir requisição"
                            className="px-2 py-1 text-[11px] font-medium text-emerald-700 bg-white border border-emerald-300 rounded hover:bg-emerald-50 transition-colors"
                          >
                            Ver / Editar
                          </button>
                          {!isFiscal && (
                            <button
                              onClick={() => {
                                if (confirm(`Deseja realmente excluir a ${chaveNC} e todos os seus itens?`)) {
                                  onExcluirNC(chaveNC);
                                }
                              }}
                              title="Excluir NC"
                              className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Valores */}
                      <div className="grid grid-cols-3 text-[11px] pt-1 border-t border-slate-200/60">
                        <div>
                          <span className="text-slate-400 block text-[10px]">Recebido:</span>
                          <span className="font-medium text-slate-800">{formatarMoedaBRL(nc.valor_recebido)}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Alocado ({itens.length}):</span>
                          <span className="font-medium text-slate-800">{formatarMoedaBRL(totalGasto)}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-slate-400 block text-[10px]">Saldo:</span>
                          <span className={`font-semibold ${saldo < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {formatarMoedaBRL(saldo)}
                          </span>
                        </div>
                      </div>

                      {/* Barra de progresso */}
                      <div className="space-y-0.5">
                        <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full transition-all ${
                              pctExec > 95 ? 'bg-amber-600' : 'bg-emerald-600'
                            }`}
                            style={{ width: `${pctExec}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[9px] text-slate-400">
                          <span>Execução</span>
                          <span>{pctExec}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal: Nova Nota de Crédito */}
      {modalNovaNC && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-emerald-700" />
                Criar Nova Nota de Crédito (NC)
              </h3>
              <button
                onClick={() => setModalNovaNC(false)}
                className="text-slate-400 hover:text-slate-700 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCriarNC} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Número / Identificação da NC:
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: 2026NC000123 ou 2026NC Material Expediente"
                  value={novaNCNumero}
                  onChange={e => setNovaNCNumero(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-semibold"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Natureza da Despesa (ND):
                  </label>
                  <select
                    value={novaNCND}
                    onChange={e => setNovaNCND(e.target.value)}
                    className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-mono font-medium"
                  >
                    <option value="339030">339030 (Consumo)</option>
                    <option value="449052">449052 (Permanente/Equip)</option>
                    <option value="339039">339039 (Serviços de Terceiros)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Programa de Trabalho / PI:
                  </label>
                  <input
                    type="text"
                    placeholder="Ex: H2004..."
                    value={novaNCPI}
                    onChange={e => setNovaNCPI(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Valor Recebido da NC (R$):
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  value={novaNCValor}
                  onChange={e => setNovaNCValor(Number(e.target.value))}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-mono text-right text-sm font-semibold"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setModalNovaNC(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={salvandoNC}
                  className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white font-medium hover:bg-emerald-800 disabled:opacity-50"
                >
                  {salvandoNC ? 'Criando...' : 'Cadastrar NC'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
