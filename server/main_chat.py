from faster_whisper import WhisperModel
from process.asr_func.asr_auto_record import record_on_speech, transcribe_audio
from process.llm_funcs.llm_scr import llm_response, llm_response_with_memory
from process.tts_func.sovits_ping import sovits_gen, play_audio, get_wav_duration
from process.tts_func.tts_preprocess import clean_llm_output
from process.vrm_func.vrm_ping import vrm_talk, vrm_animate
from process.vrm_func.vrm_states_ping import set_vrm_state

from pathlib import Path
import os
import time
### transcribe audio 
import uuid
import soundfile as sf
import asyncio
import threading
import random
import os
import time
import uuid
import json
import shutil
import yaml
from pathlib import Path
from openai import OpenAI
from contextlib import suppress
from queue import Queue
from threading import Event, Thread
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
def get_wav_duration(path):
    with sf.SoundFile(path) as f:
        return len(f) / f.samplerate


#!/usr/bin/env python3
"""
Streaming LLM -> chunked TTS -> queued playback script for Riko.

What it does:
- Records user speech (uses your record_on_speech)
- Transcribes (transcribe_audio)
- Streams LLM text (OpenAI Responses streaming)
- For each chunk: generate TTS via sovits_gen, copy to public audio dir, enqueue for playback
- Playback loop calls vrm_talk and vrm_animate and waits for the audio's duration to avoid overlap
- At the end of the stream, the full assistant text is appended to the JSON history file

Fill in or import the helper functions you already have in your project:
- record_on_speech(output_file, samplerate, channels, silence_threshold, silence_duration, device)
- transcribe_audio(whisper_model, aud_path)
- clean_asr_output(text)
- sovits_gen(in_text, emotion, output_wav_pth) -> returns path to generated wav (must write to output_wav_pth)
- vrm_talk(public_audio_path, expression, llm_output, duration)
- vrm_animate(cmd, path)
- clean_llm_output(text)
- get_emotion(text, emotion_model, tokenizer)
- map_emotion_to_expression(emotion)
- get_wav_duration(path)

Make sure char_config.yaml contains history_file and model keys (see your example config).
"""

import os
import time
import uuid
import json
import shutil
import yaml
from pathlib import Path
from openai import OpenAI
from contextlib import suppress
from queue import Queue
from threading import Thread

# ---------------------------
# Load config + OpenAI client
# ---------------------------
CONFIG_PATH = os.path.expanduser('character_config.yaml')
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Config not found at {CONFIG_PATH}")

with open(CONFIG_PATH, 'r') as f:
    char_config = yaml.safe_load(f)

HISTORY_FILE = char_config['history_file']
MODEL = char_config.get('model', 'gpt-4.1-mini')
# MODEL = 'gpt-4.1'
CASE_SYSTEM_PROMPT = "You are a helpful assistant." # override for testing.

SYSTEM_PROMPT = [
    {
        "role": "system",
        "content": [
            {"type": "input_text", "text": char_config['presets']['default']['system_prompt']}
            #{"type": "input_text", "text": CASE_SYSTEM_PROMPT}
        ]
    }
]

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise EnvironmentError('Please set OPENAI_API_KEY in your environment')


OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# ---------------------------
# History utilities
# ---------------------------

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return SYSTEM_PROMPT.copy()


def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# ---------------------------
# Streaming helper
# ---------------------------

def to_chat_messages(history):
    out = []
    for m in history:
        role = m.get("role", "user")
        content = m.get("content", "")

        # Riko stocke souvent content sous forme de liste de blocs {"type": "...", "text": "..."}
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            ).strip()
        else:
            text = str(content).strip()

        if text:
            out.append({"role": role, "content": text})
    return out


def stream_text_chunks(messages, min_len=30, max_len=120):
    chat_messages = to_chat_messages(messages)
    buffer = ""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        temperature=1.0,
        top_p=1.0,
        stream=True,
        max_tokens=1024,
    )

    for part in stream:
        delta = part.choices[0].delta.content
        if not delta:
            continue

        buffer += delta

        # On coupe en morceaux pour TTS (ponctuation ou longueur)
        if buffer.endswith((".", "?", "!", "…")) and len(buffer) >= min_len:
            yield buffer.strip()
            buffer = ""
        elif len(buffer) >= max_len:
            yield buffer.strip()
            buffer = ""

    if buffer.strip():
        yield buffer.strip()

