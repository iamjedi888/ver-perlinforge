"""
channels_page.py — TriptokForge Live Channels
Iron Man JARVIS holographic player + Fortnite futuristic right-side channel guide.
Sidebar: right-side slide panel, collapsible categories, theater mode hides it.
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
        "Fortnite Competitive": "⬡",
        "Game Developers":      "◈",
        "Esports":              "◉",
        "Creative / UEFN":      "△",
        "Chill / Music":        "♫",
        "Gaming News":          "◇",
    }

    guide_items = ""
    for cat, items in groups.items():
        icon = icons.get(cat, "▶")
        rows_html = ""
        for ch in items:
            name       = ch.get("name", "Unnamed")
            desc       = ch.get("description", "")
            raw_url    = ch.get("embed_url", "")
            embed      = _detect_embed(raw_url)
            safe_name  = name.replace("'", "\\'").replace('"', "&quot;")
            safe_embed = embed.replace("'", "\\'")
            rows_html += f"""
          <div class="ch-row" onclick="loadChannel('{safe_embed}','{safe_name}')"
               data-url="{embed}" data-name="{safe_name}">
            <span class="ch-live-dot"></span>
            <div class="ch-info">
              <span class="ch-name">{name}</span>
              <span class="ch-desc">{desc}</span>
            </div>
            <span class="ch-arr">&#9654;</span>
          </div>"""

        guide_items += f"""
        <div class="cat-section" data-cat="{cat}">
          <div class="cat-hd" onclick="toggleCat(this)">
            <span class="cat-ic">{icon}</span>
            <span class="cat-nm">{cat}</span>
            <span class="cat-ct">{len(items)}</span>
            <span class="cat-chevron">&#9660;</span>
          </div>
          <div class="cat-body">{rows_html}
          </div>
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
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/static/triptokforge.css"/>
<style>
/* ── Design Tokens ───────────────────────────────────────────── */
:root {{
  --bg:        #07090d;
  --deep:      #04060a;
  --panel:     #0d1018;
  --panel2:    #111520;
  --border:    #1a2535;
  --border2:   #243040;
  --teal:      #00e5a0;
  --teal-dim:  rgba(0,229,160,.08);
  --teal-glow: rgba(0,229,160,.25);
  --blue:      #0091ff;
  --blue-dim:  rgba(0,145,255,.08);
  --blue-glow: rgba(0,145,255,.3);
  --jarvis:    #00eaff;
  --jarvis-dim:rgba(0,234,255,.08);
  --amber:     #ffaa00;
  --red:       #ff3355;
  --text:      #c8d8e8;
  --mid:       #7a8aa8;
  --dim:       #3a4a60;
  --nav-h:     56px;
}}

/* ── Reset ───────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; overflow: hidden; background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; }}

/* ── Nav ─────────────────────────────────────────────────────── */
nav.ch-nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 500;
  height: var(--nav-h);
  display: flex; align-items: center; padding: 0 28px;
  background: rgba(7,9,13,.96); backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--border);
}}
.nav-logo {{
  font-family: 'Orbitron', monospace; font-size: 13px; font-weight: 900;
  color: var(--teal); letter-spacing: 3px; text-decoration: none;
  transition: color .2s;
}}
.nav-logo:hover {{ color: var(--blue); }}
.nav-logo em {{ color: var(--blue); font-style: normal; }}
.ch-nav-links {{
  display: flex; gap: 2px; margin-left: 20px;
}}
.ch-nav-links a {{
  font-family: 'Share Tech Mono', monospace; font-size: .56rem;
  letter-spacing: 2px; text-transform: uppercase; padding: 5px 10px;
  border-radius: 3px; color: var(--dim); text-decoration: none; transition: all .15s;
}}
.ch-nav-links a:hover {{ color: var(--teal); background: var(--teal-dim); }}
.ch-nav-links a.active {{ color: var(--teal); }}
.nav-right {{
  margin-left: auto; display: flex; gap: 12px; align-items: center;
}}
.nav-right a {{
  font-family: 'Share Tech Mono', monospace; font-size: .56rem; letter-spacing: 2px;
  text-transform: uppercase; color: var(--mid); text-decoration: none; transition: color .15s;
  padding: 5px 10px; border-radius: 3px;
}}
.nav-right a:hover {{ color: var(--teal); background: var(--teal-dim); }}

