import { useState, type FormEvent } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  User, 
  KeyRound, 
  AlertCircle, 
  Check, 
  Building, 
  Layers, 
  ArrowRight,
  ShieldAlert,
  HelpCircle
} from 'lucide-react';
import { Usuario } from '../types';
import { loginUsuario, criarNovoUsuario, alterarSenha } from '../lib/supabase';

interface LoginScreenProps {
  onLoginSucesso: (user: Usuario) => void;
}

export function LoginScreen({ onLoginSucesso }: LoginScreenProps) {
  // Estados do formulário de Login
  const [usuarioLogin, setUsuarioLogin] = useState('');
  const [senhaLogin, setSenhaLogin] = useState('');
  const [carregandoLogin, setCarregandoLogin] = useState(false);
  const [erroLogin, setErroLogin] = useState('');

  // Estados do formulário de Cadastro da Conta Matriz (Fiscal)
  const [novoUser, setNovoUser] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [novoNome, setNovoNome] = useState('');
  const [novaOm, setNovaOm] = useState('');
  const [novaSecao, setNovaSecao] = useState('');
  const [carregandoCad, setCarregandoCad] = useState(false);
  const [erroCad, setErroCad] = useState('');
  const [sucessoCad, setSucessoCad] = useState('');

  // Modal para recuperar / alterar senha
  const [modalEsqueci, setModalEsqueci] = useState(false);
  const [idEsqueci, setIdEsqueci] = useState('');
  const [senhaEsqueci, setSenhaEsqueci] = useState('');
  const [confirmaEsqueci, setConfirmaEsqueci] = useState('');
  const [carregandoEsqueci, setCarregandoEsqueci] = useState(false);
  const [erroEsqueci, setErroEsqueci] = useState('');
  const [sucessoEsqueci, setSucessoEsqueci] = useState('');

  const handleEntrar = async (e: FormEvent) => {
    e.preventDefault();
    setErroLogin('');
    if (!usuarioLogin.trim() || !senhaLogin) {
      setErroLogin('Por favor, informe usuário e senha.');
      return;
    }

    setCarregandoLogin(true);
    try {
      const user = await loginUsuario((usuarioLogin || '').trim().toLowerCase(), senhaLogin);
      onLoginSucesso(user);
    } catch (err: any) {
      setErroLogin(err.message || 'Credenciais inválidas.');
    } finally {
      setCarregandoLogin(false);
    }
  };

  const handleCadastrarMatriz = async (e: FormEvent) => {
    e.preventDefault();
    setErroCad('');
    setSucessoCad('');

    if (!novoUser.trim() || !novaSenha || !novoNome.trim() || !novaOm.trim() || !novaSecao.trim()) {
      setErroCad('Preencha todos os campos obrigatórios.');
      return;
    }

    setCarregandoCad(true);
    try {
      await criarNovoUsuario({
        id: (novoUser || '').trim().toLowerCase(),
        nome: novoNome.trim(),
        om: novaOm.trim().toUpperCase(),
        secao: novaSecao.trim().toUpperCase(),
        perfil: 'Fiscal',
        senha: novaSenha
      });
      setSucessoCad('Conta de Fiscal criada com sucesso! Faça seu login ao lado.');
      setUsuarioLogin((novoUser || '').trim().toLowerCase());
      setSenhaLogin(novaSenha);
      setNovoUser('');
      setNovaSenha('');
      setNovoNome('');
      setNovaOm('');
      setNovaSecao('');
    } catch (err: any) {
      setErroCad(err.message || 'Erro ao cadastrar conta matriz.');
    } finally {
      setCarregandoCad(false);
    }
  };

  const handleAtualizarSenhaEsqueci = async (e: FormEvent) => {
    e.preventDefault();
    setErroEsqueci('');
    setSucessoEsqueci('');

    if (!idEsqueci.trim() || !senhaEsqueci) {
      setErroEsqueci('Preencha todos os campos.');
      return;
    }
    if (senhaEsqueci !== confirmaEsqueci) {
      setErroEsqueci('As senhas não coincidem.');
      return;
    }

    setCarregandoEsqueci(true);
    try {
      await alterarSenha((idEsqueci || '').trim().toLowerCase(), senhaEsqueci);
      setSucessoEsqueci('Senha atualizada com sucesso! Você já pode realizar o login.');
      setUsuarioLogin((idEsqueci || '').trim().toLowerCase());
      setSenhaLogin(senhaEsqueci);
      setTimeout(() => setModalEsqueci(false), 2000);
    } catch (err: any) {
      setErroEsqueci(err.message || 'Falha ao redefinir a senha.');
    } finally {
      setCarregandoEsqueci(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-between p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl w-full mx-auto my-auto space-y-8">
        {/* Cabeçalho Oficial do Exército Brasileiro */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-800 to-slate-900 text-white shadow-lg text-3xl font-bold">
            EB
          </div>
          <div>
            <span className="text-[11px] font-extrabold tracking-widest text-emerald-800 uppercase block">
              Exército Brasileiro • Comando Militar
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">
              Sistema Integrado de Gestão Orçamentária &amp; Pregões
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-xl mx-auto">
              Controle de Recursos, Notas de Crédito, Aquisições e Atas de Registro de Preços do SIASG
            </p>
          </div>
        </div>

        {/* Grade com Login à esquerda e Cadastro Matriz à direita */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
          {/* Coluna 1: Formulário de Login */}
          <div className="md:col-span-6 bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="text-emerald-700">🔑</span>
                Acesso ao Sistema
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Informe suas credenciais autorizadas para ingressar
              </p>
            </div>

            {erroLogin && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{erroLogin}</span>
              </div>
            )}

            <form onSubmit={handleEntrar} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Usuário de Acesso (Login ou E-mail):
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={usuarioLogin}
                    onChange={e => setUsuarioLogin(e.target.value)}
                    placeholder="Ex: usuario.militar ou e-mail"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Senha:
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="password"
                    required
                    value={senhaLogin}
                    onChange={e => setSenhaLogin(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={carregandoLogin}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 shadow-xs flex items-center justify-center gap-2"
              >
                {carregandoLogin ? 'Autenticando...' : 'Entrar no Sistema'}
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-2 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => setModalEsqueci(true)}
                  className="text-slate-500 hover:text-emerald-700 font-medium flex items-center gap-1 text-[11px]"
                >
                  <KeyRound className="w-3.5 h-3.5" />
                  Alterar minha senha
                </button>
                <span className="text-[10px] text-slate-400 font-mono">
                  Sessão Segura Supabase
                </span>
              </div>
            </form>
          </div>

          {/* Coluna 2: Formulário de Cadastro da Conta Matriz */}
          <div className="md:col-span-6 bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="text-emerald-700">🛡️</span>
                Cadastrar Conta Matriz da OM
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Apenas para o Fiscal Administrativo da Organização Militar
              </p>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 text-amber-700 mt-0.5" />
              <span>
                <strong>Acesso Restrito:</strong> Apenas o <strong>Fiscal Administrativo</strong> pode criar a primeira conta da OM. Contas de Chefe e Operador são criadas internamente na aba de Gestão de Acessos.
              </span>
            </div>

            {erroCad && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{erroCad}</span>
              </div>
            )}

            {sucessoCad && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>{sucessoCad}</span>
              </div>
            )}

            <form onSubmit={handleCadastrarMatriz} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Escolha um nome de Usuário:
                </label>
                <input
                  type="text"
                  required
                  value={novoUser}
                  onChange={e => setNovoUser(e.target.value)}
                  placeholder="Ex: fiscal.23bi"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Crie uma Senha:
                </label>
                <input
                  type="password"
                  required
                  value={novaSenha}
                  onChange={e => setNovaSenha(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Seu Nome / Posto ou Graduação:
                </label>
                <input
                  type="text"
                  required
                  value={novoNome}
                  onChange={e => setNovoNome(e.target.value)}
                  placeholder="Ex: Cap Silva ou 1º Ten Oliveira"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Sua OM:
                </label>
                <input
                  type="text"
                  required
                  value={novaOm}
                  onChange={e => setNovaOm(e.target.value)}
                  placeholder="Ex: 1º BTL INF / UNIDADE"
                  className="w-full px-3 py-2 text-xs font-bold uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Seção Primária:
                  </label>
                  <input
                    type="text"
                    required
                    value={novaSecao}
                    onChange={e => setNovaSecao(e.target.value)}
                    placeholder="Ex: FISCALIZACAO ou SALC"
                    className="w-full px-3 py-2 text-xs font-bold uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Nível de Acesso:
                  </label>
                  <input
                    type="text"
                    disabled
                    value="Fiscal"
                    className="w-full px-3 py-2 text-xs bg-slate-100 font-bold text-slate-600 border border-slate-200 rounded-lg cursor-not-allowed"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={carregandoCad}
                className="w-full mt-2 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 shadow-xs"
              >
                {carregandoCad ? 'Cadastrando...' : 'Criar Conta Matriz (Fiscal)'}
              </button>
            </form>
          </div>
        </div>

        {/* Rodapé Institucional */}
        <div className="text-center text-xs text-slate-500 pt-4 border-t border-slate-200/80 space-y-1">
          <div>
            <strong>Sistema Integrado de Gestão Orçamentária e Classificação SIAFI</strong>
          </div>
          <p className="italic text-[11px] text-slate-400">
            Controle de Recursos, Notas de Crédito, Pregões e Requisições Oficiais.
          </p>
        </div>
      </div>

      {/* Modal Redefinir / Alterar Senha */}
      {modalEsqueci && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-slate-200 space-y-5">
            <div className="text-center space-y-1">
              <div className="w-10 h-10 rounded-xl bg-emerald-800 text-white flex items-center justify-center mx-auto">
                <KeyRound className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Alteração de Senha de Usuário
              </h3>
              <p className="text-xs text-slate-500">
                Informe sua identificação para registrar uma nova senha
              </p>
            </div>

            {erroEsqueci && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{erroEsqueci}</span>
              </div>
            )}

            {sucessoEsqueci && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>{sucessoEsqueci}</span>
              </div>
            )}

            <form onSubmit={handleAtualizarSenhaEsqueci} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Identificação do Usuário (Login):
                </label>
                <input
                  type="text"
                  required
                  value={idEsqueci}
                  onChange={e => setIdEsqueci(e.target.value)}
                  placeholder="Ex: seu.usuario ou e-mail"
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Nova Senha:
                </label>
                <input
                  type="password"
                  required
                  value={senhaEsqueci}
                  onChange={e => setSenhaEsqueci(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Confirmar Nova Senha:
                </label>
                <input
                  type="password"
                  required
                  value={confirmaEsqueci}
                  onChange={e => setConfirmaEsqueci(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div className="pt-2 flex justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setModalEsqueci(false)}
                  className="px-3 py-2 border rounded-lg text-slate-600 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={carregandoEsqueci}
                  className="px-4 py-2 bg-emerald-700 text-white rounded-lg font-semibold hover:bg-emerald-800 disabled:opacity-50"
                >
                  {carregandoEsqueci ? 'Salvando...' : 'Confirmar Nova Senha'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
