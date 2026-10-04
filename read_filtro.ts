import https from 'https';

const agent = new https.Agent({ rejectUnauthorized: false });

async function readFiltro() {
  const urls = [
    'https://contratos.sistema.gov.br/assets/js/admin/forms/arp_transparencia_filtro.js',
    'https://contratos.sistema.gov.br/assets/js/admin/forms/filtro_ata.js'
  ];

  for (const u of urls) {
    console.log('--- LENDO:', u);
    const res = await (fetch as any)(u, { headers: { 'User-Agent': 'Mozilla/5.0' }, agent });
    const text = await res.text();
    console.log(text.substring(0, 1500));
  }
}

readFiltro().catch(console.error);
