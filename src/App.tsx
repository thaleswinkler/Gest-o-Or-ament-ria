import { useState, useEffect, useCallback } from 'react';
import { Navbar, AbaNavegacao } from './components/Navbar';
import { TabCadastro } from './components/TabCadastro';
import { TabVisualizacao } from './components/TabVisualizacao';
import { TabVisaoGlobal } from './components/TabVisaoGlobal';
import { TabPregoes } from './components/TabPregoes';
import { TabGerenciamentoUsuarios } from './components/TabGerenciamentoUsuarios';
import { LoginScreen } from './components/LoginScreen';
import { LoginModal } from './components/LoginModal';
import { 
  Usuario, 
  BancoNCs, 
  NotaCredito, 
  ConfigRequisicao 
} from './types';
import { 
  carregarDadosSecao, 
  salvarDadosSecao, 
  carregarSecoesDaOM, 
  CONFIG_PADRAO_REQUISICAO 
} from './lib/supabase';
import { Loader2, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    const saved = localStorage.getItem('usuario_sessao');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // fallback
      }
    }
    return null;
  });

  const [modalLoginAberto, setModalLoginAberto] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState<AbaNavegacao>('cadastro');
  const [anoFiltro, setAnoFiltro] = useState('2026');
  const [ncSelecionada, setNcSelecionada] = useState<string>('');
  const [secoesDisponiveis, setSecoesDisponiveis] = useState<string[]>([]);
  const [secaoAtual, setSecaoAtual] = useState<string>('');

  const [banco, setBanco] = useState<BancoNCs>({});
  const [carregandoDados, setCarregandoDados] = useState(false);
  const [salvandoNoBanco, setSalvandoNoBanco] = useState(false);
  const [notificacao, setNotificacao] = useState<{ tipo: 'sucesso' | 'erro'; texto: string } | null>(null);

  const mostrarNotificacao = (tipo: 'sucesso' | 'erro', texto: string) => {
    setNotificacao({ tipo, texto });
    setTimeout(() => setNotificacao(null), 3500);
  };

  // Carrega seções da OM e dados da seção ativa
  const carregarDados = useCallback(async (om: string, sec: string) => {
    if (!om) return;
    setCarregandoDados(true);
    try {
      // 1. Carrega seções cadastradas da OM
      const secs = await carregarSecoesDaOM(om);
      if (secs.length > 0) {
        setSecoesDisponiveis(secs);
        if (!secs.includes(sec)) {
          sec = secs[0];
          setSecaoAtual(sec);
        }
      }

      // 2. Carrega dados da seção atual do Supabase
      const dados = await carregarDadosSecao(om, sec);
      setBanco(dados);

      // Define NC selecionada padrão
      const chavesValidas = Object.keys(dados).filter(k => k !== 'CONFIG_REQUISICAO');
      if (chavesValidas.length > 0 && !ncSelecionada) {
        setNcSelecionada(chavesValidas[0]);
      }
    } catch (err: any) {
      console.error('Erro ao carregar dados:', err);
      mostrarNotificacao('erro', 'Não foi possível sincronizar com o Supabase. Utilizando cache local.');
    } finally {
      setCarregandoDados(false);
    }
  }, [ncSelecionada]);

  useEffect(() => {
    if (usuario?.om) {
      carregarDados(usuario.om, secaoAtual || usuario.secao);
    }
  }, [usuario?.om, usuario?.secao, secaoAtual, carregarDados]);

  // Configuração atual da requisição
  const configRequisicao: ConfigRequisicao = 
    (banco['CONFIG_REQUISICAO'] as ConfigRequisicao) || CONFIG_PADRAO_REQUISICAO;

  // Salva ou atualiza uma NC no Supabase
  const handleSalvarNC = async (chaveNC: string, nc: NotaCredito) => {
    if (!usuario) return;
    setSalvandoNoBanco(true);
    const novoBanco = {
      ...banco,
      [chaveNC]: nc
    };
    setBanco(novoBanco);
    setNcSelecionada(chaveNC);

    try {
      await salvarDadosSecao(usuario.om, secaoAtual || usuario.secao, novoBanco);
      mostrarNotificacao('sucesso', `Nota de Crédito ${chaveNC} salva com sucesso.`);
    } catch (err: any) {
      console.error(err);
      mostrarNotificacao('erro', 'Falha ao sincronizar com o banco Supabase.');
    } finally {
      setSalvandoNoBanco(false);
    }
  };

  // Exclui uma NC do Supabase
  const handleExcluirNC = async (chaveNC: string) => {
    if (!usuario) return;
    setSalvandoNoBanco(true);
    const novoBanco = { ...banco };
    delete novoBanco[chaveNC];
    setBanco(novoBanco);

    if (ncSelecionada === chaveNC) {
      const restantes = Object.keys(novoBanco).filter(k => k !== 'CONFIG_REQUISICAO');
      setNcSelecionada(restantes[0] || '');
    }

    try {
      await salvarDadosSecao(usuario.om, secaoAtual || usuario.secao, novoBanco);
      mostrarNotificacao('sucesso', `Nota de Crédito ${chaveNC} excluída.`);
    } catch (err: any) {
      console.error(err);
      mostrarNotificacao('erro', 'Falha ao sincronizar exclusão com o Supabase.');
    } finally {
      setSalvandoNoBanco(false);
    }
  };

  // Salva configurações do documento oficial (cabeçalho e assinaturas)
  const handleSalvarConfig = async (novaConfig: ConfigRequisicao) => {
    if (!usuario) return;
    setSalvandoNoBanco(true);
    const novoBanco = {
      ...banco,
      CONFIG_REQUISICAO: novaConfig
    };
    setBanco(novoBanco);

    try {
      await salvarDadosSecao(usuario.om, secaoAtual || usuario.secao, novoBanco);
      mostrarNotificacao('sucesso', 'Configurações do documento oficial atualizadas.');
    } catch (err: any) {
      console.error(err);
      mostrarNotificacao('erro', 'Falha ao salvar configurações no Supabase.');
    } finally {
      setSalvandoNoBanco(false);
    }
  };

  const handleLoginSucesso = (user: Usuario) => {
    setUsuario(user);
    setSecaoAtual(user.secao);
    localStorage.setItem('usuario_sessao', JSON.stringify(user));
    setModalLoginAberto(false);
    mostrarNotificacao('sucesso', `Bem-vindo, ${user.nome || user.id}!`);
  };

  const handleLogout = () => {
    localStorage.removeItem('usuario_sessao');
    setUsuario(null);
    setBanco({});
  };

  const handleMudarSecao = (novaSec: string) => {
    if (!usuario) return;
    setSecaoAtual(novaSec);
    carregarDados(usuario.om, novaSec);
  };

  const handleSelecionarNCParaVisualizar = (chaveNC: string) => {
    setNcSelecionada(chaveNC);
    setAbaAtiva('visualizacao');
  };

  // Se o militar não estiver logado, exibe a tela cheia de Login & Cadastro Matriz da OM
  if (!usuario) {
    return <LoginScreen onLoginSucesso={handleLoginSucesso} />;
  }

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-900 flex flex-col antialiased">
      {/* Navbar Superior */}
      <Navbar
        usuario={usuario}
        anoFiltro={anoFiltro}
        onMudarAno={setAnoFiltro}
        abaAtiva={abaAtiva}
        onMudarAba={setAbaAtiva}
        secoesDisponiveis={secoesDisponiveis}
        secaoAtual={secaoAtual}
        onMudarSecao={handleMudarSecao}
        onLogout={handleLogout}
      />

      {/* Notificação Flutuante */}
      {notificacao && (
        <div
          className={`fixed top-16 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg border text-xs font-medium flex items-center gap-2 transition-all ${
            notificacao.tipo === 'sucesso'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-red-50 border-red-300 text-red-900'
          }`}
        >
          {notificacao.tipo === 'sucesso' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{notificacao.texto}</span>
        </div>
      )}

      {/* Indicador de Salvamento em Segundo Plano */}
      {salvandoNoBanco && (
        <div className="fixed bottom-4 right-4 z-50 bg-slate-900 text-white px-3 py-1.5 rounded-full shadow-lg text-[11px] font-medium flex items-center gap-2 border border-slate-700">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
          <span>Salvando no Supabase...</span>
        </div>
      )}

      {/* Conteúdo Principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {carregandoDados ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-3">
            <Loader2 className="w-8 h-8 text-emerald-700 animate-spin" />
            <p className="text-xs font-medium text-slate-500">
              Sincronizando recursos orçamentários do Supabase ({usuario.om} • {secaoAtual})...
            </p>
          </div>
        ) : (
          <div>
            {abaAtiva === 'cadastro' && (
              <TabCadastro
                banco={banco}
                anoFiltro={anoFiltro}
                perfil={usuario.perfil}
                onSalvarNC={handleSalvarNC}
                onExcluirNC={handleExcluirNC}
                onSelecionarNCParaVisualizar={handleSelecionarNCParaVisualizar}
              />
            )}

            {abaAtiva === 'visualizacao' && (
              <TabVisualizacao
                banco={banco}
                ncSelecionada={ncSelecionada}
                onSelecionarNC={setNcSelecionada}
                anoFiltro={anoFiltro}
                perfil={usuario.perfil}
                configRequisicao={configRequisicao}
                onSalvarNC={handleSalvarNC}
                onSalvarConfig={handleSalvarConfig}
              />
            )}

            {abaAtiva === 'global' && (
              <TabVisaoGlobal
                banco={banco}
                anoFiltro={anoFiltro}
                om={usuario.om}
                secao={secaoAtual}
              />
            )}

            {abaAtiva === 'pregoes' && (
              <TabPregoes
                banco={banco}
                anoFiltro={anoFiltro}
                isFiscal={usuario.perfil === 'Fiscal'}
                onSalvarNC={handleSalvarNC}
              />
            )}

            {abaAtiva === 'equipe' && (
              <TabGerenciamentoUsuarios
                usuarioLogado={usuario}
                secoesDisponiveis={secoesDisponiveis}
              />
            )}
          </div>
        )}
      </main>

      {/* Modal de Autenticação / Troca de Usuário */}
      {modalLoginAberto && (
        <LoginModal
          usuarioAtual={usuario}
          onLoginSucesso={handleLoginSucesso}
          onClose={() => setModalLoginAberto(false)}
        />
      )}
    </div>
  );
}
