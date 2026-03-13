#!/usr/bin/env python3
"""
patch_whitepages.py
Run on Oracle VM from inside islandforge/:
    python3 patch_whitepages.py

What it does:
  1. Backs up server.py → server.py.bak2
  2. Adds /whitepages route to server.py (only if not already there)
  3. Writes whitepages.html into islandforge/
  4. Restarts the service
  5. Checks health
"""

import os, sys, shutil, subprocess, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(ROOT, "server.py")
BACKUP = os.path.join(ROOT, "server.py.bak2")
WP_HTML = os.path.join(ROOT, "whitepages.html")

# ── STEP 1: BACKUP ──────────────────────────────────────────────
shutil.copy2(SERVER, BACKUP)
print(f"✓ Backed up server.py → server.py.bak2")

# ── STEP 2: PATCH server.py ─────────────────────────────────────
with open(SERVER, "r") as f:
    src = f.read()

if "/whitepages" in src:
    print("✓ /whitepages route already in server.py — skipping patch")
else:
    ROUTE = textwrap.dedent("""

# ── WHITEPAGES ───────────────────────────────────────────────────
@app.route("/whitepages")
def whitepages():
    import os as _os
    p = _os.path.join(_os.path.dirname(__file__), "whitepages.html")
    if _os.path.exists(p):
        with open(p) as f:
            return f.read()
    return "<h1 style='color:#00e5a0;font-family:monospace;padding:40px'>Whitepages coming soon.</h1>", 200

""")

    # Insert before the last if __name__ block, or just append
    if 'if __name__ == "__main__"' in src:
        src = src.replace('if __name__ == "__main__"',
                          ROUTE + 'if __name__ == "__main__"')
    else:
        src = src + ROUTE

    with open(SERVER, "w") as f:
        f.write(src)
    print("✓ Patched server.py with /whitepages route")

