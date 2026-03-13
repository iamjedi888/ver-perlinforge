"""
Integration Patch for TriptokForge
Connects UEFN Verse Export System to existing forge
"""

import os
import sys
import shutil

# Add this integration to your existing audio_to_heightmap.py or forge route

INTEGRATION_CODE = '''
# ADD TO IMPORTS at top of audio_to_heightmap.py:
from verse_export_generator import integrate_with_forge

# ADD TO generate_heightmap() function or /generate route handler:
# Right before returning the result dict, add:

def generate_heightmap_with_verse(audio_path, seed, size, world_size, weights, theme="Chapter 2"):
    """
    Enhanced version of your existing generate function
    Now includes complete UEFN Verse package
    """
    # Your existing generation code
    heightmap, normalized = create_perlin_heightmap(seed, size, weights)
    biome_map = classify_biomes(normalized, theme)  # uses UEFN_THEMES
    plots_found = find_plots(normalized, world_size)
    town_center = generate_town_layout(plots_found)
    
    # Existing result assembly
    result = {
        "preview_b64": create_preview_image(normalized, biome_map),
        "plots_found": plots_found,
        "biome_stats": calculate_biome_stats(biome_map),
        "verse_constants": generate_verse_constants(plots_found, town_center),  # old single-file
        "town_center": town_center,
        "world_size_cm": world_size_to_cm(world_size),
        "heightmap_normalized": normalized,
        "biome_map": biome_map,
    }
    
    # NEW: Add complete Verse package
    result = integrate_with_forge(result, theme=theme, seed=seed)
    
    # result now has result["verse_package"] = {
    #     "plot_registry.verse": "...",
    #     "biome_manifest.verse": "...",
    #     "foliage_spawner.verse": "...",
    #     "poi_placer.verse": "...",
    #     "landscape_config.json": "...",
    #     "asset_manifest.json": "...",
    #     "README.md": "...",
    # }
    
    return result
'''

FRONTEND_INTEGRATION = '''
// ADD TO FRONTEND (index.html or forge template)
// After generation completes, offer Verse package download

async function downloadVersePackage() {
    const response = await fetch('/api/forge/download-verse', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            seed: currentSeed,
            theme: currentTheme
        })
    });
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `triptokforge_island_${currentSeed}.zip`;
    a.click();
}

// Add download button to forge UI
<button onclick="downloadVersePackage()" class="verse-download-btn">
    ↓ Download Complete UEFN Package
</button>
'''

ROUTE_HANDLER = '''
# ADD NEW ROUTE to islandforge/server.py or routes file:

@app.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    """Generate and return .zip of complete Verse package"""
    import io
    import zipfile
    from flask import send_file
    
    data = request.json
    seed = data.get('seed', 42)
    theme = data.get('theme', 'Chapter 2')
    
    # Get latest generation result (or re-generate)
    result = get_or_generate_island(seed, theme)
    
    # Create zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        verse_package = result.get('verse_package', {})
        
        for filename, content in verse_package.items():
            zf.writestr(filename, content)
        
        # Add heightmap PNG
        zf.writestr('heightmap.png', result['preview_b64'].decode('base64'))
    
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'triptokforge_island_{seed}.zip'
    )
'''

def apply_integration_patch():
    """
    Apply this patch to integrate Verse export into TriptokForge
    """
    print("TriptokForge UEFN Verse Integration Patch")
    print("=" * 60)
    
    print("\n1. BACKEND INTEGRATION")
    print("-" * 60)
    print(INTEGRATION_CODE)
    
    print("\n2. FRONTEND INTEGRATION")
    print("-" * 60)
    print(FRONTEND_INTEGRATION)
    
    print("\n3. ROUTE HANDLER")
    print("-" * 60)
    print(ROUTE_HANDLER)
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT STEPS:")
    print("=" * 60)
    print("""
1. Copy uefn_asset_catalog.py and verse_export_generator.py to islandforge/
2. Add imports and integrate_with_forge call to audio_to_heightmap.py
3. Add /api/forge/download-verse route to server.py
4. Add download button to forge frontend
5. Test: Generate island, click "Download UEFN Package", get .zip
6. Extract .zip, open UEFN project, copy .verse files to Verse folder
7. Import heightmap.png as landscape, apply materials
8. Build and run - props spawn at runtime!

The Verse package contains:
- plot_registry.verse (plot positions)
- biome_manifest.verse (biome zones)
- foliage_spawner.verse (runtime vegetation spawner)
- poi_placer.verse (procedural building system)  
- landscape_config.json (material assignments)
- asset_manifest.json (asset reference list)
- README.md (deployment guide)
- heightmap.png (16-bit grayscale)

All Epic asset references - 0 MB custom content cost!
""")


if __name__ == "__main__":
    apply_integration_patch()
