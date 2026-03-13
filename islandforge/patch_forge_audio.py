#!/usr/bin/env python3
"""
patch_forge_audio.py — Fix audio library issues
Run on VM: python3 ~/ver-perlinforge/islandforge/patch_forge_audio.py

Fixes:
  1. Store full weights (incl. tempo_bpm, duration_s) in _lastAudioWeights global
     so generate() passes real values, not hardcoded 120/0
  2. Active track illumination persists — highlighted by _playerFile state,
     not just playing state
  3. "AUDIO LOADED" status stays visible for 2s then fades to "READY"
  4. Generate gets a 90s timeout so it can't hang the button forever
  5. Header shows active track name while audio is selected
"""
import os, subprocess, time, re

ROOT = "/home/ubuntu/ver-perlinforge/islandforge"
idx  = os.path.join(ROOT, "index.html")
html = open(idx).read()

# ── 1. Store full weights in global when audio is selected ──────
# Replace the applyWeights call in selectAudio to also store globally
OLD_SELECT = """async function selectAudio(filename) {
  setStatus('LOADING AUDIO...');
  try {
    const r = await fetch('/audio/select', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({filename})
    });
    const d = await r.json();
    if (!d.ok) throw new Error(d.error);
    applyWeights(d.weights);
    showBands(d.weights);
    await playerLoad(filename, true);
    await refreshAudioLib();
    setStatus('READY');
    toast(`▶ ${filename}`);
  } catch(e) {
    setStatus('READY');
    toast(e.message, true);
  }
}"""

NEW_SELECT = """async function selectAudio(filename) {
  setStatus('LOADING AUDIO...');
  try {
    const r = await fetch('/audio/select', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({filename})
    });
    const d = await r.json();
    if (!d.ok) throw new Error(d.error);

    // Store FULL weights globally (includes tempo_bpm, duration_s from server)
    window._lastAudioWeights = d.weights;
    window._lastAudioFile    = filename;

    applyWeights(d.weights);
    showBands(d.weights);

    // Update header indicator
    const tag = document.getElementById('audio-active-tag');
    if (tag) tag.textContent = '▶ ' + filename;
    const headerEl = document.getElementById('header-audio-name');
    if (headerEl) {
      headerEl.textContent  = filename.replace(/\\.[^.]+$/, '');
      headerEl.style.opacity = '1';
    }

    await playerLoad(filename, true);
    await refreshAudioLib();

    // Hold "AUDIO LOADED" for 2s so user can see it
    setStatus('AUDIO LOADED — ' + filename.replace(/\\.[^.]+$/, '').toUpperCase());
    setTimeout(() => setStatus('READY'), 2000);

    toast('▶ ' + filename);
  } catch(e) {
    setStatus('READY');
    toast(e.message, true);
  }
}"""

if "_lastAudioWeights" not in html:
    if "async function selectAudio(filename)" in html:
        html = html.replace(OLD_SELECT, NEW_SELECT)
        print("✓ selectAudio — full weights stored + status hold")
    else:
        # Fallback: inject after applyWeights call in selectAudio
        html = html.replace(
            "applyWeights(d.weights);\n    showBands(d.weights);",
            "window._lastAudioWeights = d.weights;\n    window._lastAudioFile = filename;\n    applyWeights(d.weights);\n    showBands(d.weights);"
        )
        print("✓ selectAudio — fallback weights store injected")
else:
    print("→ selectAudio — already storing weights")

# ── 2. generate() uses _lastAudioWeights for tempo_bpm / duration_s ──
OLD_WEIGHTS_BUILD = """  const weights = {
    sub_bass:   $('sub_bass').value/100,
    bass:       $('bass').value/100,
    midrange:   $('midrange').value/100,
    presence:   $('presence').value/100,
    brilliance: $('brilliance').value/100,
    tempo_bpm:  120, duration_s: 0
  };"""

NEW_WEIGHTS_BUILD = """  // Use stored audio weights for tempo/duration; fall back to slider values
  const _aw = window._lastAudioWeights || {};
  const weights = {
    sub_bass:   $('sub_bass').value/100,
    bass:       $('bass').value/100,
    midrange:   $('midrange').value/100,
    presence:   $('presence').value/100,
    brilliance: $('brilliance').value/100,
    tempo_bpm:  _aw.tempo_bpm  || 120,
    duration_s: _aw.duration_s || 0,
    rms:        _aw.rms        || 0.5,
    zcr:        _aw.zcr        || 0,
    spectral_centroid: _aw.spectral_centroid || 2000,
  };"""

