import socketio
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time
import re
import json
from vosk import Model, KaldiRecognizer

# --- Configuration ---
NODE_SERVER_URL = "http://localhost:3000"
UPLOAD_DIR = "audio_uploads_vosk"
os.makedirs(UPLOAD_DIR, exist_ok=True)
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15" # Path to the Vosk model directory

# --- Malay Words Dictionary (can be expanded) ---
MALAY_WORDS = {
    'saya', 'awak', 'kamu', 'kami', 'kita', 'mereka', 'ini', 'itu', 'sini', 'situ',
    'sana', 'yang', 'dan', 'atau', 'tapi', 'tetapi', 'dengan', 'untuk', 'kepada',
    'dari', 'pada', 'di', 'ke', 'pergi', 'makan', 'minum', 'tidur', 'rumah',
    'kereta', 'terima', 'kasih', 'selamat', 'pagi', 'malam', 'petang', 'boleh', 'jom'
}

# --- Initialize Vosk Model ---
if not os.path.exists(VOSK_MODEL_PATH):
    print(f"❌ Vosk model not found at '{VOSK_MODEL_PATH}'")
    print("Please download a model from https://alphacephei.com/vosk/models and unpack it here.")
    exit()

print("Loading Vosk model...")
model = Model(VOSK_MODEL_PATH)
print("✅ Vosk model loaded.")

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
    text = text.strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:] if text else text
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
    
    try:
        # Convert Float32 to Int16 PCM, which Vosk prefers
        audio_float32 = np.array(data['audioFloat32'], dtype=np.float32)
        audio_int16 = (audio_float32 * 32767).astype(np.int16)
        
        recognizer = KaldiRecognizer(model, 16000)
        
        if recognizer.AcceptWaveform(audio_int16.tobytes()):
            result = json.loads(recognizer.Result())
            raw_transcription = result.get('text', '')
            
            if raw_transcription:
                print(f"📝 Raw transcription: {raw_transcription}")
                processed_transcription = enhance_transcription(raw_transcription, language_mode)
                print(f"🎨 Processed transcription: {processed_transcription}")

                save_audio_and_transcription(audio_float32, raw_transcription, processed_transcription)

                sio.emit('transcription_from_python', {
                    'transcript': processed_transcription,
                    'browserSocketId': browser_socket_id,
                    'raw_transcript': raw_transcription
                })
        else:
            partial_result = json.loads(recognizer.PartialResult())
            partial_text = partial_result.get('partial', '')
            if partial_text:
                print(f"Partial transcription: {partial_text}")


    except Exception as e:
        print(f"❌ An error occurred during transcription: {e}")
        sio.emit('transcription_error', {
            'browserSocketId': browser_socket_id,
            'error': str(e)
        })

def save_audio_and_transcription(audio_data, raw_transcription, processed_transcription):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        audio_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        sf.write(audio_filename, audio_data, 16000)
        
        txt_filename = os.path.join(UPLOAD_DIR, f"transcription_{timestamp}.txt")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"Raw: {raw_transcription}\n")
            f.write(f"Processed: {processed_transcription}\n")
        print(f"✅ Audio and transcription saved.")

    except Exception as e:
        print(f"❌ Failed to write audio/text to file: {e}")

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
