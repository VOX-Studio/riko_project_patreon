# sudo apt update
# sudo apt install libportaudio2 libasound2-dev

import sounddevice as sd
print(sd.query_devices())