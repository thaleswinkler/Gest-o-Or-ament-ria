import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { Usuario, BancoNCs, ConfigRequisicao } from '../types';

export const SUPABASE_URL = 'https://oxneqoegehufjksvupji.supabase.co';
export const SUPABASE_ANON_KEY = 'sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX';

export const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export async function hashSenha(senha: string): Promise<string> {
  if (!senha) return '';
  const encoder = new TextEncoder();
  const data = encoder.encode(senha);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function checarSenha(senhaDigitada: string, senhaDb: string): Promise<boolean> {
  if (!senhaDb) return false;
  if (senhaDb === senhaDigitada) return true;
  const hash = await hashSenha(senhaDigitada);
  return senhaDb === hash;
}

export async function loginUsuario(idUser: string, senhaInput: string): Promise<Usuario> {
  const cleanId = (idUser || '').trim().toLowerCase();
  const { data, error } = await supabase
    .from('usuarios')
    .select('*')
    .eq('id', cleanId)
    .single();

  if (error || !data) {
    throw new Error('Usuário não encontrado.');
  }

  const senhaCorreta = await checarSenha(senhaInput, data.senha);
  if (!senhaCorreta) {
    throw new Error('Senha incorreta.');
  }

  // Se a senha do banco ainda estiver em texto puro, atualiza para o hash SHA-256
  const hash = await hashSenha(senhaInput);
  if (data.senha !== hash) {
    await supabase.from('usuarios').update({ senha: hash }).eq('id', cleanId);
  }

  return {
    id: data.id,
    nome: data.nome,
    om: data.om,
    secao: data.secao,
    perfil: data.perfil
  };
}

export async function alterarSenha(idUser: string, novaSenha: string): Promise<void> {
  const hash = await hashSenha(novaSenha);
  const { error } = await supabase
    .from('usuarios')
    .update({ senha: hash })
    .eq('id', (idUser || '').trim().toLowerCase());

  if (error) throw new Error(`Falha ao alterar senha: ${error.message}`);
}

export async function carregarSecoesDaOM(om: string): Promise<string[]> {
  const { data, error } = await supabase
    .from('usuarios')
    .select('secao')
    .eq('om', om);

  if (error || !data) return [];
  const secoes = Array.from(new Set(data.map((u: { secao: string }) => u.secao).filter(Boolean))) as string[];
  return secoes;
}

export async function carregarDadosSecao(om: string, secao: string): Promise<BancoNCs> {
  const idSecao = `${om}_${secao}`;
  const { data, error } = await supabase
    .from('dados')
    .select('ncs')
    .eq('id', idSecao)
    .maybeSingle();

  if (error) {
    console.error('Erro ao carregar dados do Supabase:', error);
    // Tenta carregar do cache local
    const cached = localStorage.getItem(`dados_${idSecao}`);
    if (cached) return JSON.parse(cached);
    return {};
  }

  if (!data || !data.ncs) {
    // Inicializa se não existir
    await supabase.from('dados').upsert({ id: idSecao, ncs: {} });
    return {};
  }

  const ncsObj = data.ncs as BancoNCs;
  try {
    localStorage.setItem(`dados_${idSecao}`, JSON.stringify(ncsObj));
  } catch (e) {
    console.warn('Falha ao salvar cache local:', e);
  }

  return ncsObj;
}

export async function salvarDadosSecao(om: string, secao: string, ncs: BancoNCs): Promise<void> {
  const idSecao = `${om}_${secao}`;

  // Atualiza cache local imediatamente para otimismo de UI
  try {
    localStorage.setItem(`dados_${idSecao}`, JSON.stringify(ncs));
  } catch (e) {
    console.warn(e);
  }

  const { error } = await supabase
    .from('dados')
    .upsert({ id: idSecao, ncs });

  if (error) {
    throw new Error(`Erro ao salvar no banco Supabase: ${error.message}`);
  }
}

export async function carregarTodasSecoesOM(om: string): Promise<Array<{ id: string; secao: string; ncs: BancoNCs }>> {
  const { data, error } = await supabase
    .from('dados')
    .select('*')
    .like('id', `${om}_%`);

  if (error || !data) return [];

  return data.map((item: any) => {
    const parts = item.id.split('_');
    const secao = parts.slice(1).join('_') || 'Principal';
    return {
      id: item.id,
      secao,
      ncs: (item.ncs || {}) as BancoNCs
    };
  });
}

export async function listarUsuariosOM(om: string): Promise<Usuario[]> {
  const { data, error } = await supabase
    .from('usuarios')
    .select('*')
    .eq('om', om);

  if (error || !data) return [];
  return data.map((u: any) => ({
    id: u.id,
    nome: u.nome,
    om: u.om,
    secao: u.secao,
    perfil: u.perfil
  }));
}

export async function criarNovoUsuario(novo: Usuario & { senha: string }): Promise<void> {
  const cleanId = (novo.id || '').trim().toLowerCase();
  
  // Verifica se o ID já existe
  const { data: existente } = await supabase
    .from('usuarios')
    .select('id')
    .eq('id', cleanId)
    .maybeSingle();

  if (existente) {
    throw new Error(`O usuário '${cleanId}' já existe.`);
  }

  if (novo.perfil === 'Fiscal') {
    const { data: fiscais } = await supabase
      .from('usuarios')
      .select('id')
      .eq('om', novo.om)
      .eq('perfil', 'Fiscal');

    if (fiscais && fiscais.length > 0) {
      throw new Error(`A OM '${novo.om}' já possui um Fiscal cadastrado.`);
    }
  }

  const hash = await hashSenha(novo.senha);
  const { error } = await supabase.from('usuarios').insert({
    id: cleanId,
    nome: novo.nome.trim(),
    senha: hash,
    om: novo.om.trim(),
    secao: novo.secao.trim(),
    perfil: novo.perfil
  });

  if (error) {
    throw new Error(`Erro ao criar usuário: ${error.message}`);
  }

  // Garante que o cofre de dados da seção exista
  const idCofre = `${novo.om.trim()}_${novo.secao.trim()}`;
  const { data: checkCofre } = await supabase
    .from('dados')
    .select('id')
    .eq('id', idCofre)
    .maybeSingle();

  if (!checkCofre) {
    await supabase.from('dados').insert({ id: idCofre, ncs: {} });
  }
}

export async function transferirPerfilUsuario(
  usuarioOrigemId: string,
  novoPerfilOrigem: PerfilUsuario,
  usuarioDestinoId: string,
  novoPerfilDestino: PerfilUsuario
): Promise<void> {
  const { error: errDest } = await supabase
    .from('usuarios')
    .update({ perfil: novoPerfilDestino })
    .eq('id', usuarioDestinoId);

  if (errDest) {
    throw new Error(`Erro ao atualizar perfil do destinatário: ${errDest.message}`);
  }

  const { error: errOrig } = await supabase
    .from('usuarios')
    .update({ perfil: novoPerfilOrigem })
    .eq('id', usuarioOrigemId);

  if (errOrig) {
    throw new Error(`Erro ao atualizar perfil do militar de origem: ${errOrig.message}`);
  }
}

export async function excluirUsuario(usuarioId: string): Promise<void> {
  const { error } = await supabase
    .from('usuarios')
    .delete()
    .eq('id', usuarioId);

  if (error) {
    throw new Error(`Erro ao excluir militar: ${error.message}`);
  }
}

export const CONFIG_PADRAO_REQUISICAO: ConfigRequisicao = {
  cabecalho_om: 'MINISTÉRIO DA DEFESA\nEXÉRCITO BRASILEIRO\nORGANIZAÇÃO MILITAR\nSEÇÃO ADMINISTRATIVA',
  indicativo_diex: 'DIEx nº ___ - Sec/OM',
  cidade_om: 'Cidade - UF',
  remetente_do: 'Chefe da Seção Requisitante',
  od_nome: 'NOME DO OD - Posto',
  od_funcao: 'Ordenador de Despesas',
  assinatura_nome: 'NOME DO REQUISITANTE - Posto/Grad',
  assinatura_funcao: 'Gestor de Recursos / Encarregado de Material'
};