# ---------------------------
# Playback worker (single-threaded sequential playback)
# ---------------------------

class PlaybackWorker:
    def __init__(self):
        # queue items are tuples: (public_audio_path (Path), expression (str), assistant_text (str), duration (float))
        self.q = Queue()
        self.thread = Thread(target=self._run, daemon=True)
        self._running = False
        self.queue_finished_event = Event()  # NEW: Event to signal queue is empty
        self.queue_finished_event.set()  # Start as finished (no items)
        # flag to indicate whether the avatar is currently in the "talking" animation state
        self._talking = False

    def start(self):
        if not self._running:
            self._running = True
            self.thread.start()

    def enqueue(self, public_audio_path: Path, expression: str, assistant_text: str, duration: float):
        self.queue_finished_event.clear()  # NEW: Mark queue as not finished
        self.q.put((public_audio_path, expression, assistant_text, duration))

    def wait_until_finished(self, timeout=None):
        """
        Wait until the playback queue is completely empty and processed.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if queue finished, False if timeout occurred
        """
        return self.queue_finished_event.wait(timeout)
    
    def _run(self):
        while True:
            item = self.q.get()
            if item is None:
                break
            public_audio_path, expression, assistant_text, duration = item

            # Start the talking animation once when the first chunk of a sequence begins.
            # Subsequent chunks won't retrigger the animation (avoids jump/cut).
            try:
                if not self._talking:
                    thinking_anim = Path("animations/mixamo") / "Talking.fbx"
                    vrm_animate("start_mixamo", str(thinking_anim))
                    set_vrm_state("talking")
                    self._talking = True
            except Exception as e:
                print("vrm_animate (start talking) failed:", e)

            # Call vrm_talk for every chunk so the client receives the audio cue + metadata
            try:
                vrm_talk(str(public_audio_path), expression, assistant_text, int(duration))
            except Exception as e:
                print("vrm_talk failed:", e)

            # wait for the audio's duration so we don't overlap
            try:
                time.sleep(duration)
            except Exception:
                # defensive
                time.sleep(max(0.2, duration))

            # If the queue is empty after finishing this chunk, return to idle and clear talking flag.
            # This ensures a smooth transition back to idle at the end of the final chunk.
            try:
                if self.q.empty():
                    self.queue_finished_event.set()
                    idle_path = Path("animations/mixamo") / "Idle.fbx"
                    #vrm_animate("start_mixamo", str(idle_path))
                    self._talking = False
            except Exception as e:
                print("vrm_animate (idle) failed:", e)

    def stop(self):
        self.q.put(None)
        self.thread.join()

# ---------------------------
# Utilities
# ---------------------------

def ensure_dirs():
    Path('client/audio').mkdir(parents=True, exist_ok=True)
    Path('audio').mkdir(parents=True, exist_ok=True)


def copy_to_public(client_path: Path, public_path: Path):
    # Copy the client audio file to the public folder that vrm_talk expects
    shutil.copy2(client_path, public_path)

# Fallback duration reader (if you don't have one)

