import { useState, useMemo, type FormEvent } from 'react';
import { X, Printer, Settings, Building2, PackageCheck } from 'lucide-react';
import { NotaCredito, ConfigRequisicao, ItemNC } from '../types';
import { formatarMoedaBRL } from '../lib/export';

interface RequisicaoModalProps {
  chaveNC: string;
  nc: NotaCredito;
  config: ConfigRequisicao;
  fornecedorInicial?: string;
  onSalvarConfig: (novaConfig: ConfigRequisicao) => Promise<void>;
  onClose: () => void;
}

export function RequisicaoModal({
  chaveNC,
  nc,
  config,
  fornecedorInicial,
  onSalvarConfig,
  onClose
}: RequisicaoModalProps) {
  const [modoEdicaoConfig, setModoEdicaoConfig] = useState(false);
  const [formConfig, setFormConfig] = useState<ConfigRequisicao>({ ...config });
  const [salvando, setSalvando] = useState(false);
  const [fornecedorSelecionado, setFornecedorSelecionado] = useState<string>(
    fornecedorInicial || 'TODOS'
  );

  // Lista de fornecedores presentes nesta NC
  const listaFornecedores = useMemo(() => {
    const s = new Set<string>();
    (nc.itens || []).forEach(it => {
      if (it.Fornecedor && it.Fornecedor.trim()) {
        s.add(it.Fornecedor.trim());
      }
    });
    return Array.from(s).sort();
  }, [nc.itens]);

  // Itens filtrados para o documento
  const itensExibidos = useMemo(() => {
    if (fornecedorSelecionado === 'TODOS') {
      return nc.itens || [];
    }
    return (nc.itens || []).filter(it => (it.Fornecedor || '').trim() === fornecedorSelecionado);
  }, [nc.itens, fornecedorSelecionado]);

  const totalRequisicao = useMemo(() => {
    return itensExibidos.reduce((acc, it) => acc + (it.Total || 0), 0);
  }, [itensExibidos]);

  // Metadados do fornecedor selecionado (DIEx, EB, Data, Assunto, etc)
  const infoForn = useMemo(() => {
    if (fornecedorSelecionado !== 'TODOS' && nc.doc_info && nc.doc_info[fornecedorSelecionado]) {
      return nc.doc_info[fornecedorSelecionado];
    }
    return null;
  }, [nc.doc_info, fornecedorSelecionado]);

  const primeiroItem = itensExibidos[0] as ItemNC | undefined;
  const pregaoAtual = primeiroItem?.Pregão || '';
  const uasgAtual = primeiroItem?.UASG || '';
  const cnpjAtual = primeiroItem?.CNPJ || '';

  const diexDisplay = infoForn?.diex ? infoForn.diex : '______';
  const ebDisplay = infoForn?.eb ? infoForn.eb : '_________________';
  const dataDisplay = infoForn?.data 
    ? infoForn.data 
    : new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
  const assuntoDisplay = infoForn?.assunto ? infoForn.assunto : 'aquisição de material de consumo/permanente';

  const handleSalvarConfig = async (e: FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      await onSalvarConfig(formConfig);
      setModoEdicaoConfig(false);
    } catch (err) {
      alert('Erro ao salvar configuração');
    } finally {
      setSalvando(false);
    }
  };

  const dispararImpressao = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4">
      {/* Container do Modal */}
      <div className="relative w-full max-w-5xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden my-auto max-h-[95vh] flex flex-col">
        {/* Barra superior de ações (escondida no print) */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-200 bg-slate-50 shrink-0 print:hidden">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-700 text-white flex items-center justify-center font-bold text-base shadow-xs">
              EB
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Termo de Requisição Oficial (DIEx)
              </h2>
              <p className="text-xs text-slate-500">
                {chaveNC} • ND {nc.nd || 'Não definida'} • {itensExibidos.length} itens inclusos
              </p>
            </div>
          </div>

          {/* Seletor de Fornecedor / Lote */}
          <div className="flex items-center gap-2">
            {listaFornecedores.length > 0 && (
              <div className="flex items-center gap-1.5 bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs">
                <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                <span className="font-semibold text-slate-700">Fornecedor:</span>
                <select
                  value={fornecedorSelecionado}
                  onChange={e => setFornecedorSelecionado(e.target.value)}
                  className="bg-transparent font-medium text-slate-900 focus:outline-none cursor-pointer max-w-[200px] truncate"
                >
                  <option value="TODOS">Todos os Fornecedores da NC</option>
                  {listaFornecedores.map(f => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={() => setModoEdicaoConfig(!modoEdicaoConfig)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <Settings className="w-3.5 h-3.5" />
              {modoEdicaoConfig ? 'Ver DIEx' : 'Cabeçalho / Assinaturas'}
            </button>

            <button
              onClick={dispararImpressao}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
            >
              <Printer className="w-3.5 h-3.5" />
              Imprimir / PDF
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Conteúdo rolável */}
        <div className="overflow-y-auto p-6 bg-slate-100/60 print:bg-white print:p-0 print:overflow-visible">
          {modoEdicaoConfig ? (
            <form onSubmit={handleSalvarConfig} className="max-w-2xl mx-auto bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-800 border-b pb-2">
                Configurações da Requisição e Assinaturas (Padrão da Seção)
              </h3>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Cabeçalho da OM (Linhas):
                </label>
                <textarea
                  rows={3}
                  value={formConfig.cabecalho_om}
                  onChange={e => setFormConfig({ ...formConfig, cabecalho_om: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Indicativo DIEx / Documento (Ex: SALC/1º Btl):
                  </label>
                  <input
                    type="text"
                    value={formConfig.indicativo_diex}
                    onChange={e => setFormConfig({ ...formConfig, indicativo_diex: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Cidade / UF da OM (Ex: Brasília-DF):
                  </label>
                  <input
                    type="text"
                    value={formConfig.cidade_om}
                    onChange={e => setFormConfig({ ...formConfig, cidade_om: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Remetente (Campo 'Do:'):
                  </label>
                  <input
                    type="text"
                    value={formConfig.remetente_do || 'Chefe da Seção'}
                    onChange={e => setFormConfig({ ...formConfig, remetente_do: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Sua Assinatura (Ex: NOME - Posto):
                  </label>
                  <input
                    type="text"
                    value={formConfig.assinatura_nome}
                    onChange={e => setFormConfig({ ...formConfig, assinatura_nome: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Função de quem Assina:
                  </label>
                  <input
                    type="text"
                    value={formConfig.assinatura_funcao}
                    onChange={e => setFormConfig({ ...formConfig, assinatura_funcao: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Nome do OD (Ex: SILVA - Cel):
                  </label>
                  <input
                    type="text"
                    value={formConfig.od_nome}
                    onChange={e => setFormConfig({ ...formConfig, od_nome: e.target.value })}
                    className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Função do OD:
                </label>
                <input
                  type="text"
                  value={formConfig.od_funcao}
                  onChange={e => setFormConfig({ ...formConfig, od_funcao: e.target.value })}
                  className="w-full text-xs p-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setModoEdicaoConfig(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={salvando}
                  className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 disabled:opacity-50"
                >
                  {salvando ? 'Salvando...' : 'Salvar Padrão da Seção'}
                </button>
              </div>
            </form>
          ) : (
            /* Folha Oficial A4 no formato idêntico ao app.py (DIEx Oficial EB) */
            <div
              id="documento-requisicao-oficial"
              className="bg-white max-w-[210mm] min-h-[297mm] mx-auto p-8 sm:p-12 shadow-md border border-slate-200 text-slate-900 print:shadow-none print:border-none print:p-0 print:max-w-none print:w-full print:m-0"
              style={{ fontFamily: "'Times New Roman', Times, serif" }}
            >
              {/* Visto do Fiscal Administrativo e Brasão das Armas da República */}
              <table style={{ width: '100%', border: 'none', borderCollapse: 'collapse', marginBottom: '15px' }}>
                <tbody>
                  <tr style={{ border: 'none' }}>
                    <td style={{ width: '30%', border: 'none' }}></td>
                    <td style={{ width: '40%', border: 'none', textAlign: 'center', verticalAlign: 'top' }}>
                      <img
                        src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Coat_of_arms_of_Brazil.svg"
                        alt="Brasão da República"
                        className="w-16 h-16 mx-auto mb-2 object-contain"
                        referrerPolicy="no-referrer"
                      />
                    </td>
                    <td style={{ width: '30%', border: 'none', textAlign: 'center', verticalAlign: 'top', fontWeight: 'bold', fontSize: '13px', lineHeight: '1.2' }}>
                      VISTO<br /><br />_________________<br />Fisc Adm
                    </td>
                  </tr>
                </tbody>
              </table>

              {/* Cabeçalho Oficial do EB */}
              <div style={{ textAlign: 'center', lineHeight: '1.25', marginBottom: '20px' }}>
                <b style={{ fontSize: '13px' }}>MINISTÉRIO DA DEFESA</b><br />
                <b style={{ fontSize: '13px' }}>EXÉRCITO BRASILEIRO</b><br />
                {config.cabecalho_om.split('\n').map((linha, idx) => (
                  <b key={idx} style={{ fontSize: '12px', display: 'block' }}>
                    {linha}
                  </b>
                ))}
              </div>

              {/* Linha DIEx e Data */}
              <table style={{ width: '100%', border: 'none', borderCollapse: 'collapse', marginBottom: '15px', fontSize: '13px' }}>
                <tbody>
                  <tr style={{ border: 'none' }}>
                    <td style={{ border: 'none', textAlign: 'left', padding: 0 }}>
                      DIEx nº {diexDisplay} - {config.indicativo_diex}<br />
                      EB: {ebDisplay}
                    </td>
                    <td style={{ border: 'none', textAlign: 'right', padding: 0 }}>
                      {config.cidade_om}, {dataDisplay}.
                    </td>
                  </tr>
                </tbody>
              </table>

              {/* Remetente / Destinatário / Assunto */}
              <div style={{ lineHeight: '1.6', fontSize: '13px', marginBottom: '15px' }}>
                <b>Do:</b> {config.remetente_do || 'Chefe da Seção'}<br />
                <b>Ao:</b> Sr Fiscal Administrativo<br />
                <b>Assunto:</b> {assuntoDisplay}
              </div>

              {/* Parágrafo 1 */}
              <div style={{ textAlign: 'justify', textIndent: '30px', lineHeight: '1.6', fontSize: '13px', marginBottom: '10px' }}>
                1. Nos termos contidos na lei 14.133/2021, solicito-vos providências junto ao Ordenador de Despesas no sentido de aprovar o empenho da despesa para aquisição de material, com os respectivos recursos e destinos:
              </div>

              {/* Dados da Despesa */}
              <div style={{ marginLeft: '30px', lineHeight: '1.6', fontSize: '13px', marginBottom: '15px' }}>
                a) <b>Nota de crédito:</b> {chaveNC} &nbsp;&nbsp;&nbsp; b) <b>PI:</b> {nc.pi || 'Não informado'}; <b>ND:</b> {nc.nd || 'Não informada'}<br />
                <b>Edital de Pregão:</b> {pregaoAtual || 'Ata/Edital'} / <b>UASG:</b> {uasgAtual || 'S/N'} / <b>Tipo de Empenho:</b> Ordinário<br />
                <b>Empresa:</b> {cnpjAtual ? `${cnpjAtual} – ` : ''}{fornecedorSelecionado === 'TODOS' ? 'Diversas' : fornecedorSelecionado}
              </div>

              {/* Tabela de Itens */}
              <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid black', marginBottom: '15px', fontSize: '12px' }}>
                <thead>
                  <tr style={{ fontWeight: 'bold', backgroundColor: '#f2f2f2' }}>
                    <th style={{ border: '1px solid black', padding: '6px 4px', textAlign: 'center', width: '45px' }}>Item</th>
                    <th style={{ border: '1px solid black', padding: '6px 4px', textAlign: 'center', width: '65px' }}>Sub Item</th>
                    <th style={{ border: '1px solid black', padding: '6px 6px', textAlign: 'left' }}>Nomenclatura</th>
                    <th style={{ border: '1px solid black', padding: '6px 4px', textAlign: 'center', width: '45px' }}>Qtd</th>
                    <th style={{ border: '1px solid black', padding: '6px 6px', textAlign: 'right', width: '90px' }}>Valor Unitário</th>
                    <th style={{ border: '1px solid black', padding: '6px 6px', textAlign: 'right', width: '95px' }}>Valor Total</th>
                  </tr>
                </thead>
                <tbody>
                  {itensExibidos.map((it, idx) => (
                    <tr key={idx}>
                      <td style={{ border: '1px solid black', padding: '5px 4px', textAlign: 'center', fontWeight: 'bold' }}>
                        {it.Item}
                      </td>
                      <td style={{ border: '1px solid black', padding: '5px 4px', textAlign: 'center' }}>
                        {it.Subitem || '-'}
                      </td>
                      <td style={{ border: '1px solid black', padding: '5px 6px', textAlign: 'left' }}>
                        <div style={{ fontWeight: 'bold' }}>{it.Nome}</div>
                        {it.Obs && <div style={{ fontSize: '10px', color: '#555', fontStyle: 'italic' }}>{it.Obs}</div>}
                      </td>
                      <td style={{ border: '1px solid black', padding: '5px 4px', textAlign: 'center' }}>
                        {it.Qtd}
                      </td>
                      <td style={{ border: '1px solid black', padding: '5px 6px', textAlign: 'right' }}>
                        {formatarMoedaBRL(it['Valor Unitário'])}
                      </td>
                      <td style={{ border: '1px solid black', padding: '5px 6px', textAlign: 'right', fontWeight: 'bold' }}>
                        {formatarMoedaBRL(it.Total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 'bold', backgroundColor: '#fafafa' }}>
                    <td colSpan={5} style={{ border: '1px solid black', padding: '6px', textAlign: 'right', textTransform: 'uppercase' }}>
                      TOTAL
                    </td>
                    <td style={{ border: '1px solid black', padding: '6px', textAlign: 'right' }}>
                      {formatarMoedaBRL(totalRequisicao)}
                    </td>
                  </tr>
                </tfoot>
              </table>

              {/* Parágrafo 2 */}
              <div style={{ textAlign: 'justify', textIndent: '30px', lineHeight: '1.6', fontSize: '13px', marginBottom: '25px' }}>
                2. O material solicitado deverá ser empenhado na empresa vencedora do item acima citado, proveniente de seu respectivo Pregão Eletrônico.
              </div>

              {/* Assinatura do Requisitante */}
              <div style={{ textAlign: 'center', lineHeight: '1.25', marginTop: '30px', marginBottom: '30px' }}>
                <b style={{ fontSize: '13px' }}>{config.assinatura_nome}</b><br />
                <span style={{ fontSize: '12px' }}>{config.assinatura_funcao}</span>
              </div>

              {/* Separador de página visual */}
              <div className="print:hidden border-t-2 border-dashed border-slate-300 text-slate-400 text-center py-4 text-xs font-sans">
                ✂️ --- QUEBRA DE PÁGINA (DESPACHO DO ORDENADOR DE DESPESAS) --- ✂️
              </div>

              {/* Despacho do OD */}
              <div style={{ paddingTop: '20px', lineHeight: '1.6', fontSize: '13px', pageBreakBefore: 'always' }}>
                <b>DESPACHO DO OD:</b><br />
                1. Autorizo a aquisição do material relacionado na letra b) do número 1);<br />
                2. Empregar os recursos provenientes da nota de crédito relacionado na letra a);<br />
                3. A SALC inicie os procedimentos legais, conforme legislação em vigor para empenho da despesa.<br />
                <br /><br />
                <div style={{ textAlign: 'center', lineHeight: '1.25', marginTop: '20px' }}>
                  <b style={{ fontSize: '13px' }}>{config.od_nome}</b><br />
                  <span style={{ fontSize: '12px' }}>{config.od_funcao}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
