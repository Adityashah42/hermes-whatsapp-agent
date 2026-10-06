const express = require('express');
const axios = require('axios');
const qrcodeTerminal = require('qrcode-terminal');
const { create } = require('@open-wa/wa-automate');
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

// API Key authentication middleware
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

// Endpoints
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    sessionStatus,
    clientConnected: !!waClient,
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
    if (!waClient) {
      return res.status(503).json({ error: 'WhatsApp client is not connected' });
    }
    console.log(`[openwa] Sending message to ${chatId}: ${content.substring(0, 50)}...`);
    const result = await waClient.sendText(chatId, content);
    res.json({ success: true, result });
  } catch (error) {
    console.error('[openwa] Error sending message:', error.message);
    res.status(500).json({ error: error.message });
  }
});

// Helper to forward incoming message to Hermes webhook
async function forwardToHermes(message) {
  if (!WEBHOOK_URL) return;
  try {
    const payload = JSON.stringify(message);
    const headers = { 'Content-Type': 'application/json' };
    if (WEBHOOK_SECRET) {
      const signature = crypto.createHmac('sha256', WEBHOOK_SECRET).update(payload).digest('hex');
      headers['X-OpenWA-Signature'] = signature;
    }
    console.log(`[openwa] Forwarding message from ${message.from} to ${WEBHOOK_URL}...`);
    const response = await axios.post(WEBHOOK_URL, message, { headers, timeout: 60000 });
    console.log(`[openwa] Hermes response status: ${response.status}`);
  } catch (error) {
    console.error(`[openwa] Failed to forward message to Hermes webhook: ${error.message}`);
  }
}

async function initWhatsApp() {
  console.log('=== Initializing WhatsApp Client via @open-wa/wa-automate ===');
  console.log(`Session directory: ${DATA_DIR}`);
  console.log(`Webhook URL: ${WEBHOOK_URL}`);

  try {
    const client = await create({
      sessionId: 'default',
      sessionDataPath: DATA_DIR,
      multiDevice: true,
      headless: true,
      useChrome: true,
      executablePath: '/usr/bin/google-chrome-stable',
      qrTimeout: 0,
      authTimeout: 0,
      cacheEnabled: false,
      restartOnCrash: true,
      disableSpins: true,
      qrRefreshS: 20,
      catchQR: (qrCode, asciiQR, attempts, urlCode) => {
        latestQr = qrCode;
        sessionStatus = 'QR_READY';
        console.log('\n========================================================');
        console.log('SCAN THIS QR CODE IN WHATSAPP (Settings > Linked Devices):');
        console.log('========================================================\n');
        if (asciiQR) {
          console.log(asciiQR);
        } else {
          qrcodeTerminal.generate(qrCode, { small: true }, qrcode => {
            console.log(qrcode);
          });
        }
        console.log(`\nQR Code attempt #${attempts}. Waiting for phone scan...\n`);
      },
      statusFind: (statusSession, session) => {
        console.log(`[openwa] Session status changed: ${statusSession}`);
        if (statusSession === 'isLogged' || statusSession === 'chatsAvailable') {
          sessionStatus = 'CONNECTED';
          latestQr = null;
        } else if (statusSession === 'notLogged') {
          sessionStatus = 'DISCONNECTED';
        }
      }
    });

    waClient = client;
    sessionStatus = 'CONNECTED';
    console.log('✓ WhatsApp Client Connected and Ready!');

    client.onMessage(async message => {
      // Ignore broadcast messages or status updates
      if (message.isGroupMsg || message.from === 'status@broadcast') {
        return;
      }
      console.log(`[openwa] Received incoming message from ${message.from}: ${message.body || '[media]'}`);
      await forwardToHermes(message);
    });

    client.onStateChanged(state => {
      console.log(`[openwa] WhatsApp connection state: ${state}`);
      if (state === 'CONFLICT' || state === 'UNLAUNCHED') {
        client.forceRefocus();
      }
    });

  } catch (error) {
    console.error('[openwa] WhatsApp client initialization error:', error);
    sessionStatus = 'ERROR';
  }
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`=== OpenWA API Server running on port ${PORT} ===`);
  initWhatsApp();
});