/* ── Shell ───────────────────────────────────────────────────── */
.ch-shell {{
  display: flex; flex-direction: row;
  height: calc(100vh - var(--nav-h)); margin-top: var(--nav-h);
  overflow: hidden; position: relative;
}}

/* ── Main Player Area ────────────────────────────────────────── */
.ch-main {{
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
  background: var(--deep); position: relative;
}}

/* ── JARVIS HUD Readout ──────────────────────────────────────── */
.jarvis-hud {{
  display: flex; align-items: center; gap: 0;
  padding: 0 24px; height: 52px; flex-shrink: 0;
  background: rgba(0,145,255,.03);
  border-bottom: 1px solid rgba(0,145,255,.15);
  position: relative;
}}
.jarvis-hud::before {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,145,255,.4) 30%, rgba(0,234,255,.4) 70%, transparent);
}}
.hud-segment {{
  display: flex; flex-direction: column; justify-content: center; padding: 0 20px;
  border-right: 1px solid rgba(0,145,255,.12);
}}
.hud-segment:first-child {{ padding-left: 0; }}
.hud-segment.grow {{ flex: 1; }}
.hud-label {{
  font-family: 'Orbitron', monospace; font-size: .42rem; letter-spacing: 3px;
  text-transform: uppercase; color: rgba(0,145,255,.5); line-height: 1;
  margin-bottom: 3px;
}}
.hud-value {{
  font-family: 'Share Tech Mono', monospace; font-size: .68rem;
  letter-spacing: 2px; color: var(--blue); line-height: 1;
}}
.hud-value.live {{ color: var(--teal); }}
.hud-np-name {{
  font-family: 'Share Tech Mono', monospace; font-size: .75rem;
  letter-spacing: 1px; color: var(--text); line-height: 1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 480px;
}}
.hud-actions {{
  display: flex; gap: 8px; align-items: center; padding-left: 20px; flex-shrink: 0;
}}
.hud-btn {{
  font-family: 'Share Tech Mono', monospace; font-size: .54rem; letter-spacing: 2px;
  text-transform: uppercase; padding: 5px 12px; cursor: pointer;
  background: rgba(0,145,255,.06); border: 1px solid var(--border2);
  color: var(--mid); border-radius: 2px; transition: all .15s; white-space: nowrap;
}}
.hud-btn:hover {{ border-color: var(--blue); color: var(--blue); background: var(--blue-dim); }}
.hud-btn.on {{ border-color: var(--teal); color: var(--teal); background: var(--teal-dim); }}
.hud-btn.muted {{ border-color: var(--amber); color: var(--amber); }}

/* ── Player Zone ─────────────────────────────────────────────── */
.ch-player {{
  flex: 1; position: relative; overflow: hidden; background: #000;
  border: 1px solid rgba(0,145,255,.2);
  box-shadow: 0 0 40px rgba(0,145,255,.08), inset 0 0 40px rgba(0,145,255,.03);
  animation: holo-border-pulse 4s ease-in-out infinite;
}}
@keyframes holo-border-pulse {{
  0%, 100% {{ border-color: rgba(0,145,255,.2); box-shadow: 0 0 30px rgba(0,145,255,.08), inset 0 0 30px rgba(0,145,255,.03); }}
  50% {{ border-color: rgba(0,234,255,.35); box-shadow: 0 0 60px rgba(0,145,255,.18), inset 0 0 60px rgba(0,145,255,.06); }}
}}

