"""
channels_page.py — TriptokForge Live Channels
Roku-style TV guide with working Twitch/YouTube/Kick embeds.
Design tokens match triptokforge.css exactly.
"""
from collections import OrderedDict


def _detect_embed(url: str) -> str:
    """Convert stream URL to embeddable iframe src."""
    if not url:
        return ""
    u = url.strip()

    # Twitch channel  e.g. https://twitch.tv/ninja
    if "twitch.tv/" in u and "/videos/" not in u:
        channel = u.split("twitch.tv/")[-1].split("?")[0].split("/")[0]
        return f"https://player.twitch.tv/?channel={channel}&parent=triptokforge.org&autoplay=false&muted=false"

    # Twitch VOD
    if "twitch.tv/videos/" in u:
        vid = u.split("/videos/")[-1].split("?")[0]
        return f"https://player.twitch.tv/?video={vid}&parent=triptokforge.org&autoplay=false"

    # YouTube watch
    if "youtube.com/watch" in u:
        vid = ""
        for part in u.split("?")[-1].split("&"):
            if part.startswith("v="):
                vid = part[2:]
        if vid:
            return f"https://www.youtube.com/embed/{vid}?autoplay=0"

    # YouTube short URL
    if "youtu.be/" in u:
        vid = u.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{vid}?autoplay=0"

    # YouTube live / channel page — link-out only
    if "youtube.com/@" in u or "youtube.com/c/" in u or "youtube.com/channel/" in u:
        return u

    # Kick
    if "kick.com/" in u:
        channel = u.split("kick.com/")[-1].split("?")[0].split("/")[0]
        return f"https://player.kick.com/{channel}?autoplay=false"

    # Streamable
    if "streamable.com/" in u:
        vid = u.split("streamable.com/")[-1].split("?")[0]
        return f"https://streamable.com/e/{vid}"

    # Already an embed or unknown — pass through
    return u


def build_channels_page(channels: list) -> str:
    groups: dict = OrderedDict()
    for ch in channels:
        cat = ch.get("category", "Other")
        groups.setdefault(cat, []).append(ch)

    icons = {
        "Fortnite Competitive":        "⬡",
        "Game Developers":             "◈",
        "Esports":                     "◉",
        "Creative / UEFN":             "△",
        "Chill / Music":               "♫",
        "Gaming News":                 "◇",
    }

    guide_items = ""
    for cat, items in groups.items():
        icon = icons.get(cat, "▶")
        rows_html = ""
        for ch in items:
            name      = ch.get("name", "Unnamed")
            desc      = ch.get("description", "")
            raw_url   = ch.get("embed_url", "")
            embed     = _detect_embed(raw_url)
            safe_name = name.replace("'", "\\'").replace('"', "&quot;")
            safe_embed = embed.replace("'", "\\'")
            rows_html += f"""
          <div class="ch-row" onclick="loadChannel('{safe_embed}','{safe_name}')"
               data-url="{embed}" data-name="{safe_name}">
            <span class="ch-live"></span>
            <div class="ch-info">
              <span class="ch-name">{name}</span>
              <span class="ch-desc">{desc}</span>
            </div>
            <span class="ch-arr">▶</span>
          </div>"""

        guide_items += f"""
        <div class="cat-section">
          <div class="cat-hd" onclick="toggleCat(this)">
            <span class="cat-ic">{icon}</span>
            <span class="cat-nm">{cat}</span>
            <span class="cat-ct">{len(items)}</span>
            <span class="cat-toggle">▾</span>
          </div>
          <div class="cat-body">{rows_html}</div>
        </div>"""

    total = len(channels)
    ncats = len(groups)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Live Channels — TriptokForge</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/static/triptokforge.css"/>
