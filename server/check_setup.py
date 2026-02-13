#!/usr/bin/env python3
"""
System Test Script for VRM Avatar Chat System
Tests each component in sequence with user-friendly feedback and troubleshooting tips.
"""

import os
from xmlrpc import client
from networkx import config
from openai import OpenAI, api_key, base_url
import sys
import time
import json
import yaml
import uuid
import requests
from pathlib import Path
from dotenv import load_dotenv
import sounddevice as sd
import numpy as np


# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def wait_for_user(prompt="Press ENTER to continue..."):
    input(f"\n{Colors.BOLD}{prompt}{Colors.ENDC}")

# Base URL for VRM server
BASE_URL = "http://localhost:8001"

# ============================================================================
# TEST 0: Configuration and API Keys
# ============================================================================

def test_config_and_keys():
    print_header("TEST 0: Configuration and API Keys")
    
    issues = []
    
    # Check .env file
    print_info("Checking .env file...")
    project_root = Path(__file__).resolve().parents[1]   # .../riko_project_patreon
    load_dotenv(dotenv_path=project_root / ".env")


    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
    OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "sk-local-dummy")

    print("BASE_URL =", OPENAI_BASE_URL)
    print("API_KEY  =", OPENAI_API_KEY)
    
    if not os.path.exists('.env'):
        print_warning(".env file not found in current directory")
        issues.append(".env file missing")
    else:
        print_success(".env file found")
    
    # Check OpenAI API Key
    print_info("Checking OpenAI API Key...")
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print_error("OPENAI_API_KEY not set in environment")
        issues.append("OPENAI_API_KEY not set")
    elif openai_key.startswith('sk-'):
        print_success(f"OpenAI API Key found (starts with: {openai_key[:10]}...)")
    else:
        print_warning("OpenAI API Key found but doesn't start with 'sk-' (might be invalid)")
        issues.append("OPENAI_API_KEY format looks incorrect")
    
    # Check Groq API Key
    print_info("Checking Groq API Key...")
    groq_key = os.getenv('GROQ_API_KEY')
    is_local_llm = "127.0.0.1" in OPENAI_BASE_URL or "localhost" in OPENAI_BASE_URL

    if not groq_key:
        if is_local_llm:
            print_warning("GROQ_API_KEY non défini (OK si tu utilises le LLM local GGUF)")
        else:
            print_error("GROQ_API_KEY not set in environment")
            issues.append("GROQ_API_KEY not set")
    else:
        print_success(f"Groq API Key found (starts with: {groq_key[:10]}...)")
    
    # Check character_config.yaml
    print_info("Checking character_config.yaml...")
    config_path = 'character_config.yaml'
    if not os.path.exists(config_path):
        print_error(f"{config_path} not found")
        issues.append("character_config.yaml missing")
    else:
        print_success(f"{config_path} found")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check required fields
            required_fields = ['history_file', 'presets']
            for field in required_fields:
                if field in config:
                    print_success(f"  - {field}: present")
                else:
                    print_error(f"  - {field}: missing")
                    issues.append(f"character_config.yaml missing '{field}'")
            
            # Check if model is set
            model = config.get('model', 'not set')
            print_info(f"  - Model: {model}")
            
        except Exception as e:
            print_error(f"Error reading config: {e}")
            issues.append(f"character_config.yaml parse error: {e}")
    
    # Summary
    print("\n" + "─"*60)
    if issues:
        print_error("Configuration Issues Found:")
        for issue in issues:
            print(f"  • {issue}")
        print("\n" + Colors.WARNING + "Troubleshooting Tips:" + Colors.ENDC)
        if "OPENAI_API_KEY not set" in str(issues):
            print("  1. Create a .env file in your project root")
            print("  2. Add: OPENAI_API_KEY=sk-your-key-here")
            print("  3. Get your key from: https://platform.openai.com/api-keys")
        if "GROQ_API_KEY not set" in str(issues):
            print("  1. Add to .env file: GROQ_API_KEY=your-groq-key-here")
            print("  2. Get your key from: https://console.groq.com/keys")
        if "character_config.yaml" in str(issues):
            print("  1. Ensure character_config.yaml exists in project root")
            print("  2. Check the file has correct YAML syntax")
        return False
    else:
        print_success("All configuration checks passed!")
        return True

# ============================================================================
# TEST 1: LLM Connection
# ============================================================================

