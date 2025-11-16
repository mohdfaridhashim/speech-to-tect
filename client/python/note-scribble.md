python3 models/convert-h5-to-ggml.py \models/malaysian-whisper-medium-v2 \whisper \models


build/bin/debug/whisper-server.exe --model models/malaysia-whisper-tiny-model.bin --threads 8 --host 127.0.0.1 --port 8011


cmake -B build -DCMAKE_BUILD_TYPE=Release -DWHISPER_ACCELERATE=ON -DWHISPER_BUILD_EXAMPLES=ON

build/bin/release/whisper-server.exe --model models/malaysia-whisper-tiny-model.bin --threads 8 --host 127.0.0.1 --port 8011 -l ms


./build/bin/Release/whisper-cli \
  --model models/ggml-model.bin \
  -f samples/sample.wav \
  -l ms \
  -t 8



cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON


cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DCUDA_TOOLKIT_ROOT_DIR="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0\bin" -DCUDA_CUDA_LIBRARY="C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.0/lib/x64/cuda.lib"


cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DGGML_CCACHE=OFF



cmake -B build_gpu  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DCUDA_ARCHITECTURES="sm_75"


cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -arch=sm_86


cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DCMAKE_CUDA_ARCHITECTURES="compute_86"



cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DCMAKE_CUDA_ARCHITECTURES="86" -allow-unsupported-compiler

//work
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DWHISPER_BUILD_EXAMPLES=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_CUDA_FLAGS="-allow-unsupported-compiler"





models/download-ggml-model.sh base.en

models\download-ggml-model.cmd base.en



build/bin/release/whisper-server.exe --model models/ggml-tiny.bin --threads 8 --host 127.0.0.1 --port 8012 -l ms


# For CUDA 12.1 (Recommended Stable)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121