<style>
:root{{
  --bg:#07090d;--deep:#04060a;--panel:#0d1018;
  --border:#1a2535;--border2:#243040;
  --teal:#00e5a0;--teal-dim:rgba(0,229,160,.1);
  --blue:#0091ff;--amber:#ffaa00;
  --text:#c8d8e8;--mid:#7a8aa8;--dim:#3a4a60;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'Rajdhani',sans-serif}}
nav{{position:fixed;top:0;left:0;right:0;z-index:200;height:56px;display:flex;align-items:center;
     padding:0 32px;background:rgba(7,9,13,.96);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}}
.nav-logo{{font-family:'Orbitron',monospace;font-size:13px;font-weight:900;color:var(--teal);letter-spacing:3px;text-decoration:none}}
.nav-logo em{{color:var(--blue);font-style:normal}}
.nav-links{{display:flex;gap:4px;margin-left:24px}}
.nav-links a{{font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:2px;text-transform:uppercase;
              padding:5px 10px;border-radius:3px;color:var(--dim);text-decoration:none;transition:all .15s}}
.nav-links a:hover{{color:var(--teal);background:var(--teal-dim)}}
.nav-r{{margin-left:auto;display:flex;gap:16px}}
.nav-r a{{color:var(--dim);text-decoration:none;font-family:'Share Tech Mono',monospace;font-size:.58rem;
          letter-spacing:2px;text-transform:uppercase;transition:color .15s}}
.nav-r a:hover{{color:var(--teal)}}
.ch-shell{{display:flex;height:calc(100vh - 56px);margin-top:56px;overflow:hidden}}
.ch-guide{{width:290px;min-width:200px;flex-shrink:0;display:flex;flex-direction:column;
           background:var(--panel);border-right:1px solid var(--border);overflow:hidden}}
.guide-header{{padding:12px 16px 10px;border-bottom:1px solid var(--border);flex-shrink:0}}
.guide-title{{font-family:'Orbitron',monospace;font-size:.7rem;font-weight:700;letter-spacing:3px;
              text-transform:uppercase;color:var(--teal);margin-bottom:2px}}
.guide-sub{{font-family:'Share Tech Mono',monospace;font-size:.55rem;letter-spacing:2px;color:var(--dim)}}
.guide-search{{padding:10px 12px;border-bottom:1px solid var(--border);flex-shrink:0}}
.guide-search input{{width:100%;background:rgba(0,229,160,.05);border:1px solid var(--border2);
  color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:7px 12px;
  outline:none;border-radius:2px;letter-spacing:1px}}
.guide-search input:focus{{border-color:var(--teal)}}
.guide-search input::placeholder{{color:var(--dim)}}
.guide-scroll{{flex:1;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}}
.guide-scroll::-webkit-scrollbar{{width:4px}}
.guide-scroll::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:2px}}
.cat-hd{{display:flex;align-items:center;gap:8px;padding:9px 14px;cursor:pointer;
         border-bottom:1px solid var(--border);transition:background .12s;user-select:none}}
.cat-hd:hover{{background:rgba(0,229,160,.04)}}
.cat-ic{{font-size:.75rem;width:16px;text-align:center;color:var(--teal);flex-shrink:0}}
.cat-nm{{flex:1;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:2px;text-transform:uppercase;color:var(--mid)}}
.cat-ct{{font-family:'Share Tech Mono',monospace;font-size:.52rem;color:var(--dim);background:var(--border);padding:2px 6px;border-radius:2px}}
.cat-toggle{{font-size:.6rem;color:var(--dim);transition:transform .2s;margin-left:4px}}
.cat-body{{overflow:hidden;transition:max-height .25s ease}}
.cat-body.collapsed{{max-height:0!important}}
.cat-hd.collapsed .cat-toggle{{transform:rotate(-90deg)}}
.ch-row{{display:flex;align-items:center;gap:10px;padding:8px 14px 8px 24px;cursor:pointer;
         border-bottom:1px solid rgba(26,37,53,.5);border-left:3px solid transparent;transition:all .1s}}
