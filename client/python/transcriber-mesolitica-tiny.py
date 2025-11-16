import socketio
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time
import traceback
import torch
from transformers import pipeline
from dotenv import load_dotenv # <-- ADD THIS

# --- Configuration ---
NODE_SERVER_URL = os.getenv("NODE_SERVER_URL", "http://localhost:3000")
UPLOAD_DIR = "audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PYTHON_SECRET_KEY = os.getenv("PYTHON_SECRET_KEY") # From server-latest.js

# --- THE ONLY LINE TO CHANGE FOR EACH FILE ---
MODEL_NAME = "mesolitica/whisper-tiny-ms-en" 
# ---------------------------------------------

# Add a quick check to make sure the key loaded
if not PYTHON_SECRET_KEY:
    raise ValueError("PYTHON_SECRET_KEY not found in .env file. Please create it.")
    
# --- Initialize Hugging Face Pipeline ---
print(f"Loading Hugging Face model '{MODEL_NAME}' on CUDA...")
# Use device="cuda" and float16 for fast inference on your RTX 3060
pipe = pipeline(
    "automatic-speech-recognition",
    model=MODEL_NAME,
    device="cuda",
    torch_dtype=torch.float16
)
print(f"✅ Hugging Face model '{MODEL_NAME}' loaded on GPU.")

# --- Initialize Socket.IO Client ---
sio = socketio.Client()

# --- Simplified Transcription Cleanup ---
def enhance_transcription(text):
    """Clean up the raw transcription text for display"""
    text = text.strip()
    if not text:
        return "[No speech detected]"
    
    # Capitalize first letter
    text = text[0].upper() + text[1:] if text else text
    return text

# --- Socket.IO Event Handlers ---
@sio.event
def connect():
    print("✅ Successfully connected to Node.js server.")
    # We connect to the SAME 'whisper' group.
    # The node.js server will send 'malay-english' audio to this script.
    sio.emit('identify_python', {
        'secret': PYTHON_SECRET_KEY,
        'group': 'whisper' 
    })

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
        print(f"Transcribing ({MODEL_NAME})...")
        
        # --- Set transcription options for Hugging Face ---
        # We pass these to generate_kwargs
        generate_kwargs = {}
        if language_mode == 'english-only':
            generate_kwargs['language'] = 'en'
        elif language_mode == 'malay-only':
            generate_kwargs['language'] = 'ms'
        # For 'malay-english', we don't set a language hint

        # --- Transcribe using the Hugging Face pipeline ---
        # The pipeline handles the audio array directly
        result = pipe(audio_data, generate_kwargs=generate_kwargs)
        
        raw_transcription = result.get('text', '').strip()
        print(f"📝 Raw transcription: {raw_transcription}")

        processed_transcription = enhance_transcription(raw_transcription)

        save_audio_and_transcription(audio_data, raw_transcription)

        # Send the PLAIN TEXT result back
        sio.emit('transcription_from_python', {
            'transcript': processed_transcription,
            'browserSocketId': browser_socket_id,
            'raw_transcript': raw_transcription
        })
        
    except Exception as e:
        print(f"❌ An error occurred during transcription: {e}")
        traceback.print_exc()
        sio.emit('transcription_error', {
            'browserSocketId': browser_socket_id,
            'error': str(e)
        })

def save_audio_and_transcription(audio_data, raw_transcription):
    """Saves the audio and the raw transcription text."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        audio_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        sf.write(audio_filename, audio_data, 16000)
        
        txt_filename = os.path.join(UPLOAD_DIR, f"transcription_{timestamp}.txt")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"Raw: {raw_transcription}\n")
        print(f"✅ Audio/Transcription saved.")

    except Exception as e:
        print(f"❌ Error saving audio/text file: {e}")

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