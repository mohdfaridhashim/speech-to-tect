import socketio
import whisper
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time

# --- Configuration ---
NODE_SERVER_URL = "http://localhost:3000"
UPLOAD_DIR = "audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Initialize Whisper Model ---
print("Loading Whisper model...")
model = whisper.load_model("base")
print("✅ Whisper model loaded.")

# --- Initialize Socket.IO Client ---
sio = socketio.Client()

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
    print(f"\n🎤 Received audio from browser client: {browser_socket_id}")
    
    try:
        audio_data = np.array(data['audioFloat32']).astype(np.float32)
        print(f"Audio data received, length: {len(audio_data)}")

        print("Transcribing...")
        result = model.transcribe(audio_data)
        transcription = result.get('text', '').strip()
        print(f"📝 Transcription: {transcription}")

        # Save the audio and its transcription
        save_audio_and_transcription(audio_data, transcription)

        # Send the result back to the Node.js server
        sio.emit('transcription_from_python', {
            'transcript': transcription,
            'browserSocketId': browser_socket_id
        })
    except Exception as e:
        print(f"❌ An error occurred during transcription: {e}")

def save_audio_and_transcription(audio_data, transcription):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Save audio file
        audio_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        sf.write(audio_filename, audio_data, 16000) # Whisper operates on 16kHz
        print(f"✅ Audio saved to {audio_filename}")
        
        # Save transcription file
        txt_filename = os.path.join(UPLOAD_DIR, f"transcription_{timestamp}.txt")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(transcription)
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