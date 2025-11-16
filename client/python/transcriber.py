import socketio
import whisper
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time
import re
from dotenv import load_dotenv # <-- ADD THIS

# --- Configuration ---
NODE_SERVER_URL = "http://localhost:3000"
UPLOAD_DIR = "audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Malay Words Dictionary ---
MALAY_WORDS = {
    'saya', 'awak', 'kamu', 'kami', 'kita', 'mereka', 'ini', 'itu', 'sini', 'situ', 
    'sana', 'yang', 'dan', 'atau', 'tapi', 'tetapi', 'dengan', 'untuk', 'kepada', 
    'dari', 'pada', 'di', 'ke', 'dari', 'oleh', 'sebagai', 'dalam', 'atas', 
    'bawah', 'depan', 'belakang', 'kiri', 'kanan', 'pergi', 'datang', 'makan', 
    'minum', 'tidur', 'bangun', 'baca', 'tulis', 'dengar', 'lihat', 'beli', 'jual',
    'kerja', 'main', 'jalan', 'lari', 'duduk', 'berdiri', 'besar', 'kecil', 'panjang',
    'pendek', 'tinggi', 'rendah', 'baik', 'buruk', 'cantik', 'hodoh', 'pandai', 
    'bodoh', 'kaya', 'miskin', 'baru', 'lama', 'cepat', 'lambat', 'mahal', 'murah',
    'suka', 'benci', 'sayang', 'marah', 'gembira', 'sedih', 'lapar', 'haus', 'penat',
    'sihat', 'sakit', 'ada', 'tiada', 'boleh', 'tidak', 'jangan', 'sudah', 'belum',
    'akan', 'telah', 'sedang', 'perlu', 'harus', 'mesti', 'boleh', 'tak', 'takde',
    'nak', 'kan', 'lah', 'pun', 'nya', 'kah', 'tah'
}

# --- Initialize Whisper Model ---
print("Loading Whisper model...")
model = whisper.load_model("base")
print("✅ Whisper model loaded.")

# --- Initialize Socket.IO Client ---
sio = socketio.Client()

# --- Language Processing Functions ---
def detect_language_word(word):
    """Detect if a word is Malay or English"""
    clean_word = re.sub(r'[^\w\s]', '', word.lower())
    return 'malay' if clean_word in MALAY_WORDS else 'english'

def process_mixed_language(text, language_mode='malay-english'):
    """Process text and add HTML tags for language highlighting"""
    if language_mode == 'english-only':
        return f"<span class='highlight-english'>{text}</span>"
    elif language_mode == 'malay-only':
        return f"<span class='highlight-malay'>{text}</span>"
    else:  # malay-english (mixed)
        words = text.split()
        processed_words = []
        
        for word in words:
            lang = detect_language_word(word)
            if lang == 'malay':
                processed_words.append(f"<span class='highlight-malay'>{word}</span>")
            else:
                processed_words.append(f"<span class='highlight-english'>{word}</span>")
        
        return ' '.join(processed_words)

def enhance_transcription(text, language_mode):
    """Clean and enhance the transcription"""
    # Clean the text
    text = text.strip()
    if not text:
        return "[No speech detected]"
    
    # Capitalize first letter
    text = text[0].upper() + text[1:] if text else text
    
    # Process based on language mode
    return process_mixed_language(text, language_mode)

# --- Socket.IO Event Handlers ---
@sio.event
def connect():
    print("✅ Successfully connected to Node.js server.")
    sio.emit('identify_python')

@sio.event
def connect_error(data):
    print(f"❌ Connection to Node.js server failed: {data}")

@sio.event
def disconnect():
    print("Disconnected from Node.js server.")

@sio.on('audio_to_python')
def on_audio_to_python(data):
    browser_socket_id = data['browserSocketId']
    language_mode = data.get('language', 'malay-english')
    
    print(f"\n🎤 Received audio from browser client: {browser_socket_id}")
    print(f"📋 Language mode: {language_mode}")
    
    try:
        audio_data = np.array(data['audioFloat32']).astype(np.float32)
        print(f"Audio data received, length: {len(audio_data)}")

        print("Transcribing...")
        result = model.transcribe(audio_data)
        raw_transcription = result.get('text', '').strip()
        print(f"📝 Raw transcription: {raw_transcription}")

        # Process the transcription with language detection
        processed_transcription = enhance_transcription(raw_transcription, language_mode)
        print(f"🎨 Processed transcription: {processed_transcription}")

        # Save the audio and its transcription
        save_audio_and_transcription(audio_data, raw_transcription, processed_transcription)

        # Send the processed result back to the Node.js server
        sio.emit('transcription_from_python', {
            'transcript': processed_transcription,
            'browserSocketId': browser_socket_id,
            'raw_transcript': raw_transcription
        })
        
    except Exception as e:
        print(f"❌ An error occurred during transcription: {e}")
        sio.emit('transcription_error', {
            'browserSocketId': browser_socket_id,
            'error': str(e)
        })

def save_audio_and_transcription(audio_data, raw_transcription, processed_transcription):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Save audio file
        audio_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        sf.write(audio_filename, audio_data, 16000)
        print(f"✅ Audio saved to {audio_filename}")
        
        # Save raw transcription file
        txt_filename = os.path.join(UPLOAD_DIR, f"transcription_{timestamp}.txt")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"Raw: {raw_transcription}\n")
            f.write(f"Processed: {processed_transcription}\n")
        print(f"✅ Transcription saved to {txt_filename}")

    except Exception as e:
        print(f"❌ Critical error: Failed to write audio/text to file: {e}")

# --- Main Entry Point ---
if __name__ == '__main__':
    while True:
        try:
            print(f"Attempting to connect to Node.js server at {NODE_SERVER_URL}...")
            sio.connect(NODE_SERVER_URL, transports=['websocket'])
            sio.wait()
        except socketio.exceptions.ConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            break