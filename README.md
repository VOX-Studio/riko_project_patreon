# Project Riko

#### **Patreon Version:** *Windows version 1.1 — 2025-11-06*

Project Riko is an anime-focused LLM project by **Just Rayen**. She listens, remembers, and speaks like your favorite snarky anime companion.
It combines **OpenAI GPT**, **GPT-SoVITS** voice synthesis, and **Faster-Whisper / Groq ASR** into a fully configurable conversational pipeline with real-time streaming responses.

**Tested with Python 3.10 (Windows 10 or higher)**

---

## ✨ Features

* 💬 **LLM-based dialogue** using OpenAI-compatible streaming (real-time responses)
* 🧠 **Persistent conversation memory** with context tracking
* 🔊 **Voice generation** powered by GPT-SoVITS
* 🎧 **Speech recognition** using Faster-Whisper or Groq ASR (free API)
* 🧍‍♀️ **VRM animated avatar** powered by Three-VRM
* ⚙️ **Simple YAML personality config** for easy customization
* 🚀 **Convenient launch script** (`start_servers.bat`) for quick setup

---

## 🆕 2025-11-06 Update (Windows Version)

**New:**

* 🧩 Added OpenAI-compatible streaming for smoother, real-time conversation
* 🎙️ Integrated **Groq API** for faster and more accurate ASR transcription (free!)
* 🐞 Fixed bug where audio would not play in the client after server launch
* ⚡ Added `start_servers.bat` for easy one-click startup

---

## ⚙️ Configuration

All prompts and parameters are stored in `config.yaml`.
You can define personalities by editing this file.

```yaml
waifu_name: riko
gpu_acceleration: cpu 
history_file: chat_history.json
model: "gpt-4.1-mini"
presets:
  default:
    system_prompt: |
      You are a helpful assistant named Riko.
      You speak like a snarky anime girl.
      Always refer to the user as "senpai."

asr_context: The following is a conversation between Rayen and Riko
sovits_ping_config:
  text_lang: en
  prompt_lang: en
  ref_audio_path: D:\PyProjects\waifu_project\riko_project_patreon\character_files\main_sample.wav
  prompt_text: This is a sample voice for you to get started with. It sounds kind of cute, but make sure there aren’t long silences.

# THE FOLLOWING IS FOR SOVITS V2, V2PRO, V2PROPLUS
# additional_aud:
#   - additional_audio1
#   - additional_audio2
```

---

## 🛠️ Setup

For setup, see SETUP_GUIDE.md!

### 💡 Conversation Flow

1. Riko listens to your voice via microphone
2. Transcribes it using Groq ASR (or Faster-Whisper)
3. Sends it to GPT (with conversation memory)
4. Generates a reply in real time (streaming)
5. Synthesizes Riko’s voice using GPT-SoVITS
6. Plays back the audio
7. Animates the VRM avatar

---

## 📌 TODO / Future Improvements

* [x] Live microphone input
* [x] VRM model frontend
* [ ] Emotion/tone control in TTS
* [ ] GUI / full web interface
* [ ] Multi-language support

---

## 🧑‍🎤 Credits

* **Voice synthesis:** [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
* **ASR:** [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) & [Groq API](https://console.groq.com/)
* **LLM:** [OpenAI GPT](https://platform.openai.com)
* **Avatar animation:** [Three-VRM](https://github.com/pixiv/three-vrm)

---

## ⚠️ License Notice

This version is for **personal use only.**
Do **not redistribute, sell, or share** the code — it’s under a **custom early access license.**
A public open-source release will come later.

---

Enjoy~
— **Rayen 💻✨**
