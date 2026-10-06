export type PerfilUsuario = 'Chefe' | 'Operador' | 'Fiscal';

export interface Usuario {
  id: string;
  nome: string;
  om: string;
  secao: string;
  perfil: PerfilUsuario;
  senha?: string;
}

export type SituacaoItem = 'Planejamento' | 'Aguardando entrega' | 'Recebido';

export interface ItemNC {
  Item: number;
  Subitem: string;
  Nome: string;
  Qtd: number;
  'Valor Unitário': number;
  Total: number;
  Fornecedor?: string;
  CNPJ?: string;
  Pregão?: string;
  UASG?: string;
  Ata?: string;
  Situação: SituacaoItem;
  Obs?: string;
  'PDF da Ata'?: string;
}

export interface DocInfoFornecedor {
  diex?: string;
  eb?: string;
  data?: string;
  assunto?: string;
  empenho?: string;
}

export interface NotaCredito {
  nd: string;
  pi?: string;
  valor_recebido: number;
  itens: ItemNC[];
  descricao?: string;
  ug_favorecida?: string;
  ug_emitente?: string;
  ano?: string;
  doc_info?: Record<string, DocInfoFornecedor>;
}

export interface ConfigRequisicao {
  cabecalho_om: string;
  indicativo_diex: string;
  cidade_om: string;
  remetente_do: string;
  od_nome: string;
  od_funcao: string;
  assinatura_nome: string;
  assinatura_funcao: string;
}

export type BancoNCs = Record<string, NotaCredito | ConfigRequisicao | any>;

export interface SubitemCatalogoItem {
  subitem: string;
  nd_completa: string;
  nome: string;
  funcao: string;
  keywords: string[];
}

export interface SubitemCorrespondencia {
  subitem: string;
  nd_completa: string;
  nome: string;
  funcao: string;
  score: number;
  termos: string[];
}

export interface PregaoLicitacao {
  uasg: string;
  modalidade: string;
  numero_licitacao: string;
  ano: string;
  objeto: string;
  numero_compra?: string;
  ano_compra?: string;
  codigo_licitacao?: string;
  link_contratos?: string;
}

export interface EmpenhoItemPregao {
  numero: string;
  unidade: string;
  fornecedor?: string;
  data?: string;
  quantidade: number;
  valor?: number;
}

export interface SolicitacaoAdesao {
  unidade: string;
  data: string;
  quantidade: string;
}

export interface ItemPregao {
  Item: string;
  Tipo: string;
  Descrição: string;
  Unidade: string;
  'Qtd Registrada': string;
  'Qtd Empenhada': string;
  'Saldo p/ Empenho': string;
  'Qtd para Adesão'?: string;
  'Saldo para Adesão'?: string;
  'Adesões Aprovadas'?: string;
  'Aceita Adesão'?: string;
  adesoes_solicitacoes?: SolicitacaoAdesao[];
  'Ata Vinculada': string;
  Fornecedor: string;
  'Fornecedor Puro'?: string;
  'CNPJ Puro'?: string;
  'Valor Unitario Sugerido'?: number;
  'Valor Unitário'?: number;
  'PDF da Ata'?: string;
  Deserto?: boolean;
  empenhos?: EmpenhoItemPregao[];
  'Link Olhinho'?: string;
}