/* Corner accents on player */
.ch-player .corner {{
  position: absolute; width: 18px; height: 18px; z-index: 10; pointer-events: none;
}}
.ch-player .corner.tl {{ top: 6px; left: 6px; border-top: 2px solid var(--blue); border-left: 2px solid var(--blue); }}
.ch-player .corner.tr {{ top: 6px; right: 6px; border-top: 2px solid var(--blue); border-right: 2px solid var(--blue); }}
.ch-player .corner.bl {{ bottom: 6px; left: 6px; border-bottom: 2px solid var(--blue); border-left: 2px solid var(--blue); }}
.ch-player .corner.br {{ bottom: 6px; right: 6px; border-bottom: 2px solid var(--blue); border-right: 2px solid var(--blue); }}

/* Scanline overlay on active player */
.player-scanlines {{
  position: absolute; inset: 0; pointer-events: none; z-index: 5;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,.04) 2px, rgba(0,0,0,.04) 4px);
  opacity: 0; transition: opacity .3s;
}}
.ch-player.active .player-scanlines {{ opacity: 1; }}

/* Arc Reactor Placeholder ─────────────────────────────────────── */
.arc-placeholder {{
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 28px; z-index: 2;
  background: var(--deep);
}}
.arc-reactor {{
  position: relative; width: 130px; height: 130px; flex-shrink: 0;
}}
.arc-ring {{
  position: absolute; border-radius: 50%; top: 50%; left: 50%;
  transform: translate(-50%, -50%); border-style: solid;
}}
.arc-ring.r1 {{
  width: 130px; height: 130px; border-width: 1px;
  border-color: rgba(0,145,255,.35) rgba(0,145,255,.08) rgba(0,145,255,.35) rgba(0,145,255,.08);
  animation: arc-cw 10s linear infinite;
}}
.arc-ring.r2 {{
  width: 96px; height: 96px; border-width: 1.5px;
  border-color: rgba(0,234,255,.5) rgba(0,234,255,.1) rgba(0,234,255,.5) rgba(0,234,255,.1);
  animation: arc-ccw 6s linear infinite;
}}
.arc-ring.r3 {{
  width: 62px; height: 62px; border-width: 1px;
  border-color: rgba(0,145,255,.4) rgba(0,145,255,.08) rgba(0,145,255,.4) rgba(0,145,255,.08);
  animation: arc-cw 3.5s linear infinite;
}}
.arc-ring.r4 {{
  width: 36px; height: 36px; border-width: 2px;
  border-color: rgba(0,234,255,.6) rgba(0,234,255,.15) rgba(0,234,255,.6) rgba(0,234,255,.15);
  animation: arc-ccw 2s linear infinite;
}}
.arc-core {{
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 20px; height: 20px; border-radius: 50%;
  background: radial-gradient(circle, rgba(0,234,255,.95) 0%, rgba(0,145,255,.5) 50%, transparent 100%);
  box-shadow: 0 0 16px var(--jarvis), 0 0 32px rgba(0,145,255,.4);
  animation: core-pulse 2.5s ease-in-out infinite;
}}
@keyframes arc-cw  {{ from {{ transform: translate(-50%,-50%) rotate(0deg); }} to {{ transform: translate(-50%,-50%) rotate(360deg); }} }}
@keyframes arc-ccw {{ from {{ transform: translate(-50%,-50%) rotate(0deg); }} to {{ transform: translate(-50%,-50%) rotate(-360deg); }} }}
@keyframes core-pulse {{
  0%, 100% {{ opacity: .75; box-shadow: 0 0 12px var(--jarvis), 0 0 24px rgba(0,145,255,.3); }}
  50% {{ opacity: 1; box-shadow: 0 0 24px var(--jarvis), 0 0 48px rgba(0,145,255,.6); }}
}}

