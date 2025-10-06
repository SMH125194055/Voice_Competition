# Fix RVC for Real-Time Voice Cloning

## The Problem
RVC has a fairseq dataclass conflict. We can fix this!

## Solution: Downgrade fairseq

Run these commands:

```bash
cd backend
.\venv\Scripts\activate

# Remove problematic version
pip uninstall fairseq -y

# Install compatible version
pip install fairseq==0.12.2

# Verify
pip show fairseq
```

## If That Doesn't Work

Try alternative RVC package:

```bash
pip uninstall rvc-python -y
pip install so-vits-svc-fork
```

## Or Use This Workaround

If fairseq still has issues, we can patch it manually.

Edit the fairseq file directly (advanced):
```bash
# Find fairseq location
python -c "import fairseq; print(fairseq.__file__)"

# Edit dataclass/configs.py
# Change CommonConfig default to use default_factory
```

## Test After Fix

```bash
# Restart backend
uvicorn main:app --reload --port 8000

# Test
curl -X POST http://localhost:8000/speak \
  -F "text=Testing RVC after fixing fairseq" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output rvc_fixed.wav
```

Expected: ~5-15 seconds with voice cloning!


