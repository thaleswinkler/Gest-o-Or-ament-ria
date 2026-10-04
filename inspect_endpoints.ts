import https from 'https';

const agent = new https.Agent({ rejectUnauthorized: false });

async function inspectEndpoints() {
  const res = await (fetch as any)('https://dadosabertos.compras.gov.br/v3/api-docs', { headers: { 'User-Agent': 'Mozilla/5.0' }, agent });
  const doc = await res.json();

  const targets = [
    '/modulo-contratacoes/1_consultarContratacoes_PNCP_14133',
    '/modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133',
    '/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133',
    '/modulo-arp/1_consultarARP',
    '/modulo-arp/2_consultarARPItem',
    '/modulo-arp/4_consultarEmpenhosSaldoItem'
  ];

  for (const t of targets) {
    console.log(`\n================== ${t} ==================`);
    const pathObj = doc.paths[t];
    if (pathObj) {
      const getObj = pathObj.get || pathObj.post;
      console.log('Summary:', getObj.summary);
      console.log('Parameters:');
      getObj.parameters?.forEach((p: any) => {
        console.log(`  - ${p.name} (${p.in}): ${p.description || ''} [required: ${p.required}]`);
      });
    }
  }
}

inspectEndpoints().catch(console.error);
