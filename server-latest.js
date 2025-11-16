const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');
const { config } = require('dotenv');
const bodyParser = require('body-parser');
const crypto = require('crypto');
const { validateKey, addKey } = require('./db'); // Import Firestore functions

// Load .env variables
config();

// Read the comma-separated list from your .env file
const ALLOWED_ORIGINS_STRING = process.env.ALLOWED_ORIGINS || "http://localhost:8010";
const ALLOWED_ORIGINS_ARRAY = ALLOWED_ORIGINS_STRING.split(',');

// This key is for the ADMIN API
const ADMIN_SECRET_KEY = process.env.ADMIN_SECRET_KEY;
if (!ADMIN_SECRET_KEY) {
    console.error("FATAL ERROR: ADMIN_SECRET_KEY is not set in .env file.");
    process.exit(1);
}

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: ALLOWED_ORIGINS_ARRAY,
    methods: ["GET", "POST"]
  }
});

// Store connected backend clients by group
let backendClients = {
  whisper: null,
  wave2vec: null,
  store: null
};

// Map for rate-limiting browser clients
const clientRateLimit = new Map();

// --- Admin API for Key Generation ---
app.use(bodyParser.json());
app.post('/admin/generate-key', async (req, res) => {
    const { group, auth_secret } = req.body;

    // 1. Check Admin Secret
    if (auth_secret !== ADMIN_SECRET_KEY) {
        return res.status(403).json({ error: "Invalid admin secret" });
    }

    // 2. Check for valid group
    if (!group || !backendClients.hasOwnProperty(group)) {
        return res.status(400).json({ error: "Invalid or missing 'group'" });
    }

    try {
        // 3. Generate new key
        const newKey = `sk_py_${crypto.randomBytes(32).toString('hex')}`;
        
        // 4. Add to Firestore database
        await addKey(newKey, group);
        
        // 5. Return the new key
        res.json({ apiKey: newKey, group: group });

    } catch (e) {
        res.status(500).json({ error: "Failed to generate key. Is it a duplicate?" });
    }
});

// Serve the 'public' folder (for index.html, etc.)
app.use(express.static(path.join(__dirname, 'public')));

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  clientRateLimit.set(socket.id, 0);

  // --- Python Worker Authentication ---
  socket.on('identify_python', async (data) => {
    const { apiKey, group } = data;
    if (!apiKey || !group) {
        console.error(`❌ FAILED auth attempt (missing key or group) from client: ${socket.id}`);
        socket.disconnect();
        return;
    }

    // Validate key against Firestore
    const isValid = await validateKey(apiKey, group);

    if (isValid) {
        if (backendClients.hasOwnProperty(group)) {
            if (backendClients[group]) {
                console.warn(`⚠️ Replacing existing client for group [${group}]: ${backendClients[group]}`);
            }
            backendClients[group] = socket.id;
            socket.backendGroup = group; 
            console.log(`✅ Python client authenticated for group [${group}]: ${socket.id}`);
        } else {
            console.error(`❌ Invalid group name from authenticated client ${socket.id}: ${group}`);
            socket.disconnect();
        }
    } else {
        console.error(`❌ FAILED auth attempt (invalid key) from client: ${socket.id}`);
        socket.disconnect();
    }
  });

  // --- Browser Audio Routing ---
  socket.on('audio_data', (data) => {
    const now = Date.now();
    const lastRequestTime = clientRateLimit.get(socket.id) || 0;
    
    if (now - lastRequestTime < 1000) {
      console.warn(`Rate limit hit for client: ${socket.id}`);
      return; 
    }
    clientRateLimit.set(socket.id, now);

    if (!data || !Array.isArray(data.audioFloat32) || !data.language) {
      console.error(`Invalid data from browser: ${socket.id}`);
      socket.emit('transcription_error', { message: "Invalid data format." });
      return;
    }

    const payload = {
      audioFloat32: data.audioFloat32,
      browserSocketId: socket.id,
      language: data.language
    };

    let transcriptionServiceUsed = false;

    // 1. Send to 'store' if connected
    if (backendClients.store) {
      console.log(`Relaying audio to 'store' client...`);
      io.to(backendClients.store).emit('audio_to_python', payload);
    }

    // 2. Route to correct transcription worker
    if (payload.language === 'malay-english' || payload.language === 'malay-only') {
      if (backendClients.whisper) {
        console.log(`Relaying audio to 'whisper' client...`);
        io.to(backendClients.whisper).emit('audio_to_python', payload);
        transcriptionServiceUsed = true;
      }
    } else if (payload.language === 'english-only') {
      if (backendClients.wave2vec) {
        console.log(`Relaying audio to 'wave2vec' client...`);
        io.to(backendClients.wave2vec).emit('audio_to_python', payload);
        transcriptionServiceUsed = true;
      }
    }

    // 3. Handle errors if no worker is connected
    if (!transcriptionServiceUsed) {
        if (!backendClients.whisper && !backendClients.wave2vec) {
             console.error("❌ No Python transcription clients are connected.");
             socket.emit('transcription_error', { message: "Transcription service unavailable." });
        } else {
             console.error(`❌ Correct Python client for language '${payload.language}' is not connected.`);
             socket.emit('transcription_error', { message: `Service for '${payload.language}' is unavailable.` });
        }
    }
  });

  // --- Transcription Result Relaying ---
  socket.on('transcription_from_python', (data) => {
    if (!data || !data.browserSocketId || data.transcript === undefined) { 
        console.error(`Invalid transcription data from Python client.`);
        return;
    }

    console.log(`📝 Received transcription from Python for browser: ${data.browserSocketId}`);
    io.to(data.browserSocketId).emit('transcription_result', {
      transcript: data.transcript
    });
  });

  // --- Disconnect Handling ---
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    clientRateLimit.delete(socket.id);

    // If a Python worker disconnects, free up its group slot
    if (socket.backendGroup) { 
      console.log(`Backend client [${socket.backendGroup}] has disconnected.`);
      backendClients[socket.backendGroup] = null;
    }
  });

  socket.on('error', (error) => {
    console.error('Socket error:', error);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Node.js server running on port ${PORT}`);
});