.arc-text {{
  font-family: 'Orbitron', monospace; font-size: .65rem; font-weight: 700;
  letter-spacing: 5px; text-transform: uppercase; color: var(--blue);
  text-shadow: 0 0 12px rgba(0,145,255,.6);
}}
.arc-hint {{
  font-family: 'Share Tech Mono', monospace; font-size: .58rem;
  letter-spacing: 2px; color: var(--dim); text-align: center;
}}

/* Active iframe */
#ch-iframe {{ width: 100%; height: 100%; border: none; display: block; }}

/* ── Glassmorphic Control Bar ────────────────────────────────── */
.glass-controls {{
  display: flex; align-items: center; gap: 12px; padding: 10px 20px; flex-shrink: 0;
  background: rgba(13,16,24,.88); backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0,145,255,.15);
}}
.gc-vol {{
  display: flex; align-items: center; gap: 8px;
}}
.vol-label {{
  font-family: 'Share Tech Mono', monospace; font-size: .5rem; letter-spacing: 2px;
  text-transform: uppercase; color: var(--dim); flex-shrink: 0;
}}
.vol-slider {{
  width: 110px; accent-color: var(--blue); cursor: pointer; flex-shrink: 0;
}}
.gc-divider {{
  width: 1px; height: 20px; background: var(--border2); flex-shrink: 0;
}}
.gc-actions {{ display: flex; align-items: center; gap: 8px; }}
.gc-btn {{
  font-family: 'Share Tech Mono', monospace; font-size: .52rem; letter-spacing: 2px;
  text-transform: uppercase; padding: 5px 12px; cursor: pointer;
  background: rgba(0,145,255,.05); border: 1px solid var(--border2);
  color: var(--mid); border-radius: 2px; transition: all .15s;
}}
.gc-btn:hover {{ border-color: var(--blue); color: var(--blue); background: var(--blue-dim); }}
.gc-btn.muted {{ border-color: var(--amber); color: var(--amber); }}
.gc-link {{
  font-family: 'Share Tech Mono', monospace; font-size: .52rem; letter-spacing: 2px;
  text-transform: uppercase; padding: 5px 12px;
  background: rgba(0,229,160,.05); border: 1px solid var(--border2);
  color: var(--mid); border-radius: 2px; transition: all .15s; text-decoration: none;
}}
.gc-link:hover {{ border-color: var(--teal); color: var(--teal); background: var(--teal-dim); }}
.gc-right {{ margin-left: auto; display: flex; gap: 8px; }}

/* ── Channel Guide Sidebar (RIGHT) ───────────────────────────── */
.ch-guide {{
  width: 300px; flex-shrink: 0; display: flex; flex-direction: column;
  background: var(--panel); border-left: 1px solid var(--border);
  overflow: hidden;
  transition: width .3s cubic-bezier(.4,0,.2,1), opacity .3s ease;
}}
.ch-shell.theater .ch-guide {{
  width: 0; opacity: 0; pointer-events: none;
}}

/* Guide Header */
.guide-header {{
  padding: 14px 16px 12px; border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: linear-gradient(135deg, rgba(0,229,160,.04) 0%, transparent 100%);
  position: relative;
}}
.guide-header::after {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,229,160,.3), transparent);
}}
.guide-title {{
  font-family: 'Orbitron', monospace; font-size: .65rem; font-weight: 700;
  letter-spacing: 4px; text-transform: uppercase; color: var(--teal);
  text-shadow: 0 0 8px var(--teal-glow); margin-bottom: 3px;
}}
.guide-sub {{
  font-family: 'Share Tech Mono', monospace; font-size: .52rem;
  letter-spacing: 2px; color: var(--dim);
}}

/* Guide Search */
.guide-search {{ padding: 10px 12px; border-bottom: 1px solid var(--border); flex-shrink: 0; }}
.guide-search input {{
  width: 100%; background: rgba(0,229,160,.04); border: 1px solid var(--border2);
  color: var(--text); font-family: 'Share Tech Mono', monospace; font-size: .6rem;
  padding: 7px 12px; outline: none; border-radius: 2px; letter-spacing: 1px;
  transition: border-color .15s;
}}
.guide-search input:focus {{ border-color: var(--teal); box-shadow: 0 0 8px var(--teal-dim); }}
.guide-search input::placeholder {{ color: var(--dim); }}