.ch-row:hover{{background:rgba(0,229,160,.04);border-left-color:var(--border2)}}
.ch-row.active{{background:rgba(0,229,160,.08);border-left-color:var(--teal)}}
.ch-live{{width:6px;height:6px;border-radius:50%;flex-shrink:0;background:var(--dim);transition:background .2s}}
.ch-row.active .ch-live{{background:var(--teal);box-shadow:0 0 6px var(--teal)}}
.ch-info{{flex:1;min-width:0}}
.ch-name{{display:block;font-size:.78rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.ch-desc{{display:block;font-size:.6rem;color:var(--dim);font-family:'Share Tech Mono',monospace;letter-spacing:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
.ch-arr{{font-size:.6rem;color:var(--dim);flex-shrink:0;transition:color .15s}}
.ch-row:hover .ch-arr,.ch-row.active .ch-arr{{color:var(--teal)}}
.suggest-wrap{{padding:12px;border-top:1px solid var(--border);flex-shrink:0;background:var(--panel)}}
.suggest-toggle{{font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:2px;text-transform:uppercase;color:var(--mid);cursor:pointer;transition:color .15s;padding:4px 0}}
.suggest-toggle:hover{{color:var(--teal)}}
#suggest-form{{margin-top:8px;display:flex;flex-direction:column;gap:5px}}
#suggest-form input{{background:rgba(0,229,160,.04);border:1px solid var(--border2);color:var(--text);
  font-family:'Share Tech Mono',monospace;font-size:.58rem;padding:6px 10px;outline:none;border-radius:2px;letter-spacing:1px}}
#suggest-form input:focus{{border-color:var(--teal)}}
#suggest-form input::placeholder{{color:var(--dim)}}
#suggest-form button{{background:var(--teal);color:#000;border:none;font-family:'Orbitron',monospace;
  font-size:.58rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:7px;cursor:pointer;transition:background .15s}}
