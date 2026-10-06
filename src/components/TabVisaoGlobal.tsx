import { useMemo, useState } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Download, 
  Layers, 
  CheckCircle2, 
  Clock, 
  FileSpreadsheet,
  PieChart,
  Printer,
  X,
  Search,
  Building2,
  PackageCheck
} from 'lucide-react';
import { BancoNCs, NotaCredito, ItemNC } from '../types';
import { formatarMoedaBRL, exportarPlanilhaGlobal } from '../lib/export';

interface TabVisaoGlobalProps {
  banco: BancoNCs;
  anoFiltro: string;
  om: string;
  secao: string;
}

export function TabVisaoGlobal({
  banco,
  anoFiltro,
  om,
  secao
}: TabVisaoGlobalProps) {
  const [relatorioModalAberto, setRelatorioModalAberto] = useState(false);
  const [filtroItens, setFiltroItens] = useState('');

  // Coleta todas as NCs válidas
  const listaNCs = useMemo(() => {
    const arr: Array<{ chave: string; nc: NotaCredito }> = [];
    for (const [chave, val] of Object.entries(banco)) {
      if (chave === 'CONFIG_REQUISICAO' || !val || typeof val !== 'object') continue;
      if (anoFiltro && anoFiltro !== 'Todos' && !chave.includes(anoFiltro)) continue;
      arr.push({ chave, nc: val as NotaCredito });
    }
    return arr.sort((a, b) => a.chave.localeCompare(b.chave));
  }, [banco, anoFiltro]);

  // Coleta todos os itens de todas as NCs do ano
  const todosItensAno = useMemo(() => {
    const itens: Array<ItemNC & { chaveNC: string; ndNC: string; piNC?: string }> = [];
    for (const { chave, nc } of listaNCs) {
      for (const it of nc.itens || []) {
        itens.push({
          ...it,
          chaveNC: chave,
          ndNC: nc.nd || '-',
          piNC: nc.pi || '-'
        });
      }
    }
    return itens;
  }, [listaNCs]);

  // Estatísticas Globais
  const estatisticas = useMemo(() => {
    let totalRecebido = 0;
    let totalGasto = 0;
    let totalItens = 0;
    let totalQtdUnidades = 0;

    const porND: Record<string, { recebido: number; gasto: number; itens: number }> = {
      '339030': { recebido: 0, gasto: 0, itens: 0 },
      '449052': { recebido: 0, gasto: 0, itens: 0 },
      '339039': { recebido: 0, gasto: 0, itens: 0 },
      'Outras': { recebido: 0, gasto: 0, itens: 0 }
    };

    const porSituacao = {
      Planejamento: { qtd: 0, valor: 0 },
      'Aguardando entrega': { qtd: 0, valor: 0 },
      Recebido: { qtd: 0, valor: 0 }
    };

    const porFornecedor: Record<string, number> = {};

    for (const item of listaNCs) {
      const nc = item.nc;
      const rec = nc.valor_recebido || 0;
      totalRecebido += rec;

      const ndLimpa = String(nc.nd || '').replace(/\D/g, '');
      let grupoND = 'Outras';
      if (ndLimpa.includes('339030') || ndLimpa.includes('30')) grupoND = '339030';
      else if (ndLimpa.includes('449052') || ndLimpa.includes('52')) grupoND = '449052';
      else if (ndLimpa.includes('339039') || ndLimpa.includes('39')) grupoND = '339039';

      porND[grupoND].recebido += rec;

      for (const it of nc.itens || []) {
        const val = it.Total || 0;
        const qtd = Number(it.Qtd) || 0;
        totalGasto += val;
        totalItens += 1;
        totalQtdUnidades += qtd;
        porND[grupoND].gasto += val;
        porND[grupoND].itens += 1;

        const sit = it.Situação || 'Planejamento';
        if (porSituacao[sit]) {
          porSituacao[sit].qtd += 1;
          porSituacao[sit].valor += val;
        }

        const forn = (it.Fornecedor || 'Não informado').trim();
        porFornecedor[forn] = (porFornecedor[forn] || 0) + val;
      }
    }

    const saldo = totalRecebido - totalGasto;
    const pct = totalRecebido > 0 ? Math.min(100, Math.round((totalGasto / totalRecebido) * 100)) : 0;

    const topFornecedores = Object.entries(porFornecedor)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);

    return {
      totalRecebido,
      totalGasto,
      saldo,
      pct,
      totalItens,
      totalQtdUnidades,
      porND,
      porSituacao,
      topFornecedores
    };
  }, [listaNCs]);

  // Itens filtrados para exibição
  const itensFiltrados = useMemo(() => {
    if (!filtroItens.trim()) return todosItensAno;
    const t = filtroItens.toLowerCase();
    return todosItensAno.filter(it => 
      (it.Nome || '').toLowerCase().includes(t) ||
      (it.Fornecedor || '').toLowerCase().includes(t) ||
      (it.chaveNC || '').toLowerCase().includes(t) ||
      (it.Pregão || '').toLowerCase().includes(t)
    );
  }, [todosItensAno, filtroItens]);

  const configReq = (banco as any)?.CONFIG_REQUISICAO || {};
  const dataHoje = new Date().toLocaleDateString('pt-BR');

  return (
    <div className="space-y-6">
      {/* Cabeçalho do Painel */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-emerald-700" />
            Visão Global e Painel Gerencial do Exercício
          </h2>
          <p className="text-xs text-slate-500">
            Consolidação orçamentária da OM {om} • Seção {secao} • Ano: {anoFiltro} ({listaNCs.length} NCs • {todosItensAno.length} itens)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setRelatorioModalAberto(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4" />
            📑 Gerar Relatório Anual (PDF / Impressão)
          </button>

          <button
            onClick={() => exportarPlanilhaGlobal(banco, anoFiltro)}
            className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium border border-slate-300 transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            Exportar Planilha (.csv)
          </button>
        </div>
      </div>

      {/* Cards de Destaque Executivo */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Orçado em NCs
          </span>
          <div className="text-2xl font-bold text-slate-900">
            {formatarMoedaBRL(estatisticas.totalRecebido)}
          </div>
          <span className="text-[11px] text-slate-500 block">
            {listaNCs.length} Notas de Crédito ativas
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Alocado / Requisitado
          </span>
          <div className="text-2xl font-bold text-slate-800">
            {formatarMoedaBRL(estatisticas.totalGasto)}
          </div>
          <span className="text-[11px] text-slate-500 block">
            {estatisticas.totalItens} materiais ({estatisticas.totalQtdUnidades} unidades)
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Saldo Disponível Global
          </span>
          <div className={`text-2xl font-bold ${estatisticas.saldo < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
            {formatarMoedaBRL(estatisticas.saldo)}
          </div>
          <span className="text-[11px] text-slate-500 block">
            Disponível para novas aquisições
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Taxa de Execução
            </span>
            <span className="text-sm font-bold text-slate-900">{estatisticas.pct}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-2.5 rounded-full transition-all ${
                estatisticas.pct > 95 ? 'bg-amber-500' : 'bg-emerald-600'
              }`}
              style={{ width: `${estatisticas.pct}%` }}
            />
          </div>
          <span className="text-[10px] text-slate-400 block">
            Índice de empenho e alocação orçamentária
          </span>
        </div>
      </div>

      {/* Detalhamento por Natureza de Despesa (ND) */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
        <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-700" />
          Execução Orçamentária por Natureza de Despesa (ND)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* ND 339030 */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-100 text-emerald-800">
                ND 339030
              </span>
              <span className="text-xs font-semibold text-slate-600">Material de Consumo</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-500">
                <span>Orçado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['339030'].recebido)}
                </span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Alocado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['339030'].gasto)}
                </span>
              </div>
              <div className="flex justify-between border-t pt-1 font-bold">
                <span>Saldo:</span>
                <span className="text-emerald-700">
                  {formatarMoedaBRL(estatisticas.porND['339030'].recebido - estatisticas.porND['339030'].gasto)}
                </span>
              </div>
            </div>
          </div>

          {/* ND 449052 */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-blue-100 text-blue-800">
                ND 449052
              </span>
              <span className="text-xs font-semibold text-slate-600">Material Permanente</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-500">
                <span>Orçado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['449052'].recebido)}
                </span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Alocado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['449052'].gasto)}
                </span>
              </div>
              <div className="flex justify-between border-t pt-1 font-bold">
                <span>Saldo:</span>
                <span className="text-blue-700">
                  {formatarMoedaBRL(estatisticas.porND['449052'].recebido - estatisticas.porND['449052'].gasto)}
                </span>
              </div>
            </div>
          </div>

          {/* ND 339039 */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-purple-100 text-purple-800">
                ND 339039
              </span>
              <span className="text-xs font-semibold text-slate-600">Outros Serviços Terceiros</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-500">
                <span>Orçado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['339039'].recebido)}
                </span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Alocado:</span>
                <span className="font-semibold text-slate-800">
                  {formatarMoedaBRL(estatisticas.porND['339039'].gasto)}
                </span>
              </div>
              <div className="flex justify-between border-t pt-1 font-bold">
                <span>Saldo:</span>
                <span className="text-purple-700">
                  {formatarMoedaBRL(estatisticas.porND['339039'].recebido - estatisticas.porND['339039'].gasto)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Situação dos Materiais e Top Fornecedores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-emerald-700" />
            Status de Aquisição e Entrega dos Materiais
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-center space-y-1">
              <span className="text-xs font-semibold text-slate-600">Planejamento</span>
              <div className="text-xl font-bold text-slate-800">
                {estatisticas.porSituacao['Planejamento'].qtd} itens
              </div>
              <span className="text-xs font-mono text-slate-500">
                {formatarMoedaBRL(estatisticas.porSituacao['Planejamento'].valor)}
              </span>
            </div>

            <div className="p-4 rounded-lg bg-amber-50/60 border border-amber-200 text-center space-y-1">
              <span className="text-xs font-semibold text-amber-800">Aguardando Entrega</span>
              <div className="text-xl font-bold text-amber-900">
                {estatisticas.porSituacao['Aguardando entrega'].qtd} itens
              </div>
              <span className="text-xs font-mono text-amber-700 font-medium">
                {formatarMoedaBRL(estatisticas.porSituacao['Aguardando entrega'].valor)}
              </span>
            </div>

            <div className="p-4 rounded-lg bg-emerald-50/60 border border-emerald-200 text-center space-y-1">
              <span className="text-xs font-semibold text-emerald-800">Recebido / Concluído</span>
              <div className="text-xl font-bold text-emerald-900">
                {estatisticas.porSituacao['Recebido'].qtd} itens
              </div>
              <span className="text-xs font-mono text-emerald-700 font-medium">
                {formatarMoedaBRL(estatisticas.porSituacao['Recebido'].valor)}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-700" />
            Top Fornecedores do Ano
          </h3>
          <div className="space-y-2">
            {estatisticas.topFornecedores.length === 0 ? (
              <p className="text-xs text-slate-400">Nenhum fornecedor registrado.</p>
            ) : (
              estatisticas.topFornecedores.map(([forn, valor], idx) => (
                <div key={idx} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1.5">
                  <span className="truncate max-w-[170px] text-slate-700 font-medium">{forn}</span>
                  <span className="font-mono font-semibold text-slate-900">{formatarMoedaBRL(valor)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Tabela Resumo de Todas as NCs */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200/80 bg-slate-50/50">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Tabela Consolidada de Notas de Crédito ({listaNCs.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/80 text-slate-700 font-semibold border-b border-slate-200">
                <th className="px-4 py-2.5">Nota de Crédito</th>
                <th className="px-4 py-2.5 text-center">ND</th>
                <th className="px-4 py-2.5 text-center">PI</th>
                <th className="px-4 py-2.5 text-center">Itens</th>
                <th className="px-4 py-2.5 text-right">Valor Recebido</th>
                <th className="px-4 py-2.5 text-right">Total Alocado</th>
                <th className="px-4 py-2.5 text-right">Saldo Disponível</th>
                <th className="px-4 py-2.5 text-center">Execução</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70">
              {listaNCs.map(({ chave, nc }) => {
                const itensCount = (nc.itens || []).length;
                const gasto = (nc.itens || []).reduce((acc, it) => acc + (it.Total || 0), 0);
                const saldo = (nc.valor_recebido || 0) - gasto;
                const pct = nc.valor_recebido > 0 ? Math.min(100, Math.round((gasto / nc.valor_recebido) * 100)) : 0;

                return (
                  <tr key={chave} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-900">{chave}</td>
                    <td className="px-4 py-3 text-center font-mono font-medium">{nc.nd || '-'}</td>
                    <td className="px-4 py-3 text-center font-mono text-slate-500">{nc.pi || '-'}</td>
                    <td className="px-4 py-3 text-center">{itensCount}</td>
                    <td className="px-4 py-3 text-right font-mono">{formatarMoedaBRL(nc.valor_recebido)}</td>
                    <td className="px-4 py-3 text-right font-mono font-medium">{formatarMoedaBRL(gasto)}</td>
                    <td className={`px-4 py-3 text-right font-mono font-bold ${saldo < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                      {formatarMoedaBRL(saldo)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                        {pct}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Listagem Geral de Todos os Itens Adquiridos no Ano (com Quantidades) */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <PackageCheck className="w-4 h-4 text-emerald-700" />
              Listagem Completa de Itens Adquiridos no Ano ({todosItensAno.length} materiais cadastrados)
            </h3>
            <p className="text-xs text-slate-500">
              Discriminação de todas as aquisições, quantidades e valores de {anoFiltro}
            </p>
          </div>

          <div className="relative w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar item, fornecedor ou NC..."
              value={filtroItens}
              onChange={e => setFiltroItens(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-600"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/80 text-slate-700 font-semibold border-b border-slate-200">
                <th className="px-3 py-2">Item</th>
                <th className="px-3 py-2">NC Vinculada</th>
                <th className="px-3 py-2">ND</th>
                <th className="px-3 py-2">Subitem</th>
                <th className="px-3 py-2">Descrição do Material</th>
                <th className="px-3 py-2 text-center font-bold text-emerald-800 bg-emerald-50/60">Quantidade</th>
                <th className="px-3 py-2 text-right">Valor Unitário</th>
                <th className="px-3 py-2 text-right">Valor Total</th>
                <th className="px-3 py-2 text-center">Situação</th>
                <th className="px-3 py-2">Fornecedor</th>
                <th className="px-3 py-2">Pregão / Ata</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70">
              {itensFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={11} className="px-4 py-8 text-center text-slate-400">
                    Nenhum item encontrado com os critérios de busca.
                  </td>
                </tr>
              ) : (
                itensFiltrados.map((it, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="px-3 py-2 text-slate-500">{it.Item || idx + 1}</td>
                    <td className="px-3 py-2 font-mono font-medium text-slate-900">{it.chaveNC}</td>
                    <td className="px-3 py-2 font-mono text-slate-600">{it.ndNC}</td>
                    <td className="px-3 py-2 font-mono text-slate-600">{it.Subitem || '-'}</td>
                    <td className="px-3 py-2 font-medium text-slate-800 max-w-xs truncate">{it.Nome}</td>
                    <td className="px-3 py-2 text-center font-bold text-emerald-700 bg-emerald-50/40">
                      {it.Qtd || 0}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{formatarMoedaBRL(it['Valor Unitário'] || 0)}</td>
                    <td className="px-3 py-2 text-right font-mono font-bold text-slate-900">{formatarMoedaBRL(it.Total || 0)}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        it.Situação === 'Recebido' ? 'bg-emerald-100 text-emerald-800' :
                        it.Situação === 'Aguardando entrega' ? 'bg-amber-100 text-amber-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {it.Situação || 'Planejamento'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-600 max-w-[150px] truncate">{it.Fornecedor || '-'}</td>
                    <td className="px-3 py-2 text-slate-500 font-mono text-[11px]">{it.Pregão || it.Ata || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
            {itensFiltrados.length > 0 && (
              <tfoot>
                <tr className="bg-slate-100 font-bold border-t-2 border-slate-300 text-slate-900">
                  <td colSpan={5} className="px-3 py-2.5 text-right uppercase text-[11px]">
                    Totais Consolidados ({itensFiltrados.length} itens):
                  </td>
                  <td className="px-3 py-2.5 text-center text-emerald-800 bg-emerald-100/50">
                    {itensFiltrados.reduce((acc, it) => acc + (Number(it.Qtd) || 0), 0)} unid.
                  </td>
                  <td className="px-3 py-2.5"></td>
                  <td className="px-3 py-2.5 text-right font-mono text-emerald-900">
                    {formatarMoedaBRL(itensFiltrados.reduce((acc, it) => acc + (it.Total || 0), 0))}
                  </td>
                  <td colSpan={3}></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* MODAL / VISUALIZAÇÃO DO RELATÓRIO ANUAL OFICIAL (DOCUMENTO PARA IMPRESSÃO/PDF) */}
      {/* ========================================================================= */}
      {relatorioModalAberto && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto print:p-0 print:bg-white print:static">
          <div className="bg-white rounded-2xl max-w-5xl w-full max-h-[92vh] overflow-y-auto shadow-2xl border border-slate-200 print:max-h-none print:shadow-none print:border-none">
            {/* Barra Superior de Ações (Ocultada na Impressão) */}
            <div className="sticky top-0 bg-slate-900 text-white p-4 flex items-center justify-between z-10 print:hidden">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                <span className="font-bold text-sm">Visualização do Relatório Anual Oficial - Exercício {anoFiltro}</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold cursor-pointer transition-colors"
                >
                  <Printer className="w-4 h-4" />
                  Imprimir / Salvar em PDF
                </button>
                <button
                  onClick={() => setRelatorioModalAberto(false)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Documento Oficial Formatado */}
            <div className="p-8 sm:p-12 space-y-8 print:p-0 font-sans text-slate-900">
              {/* Cabeçalho Militar */}
              <div className="text-center space-y-1 pb-6 border-b-2 border-slate-900">
                <div className="text-xs font-bold uppercase tracking-widest text-slate-700">MINISTÉRIO DA DEFESA</div>
                <div className="text-sm font-black uppercase tracking-wider text-slate-900">EXÉRCITO BRASILEIRO</div>
                <div className="text-xs font-semibold text-slate-800">{om || 'ORGANIZAÇÃO MILITAR'}</div>
                <div className="text-xs text-slate-600">{secao || 'SEÇÃO DE AQUISIÇÕES'}</div>
                <div className="pt-4">
                  <h1 className="text-base font-extrabold uppercase tracking-wide text-slate-900">
                    RELATÓRIO ANUAL DE EXECUÇÃO ORÇAMENTÁRIA E AQUISIÇÕES
                  </h1>
                  <p className="text-xs text-slate-600">
                    Exercício Financeiro: <b>{anoFiltro}</b> • Data de Emissão: {dataHoje}
                  </p>
                </div>
              </div>

              {/* 1. Balanço de Recursos Orçamentários */}
              <div className="space-y-4">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-1">
                  1. Balanço de Recursos Orçamentários e Créditos Concedidos
                </h2>

                <div className="grid grid-cols-4 gap-3 text-center">
                  <div className="p-3 border border-slate-300 rounded-lg bg-slate-50">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Concedido</span>
                    <span className="text-sm font-extrabold text-slate-900">{formatarMoedaBRL(estatisticas.totalRecebido)}</span>
                  </div>
                  <div className="p-3 border border-slate-300 rounded-lg bg-slate-50">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Empenhado</span>
                    <span className="text-sm font-extrabold text-slate-900">{formatarMoedaBRL(estatisticas.totalGasto)}</span>
                  </div>
                  <div className="p-3 border border-slate-300 rounded-lg bg-slate-50">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Saldo Disponível</span>
                    <span className={`text-sm font-extrabold ${estatisticas.saldo < 0 ? 'text-red-700' : 'text-emerald-800'}`}>
                      {formatarMoedaBRL(estatisticas.saldo)}
                    </span>
                  </div>
                  <div className="p-3 border border-slate-300 rounded-lg bg-slate-50">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Taxa de Execução</span>
                    <span className="text-sm font-extrabold text-slate-900">{estatisticas.pct}%</span>
                  </div>
                </div>

                {/* Tabela de Notas de Crédito */}
                <table className="w-full text-[11px] border border-slate-300 border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300">
                      <th className="p-2 text-left border-r border-slate-300">Nota de Crédito</th>
                      <th className="p-2 text-center border-r border-slate-300">ND</th>
                      <th className="p-2 text-center border-r border-slate-300">PI</th>
                      <th className="p-2 text-center border-r border-slate-300">Itens</th>
                      <th className="p-2 text-right border-r border-slate-300">Valor Concedido</th>
                      <th className="p-2 text-right border-r border-slate-300">Total Alocado</th>
                      <th className="p-2 text-right border-r border-slate-300">Saldo</th>
                      <th className="p-2 text-center">Execução</th>
                    </tr>
                  </thead>
                  <tbody>
                    {listaNCs.map(({ chave, nc }) => {
                      const gasto = (nc.itens || []).reduce((acc, it) => acc + (it.Total || 0), 0);
                      const saldo = (nc.valor_recebido || 0) - gasto;
                      const pct = nc.valor_recebido > 0 ? Math.round((gasto / nc.valor_recebido) * 100) : 0;
                      return (
                        <tr key={chave} className="border-b border-slate-200">
                          <td className="p-2 font-mono font-bold border-r border-slate-200">{chave}</td>
                          <td className="p-2 text-center font-mono border-r border-slate-200">{nc.nd || '-'}</td>
                          <td className="p-2 text-center font-mono border-r border-slate-200">{nc.pi || '-'}</td>
                          <td className="p-2 text-center border-r border-slate-200">{(nc.itens || []).length}</td>
                          <td className="p-2 text-right font-mono border-r border-slate-200">{formatarMoedaBRL(nc.valor_recebido)}</td>
                          <td className="p-2 text-right font-mono border-r border-slate-200">{formatarMoedaBRL(gasto)}</td>
                          <td className="p-2 text-right font-mono font-bold border-r border-slate-200">{formatarMoedaBRL(saldo)}</td>
                          <td className="p-2 text-center font-semibold">{pct}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="bg-slate-100 font-bold border-t-2 border-slate-400">
                      <td colSpan={4} className="p-2 text-right uppercase">Total Consolidado:</td>
                      <td className="p-2 text-right font-mono border-r border-slate-300">{formatarMoedaBRL(estatisticas.totalRecebido)}</td>
                      <td className="p-2 text-right font-mono border-r border-slate-300">{formatarMoedaBRL(estatisticas.totalGasto)}</td>
                      <td className="p-2 text-right font-mono border-r border-slate-300">{formatarMoedaBRL(estatisticas.saldo)}</td>
                      <td className="p-2 text-center">{estatisticas.pct}%</td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* 2. Distribuição dos Recursos e Gráficos */}
              <div className="space-y-4">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-1">
                  2. Distribuição Orçamentária por Natureza de Despesa e Situação
                </h2>

                <div className="grid grid-cols-3 gap-4 text-xs">
                  {Object.entries(estatisticas.porND).filter(([k]) => k !== 'Outras' || estatisticas.porND[k].gasto > 0).map(([nd, valRaw]) => {
                    const val = valRaw as { recebido: number; gasto: number };
                    return (
                    <div key={nd} className="p-3 border border-slate-200 rounded-lg bg-slate-50 space-y-1">
                      <span className="font-mono font-bold text-slate-800 block">ND {nd}</span>
                      <div className="flex justify-between text-[11px] text-slate-600">
                        <span>Orçado:</span>
                        <span className="font-semibold">{formatarMoedaBRL(val.recebido)}</span>
                      </div>
                      <div className="flex justify-between text-[11px] text-slate-600">
                        <span>Alocado:</span>
                        <span className="font-semibold">{formatarMoedaBRL(val.gasto)}</span>
                      </div>
                      <div className="flex justify-between text-[11px] font-bold border-t border-slate-200 pt-1">
                        <span>Saldo:</span>
                        <span className="text-emerald-700">{formatarMoedaBRL(val.recebido - val.gasto)}</span>
                      </div>
                    </div>
                  );
                })}
                </div>
              </div>

              {/* 3. Listagem Geral de Todos os Itens Adquiridos no Ano */}
              <div className="space-y-4">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-1">
                  3. Listagem Discriminada de Todos os Itens Adquiridos no Exercício ({todosItensAno.length} itens • {estatisticas.totalQtdUnidades} unidades)
                </h2>

                <table className="w-full text-[10px] border border-slate-300 border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300">
                      <th className="p-1.5 text-center border-r border-slate-300">Item</th>
                      <th className="p-1.5 text-left border-r border-slate-300">NC</th>
                      <th className="p-1.5 text-center border-r border-slate-300">Subitem</th>
                      <th className="p-1.5 text-left border-r border-slate-300">Descrição do Material</th>
                      <th className="p-1.5 text-center font-bold border-r border-slate-300 bg-slate-200/60">Qtd</th>
                      <th className="p-1.5 text-right border-r border-slate-300">Valor Unit.</th>
                      <th className="p-1.5 text-right border-r border-slate-300">Total (R$)</th>
                      <th className="p-1.5 text-center border-r border-slate-300">Situação</th>
                      <th className="p-1.5 text-left border-r border-slate-300">Fornecedor</th>
                      <th className="p-1.5 text-left">Pregão / Ata</th>
                    </tr>
                  </thead>
                  <tbody>
                    {todosItensAno.map((it, idx) => (
                      <tr key={idx} className="border-b border-slate-200">
                        <td className="p-1.5 text-center border-r border-slate-200">{it.Item || idx + 1}</td>
                        <td className="p-1.5 font-mono font-medium border-r border-slate-200">{it.chaveNC}</td>
                        <td className="p-1.5 text-center font-mono border-r border-slate-200">{it.Subitem || '-'}</td>
                        <td className="p-1.5 font-medium border-r border-slate-200 max-w-xs">{it.Nome}</td>
                        <td className="p-1.5 text-center font-bold border-r border-slate-200 bg-slate-50">{it.Qtd || 0}</td>
                        <td className="p-1.5 text-right font-mono border-r border-slate-200">{formatarMoedaBRL(it['Valor Unitário'] || 0)}</td>
                        <td className="p-1.5 text-right font-mono font-bold border-r border-slate-200">{formatarMoedaBRL(it.Total || 0)}</td>
                        <td className="p-1.5 text-center border-r border-slate-200">{it.Situação || 'Planejamento'}</td>
                        <td className="p-1.5 border-r border-slate-200 truncate max-w-[130px]">{it.Fornecedor || '-'}</td>
                        <td className="p-1.5 font-mono">{it.Pregão || it.Ata || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-slate-100 font-bold border-t-2 border-slate-400">
                      <td colSpan={4} className="p-2 text-right uppercase">Soma Geral dos Itens:</td>
                      <td className="p-2 text-center bg-slate-200/80 font-bold">{estatisticas.totalQtdUnidades}</td>
                      <td className="p-2"></td>
                      <td className="p-2 text-right font-mono font-bold">{formatarMoedaBRL(estatisticas.totalGasto)}</td>
                      <td colSpan={3}></td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* 4. Termo de Encerramento e Assinaturas */}
              <div className="pt-8 space-y-12">
                <p className="text-center text-xs text-slate-600">
                  Certifico que os recursos orçamentários e itens constantes deste relatório anual foram devidamente conferidos e espelham a exata execução das Notas de Crédito do exercício de {anoFiltro}.
                </p>

                <div className="flex justify-around pt-6 text-center">
                  <div className="space-y-1 min-w-[220px]">
                    <div className="border-t border-slate-900 w-52 mx-auto mb-1"></div>
                    <div className="text-xs font-bold text-slate-900">{configReq.assinatura_nome || 'Chefe da Seção'}</div>
                    <div className="text-[11px] text-slate-500">{configReq.assinatura_funcao || `Chefe da ${secao}`}</div>
                  </div>

                  <div className="space-y-1 min-w-[220px]">
                    <div className="border-t border-slate-900 w-52 mx-auto mb-1"></div>
                    <div className="text-xs font-bold text-slate-900">{configReq.od_nome || 'Ordenador de Despesas'}</div>
                    <div className="text-[11px] text-slate-500">{configReq.od_funcao || 'Ordenador de Despesas'}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