/* Guide Scroll */
.guide-scroll {{
  flex: 1; overflow-y: auto; overflow-x: hidden;
  scrollbar-width: thin; scrollbar-color: var(--border2) transparent;
}}
.guide-scroll::-webkit-scrollbar {{ width: 3px; }}
.guide-scroll::-webkit-scrollbar-thumb {{ background: var(--border2); border-radius: 2px; }}

/* Category sections */
.cat-section {{ border-bottom: 1px solid var(--border); }}
.cat-hd {{
  display: flex; align-items: center; gap: 8px; padding: 9px 14px;
  cursor: pointer; transition: background .12s; user-select: none;
  position: relative;
}}
.cat-hd:hover {{ background: rgba(0,229,160,.04); }}
.cat-hd.open {{ background: rgba(0,229,160,.03); }}
.cat-ic {{
  font-size: .72rem; width: 16px; text-align: center;
  color: var(--teal); flex-shrink: 0;
}}
.cat-nm {{
  flex: 1; font-family: 'Orbitron', monospace; font-size: .52rem;
  letter-spacing: 2px; text-transform: uppercase; color: var(--mid); font-weight: 600;
}}
.cat-ct {{
  font-family: 'Share Tech Mono', monospace; font-size: .5rem; color: var(--dim);
  background: var(--border); padding: 2px 7px; border-radius: 10px;
}}
.cat-chevron {{
  font-size: .55rem; color: var(--dim); transition: transform .25s ease; margin-left: 4px;
}}
.cat-hd.open .cat-chevron {{ transform: rotate(180deg); }}

/* Cat body animation */
.cat-body {{
  overflow: hidden; transition: max-height .28s cubic-bezier(.4,0,.2,1);
}}

/* Channel rows */
.ch-row {{
  display: flex; align-items: center; gap: 10px; padding: 8px 14px 8px 22px;
  cursor: pointer; border-bottom: 1px solid rgba(26,37,53,.4);
  border-left: 3px solid transparent; transition: all .12s;
}}
.ch-row:hover {{
  background: rgba(0,229,160,.04); border-left-color: rgba(0,229,160,.3);
}}
.ch-row.active {{
  background: rgba(0,229,160,.08); border-left-color: var(--teal);
}}
.ch-live-dot {{
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  background: var(--dim); transition: all .2s;
}}
.ch-row.active .ch-live-dot {{
  background: var(--teal); box-shadow: 0 0 6px var(--teal);
  animation: live-blink 2s ease-in-out infinite;
}}
@keyframes live-blink {{
  0%, 100% {{ opacity: 1; }} 50% {{ opacity: .4; }}
}}
.ch-info {{ flex: 1; min-width: 0; }}
.ch-name {{
  display: block; font-size: .78rem; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.ch-row.active .ch-name {{ color: var(--teal); }}
.ch-desc {{
  display: block; font-size: .58rem; color: var(--dim);
  font-family: 'Share Tech Mono', monospace; letter-spacing: 1px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;
}}
.ch-arr {{ font-size: .55rem; color: var(--dim); flex-shrink: 0; transition: color .15s; }}
.ch-row:hover .ch-arr, .ch-row.active .ch-arr {{ color: var(--teal); }}

/* Suggest form */
.suggest-wrap {{
  padding: 12px; border-top: 1px solid var(--border); flex-shrink: 0;
  background: var(--panel);
}}
.suggest-toggle {{
  font-family: 'Share Tech Mono', monospace; font-size: .56rem; letter-spacing: 2px;
  text-transform: uppercase; color: var(--mid); cursor: pointer;
  transition: color .15s; padding: 4px 0; display: flex; align-items: center; gap: 6px;
}}
.suggest-toggle:hover {{ color: var(--teal); }}
.suggest-toggle::before {{ content: '&#8853;'; }}
#suggest-form {{ margin-top: 8px; display: flex; flex-direction: column; gap: 5px; }}
#suggest-form input {{
  background: rgba(0,229,160,.03); border: 1px solid var(--border2); color: var(--text);
  font-family: 'Share Tech Mono', monospace; font-size: .56rem; padding: 6px 10px;
  outline: none; border-radius: 2px; letter-spacing: 1px; transition: border-color .15s;
}}
#suggest-form input:focus {{ border-color: var(--teal); }}
#suggest-form input::placeholder {{ color: var(--dim); }}
#suggest-form button {{
  background: var(--teal); color: #000; border: none;
  font-family: 'Orbitron', monospace; font-size: .56rem; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase; padding: 7px; cursor: pointer;
  transition: background .15s; border-radius: 2px;
}}
#suggest-form button:hover {{ background: #fff; }}
#sg-msg {{
  font-family: 'Share Tech Mono', monospace; font-size: .53rem;
  margin-top: 4px; letter-spacing: 1px;
}}

