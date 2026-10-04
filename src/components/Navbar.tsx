import { Shield, User, LogOut, Layers, CreditCard, BarChart2, Calendar, Building, Search, Users } from 'lucide-react';
import { Usuario } from '../types';

export type AbaNavegacao = 'cadastro' | 'visualizacao' | 'global' | 'pregoes' | 'equipe';

interface NavbarProps {
  usuario: Usuario;
  anoFiltro: string;
  onMudarAno: (ano: string) => void;
  abaAtiva: AbaNavegacao;
  onMudarAba: (aba: AbaNavegacao) => void;
  secoesDisponiveis: string[];
  secaoAtual: string;
  onMudarSecao: (secao: string) => void;
  onLogout: () => void;
}

export function Navbar({
  usuario,
  anoFiltro,
  onMudarAno,
  abaAtiva,
  onMudarAba,
  secoesDisponiveis,
  secaoAtual,
  onMudarSecao,
  onLogout
}: NavbarProps) {
  const anos = ['2024', '2025', '2026', 'Todos'];

  return (
    <header className="bg-slate-900 text-white sticky top-0 z-40 shadow-md border-b border-slate-800">
      {/* Barra de Informações do Usuário e OM */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 border-b border-slate-800/80">
          {/* Logo e Título Oficial */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-700 flex items-center justify-center font-bold text-xs text-white shadow-xs">
              EB
            </div>
            <div>
              <h1 className="text-xs sm:text-sm font-bold tracking-tight text-white flex items-center gap-2">
                <span>Gestão de Recursos &amp; Notas de Crédito</span>
                <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                  {usuario.om}
                </span>
              </h1>
              <p className="text-[10px] text-slate-400 hidden sm:block">
                Controle Orçamentário e Classificação Inteligente por Função SIAFI
              </p>
            </div>
          </div>

          {/* Filtros e Usuário */}
          <div className="flex items-center gap-3 text-xs">
            {/* Seletor de Ano */}
            <div className="flex items-center gap-1.5 bg-slate-800 px-2 py-1 rounded-md border border-slate-700">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={anoFiltro}
                onChange={e => onMudarAno(e.target.value)}
                className="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer"
              >
                {anos.map(ano => (
                  <option key={ano} value={ano} className="bg-slate-800 text-white">
                    Ano: {ano}
                  </option>
                ))}
              </select>
            </div>

            {/* Seletor de Seção (se houver mais de uma) */}
            {secoesDisponiveis.length > 1 && (
              <div className="flex items-center gap-1.5 bg-slate-800 px-2 py-1 rounded-md border border-slate-700">
                <Building className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={secaoAtual}
                  onChange={e => onMudarSecao(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer"
                >
                  {secoesDisponiveis.map(sec => (
                    <option key={sec} value={sec} className="bg-slate-800 text-white">
                      {sec}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Badge do Usuário */}
            <div className="hidden md:flex items-center gap-2 pl-2 border-l border-slate-800">
              <div className="text-right">
                <div className="text-xs font-medium text-white flex items-center gap-1.5 justify-end">
                  <span>{usuario.nome || usuario.id}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                      usuario.perfil === 'Chefe'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : usuario.perfil === 'Fiscal'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {usuario.perfil}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400">
                  {usuario.secao} • {usuario.om}
                </div>
              </div>

              <button
                onClick={onLogout}
                title="Desconectar"
                className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Abas de Navegação */}
        <nav className="flex space-x-1 sm:space-x-3 py-2 overflow-x-auto">
          <button
            onClick={() => onMudarAba('cadastro')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              abaAtiva === 'cadastro'
                ? 'bg-emerald-700 text-white shadow-xs font-semibold'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>📝 Cadastrar e Lançar Compras</span>
          </button>

          <button
            onClick={() => onMudarAba('visualizacao')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              abaAtiva === 'visualizacao'
                ? 'bg-emerald-700 text-white shadow-xs font-semibold'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>📊 Controle Individual por NC</span>
          </button>

          <button
            onClick={() => onMudarAba('global')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              abaAtiva === 'global'
                ? 'bg-emerald-700 text-white shadow-xs font-semibold'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>📈 Visão Global do Ano</span>
          </button>

          <button
            onClick={() => onMudarAba('pregoes')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              abaAtiva === 'pregoes'
                ? 'bg-emerald-700 text-white shadow-xs font-semibold'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>🔎 Consultar Pregões &amp; Importar para NC</span>
          </button>

          <button
            onClick={() => onMudarAba('equipe')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              abaAtiva === 'equipe'
                ? 'bg-emerald-700 text-white shadow-xs font-semibold'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>👥 Gerenciar Acessos</span>
          </button>
        </nav>
      </div>
    </header>
  );
}
