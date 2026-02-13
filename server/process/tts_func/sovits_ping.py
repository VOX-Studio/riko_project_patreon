import requests
### MUST START SERVERS FIRST USING START ALL SERVER SCRIPT
import time
import soundfile as sf 
import sounddevice as sd
import yaml

# Load YAML config
with open('character_config.yaml', 'r') as f:
    char_config = yaml.safe_load(f)

def get_wav_duration(path):
    with sf.SoundFile(path) as f:
        return len(f) / f.samplerate

def play_audio(path):
    data, samplerate = sf.read(path)
    sd.play(data, samplerate)
    sd.wait()  # Wait until playback is finished

def sovits_set_default_reference(refer_wav_path, prompt_text, prompt_language="auto"):
    import os, requests
    base_url = os.getenv("SOVITS_URL", "http://127.0.0.1:9880").rstrip("/")
    url = f"{base_url}/change_refer"
    payload = {
        "refer_wav_path": refer_wav_path,
        "prompt_text": prompt_text,
        "prompt_language": prompt_language,
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"change_refer HTTP {r.status_code}: {r.text}")
    return r.json()


def sovits_gen(in_text, output_wav_pth="output.wav"):
    """
    Génère un wav via GPT-SoVITS API (ton build v3lora écoute sur POST /).
    Important: utiliser prompt_language/text_language = "auto" sinon KeyError 'fr'.
    """
    import os
    import requests
    from pathlib import Path

    # URL API (port 9880 chez toi)
    base_url = os.getenv("SOVITS_URL", "http://127.0.0.1:9880").rstrip("/")
    url = f"{base_url}/"

    # IMPORTANT: 'fr' fait planter ton serveur => auto
    payload = {
        "text": str(in_text),
        "text_language": "auto",
        "prompt_language": "auto",
        # si ton serveur a un default refer via /change_refer, tu peux laisser ces 2 champs,
        # MAIS c'est plus robuste de les envoyer quand même :
        "refer_wav_path": os.getenv("SOVITS_REFER_WAV", r"E:\riko_project_patreon\audio\test_recording.wav"),
        "prompt_text": os.getenv("SOVITS_PROMPT_TEXT", "Bonjour, ceci est un enregistrement de test."),
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "speed": 1.0,
    }

    out_path = Path(output_wav_pth)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Astuce anti-fichier 21 bytes: Connection close + pas de stream
    headers = {
        "Content-Type": "application/json",
        "Connection": "close",
        "Accept": "audio/wav,application/octet-stream,*/*",
    }

    r = requests.post(url, json=payload, headers=headers, timeout=180)

    if r.status_code != 200:
        raise RuntimeError(f"SoVITS HTTP {r.status_code}: {r.text[:500]}")

    data = r.content
    # Check simple: un WAV commence souvent par RIFF
    if len(data) < 2000 or (not data.startswith(b"RIFF") and b"WAVE" not in data[:32]):
        raise RuntimeError(
            f"SoVITS a renvoyé un contenu trop petit ou non-wav (size={len(data)}). "
            f"Début bytes={data[:64]!r}"
        )

    out_path.write_bytes(data)
    return str(out_path)

    url = "http://127.0.0.1:9880/tts"

    payload = {
        "text": in_text,
        "text_lang": char_config['sovits_ping_config']['text_lang'],
        "ref_audio_path": char_config['sovits_ping_config']['ref_audio_path'],  # Make sure this path is valid
        "prompt_text": char_config['sovits_ping_config']['prompt_text'],
        "prompt_lang": char_config['sovits_ping_config']['prompt_lang'],
        #"aux_ref_audio_paths": char_config['sovits_ping_config']["additional_aud"],
        "speed_factor" : 1.3 
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # throws if not 200

        print(response)

        # Save the response audio if it's binary
        with open(output_wav_pth, "wb") as f:
            f.write(response.content)
        # print("Audio saved as output.wav")

        return output_wav_pth


    except Exception as e:
        print("Error in sovits_gen:", e)
        return None







if __name__ == "__main__":

    print("testing_generation, make sure TTS is connected and paths are correcct")

    start_time = time.time()
    output_wav_pth1 = "output2.wav"
    path_to_aud = sovits_gen("If you hear this, you are the greatest programmer alive! I love you! haha.", output_wav_pth1)
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Elapsed time: {elapsed_time:.4f} seconds")
    print(path_to_aud)