# ── STEP 3: WRITE whitepages.html ───────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Whitepages — TriptokForge Developer Docs</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Barlow+Condensed:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#07090d;--surface:#0d1018;--surface2:#0f1520;--border:#1a2535;--border2:#243040;--teal:#00e5a0;--teal-dim:#009966;--blue:#0091ff;--amber:#ffaa00;--red:#ff4455;--text:#d0dce8;--text-mid:#8899aa;--text-dim:#445566;--mono:'Share Tech Mono',monospace;--head:'Rajdhani',sans-serif;--body:'Barlow Condensed',sans-serif;--sidebar-w:260px;--header-h:52px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--body);font-size:16px;line-height:1.7;min-height:100vh}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}::-webkit-scrollbar-thumb:hover{background:var(--teal-dim)}
.global-nav{position:fixed;top:0;left:0;right:0;height:var(--header-h);background:rgba(7,9,13,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:16px;z-index:200}
.nav-logo{display:flex;align-items:center;gap:10px;text-decoration:none}
.nav-wordmark{font-family:var(--head);font-weight:700;font-size:1.1rem;letter-spacing:3px;color:var(--teal);text-transform:uppercase}
.nav-slash{color:var(--border2);font-family:var(--mono);font-size:.9rem}
.nav-section{font-family:var(--mono);font-size:.75rem;color:var(--text-mid);letter-spacing:2px}
.nav-right{margin-left:auto;display:flex;align-items:center;gap:14px}
.nav-link{font-family:var(--mono);font-size:.68rem;color:var(--text-dim);text-decoration:none;letter-spacing:2px;transition:color .15s}
.nav-link:hover{color:var(--teal)}
.nav-badge{background:var(--teal);color:#000;font-family:var(--mono);font-size:.6rem;font-weight:700;letter-spacing:1px;padding:3px 8px;border-radius:2px}
.layout{display:flex;padding-top:var(--header-h);min-height:100vh}
.sidebar{width:var(--sidebar-w);flex-shrink:0;position:fixed;top:var(--header-h);left:0;bottom:0;overflow-y:auto;border-right:1px solid var(--border);background:var(--surface);padding:28px 0 60px}
.sb-group{margin-bottom:28px}
.sb-group-label{font-family:var(--mono);font-size:.6rem;letter-spacing:3px;color:var(--text-dim);text-transform:uppercase;padding:0 20px;margin-bottom:8px}
.sb-link{display:flex;align-items:center;gap:8px;padding:7px 20px;font-family:var(--body);font-size:.9rem;font-weight:500;color:var(--text-mid);text-decoration:none;border-left:2px solid transparent;transition:all .12s;letter-spacing:.5px}
.sb-link:hover{color:var(--text);background:var(--surface2)}
.sb-link.active{color:var(--teal);border-left-color:var(--teal);background:rgba(0,229,160,.04)}
.sb-link .sb-tag{margin-left:auto;font-family:var(--mono);font-size:.58rem;letter-spacing:1px;padding:2px 6px;border-radius:2px;background:var(--border);color:var(--text-dim)}
.sb-link .sb-tag.new{background:rgba(0,229,160,.15);color:var(--teal)}
.sb-link .sb-tag.wip{background:rgba(255,170,0,.12);color:var(--amber)}
.content{margin-left:var(--sidebar-w);flex:1;max-width:860px;padding:48px 56px 120px}
.page-hero{border-bottom:1px solid var(--border);padding-bottom:36px;margin-bottom:52px}
.hero-eyebrow{font-family:var(--mono);font-size:.68rem;letter-spacing:4px;color:var(--teal);text-transform:uppercase;margin-bottom:14px}
.page-hero h1{font-family:var(--head);font-weight:700;font-size:2.8rem;letter-spacing:4px;color:var(--text);text-transform:uppercase;line-height:1.1;margin-bottom:16px}
.page-hero h1 span{color:var(--teal)}
.page-hero p{font-size:1.05rem;color:var(--text-mid);max-width:580px;line-height:1.7}
.hero-meta{display:flex;gap:24px;margin-top:20px;flex-wrap:wrap}
.hero-stat .val{font-family:var(--mono);font-size:.75rem;color:var(--teal);letter-spacing:2px;display:block}
.hero-stat .lbl{font-family:var(--mono);font-size:.6rem;color:var(--text-dim);letter-spacing:2px;display:block}
.doc-section{margin-bottom:68px;scroll-margin-top:76px}
.doc-section+.doc-section{border-top:1px solid var(--border);padding-top:56px}
.section-head{display:flex;align-items:baseline;gap:14px;margin-bottom:24px}
.section-num{font-family:var(--mono);font-size:.65rem;color:var(--text-dim);letter-spacing:3px;flex-shrink:0}
.section-head h2{font-family:var(--head);font-weight:700;font-size:1.6rem;letter-spacing:3px;text-transform:uppercase;color:var(--text)}
.section-head h2 .accent{color:var(--teal)}
.callout{border-left:3px solid var(--teal);background:rgba(0,229,160,.04);border-radius:0 6px 6px 0;padding:14px 18px;margin:20px 0;font-size:.92rem}
.callout.blue{border-color:var(--blue);background:rgba(0,145,255,.04)}
.callout.amber{border-color:var(--amber);background:rgba(255,170,0,.04)}
.callout.red{border-color:var(--red);background:rgba(255,68,85,.04)}
.callout-label{font-family:var(--mono);font-size:.6rem;letter-spacing:3px;color:var(--teal);text-transform:uppercase;margin-bottom:6px;display:block}
.callout.blue .callout-label{color:var(--blue)}.callout.amber .callout-label{color:var(--amber)}.callout.red .callout-label{color:var(--red)}
.code-block{background:#060810;border:1px solid var(--border);border-radius:6px;overflow:hidden;margin:18px 0;font-size:.82rem}
.code-bar{display:flex;align-items:center;justify-content:space-between;padding:9px 16px;background:var(--surface);border-bottom:1px solid var(--border)}
.code-bar .lang{font-family:var(--mono);font-size:.62rem;letter-spacing:2px;color:var(--text-dim)}
.code-bar .file{font-family:var(--mono);font-size:.65rem;color:var(--teal);letter-spacing:1px}
.copy-btn{background:none;border:1px solid var(--border2);color:var(--text-dim);font-family:var(--mono);font-size:.6rem;letter-spacing:1px;padding:3px 10px;border-radius:2px;cursor:pointer;transition:all .12s}
.copy-btn:hover{border-color:var(--teal);color:var(--teal)}
.copy-btn.ok{border-color:var(--teal);color:#000;background:var(--teal)}
pre{padding:18px 20px;font-family:var(--mono);line-height:1.9;overflow-x:auto;color:var(--text-mid)}
code{font-family:var(--mono);font-size:.82em;color:var(--teal);background:rgba(0,229,160,.07);padding:1px 6px;border-radius:3px}
.prose p{margin-bottom:14px;font-size:.97rem;color:var(--text-mid)}
.prose h3{font-family:var(--head);font-weight:600;font-size:1.1rem;letter-spacing:2px;color:var(--text);text-transform:uppercase;margin:28px 0 10px}
.prose h3::before{content:'// ';color:var(--text-dim);font-family:var(--mono);font-weight:400;font-size:.85em}
.prose ul{list-style:none;margin:10px 0 18px}
.prose ul li{font-size:.95rem;color:var(--text-mid);padding:4px 0 4px 18px;position:relative}
.prose ul li::before{content:'▸';position:absolute;left:0;color:var(--teal);font-size:.75em;top:6px}
.file-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:20px 0}
.file-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:14px 16px;transition:border-color .15s}
.file-card.done{border-color:rgba(0,229,160,.3)}.file-card.wip{border-color:rgba(255,170,0,.25)}
.fc-name{font-family:var(--mono);font-size:.72rem;color:var(--teal);letter-spacing:1px;margin-bottom:5px;display:flex;align-items:center;justify-content:space-between}
.fc-status{font-size:.58rem;letter-spacing:1px;padding:2px 6px;border-radius:2px}
.fc-status.done{background:rgba(0,229,160,.12);color:var(--teal)}.fc-status.wip{background:rgba(255,170,0,.12);color:var(--amber)}.fc-status.todo{background:rgba(68,85,102,.2);color:var(--text-dim)}
.fc-desc{font-size:.78rem;color:var(--text-dim);line-height:1.5}
.doc-table{width:100%;border-collapse:collapse;margin:18px 0;font-size:.85rem}
.doc-table th{text-align:left;font-family:var(--mono);font-size:.62rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;padding:10px 14px;border-bottom:1px solid var(--border2);background:var(--surface)}
.doc-table td{padding:10px 14px;border-bottom:1px solid var(--border);color:var(--text-mid);vertical-align:top;line-height:1.5}
.doc-table tr:last-child td{border-bottom:none}.doc-table tr:hover td{background:var(--surface2)}
.doc-table td code{font-family:var(--mono);font-size:.78rem;color:var(--teal);background:rgba(0,229,160,.06);padding:1px 6px;border-radius:3px}
.td-method{font-family:var(--mono);font-size:.7rem;padding:3px 8px;border-radius:3px;white-space:nowrap;font-weight:700;letter-spacing:1px}
.method-get{background:rgba(0,229,160,.12);color:var(--teal)}.method-post{background:rgba(0,145,255,.12);color:var(--blue)}
.steps{display:flex;flex-direction:column;gap:0;margin:20px 0}
.step{display:flex;gap:18px;padding-bottom:28px;position:relative}
.step::before{content:'';position:absolute;left:15px;top:32px;bottom:0;width:1px;background:var(--border)}
.step:last-child::before{display:none}
.step-num{width:32px;height:32px;border:1.5px solid var(--teal);border-radius:4px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:.75rem;color:var(--teal);background:rgba(0,229,160,.06)}
.step-body{flex:1;padding-top:5px}
.step-body strong{font-family:var(--head);font-weight:600;font-size:1rem;letter-spacing:1px;color:var(--text);display:block;margin-bottom:4px}
.step-body p{font-size:.88rem;color:var(--text-mid);margin:0}
.doc-footer{margin-left:var(--sidebar-w);border-top:1px solid var(--border);padding:24px 56px;display:flex;align-items:center;gap:16px}
.doc-footer span{font-family:var(--mono);font-size:.65rem;color:var(--text-dim);letter-spacing:2px}
.doc-footer span.teal{color:var(--teal)}
@media(max-width:768px){:root{--sidebar-w:0px}.sidebar{display:none}.content{padding:28px 20px 80px}.doc-footer{margin-left:0;padding:20px}.page-hero h1{font-size:2rem}}
</style>
</head>
<body>
<nav class="global-nav">
  <a href="/home" class="nav-logo">
    <svg width="24" height="24" viewBox="0 0 256 256"><rect width="256" height="256" rx="44" fill="#07090d"/><polygon points="36,32 208,32 220,44 220,212 208,224 36,224 24,212 24,44" fill="#0d1018" stroke="#1a2535" stroke-width="2"/><rect x="44" y="62" width="168" height="34" fill="#00e5a0"/><rect x="99" y="96" width="58" height="100" fill="#00e5a0"/><polygon points="82,62 118,62 156,130 120,130" fill="#07090d"/><rect x="99" y="130" width="58" height="66" fill="#00e5a0"/><rect x="44" y="196" width="168" height="10" fill="#0091ff"/></svg>
    <span class="nav-wordmark">TriptokForge</span>
  </a>
  <span class="nav-slash">/</span>
  <span class="nav-section">WHITEPAGES</span>
  <div class="nav-right">
    <a href="/forge" class="nav-link">ISLAND FORGE</a>
    <a href="/channels" class="nav-link">CHANNELS</a>
    <a href="/home" class="nav-link">PLATFORM</a>
    <span class="nav-badge">BETA DOCS</span>
  </div>
</nav>
<div class="layout">
<aside class="sidebar">
  <div class="sb-group">
    <div class="sb-group-label">Getting Started</div>
    <a href="#overview" class="sb-link active"><span>◈</span> Overview</a>
    <a href="#architecture" class="sb-link"><span>⬡</span> Architecture</a>
    <a href="#deploy" class="sb-link"><span>↑</span> Deploy Guide</a>
  </div>
  <div class="sb-group">
    <div class="sb-group-label">Platform API</div>
    <a href="#routes" class="sb-link"><span>⇌</span> Routes Reference</a>
    <a href="#database" class="sb-link"><span>◉</span> Database Schema</a>
  </div>
  <div class="sb-group">
    <div class="sb-group-label">Verse / UEFN</div>
    <a href="#verse-arch" class="sb-link"><span>◇</span> Verse Architecture <span class="sb-tag new">NEW</span></a>
    <a href="#verse-files" class="sb-link"><span>▤</span> File Reference</a>
  </div>
  <div class="sb-group">
    <div class="sb-group-label">Features</div>
    <a href="#island-forge" class="sb-link"><span>▲</span> Island Forge</a>
    <a href="#channels" class="sb-link"><span>▶</span> Live Channels</a>
    <a href="#epic-oauth" class="sb-link"><span>⚡</span> Epic OAuth <span class="sb-tag wip">PENDING</span></a>
  </div>
  <div class="sb-group">
    <div class="sb-group-label">Tarkov-Lite</div>
    <a href="#tarkov-vision" class="sb-link"><span>◐</span> Vision & Design</a>
    <a href="#tarkov-systems" class="sb-link"><span>⚙</span> Game Systems <span class="sb-tag wip">WIP</span></a>
  </div>
</aside>
<main class="content">
  <div class="page-hero">
    <div class="hero-eyebrow">TriptokForge Docs</div>
    <h1>White<span>pages</span></h1>
    <p>Internal reference and developer guide for the TriptokForge platform — Fortnite Creative community tools, Verse architecture, Oracle backend, and UEFN game systems.</p>
    <div class="hero-meta">
      <div class="hero-stat"><span class="val">v0.4.1</span><span class="lbl">PLATFORM VER</span></div>
      <div class="hero-stat"><span class="val">FLASK · ORACLE · OCI</span><span class="lbl">STACK</span></div>
      <div class="hero-stat"><span class="val">UEFN + VERSE</span><span class="lbl">GAME ENGINE</span></div>
      <div class="hero-stat"><span class="val">EPIC OAUTH PENDING</span><span class="lbl">AUTH STATUS</span></div>
    </div>
  </div>

  <section class="doc-section" id="overview">
    <div class="section-head"><span class="section-num">01</span><h2>Platform <span class="accent">Overview</span></h2></div>
    <div class="prose">
      <p>TriptokForge is an esports and creative platform for Fortnite and UEFN creators. Built on Oracle Cloud Always Free infrastructure — member profiles, island generation tools, a live channels guide, and a social feed, all gated behind Epic Games OAuth.</p>
      <h3>What it does</h3>
      <ul>
        <li>Authenticates players via Epic Games OAuth2 (pending brand approval)</li>
        <li>Generates UEFN island heightmaps from audio frequency analysis</li>
        <li>Hosts a 65-channel live TV guide — esports, global news, gaming</li>
        <li>TikTok-style social feed for clip sharing</li>
        <li>Oracle Autonomous Database via thin mode Python driver</li>
        <li>Media served via OCI Object Storage public bucket CDN</li>
      </ul>
    </div>
    <div class="callout"><span class="callout-label">Note</span>All features requiring player identity are gated behind Epic OAuth. Until brand approval completes, auth routes return a pending state but all other platform features are live.</div>
  </section>

  <section class="doc-section" id="architecture">
    <div class="section-head"><span class="section-num">02</span><h2>System <span class="accent">Architecture</span></h2></div>
    <div class="prose">
      <h3>Infrastructure</h3>
      <ul>
        <li><strong>VM:</strong> Oracle Always Free ARM — Ubuntu 22.04 @ <code>129.80.222.152</code></li>
        <li><strong>Web server:</strong> nginx → Gunicorn :5000</li>
        <li><strong>App:</strong> Flask + Gunicorn 2 workers, systemd service</li>
        <li><strong>Database:</strong> Oracle Autonomous DB — DSN <code>tiktokdb_high</code></li>
        <li><strong>Object storage:</strong> OCI bucket <code>triptokforge</code>, region <code>us-ashburn-1</code></li>
        <li><strong>Auth:</strong> Epic Games OAuth2 — pending brand approval</li>
      </ul>
    </div>
    <div class="callout blue"><span class="callout-label blue">Deploy flow</span>Commit locally → push to GitHub master → SSH to Oracle VM → <code>git pull</code> → <code>sudo systemctl restart islandforge</code></div>
  </section>

  <section class="doc-section" id="routes">
    <div class="section-head"><span class="section-num">03</span><h2>Routes <span class="accent">Reference</span></h2></div>
    <table class="doc-table">
      <thead><tr><th>Method</th><th>Route</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/home</code></td><td>Homepage — member/island/track counts</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/forge</code></td><td>Island Forge audio → heightmap generator</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/gallery</code></td><td>Island gallery from Oracle DB</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/feed</code></td><td>TikTok-style social feed</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/channels</code></td><td>65-channel TV guide + embedded player</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/community</code></td><td>Members + announcements</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/dashboard</code></td><td>Member dashboard (requires Epic login)</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/admin</code></td><td>Admin panel — password gated</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/whitepages</code></td><td>This developer documentation hub</td></tr>
        <tr><td><span class="td-method method-get">GET</span></td><td><code>/health</code></td><td>JSON health check</td></tr>
        <tr><td><span class="td-method method-post">POST</span></td><td><code>/api/post</code></td><td>Submit a social feed post</td></tr>
        <tr><td><span class="td-method method-post">POST</span></td><td><code>/api/like/&lt;id&gt;</code></td><td>Like a feed post</td></tr>
        <tr><td><span class="td-method method-post">POST</span></td><td><code>/api/suggest_channel</code></td><td>Suggest a new channel</td></tr>
      </tbody>
    </table>
  </section>

  <section class="doc-section" id="database">
    <div class="section-head"><span class="section-num">04</span><h2>Database <span class="accent">Schema</span></h2></div>
    <div class="prose"><p>Oracle Autonomous Database via <code>python-oracledb</code> thin mode. All tables auto-created via <code>init_schema()</code> on first run.</p></div>
    <table class="doc-table">
      <thead><tr><th>Table</th><th>Key Columns</th><th>Purpose</th></tr></thead>
      <tbody>
        <tr><td><code>members</code></td><td><code>epic_id</code>, <code>display_name</code>, <code>skin_img</code>, <code>level</code></td><td>Epic OAuth users — profile, skin, stats</td></tr>
        <tr><td><code>island_saves</code></td><td><code>epic_id</code>, <code>island_name</code>, <code>image_url</code>, <code>oci_key</code></td><td>Generated islands + OCI URLs</td></tr>
        <tr><td><code>audio_tracks</code></td><td><code>epic_id</code>, <code>track_name</code>, <code>oci_url</code>, <code>bpm</code></td><td>Uploaded audio + OCI URLs</td></tr>
        <tr><td><code>announcements</code></td><td><code>title</code>, <code>body</code>, <code>pinned</code></td><td>Admin posts shown on community page</td></tr>
        <tr><td><code>posts</code></td><td><code>epic_id</code>, <code>caption</code>, <code>embed_url</code>, <code>likes</code></td><td>Social feed posts</td></tr>
        <tr><td><code>channels</code></td><td><code>name</code>, <code>category</code>, <code>embed_url</code>, <code>approved</code></td><td>Channel guide — 65 seeded</td></tr>
      </tbody>
    </table>
    <div class="callout amber"><span class="callout-label">ORA-00955 pattern</span>Oracle doesn't support <code>CREATE TABLE IF NOT EXISTS</code>. Catch <code>ORA-00955</code> and continue silently.</div>
  </section>

  <section class="doc-section" id="verse-arch">
    <div class="section-head"><span class="section-num">05</span><h2>Verse <span class="accent">Architecture</span></h2></div>
    <div class="prose">
      <p>Tarkov-Lite game systems built in Verse for UEFN. All files communicate through shared <code>player_data</code> class references. No global mutable state — everything flows through immutable data constructors.</p>
      <h3>Core patterns</h3>
      <ul>
        <li><strong>Immutable player data:</strong> <code>MakePlayerData(Data)</code> — never mutate in place</li>
        <li><strong>Manager isolation:</strong> each system is a standalone Verse file, no circular imports</li>
        <li><strong>UI state:</strong> <code>weak_map(player, canvas)</code> pattern</li>
        <li><strong>Material encoding:</strong> <code>rarity * 18 + element</code> = single index into 108-slot array</li>
        <li><strong>Persistence:</strong> <code>@persist</code> applied to field types, not the class</li>
      </ul>
    </div>
  </section>

  <section class="doc-section" id="verse-files">
    <div class="section-head"><span class="section-num">06</span><h2>Verse File <span class="accent">Reference</span></h2></div>
    <div class="prose"><p>Build command: <strong>UEFN → Verse → Build Verse Code</strong>. Each file is self-contained.</p></div>
    <div class="file-grid">
      <div class="file-card done"><div class="fc-name">player_data.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Core persistence class — coins, gold, bag, XP, level, farm plots, death stats.</div></div>
      <div class="file-card done"><div class="fc-name">persistence_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Join/leave hooks, new player init, 72hr shield.</div></div>
      <div class="file-card done"><div class="fc-name">death_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Death penalty — 100% under 5 stacks, 75% over. Kill credit to XP + Quest.</div></div>
      <div class="file-card done"><div class="fc-name">farm_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">32 plots × 5 slots, 18 element seeds, co-op water/harvest, grow timer.</div></div>
      <div class="file-card done"><div class="fc-name">hud_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">4-row HUD: coins/gold/bag/shield, level/XP, stats, quest progress.</div></div>
      <div class="file-card done"><div class="fc-name">vendor_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Sell by category, sell all, insurance token purchases.</div></div>
      <div class="file-card done"><div class="fc-name">material_values.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Rarity-aware values — Common→Mythic ×75, 5 categories × 18 elements.</div></div>
      <div class="file-card done"><div class="fc-name">quest_manager.verse <span class="fc-status done">DONE</span></div><div class="fc-desc">Kill/Extract/Deposit/Harvest/ZoneClear/NightmareElim hooks.</div></div>
      <div class="file-card wip"><div class="fc-name">sky_manager.verse <span class="fc-status todo">TODO</span></div><div class="fc-desc">Day/night cycle, weather roller, 16 day_sequence_device swap.</div></div>
      <div class="file-card wip"><div class="fc-name">season_manager.verse <span class="fc-status todo">TODO</span></div><div class="fc-desc">4 seasons in EventFlags, cross-system broadcast.</div></div>
      <div class="file-card wip"><div class="fc-name">loot_pool_manager.verse <span class="fc-status todo">TODO</span></div><div class="fc-desc">3-layer weighted roll: zone table → rarity → player modifier.</div></div>
      <div class="file-card wip"><div class="fc-name">world_evolution_manager.verse <span class="fc-status todo">TODO</span></div><div class="fc-desc">Activity tracking, path prop swaps, build persistence.</div></div>
    </div>
  </section>

  <section class="doc-section" id="island-forge">
    <div class="section-head"><span class="section-num">07</span><h2>Island <span class="accent">Forge</span></h2></div>
    <div class="steps">
      <div class="step"><div class="step-num">01</div><div class="step-body"><strong>Audio Upload</strong><p><code>file_compressor.py</code> auto-compresses to 128k MP3 via ffmpeg.</p></div></div>
      <div class="step"><div class="step-num">02</div><div class="step-body"><strong>Frequency Analysis</strong><p>librosa extracts bass (mountains), mid (terrain), high (rivers) bands.</p></div></div>
      <div class="step"><div class="step-num">03</div><div class="step-body"><strong>Heightmap Generation</strong><p>Bass energy = elevation. Rhythm = terrain variation. Tone = biome assignment.</p></div></div>
      <div class="step"><div class="step-num">04</div><div class="step-body"><strong>OCI Export</strong><p>Island image + metadata stored in OCI. URL saved to <code>island_saves</code> table.</p></div></div>
    </div>
  </section>

  <section class="doc-section" id="epic-oauth">
    <div class="section-head"><span class="section-num">08</span><h2>Epic <span class="accent">OAuth</span></h2></div>
    <div class="callout red"><span class="callout-label">Pending</span>Current deployment ID <code>b4d6e13c2206494a88d6ea1783129dad</code> is under Epic brand review. Approved ID ready to swap: <code>8c57f3550d41430f9cf2ff2be4695fbf</code></div>
    <div class="prose"><p>When approval arrives, update <code>EPIC_DEPLOYMENT_ID</code> in <code>/etc/systemd/system/islandforge.service</code> then run <code>sudo systemctl daemon-reload && sudo systemctl restart islandforge</code>.</p></div>
  </section>

  <section class="doc-section" id="tarkov-vision">
    <div class="section-head"><span class="section-num">09</span><h2>Tarkov-Lite <span class="accent">Vision</span></h2></div>
    <div class="prose">
      <p>Persistent extraction MMO on Fortnite — Tarkov-style risk/reward, tiered PvE zones, safe town hub, farm system, death penalty, insurance tokens, leaderboards, V-Bucks cosmetics store.</p>
      <h3>Zone tiers</h3>
      <ul>
        <li><strong>Frontier</strong> — starter zone, low risk, low reward</li>
        <li><strong>Wildlands</strong> — mid tier, PvPvE, moderate loot</li>
        <li><strong>Corrupted</strong> — high risk, rare drops, elite enemies</li>
        <li><strong>Nightmare</strong> — endgame, max death penalty, mythic loot</li>
      </ul>
      <h3>Death penalty</h3>
      <ul>
        <li>Under 5 stacks — lose 100% of carried inventory</li>
        <li>Over 5 stacks — lose 75%, insurance tokens can protect specific items</li>
      </ul>
    </div>
  </section>

</main>
</div>
<footer class="doc-footer">
  <svg width="18" height="18" viewBox="0 0 256 256"><rect width="256" height="256" rx="44" fill="#07090d"/><rect x="44" y="62" width="168" height="34" fill="#00e5a0"/><rect x="99" y="96" width="58" height="100" fill="#00e5a0"/><polygon points="82,62 118,62 156,130 120,130" fill="#07090d"/><rect x="99" y="130" width="58" height="66" fill="#00e5a0"/><rect x="44" y="196" width="168" height="10" fill="#0091ff"/></svg>
  <span class="teal">TRIPTOKFORGE</span><span>/</span><span>WHITEPAGES — INTERNAL DEVELOPER REFERENCE</span>
  <span style="margin-left:auto;">© 2026 EuphoriÆ Studios</span>
</footer>
<script>
const sections=document.querySelectorAll('.doc-section[id]');
const links=document.querySelectorAll('.sb-link');
const obs=new IntersectionObserver((entries)=>{entries.forEach(e=>{if(e.isIntersecting){links.forEach(l=>l.classList.remove('active'));const a=document.querySelector(`.sb-link[href="#${e.target.id}"]`);if(a)a.classList.add('active')}})},{rootMargin:'-20% 0px -70% 0px'});
sections.forEach(s=>obs.observe(s));
</script>
</body>
</html>"""

with open(WP_HTML, "w") as f:
    f.write(HTML)
print(f"✓ Wrote whitepages.html ({len(HTML):,} bytes)")

# ── STEP 4: RESTART ─────────────────────────────────────────────
print("\n▸ Restarting service...")
subprocess.run(["sudo", "systemctl", "restart", "islandforge"], check=True)

import time
time.sleep(4)

# ── STEP 5: HEALTH CHECK ─────────────────────────────────────────
print("▸ Health check...")
result = subprocess.run(
    ["curl", "-s", "http://127.0.0.1:5000/health"],
    capture_output=True, text=True)
if result.returncode == 0 and result.stdout:
    print(f"✓ ONLINE: {result.stdout[:120]}")
    print("\n✅ Done! Visit https://triptokforge.org/whitepages")
else:
    print("✗ Service not responding — checking logs...")
    subprocess.run(["sudo", "journalctl", "-u", "islandforge", "-n", "10", "--no-pager"])
    print(f"\n⚠ If broken, restore with: cp server.py.bak2 server.py && sudo systemctl restart islandforge")
