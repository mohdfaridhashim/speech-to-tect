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

// Variable to store the socket ID of our Python client
let pythonClientId = null;

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Handle all socket connections
io.on('connection', (socket) => {
  console.log('A client connected:', socket.id);

  // Event for the Python client to identify itself
  socket.on('identify_python', () => {
    pythonClientId = socket.id;
    console.log(`Python client identified with ID: ${pythonClientId}`);
  });

  // Handle audio data from the browser client
  socket.on('audio_data', (data) => {
    console.log('Received audio data from browser client:', socket.id);
    
    // Check if the Python client is connected
    if (pythonClientId) {
      // Forward the audio data and the browser's socket ID to the Python client
      io.to(pythonClientId).emit('audio_to_python', {
        audioFloat32: data.audioFloat32,
        browserSocketId: socket.id // We need this to send the result back to the correct browser
      });
    } else {
      console.error("Python client is not connected. Cannot transcribe.");
      // Optionally, send an error back to the browser
      socket.emit('transcription_error', { message: "Transcription service is currently unavailable." });
    }
  });

  // Listen for the final transcription from the Python client
  socket.on('transcription_from_python', (data) => {
    console.log(`Received transcription from Python for browser: ${data.browserSocketId}`);
    
    // Send the transcription result back to the original browser client
    io.to(data.browserSocketId).emit('transcription_result', {
      transcript: data.transcript
    });
  });

  // Handle client disconnection
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    // If the disconnected client was our Python script, nullify its ID
    if (socket.id === pythonClientId) {
      console.log('Python client has disconnected.');
      pythonClientId = null;
    }
  });

  // Handle errors
  socket.on('error', (error) => {
    console.error('Socket error:', error);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Node.js server running on port ${PORT}`);
  console.log(`Open http://localhost:${PORT} in your browser`);
});
