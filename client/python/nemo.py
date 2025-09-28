import socketio
import numpy as np
import soundfile as sf
from datetime import datetime
import os
import time
import torch

# --- NVIDIA NeMo Imports ---
import nemo.collections.asr as nemo_asr
from nemo.core.config import ModelConfig

# --- Configuration ---
NODE_SERVER_URL = "http://localhost:3000"
UPLOAD_DIR = "audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Initialize NVIDIA NeMo ASR Model ---
print("Loading NVIDIA NeMo ASR model...")

# Choose one of the available models based on your needs:
# - 'stt_en_conformer_ctc_small'  (fastest, lower accuracy)
# - 'stt_en_conformer_ctc_medium' (balanced)
# - 'stt_en_conformer_ctc_large'  (slowest, highest accuracy)

try:
    # Load a pre-trained model
    model = nemo_asr.models.EncDecCTCModel.from_pretrained(
        model_name="stt_en_conformer_ctc_small"
    )
    
    # Move model to GPU if available
    if torch.cuda.is_available():
        model = model.cuda()
        print("✅ NVIDIA NeMo model loaded on GPU.")
    else:
        print("✅ NVIDIA NeMo model loaded on CPU.")
        
    print(f"Model sample rate: {model.cfg.sample_rate}")
    
except Exception as e:
    print(f"❌ Error loading NeMo model: {e}")
    print("Falling back to CPU mode...")
    model = nemo_asr.models.EncDecCTCModel.from_pretrained(
        model_name="stt_en_conformer_ctc_small"
    )

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

        print("Transcribing with NVIDIA NeMo...")
        
        # Save temporary audio file for NeMo processing
        temp_audio_path = os.path.join(UPLOAD_DIR, "temp_audio.wav")
        sf.write(temp_audio_path, audio_data, 16000)
        
        # Transcribe using NeMo
        transcription = transcribe_audio_nemo(temp_audio_path)
        print(f"📝 Transcription: {transcription}")

        # Save the audio and its transcription
        save_audio_and_transcription(audio_data, transcription)

        # Send the result back to the Node.js server
        sio.emit('transcription_from_python', {
            'transcript': transcription,
            'browserSocketId': browser_socket_id
        })
        
        # Clean up temporary file
        try:
            os.remove(temp_audio_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ An error occurred during transcription: {e}")
        import traceback
        traceback.print_exc()

def transcribe_audio_nemo(audio_path):
    """Transcribe audio using NVIDIA NeMo"""
    try:
        # Transcribe the audio file
        transcriptions = model.transcribe(
            paths2audio_files=[audio_path],
            batch_size=1
        )
        
        if transcriptions and len(transcriptions) > 0:
            return transcriptions[0].strip()
        else:
            return "No transcription generated"
            
    except Exception as e:
        print(f"Error in NeMo transcription: {e}")
        return f"Transcription error: {str(e)}"

def save_audio_and_transcription(audio_data, transcription):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Save audio file
        audio_filename = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        sf.write(audio_filename, audio_data, 16000)
        print(f"✅ Audio saved to {audio_filename}")
        
        # Save transcription file
        txt_filename = os.path.join(UPLOAD_DIR, f"transcription_{timestamp}.txt")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(transcription)
        print(f"✅ Transcription saved to {txt_filename}")

    except Exception as e:
        print(f"❌ Critical error: Failed to write audio/text to file: {e}")

# --- GPU Monitoring Function ---
def print_gpu_status():
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        allocated = torch.cuda.memory_allocated(0) / 1e9
        reserved = torch.cuda.memory_reserved(0) / 1e9
        print(f"GPU Memory: {allocated:.2f}/{gpu_memory:.2f} GB allocated, {reserved:.2f} GB reserved")

# --- Main Entry Point ---
if __name__ == '__main__':
    print("🚀 Starting NVIDIA NeMo ASR Server")
    print_gpu_status()
    
    while True:
        try:
            print(f"Attempting to connect to Node.js server at {NODE_SERVER_URL}...")
            sio.connect(NODE_SERVER_URL, transports=['websocket'])
            sio.wait()
        except socketio.exceptions.ConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nShutting down NVIDIA NeMo ASR Server...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)