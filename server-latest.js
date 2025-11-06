const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');

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
    // [FIX] Restrict the origin to your PHP app's URL.
    origin: ALLOWED_ORIGINS_ARRAY,
    methods: ["GET", "POST"]
  }
});

let pythonClientId = null;

// [FIX] Create a map to rate-limit clients.
const clientRateLimit = new Map();

app.use(express.static(path.join(__dirname, 'public')));

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Set a 1-second cooldown for this client
  clientRateLimit.set(socket.id, 0);

  socket.on('identify_python', (data) => {
    // [FIX] Authenticate the Python client with the secret key.
    if (data && data.secret === PYTHON_SECRET_KEY) {
      pythonClientId = socket.id;
      console.log(`✅ Python client identified and authenticated: ${pythonClientId}`);
    } else {
      // Log and disconnect the unauthorized client.
      console.error(`❌ FAILED auth attempt from client: ${socket.id}`);
      socket.disconnect();
    }
  });

  socket.on('audio_data', (data) => {
    
    // [FIX] Add Rate Limiting.
    const now = Date.now();
    const lastRequestTime = clientRateLimit.get(socket.id) || 0;
    
    // Set a 1-second (1000ms) cooldown between requests per user.
    if (now - lastRequestTime < 1000) {
      console.warn(`Rate limit hit for client: ${socket.id}`);
      // (Optional) Tell the client they are too fast.
      // socket.emit('transcription_error', { message: "You are sending audio too quickly." });
      return; 
    }
    clientRateLimit.set(socket.id, now);

    // [FIX] Add Data Validation.
    if (!data || !Array.isArray(data.audioFloat32) || !data.language) {
      console.error(`Invalid data from browser: ${socket.id}`);
      socket.emit('transcription_error', { message: "Invalid data format." });
      return;
    }

    // Check if Python backend is connected.
    if (pythonClientId) {
      console.log(`Relaying audio to Python client...`);
      io.to(pythonClientId).emit('audio_to_python', {
        audioFloat32: data.audioFloat32,
        browserSocketId: socket.id,
        language: data.language
      });
    } else {
      console.error("❌ Python client is not connected. Cannot transcribe.");
      socket.emit('transcription_error', { message: "Transcription service unavailable." });
    }
  });

  socket.on('transcription_from_python', (data) => {
    
    // [FIX] Validate data from Python before relaying.
    if (!data || !data.browserSocketId || !data.transcript) {
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
    
    // [FIX] Clean up rate-limit map.
    clientRateLimit.delete(socket.id);

    if (socket.id === pythonClientId) {
      console.log('Python client has disconnected.');
      pythonClientId = null;
    }
  });

  socket.on('error', (error) => {
    console.error('Socket error:', error);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Node.js server running on port ${PORT}`);
  console.log(`🚀 Open ${ALLOWED_ORIGIN} in your browser`);
});