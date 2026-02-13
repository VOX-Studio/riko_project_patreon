
import os
from groq import Groq
import yaml
import gradio as gr
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path



# 0. IMPORT ALL FILES!
import os 
import sounddevice as sd
import numpy as np
import soundfile as sf
import queue
import sys
from scipy.io.wavfile import read
from faster_whisper import WhisperModel


load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
client_groq = Groq(api_key = groq_api_key)


def record_on_speech(output_file="conversation.wav", samplerate=44100, channels=1, silence_threshold=0.01, silence_duration=1, device=None):
    """
    Records audio from the microphone, starting only when the user speaks and stopping after a period of silence.
    
    Args:
        output_file (str): Path to save the recorded audio.
        samplerate (int): Sampling rate in Hz. Default is 44100.
        channels (int): Number of audio channels. Default is 1 (mono).
        silence_threshold (float): RMS threshold to detect silence. Default is 0.01 (normalized amplitude).
        silence_duration (float): Duration in seconds of silence to stop recording. Default is 2.
        device (int or str): Input device ID or name. Default is None (use system default).
    
    Returns:
        None
    """

    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Existing file '{output_file}' was deleted.")
        
    q = queue.Queue()

    def callback(indata, frames, time, status):
        """Callback for audio input."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    def rms_level(data):
        """Calculate the RMS level of the audio."""
        return np.sqrt(np.mean(np.square(data)))

    try:
        # Open the sound file
        with sf.SoundFile(output_file, mode='x', samplerate=samplerate,
                          channels=channels, subtype='PCM_16') as file:
            with sd.InputStream(samplerate=samplerate, device=device,
                                channels=channels, callback=callback):
                print("Listening for speech...")
                silent_time = 0
                recording_started = False

                while True:
                    data = q.get()
                    rms = rms_level(data)

                    if not recording_started:
                        if rms > silence_threshold:
                            print("Voice detected, starting recording...")
                            recording_started = True

                    if recording_started:
                        file.write(data)

                        if rms < silence_threshold:
                            silent_time += len(data) / samplerate
                        else:
                            silent_time = 0

                        if silent_time >= silence_duration:
                            print("Silence detected, stopping recording...")
                            break

    except KeyboardInterrupt:
        print("\nRecording interrupted.")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)

    return output_file


def transcribe_audio_groq(aud_path = "conversation.wav"):
    with open(aud_path, "rb") as file:
        transcription = client_groq.audio.transcriptions.create(
        file=(aud_path, file.read()),
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
        prompt="The following is a conversation between Riko and Rayen", 
        )
        print(transcription.text)

        return transcription.text



if __name__ == "__main__": 
    print('Running module')

    conversation_recording = "~/riko_project_v1/conversation.wav"
    conversation_recording = Path("audio") / "conversation.wav"
    conversation_recording = str(conversation_recording)

    record_on_speech(
            output_file=conversation_recording,
            samplerate=44100,
            channels=1,
            silence_threshold=0.02,  # Adjust based on your microphone sensitivity
            silence_duration=1,     # Stop after 3 seconds of silence
            device=None             # Use default device, or specify by ID or name
        )
    
    user_spoken_text = transcribe_audio_groq(aud_path=conversation_recording)
    print(user_spoken_text)
    






      