/* ── Responsive ──────────────────────────────────────────────── */
@media (max-width: 900px) {{
  .ch-guide {{ width: 240px; }}
  .ch-nav-links {{ display: none; }}
  nav.ch-nav {{ padding: 0 14px; }}
  .hud-segment.side {{ display: none; }}
}}
@media (max-width: 600px) {{
  .ch-guide {{ display: none; }}
  .ch-shell.theater .ch-guide {{ display: none; }}
}}
</style>
</head>
<body>

<!-- ── Nav ───────────────────────────────────────────────────── -->
<nav class="ch-nav">
  <a href="/" class="nav-logo">Triptok<em>Forge</em></a>
  <div class="ch-nav-links">
    <a href="/">Home</a>
    <a href="/forge">Island Forge</a>
    <a href="/leaderboard">Leaderboard</a>
    <a href="/channels" class="active">TV Channels</a>
    <a href="/news">News</a>
    <a href="/cardgame">Card Game</a>
    <a href="/community">Community</a>
  </div>
  <div class="nav-right">
    <a href="/dashboard">Dashboard</a>
    <a href="/whitepages">Whitepages</a>
  </div>
</nav>

<!-- ── Shell ─────────────────────────────────────────────────── -->
<div class="ch-shell" id="chShell">

  <!-- LEFT: Main Player -->
  <div class="ch-main">

    <!-- JARVIS HUD -->
    <div class="jarvis-hud">
      <div class="hud-segment side">
        <span class="hud-label">System</span>
        <span class="hud-value" id="hudStatus">STANDBY</span>
      </div>
      <div class="hud-segment grow">
        <span class="hud-label">Now Playing</span>
        <span class="hud-np-name" id="nowPlaying">Select a channel from the guide &rsaquo;</span>
      </div>
      <div class="hud-segment side">
        <span class="hud-label">Channels</span>
        <span class="hud-value">{total} &middot; {ncats} cats</span>
      </div>
      <div class="hud-actions">
        <button class="hud-btn" id="muteBtn" onclick="toggleMute()">&#9900; MUTE</button>
        <button class="hud-btn" id="theaterBtn" onclick="toggleTheater()">&#9632; THEATER</button>
      </div>
    </div>

    <!-- Player -->
    <div class="ch-player" id="chPlayer">
      <div class="corner tl"></div>
      <div class="corner tr"></div>
      <div class="corner bl"></div>
      <div class="corner br"></div>
      <div class="player-scanlines" id="playerScanlines"></div>

      <!-- Arc Reactor Placeholder -->
      <div class="arc-placeholder" id="placeholder">
        <div class="arc-reactor">
          <div class="arc-ring r1"></div>
          <div class="arc-ring r2"></div>
          <div class="arc-ring r3"></div>
          <div class="arc-ring r4"></div>
          <div class="arc-core"></div>
        </div>
        <div class="arc-text">AWAITING UPLINK</div>
        <div class="arc-hint">Select a channel from the guide &#8594;</div>
      </div>

      <iframe id="ch-iframe" src="" allow="autoplay; fullscreen; picture-in-picture"
              allowfullscreen style="display:none;width:100%;height:100%;border:none;"></iframe>
    </div>

    <!-- Glassmorphic Controls -->
    <div class="glass-controls">
      <div class="gc-vol">
        <span class="vol-label">Vol</span>
        <input type="range" class="vol-slider" id="volSlider" min="0" max="100" value="80"/>
      </div>
      <div class="gc-divider"></div>
      <div class="gc-actions">
        <a id="linkOut" class="gc-link" href="#" target="_blank" rel="noopener">Open Stream &#8599;</a>
        <button class="gc-btn" onclick="goFullscreen()">&#9633; Fullscreen</button>
      </div>
      <div class="gc-right">
        <button class="gc-btn" onclick="toggleSidebar()">&#9776; Guide</button>
      </div>
    </div>

  </div><!-- /ch-main -->

  <!-- RIGHT: Channel Guide -->
  <div class="ch-guide" id="chGuide">

    <div class="guide-header">
      <div class="guide-title">&#9652; Live Channels</div>
      <div class="guide-sub">{total} channels &middot; {ncats} categories</div>
    </div>

    <div class="guide-search">
      <input type="text" id="ch-search" placeholder="Search channels..."
             oninput="filterChannels(this.value)"/>
    </div>

    <div class="guide-scroll" id="guideScroll">
      {guide_items}
    </div>

    <div class="suggest-wrap">
      <div class="suggest-toggle" onclick="toggleSuggest()">Suggest a Channel</div>
      <div id="suggest-form" style="display:none">
        <input id="sg-name" type="text" placeholder="Channel name"/>
        <input id="sg-cat"  type="text" placeholder="Category"/>
        <input id="sg-url"  type="text" placeholder="Twitch / YouTube / Kick URL"/>
        <input id="sg-desc" type="text" placeholder="Short description (optional)"/>
        <button onclick="submitSuggest()">Submit Suggestion</button>
        <div id="sg-msg" style="display:none"></div>
      </div>
    </div>

  </div><!-- /ch-guide -->

