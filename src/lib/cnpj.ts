export interface DadosCNPJ {
  cnpj: string;
  razao_social: string;
  nome_fantasia?: string;
  uf?: string;
  municipio?: string;
  situacao?: string;
}

export function formatarCNPJ(cnpj: string): string {
  const digits = String(cnpj).replace(/\D/g, '');
  if (digits.length !== 14) return cnpj;
  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

export async function consultarCNPJ(cnpjInput: string): Promise<DadosCNPJ | null> {
  const clean = String(cnpjInput).replace(/\D/g, '');
  if (clean.length !== 14) return null;

  // 1. BrasilAPI (rápida, sem auth)
  try {
    const res = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${clean}`, {
      headers: { Accept: 'application/json' }
    });
    if (res.ok) {
      const data = await res.json();
      return {
        cnpj: formatarCNPJ(clean),
        razao_social: data.razao_social || data.nome_fantasia || '',
        nome_fantasia: data.nome_fantasia || '',
        uf: data.uf || '',
        municipio: data.municipio || '',
        situacao: data.descricao_situacao_cadastral || ''
      };
    }
  } catch (e) {
    console.warn('Falha BrasilAPI:', e);
  }

  // 2. Fallback MinhaReceita
  try {
    const res = await fetch(`https://minhareceita.org/${clean}`);
    if (res.ok) {
      const data = await res.json();
      return {
        cnpj: formatarCNPJ(clean),
        razao_social: data.razao_social || '',
        nome_fantasia: data.nome_fantasia || '',
        uf: data.uf || '',
        municipio: data.municipio || '',
        situacao: data.situacao_cadastral || ''
      };
    }
  } catch (e) {
    console.warn('Falha MinhaReceita:', e);
  }

  return null;
}
