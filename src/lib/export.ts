import { NotaCredito, BancoNCs } from '../types';

export function formatarMoedaBRL(valor: number): string {
  return (valor || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  });
}

export function exportarParaCSV(nomeArquivo: string, linhas: Array<Record<string, any>>, colunas: Array<{ chave: string; titulo: string }>): void {
  if (!linhas || linhas.length === 0) return;

  const cabecalho = colunas.map(c => `"${c.titulo.replace(/"/g, '""')}"`).join(';');
  const corpo = linhas.map(linha => {
    return colunas.map(c => {
      let val = linha[c.chave];
      if (val === undefined || val === null) val = '';
      if (typeof val === 'number') {
        // Formata número com vírgula para o Excel padrão brasileiro
        val = String(val).replace('.', ',');
      }
      return `"${String(val).replace(/"/g, '""')}"`;
    }).join(';');
  }).join('\r\n');

  // UTF-8 BOM (\uFEFF) para garantir acentuação correta no Microsoft Excel
  const conteudo = '\uFEFF' + cabecalho + '\r\n' + corpo;
  const blob = new Blob([conteudo], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${nomeArquivo}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportarPlanilhaNC(chaveNC: string, nc: NotaCredito): void {
  const colunas = [
    { chave: 'Item', titulo: 'Nº Item' },
    { chave: 'Subitem', titulo: 'Subitem ND' },
    { chave: 'Nome', titulo: 'Descrição do Material' },
    { chave: 'Qtd', titulo: 'Quantidade' },
    { chave: 'Valor Unitário', titulo: 'Valor Unitário (R$)' },
    { chave: 'Total', titulo: 'Valor Total (R$)' },
    { chave: 'Situação', titulo: 'Situação' },
    { chave: 'Fornecedor', titulo: 'Fornecedor' },
    { chave: 'CNPJ', titulo: 'CNPJ' },
    { chave: 'Pregão', titulo: 'Pregão' },
    { chave: 'Ata', titulo: 'Ata SRP' },
    { chave: 'UASG', titulo: 'UASG' }
  ];

  const linhas = (nc.itens || []).map(it => ({
    ...it,
    'Valor Unitário': (it['Valor Unitário'] || 0).toFixed(2),
    Total: (it.Total || 0).toFixed(2)
  }));

  exportarParaCSV(`Planilha_${chaveNC.replace(/[^a-zA-Z0-9_-]/g, '_')}`, linhas, colunas);
}

export function exportarPlanilhaGlobal(banco: BancoNCs, anoFiltro: string): void {
  const colunas = [
    { chave: 'NC', titulo: 'Nota de Crédito' },
    { chave: 'ND', titulo: 'Natureza de Despesa (ND)' },
    { chave: 'ValorRecebido', titulo: 'Valor Recebido da NC (R$)' },
    { chave: 'Item', titulo: 'Nº Item' },
    { chave: 'Subitem', titulo: 'Subitem ND' },
    { chave: 'Nome', titulo: 'Descrição' },
    { chave: 'Qtd', titulo: 'Quantidade' },
    { chave: 'ValorUnit', titulo: 'Valor Unitário (R$)' },
    { chave: 'TotalItem', titulo: 'Total do Item (R$)' },
    { chave: 'Situacao', titulo: 'Situação' },
    { chave: 'Fornecedor', titulo: 'Fornecedor' },
    { chave: 'CNPJ', titulo: 'CNPJ' },
    { chave: 'Pregao', titulo: 'Pregão' }
  ];

  const linhas: any[] = [];

  for (const [chaveNC, val] of Object.entries(banco)) {
    if (chaveNC === 'CONFIG_REQUISICAO' || !val || typeof val !== 'object') continue;
    const nc = val as NotaCredito;
    if (anoFiltro && anoFiltro !== 'Todos' && !chaveNC.includes(anoFiltro)) continue;

    if (!nc.itens || nc.itens.length === 0) {
      linhas.push({
        NC: chaveNC,
        ND: nc.nd || '',
        ValorRecebido: (nc.valor_recebido || 0).toFixed(2),
        Item: '-',
        Subitem: '-',
        Nome: '(Nenhum item cadastrado)',
        Qtd: 0,
        ValorUnit: 0,
        TotalItem: 0,
        Situacao: '-',
        Fornecedor: '-',
        CNPJ: '-',
        Pregao: '-'
      });
    } else {
      for (const it of nc.itens) {
        linhas.push({
          NC: chaveNC,
          ND: nc.nd || '',
          ValorRecebido: (nc.valor_recebido || 0).toFixed(2),
          Item: it.Item,
          Subitem: it.Subitem || '',
          Nome: it.Nome || '',
          Qtd: it.Qtd || 0,
          ValorUnit: (it['Valor Unitário'] || 0).toFixed(2),
          TotalItem: (it.Total || 0).toFixed(2),
          Situacao: it.Situação || 'Planejamento',
          Fornecedor: it.Fornecedor || '',
          CNPJ: it.CNPJ || '',
          Pregao: it.Pregão || ''
        });
      }
    }
  }

  exportarParaCSV(`Relatorio_Global_Execucao_${anoFiltro}`, linhas, colunas);
}
