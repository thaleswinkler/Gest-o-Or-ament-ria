import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import { consultarPregoes, consultarItensPregao } from './server/siasgService';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // 1. API: Consultar pregões da UASG via SIASGnet
  app.get('/api/pregoes', async (req, res) => {
    const uasg = String(req.query.uasg || '').trim();
    const anosParam = String(req.query.anos || '2026,2025,2024').trim();

    if (!uasg) {
      return res.status(400).json({ error: 'UASG é obrigatória' });
    }

    const anos = anosParam.split(',').map(a => a.trim()).filter(Boolean);

    try {
      const dados = await consultarPregoes(uasg, anos);
      return res.json(dados);
    } catch (err: any) {
      console.error('Erro ao consultar pregoes:', err);
      return res.status(500).json({ error: 'Erro ao consultar SIASGnet', details: err?.message || String(err) });
    }
  });

  // 2. API: Consultar itens de um pregão específico com saldo
  app.get('/api/pregao-itens', async (req, res) => {
    const uasg = String(req.query.uasg || '').trim();
    const numCompra = String(req.query.numCompra || '').trim();
    const anoCompra = String(req.query.anoCompra || '').trim();

    if (!uasg || !numCompra || !anoCompra) {
      return res.status(400).json({ error: 'UASG, numCompra e anoCompra são obrigatórios' });
    }

    try {
      const dados = await consultarItensPregao(uasg, numCompra, anoCompra);
      return res.json(dados);
    } catch (err: any) {
      console.error('Erro ao consultar itens do pregao:', err);
      return res.status(500).json({ error: 'Erro ao consultar itens no SIASG', details: err?.message || String(err) });
    }
  });

  // Health check
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', time: new Date().toISOString() });
  });

  // Vite middleware setup
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
