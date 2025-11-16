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

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Store language preferences for each client
const clientPreferences = new Map();

// Handle socket connections
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  // Initialize client preferences
  clientPreferences.set(socket.id, { language: 'malay-english' });
  
  // Handle audio data from client
  socket.on('audio_data', (data) => {
    console.log('Received audio data from client:', socket.id);
    
    // Process the text with language-specific logic
    let processedText = data.transcript;
    
    // Apply language-specific processing
    /*if (clientPreferences.get(socket.id).language === 'malay-english') {
      processedText = processMixedLanguage(data.transcript);
    } else if (clientPreferences.get(socket.id).language === 'malay-only') {
      processedText = processMalayLanguage(data.transcript);
    } else if (clientPreferences.get(socket.id).language === 'english-only') {
      processedText = processEnglishLanguage(data.transcript);
    }*/
    processedText = processEnglishLanguage(data.transcript);
    
    // Simulate processing delay
    setTimeout(() => {
      // Send the processed transcription back to the client
      socket.emit('transcription_result', {
        transcript: processedText,
        confidence: 0.85, // Simulated confidence score
        language: clientPreferences.get(socket.id).language
      });
    }, 500);
  });
  
  // Handle language preference changes
  socket.on('language_change', (data) => {
    console.log('Language preference changed for client:', socket.id, data.language);
    clientPreferences.set(socket.id, { language: data.language });
    
    // Confirm the language change
    socket.emit('language_update', {
      language: data.language,
      status: 'success'
    });
  });
  
  // Handle client disconnection
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    clientPreferences.delete(socket.id);
  });
  
  // Handle errors
  socket.on('error', (error) => {
    console.error('Socket error:', error);
  });
});

// Function to process mixed Malay-English language
function processMixedLanguage(text) {
  // Common Malay words and phrases with their English equivalents
  const malayDictionary = {
    'saya': 'I',
    'awak': 'you',
    'kamu': 'you',
    'dia': 'he/she',
    'mereka': 'they',
    'kita': 'we',
    'ini': 'this',
    'itu': 'that',
    'sini': 'here',
    'sana': 'there',
    'pergi': 'go',
    'makan': 'eat',
    'minum': 'drink',
    'tidur': 'sleep',
    'baca': 'read',
    'tulis': 'write',
    'rumah': 'house',
    'kereta': 'car',
    'makanan': 'food',
    'minuman': 'drink',
    'hari': 'day',
    'malam': 'night',
    'pagi': 'morning',
    'petang': 'evening',
    'terima kasih': 'thank you',
    'selamat pagi': 'good morning',
    'selamat malam': 'good night',
    'ya': 'yes',
    'tidak': 'no',
    'boleh': 'can',
    'jom': "let's"
  };

  // Add some context-aware processing for mixed language
  let processedText = text;
  
  // Replace common Malay phrases with their English equivalents for demonstration
  Object.keys(malayDictionary).forEach(malayWord => {
    const regex = new RegExp(`\\b${malayWord}\\b`, 'gi');
    processedText = processedText.replace(regex, `[${malayWord}/${malayDictionary[malayWord]}]`);
  });
  
  return processedText;
}

// Function to process Malay language only
function processMalayLanguage(text) {
  // Simulate Malay language processing
  return `[Malay Processed] ${text}`;
}

// Function to process English language only
function processEnglishLanguage(text) {
  // Simulate English language processing
  return `[English Processed] ${text}`;
}

// API endpoint for health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', message: 'Server is running' });
});

// API endpoint for manual transcription
app.post('/api/transcribe', express.json(), (req, res) => {
  const { text, language } = req.body;
  
  if (!text) {
    return res.status(400).json({ error: 'Text is required' });
  }
  
  let processedText;
  switch (language) {
    case 'malay-only':
      //processedText = processMalayLanguage(text);
	processedText = processEnglishLanguage(text);
      break;
    case 'english-only':
      processedText = processEnglishLanguage(text);
      break;
    case 'malay-english':
      //processedText = processMixedLanguage(text);
      processedText = processEnglishLanguage(text);
      break;
    default:
      //processedText = processMixedLanguage(text);
      processedText = processEnglishLanguage(text);
  }
  
  res.json({
    original: text,
    processed: processedText,
    language: language || 'malay-english'
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Open http://localhost:${PORT} in your browser`);
});