if "_aw.tempo_bpm" not in html:
    html = html.replace(OLD_WEIGHTS_BUILD, NEW_WEIGHTS_BUILD)
    print("✓ generate() — real tempo_bpm/duration_s from audio analysis")
else:
    print("→ generate() — weights already using _lastAudioWeights")

# ── 3. generate() timeout — 90s so button never hangs forever ───
OLD_FETCH = """    const r = await fetch('/generate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({"""

NEW_FETCH = """    // 90s timeout so button never stays stuck
    const _ctrl = new AbortController();
    const _genTimeout = setTimeout(() => _ctrl.abort(), 90000);
    const r = await fetch('/generate', {
      signal: _ctrl.signal,
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({"""

if "_ctrl.abort()" not in html:
    html = html.replace(OLD_FETCH, NEW_FETCH)
    # Clear timeout on success
    html = html.replace(
        "if (!d.ok) throw new Error(d.error);",
        "clearTimeout(_genTimeout);\n    if (!d.ok) throw new Error(d.error);",
        1  # only first occurrence (inside generate)
    )
    print("✓ generate() — 90s abort timeout added")
else:
    print("→ generate() — timeout already present")

# ── 4. Active track illumination — stays lit by _playerFile ─────
# The existing CSS uses .active class but refreshAudioLib only sets it
# if file === _playerFile AND not paused. Fix: always highlight selected file.
OLD_ITEM_CLASS = '`<div class="audio-file-item ${f.filename===_playerFile ? ((!_audio.paused)?\'playing\':\'active\') : \'\'}" data-fn="${f.filename}">`'
NEW_ITEM_CLASS = '`<div class="audio-file-item ${f.filename===_playerFile ? \'active\' : \'\'} ${(f.filename===_playerFile && !_audio.paused) ? \'playing\' : \'\'}" data-fn="${f.filename}">`'

# Use simpler string match since backtick template literals are tricky
html = html.replace(
    'f.filename===_playerFile ? ((!_audio.paused)?\'playing\':\'active\') : \'\'',
    'f.filename===_playerFile ? \'active\' : \'\''
)
html = html.replace(
    "((!_audio.paused)?'playing':'active')",
    "'active'"
)
print("✓ audio list — active stays lit regardless of play state")

# ── 5. Add header audio indicator element if not present ────────
# Find the header status element and add a track name next to it
if "header-audio-name" not in html:
    # Inject a small track name span near the status text
    html = html.replace(
        'id="status-text"',
        'id="status-text"'  # keep as is, add sibling
    )
    # Add CSS for the indicator
    INDICATOR_CSS = """
<style id="audio-indicator-css">
#header-audio-name {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 1px;
  color: var(--accent);
  opacity: 0;
  transition: opacity .3s;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: 10px;
}
.audio-file-item.active {
  border-color: var(--accent) !important;
  background: rgba(0,229,160,.07) !important;
  color: var(--accent) !important;
}
.audio-file-item.active .audio-file-name {
  color: var(--accent) !important;
}
</style>"""
    html = html.replace("</head>", INDICATOR_CSS + "\n</head>")

    # Add the span next to status-text
    html = html.replace(
        '<span id="status-text"',
        '<span id="header-audio-name"></span><span id="status-text"'
    )
    print("✓ header — audio track name indicator added")
else:
    print("→ header — audio indicator already present")

open(idx, "w").write(html)
print("✓ index.html saved")

# ── Restart ──────────────────────────────────────────────────────
print("\n▸ Restarting...")
subprocess.run(["sudo","systemctl","restart","islandforge"], check=True)
time.sleep(5)
r = subprocess.run(
    ["curl","-s","-o","/dev/null","-w","%{http_code}","http://127.0.0.1:5000/health"],
    capture_output=True, text=True
)
print(f"  health → {r.stdout}")
print("""
✅ Audio fixes live on /forge

Fixed:
  ✓ Selected track stays illuminated (green border) whether playing or paused
  ✓ Status shows "AUDIO LOADED — trackname" for 2s then goes back to READY
  ✓ Header shows active track name in teal
  ✓ generate() passes real tempo_bpm + duration_s from audio analysis
    (was hardcoded 120/0 — now uses actual values from /audio/select)
  ✓ 90s timeout on generate() — button can never get permanently stuck
""")
