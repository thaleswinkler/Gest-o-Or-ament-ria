import { useState, useMemo, useEffect, type FormEvent } from 'react';
import { 
  Users, 
  UserPlus, 
  ShieldCheck, 
  ArrowRightLeft, 
  Layers, 
  CheckCircle2, 
  AlertCircle, 
  Search,
  KeyRound,
  Shield,
  UserCheck,
  Building2,
  RefreshCw,
  Trash2
} from 'lucide-react';
import { Usuario, PerfilUsuario } from '../types';
import { criarNovoUsuario, listarUsuariosOM, transferirPerfilUsuario, excluirUsuario } from '../lib/supabase';

interface TabGerenciamentoUsuariosProps {
  usuarioLogado: Usuario;
  secoesDisponiveis: string[];
}

export function TabGerenciamentoUsuarios({
  usuarioLogado,
  secoesDisponiveis
}: TabGerenciamentoUsuariosProps) {
  const [subAbaAtiva, setSubAbaAtiva] = useState<'lista' | 'transferir' | 'cadastrar'>('lista');

  // Cadastro de Novo Usuário
  const [novoId, setNovoId] = useState('');
  const [novoNome, setNovoNome] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [novoPerfil, setNovoPerfil] = useState<PerfilUsuario>('Operador');
  const [secaoEscolhida, setSecaoEscolhida] = useState(
    usuarioLogado.perfil === 'Chefe' ? usuarioLogado.secao : (secoesDisponiveis[0] || usuarioLogado.secao)
  );
  const [nomeNovaSecao, setNomeNovaSecao] = useState('');
  const [carregandoCadastro, setCarregandoCadastro] = useState(false);
  const [sucessoCadastroMsg, setSucessoCadastroMsg] = useState('');
  const [erroCadastroMsg, setErroCadastroMsg] = useState('');

  // Transferência de Função / Perfil
  const [candidatoDestinoId, setCandidatoDestinoId] = useState('');
  const [novoPerfilOrigemFiscal, setNovoPerfilOrigemFiscal] = useState<PerfilUsuario>('Chefe');
  const [confirmacaoTransferencia, setConfirmacaoTransferencia] = useState(false);
  const [carregandoTransferencia, setCarregandoTransferencia] = useState(false);
  const [sucessoTransfMsg, setSucessoTransfMsg] = useState('');
  const [erroTransfMsg, setErroTransfMsg] = useState('');

  // Lista de militares da OM para conferência e visualização de subordinados
  const [militares, setMilitares] = useState<Usuario[]>([]);
  const [carregandoLista, setCarregandoLista] = useState(false);
  const [busca, setBusca] = useState('');
  const [filtroSecaoFiscal, setFiltroSecaoFiscal] = useState('TODAS');

  const ehOperador = usuarioLogado.perfil === 'Operador';
  const ehChefe = usuarioLogado.perfil === 'Chefe';
  const ehFiscal = usuarioLogado.perfil === 'Fiscal';

  const buscarMilitares = async () => {
    setCarregandoLista(true);
    try {
      const lista = await listarUsuariosOM(usuarioLogado.om);
      setMilitares(lista);
    } catch (e: any) {
      console.error('Erro ao buscar lista de militares:', e);
    } finally {
      setCarregandoLista(false);
    }
  };

  useEffect(() => {
    buscarMilitares();
  }, [usuarioLogado.om]);

  // Subordinados / Integrantes filtrados
  const militaresFiltrados = useMemo(() => {
    const termo = (busca || '').toLowerCase().trim();
    return militares.filter(m => {
      // Se for chefe, só vê subordinados e integrantes da sua própria seção
      if (ehChefe && m.secao !== usuarioLogado.secao) return false;
      // Se for fiscal e filtrou seção
      if (ehFiscal && filtroSecaoFiscal !== 'TODAS' && m.secao !== filtroSecaoFiscal) return false;
      if (!termo) return true;
      return (
        (m.nome || '').toLowerCase().includes(termo) ||
        (m.id || '').toLowerCase().includes(termo) ||
        (m.secao || '').toLowerCase().includes(termo) ||
        (m.perfil || '').toLowerCase().includes(termo)
      );
    });
  }, [militares, busca, ehChefe, ehFiscal, filtroSecaoFiscal, usuarioLogado.secao]);

  // Candidatos para transferência
  const candidatosTransferencia = useMemo(() => {
    if (ehChefe) {
      // Chefe pode transferir para um Operador da sua própria seção
      return militares.filter(
        m => m.secao === usuarioLogado.secao && m.perfil === 'Operador' && m.id !== usuarioLogado.id
      );
    }
    if (ehFiscal) {
      // Fiscal pode transferir para qualquer militar cadastrado na OM (exceto ele próprio)
      return militares.filter(m => m.id !== usuarioLogado.id);
    }
    return [];
  }, [militares, ehChefe, ehFiscal, usuarioLogado.secao, usuarioLogado.id]);

  const handleCadastrar = async (e: FormEvent) => {
    e.preventDefault();
    setErroCadastroMsg('');
    setSucessoCadastroMsg('');

    if (!novoId.trim() || !novoNome.trim() || !novaSenha.trim()) {
      setErroCadastroMsg('Preencha todos os campos obrigatórios.');
      return;
    }

    const secaoFinal = (ehFiscal && secaoEscolhida === '__NOVA__')
      ? nomeNovaSecao.trim().toUpperCase()
      : (ehChefe ? usuarioLogado.secao : secaoEscolhida);

    if (!secaoFinal) {
      setErroCadastroMsg('Informe ou selecione a Seção do novo militar.');
      return;
    }

    setCarregandoCadastro(true);
    try {
      await criarNovoUsuario({
        id: novoId.trim().toLowerCase(),
        nome: novoNome.trim(),
        senha: novaSenha,
        om: usuarioLogado.om,
        secao: secaoFinal,
        perfil: novoPerfil
      });

      setSucessoCadastroMsg(`Militar ${novoNome} cadastrado com sucesso na Seção ${secaoFinal}!`);
      setNovoId('');
      setNovoNome('');
      setNovaSenha('');
      setNomeNovaSecao('');
      await buscarMilitares();
    } catch (err: any) {
      setErroCadastroMsg(err.message || 'Falha ao cadastrar novo militar.');
    } finally {
      setCarregandoCadastro(false);
    }
  };

  const handleTransferir = async (e: FormEvent) => {
    e.preventDefault();
    setErroTransfMsg('');
    setSucessoTransfMsg('');

    if (!candidatoDestinoId) {
      setErroTransfMsg('Selecione o militar que assumirá a função.');
      return;
    }
    if (!confirmacaoTransferencia) {
      setErroTransfMsg('Marque a caixa de confirmação para autorizar a transferência.');
      return;
    }

    const candidatoEscolhido = candidatosTransferencia.find(c => c.id === candidatoDestinoId);
    const nomeDestino = candidatoEscolhido ? candidatoEscolhido.nome : candidatoDestinoId;

    setCarregandoTransferencia(true);
    try {
      if (ehChefe) {
        await transferirPerfilUsuario(
          usuarioLogado.id,
          'Operador',
          candidatoDestinoId,
          'Chefe'
        );
        setSucessoTransfMsg(`Chefia da Seção ${usuarioLogado.secao} transferida com sucesso para ${nomeDestino}! Seu perfil foi alterado para Operador. Recarregue a página para atualizar suas permissões.`);
      } else if (ehFiscal) {
        await transferirPerfilUsuario(
          usuarioLogado.id,
          novoPerfilOrigemFiscal,
          candidatoDestinoId,
          'Fiscal'
        );
        setSucessoTransfMsg(`Função de Fiscal da OM transferida com sucesso para ${nomeDestino}! Seu perfil foi alterado para ${novoPerfilOrigemFiscal}. Recarregue a página para atualizar suas permissões.`);
      }
      setConfirmacaoTransferencia(false);
      setCandidatoDestinoId('');
      await buscarMilitares();
    } catch (err: any) {
      setErroTransfMsg(err.message || 'Falha ao processar transferência.');
    } finally {
      setCarregandoTransferencia(false);
    }
  };

  // Exclusão de Operador
  const [carregandoExclusao, setCarregandoExclusao] = useState(false);
  const [sucessoExclusaoMsg, setSucessoExclusaoMsg] = useState('');
  const [erroExclusaoMsg, setErroExclusaoMsg] = useState('');

  const handleExcluirOperador = async (op: Usuario) => {
    if (!window.confirm(`Confirma a exclusão definitiva do operador ${op.nome} (login: ${op.id})? Ele perderá todo o acesso ao sistema.`)) {
      return;
    }
    setCarregandoExclusao(true);
    setErroExclusaoMsg('');
    setSucessoExclusaoMsg('');
    try {
      await excluirUsuario(op.id);
      setSucessoExclusaoMsg(`Operador ${op.nome} foi excluído com sucesso!`);
      await buscarMilitares();
    } catch (err: any) {
      setErroExclusaoMsg(err.message || 'Falha ao excluir operador.');
    } finally {
      setCarregandoExclusao(false);
    }
  };

  if (ehOperador) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200/80 shadow-xs text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-slate-800">Acesso Restrito</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          O perfil <strong>Operador</strong> não possui autorização para gerenciar outros usuários ou transferir perfis.
          Apenas <strong>Chefes de Seção</strong> e o <strong>Fiscal da OM</strong> podem gerenciar equipes e transferir chefias.
        </p>
      </div>
    );
  }

  // Estatísticas
  const totalIntegrantes = militaresFiltrados.length;
  const qtdChefes = militaresFiltrados.filter(m => m.perfil === 'Chefe').length;
  const qtdOperadores = militaresFiltrados.filter(m => m.perfil === 'Operador').length;
  const qtdFiscais = militaresFiltrados.filter(m => m.perfil === 'Fiscal').length;

  return (
    <div className="space-y-6">
      {/* Cabeçalho do Painel */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-700" />
            <h2 className="text-base font-semibold text-slate-900">
              Gestão de Acessos, Equipe e Transferência de Funções
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {ehFiscal
              ? `Como Fiscal da OM (${usuarioLogado.om}), você visualiza todos os militares cadastrados, cadastra novos usuários e pode transferir a função de Fiscal.`
              : `Como Chefe da Seção ${usuarioLogado.secao}, você visualiza os subordinados da sua seção, cadastra novos operadores e pode transferir a Chefia.`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            {usuarioLogado.om} • {usuarioLogado.secao} ({usuarioLogado.perfil})
          </span>
          <button
            onClick={buscarMilitares}
            disabled={carregandoLista}
            title="Atualizar lista"
            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${carregandoLista ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Navegação entre Sub-abas */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setSubAbaAtiva('lista')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            subAbaAtiva === 'lista'
              ? 'bg-emerald-700 text-white shadow-xs'
              : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Integrantes Cadastrados ({totalIntegrantes})
        </button>

        <button
          onClick={() => setSubAbaAtiva('transferir')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            subAbaAtiva === 'transferir'
              ? 'bg-emerald-700 text-white shadow-xs'
              : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <ArrowRightLeft className="w-4 h-4" />
          Transferência de Perfil / Função
        </button>

        <button
          onClick={() => setSubAbaAtiva('cadastrar')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            subAbaAtiva === 'cadastrar'
              ? 'bg-emerald-700 text-white shadow-xs'
              : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <UserPlus className="w-4 h-4" />
          Cadastrar Novo Militar
        </button>
      </div>

      {/* SUB-ABA 1: INTEGRANTES CADASTRADOS */}
      {subAbaAtiva === 'lista' && (
        <div className="space-y-4">
          {/* Métricas da Equipe */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Total Integrantes</span>
              <div className="text-xl font-extrabold text-slate-900 mt-0.5">{totalIntegrantes}</div>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Chefes de Seção</span>
              <div className="text-xl font-extrabold text-emerald-700 mt-0.5">{qtdChefes}</div>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Operadores</span>
              <div className="text-xl font-extrabold text-slate-700 mt-0.5">{qtdOperadores}</div>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Fiscais da OM</span>
              <div className="text-xl font-extrabold text-purple-700 mt-0.5">{qtdFiscais}</div>
            </div>
          </div>

          {/* Filtros e Lista */}
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-700" />
                <h3 className="text-sm font-semibold text-slate-900">
                  {ehChefe ? `Subordinados e Integrantes da Seção ${usuarioLogado.secao}` : 'Integrantes Cadastrados na OM'}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                {ehFiscal && (
                  <select
                    value={filtroSecaoFiscal}
                    onChange={e => setFiltroSecaoFiscal(e.target.value)}
                    className="text-xs p-1.5 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 font-medium text-slate-700"
                  >
                    <option value="TODAS">Todas as Seções</option>
                    {secoesDisponiveis.map(sec => (
                      <option key={sec} value={sec}>{sec}</option>
                    ))}
                  </select>
                )}

                <div className="relative w-48 sm:w-64">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Filtrar por nome ou login..."
                    value={busca}
                    onChange={e => setBusca(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {sucessoExclusaoMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{sucessoExclusaoMsg}</span>
              </div>
            )}

            {erroExclusaoMsg && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{erroExclusaoMsg}</span>
              </div>
            )}

            {carregandoLista ? (
              <div className="text-center py-12 text-xs text-slate-400">
                Carregando integrantes cadastrados...
              </div>
            ) : militaresFiltrados.length === 0 ? (
              <div className="text-center py-12 text-xs text-slate-400">
                Nenhum militar localizado com os filtros selecionados.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-[520px] overflow-y-auto pr-1">
                {militaresFiltrados.map(m => {
                  const ehVoce = m.id === usuarioLogado.id;
                  const podeExcluir = m.perfil === 'Operador' && !ehVoce && (ehFiscal || (ehChefe && m.secao === usuarioLogado.secao));
                  return (
                    <div key={m.id} className="py-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`w-8 h-8 rounded-full font-bold text-xs flex items-center justify-center shrink-0 ${
                          ehVoce ? 'bg-emerald-700 text-white' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {m.nome.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-slate-900 truncate flex items-center gap-1.5">
                            <span>{m.nome}</span>
                            {ehVoce && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-100 text-emerald-800 font-bold">
                                Você
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 truncate">
                            Login: <span className="font-mono text-slate-700">{m.id}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {m.secao}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            m.perfil === 'Fiscal'
                              ? 'bg-purple-50 text-purple-800 border-purple-200'
                              : m.perfil === 'Chefe'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-slate-50 text-slate-700 border-slate-200'
                          }`}
                        >
                          {m.perfil}
                        </span>
                        {podeExcluir && (
                          <button
                            type="button"
                            onClick={() => handleExcluirOperador(m)}
                            disabled={carregandoExclusao}
                            title={`Excluir operador ${m.nome}`}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-ABA 2: TRANSFERÊNCIA DE PERFIL / FUNÇÃO */}
      {subAbaAtiva === 'transferir' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5 max-w-2xl">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <ArrowRightLeft className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                {ehChefe ? 'Transferência da Função de Chefe de Seção' : 'Transferência da Função de Fiscal da OM'}
              </h3>
              <p className="text-xs text-slate-500">
                {ehChefe
                  ? `Passe a responsabilidade de Chefe da Seção ${usuarioLogado.secao} para um de seus Operadores subordinados.`
                  : `Passe a responsabilidade de Fiscal Geral da OM para outro militar cadastrado.`}
              </p>
            </div>
          </div>

          {sucessoTransfMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{sucessoTransfMsg}</span>
            </div>
          )}

          {erroTransfMsg && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{erroTransfMsg}</span>
            </div>
          )}

          {candidatosTransferencia.length === 0 ? (
            <div className="p-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg text-xs space-y-2">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                Nenhum militar disponível para transferência
              </div>
              <p>
                {ehChefe
                  ? `Não há outros Operadores cadastrados na seção ${usuarioLogado.secao}. Cadastre um novo operador na aba "Cadastrar Novo Militar" antes de realizar a transferência.`
                  : `Não há outros militares cadastrados no ${usuarioLogado.om}. Cadastre novos militares antes de transferir.`}
              </p>
            </div>
          ) : (
            <form onSubmit={handleTransferir} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  {ehChefe
                    ? `Selecione o Operador da seção ${usuarioLogado.secao} que assumirá a Chefia:`
                    : `Selecione o militar que assumirá a função de Fiscal da OM:`}
                </label>
                <select
                  value={candidatoDestinoId}
                  onChange={e => {
                    setCandidatoDestinoId(e.target.value);
                    setConfirmacaoTransferencia(false);
                  }}
                  required
                  className="w-full p-2.5 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium text-slate-800"
                >
                  <option value="">-- Selecione o militar destinatário --</option>
                  {candidatosTransferencia.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.nome} — {c.secao} ({c.perfil}) [login: {c.id}]
                    </option>
                  ))}
                </select>
              </div>

              {ehFiscal && (
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Qual perfil você passará a ter na sua seção ({usuarioLogado.secao})?
                  </label>
                  <select
                    value={novoPerfilOrigemFiscal}
                    onChange={e => setNovoPerfilOrigemFiscal(e.target.value as PerfilUsuario)}
                    className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium text-slate-800"
                  >
                    <option value="Chefe">Chefe de Seção</option>
                    <option value="Operador">Operador</option>
                  </select>
                </div>
              )}

              {(() => {
                const candSel = candidatosTransferencia.find(c => c.id === candidatoDestinoId);
                return (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 space-y-1">
                    <span className="font-semibold text-slate-800 block">Efeitos da Transferência:</span>
                    {ehChefe ? (
                      <p>
                        O militar <strong>{candSel ? candSel.nome : 'selecionado'}</strong> será promovido a <strong>Chefe da Seção {usuarioLogado.secao}</strong>.
                        Seu acesso permanecerá ativo no sistema com o perfil de <strong>Operador</strong>.
                      </p>
                    ) : (
                      <p>
                        O militar <strong>{candSel ? `${candSel.nome} (${candSel.secao})` : 'selecionado'}</strong> será promovido a <strong>Fiscal da OM ({usuarioLogado.om})</strong>.
                        Seu perfil passará a ser <strong>{novoPerfilOrigemFiscal}</strong> da seção {usuarioLogado.secao}.
                      </p>
                    )}
                  </div>
                );
              })()}

              <div className="flex items-start gap-2 pt-1">
                <input
                  type="checkbox"
                  id="chk_confirma_transf"
                  checked={confirmacaoTransferencia}
                  onChange={e => setConfirmacaoTransferencia(e.target.checked)}
                  className="mt-0.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                <label htmlFor="chk_confirma_transf" className="text-xs text-slate-700 leading-tight select-none">
                  {(() => {
                    const candSel = candidatosTransferencia.find(c => c.id === candidatoDestinoId);
                    return (
                      <span>
                        Declaro que estou ciente da passagem da Chefia para <strong>{candSel ? candSel.nome : 'o militar selecionado'}</strong> e que meu perfil será atualizado.
                      </span>
                    );
                  })()}
                </label>
              </div>

              <button
                type="submit"
                disabled={carregandoTransferencia || !candidatoDestinoId || !confirmacaoTransferencia}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-700 text-white font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
              >
                <ArrowRightLeft className="w-4 h-4" />
                {carregandoTransferencia ? 'Processando transferência...' : 'Confirmar Transferência de Perfil'}
              </button>
            </form>
          )}
        </div>
      )}


      {/* SUB-ABA 3: CADASTRAR NOVO MILITAR */}
      {subAbaAtiva === 'cadastrar' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4 max-w-xl">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <UserPlus className="w-4 h-4 text-emerald-700" />
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Cadastrar Novo Militar na Equipe</h3>
              <p className="text-xs text-slate-500">
                {ehFiscal
                  ? `Cadastre Chefes de Seção ou Operadores para qualquer setor do ${usuarioLogado.om}.`
                  : `Cadastre novos Operadores para integrarem a Seção ${usuarioLogado.secao}.`}
              </p>
            </div>
          </div>

          {sucessoCadastroMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{sucessoCadastroMsg}</span>
            </div>
          )}

          {erroCadastroMsg && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{erroCadastroMsg}</span>
            </div>
          )}

          <form onSubmit={handleCadastrar} className="space-y-3.5 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">
                Identificador de Login (E-mail ou Usuário):
              </label>
              <input
                type="text"
                required
                placeholder="ex: cbsilva ou militar@eb.mil.br"
                value={novoId}
                onChange={e => setNovoId(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">
                Nome Completo / Posto ou Graduação:
              </label>
              <input
                type="text"
                required
                placeholder="Ex: Cb Silva, 1º Ten Costa..."
                value={novoNome}
                onChange={e => setNovoNome(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">
                Senha Provisória de Acesso:
              </label>
              <input
                type="password"
                required
                placeholder="Mínimo 4 caracteres"
                value={novaSenha}
                onChange={e => setNovaSenha(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                O militar poderá alterar a senha pelo botão "Trocar Senha" na tela de login.
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Perfil de Acesso:
                </label>
                <select
                  value={novoPerfil}
                  onChange={e => setNovoPerfil(e.target.value as PerfilUsuario)}
                  className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium text-slate-800"
                >
                  <option value="Operador">Operador</option>
                  {ehFiscal && <option value="Chefe">Chefe de Seção</option>}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Seção da OM:
                </label>
                {ehChefe ? (
                  <input
                    type="text"
                    disabled
                    value={usuarioLogado.secao}
                    className="w-full p-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-600 font-medium"
                  />
                ) : (
                  <select
                    value={secaoEscolhida}
                    onChange={e => setSecaoEscolhida(e.target.value)}
                    className="w-full p-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none font-medium text-slate-800"
                  >
                    {secoesDisponiveis.map(sec => (
                      <option key={sec} value={sec}>
                        {sec}
                      </option>
                    ))}
                    <option value="__NOVA__">+ Nova Seção...</option>
                  </select>
                )}
              </div>
            </div>

            {ehFiscal && secaoEscolhida === '__NOVA__' && (
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Nome da Nova Seção:
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: ALMOX, SALC, COM SOCIAL..."
                  value={nomeNovaSecao}
                  onChange={e => setNomeNovaSecao(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-emerald-600 focus:outline-none uppercase font-semibold"
                />
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={carregandoCadastro}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-700 text-white font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
              >
                <UserPlus className="w-4 h-4" />
                {carregandoCadastro ? 'Cadastrando militar...' : 'Cadastrar Novo Militar'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
