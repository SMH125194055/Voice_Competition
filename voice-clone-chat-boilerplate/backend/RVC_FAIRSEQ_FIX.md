# RVC Fairseq Compatibility Fix

## Error

```
mutable default <class 'fairseq.dataclass.configs.CommonConfig'> for field common is not allowed: use default_factory
```

## Problem

The `rvc-python` library has a dependency conflict with newer versions of `fairseq`. This is a known issue with the dataclass implementation in fairseq.

## Solution Options

### Option 1: Downgrade fairseq (Recommended)

```bash
cd backend
.\venv\Scripts\activate
pip uninstall fairseq -y
pip install fairseq==0.12.2
```

### Option 2: Use alternative RVC implementation

Install the more stable RVC implementation:

```bash
pip uninstall rvc-python -y
pip install rvc-infer
```

### Option 3: Patch fairseq (Advanced)

If downgrade doesn't work, you can patch fairseq manually. But this is complex.

## Recommended: Use Lighter Alternative

Since RVC has dependency issues, I recommend using a simpler fast TTS approach. Let me update the code to use a more reliable method.





