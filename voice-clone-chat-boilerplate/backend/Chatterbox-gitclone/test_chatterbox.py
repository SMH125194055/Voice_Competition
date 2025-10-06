import torch
import torchaudio as ta

from chatterbox.vc import ChatterboxVC

# Automatically detect the best available device
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Using device: {device}")

AUDIO_PATH = "audio/test-english.wav"
TARGET_VOICE_PATH = "audio/Nafay_Org.mp3"

model = ChatterboxVC.from_pretrained(device)
wav = model.generate(
    audio=AUDIO_PATH,
    target_voice_path=TARGET_VOICE_PATH,
)
ta.save("testvc.wav", wav, model.sr)