# How to Install & Build `whisper.cpp` on Windows 11

This guide covers two methods for compiling `whisper.cpp` on a Windows 11 machine:

1.  **Method 1 (Recommended): Build with GPU (CUDA) Support**
    * Uses your NVIDIA GPU (e.g., RTX 3060) for massive speed.
    * Requires Visual Studio and the NVIDIA CUDA Toolkit.

2.  **Method 2 (Simple): Build for CPU-Only**
    * Much simpler and doesn't require extra tools.
    * Will be significantly slower than the GPU method.

---

## Step 1: Get the `whisper.cpp` Code

This step is the same for both methods.

1.  **Install Git:** If you don't have it, [download and install Git for Windows](https://git-scm.com/downloads).

2.  **Open Terminal:** Open a **PowerShell** window.

3.  **Clone the Repository:** Navigate to your code folder and "clone" (download) the project.

    ```powershell
    # Navigate to your main code directory
    cd D:\code\speech-to-tect\client

    # Clone the project from GitHub
    git clone [https://github.com/ggerganov/whisper.cpp.git](https://github.com/ggerganov/whisper.cpp.git)

    # Enter the new folder
    cd whisper.cpp
    ```

---

## Method 1: Build with GPU Support (CUDA)

### Prerequisites for GPU Build

* **Visual Studio 2022:** [Download the Community version](https://visualstudio.microsoft.com/vs/community/).
    * During installation, you **must** select the workload: **"Desktop development with C++"**.
* **NVIDIA CUDA Toolkit:** [Download and install the latest version](https://developer.nvidia.com/cuda-toolkit).
    * The **"Express"** installation is recommended as it automatically sets up the system `PATH`.

### Build Steps (GPU)

1.  **Open PowerShell** and navigate to the `whisper.cpp` folder.

    ```powershell
    cd D:\code\speech-to-tect\client\whisper.cpp
    ```

2.  **Verify CUDA:** Check that the NVIDIA compiler (`nvcc`) is found.
    ```powershell
    nvcc --version
    ```
    *(If this fails, restart your PC after installing the CUDA Toolkit).*

3.  **Clean Old Builds (Optional):** If you have a failed build, remove it.
    ```powershell
    Remove-Item -Recurse -Force build
    ```

4.  **Run CMake:** This command configures the project to build with CUDA.
    ```powershell
    # -B build = Create a 'build' directory
    # -DGGML_CUDA=ON = The flag to enable NVIDIA GPU support
    cmake -B build -DGGML_CUDA=ON
    ```

5.  **Compile:** This command runs the actual compilation. It will take a few minutes.
    ```powershell
    cmake --build build --config Release
    ```

6.  **Done!** Your executable is at: `.\build\bin\Release\main.exe`

---

## Method 2: Build for CPU-Only

This is the simplest method and doesn't use Visual Studio or CUDA.

### Prerequisites for CPU Build

* **w64devkit:** [Download the latest `.zip` file from GitHub](https://github.com/skeeto/w64devkit/releases). This is a self-contained development terminal.

### Build Steps (CPU)

1.  **Unzip `w64devkit`** to a simple location, for example: `D:\w64devkit`.

2.  **Run `w64devkit.bat`**. A new black terminal window will open. This terminal understands the `make` command.

3.  **Inside the w64devkit terminal**, navigate to your `whisper.cpp` folder.
    ```bash
    # Change drive to D:
    D:
    
    # Navigate to your project
    cd \code\speech-to-tect\client\whisper.cpp
    ```

4.  **Run `make`:**
    ```bash
    make
    ```

5.  **Done!** The compiler will run and create your executable at: `.\main.exe`

---

## How to Run `whisper.cpp`

1.  **Download a Model:**
    * For Malay-English code-switching, download a fine-tuned GGUF model (e.g., from [Mesolitica on Hugging Face](https://huggingface.co/mesolitica)).
    * Place it in a `models` folder (e.g., `.\models\mesolitica-large-v3.gguf`).

2.  **Open Your Terminal** (PowerShell for GPU, w64devkit for CPU) and `cd` to the `whisper.cpp` directory.

### Example Run (GPU Version)

```powershell
# -m = model
# -f = audio file
# -l ms = language (Malay)
# -ngl 99 = Offload all layers to GPU (This is the most important part!)
.\build\bin\Release\main.exe -m .\models\mesolitica-large-v3.gguf -f .\samples\rakaman-saya.wav -l ms -ngl 99

### 📝 **Cheat Sheet: How to Run `whisper.cpp`**

#### 1\. Find Your `main.exe` File

Your executable (`main.exe`) is in one of two places, depending on how you just compiled it:

  * **If you used `make` (in w64devkit):**
    It's in the main folder:
    `D:\code\speech-to-tect\client\whisper.cpp\main.exe`

  * **If you used `cmake` (in PowerShell):**
    It's in the `build` folder:
    `D:\code\speech-to-tect\client\whisper.cpp\build\bin\Release\main.exe`

#### 2\. Open Your Terminal

  * **If you used `make`:** Use the **w64devkit terminal** you already have open.
  * **If you used `cmake`:** Use a regular **PowerShell** window.

Then, make sure you are in the main `whisper.cpp` folder:

```powershell
# In PowerShell or w64devkit terminal
cd D:\code\speech-to-tect\client\whisper.cpp
```

#### 3\. Run the Command 
https://huggingface.co/mesolitica/collections
Here are the commands to run. I'm assuming:

  * You have a Mesolitica model file in a folder named `models` (e.g., `.\models\mesolitica-large-v3.gguf`)
  * You have an audio file in a folder named `samples` (e.g., `.\samples\rakaman-saya.wav`)

-----

#### **Command Example (if you used `make`):**

```bash
# This command runs the .exe from the current folder
# -l ms sets the language to Malay (for code-switching)
# -t 8 uses 8 CPU threads (adjust this for your CPU)

.\main.exe -m .\models\mesolitica-large-v3.gguf -f .\samples\rakaman-saya.wav -l ms -t 8
```

#### **Command Example (if you used `cmake`):**

```powershell
# This command points to the .exe inside the 'build' folder
# All other flags are the same

.\build\bin\Release\main.exe -m .\models\mesolitica-large-v3.gguf -f .\samples\rakaman-saya.wav -l ms -t 8
```

-----

### ⭐ **Useful Extra Flags**

Add these to the end of your command:

  * **To create a subtitle file (`.srt`):**
    `  -osrt `
    *(e.g., `.\main.exe ... -l ms -t 8 -osrt`)*

  * **To save the transcript to a text file:**
    `  -otxt `

  * **To use more/fewer CPU threads:**
    `  -t 12 ` (use 12 threads)
    `  -t 6 ` (use 6 threads)

  * **To auto-detect the language (if not Malay):**
    `  -l auto `