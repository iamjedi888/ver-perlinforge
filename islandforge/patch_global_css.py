#!/usr/bin/env python3
"""
patch_global_css.py
Run on VM:
    python3 ~/ver-perlinforge/islandforge/patch_global_css.py

What it does:
  1. Writes static/triptokforge.css — global design system
  2. Writes static/nav-overlay.js — slide-in nav for all pages
  3. Patches <link> + nav HTML into index.html, 404.html, whitepages
  4. Restarts service
"""
import os, subprocess, time

ROOT   = "/home/ubuntu/ver-perlinforge/islandforge"
STATIC = os.path.join(ROOT, "static")
os.makedirs(STATIC, exist_ok=True)

# ── 1. GLOBAL CSS ────────────────────────────────────────────────
CSS = """/* ═══════════════════════════════════════════════════════════════
   TriptokForge — Global Design System
   triptokforge.css v1.0
   Import in every page: <link rel="stylesheet" href="/static/triptokforge.css"/>
═══════════════════════════════════════════════════════════════ */

/* ── TOKENS ──────────────────────────────────────────────────── */
:root {
  /* Colours */
  --bg:        #0a0c10;
  --bg2:       #07090d;
  --surface:   #111318;
  --surface2:  #161b24;
  --border:    #1e2330;
  --border2:   #2a3045;
  --teal:      #00e5a0;
  --teal-dim:  #00b07a;
  --teal-glow: rgba(0,229,160,.12);
  --blue:      #0091ff;
  --blue-dim:  #0060cc;
  --blue-glow: rgba(0,145,255,.10);
  --amber:     #ffaa00;
  --red:       #ff4444;
  --warn:      #ff6b35;
  --text:      #c8d0e0;
  --mid:       #7a8aaa;
  --dim:       #4a5570;

  /* Typography */
  --mono:      'Share Tech Mono', monospace;
  --display:   'Bebas Neue', sans-serif;
  --head:      'Rajdhani', sans-serif;
  --body:      'Barlow Condensed', sans-serif;

  /* Layout */
  --nav-h:     52px;
  --radius:    4px;
  --radius-lg: 8px;
}

/* ── RESET ───────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--body);
  font-size: 15px;
  line-height: 1.65;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── SCROLLBAR ───────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--teal-dim); }

/* ── GLOBAL NAV ──────────────────────────────────────────────── */
#tf-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--nav-h);
  z-index: 900;
  background: rgba(7,9,13,.94);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 0;
}
#tf-nav .tf-logo {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
  margin-right: 24px;
  flex-shrink: 0;
}
#tf-nav .tf-wordmark {
  font-family: var(--head);
  font-weight: 700;
  font-size: .95rem;
  letter-spacing: 3px;
  color: var(--teal);
  text-transform: uppercase;
}
#tf-nav .tf-nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}
#tf-nav .tf-nav-links::-webkit-scrollbar { display: none; }
#tf-nav .tf-nav-links a {
  font-family: var(--mono);
  font-size: .6rem;
  letter-spacing: 2px;
  color: var(--dim);
  text-decoration: none;
  padding: 5px 10px;
  border-radius: var(--radius);
  transition: color .15s, background .15s;
  white-space: nowrap;
  text-transform: uppercase;
}
#tf-nav .tf-nav-links a:hover { color: var(--teal); background: var(--teal-glow); }
#tf-nav .tf-nav-links a.active { color: var(--teal); }
#tf-nav .tf-nav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
#tf-nav .tf-menu-btn {
  background: none;
  border: 1px solid var(--border2);
  color: var(--mid);
  font-family: var(--mono);
  font-size: .58rem;
  letter-spacing: 2px;
  padding: 5px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all .15s;
  text-transform: uppercase;
}
#tf-nav .tf-menu-btn:hover { border-color: var(--teal); color: var(--teal); }

/* ── OVERLAY NAV ─────────────────────────────────────────────── */
#tf-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  pointer-events: none;
  opacity: 0;
  transition: opacity .2s;
}
#tf-overlay.open {
  pointer-events: all;
  opacity: 1;
}
#tf-overlay-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(4,6,10,.85);
  backdrop-filter: blur(6px);
}
#tf-overlay-panel {
  position: relative;
  width: 320px;
  max-width: 90vw;
  height: 100%;
  background: var(--surface);
  border-right: 1px solid var(--border2);
  display: flex;
  flex-direction: column;
  transform: translateX(-100%);
  transition: transform .28s cubic-bezier(.4,0,.2,1);
  overflow-y: auto;
}
#tf-overlay.open #tf-overlay-panel {
  transform: translateX(0);
}
#tf-overlay-panel .ov-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
#tf-overlay-panel .ov-head .ov-logo {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
}
#tf-overlay-panel .ov-head .ov-wordmark {
  font-family: var(--head);
  font-weight: 700;
  font-size: .95rem;
  letter-spacing: 3px;
  color: var(--teal);
  text-transform: uppercase;
}
#tf-overlay-panel .ov-close {
  background: none;
  border: 1px solid var(--border2);
  color: var(--mid);
  font-size: 1rem;
  width: 30px;
  height: 30px;
  border-radius: var(--radius);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}
#tf-overlay-panel .ov-close:hover { border-color: var(--red); color: var(--red); }
.ov-section { padding: 20px 0; border-bottom: 1px solid var(--border); }
.ov-section:last-child { border-bottom: none; }
.ov-label {
  font-family: var(--mono);
  font-size: .55rem;
  letter-spacing: 4px;
  color: var(--dim);
  text-transform: uppercase;
  padding: 0 20px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ov-label::after { content: ''; flex: 1; height: 1px; background: var(--border); }
.ov-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  font-family: var(--body);
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: .5px;
  color: var(--mid);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: all .12s;
}
.ov-link:hover { color: var(--text); background: rgba(255,255,255,.02); border-left-color: var(--border2); }
.ov-link.active { color: var(--teal); border-left-color: var(--teal); background: var(--teal-glow); }
.ov-link .ov-icon { font-size: .75rem; opacity: .5; flex-shrink: 0; width: 16px; text-align: center; }
.ov-tag {
  margin-left: auto;
  font-family: var(--mono);
  font-size: .52rem;
  letter-spacing: 1px;
  padding: 2px 6px;
  border-radius: 2px;
}
.ov-tag-live { background: rgba(0,229,160,.1); color: var(--teal); }
.ov-tag-wip  { background: rgba(255,170,0,.1); color: var(--amber); }
.ov-tag-new  { background: rgba(0,145,255,.1); color: var(--blue); }
.ov-footer {
  margin-top: auto;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ov-footer .ov-ver { font-family: var(--mono); font-size: .58rem; color: var(--dim); letter-spacing: 2px; }
.ov-footer .ov-status { display: flex; align-items: center; gap: 6px; }
.ov-footer .ov-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--teal); box-shadow: 0 0 5px var(--teal); animation: tf-pulse 2s infinite; }
@keyframes tf-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
.ov-footer .ov-status span { font-family: var(--mono); font-size: .58rem; color: var(--mid); letter-spacing: 2px; }

/* ── TYPOGRAPHY UTILS ────────────────────────────────────────── */
.tf-display { font-family: var(--display); letter-spacing: 3px; text-transform: uppercase; }
.tf-head    { font-family: var(--head); font-weight: 700; letter-spacing: 2px; }
.tf-mono    { font-family: var(--mono); }
.tf-teal    { color: var(--teal); }
.tf-blue    { color: var(--blue); }
.tf-dim     { color: var(--dim); }
.tf-mid     { color: var(--mid); }

/* ── BUTTON UTILS ────────────────────────────────────────────── */
.tf-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-family: var(--mono);
  font-size: .65rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 8px 16px;
  border-radius: var(--radius);
  cursor: pointer;
  text-decoration: none;
  transition: all .15s;
  border: none;
}
.tf-btn-primary   { background: var(--teal); color: #000; }
.tf-btn-primary:hover { background: var(--teal-dim); }
.tf-btn-outline   { background: none; border: 1px solid var(--border2); color: var(--mid); }
.tf-btn-outline:hover { border-color: var(--teal); color: var(--teal); }
.tf-btn-ghost     { background: none; color: var(--dim); }
.tf-btn-ghost:hover { color: var(--teal); }

/* ── CARD UTILS ──────────────────────────────────────────────── */
.tf-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.tf-card:hover { border-color: var(--border2); }

/* ── BADGE UTILS ─────────────────────────────────────────────── */
.tf-badge {
  font-family: var(--mono);
  font-size: .55rem;
  letter-spacing: 1px;
  padding: 2px 8px;
  border-radius: 2px;
  text-transform: uppercase;
}
.tf-badge-teal   { background: rgba(0,229,160,.1); color: var(--teal); border: 1px solid rgba(0,229,160,.2); }
.tf-badge-blue   { background: rgba(0,145,255,.1); color: var(--blue); border: 1px solid rgba(0,145,255,.2); }
.tf-badge-amber  { background: rgba(255,170,0,.1);  color: var(--amber); border: 1px solid rgba(255,170,0,.2); }
.tf-badge-red    { background: rgba(255,68,68,.1);  color: var(--red);   border: 1px solid rgba(255,68,68,.2); }

/* ── DIVIDER ─────────────────────────────────────────────────── */
.tf-rule { height: 1px; background: var(--border); margin: 24px 0; }
.tf-rule-teal { height: 1px; background: linear-gradient(to right, var(--teal), transparent); }

/* ── CODE ────────────────────────────────────────────────────── */
code, .tf-code {
  font-family: var(--mono);
  font-size: .8em;
  color: var(--teal);
  background: rgba(0,229,160,.06);
  border: 1px solid rgba(0,229,160,.1);
  padding: 1px 7px;
  border-radius: 3px;
}

/* ── SCANLINE OVERLAY ────────────────────────────────────────── */
body.tf-scanlines::after {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,.025) 2px,
    rgba(0,0,0,.025) 4px
  );
  pointer-events: none;
  z-index: 9998;
}

/* ── PAGE BODY OFFSET ────────────────────────────────────────── */
body.tf-has-nav { padding-top: var(--nav-h); }
"""