#suggest-form button:hover{{background:#fff}}
.ch-main{{flex:1;display:flex;flex-direction:column;overflow:hidden;background:var(--deep)}}
.ch-toolbar{{padding:10px 16px;border-bottom:1px solid var(--border);background:var(--panel);flex-shrink:0;display:flex;align-items:center;gap:12px}}
.ch-now-playing{{font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:2px;text-transform:uppercase;color:var(--teal);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tb-btn{{font-family:'Share Tech Mono',monospace;font-size:.55rem;letter-spacing:2px;text-transform:uppercase;padding:5px 12px;background:rgba(0,229,160,.06);border:1px solid var(--border2);color:var(--mid);cursor:pointer;transition:all .15s;border-radius:2px}}
.tb-btn:hover,.tb-btn.on{{border-color:var(--teal);color:var(--teal);background:var(--teal-dim)}}
.ch-player{{flex:1;position:relative;overflow:hidden;background:#000}}
#ch-iframe{{width:100%;height:100%;border:none;display:block}}
.ch-placeholder{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;background:var(--deep)}}
.ph-icon{{font-family:'Orbitron',monospace;font-size:3.5rem;font-weight:900;color:rgba(0,229,160,.07);letter-spacing:4px}}
.ph-text{{font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:3px;text-transform:uppercase;color:var(--dim)}}
.ph-hint{{font-family:'Rajdhani',sans-serif;font-size:.85rem;color:var(--dim);font-weight:300}}
.player-controls{{padding:8px 16px;border-top:1px solid var(--border);background:var(--panel);flex-shrink:0;display:flex;align-items:center;gap:10px}}
.vol-label{{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:2px;color:var(--dim);text-transform:uppercase;flex-shrink:0}}
.vol-slider{{flex:1;max-width:130px;accent-color:var(--teal);cursor:pointer}}
.pc-btn{{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:2px;text-transform:uppercase;padding:4px 10px;background:rgba(0,229,160,.04);border:1px solid var(--border2);color:var(--mid);cursor:pointer;transition:all .15s;border-radius:2px}}
.pc-btn:hover{{border-color:var(--teal);color:var(--teal)}}
.pc-btn.muted{{color:var(--amber);border-color:var(--amber)}}
.link-out{{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:2px;text-transform:uppercase;padding:4px 10px;background:rgba(0,145,255,.05);border:1px solid var(--border2);color:var(--mid);transition:all .15s;border-radius:2px;text-decoration:none}}
.link-out:hover{{border-color:var(--blue);color:var(--blue)}}
.fs-btn{{margin-left:auto;font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:2px;text-transform:uppercase;padding:4px 10px;background:rgba(0,145,255,.05);border:1px solid var(--border2);color:var(--mid);cursor:pointer;transition:all .15s;border-radius:2px}}
.fs-btn:hover{{border-color:var(--blue);color:var(--blue)}}
@media(max-width:768px){{.ch-guide{{width:220px}}.nav-links{{display:none}}nav{{padding:0 14px}}}}
</style>
</head>
<body>
<nav>
  <a href="/home" class="nav-logo">Triptok<em>Forge</em></a>
  <div class="nav-links">
    <a href="/home">Home</a>
    <a href="/forge">Forge</a>
    <a href="/feed">Feed</a>
    <a href="/room">My Room</a>
    <a href="/community">Community</a>
  </div>
  <div class="nav-r">
    <a href="/dashboard">Dashboard</a>
  </div>
</nav>

<div class="ch-shell">
  <div class="ch-guide">
    <div class="guide-header">
      <div class="guide-title">Live Channels</div>
      <div class="guide-sub">{total} channels &middot; {ncats} categories</div>
    </div>
    <div class="guide-search">
      <input type="text" id="ch-search" placeholder="Search channels..." oninput="filterChannels(this.value)"/>
    </div>
    <div class="guide-scroll" id="guideScroll">
      {guide_items}
    </div>
    <div class="suggest-wrap">
      <div class="suggest-toggle" onclick="toggleSuggest()">&#8853; Suggest a Channel</div>
      <div id="suggest-form" style="display:none">
        <input id="sg-name" type="text" placeholder="Channel name"/>
        <input id="sg-cat"  type="text" placeholder="Category"/>
        <input id="sg-url"  type="text" placeholder="Twitch / YouTube / Kick URL"/>
        <input id="sg-desc" type="text" placeholder="Short description"/>
        <button onclick="submitSuggest()">Submit</button>
        <div id="sg-msg" style="font-family:'Share Tech Mono',monospace;font-size:.55rem;margin-top:5px;display:none"></div>
      </div>
    </div>
  </div>

  <div class="ch-main">
    <div class="ch-toolbar">
      <span class="ch-now-playing" id="nowPlaying">Select a channel &#8594;</span>
      <button class="tb-btn" id="theaterBtn" onclick="toggleTheater()">Theater</button>
    </div>
    <div class="ch-player" id="chPlayer">
      <div class="ch-placeholder" id="placeholder">
        <div class="ph-icon">TF</div>
        <div class="ph-text">No Channel Selected</div>
        <div class="ph-hint">Pick a stream from the guide</div>
      </div>
      <iframe id="ch-iframe" src="" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen style="display:none"></iframe>
    </div>
    <div class="player-controls">
      <span class="vol-label">Vol</span>
      <input type="range" class="vol-slider" id="volSlider" min="0" max="100" value="80"/>
      <button class="pc-btn" id="muteBtn" onclick="toggleMute()">Mute</button>
      <a id="linkOut" class="link-out" href="#" target="_blank" rel="noopener">Open &#8599;</a>
      <button class="fs-btn" onclick="goFullscreen()">&#9633; Fullscreen</button>
    </div>
  </div>
</div>

<script>
let currentUrl='', currentRaw='', muted=false, theater=false;

function loadChannel(url, name) {{
  if (!url) return;
  currentUrl = url; currentRaw = url;
  document.getElementById('nowPlaying').textContent = '&#9654; ' + name;
  document.getElementById('placeholder').style.display = 'none';
  const iframe = document.getElementById('ch-iframe');
  iframe.style.display = 'block';
  iframe.src = muted ? (url + (url.includes('?')?'&':'?') + 'muted=true') : url;
  // link-out best guess
  let lo = url;
  const tch = url.match(/channel=([^&]+)/);
  if (tch) lo = 'https://twitch.tv/' + tch[1];
  const yt = url.match(/youtube\.com\/embed\/([^?]+)/);
  if (yt) lo = 'https://youtu.be/' + yt[1];
  document.getElementById('linkOut').href = lo;
  document.querySelectorAll('.ch-row').forEach(r => r.classList.toggle('active', r.dataset.name===name));
}}

function toggleMute() {{
  muted = !muted;
  const btn = document.getElementById('muteBtn');
  btn.textContent = muted ? 'Unmute' : 'Mute';
  btn.classList.toggle('muted', muted);
  if (currentUrl) {{
    const iframe = document.getElementById('ch-iframe');
    iframe.src = muted ? (currentUrl+(currentUrl.includes('?')?'&':'?')+'muted=true') : currentUrl;
  }}
}}

function goFullscreen() {{
  const p = document.getElementById('chPlayer');
  (p.requestFullscreen||p.webkitRequestFullscreen).call(p);
}}

function toggleTheater() {{
  theater = !theater;
  document.querySelector('.ch-guide').style.display = theater?'none':'';
  document.getElementById('theaterBtn').classList.toggle('on', theater);
}}

function toggleCat(hd) {{
  hd.classList.toggle('collapsed');
  const body = hd.nextElementSibling;
  if (body.classList.contains('collapsed')) {{
    body.style.maxHeight = body.scrollHeight + 'px';
    body.classList.remove('collapsed');
  }} else {{
    body.style.maxHeight = body.scrollHeight + 'px';
    requestAnimationFrame(() => {{ body.style.maxHeight = '0'; body.classList.add('collapsed'); }});
  }}
}}

function filterChannels(q) {{
  const ql = q.toLowerCase();
  document.querySelectorAll('.ch-row').forEach(r => {{
    r.style.display = (!ql || r.dataset.name.toLowerCase().includes(ql)) ? '' : 'none';
  }});
  if (ql) document.querySelectorAll('.cat-body').forEach(b => {{ b.style.maxHeight='none'; b.classList.remove('collapsed'); b.previousElementSibling.classList.remove('collapsed'); }});
}}

function toggleSuggest() {{
  const f = document.getElementById('suggest-form');
  f.style.display = f.style.display==='none' ? 'flex' : 'none';
}}

async function submitSuggest() {{
  const name=document.getElementById('sg-name').value.trim();
  const cat=document.getElementById('sg-cat').value.trim();
  const url=document.getElementById('sg-url').value.trim();
  const desc=document.getElementById('sg-desc').value.trim();
  if (!name||!url) {{ alert('Name and URL required.'); return; }}
  const msg = document.getElementById('sg-msg');
  try {{
    const r = await fetch('/api/suggest_channel',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name,category:cat||'Other',embed_url:url,description:desc}})}});
    const d = await r.json();
    msg.textContent = d.ok ? '&#10003; Submitted for review!' : (d.error||'Error');
    msg.style.display='block'; msg.style.color = d.ok?'var(--teal)':'var(--amber)';
    if(d.ok) ['sg-name','sg-cat','sg-url','sg-desc'].forEach(id=>document.getElementById(id).value='');
  }} catch(e) {{ msg.textContent='Network error.'; msg.style.display='block'; msg.style.color='var(--amber)'; }}
}}

// Init cat-body heights for animation
document.querySelectorAll('.cat-body').forEach(b => {{ b.style.maxHeight = b.scrollHeight + 'px'; }});
</script>
</body>
</html>"""
