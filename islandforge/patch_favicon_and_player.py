#!/usr/bin/env python3
"""
patch_favicon_and_player.py
Run from islandforge/:
    python3 patch_favicon_and_player.py

What it does:
  1. Writes favicon.svg into static/
  2. Patches favicon <link> tags into templates/forge.html <head>
  3. Patches forge player bar before </body> in templates/forge.html
  4. Patches favicon route + static folder into server.py
  5. Restarts service and health checks
"""

import os, shutil, subprocess, time

ROOT     = os.path.dirname(os.path.abspath(__file__))
SERVER   = os.path.join(ROOT, "server.py")
FORGE    = os.path.join(ROOT, "templates", "forge.html")
STATIC   = os.path.join(ROOT, "static")
FAVICON  = os.path.join(STATIC, "favicon.svg")

# ── STEP 1: WRITE FAVICON ───────────────────────────────────────
os.makedirs(STATIC, exist_ok=True)

FAVICON_SVG = """<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <rect width="256" height="256" rx="44" fill="#07090d"/>
  <line x1="148" y1="38"  x2="252" y2="26"  stroke="#00e5a0" stroke-width="1.5" opacity="0.22"/>
  <line x1="152" y1="50"  x2="252" y2="42"  stroke="#00e5a0" stroke-width="0.8" opacity="0.13"/>
  <line x1="150" y1="205" x2="252" y2="220" stroke="#0091ff" stroke-width="1.5" opacity="0.22"/>
  <line x1="155" y1="218" x2="252" y2="234" stroke="#0091ff" stroke-width="0.8" opacity="0.13"/>
  <polygon points="128,58 160,105 96,105" fill="none" stroke="#00e5a0" stroke-width="1" opacity="0.08"/>
  <polygon points="36,32 208,32 220,44 220,212 208,224 36,224 24,212 24,44" fill="#0d1018" stroke="#1a2535" stroke-width="1.5"/>
  <rect x="44" y="62" width="168" height="34" fill="#00e5a0"/>
  <rect x="99" y="96" width="58" height="100" fill="#00e5a0"/>
  <polygon points="82,62 118,62 156,130 120,130" fill="#07090d"/>
  <rect x="99" y="130" width="58" height="66" fill="#00e5a0"/>
  <rect x="44" y="196" width="168" height="10" fill="#0091ff"/>
  <rect x="44" y="206" width="80" height="4" fill="#0091ff" opacity="0.4"/>
  <rect x="24" y="24" width="14" height="4" fill="#00e5a0"/>
  <rect x="24" y="24" width="4" height="14" fill="#00e5a0"/>
  <rect x="218" y="228" width="14" height="4" fill="#0091ff"/>
  <rect x="228" y="218" width="4" height="14" fill="#0091ff"/>
  <line x1="212" y1="90"  x2="220" y2="90"  stroke="#00e5a0" stroke-width="2.5" opacity="0.55"/>
  <line x1="214" y1="100" x2="220" y2="100" stroke="#00e5a0" stroke-width="1.5" opacity="0.35"/>
  <line x1="216" y1="110" x2="220" y2="110" stroke="#00e5a0" stroke-width="1"   opacity="0.2"/>
</svg>"""

with open(FAVICON, "w") as f:
    f.write(FAVICON_SVG)
print(f"✓ Wrote static/favicon.svg")

# ── STEP 2: PATCH forge.html HEAD ──────────────────────────────
FAVICON_TAGS = """    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg"/>
    <link rel="shortcut icon" href="/static/favicon.svg"/>
    <link rel="apple-touch-icon" href="/static/favicon.svg"/>
    <meta name="theme-color" content="#07090d"/>"""

with open(FORGE, "r") as f:
    forge = f.read()

if 'favicon.svg' in forge:
    print("✓ Favicon tags already in forge.html — skipping")
else:
    forge = forge.replace(
        '<meta name="viewport"',
        FAVICON_TAGS + '\n    <meta name="viewport"'
    )
    print("✓ Patched favicon tags into forge.html <head>")

