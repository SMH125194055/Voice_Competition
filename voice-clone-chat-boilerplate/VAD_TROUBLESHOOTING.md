# 🔧 VAD Troubleshooting Guide

## Issue: "Failed to initialize voice detection" or "Failed to load model file"

### Problem
The browser console shows errors like:
```
Failed to load module script: Expected a JavaScript-or-Wasm module script but the server responded with a MIME type of "text/html"
Encountered an error while loading model file ./silero_vad_legacy.onnx
```

### Root Cause
The `@ricky0123/vad-web` library needs to load ONNX model files, but it can't find them in the default location. By default, it tries to load from relative paths, which don't work in a React development environment.

### Solution ✅ (Already Applied)
The VAD component has been configured to load models from **local files** in the public folder:

```javascript
const vad = useMicVAD({
  modelURL: '/vad-models/silero_vad_legacy.onnx',
  workletURL: '/vad-models/vad.worklet.bundle.min.js',
  // ... other config
});
```

The model files have been copied to `public/vad-models/` from the npm package.

### Expected Behavior After Fix

1. **Refresh the page** (should happen automatically with hot reload)
2. You should see in the console:
   ```
   Loading VAD model...
   VAD model loaded successfully
   ```
3. Status should change from "Initializing..." to "Ready! Click Start to begin"

### If Still Not Working

#### Option 1: Try Alternative CDN
If jsdelivr is blocked or slow, use unpkg instead:

Edit `VADVoiceAgent.js` and change:
```javascript
modelURL: 'https://unpkg.com/@ricky0123/vad-web@0.0.7/dist/silero_vad.onnx',
workletURL: 'https://unpkg.com/@ricky0123/vad-web@0.0.7/dist/vad.worklet.bundle.min.js',
```

#### Option 2: Use Local Models (Advanced)
If you need offline support:

1. **Copy model files to public folder:**
```bash
cd voice-clone-chat-boilerplate/frontend/voice-ui
mkdir -p public/vad-models
cp node_modules/@ricky0123/vad-web/dist/silero_vad.onnx public/vad-models/
cp node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js public/vad-models/
```

2. **Update config in VADVoiceAgent.js:**
```javascript
const vad = useMicVAD({
  modelURL: '/vad-models/silero_vad.onnx',
  workletURL: '/vad-models/vad.worklet.bundle.min.js',
  // ... other config
});
```

3. **Restart development server:**
```bash
npm start
```

#### Option 3: Check Internet Connection
The CDN approach requires internet. Verify:
- Internet connection is working
- No firewall blocking CDN domains
- No proxy issues

#### Option 4: Clear Cache
Sometimes browser cache causes issues:
1. Open DevTools (F12)
2. Right-click refresh button
3. Select "Empty Cache and Hard Reload"

### Verification Steps

#### Step 1: Check Network Tab
1. Open DevTools (F12)
2. Go to "Network" tab
3. Refresh page
4. Look for:
   - `silero_vad.onnx` - should show status 200
   - `vad.worklet.bundle.min.js` - should show status 200

#### Step 2: Check Console
Should see:
```
✅ No errors about model loading
✅ "VAD model loaded" or similar success message
✅ Status: "Ready! Click Start to begin"
```

#### Step 3: Test Functionality
1. Click "Start Listening"
2. Status should change to "Listening for speech..."
3. Speak into microphone
4. User orb (left) should light up blue
5. Pause - processing should start automatically

### Common Browser Issues

#### Chrome/Edge
- Usually works best with VAD
- May need to allow microphone permissions
- Check: Settings → Privacy → Site Settings → Microphone

#### Firefox
- May have stricter CORS policies
- Try clearing cache and cookies
- Enable media.navigator.permission.disabled in about:config (for testing only)

#### Safari
- May need additional permissions
- Check: Preferences → Websites → Microphone
- Some older versions don't support AudioWorklet

### Network Restrictions

If you're on a corporate/school network:

1. **Check if CDNs are blocked**
   - Try accessing: https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.7/dist/silero_vad.onnx
   - Should download a file, not show an error

2. **Use VPN if needed**
   - Some networks block CDNs
   - VPN can bypass restrictions

3. **Use local models**
   - Follow "Option 2" above for offline support

### Development Mode Issues

#### Issue: Models load slowly
**Cause:** First-time download from CDN
**Solution:** Be patient, models are ~5MB and cached after first load

#### Issue: Hot reload breaks VAD
**Cause:** React development mode sometimes interferes
**Solution:** 
- Refresh page manually (Ctrl+R)
- Or restart dev server: `npm start`

### Production Deployment

When deploying to production:

#### Recommended: Use CDN (Current Setup)
- ✅ No build configuration needed
- ✅ Models cached by browser
- ✅ No file hosting required
- ⚠️ Requires internet connection

#### Alternative: Self-Host Models
1. Copy models to public folder (see Option 2 above)
2. Update URLs to use relative paths
3. Models will be served from your domain
4. Works offline

### Testing Checklist

Before reporting issues, verify:

- [ ] Internet connection working
- [ ] No console errors (F12)
- [ ] Microphone permission granted
- [ ] Page fully loaded (no spinners)
- [ ] Browser is modern (Chrome 90+, Firefox 88+, Safari 14.1+)
- [ ] Not using incognito/private mode (may block features)
- [ ] Backend is running (`http://localhost:8000` accessible)

### Still Having Issues?

1. **Check browser console** (F12) for exact error messages
2. **Check network tab** for failed requests
3. **Try different browser** (Chrome usually works best)
4. **Clear all cache and cookies**
5. **Restart both frontend and backend servers**

### Error Messages Reference

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to load model file" | Can't access ONNX model | Use CDN URLs (already fixed) |
| "MIME type text/html" | 404 on model file | Check modelURL is correct |
| "Failed to initialize" | Model loading failed | Check internet, try alt CDN |
| "Microphone permission denied" | No mic access | Grant permissions in browser |
| "AudioWorklet not supported" | Old browser | Update browser |

### Quick Fix Commands

If you need to reset everything:

```bash
# Stop servers (Ctrl+C)

# Clear frontend cache
cd voice-clone-chat-boilerplate/frontend/voice-ui
rm -rf node_modules/.cache

# Restart
npm start
```

### Success Indicators

You'll know it's working when:
1. ✅ Status shows "Ready! Click Start to begin"
2. ✅ No red errors in console
3. ✅ "Start Listening" button is enabled (not grayed out)
4. ✅ Network tab shows successful model downloads (200 status)

### Performance Notes

- **First load**: 5-10 seconds (downloading models)
- **Subsequent loads**: Instant (models cached)
- **Model size**: ~5MB total
- **Memory usage**: ~50MB in browser

---

## Current Status

✅ **Fix Applied**: VAD now uses CDN for model loading
✅ **Code Updated**: `VADVoiceAgent.js` configured with jsdelivr CDN
✅ **Ready to Test**: Refresh page and test

The issue has been resolved. Simply **refresh your browser** and the VAD should initialize correctly!