</div><!-- /ch-shell -->

<script>
let currentUrl = '', muted = false, theater = false, sidebarOpen = true;

function loadChannel(url, name) {{
  if (!url) return;
  currentUrl = url;

  // Update HUD
  document.getElementById('nowPlaying').textContent = name;
  document.getElementById('hudStatus').textContent = 'LIVE';
  document.getElementById('hudStatus').classList.add('live');

  // Show iframe, hide placeholder
  document.getElementById('placeholder').style.display = 'none';
  const iframe = document.getElementById('ch-iframe');
  iframe.style.display = 'block';
  iframe.src = muted ? url + (url.includes('?') ? '&' : '?') + 'muted=true' : url;

  // Activate player holographic effects
  document.getElementById('chPlayer').classList.add('active');
  document.getElementById('playerScanlines').style.opacity = '1';

  // Link-out
  let lo = url;
  const tch = url.match(/channel=([^&]+)/);
  if (tch) lo = 'https://twitch.tv/' + tch[1];
  const yt = url.match(/youtube\.com\/embed\/([^?]+)/);
  if (yt) lo = 'https://youtu.be/' + yt[1];
  document.getElementById('linkOut').href = lo;

  // Active state in guide
  document.querySelectorAll('.ch-row').forEach(r => {{
    r.classList.toggle('active', r.dataset.name === name);
  }});
}}