# ── STEP 3: PATCH FORGE PLAYER BAR ─────────────────────────────
PLAYER_HTML = """
<!-- ── FORGE PERSISTENT PLAYER ─────────────────────────────── -->
<style>
#forge-player{position:fixed;bottom:0;left:0;right:0;height:62px;background:#0d1018;border-top:1px solid #1e2330;display:flex;align-items:center;gap:12px;padding:0 18px;z-index:9999;transform:translateY(100%);transition:transform .35s cubic-bezier(.4,0,.2,1),opacity .4s;opacity:1}
#forge-player.visible{transform:translateY(0)}
#forge-player.idle{opacity:.2}
#forge-player:hover{opacity:1!important}
#fp-track{flex:1;font-size:.75rem;color:#00e5a0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;font-family:'Share Tech Mono',monospace}
.fp-btn{background:none;border:none;color:#bbb;font-size:1rem;cursor:pointer;padding:4px 6px;border-radius:4px;transition:color .15s,background .15s;flex-shrink:0}
.fp-btn:hover{color:#00e5a0;background:#1e2330}
#fp-play{font-size:1.2rem;color:#00e5a0}
#fp-scrubber{flex:2;min-width:80px;max-width:340px;accent-color:#00e5a0;cursor:pointer}
#fp-vol{width:70px;accent-color:#0091ff;cursor:pointer;flex-shrink:0}
.fp-time{font-size:.68rem;color:#555;flex-shrink:0;font-family:'Share Tech Mono',monospace;min-width:36px}
</style>
<div id="forge-player">
  <span id="fp-track">No track loaded</span>
  <button class="fp-btn" id="fp-prev" title="Previous">&#9198;</button>
  <button class="fp-btn" id="fp-play" title="Play / Pause">&#9654;</button>
  <button class="fp-btn" id="fp-next" title="Next">&#9197;</button>
  <span class="fp-time" id="fp-cur">0:00</span>
  <input type="range" id="fp-scrubber" min="0" max="100" value="0" step="0.1"/>
  <span class="fp-time" id="fp-dur">0:00</span>
  <input type="range" id="fp-vol" min="0" max="1" value="0.8" step="0.01" title="Volume"/>
</div>
<script>
(function(){
  var bar=document.getElementById('forge-player');
  var btnPlay=document.getElementById('fp-play');
  var btnPrev=document.getElementById('fp-prev');
  var btnNext=document.getElementById('fp-next');
  var scrubber=document.getElementById('fp-scrubber');
  var volSlider=document.getElementById('fp-vol');
  var trackLbl=document.getElementById('fp-track');
  var curLbl=document.getElementById('fp-cur');
  var durLbl=document.getElementById('fp-dur');
  var audio=new Audio();
  audio.volume=0.8;
  window.globalAudio=audio;
  var trackList=[];
  var trackIndex=-1;
  function fmt(s){var m=Math.floor(s/60);return m+':'+(Math.floor(s%60)).toString().padStart(2,'0');}
  var idleTimer;
  function resetIdle(){bar.classList.remove('idle');clearTimeout(idleTimer);idleTimer=setTimeout(function(){bar.classList.add('idle');},4000);}
  bar.addEventListener('mouseenter',resetIdle);
  function showBar(){bar.classList.add('visible');resetIdle();}
  function loadIndex(idx){
    if(!trackList.length)return;
    trackIndex=(idx+trackList.length)%trackList.length;
    var t=trackList[trackIndex];
    audio.src=t.url;trackLbl.textContent=t.name;
    audio.play();btnPlay.innerHTML='&#9646;&#9646;';showBar();
    document.querySelectorAll('.track-row').forEach(function(r,i){r.classList.toggle('active',i===trackIndex);});
  }
  var _orig=window.loadTrack;
  window.loadTrack=function(url,name){
    trackList=[];
    document.querySelectorAll('.track-row[data-url]').forEach(function(r){trackList.push({url:r.dataset.url,name:r.dataset.name||r.textContent.trim()});});
    var idx=trackList.findIndex(function(t){return t.url===url;});
    if(idx>=0){loadIndex(idx);}else{audio.src=url;trackLbl.textContent=name||url;audio.play();btnPlay.innerHTML='&#9646;&#9646;';showBar();}
    if(_orig)_orig(url,name);
  };
  btnPlay.addEventListener('click',function(){
    if(audio.paused){audio.play();btnPlay.innerHTML='&#9646;&#9646;';}
    else{audio.pause();btnPlay.innerHTML='&#9654;';}
    resetIdle();
  });
  btnNext.addEventListener('click',function(){loadIndex(trackIndex+1);resetIdle();});
  btnPrev.addEventListener('click',function(){loadIndex(trackIndex-1);resetIdle();});
  var scrubbing=false;
  scrubber.addEventListener('mousedown',function(){scrubbing=true;});
  scrubber.addEventListener('mouseup',function(){audio.currentTime=(scrubber.value/100)*audio.duration;scrubbing=false;});
  audio.addEventListener('timeupdate',function(){if(!scrubbing&&audio.duration){scrubber.value=(audio.currentTime/audio.duration)*100;curLbl.textContent=fmt(audio.currentTime);}});
  audio.addEventListener('loadedmetadata',function(){durLbl.textContent=fmt(audio.duration);});
  audio.addEventListener('ended',function(){loadIndex(trackIndex+1);});
  volSlider.addEventListener('input',function(){audio.volume=volSlider.value;resetIdle();});
})();
</script>"""

