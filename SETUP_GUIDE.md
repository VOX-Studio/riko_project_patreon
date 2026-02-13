# Setup Guide

## Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.10** - [Download from Microsoft Store](https://apps.microsoft.com/store/detail/python-310/9PJPW5LDXLZ5) or [python.org](https://www.python.org/downloads/)
- **VS Code** - [Download here](https://code.visualstudio.com/)
- **Node.js and npm** - [Download here](https://nodejs.org/) (includes npx)
- **GPT-SoVITS** - [One-click installer](https://github.com/RVC-Boss/GPT-SoVITS)

---

## 1. Project Setup

### Create Virtual Environment

1. Open VS Code
2. **File → New Window**
3. **File → Open Folder** (select your project directory)
4. Press **Ctrl+Shift+P** to open the command palette
5. Type `Python: Create Environment` and select it

   > **Note:** If you don't see this option, install the Python extension:
   > - Go to the Extensions sidebar (Ctrl+Shift+X)
   > - Search for "Python" and install it
   > - Close and reopen VS Code, then try again

6. Select **Venv** and choose **Python 3.10**
7. **Uncheck** "Install dependencies from requirements.txt" (we'll do this manually)
8. Click **OK**

### Install Dependencies

1. Open a new terminal: **Terminal → New Terminal**
2. Verify your virtual environment is active (you should see `.venv` in the prompt):
   ```
   (.venv) F:\your_project_path>
   ```

3. Install dependencies using uv (faster) or pip:
   ```bash
   # Option 1: Using uv (recommended - faster)
   pip install uv
   uv pip install -r requirements.txt
   
   # Option 2: Using pip
   pip install -r requirements.txt
   ```
   This should take 30 seconds to 1 minute depending on your system.

---

## 2. API Configuration

### Create .env File

Create a `.env` file in the root directory with the following content:

```text
OPENAI_API_KEY="sk-proj-YOUR_API_KEY"
GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

### Get API Keys

1. **OpenAI API Key:**
   - Sign up at [OpenAI Platform](https://platform.openai.com/api-keys)
   - Add $5 credit (should last 1-2 months for typical usage)
   - Copy your API key to the `.env` file
   
   > **Note:** You can customize this to use a local AI model if preferred (streaming code doesn't support this yet, but local model support is planned)

2. **Groq API Key (Free):**
   - Sign up at [Groq Console](https://console.groq.com/keys)
   - Copy your API key to the `.env` file

---

## 3. Configuration

### Character Configuration

There are two main configuration files:

#### A. `character_config.yaml`
- Set the AI prompt
- Configure ASR (Automatic Speech Recognition) context
- Add reference audio sample (must be 3-10 seconds long)
- Enter the text spoken in the audio file

#### B. `client/config.js`
- Change the 3D model
- Adjust mouth audio threshold
- Place model files in `client/models/` directory
- Update the filename in config
- **Important:** Model must be in VRM 1.0 format (export setting in VRoid Studio)

---

## 4. Starting the Servers

### Option A: Automatic Start (Recommended)

1. Edit `start_server.bat`
2. Change the following line to match your GPT-SoVITS installation path:
   ```batch
   set SOVITS_PATH=D:\PyProjects\GPT-SoVITS-v3lora-20250228\GPT-SoVITS-v3lora-20250228
   ```
3. Run the script:
   - In terminal: `start_server.bat`
   - Or double-click the file in File Explorer
4. **Do not close any of the terminal windows that open**

### Option B: Manual Start

If automatic start doesn't work:

1. **Start the Python server:**
   ```bash
   cd server
   python server.py
   ```

2. **Start the animation server** (open a second terminal):
   ```bash
   cd client
   npx vite
   ```

3. Open your browser and go to: [http://localhost:5173](http://localhost:5173)
   
   You should see a 3D model floating on screen.

---

## 5. Running the Chat

1. Run the main chat script:
   ```bash
   python main_chat.py
   ```

2. **Troubleshooting:** If you encounter issues, run the setup check script:
   ```bash
   cd server
   python check_setup.py
   ```

---

## 6. Customization

### Facial Expressions

Currently, the model's face defaults to "smug". You can change this or implement your own emotion classification.

**To change the expression**, edit `main_chat.py`:

```python
for chunk in stream_text_chunks(messages):
    print("[chunk]", chunk)
    
    # Accumulate final text
    full_assistant_text += (chunk + " ")
    
    # Prepare TTS text and emotion
    tts_read_text = clean_llm_output(chunk)
    
    # Option 1: Use emotion detection (plug in your own model)
    # emotion = get_emotion(chunk, None, None)
    # expression = map_emotion_to_expression(emotion)
    
    # Option 2: Set manually (current implementation)
    emotion = "relaxed"   
    expression = "relaxed"
```

**Supported VRM 1.0 expressions:**
- `happy`
- `angry`
- `sad`
- `relaxed`
- `surprised`
- `neutral`

---

## Summary

1. ✅ Install prerequisites (Python 3.10, VS Code, Node.js, GPT-SoVITS)
2. ✅ Create virtual environment and install dependencies
3. ✅ Configure API keys in `.env`
4. ✅ Customize `character_config.yaml` and `client/config.js`
5. ✅ Start servers (automatic or manual)
6. ✅ Run `main_chat.py`
7. ✅ (Optional) Customize facial expressions

For issues, run `server/check_setup.py` to diagnose problems.