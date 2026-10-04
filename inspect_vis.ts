import https from 'https';
import * as cheerio from 'cheerio';
import fs from 'fs';

const agent = new https.Agent({ rejectUnauthorized: false });

async function inspectVisItem() {
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
  
  // Salva o HTML para podermos examinar
  fs.writeFileSync('/tmp/vis_item.html', htmlVis);
  console.log('HTML salvo em /tmp/vis_item.html, tamanho:', htmlVis.length);

  const $ = cheerio.load(htmlVis);
  
  // Procura fornecedor, CNPJ, valor, 3770, etc.
  console.log('--- BUSCANDO VALORES RELEVANTES ---');
  $('tr').each((i, tr) => {
    const text = $(tr).text().replace(/\s+/g, ' ').trim();
    if (text.includes('3.770') || text.includes('3770') || text.includes('Fornecedor') || text.includes('Homologado') || text.includes('120') || text.includes('220')) {
      console.log(`TR ${i}:`, text);
    }
  });

  // Mostra todos os inputs com seus names e values
  console.log('--- INPUTS ---');
  $('input').each((_, inp) => {
    const name = $(inp).attr('name');
    const val = $(inp).attr('value');
    if (name && val && val.trim()) {
      console.log(`${name} = "${val}"`);
    }
  });

  // Também busca links em visualizarItemSRP
  console.log('--- LINKS ---');
  $('a').each((_, a) => {
    const href = $(a).attr('href') || '';
    const text = $(a).text().trim();
    if (href.includes('javascript') || href.includes('.do')) {
      console.log(`Link: ${text} => ${href}`);
    }
  });
}

inspectVisItem().catch(console.error);
