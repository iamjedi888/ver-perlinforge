# TriptokForge: Verse Package Compression & Download System
## Integration Guide

This guide shows how to add zip download and compression to your UEFN Verse export system.

---

## Files Created

1. **compression_utils.py** - Core compression/decompression utilities
2. **forge_verse_routes.py** - Flask download endpoints
3. **verse_downloader.js** - Frontend download UI

---

## Step 1: Copy Files to Project

```bash
# On your PC (in ver-perlinforge directory)
# Copy the 3 files to the islandforge folder
cp compression_utils.py islandforge/
cp forge_verse_routes.py islandforge/
cp verse_downloader.js islandforge/static/js/
```

---

## Step 2: Update forge.py (Add Download Routes)

Open `islandforge/forge.py` and add these imports at the top:

```python
from compression_utils import (
    compress_verse_package, 
    decompress_verse_package,
    create_verse_package_zip
)
```

Then add these two routes to your forge blueprint (copy from `forge_verse_routes.py`):

```python
@forge_bp.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    """Download Verse package as zip"""
    # ... (copy full function from forge_verse_routes.py)

@forge_bp.route('/api/forge/get-saved-verse/<int:save_id>', methods=['GET'])
def get_saved_verse_package(save_id):
    """Get saved Verse package"""
    # ... (copy full function from forge_verse_routes.py)
```

---

## Step 3: Update Island Save Logic (Add Compression)

In your `/api/forge/generate` route (or wherever you save islands to Oracle), add compression:

```python
@forge_bp.route('/api/forge/generate', methods=['POST'])
def generate_island():
    # ... existing generation code ...
    
    # After you get the result with verse_package:
    verse_package = result.get('verse_package', {})
    
    if verse_package:
        # Compress before storing in Oracle
        from compression_utils import compress_verse_package
        compressed_verse = compress_verse_package(verse_package)
        
        # Save to Oracle with compressed data
        oracle_db.execute_query("""
            INSERT INTO island_saves 
            (epic_id, seed, display_name, verse_data, config, created_at)
            VALUES 
            (:epic_id, :seed, :name, :verse_data, :config, CURRENT_TIMESTAMP)
        """, {
            'epic_id': session.get('epic_id'),
            'seed': seed,
            'name': f'Island {seed}',
            'verse_data': compressed_verse,  # <-- Compressed!
            'config': json.dumps(request_data)
        })
    
    # Return verse_package in response for immediate download
    return jsonify(result)
```

---

## Step 4: Update forge.html (Add Download Button)

Add the JavaScript file to your forge.html:

```html
<!-- Near the end of <body>, after other script tags -->
<script src="{{ url_for('static', filename='js/verse_downloader.js') }}"></script>
```

Then modify your island generation JavaScript to dispatch the event:

```javascript
// In your existing AJAX success handler for island generation:
fetch('/api/forge/generate', {
    method: 'POST',
    // ... your existing code
})
.then(response => response.json())
.then(data => {
    // ... your existing code to show the preview image ...
    
    // NEW: Dispatch event for verse downloader
    const event = new CustomEvent('islandGenerated', {
        detail: data
    });
    window.dispatchEvent(event);
});
```

---

## Step 5: Test Locally

```powershell
# In ver-perlinforge directory
python islandforge/audio_to_heightmap.py --seed 777 --size 505 --out test_output --theme volcanic
```

Check that `test_output/island_777_verse_package/` has 7 files.

---

## Step 6: Deploy to Oracle VM

```powershell
# Push to GitHub
git add -A
git commit -m "Add Verse package compression and zip download system"
git push origin main

# SSH to VM
ssh -i "C:\Users\xinc\Downloads\ssh-key-2.key" ubuntu@129.80.222.152

# Pull and restart
cd ~/ver-perlinforge
git pull origin main
sudo systemctl restart islandforge
sudo systemctl status islandforge
```

---

## Step 7: Verify on Production

1. Visit **triptokforge.org/forge**
2. Generate an island
3. Look for **"Download UEFN Verse Package"** button
4. Click it → should download a .zip file
5. Extract zip → should have 7 Verse files inside

---

## Compression Stats

Typical compression ratios for Verse packages:

- **JSON files** (plot_registry, biome_manifest): 80-90% compression
- **Verse code** (foliage_spawner, poi_placer): 70-75% compression
- **README.md**: 65-70% compression

**Example**: A 250 KB Verse package compresses to ~50 KB (80% savings)

This dramatically reduces Oracle CLOB storage and speeds up downloads.

---

## Bonus: Add Download Button to Saved Islands List

If you have a "My Saved Islands" page, add download links:

```html
<!-- In your saved islands list -->
<a href="/api/forge/get-saved-verse/{{ island.id }}?zip=true" 
   class="btn btn-sm btn-success">
    <i class="fas fa-download"></i> Download Verse
</a>
```

---

## Troubleshooting

### "No verse_package in response"
- Check that `audio_to_heightmap.py` is calling `integrate_with_forge()`
- Verify `verse_export_generator.py` is imported correctly

### "Zip file is empty"
- Check Flask route has `send_file()` with correct parameters
- Verify `create_verse_package_zip()` is creating files

### "Button doesn't appear"
- Check browser console for JavaScript errors
- Verify `verse_downloader.js` is loaded
- Dispatch the `islandGenerated` event correctly

---

## Next Steps (Future Phases)

**Phase 2**: Asset Library Integration
- Browse free 3D models from Sketchfab API
- Add texture packs from OpenGameArt
- Let users pick assets for islands

**Phase 3**: Audio Generator
- Integrate Tone.js for music synthesis
- Bfxr-style sound effect generator
- ChipTone music maker

**Phase 4**: Advanced Compression
- Add preview image compression (PNG → WebP)
- Compress heightmap arrays (NumPy → compressed binary)
- Delta compression for similar islands

Ready to deploy? Start with Step 1!