def fallback_get_wav_duration(p: Path):
    try:
        import wave, contextlib
        with contextlib.closing(wave.open(str(p),'r')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        return 3.0

# ---------------------------
# Main orchestration
# ---------------------------

def main_loop():
    ensure_dirs()

    playback = PlaybackWorker()
    playback.start()

    # Load any models or tokenizers you have for emotion detection here
    # whisper_model, emotion_model, tokenizer = load_your_models()

    from faster_whisper import WhisperModel

    gpu_mode = char_config.get("gpu_acceleration", "cpu")  # dans ton character_config.yaml :contentReference[oaicite:5]{index=5}
    if gpu_mode.lower() == "cuda":
        whisper_model = WhisperModel("small", device="cuda", compute_type="float16")
    else:
        whisper_model = WhisperModel("small", device="cpu", compute_type="int8")


    while True:

        try:

            print("\n⏳ Waiting for playback queue to finish...")
            playback.wait_until_finished()
            print("✅ Queue finished, ready for input")
            # 1) Idle animation + state 
            # try:
            idle_anim = Path("animations/mixamo") / "Idle.fbx"
            vrm_animate("start_mixamo", str(idle_anim))
            set_vrm_state("idle")
            # except Exception:
            #     pass
            
            # cont = input(">>> ENTER TO CONTINUE") # UNCOMMENT IF YOU WANT PUSH TO TALK

            conversation_recording = Path("audio") / "conversation.wav"
            conversation_recording.parent.mkdir(parents=True, exist_ok=True)
            conversation_recording = str(conversation_recording)
            record_on_speech(
                output_file=conversation_recording,
                samplerate=44100,
                channels=1,
                silence_threshold=0.02,  # Adjust based on your microphone sensitivity
                silence_duration=2,     # Stop after 3 seconds of silence
                device=None             # Use default device, or specify by ID or name
            )
            # record while listening sorry I don't think this works I'll have to work on it later. 
            # set_vrm_state("listening")


            # 3) Thinking animation
            try:
                thinking_anim = Path("animations/mixamo") / "Thinking.fbx"
                vrm_animate("start_mixamo", str(thinking_anim))
                set_vrm_state("thinking")
            except Exception:
                pass

            # 4) Transcribe
            user_spoken_text = transcribe_audio(whisper_model, aud_path=conversation_recording)

            # 5) Build messages history
            messages = load_history()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_spoken_text}
                ]
            })

            # 6) Stream model and generate TTS per chunk
            print("[llm] streaming response...")
            # thinking_anim = Path("animations/mixamo") / "Talking.fbx"
            # vrm_animate("start_mixamo", str(thinking_anim))
            # set_vrm_state("talking")
            full_assistant_text = ""

            for chunk in stream_text_chunks(messages):
                print("[chunk]", chunk)

                # accumulate final text
                full_assistant_text += (chunk + " ")

                # prepare TTS text and emotion
                tts_read_text = clean_llm_output(chunk)
                # emotion = get_emotion(chunk, None, None)  # plug your emotion model/tokenizer
                # expression = map_emotion_to_expression(emotion)
                # temp implementation
                emotion = "relaxed"   # or "smug" etc.
                expression = "relaxed" 

                # create unique filename for this chunk
                uid = uuid.uuid4().hex
                filename = f"output_{uid}.wav"
                client_out = Path('client') / 'audio' / filename
                public_out = Path('audio') / filename
                client_out.parent.mkdir(parents=True, exist_ok=True)

                # generate TTS (blocking). Expected to write client_out
                try:
                    sovits_gen(tts_read_text, output_wav_pth=str(client_out))
                except TypeError:
                    # fallback if your function signature is sovits_gen(text, emotion, output_path)
                    sovits_gen(tts_read_text, str(client_out))

                # copy to public path expected by VRM bridge
                copy_to_public(client_out, public_out)

                # determine duration
                try:
                    duration = get_wav_duration(public_out)
                except Exception:
                    duration = fallback_get_wav_duration(public_out)

                # enqueue for sequential playback
                playback.enqueue(public_out, expression, chunk, duration)

            # 7) After streaming ends, append the full assistant message to history and save
            final_text = full_assistant_text.strip()
            print("[llm final]", final_text)

            # append assistant to messages and save history
            messages.append({
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": final_text}
                ]
            })
            save_history(messages)

            # Optionally wait a short moment for queued audio to finish playing before next loop
            # NOTE: playback worker will ensure queued audio plays sequentially; here we don't block.
            time.sleep(0.1)

        except KeyboardInterrupt:
            print("Interrupted by user, stopping.")
            playback.stop()
            break
        except Exception as e:
            print("Error in main loop:", e)
            time.sleep(1)


if __name__ == '__main__':
    main_loop()

