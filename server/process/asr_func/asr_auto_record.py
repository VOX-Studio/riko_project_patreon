# 0. IMPORT ALL FILES!
import os 
import sounddevice as sd
import numpy as np
import soundfile as sf
import queue
import sys
from scipy.io.wavfile import read
from faster_whisper import WhisperModel
import yaml

with open('character_config.yaml', 'r') as f:
    char_config = yaml.safe_load(f)







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





def record_push_to_talk(model, output_file="conversation.wav", samplerate=44100):
    """
    Simple push-to-talk recorder: record -> save -> transcribe -> return text
    """
    
    # Remove existing file
    if os.path.exists(output_file):
        os.remove(output_file)
    
    print("Press ENTER to start recording...")
    input()
    
    print("🔴 Recording... Press ENTER to stop")
    
    # Record audio directly
    recording = sd.rec(int(60 * samplerate), samplerate=samplerate, channels=1, dtype='float64')
    input()  # Wait for stop
    sd.stop()
    
    print("⏹️  Saving audio...")
    
    # Write the file
    sf.write(output_file, recording, samplerate)
    
    return output_file


def transcribe_audio(model, aud_path = "conversation.wav"):
    segments, _ = model.transcribe(
        audio=aud_path ,
        task="transcribe",
        beam_size=5,
        best_of=5,
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        initial_prompt= char_config["asr_context"],
        word_timestamps=True,
        compression_ratio_threshold=None,
        no_repeat_ngram_size=0,
        max_new_tokens=100,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    trnsc = " ".join([segment.text for segment in segments])

    return trnsc


if __name__ == "__main__": 
    print('Running module')

    whisper_model = WhisperModel("base.en", device="cpu", compute_type="float32")
    #whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")
    print(' \n ========= WHISPER MODEL LOADED FROM FILES ================ \n')

    conversation_recording = "conversation.wav"

    record_on_speech(
            output_file=conversation_recording,
            samplerate=44100,
            channels=1,
            silence_threshold=0.005,            # Adjust based on your microphone sensitivity
            silence_duration=1,                 # Stop after 3 seconds of silence
            device=2                            # Use default device, or specify by ID or name
        )
    
    user_spoken_text = transcribe_audio(whisper_model, aud_path=conversation_recording)
    print(user_spoken_text)
    