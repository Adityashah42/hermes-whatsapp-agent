const express = require('express');
const axios = require('axios');
const qrcodeTerminal = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');

const PORT = parseInt(process.env.PORT || process.env.OPENWA_PORT || '2785', 10);
const API_KEY = process.env.OPENWA_API_KEY || 'default_secret_key';
const WEBHOOK_URL = process.env.OPENWA_WEBHOOK_URL || 'http://hermes.railway.internal:8080/webhook/whatsapp';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || '';
const DATA_DIR = process.env.OPENWA_DATA_PATH || '/app/data';

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const app = express();
app.use(express.json({ limit: '50mb' }));

const authenticate = (req, res, next) => {
  const authHeader = req.headers['x-api-key'] || req.headers['authorization'];
  if (API_KEY && API_KEY !== 'default_secret_key') {
    if (!authHeader || (authHeader !== API_KEY && authHeader !== `Bearer ${API_KEY}`)) {
      return res.status(401).json({ error: 'Unauthorized: Invalid API Key' });
    }
  }
  next();
};

let waClient = null;
let latestQr = null;
let sessionStatus = 'INITIALIZING';

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    sessionStatus,
    clientConnected: sessionStatus === 'CONNECTED',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/sessions/default/status', authenticate, (req, res) => {
  res.json({
    sessionId: 'default',
    status: sessionStatus,
    isLogged: sessionStatus === 'CONNECTED'
  });
});

app.get('/api/sessions/default/qr', authenticate, (req, res) => {
  if (sessionStatus === 'CONNECTED') {
    return res.json({ status: 'already_connected', message: 'WhatsApp is already authenticated and connected.' });
  }
  if (!latestQr) {
    return res.status(404).json({ status: 'qr_not_ready', message: 'QR code not generated yet.' });
  }
  res.json({ status: 'qr_ready', qr: latestQr });
});

app.post('/api/sessions/default/messages/send-text', authenticate, async (req, res) => {
  try {
    const { chatId, content } = req.body;
    if (!chatId || !content) {
      return res.status(400).json({ error: 'Missing chatId or content in request body' });
    }
    if (!waClient || sessionStatus !== 'CONNECTED') {
      return res.status(503).json({ error: 'WhatsApp client is not connected' });
    }
    console.log(`[openwa] Sending message to ${chatId}: ${content.substring(0, 50)}...`);
    const formattedChatId = chatId.includes('@') ? chatId : `${chatId.replace('+', '')}@c.us`;
    const result = await waClient.sendMessage(formattedChatId, content);
    res.json({ success: true, result });
  } catch (error) {
    console.error('[openwa] Error sending message:', error.message);
    res.status(500).json({ error: error.message });
  }
});

async function forwardToHermes(message) {
  if (!WEBHOOK_URL) return;
  try {
    const payload = {
      id: message.id ? (message.id._serialized || message.id.id) : String(Date.now()),
      from: message.from,
      to: message.to,
      body: message.body,
      type: message.type || 'chat',
      timestamp: message.timestamp || Math.floor(Date.now() / 1000),
      isGroupMsg: message.from ? message.from.includes('@g.us') : false,
      sender: {
        id: message.from,
        pushname: message._data ? (message._data.notifyName || '') : ''
      }
    };
    const bodyStr = JSON.stringify(payload);
    const headers = { 'Content-Type': 'application/json' };
    if (WEBHOOK_SECRET) {
      headers['X-OpenWA-Signature'] = crypto.createHmac('sha256', WEBHOOK_SECRET).update(bodyStr).digest('hex');
    }
    console.log(`[openwa] Forwarding message from ${payload.from} to ${WEBHOOK_URL}...`);
    const response = await axios.post(WEBHOOK_URL, payload, { headers, timeout: 60000 });
    console.log(`[openwa] Hermes response status: ${response.status}`);
  } catch (error) {
    console.error(`[openwa] Failed to forward message to Hermes webhook: ${error.message}`);
  }
}

async function initWhatsApp() {
  console.log('=== Initializing WhatsApp Client (Engine: LocalAuth + Puppeteer) ===');
  console.log(`Session directory: ${DATA_DIR}`);
  console.log(`Webhook URL: ${WEBHOOK_URL}`);

  try {
    const client = new Client({
      authStrategy: new LocalAuth({
        dataPath: DATA_DIR,
        clientId: 'default'
      }),
      puppeteer: {
        headless: true,
        executablePath: '/usr/bin/google-chrome-stable',
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--no-first-run'
        ]
      }
    });

    client.on('qr', qr => {
      latestQr = qr;
      sessionStatus = 'QR_READY';
      console.log('\n========================================================');
      console.log('SCAN THIS QR CODE IN WHATSAPP (Settings > Linked Devices):');
      console.log('========================================================\n');
      qrcodeTerminal.generate(qr, { small: true });
      console.log('\nWaiting for phone scan...\n');
    });

    client.on('ready', () => {
      waClient = client;
      sessionStatus = 'CONNECTED';
      latestQr = null;
      console.log('✓ WhatsApp Client Connected and Ready!');
    });

    client.on('authenticated', () => {
      console.log('✓ WhatsApp Client Authenticated successfully!');
      sessionStatus = 'AUTHENTICATED';
    });

    client.on('auth_failure', msg => {
      console.error('[openwa] WhatsApp authentication failure:', msg);
      sessionStatus = 'AUTH_FAILURE';
    });

    client.on('disconnected', reason => {
      console.log('[openwa] WhatsApp client disconnected:', reason);
      sessionStatus = 'DISCONNECTED';
      setTimeout(() => client.initialize(), 5000);
    });

    client.on('message', async msg => {
      if (msg.from && (msg.from.includes('@g.us') || msg.from === 'status@broadcast')) {
        return;
      }
      console.log(`[openwa] Received incoming message from ${msg.from}: ${msg.body || '[media]'}`);
      await forwardToHermes(msg);
    });

    await client.initialize();
  } catch (error) {
    console.error('[openwa] WhatsApp client initialization error:', error);
    sessionStatus = 'ERROR';
  }
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`=== OpenWA API Server running on port ${PORT} ===`);
  initWhatsApp();
});