with open(os.path.join(STATIC, "triptokforge.css"), "w") as f:
    f.write(CSS)
print("✓ triptokforge.css written")

# ── 2. NAV OVERLAY JS ────────────────────────────────────────────
JS = """/* TriptokForge — Global Nav + Overlay
   nav-overlay.js v1.0
   Include after triptokforge.css on every page.
*/
(function(){
  var LOGO_SVG = '<svg width="24" height="24" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><rect width="256" height="256" rx="44" fill="#07090d"/><line x1="148" y1="38" x2="252" y2="26" stroke="#00e5a0" stroke-width="1.5" opacity=".22"/><line x1="152" y1="50" x2="252" y2="42" stroke="#00e5a0" stroke-width=".8" opacity=".13"/><line x1="150" y1="205" x2="252" y2="220" stroke="#0091ff" stroke-width="1.5" opacity=".22"/><polygon points="128,58 160,105 96,105" fill="none" stroke="#00e5a0" stroke-width="1" opacity=".08"/><polygon points="36,32 208,32 220,44 220,212 208,224 36,224 24,212 24,44" fill="#0d1018" stroke="#1a2535" stroke-width="1.5"/><rect x="44" y="62" width="168" height="34" fill="#00e5a0"/><rect x="99" y="96" width="58" height="100" fill="#00e5a0"/><polygon points="82,62 118,62 156,130 120,130" fill="#07090d"/><rect x="99" y="130" width="58" height="66" fill="#00e5a0"/><rect x="44" y="196" width="168" height="10" fill="#0091ff"/><rect x="24" y="24" width="14" height="4" fill="#00e5a0"/><rect x="24" y="24" width="4" height="14" fill="#00e5a0"/><rect x="218" y="228" width="14" height="4" fill="#0091ff"/><rect x="228" y="218" width="4" height="14" fill="#0091ff"/></svg>';

  var NAV_LINKS = [
    { href:'/home',       label:'Home' },
    { href:'/',           label:'Forge' },
    { href:'/feed',       label:'Feed' },
    { href:'/channels',   label:'Channels' },
    { href:'/community',  label:'Community' },
    { href:'/whitepages', label:'Docs' },
  ];

  var OV_SECTIONS = [
    { label: 'Platform', links: [
      { href:'/',           icon:'▲', label:'Island Forge',  tag:null },
      { href:'/feed',       icon:'◈', label:'Feed',          tag:null },
      { href:'/channels',   icon:'▶', label:'Live Channels', tag:'LIVE' },
      { href:'/community',  icon:'◉', label:'Community',     tag:null },
      { href:'/gallery',    icon:'⬡', label:'Gallery',       tag:null },
    ]},
    { label: 'Account', links: [
      { href:'/dashboard',  icon:'◐', label:'Dashboard',     tag:'LOGIN' },
      { href:'/admin',      icon:'⚙', label:'Admin',         tag:null },
    ]},
    { label: 'Developer', links: [
      { href:'/whitepages', icon:'◇', label:'Whitepages',    tag:'DOCS' },
      { href:'/health',     icon:'⇌', label:'Health Check',  tag:null },
    ]},
  ];

  var cur = window.location.pathname;

  function activeClass(href){
    return (href === cur || (href !== '/' && cur.startsWith(href))) ? ' active' : '';
  }

  // ── BUILD NAV BAR ──
  var nav = document.createElement('div');
  nav.id = 'tf-nav';
  nav.innerHTML =
    '<a href="/home" class="tf-logo">' + LOGO_SVG +
    '<span class="tf-wordmark">TriptokForge</span></a>' +
    '<div class="tf-nav-links">' +
    NAV_LINKS.map(function(l){
      return '<a href="'+l.href+'"'+activeClass(l.href)+'>'+l.label+'</a>';
    }).join('') +
    '</div>' +
    '<div class="tf-nav-right">' +
    '<button class="tf-menu-btn" id="tf-menu-open">&#9776; MENU</button>' +
    '</div>';
  document.body.insertBefore(nav, document.body.firstChild);
  document.body.classList.add('tf-has-nav', 'tf-scanlines');

  // ── BUILD OVERLAY ──
  var ov = document.createElement('div');
  ov.id = 'tf-overlay';
  var sectionsHTML = OV_SECTIONS.map(function(s){
    return '<div class="ov-section"><div class="ov-label">'+s.label+'</div>' +
      s.links.map(function(l){
        var tag = l.tag ? '<span class="ov-tag ov-tag-live">'+l.tag+'</span>' : '';
        return '<a href="'+l.href+'" class="ov-link'+activeClass(l.href)+'">' +
          '<span class="ov-icon">'+l.icon+'</span>'+l.label+tag+'</a>';
      }).join('') + '</div>';
  }).join('');

  ov.innerHTML =
    '<div id="tf-overlay-backdrop"></div>' +
    '<div id="tf-overlay-panel">' +
      '<div class="ov-head">' +
        '<a href="/home" class="ov-logo">' + LOGO_SVG +
        '<span class="ov-wordmark">TriptokForge</span></a>' +
        '<button class="ov-close" id="tf-ov-close">✕</button>' +
      '</div>' +
      sectionsHTML +
      '<div class="ov-footer">' +
        '<span class="ov-ver">v0.4.1 · BETA</span>' +
        '<div class="ov-status"><div class="ov-dot"></div><span>ONLINE</span></div>' +
      '</div>' +
    '</div>';
  document.body.appendChild(ov);

  // ── OPEN / CLOSE ──
  function openOv(){ ov.classList.add('open'); document.body.style.overflow='hidden'; }
  function closeOv(){ ov.classList.remove('open'); document.body.style.overflow=''; }

  document.getElementById('tf-menu-open').addEventListener('click', openOv);
  document.getElementById('tf-ov-close').addEventListener('click', closeOv);
  document.getElementById('tf-overlay-backdrop').addEventListener('click', closeOv);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeOv(); });
})();
"""

