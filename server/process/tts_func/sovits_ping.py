import requests
### MUST START SERVERS FIRST USING START ALL SERVER SCRIPT
import time
import soundfile as sf 
import sounddevice as sd
import yaml
from pathlib import Path


# Load YAML config
with open('character_config.yaml', 'r') as f:
    char_config = yaml.safe_load(f)

def load_char_config():
    root = Path(__file__).resolve().parents[3]  # .../server/process/tts_func -> remonte au repo
    cfg_path = root / "character_config.yaml"
    try:
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"[TTS] ERREUR YAML dans {cfg_path}: {e}")
        return {}


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
    import os
    import json
    import requests

    # --- Charger config YAML (tu l'as déjà dans ce fichier normalement) ---
    # char_config = yaml.safe_load(...)
    # cfg = char_config.get("sovits_ping_config", {})
    cfg = char_config.get("sovits_ping_config", {})  # si ton code existe déjà

    base_url = cfg.get("base_url", "http://127.0.0.1:9880").rstrip("/")
    refer_wav_path = cfg.get("refer_wav_path")  # ex: E:\riko_project_patreon\audio\test_recording.wav
    prompt_text = cfg.get("prompt_text", "Bonjour, ceci est un enregistrement de test.")
    prompt_language = cfg.get("prompt_language", "auto")
    text_language = cfg.get("text_language", "auto")

    payload = {
        "text": in_text,
        "text_language": text_language,
        "refer_wav_path": refer_wav_path,
        "prompt_text": prompt_text,
        "prompt_language": prompt_language,
        "top_k": int(cfg.get("top_k", 15)),
        "top_p": float(cfg.get("top_p", 1.0)),
        "temperature": float(cfg.get("temperature", 1.0)),
        "speed": float(cfg.get("speed", 1.0)),
    }

    # Sécurité: si pas de ref dans cfg, le serveur répond 400 "未指定参考音频且接口无预设"
    if not refer_wav_path or not os.path.exists(refer_wav_path):
        raise FileNotFoundError(f"refer_wav_path introuvable: {refer_wav_path}")

    # --- Appel API (POST /) ---
    url = f"{base_url}/"
    headers = {"Content-Type": "application/json"}

    r = requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=300)

    # Si erreur, on affiche le texte au lieu d'écrire un faux wav
    if r.status_code != 200:
        raise RuntimeError(f"SoVITS HTTP {r.status_code}: {r.text[:300]}")

    # Vérif contenu
    ctype = (r.headers.get("content-type") or "").lower()
    if "audio" not in ctype and "wav" not in ctype:
        # Souvent: erreur JSON renvoyée quand même en 200 selon certaines configs
        raw = r.content[:300]
        raise RuntimeError(f"Réponse non-audio (content-type={ctype}). Début={raw!r}")

    os.makedirs(os.path.dirname(output_wav_pth) or ".", exist_ok=True)
    with open(output_wav_pth, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 64):
            if chunk:
                f.write(chunk)

    return output_wav_pth