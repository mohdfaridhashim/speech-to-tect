const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

let pythonClientId = null;

app.use(express.static(path.join(__dirname, 'public')));

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('identify_python', () => {
    pythonClientId = socket.id;
    console.log(`✅ Python client identified: ${pythonClientId}`);
  });

  socket.on('audio_data', (data) => {
    console.log(` Received audio from browser: ${socket.id}. Data length: ${data.audioFloat32.length}`);
    
    if (pythonClientId) {
      console.log(`Relaying audio to Python client...`);
      io.to(pythonClientId).emit('audio_to_python', {
        audioFloat32: data.audioFloat32,
        browserSocketId: socket.id
      });
    } else {
      console.error("❌ Python client is not connected. Cannot transcribe.");
      socket.emit('transcription_error', { message: "Transcription service unavailable." });
    }
  });

  socket.on('transcription_from_python', (data) => {
    console.log(`📝 Received transcription from Python for browser: ${data.browserSocketId}`);
    io.to(data.browserSocketId).emit('transcription_result', {
      transcript: data.transcript
    });
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
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
  console.log(`🚀 Open http://localhost:${PORT} in your browser`);
});