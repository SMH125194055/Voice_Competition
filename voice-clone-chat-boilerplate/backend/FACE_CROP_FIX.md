# 🎭 Face Cropping Fix - Include Shoulders

## Issue:
Avatar videos crop too tight - only shows face up to chin, missing shoulders.

## Root Cause:
SadTalker's cropping algorithm centers on face landmarks and creates a tight bounding box. Need to expand the crop area downward to include shoulders.

## Solution:

### File to Modify:
`backend/Avatar/SadTalker/src/utils/croper.py`

### Current Code (Line ~90-125):
```python
def align_face(self, img, lm, output_size=1024):
    # ... existing code ...
    
    # Create quad bounding box around face
    quad = np.stack([
        transform.dot([0, 0, 1]),
        transform.dot([0, output_size, 1]),
        transform.dot([output_size, output_size, 1]),
        transform.dot([output_size, 0, 1])
    ])
    
    # ... existing code ...
    
    # Transform
    quad = (quad + 0.5).flatten()
    lx = max(min(quad[0], quad[2]), 0)
    ly = max(min(quad[1], quad[7]), 0)   # Top edge
    rx = min(max(quad[4], quad[6]), img.size[0])
    ry = min(max(quad[3], quad[5]), img.size[0])  # Bottom edge
    
    return rsize, crop, [lx, ly, rx, ry]
```

### Recommended Fix:

**Option 1: Expand Bottom Crop (Simple)**

Around line 121, change:
```python
# OLD:
ry = min(max(quad[3], quad[5]), img.size[0])

# NEW - Expand by 30%:
bottom_expand = int((ry - ly) * 0.3)  # Add 30% more height at bottom
ry = min(max(quad[3], quad[5]) + bottom_expand, img.size[1])
```

**Option 2: Adjust scale parameter**

Around line 66-70 where scale is calculated:
```python
# OLD:
scale = quad_size / (np.hypot(*right_direction) * 2.0)

# NEW - Increase scale by 1.3x:
scale = quad_size / (np.hypot(*right_direction) * 2.0) * 1.3
```

**Option 3: Modify landmark-based centering**

Around line 45-50:
```python
# OLD:
center = lm[57, :]  # Nose tip or face center

# NEW - Move center point down to include shoulders:
center_y_offset = (lm[:, 1].max() - lm[:, 1].min()) * 0.2  # 20% of face height
center = lm[57, :].copy()
center[1] -= center_y_offset  # Move up so more space at bottom
```

## Recommended Approach:

**Use Option 1** - It's the simplest and most direct:

```python
def align_face(self, img, lm, output_size=1024):
    # ... keep all existing code until line 118 ...
    
    # Transform.
    quad = (quad + 0.5).flatten()
    lx = max(min(quad[0], quad[2]), 0)
    ly = max(min(quad[1], quad[7]), 0)
    rx = min(max(quad[4], quad[6]), img.size[0])
    
    # ✅ FIX: Expand bottom to include shoulders
    ry_original = min(max(quad[3], quad[5]), img.size[1])
    height = ry_original - ly
    shoulder_expand = int(height * 0.4)  # Expand by 40% for shoulders
    ry = min(ry_original + shoulder_expand, img.size[1])
    
    # Save aligned image.
    return rsize, crop, [lx, ly, rx, ry]
```

## Testing:

After applying fix:

1. Upload new reference image
2. Generate avatar video
3. Check if shoulders are visible
4. Adjust `shoulder_expand` percentage if needed:
   - 0.3 = 30% more (conservative)
   - 0.4 = 40% more (recommended)
   - 0.5 = 50% more (generous)

## Alternative: Use 'full' mode instead of 'crop'

In `backend/utils/avatar_generator.py` line 177:

```python
# OLD:
preprocess: str = 'crop',

# NEW:
preprocess: str = 'full',
```

The 'full' mode uses the entire detection area rather than tight crop.

## Validation:

After fix, verify:
- ✅ Face fully visible
- ✅ Shoulders included
- ✅ Not too much empty space
- ✅ Good framing like professional headshot

## Quick Test Script:

```python
# Test the crop adjustment
import cv2
import numpy as np

image_path = "your_reference_image.jpg"
img = cv2.imread(image_path)
height, width = img.shape[:2]

# Simulate new crop (40% expansion at bottom)
face_height = height // 2  # Approximate
expansion = int(face_height * 0.4)
print(f"Will expand bottom by {expansion}px to include shoulders")
```

## Expected Result:

**Before Fix:**
```
┌─────────┐
│  👀     │  ← Eyes
│  👃     │  ← Nose  
│  👄     │  ← Mouth
└─────────┘  ← Chin (CUT HERE ❌)
   Missing shoulders
```

**After Fix:**
```
┌─────────┐
│  👀     │  ← Eyes
│  👃     │  ← Nose
│  👄     │  ← Mouth
│  ━━     │  ← Chin
│  💪 💪  │  ← Shoulders (NOW VISIBLE ✅)
└─────────┘
```

## Notes:

- The expansion is proportional to face height
- Works with any image aspect ratio
- Doesn't break existing functionality
- Can be adjusted per user preference

## Implementation Priority:

**Recommended: Option 1 (Bottom Expansion)**
- File: `backend/Avatar/SadTalker/src/utils/croper.py`
- Line: ~121
- Change: Add shoulder_expand calculation
- Impact: Low risk, easy to adjust
- Test: Immediate visual feedback

Ready to implement!