with open(os.path.join(STATIC, "nav-overlay.js"), "w") as f:
    f.write(JS)
print("✓ nav-overlay.js written")

# ── 3. PATCH HTML FILES ──────────────────────────────────────────
INJECT = """    <link rel="stylesheet" href="/static/triptokforge.css"/>"""
INJECT_JS = """    <script src="/static/nav-overlay.js" defer></script>"""

html_files = [
    os.path.join(ROOT, "index.html"),
    os.path.join(ROOT, "404.html"),
    os.path.join(ROOT, "templates", "whitepages", "index.html"),
]

for path in html_files:
    if not os.path.exists(path):
        print(f"→ skip (not found): {path}")
        continue
    src = open(path).read()
    changed = False

    if "triptokforge.css" not in src:
        src = src.replace("</head>", INJECT + "\n</head>")
        changed = True
        print(f"✓ css injected: {path.split('islandforge/')[-1]}")

    if "nav-overlay.js" not in src:
        src = src.replace("</head>", INJECT_JS + "\n</head>")
        changed = True
        print(f"✓ js injected: {path.split('islandforge/')[-1]}")

    if changed:
        open(path, "w").write(src)

# ── 4. RESTART ───────────────────────────────────────────────────
print("\n▸ Restarting...")
subprocess.run(["sudo","systemctl","restart","islandforge"], check=True)
time.sleep(4)
r = subprocess.run(["curl","-s","http://127.0.0.1:5000/health"], capture_output=True, text=True)
print("health:", r.stdout[:80])
print("\n✅ Done!")
print("   → Every page now has the global nav bar + slide-in overlay menu")
print("   → Design tokens unified in /static/triptokforge.css")
print("   → Add class tf-scanlines to body for scanline effect on any page")
