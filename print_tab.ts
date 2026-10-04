import https from 'https';
import * as cheerio from 'cheerio';

const agent = new https.Agent({ rejectUnauthorized: false });

async function printTables() {
  const uasg = '160440';
  const numCompra = '90003';
  const anoCompra = '2025';

  const initRes = await (fetch as any)('https://www2.comprasnet.gov.br/siasgnet-atasrp/public/pesquisarLicitacaoSRP.do?method=iniciar', { headers: { 'User-Agent': 'Mozilla/5.0' }, agent });
  const setCookie = initRes.headers.get('set-cookie');
  const cookie = setCookie ? setCookie.split(',').map(c => c.split(';')[0]).join('; ') : '';

  const urlItens = `https://www2.comprasnet.gov.br/siasgnet-atasrp/public/pesquisarItemSRP.do?method=iniciar&parametro.identificacaoCompra.numeroUasg=${uasg}&parametro.identificacaoCompra.modalidadeCompra=5&parametro.identificacaoCompra.numeroCompra=${numCompra}&parametro.identificacaoCompra.anoCompra=${anoCompra}`;
  const resItens = await (fetch as any)(urlItens, { headers: { 'User-Agent': 'Mozilla/5.0', 'Cookie': cookie }, agent });
  const htmlItens = await resItens.text();
  const m = htmlItens.match(/selecionarItem\((\d+)\)/);
  if (!m) return;

  const codItem = m[1];
  const urlVis = `https://www2.comprasnet.gov.br/siasgnet-atasrp/public/visualizarItemSRP.do?method=iniciar&itemAtaSRP.codigoItemAtaSRP=${codItem}`;
  const resVis = await (fetch as any)(urlVis, { headers: { 'User-Agent': 'Mozilla/5.0', 'Cookie': cookie }, agent });
  const htmlVis = await resVis.text();
  const $v = cheerio.load(htmlVis);

  for (let i = 0; i <= 9; i++) {
    const tbl = $v('table').eq(i);
    console.log(`\nTABELA ${i} (id="${tbl.attr('id')}", class="${tbl.attr('class')}"):`);
    tbl.find('tr').each((j, tr) => {
      const cells = $v(tr).find('th, td').map((_, el) => $v(el).text().replace(/\s+/g, ' ').trim()).get();
      console.log(`  TR ${j}:`, cells);
    });
  }
}

printTables().catch(console.error);
