# VAD Model Files

These files are required for the Voice Activity Detection feature to work.

## Files in this directory:
- `silero_vad_legacy.onnx` - Legacy VAD model (1.8 MB)
- `silero_vad_v5.onnx` - Version 5 VAD model (2.3 MB)  
- `vad.worklet.bundle.min.js` - Audio worklet for processing
- Other supporting JavaScript files

## Source
These files are copied from `node_modules/@ricky0123/vad-web/dist/` during setup.

## Usage
The VADVoiceAgent component loads these files from `/vad-models/` path.

## Why local instead of CDN?
Version 0.0.28 of @ricky0123/vad-web doesn't publish these files to CDN, so we need to serve them locally.

## If files are missing:
Run from the `frontend/voice-ui` directory:
```bash
# PowerShell
Copy-Item "node_modules\@ricky0123\vad-web\dist\*.onnx" -Destination "public\vad-models\"
Copy-Item "node_modules\@ricky0123\vad-web\dist\*.js" -Destination "public\vad-models\"

# Bash
cp node_modules/@ricky0123/vad-web/dist/*.onnx public/vad-models/
cp node_modules/@ricky0123/vad-web/dist/*.js public/vad-models/
```

## For production deployment:
Make sure to include this `vad-models` folder when deploying your application.

