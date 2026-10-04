import { useState, type FormEvent } from 'react';
import { ShieldCheck, Lock, User, KeyRound, AlertCircle, Check } from 'lucide-react';
import { Usuario } from '../types';
import { loginUsuario, alterarSenha } from '../lib/supabase';

interface LoginModalProps {
  usuarioAtual: Usuario | null;
  onLoginSucesso: (user: Usuario) => void;
  onClose?: () => void;
}

export function LoginModal({
  usuarioAtual,
  onLoginSucesso,
  onClose
}: LoginModalProps) {
  const [modoAlterarSenha, setModoAlterarSenha] = useState(false);
  const [idUser, setIdUser] = useState(usuarioAtual?.id || '');
  const [senha, setSenha] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmaNovaSenha, setConfirmaNovaSenha] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [mensagemSucesso, setMensagemSucesso] = useState('');

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setErro('');
    setCarregando(true);
    try {
      const user = await loginUsuario(idUser, senha);
      onLoginSucesso(user);
    } catch (err: any) {
      setErro(err.message || 'Credenciais inválidas.');
    } finally {
      setCarregando(false);
    }
  };

  const handleAlterarSenha = async (e: FormEvent) => {
    e.preventDefault();
    setErro('');
    if (!novaSenha) {
      setErro('Digite a nova senha.');
      return;
    }
    if (novaSenha !== confirmaNovaSenha) {
      setErro('As novas senhas não coincidem.');
      return;
    }

    setCarregando(true);
    try {
      await alterarSenha(idUser, novaSenha);
      setMensagemSucesso('Senha alterada com sucesso! Faça login com a nova senha.');
      setModoAlterarSenha(false);
      setSenha('');
    } catch (err: any) {
      setErro(err.message || 'Falha ao alterar senha.');
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-slate-200 space-y-6">
        {/* Cabeçalho */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-emerald-800 text-white flex items-center justify-center mx-auto shadow-md">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">
            {modoAlterarSenha ? 'Alteração de Senha' : 'Autenticação no Sistema'}
          </h2>
          <p className="text-xs text-slate-500">
            Gestão de Recursos e Notas de Crédito (NCs) • Exército Brasileiro
          </p>
        </div>

        {erro && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{erro}</span>
          </div>
        )}

        {mensagemSucesso && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
            <Check className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{mensagemSucesso}</span>
          </div>
        )}

        {!modoAlterarSenha ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Identificação do Usuário:
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  placeholder="Seu usuário ou e-mail"
                  value={idUser}
                  onChange={e => setIdUser(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Senha de Acesso:
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={senha}
                  onChange={e => setSenha(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={carregando}
              className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 shadow-xs"
            >
              {carregando ? 'Autenticando...' : 'Entrar no Sistema'}
            </button>

            <div className="flex items-center justify-between text-[11px] pt-2">
              <button
                type="button"
                onClick={() => setModoAlterarSenha(true)}
                className="text-slate-500 hover:text-slate-800 flex items-center gap-1"
              >
                <KeyRound className="w-3.5 h-3.5" />
                Alterar minha senha
              </button>

              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="text-slate-400 hover:text-slate-600"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>
        ) : (
          <form onSubmit={handleAlterarSenha} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Identificação do Usuário:
              </label>
              <input
                type="text"
                required
                value={idUser}
                onChange={e => setIdUser(e.target.value)}
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
                value={novaSenha}
                onChange={e => setNovaSenha(e.target.value)}
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
                value={confirmaNovaSenha}
                onChange={e => setConfirmaNovaSenha(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg"
              />
            </div>

            <div className="pt-2 flex justify-between gap-2">
              <button
                type="button"
                onClick={() => setModoAlterarSenha(false)}
                className="px-3 py-2 border rounded-lg text-slate-600 hover:bg-slate-50"
              >
                Voltar
              </button>
              <button
                type="submit"
                disabled={carregando}
                className="px-4 py-2 bg-emerald-700 text-white rounded-lg font-semibold hover:bg-emerald-800 disabled:opacity-50"
              >
                {carregando ? 'Salvando...' : 'Confirmar Nova Senha'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