def test_llm():
    print_header("TEST 1: LLM (OpenAI) Connection")
    
    print_info("Testing connection to OpenAI API...")
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print_error("OPENAI_API_KEY not found in environment")
            print_warning("Troubleshooting:")
            print("  1. Make sure .env file contains OPENAI_API_KEY=sk-...")
            print("  2. Restart your terminal/IDE after adding the key")
            return False
        
        # Recharge .env depuis la racine (robuste)
        project_root = Path(__file__).resolve().parents[1]
        load_dotenv(dotenv_path=project_root / ".env")

        base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
        api_key  = os.getenv("OPENAI_API_KEY", "sk-local-dummy")

        # Récupère le modèle depuis character_config.yaml
        config_path = project_root / "character_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        model_id = config.get("model")
        if not model_id:
            print_error("Le champ 'model' est vide dans character_config.yaml")
            return False

        client = OpenAI(api_key=api_key, base_url=base_url)

        print_info(f"Sending test message to local LLM at {base_url} ...")
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Réponds uniquement par: OK"},
                {"role": "user", "content": "OK ?"}
            ],
            temperature=0.0,
            max_tokens=10
        )
        
        response_text = response.choices[0].message.content
        print_success(f"LLM Response: {response_text}")
        print_success("OpenAI API is working correctly!")
        return True
        
    except ImportError:
        print_error("OpenAI library not installed")
        print_warning("Install with: pip install openai")
        return False
    except Exception as e:
        print_error(f"LLM test failed: {e}")
        print_warning("\nTroubleshooting:")
        print("  1. Check your API key is valid at https://platform.openai.com/api-keys")
        print("  2. Ensure you have credits/billing set up on your OpenAI account")
        print("  3. Check your internet connection")
        print(f"  4. Error details: {str(e)}")
        return False

# ============================================================================
# TEST 2: Audio Recording
# ============================================================================

