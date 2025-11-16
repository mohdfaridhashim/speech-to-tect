const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');
const { config } = require('dotenv'); // Use dotenv for secrets

// Load .env variables
config();

// Read the comma-separated list from your .env file
const ALLOWED_ORIGINS_STRING = process.env.ALLOWED_ORIGINS || "http://localhost:8010";
const ALLOWED_ORIGINS_ARRAY = ALLOWED_ORIGINS_STRING.split(',');

// This key MUST match the one in your python/.env file
const PYTHON_SECRET_KEY = process.env.PYTHON_SECRET_KEY || "your-long-random-secret-key-here"; 

// [FIX] Read the comma-separated list from your .env file
const ALLOWED_ORIGINS_STRING = process.env.ALLOWED_ORIGINS || "http://localhost:8010";

// This is the line that "puts it into an array"
const ALLOWED_ORIGINS_ARRAY = ALLOWED_ORIGINS_STRING.split(',');

// [FIX] Add a secret key to authenticate your Python client.
// This prevents unauthorized clients from connecting as your backend.
// *** YOU MUST ADD THIS SAME KEY TO YOUR transcriber.py SCRIPT ***
const PYTHON_SECRET_KEY = "your-long-random-secret-key-here"; 

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: ALLOWED_ORIGINS_ARRAY,
    methods: ["GET", "POST"]
  }
});

// Store backend clients by group
let backendClients = {
  whisper: null,
  wave2vec: null,
  store: null
};

// Create a map to rate-limit clients.
const clientRateLimit = new Map();

// [FIX] Create a map to rate-limit clients.
const clientRateLimit = new Map();

app.use(express.static(path.join(__dirname, 'public')));

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Set a 1-second cooldown for this client
  clientRateLimit.set(socket.id, 0);

  // Handle identification for different backend groups
  socket.on('identify_python', (data) => {
    // Authenticate the Python client with the secret key AND group
    if (data && data.secret === PYTHON_SECRET_KEY && data.group) {
      
      // Check if the group name is one we expect
      if (backendClients.hasOwnProperty(data.group)) {
        
        // Assign this client to its group
        backendClients[data.group] = socket.id;
        
        // Tag the socket with its group for easy disconnect cleanup
        socket.backendGroup = data.group; 
        
        console.log(`✅ Python client identified for group [${data.group}]: ${socket.id}`);
        
      } else {
        console.error(`❌ Invalid group name from client ${socket.id}: ${data.group}. Must be 'whisper', 'wave2vec', or 'store'.`);
        socket.disconnect();
      }
    } else {
      // Log and disconnect the unauthorized client.
      console.error(`❌ FAILED auth attempt from client: ${socket.id}`);
      socket.disconnect();
    }
  });

  socket.on('audio_data', (data) => {
    
    // Add Rate Limiting.
    const now = Date.now();
    const lastRequestTime = clientRateLimit.get(socket.id) || 0;
    
    if (now - lastRequestTime < 1000) {
      console.warn(`Rate limit hit for client: ${socket.id}`);
      return; 
    }
    clientRateLimit.set(socket.id, now);

    // Add Data Validation.
    if (!data || !Array.isArray(data.audioFloat32) || !data.language) {
      console.error(`Invalid data from browser: ${socket.id}`);
      socket.emit('transcription_error', { message: "Invalid data format." });
      return;
    }

    // Define the audio payload
    const payload = {
      audioFloat32: data.audioFloat32,
      browserSocketId: socket.id,
      language: data.language
    };

    let transcriptionServiceUsed = false;

    // 1. Always send to the 'store' group if it's connected
    if (backendClients.store) {
      console.log(`Relaying audio to 'store' client...`);
      io.to(backendClients.store).emit('audio_to_python', payload);
    }

    // 2. Send to the correct transcription group based on language
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

    // 3. Handle error if no appropriate transcription service is connected
    if (!transcriptionServiceUsed) {
        if (!backendClients.whisper && !backendClients.wave2vec) {
             console.error("❌ No Python transcription clients are connected.");
             socket.emit('transcription_error', { message: "Transcription service unavailable." });
        } else {
             // One is connected, but not the right one
             console.error(`❌ Correct Python client for language '${payload.language}' is not connected.`);
             socket.emit('transcription_error', { message: `Service for '${payload.language}' is unavailable.` });
        }
    }
  });

  socket.on('transcription_from_python', (data) => {
    
    // Validate data from Python before relaying.
    if (!data || !data.browserSocketId || data.transcript === undefined) { 
        console.error(`Invalid transcription data from Python client.`);
        return;
    }

    console.log(`📝 Received transcription from Python for browser: ${data.browserSocketId}`);
    // Only send to the specific browser client
    io.to(data.browserSocketId).emit('transcription_result', {
      transcript: data.transcript
    });
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    
    // Clean up rate-limit map.
    clientRateLimit.delete(socket.id);

    // Clean up backend client map if a backend client disconnects
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