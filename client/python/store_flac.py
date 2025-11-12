import socketio
import numpy as np
from pydub import AudioSegment
from datetime import datetime
import os
import time
import traceback

# --- Configuration ---
NODE_SERVER_URL = "http://localhost:3000"
UPLOAD_DIR = "audio_uploads_flac"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# This key MUST match the one in your server-latest.js
PYTHON_SECRET_KEY = "your-long-random-secret-key-here"

# --- Initialize Socket.IO Client ---
sio = socketio.Client()

# --- Socket.IO Event Handlers ---
@sio.event
def connect():
    print("✅ Successfully connected to Node.js server.")
    # Identify this client as part of the 'store' group
    sio.emit('identify_python', {
        'secret': PYTHON_SECRET_KEY,
        'group': 'store'
    })

@sio.event
def connect_error(data):
    print(f"❌ Connection to Node.js server failed: {data}")

@sio.event
def disconnect():
    print("Disconnected from Node.js server.")

@sio.on('audio_to_python')
def on_audio_to_python(data):
    """
    This function is triggered when the Node.js server forwards audio.
    It compresses the audio to FLAC and saves it.
    """
    browser_socket_id = data['browserSocketId']
    print(f"\n🎧 Received audio from browser client: {browser_socket_id} for storage...")
    
    try:
        # 1. Get the raw audio data (Float32)
        audio_float32 = np.array(data['audioFloat32'], dtype=np.float32)
        
        # 2. Convert from Float32 to Int16 PCM
        # pydub works with raw bytes, and 16-bit PCM is standard.
        audio_int16 = (audio_float32 * 32767).astype(np.int16)

        # 3. Create a pydub AudioSegment from the raw data
        # We must provide the exact parameters of the incoming audio.
        audio_segment = AudioSegment.from_raw(
            audio_int16.tobytes(),
            sample_width=2,         # 2 bytes = 16-bit
            frame_rate=16000,       # 16kHz from browser
            channels=1              # Mono from browser
        )
        
        # 4. Define filename and export to FLAC
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        flac_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}_{browser_socket_id[:5]}.flac")
        
        print(f"Compressing to FLAC: {flac_filename}...")
        
        # This one line does the lossless compression, as you described.
        audio_segment.export(flac_filename, format="flac")
        
        print(f"✅ Lossless FLAC file saved.")

        # --- Optional: Show compression results ---
        original_size_bytes = len(audio_int16.tobytes())
        compressed_size_bytes = os.path.getsize(flac_filename)
        
        if original_size_bytes > 0:
            print(f"--- Compression Stats ---")
            print(f"  Original PCM size:    {original_size_bytes / 1024:.2f} KB")
            print(f"  Compressed FLAC size: {compressed_size_bytes / 1024:.2f} KB")
            print(f"  Ratio (FLAC/PCM):     {(compressed_size_bytes / original_size_bytes) * 100:.2f}%")

    except Exception as e:
        print(f"❌ An error occurred during audio processing/saving: {e}")
        traceback.print_exc()

# --- Main Entry Point ---
if __name__ == '__main__':
    print("🚀 Starting FLAC Storage Client...")
    print(f"Will save compressed audio to: {UPLOAD_DIR}")
    print("NOTE: This script requires 'pydub' (pip install pydub) and 'ffmpeg'.")
    
    while True:
        try:
            print(f"Attempting to connect to Node.js server at {NODE_SERVER_URL}...")
            sio.connect(NODE_SERVER_URL, transports=['websocket'])
            sio.wait()
        except socketio.exceptions.ConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 Shutting down storage client...")
            break