function toggleMute() {{
  muted = !muted;
  const btn = document.getElementById('muteBtn');
  btn.textContent = muted ? '&#9900; UNMUTE' : '&#9900; MUTE';
  btn.classList.toggle('muted', muted);
  if (currentUrl) {{
    const iframe = document.getElementById('ch-iframe');
    iframe.src = muted
      ? currentUrl + (currentUrl.includes('?') ? '&' : '?') + 'muted=true'
      : currentUrl;
  }}
}}

function goFullscreen() {{
  const p = document.getElementById('chPlayer');
  (p.requestFullscreen || p.webkitRequestFullscreen).call(p);
}}

function toggleTheater() {{
  theater = !theater;
  document.getElementById('chShell').classList.toggle('theater', theater);
  const btn = document.getElementById('theaterBtn');
  btn.textContent = theater ? '&#9633; EXIT THEATER' : '&#9632; THEATER';
  btn.classList.toggle('on', theater);
  if (theater) sidebarOpen = false;
  else sidebarOpen = true;
}}

function toggleSidebar() {{
  sidebarOpen = !sidebarOpen;
  if (sidebarOpen) {{
    document.getElementById('chShell').classList.remove('theater');
    theater = false;
    document.getElementById('theaterBtn').textContent = '&#9632; THEATER';
    document.getElementById('theaterBtn').classList.remove('on');
  }} else {{
    document.getElementById('chShell').classList.add('theater');
  }}
}}

function toggleCat(hd) {{
  const isOpen = hd.classList.contains('open');
  const body = hd.nextElementSibling;
  if (isOpen) {{
    body.style.maxHeight = '0';
    hd.classList.remove('open');
  }} else {{
    body.style.maxHeight = body.scrollHeight + 'px';
    hd.classList.add('open');
  }}
}}

function filterChannels(q) {{
  const ql = q.toLowerCase();
  document.querySelectorAll('.ch-row').forEach(r => {{
    r.style.display = (!ql || r.dataset.name.toLowerCase().includes(ql)) ? '' : 'none';
  }});
  if (ql) {{
    document.querySelectorAll('.cat-section').forEach(sec => {{
      const body = sec.querySelector('.cat-body');
      const hd = sec.querySelector('.cat-hd');
      body.style.maxHeight = 'none';
      hd.classList.add('open');
    }});
  }}
}}

function toggleSuggest() {{
  const f = document.getElementById('suggest-form');
  f.style.display = f.style.display === 'none' ? 'flex' : 'none';
}}

async function submitSuggest() {{
  const name = document.getElementById('sg-name').value.trim();
  const cat  = document.getElementById('sg-cat').value.trim();
  const url  = document.getElementById('sg-url').value.trim();
  const desc = document.getElementById('sg-desc').value.trim();
  if (!name || !url) {{ alert('Name and URL required.'); return; }}
  const msg = document.getElementById('sg-msg');
  try {{
    const r = await fetch('/api/suggest_channel', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ name, category: cat || 'Other', embed_url: url, description: desc }})
    }});
    const d = await r.json();
    msg.textContent = d.ok ? '\u2713 Submitted for review!' : (d.error || 'Error submitting');
    msg.style.display = 'block';
    msg.style.color = d.ok ? 'var(--teal)' : 'var(--amber)';
    if (d.ok) ['sg-name','sg-cat','sg-url','sg-desc'].forEach(id => document.getElementById(id).value = '');
  }} catch(e) {{
    msg.textContent = 'Network error.';
    msg.style.display = 'block';
    msg.style.color = 'var(--amber)';
  }}
}}

// Init: open all cat sections
document.addEventListener('DOMContentLoaded', () => {{
  document.querySelectorAll('.cat-hd').forEach(hd => {{
    hd.classList.add('open');
  }});
  document.querySelectorAll('.cat-body').forEach(body => {{
    body.style.maxHeight = body.scrollHeight + 'px';
  }});
}});
</script>
</body>
</html>"""
