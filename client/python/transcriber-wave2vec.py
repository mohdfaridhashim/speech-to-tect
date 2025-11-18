import socketio
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time
import traceback
import torch
from transformers import pipeline, Wav2Vec2ForCTC, Wav2Vec2Processor
from dotenv import load_dotenv

# --- Configuration ---
NODE_SERVER_URL = os.getenv("NODE_SERVER_URL", "http://localhost:3000")
UPLOAD_DIR = "audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

load_dotenv() # Load from .env file
PYTHON_SECRET_KEY = os.getenv("PYTHON_SECRET_KEY")

MODEL_NAME = "facebook/wav2vec2-base-960h" 

# Add a check for the key
if not PYTHON_SECRET_KEY:
    raise ValueError("PYTHON_SECRET_KEY not found in .env file. Please create it.")

# --- Initialize Hugging Face Pipeline ---
print(f"Loading Hugging Face model '{MODEL_NAME}' on CUDA...")
# Wav2Vec benefits from float32 for stability, but we can try float16
# We also explicitly load the processor and model to ensure correct setup
processor = Wav2Vec2Processor.from_pretrained(MODEL_NAME)
model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME).to(torch.float16).to("cuda")

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
    # Identify this client to the 'wave2vec' group
    sio.emit('identify_python', {
        'apiKey': PYTHON_SECRET_KEY, # <-- FIX: Changed 'secret' to 'apiKey'
        'group': 'wave2vec' 
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
    
    print(f"\n🎤 Received audio from browser client: {browser_socket_id} for 'english-only'")
    
    try:
        audio_data = np.array(data['audioFloat32']).astype(np.float32)
        print(f"Transcribing ({MODEL_NAME})...")
        
        # --- Transcribe using Wav2Vec2 ---
        # 1. Process the audio (resample if needed, though it's 16k)
        input_values = processor(audio_data, sampling_rate=16000, return_tensors="pt").input_values
        input_values = input_values.to(torch.float16).to("cuda")

        # 2. Get model logits (predictions)
        with torch.no_grad():
            logits = model(input_values).logits

        # 3. Decode the logits to text
        predicted_ids = torch.argmax(logits, dim=-1)
        raw_transcription = processor.batch_decode(predicted_ids)[0]
        
        # Wav2Vec models output in ALL CAPS
        raw_transcription = raw_transcription.lower()
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