def test_audio_recording():
    print_header("TEST 2: Audio Recording (Microphone)")
    
    print_info("Checking available audio devices...")
    
    try:
        devices = sd.query_devices()
        print_info("Available audio devices:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                default = " (DEFAULT)" if i == sd.default.device[0] else ""
                print(f"  [{i}] {device['name']}{default}")
        
        default_input = sd.default.device[0]
        print_success(f"\nDefault input device: {devices[default_input]['name']}")
        
    except Exception as e:
        print_error(f"Error querying audio devices: {e}")
        print_warning("Troubleshooting:")
        print("  1. Make sure a microphone is plugged in")
        print("  2. Check system audio settings")
        print("  3. Install required library: pip install sounddevice")
        return False
    
    print_info("\nTesting microphone recording...")
    print_warning("When prompted, speak into your microphone for 3 seconds")
    wait_for_user("Press ENTER when ready to record...")
    
    try:
        from process.asr_func.asr_auto_record import record_on_speech
        
        test_audio_path = Path("audio") / "test_recording.wav"
        test_audio_path.parent.mkdir(parents=True, exist_ok=True)
        
        print_info("Recording... (speak now!)")
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        dev = os.getenv("AUDIO_INPUT_DEVICE", "").strip()
        device = int(dev) if dev.isdigit() else (dev if dev else None)

        record_on_speech(
            output_file=str(test_audio_path),
            samplerate=44100,
            channels=1,
            silence_threshold=0.005,
            silence_duration=1,
            device=device
        )
        
        if test_audio_path.exists() and test_audio_path.stat().st_size > 1000:
            print_success(f"Audio recorded successfully! File: {test_audio_path}")
            print_info(f"File size: {test_audio_path.stat().st_size} bytes")
            
            # Test transcription
            print_info("\nTesting transcription with Groq...")
            try:
                from process.asr_func.asr_transcribe_groq import transcribe_audio_groq
                
                transcription = transcribe_audio_groq(aud_path=str(test_audio_path))
                print_success(f"Transcription: '{transcription}'")
                
                if transcription and len(transcription.strip()) > 0:
                    print_success("Audio recording and transcription working!")
                    return True
                else:
                    print_warning("Transcription returned empty text")
                    print_info("This might be normal if you didn't speak during recording")
                    return True
                    
            except Exception as e:
                print_error(f"Transcription failed: {e}")
                print_warning("\nTroubleshooting:")
                print("  1. Check GROQ_API_KEY is set in .env file")
                print("  2. Verify Groq API key at https://console.groq.com/keys")
                print("  3. Check internet connection")
                return False
        else:
            print_error("Recording file not created or is too small")
            return False
            
    except ImportError as e:
        print_error(f"Missing required module: {e}")
        print_warning("Install required libraries:")
        print("  pip install sounddevice soundfile")
        return False
    except Exception as e:
        print_error(f"Recording test failed: {e}")
        print_warning("\nTroubleshooting:")
        print("  1. Check microphone is plugged in and working")
        print("  2. Grant microphone permissions to Python/terminal")
        print("  3. Try a different microphone or audio device")
        print("  4. Check audio device settings in your OS")
        return False

# ============================================================================
# TEST 3: TTS (SoVITS) Audio Generation
# ============================================================================

def test_tts_generation():
    print_header("TEST 3: TTS Audio Generation (GPT-SoVITS)")
    
    print_info("Testing connection to GPT-SoVITS server...")
    
    try:
        from process.tts_func.sovits_ping import sovits_gen
        
        test_text = "Hello! This is a test of the text to speech system."
        output_path = Path("audio") / f"test_tts_{uuid.uuid4().hex}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print_info(f"Generating speech for: '{test_text}'")
        print_warning("This requires GPT-SoVITS server to be running...")
        
        sovits_gen(test_text, output_wav_pth=str(output_path))
        
        if output_path.exists() and output_path.stat().st_size > 1000:
            print_success(f"TTS audio generated! File: {output_path}")
            print_info(f"File size: {output_path.stat().st_size} bytes")
            
            # Try to get duration
            try:
                from process.tts_func.sovits_ping import get_wav_duration
                duration = get_wav_duration(str(output_path))
                print_info(f"Audio duration: {duration:.2f} seconds")
            except:
                pass
            
            print_success("\n✓ TTS generation is working!")
            print_info("You can manually check the audio file to verify quality")
            
            response = input(f"\n{Colors.BOLD}Can you hear the audio when you play it? (y/n): {Colors.ENDC}").lower()
            if response == 'y':
                print_success("Great! TTS system is fully functional")
                return True
            else:
                print_warning("Audio file was generated but might have issues")
                print_info("Check the audio file manually: " + str(output_path))
                return True
        else:
            print_error("TTS file not created or is too small")
            return False
            
    except ImportError as e:
        print_error(f"Missing required module: {e}")
        return False
    except ConnectionError as e:
        print_error(f"Cannot connect to GPT-SoVITS server: {e}")
        print_warning("\nTroubleshooting:")
        print("  1. Make sure GPT-SoVITS server is running")
        print("  2. Check the server is accessible (usually http://localhost:9880)")
        print("  3. Verify server configuration in your code")
        print("  4. Check server logs for errors")
        return False
    except Exception as e:
        print_error(f"TTS test failed: {e}")
        print_warning("\nTroubleshooting:")
        print("  1. Ensure GPT-SoVITS server is running and accessible")
        print("  2. Check server URL/port configuration")
        print("  3. Verify server has required voice models loaded")
        print("  4. Check server logs for detailed error messages")
        return False

# ============================================================================
# TEST 4: VRM Server and Audio Playback
# ============================================================================

def test_vrm_server():
    print_header("TEST 4: VRM Server Connection")
    
    print_info(f"Checking VRM server at {BASE_URL}...")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print_success("VRM server is running!")
        return True
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to VRM server at {BASE_URL}")
        print_warning("\nTroubleshooting:")
        print("  1. Make sure the VRM server (Node.js/Three.js app) is running")
        print("  2. Check it's running on port 8001")
        print("  3. Verify no firewall is blocking the connection")
        print("  4. Start the server with: npm start (or your start command)")
        return False
    except Exception as e:
        print_error(f"Error connecting to VRM server: {e}")
        return False

def test_vrm_audio_playback():
    print_header("TEST 5: VRM Audio Playback")
    
    print_info("Testing vrm_talk function with audio playback...")
    
    # First, generate a test audio file
    try:
        from process.tts_func.sovits_ping import sovits_gen, get_wav_duration
        
        test_text = "Testing audio playback through the VRM system."
        client_audio = Path("client/audio") / f"test_playback_{uuid.uuid4().hex}.wav"
        client_audio.parent.mkdir(parents=True, exist_ok=True)
        
        public_audio = Path("audio") / client_audio.name
        public_audio.parent.mkdir(parents=True, exist_ok=True)
        
        print_info("Generating test audio...")
        sovits_gen(test_text, output_wav_pth=str(client_audio))
        
        # Copy to public directory
        import shutil
        shutil.copy2(client_audio, public_audio)
        
        duration = get_wav_duration(str(public_audio))
        print_success(f"Test audio generated: {public_audio}")
        
        # Send to VRM
        print_info("Sending audio to VRM server...")
        url = f"{BASE_URL}/talk"
        payload = {
            "audio_path": str(public_audio),
            "expression": "relaxed",
            "audio_text": test_text,
            "audio_duraction": int(duration)
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print_success(f"VRM talk request successful! Status: {response.status_code}")
            print_info("Response: " + str(response.json()))
            
            print_warning("\n" + "─"*60)
            print_warning("IMPORTANT: Check the VRM client in your browser!")
            print_warning("─"*60)
            
            print_info("\nYou should see/hear:")
            print("  1. The avatar's mouth moving")
            print("  2. Audio playing from your speakers")
            
            while True:
                response = input(f"\n{Colors.BOLD}Did you see the mouth move AND hear audio? (y/n): {Colors.ENDC}").lower()
                
                if response == 'y':
                    print_success("Perfect! VRM audio playback is working correctly!")
                    return True
                else:
                    print_warning("\nDiagnosing the issue...")
                    
                    mouth = input(f"{Colors.BOLD}Did you see the mouth move? (y/n): {Colors.ENDC}").lower()
                    audio = input(f"{Colors.BOLD}Did you hear audio? (y/n): {Colors.ENDC}").lower()
                    
                    if audio == 'y' and mouth == 'n':
                        print_warning("\n🔧 Issue: Audio plays but mouth doesn't move")
                        print_info("Solution:")
                        print("  1. Open client/config.js")
                        print("  2. Find 'mouth_threshold' variable")
                        print("  3. Try lowering it (e.g., from 0.01 to 0.005)")
                        print("  4. Refresh the browser and test again")
                        
                    elif audio == 'n' and mouth == 'n':
                        print_warning("\n🔧 Issue: No audio and no animation")
                        print_info("Solution:")
                        print("  1. Refresh the browser page")
                        print("  2. Click inside the browser window to activate it")
                        print("  3. Try again")
                        print("  4. Check browser console (F12) for errors")
                        print("  5. Ensure audio files are in the correct directory")
                        
                    elif audio == 'n' and mouth == 'y':
                        print_warning("\n🔧 Issue: Mouth moves but no audio")
                        print_info("Solution:")
                        print("  1. Check browser audio isn't muted")
                        print("  2. Check system volume")
                        print("  3. Verify audio file path is correct")
                        print("  4. Check browser console (F12) for audio errors")
                    
                    # Ask if they want to retry or continue
                    print("\n" + "─"*60)
                    retry = input(f"{Colors.BOLD}Would you like to:\n  [r] Retry the test after applying changes\n  [c] Continue to next test anyway\n  [q] Mark as failed and continue\nChoice (r/c/q): {Colors.ENDC}").lower()
                    
                    if retry == 'r':
                        print_info("\nRetrying test...\n")
                        # Re-send the audio to VRM
                        time.sleep(1)
                        requests.post(url, json=payload, timeout=10)
                        continue  # Loop back to ask if it worked
                    elif retry == 'c':
                        print_warning("Continuing despite issues...")
                        return True  # Mark as passed but with warning
                    else:
                        print_warning("Marking test as failed")
                        return False
        else:
            print_error(f"VRM talk request failed! Status: {response.status_code}")
            print_info("Response: " + str(response.text))
            return False
            
    except Exception as e:
        print_error(f"VRM audio playback test failed: {e}")
        print_warning("\nTroubleshooting:")
        print("  1. Ensure VRM server is running")
        print("  2. Check browser is open with the VRM client")
        print("  3. Verify audio files are in correct directories")
        print("  4. Check server logs for errors")
        return False

# ============================================================================
# TEST 6: VRM Animations
# ============================================================================

def test_vrm_animations():
    print_header("TEST 6: VRM Animations")
    
    animations = [
        ("idle", "animations/mixamo/Idle.fbx", "Idle (looking around)"),
        ("thinking", "animations/mixamo/Thinking.fbx", "Thinking (looking away)"),
        ("talking", "animations/mixamo/Talking.fbx", "Talking (nodding)"),
    ]
    
    print_info("Testing VRM animations...")
    print_warning("Watch the VRM client in your browser during these tests\n")
    
    all_passed = True
    
    for state_name, anim_path, description in animations:
        while True:
            try:
                print_info(f"Testing: {description}")
                
                # Set animation
                url = f"{BASE_URL}/animate"
                payload = {
                    "animate_type": "start_mixamo",
                    "animation_url": anim_path,
                    "play_once": False,
                    "crop_start": 0.0,
                    "crop_end": 0.0,
                    "lock_position": False,
                    "track_position": True,
                }
                response = requests.post(url, json=payload, timeout=5)
                
                # Set state
                state_url = f"{BASE_URL}/set_state"
                state_payload = {"state": state_name}
                state_response = requests.post(state_url, json=state_payload, timeout=5)
                
                if response.status_code == 200 and state_response.status_code == 200:
                    print_success(f"  Animation command sent successfully")
                    
                    time.sleep(2)  # Let user observe
                    
                    saw_it = input(f"  {Colors.BOLD}Did you see the {description} animation? (y/n): {Colors.ENDC}").lower()
                    if saw_it == 'y':
                        print_success(f"  ✓ {state_name} animation working!\n")
                        break  # Move to next animation
                    else:
                        print_warning(f"  ! {state_name} animation may not be working")
                        print_info("\nTroubleshooting:")
                        print(f"  1. Check that {anim_path} exists")
                        print("  2. Refresh the browser and ensure VRM client is loaded")
                        print("  3. Check browser console (F12) for errors")
                        print("  4. Verify VRM server logs")
                        
                        retry = input(f"\n{Colors.BOLD}Would you like to:\n  [r] Retry this animation\n  [c] Continue to next animation\n  [q] Mark as failed and continue\nChoice (r/c/q): {Colors.ENDC}").lower()
                        
                        if retry == 'r':
                            print_info("Retrying animation...\n")
                            time.sleep(1)
                            continue  # Retry this animation
                        elif retry == 'c':
                            print_warning(f"Continuing despite {state_name} animation issues...\n")
                            all_passed = False
                            break  # Move to next animation
                        else:
                            print_warning(f"Marking {state_name} animation as failed\n")
                            all_passed = False
                            break  # Move to next animation
                else:
                    print_error(f"  Animation request failed: {response.status_code}")
                    print_warning("  Check VRM server logs for details\n")
                    
                    retry = input(f"{Colors.BOLD}Would you like to:\n  [r] Retry this animation\n  [c] Continue to next animation\nChoice (r/c): {Colors.ENDC}").lower()
                    
                    if retry == 'r':
                        print_info("Retrying...\n")
                        continue
                    else:
                        all_passed = False
                        break
                    
            except Exception as e:
                print_error(f"  Animation test failed: {e}")
                
                retry = input(f"{Colors.BOLD}Would you like to:\n  [r] Retry this animation\n  [c] Continue to next animation\nChoice (r/c): {Colors.ENDC}").lower()
                
                if retry == 'r':
                    print_info("Retrying...\n")
                    continue
                else:
                    all_passed = False
                    break
    
    if all_passed:
        print_success("\n✓ All animations are working!")
        return True
    else:
        print_warning("\nSome animations may not be working correctly")
        print_info("Troubleshooting:")
        print("  1. Check that animation files exist in animations/mixamo/")
        print("  2. Verify file paths are correct")
        print("  3. Check VRM server console for errors")
        print("  4. Ensure browser client has loaded properly")
        return False

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     VRM AVATAR CHAT SYSTEM - COMPREHENSIVE TEST SUITE     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    print_info("This script will test all components of your VRM chat system")
    print_info("Each test will provide feedback and troubleshooting tips if needed\n")
    
    wait_for_user()
    
    results = {}
    
    # Run tests in sequence
    results['config'] = test_config_and_keys()
    
    if results['config']:
        results['llm'] = test_llm()
    else:
        print_warning("\nSkipping LLM test due to configuration issues")
        results['llm'] = False
    
    results['recording'] = test_audio_recording()
    results['tts'] = test_tts_generation()
    results['vrm_server'] = test_vrm_server()
    
    if results['vrm_server']:
        results['vrm_playback'] = test_vrm_audio_playback()
        results['vrm_animations'] = test_vrm_animations()
    else:
        print_warning("\nSkipping VRM tests due to server connection issues")
        results['vrm_playback'] = False
        results['vrm_animations'] = False
    
    # Final Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"  {test_name.upper():.<50} {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 All systems operational! Your VRM chat system is ready to use!{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}⚠ Some tests failed. Please review the troubleshooting tips above.{Colors.ENDC}")
        print_info("\nCommon next steps:")
        print("  1. Fix configuration issues (API keys, config files)")
        print("  2. Ensure all servers are running (GPT-SoVITS, VRM server)")
        print("  3. Check hardware (microphone, speakers)")
        print("  4. Verify network connectivity")
        print("  5. Review server logs for detailed errors")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)