if 'forge-player' in forge:
    print("✓ Forge player already in forge.html — skipping")
else:
    forge = forge.replace('</body>', PLAYER_HTML + '\n</body>')
    print("✓ Patched forge player bar into forge.html")

with open(FORGE, "w") as f:
    f.write(forge)

# ── STEP 4: PATCH server.py ─────────────────────────────────────
shutil.copy2(SERVER, SERVER + ".bak3")

with open(SERVER, "r") as f:
    src = f.read()

# Add static_folder and favicon route if not there
if "send_from_directory" not in src:
    # Add import
    src = src.replace(
        "from flask import",
        "from flask import send_from_directory,"
    )
    print("✓ Added send_from_directory import to server.py")

if "favicon.svg" not in src:
    FAVICON_ROUTE = """
# ── FAVICON ──────────────────────────────────────────────────────
@app.route('/favicon.svg')
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.svg', mimetype='image/svg+xml')

"""
    # Insert before the last route or errorhandler
    if '@app.errorhandler' in src:
        src = src.replace('@app.errorhandler', FAVICON_ROUTE + '@app.errorhandler')
    else:
        src = src + FAVICON_ROUTE
    print("✓ Added favicon route to server.py")
else:
    print("✓ Favicon route already in server.py — skipping")

# Make sure Flask app has static_folder set
if "static_folder" not in src:
    src = src.replace(
        "Flask(__name__)",
        "Flask(__name__, static_folder='static', static_url_path='/static')"
    )
    print("✓ Added static_folder to Flask app init")
else:
    print("✓ static_folder already set")

with open(SERVER, "w") as f:
    f.write(src)

# ── STEP 5: RESTART ─────────────────────────────────────────────
print("\n▸ Restarting service...")
subprocess.run(["sudo", "systemctl", "restart", "islandforge"], check=True)
time.sleep(4)

result = subprocess.run(
    ["curl", "-s", "http://127.0.0.1:5000/health"],
    capture_output=True, text=True)

if result.returncode == 0 and result.stdout:
    print(f"✓ ONLINE: {result.stdout[:120]}")
    print("\n✅ Done!")
    print("   → triptokforge.org/forge  (bottom player bar)")
    print("   → Browser tab should now show the favicon")
else:
    print("✗ Not responding — checking logs...")
    subprocess.run(["sudo", "journalctl", "-u", "islandforge", "-n", "8", "--no-pager"])
    print(f"\n⚠ Restore: cp server.py.bak3 server.py && sudo systemctl restart islandforge")
