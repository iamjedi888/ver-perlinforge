#!/usr/bin/env python3
"""
patch_restore_full.py
Restores everything lost in the blueprint refactor.

Run on VM:
    python3 ~/ver-perlinforge/islandforge/patch_restore_full.py

Restores:
  - templates/home.html         full landing page (hero, features, forge block)
  - templates/dashboard.html    holographic player card + stats + skin selector
  - templates/privacy.html      privacy policy
  - routes/forge.py             /generate /upload_audio /audio/* /download/* /random_seed /api/stats /api/cosmetics /api/set_skin
  - routes/platform.py          updated to render proper templates
  - server.py                   registers forge blueprint
"""
import os, subprocess, time

ROOT = "/home/ubuntu/ver-perlinforge/islandforge"
ROUTES = os.path.join(ROOT, "routes")
TEMPLATES = os.path.join(ROOT, "templates")
os.makedirs(TEMPLATES, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# 1. templates/home.html
# ══════════════════════════════════════════════════════════════
open(os.path.join(TEMPLATES, "home.html"), "w").write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TriptokForge — Fortnite Esports Platform</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg"/>
<link rel="manifest" href="/manifest.json"/>
<meta name="theme-color" content="#07090d"/>
<meta name="description" content="Fortnite esports community platform — island generator, live channels, social feed, player profiles."/>
<meta property="og:title" content="TriptokForge — Fortnite Esports Platform"/>
<meta property="og:description" content="Build islands, share clips, watch live channels."/>
<meta property="og:image" content="https://triptokforge.org/static/og.png"/>
<meta property="og:url" content="https://triptokforge.org"/>
<meta name="twitter:card" content="summary_large_image"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#07090d;--deep:#04060a;--panel:#0d1018;--border:#1a2535;--border2:#243040;--teal:#00e5a0;--teal-dim:#00b07a;--blue:#0091ff;--text:#c8d8e8;--dim:#4a5a70;--mid:#7a8aa8}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Rajdhani',sans-serif;font-size:17px;overflow-x:hidden;min-height:100vh}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,229,160,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,160,.025) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}
body::after{content:'';position:fixed;top:-100%;left:0;right:0;height:200%;background:linear-gradient(transparent 50%,rgba(0,229,160,.012) 50%);background-size:100% 4px;pointer-events:none;z-index:0;animation:scan 10s linear infinite}
@keyframes scan{to{transform:translateY(50%)}}
/* NAV */
nav{position:fixed;top:0;left:0;right:0;z-index:200;height:58px;display:flex;align-items:center;padding:0 40px;background:rgba(7,9,13,.94);backdrop-filter:blur(18px);border-bottom:1px solid var(--border)}
.nav-logo{font-family:'Orbitron',monospace;font-size:14px;font-weight:900;color:var(--teal);letter-spacing:3px;text-decoration:none;flex-shrink:0}
.nav-logo em{color:var(--blue);font-style:normal}
.nav-links{display:flex;gap:4px;margin-left:28px;overflow-x:auto;scrollbar-width:none}
.nav-links::-webkit-scrollbar{display:none}
.nav-links a{font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:2px;color:var(--dim);text-decoration:none;padding:5px 10px;border-radius:3px;transition:all .15s;white-space:nowrap;text-transform:uppercase}
.nav-links a:hover{color:var(--teal);background:rgba(0,229,160,.08)}
.nav-r{margin-left:auto;display:flex;gap:8px;align-items:center;flex-shrink:0}
.btn{display:inline-flex;align-items:center;gap:8px;font-family:'Orbitron',monospace;font-size:.65rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:10px 22px;text-decoration:none;transition:all .2s;border:none;cursor:pointer;clip-path:polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%)}
.btn-p{background:var(--teal);color:#000}.btn-p:hover{background:#fff;box-shadow:0 0 32px var(--teal);transform:translateY(-2px)}
.btn-o{background:transparent;color:var(--text);border:1px solid var(--border2)}.btn-o:hover{border-color:var(--teal);color:var(--teal)}
/* HERO */
.hero{position:relative;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:120px 24px 80px;z-index:1}
.hero-bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%,rgba(0,229,160,.07) 0%,transparent 70%),radial-gradient(ellipse 40% 40% at 20% 80%,rgba(0,145,255,.05) 0%,transparent 60%);z-index:-1}
.hero-tag{display:inline-block;font-family:'Share Tech Mono',monospace;font-size:.62rem;letter-spacing:4px;text-transform:uppercase;color:var(--blue);border:1px solid rgba(0,145,255,.3);padding:6px 18px;margin-bottom:32px}
h1{font-family:'Orbitron',monospace;font-size:clamp(34px,7vw,86px);font-weight:900;line-height:1;margin-bottom:24px}
.l1{color:#fff;display:block}
.l2{color:transparent;-webkit-text-stroke:1px var(--teal);display:block}
.hero p{max-width:520px;margin:0 auto 48px;font-size:18px;font-weight:300;line-height:1.7;color:var(--mid)}
.hero-btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
/* STATS BAR */
.stats-bar{position:relative;z-index:1;display:flex;justify-content:center;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:rgba(13,16,24,.7);flex-wrap:wrap}
.stat{flex:1;min-width:120px;max-width:220px;padding:26px 24px;text-align:center;border-right:1px solid var(--border)}
.stat:last-child{border-right:none}
.stat-n{font-family:'Orbitron',monospace;font-size:22px;font-weight:900;color:var(--teal);display:block}
.stat-l{font-family:'Share Tech Mono',monospace;font-size:.55rem;letter-spacing:3px;text-transform:uppercase;color:var(--dim);margin-top:4px;display:block}
/* SECTIONS */
.sec{position:relative;z-index:1;padding:90px 48px;max-width:1200px;margin:0 auto}
.s-tag{font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:4px;text-transform:uppercase;color:var(--teal);margin-bottom:16px}
h2{font-family:'Orbitron',monospace;font-size:clamp(20px,3vw,38px);font-weight:900;color:#fff;margin-bottom:14px;line-height:1.1}
.s-sub{color:var(--mid);font-size:17px;max-width:500px;line-height:1.7;margin-bottom:52px;font-weight:300}
/* FEATURE GRID */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:2px;background:var(--border);border:1px solid var(--border)}
.card{background:var(--panel);padding:38px 30px;position:relative;overflow:hidden;transition:background .3s}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--teal),transparent);opacity:0;transition:opacity .3s}
.card:hover{background:#0d1520}.card:hover::before{opacity:1}
.ci{font-size:26px;margin-bottom:18px;display:block}
.ct{font-family:'Orbitron',monospace;font-size:.75rem;font-weight:700;letter-spacing:1px;color:#fff;margin-bottom:10px}
.card p{font-size:14px;color:var(--dim);line-height:1.6;font-weight:300}
/* FORGE BLOCK */
.forge-block{position:relative;z-index:1;margin:0 48px 90px;border:1px solid var(--border);background:var(--panel);display:grid;grid-template-columns:1fr 1fr;min-height:300px;overflow:hidden}
.forge-block::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 100% at 0% 50%,rgba(0,229,160,.05) 0%,transparent 70%);pointer-events:none}
.fc{padding:52px;display:flex;flex-direction:column;justify-content:center;position:relative;z-index:1}
.fl{font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:4px;text-transform:uppercase;color:var(--blue);margin-bottom:14px}
.fc h2{margin-bottom:14px}.fc p{color:var(--mid);font-size:15px;line-height:1.7;margin-bottom:28px;font-weight:300}
.fv{position:relative;overflow:hidden;background:var(--deep);display:flex;align-items:center;justify-content:center}
.fg{position:absolute;inset:0;background-image:linear-gradient(rgba(0,229,160,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,160,.05) 1px,transparent 1px);background-size:30px 30px;animation:gm 5s linear infinite}
@keyframes gm{to{background-position:30px 30px}}
.fh{position:relative;z-index:1;font-family:'Orbitron',monospace;font-size:68px;font-weight:900;color:transparent;-webkit-text-stroke:1px rgba(0,229,160,.25);animation:pulse 3s ease-in-out infinite}
@keyframes pulse{0%,100%{-webkit-text-stroke-color:rgba(0,229,160,.25)}50%{-webkit-text-stroke-color:rgba(0,229,160,.7);text-shadow:0 0 50px rgba(0,229,160,.2)}}
/* PLATFORM LINKS */
.platform-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:32px}
.plink{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--border);padding:18px 20px;text-decoration:none;color:var(--text);transition:all .15s;font-weight:500;font-size:15px}
.plink:hover{border-color:var(--teal);color:var(--teal);background:rgba(0,229,160,.04)}
.plink-icon{font-size:1.1rem;flex-shrink:0}
/* FOOTER */
footer{position:relative;z-index:1;border-top:1px solid var(--border);padding:32px 48px;display:flex;align-items:center;justify-content:space-between;background:var(--deep);flex-wrap:wrap;gap:16px}
.f-logo{font-family:'Orbitron',monospace;font-size:.75rem;font-weight:900;color:var(--dim);letter-spacing:3px}
.f-logo em{color:var(--blue);font-style:normal}
.flinks{display:flex;gap:28px;list-style:none;flex-wrap:wrap}
.flinks a{color:var(--dim);text-decoration:none;font-size:13px;transition:color .2s}.flinks a:hover{color:var(--teal)}
.fcopy{font-size:12px;color:var(--dim);opacity:.5}
@media(max-width:768px){nav{padding:0 16px}.nav-links{display:none}.sec{padding:52px 20px}.forge-block{grid-template-columns:1fr;margin:0 16px 52px}.fv{min-height:160px}.fc{padding:32px 24px}footer{flex-direction:column;text-align:center}}
</style>
</head>
<body>
<nav>
  <a href="/home" class="nav-logo">Triptok<em>Forge</em></a>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="/forge">Island Forge</a>
    <a href="/feed">Feed</a>
    <a href="/channels">Channels</a>
    <a href="/community">Community</a>
    <a href="/whitepages">Docs</a>
    <a href="/privacy">Privacy</a>
  </div>
  <div class="nav-r">
    {% if user %}
      <a href="/dashboard" class="btn btn-p" style="padding:7px 18px">Dashboard →</a>
    {% else %}
      <a href="/auth/epic" class="btn btn-p" style="padding:7px 18px">⚡ Connect Epic</a>
    {% endif %}
  </div>
</nav>
<section class="hero">
  <div class="hero-bg"></div>
  <div>
    <div class="hero-tag">⚡ Esports Platform — Members Only</div>
    <h1><span class="l1">FORGE YOUR</span><span class="l2">LEGACY</span></h1>
    <p>Connect your Epic Games account. Build your member profile. Access tools built for serious Fortnite players and creators.</p>
    <div class="hero-btns">
      {% if user %}
        <a href="/dashboard" class="btn btn-p">Go to Dashboard →</a>
      {% else %}
        <a href="/auth/epic" class="btn btn-p">⚡ Connect Epic Account</a>
      {% endif %}
      <a href="#features" class="btn btn-o">Explore Platform →</a>
    </div>
  </div>
</section>
<div class="stats-bar">
  <div class="stat"><span class="stat-n">{{ n_members or 0 }}</span><span class="stat-l">Members</span></div>
  <div class="stat"><span class="stat-n">{{ n_islands or 0 }}</span><span class="stat-l">Islands</span></div>
  <div class="stat"><span class="stat-n">65</span><span class="stat-l">Live Channels</span></div>
  <div class="stat"><span class="stat-n">EPIC</span><span class="stat-l">OAuth Login</span></div>
  <div class="stat"><span class="stat-n">FREE</span><span class="stat-l">Always</span></div>
</div>
<section class="sec" id="features">
  <div class="s-tag">// Platform Features</div>
  <h2>Everything You Need</h2>
  <p class="s-sub">Built for Fortnite creators and competitive players. Login once with Epic, unlock everything.</p>
  <div class="grid">
    <div class="card"><span class="ci">🎮</span><div class="ct">Epic Account Login</div><p>Secure OAuth2 authentication directly through Epic Games. Your real account, your real identity.</p></div>
    <div class="card"><span class="ci">🃏</span><div class="ct">3D Member Card</div><p>Holographic player ID card with your stats, chosen skin, and rank. Shareable and always live.</p></div>
    <div class="card"><span class="ci">📊</span><div class="ct">Live Stats</div><p>K/D ratio, win rate, season performance pulled live from Fortnite and displayed on your profile.</p></div>
    <div class="card"><span class="ci">🏝️</span><div class="ct">Island Forge</div><p>Generate UEFN-ready island heightmaps from audio files. Export directly to Fortnite Creative.</p></div>
    <div class="card"><span class="ci">📺</span><div class="ct">Live Channels</div><p>65 live channels — Fortnite esports, creative, gaming, music, news. Roku-style TV guide.</p></div>
    <div class="card"><span class="ci">🎨</span><div class="ct">Skin Avatar</div><p>Browse the full Fortnite cosmetics library and pick any skin as your profile avatar.</p></div>
  </div>
</section>
<div class="forge-block">
  <div class="fc">
    <div class="fl">// Tool — Island Forge</div>
    <h2>Generate Islands<br>From Sound</h2>
    <p>Upload any audio file. Island Forge analyzes frequency bands and generates a unique UEFN-ready heightmap — mountains from bass, rivers from rhythm, biomes from tone.</p>
    <a href="/forge" class="btn btn-p">Open Island Forge →</a>
  </div>
  <div class="fv"><div class="fg"></div><div class="fh">IF</div></div>
</div>
<section class="sec" id="platform">
  <div class="s-tag">// Explore</div>
  <h2>The Platform</h2>
  <p class="s-sub">Everything TriptokForge has to offer.</p>
  <div class="platform-grid">
    <a href="/forge" class="plink"><span class="plink-icon">▲</span>Island Forge</a>
    <a href="/feed" class="plink"><span class="plink-icon">◈</span>Social Feed</a>
    <a href="/channels" class="plink"><span class="plink-icon">▶</span>Live Channels</a>
    <a href="/gallery" class="plink"><span class="plink-icon">⬡</span>Gallery</a>
    <a href="/community" class="plink"><span class="plink-icon">◉</span>Community</a>
    <a href="/dashboard" class="plink"><span class="plink-icon">◐</span>Dashboard</a>
    <a href="/whitepages" class="plink"><span class="plink-icon">◇</span>Dev Docs</a>
    <a href="/admin" class="plink"><span class="plink-icon">⚙</span>Admin</a>
  </div>
</section>
<footer>
  <div class="f-logo">Triptok<em>Forge</em></div>
  <ul class="flinks">
    <li><a href="#features">Features</a></li>
    <li><a href="/forge">Island Forge</a></li>
    <li><a href="/channels">Channels</a></li>
    <li><a href="/privacy">Privacy</a></li>
  </ul>
  <div class="fcopy">© 2026 EuphoriÆ Studios</div>
</footer>
</body></html>""")
print("✓ templates/home.html")

# ══════════════════════════════════════════════════════════════
# 2. templates/dashboard.html
# ══════════════════════════════════════════════════════════════
open(os.path.join(TEMPLATES, "dashboard.html"), "w").write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ name }} — TriptokForge Dashboard</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#07090d;--deep:#04060a;--panel:#0d1018;--border:#1a2535;--border2:#243040;--teal:#00e5a0;--blue:#0091ff;--text:#c8d8e8;--dim:#4a5a70;--mid:#7a8aa8}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Rajdhani',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,229,160,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,160,.025) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}
nav{position:fixed;top:0;left:0;right:0;z-index:200;height:58px;display:flex;align-items:center;padding:0 40px;background:rgba(7,9,13,.94);backdrop-filter:blur(18px);border-bottom:1px solid var(--border)}
.nav-logo{font-family:'Orbitron',monospace;font-size:14px;font-weight:900;color:var(--teal);letter-spacing:3px;text-decoration:none}
.nav-logo em{color:var(--blue);font-style:normal}
.nav-r{margin-left:auto;display:flex;gap:20px;align-items:center}
.nav-r a{color:var(--dim);text-decoration:none;font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:2px;text-transform:uppercase;transition:color .2s}
.nav-r a:hover{color:var(--teal)}.logout{color:var(--blue)!important}
.dash{position:relative;z-index:1;max-width:1300px;margin:0 auto;padding:90px 48px 80px}
.dash-grid{display:grid;grid-template-columns:360px 1fr;gap:28px;align-items:start}
/* HOLO CARD */
.card-wrap{perspective:1200px}
.holo-card{width:340px;height:520px;border-radius:14px;background:linear-gradient(135deg,var(--panel) 0%,#0d2040 50%,var(--panel) 100%);border:1px solid var(--border);position:relative;overflow:hidden;transform-style:preserve-3d;transition:transform .1s ease;cursor:pointer;box-shadow:0 0 40px rgba(0,229,160,.08),inset 0 0 60px rgba(0,229,160,.02)}
.holo-card::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,229,160,.12) 0%,transparent 30%,rgba(0,145,255,.07) 60%,transparent 80%,rgba(0,229,160,.08) 100%);z-index:2;pointer-events:none;animation:holo 4s ease-in-out infinite}
@keyframes holo{0%,100%{opacity:.6}50%{opacity:1}}
.holo-card::after{content:'';position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,229,160,.02) 2px,rgba(0,229,160,.02) 4px);z-index:3;pointer-events:none}
.ch{position:relative;z-index:4;padding:18px 22px 0;display:flex;justify-content:space-between;align-items:center}
.ch-s{font-family:'Orbitron',monospace;font-size:.6rem;letter-spacing:3px;color:var(--teal);text-transform:uppercase}
.ch-id{font-family:'Share Tech Mono',monospace;font-size:.6rem;color:var(--dim);letter-spacing:1px}
.cskin{position:relative;z-index:4;height:280px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.cskin img{max-height:280px;max-width:100%;object-fit:contain;filter:drop-shadow(0 0 18px rgba(0,229,160,.35));animation:float 3s ease-in-out infinite}
.no-skin{font-family:'Orbitron',monospace;font-size:46px;font-weight:900;color:transparent;-webkit-text-stroke:1px rgba(0,229,160,.18)}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.cinfo{position:relative;z-index:4;padding:0 22px 18px}
.cname{font-family:'Orbitron',monospace;font-size:17px;font-weight:900;color:#fff;letter-spacing:1px;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.csname{font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--teal);letter-spacing:2px;text-transform:uppercase;margin-bottom:14px}
.cstats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}
.csv{background:rgba(0,229,160,.04);border:1px solid rgba(0,229,160,.1);padding:7px;text-align:center}
.csv-v{font-family:'Orbitron',monospace;font-size:13px;font-weight:700;color:var(--teal);display:block}
.csv-l{font-family:'Share Tech Mono',monospace;font-size:.5rem;letter-spacing:2px;text-transform:uppercase;color:var(--dim)}
.cglow{position:absolute;bottom:-40px;left:50%;transform:translateX(-50%);width:200px;height:80px;background:radial-gradient(ellipse,rgba(0,229,160,.18) 0%,transparent 70%);z-index:1;animation:glow 3s ease-in-out infinite}
@keyframes glow{0%,100%{opacity:.5}50%{opacity:1}}
/* RIGHT PANEL */
.rp{display:flex;flex-direction:column;gap:20px}
.pb{background:var(--panel);border:1px solid var(--border);padding:28px}
.pt{font-family:'Orbitron',monospace;font-size:.7rem;font-weight:700;letter-spacing:2px;color:var(--teal);text-transform:uppercase;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.welcome{font-family:'Orbitron',monospace;font-size:clamp(15px,2vw,24px);font-weight:900;color:#fff;margin-bottom:6px}
.welcome span{color:var(--teal)}
.wsub{color:var(--mid);font-size:14px;line-height:1.6;margin-bottom:20px;font-weight:300}
.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.tbtn{display:flex;align-items:center;gap:10px;background:rgba(0,229,160,.04);border:1px solid var(--border);padding:14px 18px;text-decoration:none;color:var(--text);transition:all .2s;font-size:14px;font-weight:500}
.tbtn:hover{border-color:var(--teal);background:rgba(0,229,160,.07);color:var(--teal)}
/* STATS GRID */
.sgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.sbox{background:rgba(0,229,160,.03);border:1px solid var(--border);padding:18px;text-align:center}
.sv{font-family:'Orbitron',monospace;font-size:20px;font-weight:900;color:var(--teal);display:block}
.sl2{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin-top:3px;display:block}
#statsMsg{color:var(--mid);font-size:13px;margin-top:10px;letter-spacing:1px}
/* SKIN SELECTOR */
.skin-search{width:100%;background:rgba(0,229,160,.04);border:1px solid var(--border);color:var(--text);font-family:'Rajdhani',sans-serif;font-size:15px;padding:10px 14px;margin-bottom:14px;outline:none;border-radius:2px}
.skin-search:focus{border-color:var(--teal)}
.skin-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:6px;max-height:280px;overflow-y:auto;scrollbar-width:thin}
.si{background:rgba(0,229,160,.03);border:1px solid var(--border);padding:7px;cursor:pointer;transition:all .15s;text-align:center;border-radius:2px}
.si:hover,.si.active{border-color:var(--teal);background:rgba(0,229,160,.08)}
.si img{width:100%;aspect-ratio:1;object-fit:cover}
.si-n{font-size:9px;color:var(--dim);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.loading{color:var(--dim);font-size:13px;letter-spacing:2px;text-align:center;padding:20px;font-family:'Share Tech Mono',monospace}
@media(max-width:900px){.dash-grid{grid-template-columns:1fr}.holo-card{width:100%;height:auto}.cskin{height:220px}.tgrid{grid-template-columns:1fr}nav{padding:0 16px}}
</style>
</head>
<body>
<nav>
  <a href="/home" class="nav-logo">Triptok<em>Forge</em></a>
  <div class="nav-r">
    <a href="/forge">Island Forge</a>
    <a href="/channels">Channels</a>
    <a href="/feed">Feed</a>
    <a href="/auth/logout" class="logout">Logout</a>
  </div>
</nav>
<div class="dash">
  <div class="dash-grid">
    <div class="card-wrap">
      <div class="holo-card" id="holoCard">
        <div class="ch"><span class="ch-s">EuphoriÆ Studios</span><span class="ch-id">MEMBER</span></div>
        <div class="cskin" id="cardSkin">
          {% if skin_img %}
            <img src="{{ skin_img }}" id="skinImg"/>
          {% else %}
            <div class="no-skin">FN</div>
          {% endif %}
        </div>
        <div class="cinfo">
          <div class="cname">{{ name }}</div>
          <div class="csname" id="cardSkinName">{{ skin_name or 'Default' }}</div>
          <div class="cstats">
            <div class="csv"><span class="csv-v" id="cWins">—</span><span class="csv-l">Wins</span></div>
            <div class="csv"><span class="csv-v" id="cKD">—</span><span class="csv-l">K/D</span></div>
            <div class="csv"><span class="csv-v" id="cMatches">—</span><span class="csv-l">Matches</span></div>
          </div>
        </div>
        <div class="cglow"></div>
      </div>
    </div>
    <div class="rp">
      <div class="pb">
        <div class="welcome">Welcome, <span>{{ name }}</span></div>
        <div class="wsub">Your TriptokForge member dashboard. Access all platform tools and manage your profile.</div>
        <div class="tgrid">
          <a href="/forge" class="tbtn">🏝️ Island Forge</a>
          <a href="#skins" class="tbtn">🎨 Change Skin</a>
          <a href="#stats" class="tbtn" onclick="loadStats()">📊 Refresh Stats</a>
          <a href="/auth/logout" class="tbtn">🚪 Logout</a>
        </div>
      </div>
      <div class="pb" id="stats">
        <div class="pt">// Fortnite Stats</div>
        <div class="sgrid">
          <div class="sbox"><span class="sv" id="s-wins">—</span><span class="sl2">Total Wins</span></div>
          <div class="sbox"><span class="sv" id="s-kd">—</span><span class="sl2">K/D Ratio</span></div>
          <div class="sbox"><span class="sv" id="s-matches">—</span><span class="sl2">Matches</span></div>
          <div class="sbox"><span class="sv" id="s-kills">—</span><span class="sl2">Total Kills</span></div>
          <div class="sbox"><span class="sv" id="s-winpct">—</span><span class="sl2">Win Rate</span></div>
          <div class="sbox"><span class="sv" id="s-score">—</span><span class="sl2">Score/Match</span></div>
        </div>
        <div id="statsMsg"></div>
      </div>
      <div class="pb" id="skins">
        <div class="pt">// Choose Your Skin</div>
        <input class="skin-search" type="text" placeholder="Search skins..." id="skinSearch" oninput="filterSkins()"/>
        <div class="skin-grid" id="skinGrid"><div class="loading">Loading cosmetics...</div></div>
      </div>
    </div>
  </div>
</div>
<script>
const DISPLAY_NAME = {{ name|tojson }};
const card = document.getElementById('holoCard');
card.addEventListener('mousemove', e => {
  const r = card.getBoundingClientRect(), x = (e.clientX-r.left)/r.width-.5, y = (e.clientY-r.top)/r.height-.5;
  card.style.transform = `rotateY(${x*18}deg) rotateX(${-y*14}deg) scale(1.02)`;
});
card.addEventListener('mouseleave', () => { card.style.transform = 'rotateY(0) rotateX(0) scale(1)'; });

async function loadStats() {
  document.getElementById('statsMsg').textContent = 'Loading stats...';
  try {
    const r = await fetch(`/api/stats?name=${encodeURIComponent(DISPLAY_NAME)}`), d = await r.json();
    if (d.ok) {
      const s = d.stats;
      ['wins','kd','matches','kills','winPct','score'].forEach((k,i) => {
        const ids = ['s-wins','s-kd','s-matches','s-kills','s-winpct','s-score'];
        document.getElementById(ids[i]).textContent = s[k] || '—';
      });
      document.getElementById('cWins').textContent = s.wins || '—';
      document.getElementById('cKD').textContent = s.kd || '—';
      document.getElementById('cMatches').textContent = s.matches || '—';
      document.getElementById('statsMsg').textContent = '';
    } else {
      document.getElementById('statsMsg').textContent = 'Stats not found — make sure your Fortnite account is public.';
    }
  } catch(e) { document.getElementById('statsMsg').textContent = 'Could not load stats.'; }
}

let allSkins = [];
async function loadSkins() {
  try {
    const r = await fetch('/api/cosmetics'), d = await r.json();
    if (d.ok) { allSkins = d.skins; renderSkins(allSkins); }
  } catch(e) { document.getElementById('skinGrid').innerHTML = '<div class="loading">Could not load cosmetics.</div>'; }
}
function renderSkins(skins) {
  const g = document.getElementById('skinGrid');
  if (!skins.length) { g.innerHTML = '<div class="loading">No results.</div>'; return; }
  g.innerHTML = skins.slice(0,120).map(s =>
    `<div class="si" onclick="selectSkin('${s.id}','${s.name.replace(/'/g,"\\'")}','${s.img}')" title="${s.name}">
      <img src="${s.img}" loading="lazy"/><div class="si-n">${s.name}</div></div>`
  ).join('');
}
function filterSkins() {
  const q = document.getElementById('skinSearch').value.toLowerCase();
  renderSkins(q ? allSkins.filter(s => s.name.toLowerCase().includes(q)) : allSkins);
}
async function selectSkin(id, name, img) {
  document.querySelectorAll('.si').forEach(el => el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('cardSkin').innerHTML = `<img src="${img}" style="max-height:280px;max-width:100%;object-fit:contain;filter:drop-shadow(0 0 18px rgba(0,229,160,.35));animation:float 3s ease-in-out infinite"/>`;
  document.getElementById('cardSkinName').textContent = name;
  await fetch('/api/set_skin', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id, name, img})});
}
loadStats(); loadSkins();
</script>
</body></html>""")
print("✓ templates/dashboard.html")

# ══════════════════════════════════════════════════════════════
# 3. templates/privacy.html
# ══════════════════════════════════════════════════════════════
open(os.path.join(TEMPLATES, "privacy.html"), "w").write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Privacy Policy — TriptokForge</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@300;400;500&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#07090d;--panel:#0d1018;--border:#1a2535;--teal:#00e5a0;--blue:#0091ff;--text:#c8d8e8;--dim:#4a5a70;--mid:#7a8aa8}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Rajdhani',sans-serif;min-height:100vh;padding:90px 0 60px}
nav{position:fixed;top:0;left:0;right:0;height:58px;display:flex;align-items:center;padding:0 40px;background:rgba(7,9,13,.94);backdrop-filter:blur(18px);border-bottom:1px solid var(--border);z-index:200}
.nav-logo{font-family:'Orbitron',monospace;font-size:14px;font-weight:900;color:var(--teal);letter-spacing:3px;text-decoration:none}
.nav-logo em{color:var(--blue);font-style:normal}
.wrap{max-width:700px;margin:0 auto;padding:40px 24px}
.box{background:var(--panel);border:1px solid var(--border);padding:32px;margin-bottom:16px}
h1{font-family:'Orbitron',monospace;font-size:1.4rem;font-weight:700;letter-spacing:3px;color:var(--teal);margin-bottom:20px}
h2{font-family:'Orbitron',monospace;font-size:.85rem;font-weight:700;letter-spacing:2px;color:#fff;margin-bottom:10px}
p,li{font-size:14px;color:var(--mid);line-height:1.75;font-weight:300;margin-bottom:8px}
ul{margin-left:18px;margin-bottom:8px}
a{color:var(--teal)}
</style>
</head>
<body>
<nav><a href="/home" class="nav-logo">Triptok<em>Forge</em></a></nav>
<div class="wrap">
  <div class="box">
    <h1>Privacy Policy</h1>
    <p>Last updated: March 2026</p>
  </div>
  <div class="box">
    <h2>What We Collect</h2>
    <ul>
      <li>Epic Games account ID and display name (via Epic OAuth)</li>
      <li>Selected skin/avatar preference</li>
      <li>Generated island metadata (seed, size, audio weights)</li>
      <li>Audio files you upload for island generation</li>
    </ul>
  </div>
  <div class="box">
    <h2>What We Don't Collect</h2>
    <ul>
      <li>Passwords — authentication is entirely through Epic Games</li>
      <li>Payment information — the platform is free</li>
      <li>Location data, IP addresses, or browsing history</li>
    </ul>
  </div>
  <div class="box">
    <h2>Data Storage</h2>
    <p>Member data is stored in Oracle Autonomous Database on Oracle Cloud Infrastructure in the US. Audio files are stored in OCI Object Storage and may be deleted after 30 days.</p>
  </div>
  <div class="box">
    <h2>Epic OAuth</h2>
    <p>Login is handled entirely by Epic Games. We never see or store your Epic password. We receive only your account ID and display name from Epic's API.</p>
  </div>
  <div class="box">
    <h2>Contact</h2>
    <p>For privacy questions: <a href="https://github.com/iamjedi888">github.com/iamjedi888</a></p>
  </div>
</div>
</body></html>""")
print("✓ templates/privacy.html")

# ══════════════════════════════════════════════════════════════
# 4. routes/forge.py  — all forge + audio + api endpoints
# ══════════════════════════════════════════════════════════════
open(os.path.join(ROUTES, "forge.py"), "w").write('''"""
routes/forge.py — Island Forge + Audio + Fortnite API endpoints
Restored from server_old.py.
"""
import io, base64, json, os, sys, traceback, secrets
import urllib.parse, urllib.request

import numpy as np
from flask import Blueprint, request, jsonify, send_file, session, redirect

forge_bp = Blueprint("forge", __name__)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR  = os.path.join(BASE_DIR, "saved_audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_EXTS = (".wav",".mp3",".flac",".ogg",".aac",".m4a",".aiff",".opus")
FORTNITE_STATS_URL = "https://fortnite-api.com/v2/stats/br/v2"
FORTNITE_COSMETICS = "https://fortnite-api.com/v2/cosmetics/br"

try:
    from audio_to_heightmap import (
        analyse_audio, generate_terrain, generate_moisture,
        classify_biomes, find_plot_positions, build_layout,
        build_preview, paint_farm_biome, get_farm_cluster_info,
        BIOME_NAMES, BIOME_COLOURS,
        WORLD_SIZE_PRESETS, DEFAULT_WORLD_SIZE_CM,
    )
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    from town_generator import generate_town, BIOME_TOWN
    TOWN_GEN_AVAILABLE = True
except ImportError:
    TOWN_GEN_AVAILABLE = False

try:
    from oracle_db import update_member_skin
except ImportError:
    def update_member_skin(*a, **k): pass

_state = {
    "heightmap_bytes": None, "layout": None, "preview_bytes": None,
    "audio_path": None, "audio_filename": None, "audio_weights": None,
}
DEFAULT_WEIGHTS = {
    "sub_bass":0.5,"bass":0.5,"midrange":0.5,
    "presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":0.0,
}
_cosmetics_cache = None

# ── FORGE PAGE ───────────────────────────────────────────────
@forge_bp.route("/forge")
def forge():
    path = os.path.join(BASE_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

# ── GENERATE ─────────────────────────────────────────────────
@forge_bp.route("/generate", methods=["POST"])
def generate():
    if not AUDIO_AVAILABLE:
        return jsonify({"ok": False, "error": "audio_to_heightmap not available"}), 500
    try:
        data           = request.get_json(force=True)
        seed           = int(data.get("seed", 42))
        size           = int(data.get("size", 2017))
        n_plots        = int(data.get("plots", 32))
        spacing        = int(data.get("spacing", 40))
        weights        = data.get("weights", DEFAULT_WEIGHTS)
        water_level    = float(data.get("water_level", 0.20))
        world_wrap     = bool(data.get("world_wrap", True))
        cluster_angle  = float(data.get("cluster_angle", 135.0))
        cluster_spread = float(data.get("cluster_spread", 1.0))
        ws_raw = data.get("world_size", "double_br")
        if isinstance(ws_raw, str) and ws_raw in WORLD_SIZE_PRESETS:
            world_size_cm = WORLD_SIZE_PRESETS[ws_raw]
        else:
            world_size_cm = int(data.get("world_size_cm", DEFAULT_WORLD_SIZE_CM))
        water_level    = max(0.0, min(0.48, water_level))
        cluster_spread = max(0.5, min(2.0, cluster_spread))
        if size not in (505, 1009, 2017, 4033): size = 1009
        for k, v in DEFAULT_WEIGHTS.items(): weights.setdefault(k, v)
        height, road_mask = generate_terrain(size, seed, weights, water_level)
        moisture = generate_moisture(size, seed)
        biome    = classify_biomes(height, moisture, water_level)
        town_data = street_mask = town_mask = farm_mask = None
        if TOWN_GEN_AVAILABLE:
            from audio_to_heightmap import build_island_mask
            island_mask = build_island_mask(size, seed, weights.get("presence", 0.5), weights.get("tempo_bpm", 120.0))
            if BIOME_TOWN not in BIOME_NAMES:
                BIOME_NAMES[BIOME_TOWN] = "Town"; BIOME_COLOURS[BIOME_TOWN] = (158, 148, 132)
            height, biome, plots, town_data, street_mask, town_mask, farm_mask = generate_town(
                height, biome, island_mask, size, seed, weights,
                n_plots=n_plots, cluster_angle_deg=cluster_angle, cluster_spread=cluster_spread * 0.22)
        else:
            plots = find_plot_positions(height, biome, n_plots, size, min_spacing=spacing, cluster_angle_deg=cluster_angle, cluster_spread=cluster_spread)
            biome = paint_farm_biome(biome, plots, size)
        layout = build_layout(height, biome, plots, size, seed, weights, water_level, world_wrap, world_size_cm)
        if town_data:
            layout["town_data"] = town_data
            layout["town_center"] = {"pixel": town_data["center_pixel"], "world_x_cm": town_data["center_world_x"], "world_z_cm": town_data["center_world_z"]}
        from PIL import Image
        hm_16 = (height * 65535).astype(np.uint16)
        hm_img = Image.fromarray(hm_16)
        hm_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_heightmap.png"))
        hm_buf = io.BytesIO(); hm_img.save(hm_buf, format="PNG")
        _state["heightmap_bytes"] = hm_buf.getvalue()
        with open(os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json"), "w") as jf:
            json.dump(layout, jf, indent=2)
        _state["layout"] = layout
        prev_size = min(size, 1009)
        if prev_size < size:
            factor = size // prev_size
            h_dn = height[::factor, ::factor][:prev_size, :prev_size]
            b_dn = biome[::factor, ::factor][:prev_size, :prev_size]
            rm_dn = road_mask[::factor, ::factor][:prev_size, :prev_size] if road_mask is not None else None
            p_dn = [(r // factor, c // factor) for r, c in plots]
        else:
            h_dn, b_dn, p_dn, rm_dn = height, biome, plots, road_mask
        prev_rgb = build_preview(h_dn, b_dn, p_dn, prev_size, rm_dn)
        if TOWN_GEN_AVAILABLE and town_data and street_mask is not None:
            from town_generator import build_street_grid, classify_blocks, place_lots_in_block, render_town_overlay
            tc = town_data["center_pixel"]; scale = prev_size / size
            tc_s = (int(tc[0]*scale), int(tc[1]*scale)); f = max(1, size // prev_size)
            s_dn = street_mask[::f, ::f][:prev_size, :prev_size]
            tm_dn = town_mask[::f, ::f][:prev_size, :prev_size]
            fm_dn = farm_mask[::f, ::f][:prev_size, :prev_size]
            st, bl = build_street_grid(tc_s[0], tc_s[1], prev_size)
            bl = classify_blocks(bl, tc_s[0], tc_s[1])
            lots = []
            for b in bl: lots.extend(place_lots_in_block(b, prev_size, b.get("type", "residential")))
            p_s = [(int(r*scale), int(c*scale)) for r, c in plots]
            prev_rgb = render_town_overlay(prev_rgb, s_dn, tm_dn, fm_dn, p_s, bl, lots, prev_size)
        prev_img = Image.fromarray(prev_rgb, mode="RGB")
        prev_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_preview.png"))
        prev_buf = io.BytesIO(); prev_img.save(prev_buf, format="PNG")
        _state["preview_bytes"] = prev_buf.getvalue()
        prev_b64 = base64.b64encode(_state["preview_bytes"]).decode("utf-8")
        total = size * size
        biome_stats = [{"name": BIOME_NAMES.get(b, "?"), "pct": round(float(np.sum(biome == b)) / total * 100, 1), "colour": "rgb({},{},{})".format(*BIOME_COLOURS.get(b, (100,100,100)))} for b in sorted(BIOME_NAMES.keys()) if np.any(biome == b)]
        return jsonify({"ok": True, "preview_b64": prev_b64, "plots_found": len(plots), "biome_stats": biome_stats, "verse_constants": layout["verse_constants"], "town_center": layout.get("town_center"), "meta": layout["meta"], "world_wrap": world_wrap, "water_level": water_level, "world_size_cm": world_size_cm, "saved_to": OUTPUT_DIR})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok": False, "error": str(e)}), 500

# ── AUDIO ────────────────────────────────────────────────────
@forge_bp.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        if "file" not in request.files: return jsonify({"ok":False,"error":"No file"}),400
        f = request.files["file"]; ext = os.path.splitext(f.filename)[1].lower()
        if ext not in SUPPORTED_EXTS: return jsonify({"ok":False,"error":f"Unsupported: {', '.join(SUPPORTED_EXTS)}"}),400
        safe = os.path.basename(f.filename); save_path = os.path.join(AUDIO_DIR, safe)
        stem, sfx = os.path.splitext(safe); c = 1
        while os.path.exists(save_path): save_path = os.path.join(AUDIO_DIR, f"{stem}_{c}{sfx}"); c += 1
        f.save(save_path)
        if AUDIO_AVAILABLE:
            weights = analyse_audio(save_path)
        else:
            weights = DEFAULT_WEIGHTS.copy()
        _state["audio_path"] = save_path; _state["audio_filename"] = os.path.basename(save_path); _state["audio_weights"] = weights
        return jsonify({"ok":True,"filename":os.path.basename(save_path),"weights":weights})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/list")
def audio_list():
    try:
        files = [{"filename":fn,"size_kb":round(os.path.getsize(os.path.join(AUDIO_DIR,fn))/1024,1),"active":_state["audio_filename"]==fn} for fn in sorted(os.listdir(AUDIO_DIR)) if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS]
        return jsonify({"ok":True,"files":files})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/select", methods=["POST"])
def audio_select():
    try:
        data = request.get_json(force=True); path = os.path.join(AUDIO_DIR, os.path.basename(data.get("filename","")))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        weights = analyse_audio(path) if AUDIO_AVAILABLE else DEFAULT_WEIGHTS.copy()
        _state["audio_path"] = path; _state["audio_filename"] = os.path.basename(path); _state["audio_weights"] = weights
        return jsonify({"ok":True,"filename":os.path.basename(path),"weights":weights})
    except Exception as e: traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/<filename>", methods=["DELETE"])
def audio_delete(filename):
    try:
        path = os.path.join(AUDIO_DIR, os.path.basename(filename))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        os.remove(path)
        if _state["audio_filename"] == filename: _state["audio_path"] = _state["audio_filename"] = _state["audio_weights"] = None
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/stream/<filename>")
def audio_stream(filename):
    path = os.path.join(AUDIO_DIR, os.path.basename(filename))
    if not os.path.exists(path): return "Not found", 404
    ext = os.path.splitext(filename)[1].lower()
    mime = {".mp3":"audio/mpeg",".wav":"audio/wav",".ogg":"audio/ogg",".flac":"audio/flac",".aac":"audio/aac",".m4a":"audio/mp4",".aiff":"audio/aiff",".opus":"audio/opus"}.get(ext,"audio/mpeg")
    return send_file(path, mimetype=mime, conditional=True)

# ── DOWNLOADS ────────────────────────────────────────────────
@forge_bp.route("/download/heightmap")
def download_heightmap():
    if not _state["heightmap_bytes"]: return "No heightmap yet", 404
    return send_file(io.BytesIO(_state["heightmap_bytes"]), mimetype="image/png", as_attachment=True, download_name="island_heightmap.png")

@forge_bp.route("/download/layout")
def download_layout():
    if not _state["layout"]: return "No layout yet", 404
    return send_file(io.BytesIO(json.dumps(_state["layout"],indent=2).encode()), mimetype="application/json", as_attachment=True, download_name="island_layout.json")

@forge_bp.route("/download/preview")
def download_preview():
    if not _state["preview_bytes"]: return "No preview yet", 404
    return send_file(io.BytesIO(_state["preview_bytes"]), mimetype="image/png", as_attachment=True, download_name="island_preview.png")

@forge_bp.route("/random_seed")
def random_seed():
    import random; return jsonify({"seed": random.randint(1, 99999)})

# ── FORTNITE API ─────────────────────────────────────────────
@forge_bp.route("/api/stats")
def api_stats():
    name = request.args.get("name","")
    if not name: return jsonify({"ok":False,"error":"No name"})
    try:
        url = f"{FORTNITE_STATS_URL}?name={urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r: data = json.loads(r.read().decode())
        if data.get("status") != 200: return jsonify({"ok":False,"error":"Player not found"})
        ov = data.get("data",{}).get("stats",{}).get("all",{}).get("overall",{})
        wins=ov.get("wins",0); kills=ov.get("kills",0); matches=ov.get("matches",0)
        kd=ov.get("kd",0.0); score=ov.get("scorePerMatch",0)
        win_pct = f"{round(wins/matches*100,1)}%" if matches else "0%"
        return jsonify({"ok":True,"stats":{"wins":wins,"kills":kills,"matches":matches,"kd":round(kd,2),"winPct":win_pct,"score":round(score,1)}})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@forge_bp.route("/api/cosmetics")
def api_cosmetics():
    global _cosmetics_cache
    if _cosmetics_cache: return jsonify({"ok":True,"skins":_cosmetics_cache})
    try:
        req = urllib.request.Request(FORTNITE_COSMETICS, headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r: data = json.loads(r.read().decode())
        skins = []
        for item in data.get("data",[]):
            if item.get("type",{}).get("value") != "outfit": continue
            imgs = item.get("images",{}); img = imgs.get("smallIcon") or imgs.get("icon") or ""
            if not img: continue
            skins.append({"id":item.get("id",""),"name":item.get("name",""),"img":img})
        _cosmetics_cache = skins
        return jsonify({"ok":True,"skins":skins})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@forge_bp.route("/api/set_skin", methods=["POST"])
def api_set_skin():
    data = request.get_json(force=True)
    if "user" in session:
        session["user"]["skin"] = data.get("id")
        session["user"]["skin_name"] = data.get("name","")
        session["user"]["skin_img"] = data.get("img","")
        session.modified = True
        update_member_skin(
            epic_id=session["user"].get("account_id",""),
            skin_id=data.get("id",""), skin_name=data.get("name",""), skin_img=data.get("img",""))
    return jsonify({"ok":True})
''')
print("✓ routes/forge.py")

# ══════════════════════════════════════════════════════════════
# 5. routes/platform.py — updated to render proper templates
# ══════════════════════════════════════════════════════════════
open(os.path.join(ROUTES, "platform.py"), "w").write('''from flask import Blueprint, render_template, request, redirect, session, jsonify, send_from_directory, Response
import os
from oracle_db import get_all_members, get_recent_islands, get_audio_tracks, get_announcements, get_posts, post_announcement, db_available, upsert_member, status

platform_bp = Blueprint("platform", __name__)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "triptokadmin2026")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def serve_index():
    return send_from_directory(ROOT, "index.html")

@platform_bp.route("/")
@platform_bp.route("/home")
def home():
    user = session.get("user")
    members = get_all_members() or []
    islands = get_recent_islands(limit=999) or []
    return render_template("home.html",
        user=user,
        n_members=len(members),
        n_islands=len(islands))

@platform_bp.route("/gallery")
def gallery():
    return serve_index()

@platform_bp.route("/feed")
def feed():
    posts = get_posts(limit=50)
    from flask import current_app
    t = os.path.join(ROOT, "templates", "feed.html")
    if os.path.exists(t):
        return render_template("feed.html", posts=posts)
    return serve_index()

@platform_bp.route("/community")
def community():
    t = os.path.join(ROOT, "templates", "community.html")
    if os.path.exists(t):
        return render_template("community.html", members=get_all_members(), announcements=get_announcements())
    return serve_index()

@platform_bp.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        epic_id = session.get("epic_id")
        if not epic_id:
            return redirect("/auth/epic")
        user = {"display_name": session.get("display_name", epic_id),
                "account_id": epic_id,
                "skin_img": session.get("skin_img",""),
                "skin_name": session.get("skin_name","Default")}
    return render_template("dashboard.html",
        name=user.get("display_name","Player"),
        skin_img=user.get("skin_img",""),
        skin_name=user.get("skin_name","Default"))

@platform_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@platform_bp.route("/admin", methods=["GET","POST"])
def admin():
    authed = session.get("admin_authed")
    if request.method == "POST":
        if request.form.get("action") == "login":
            if request.form.get("password") == ADMIN_PASSWORD:
                session["admin_authed"] = True
                authed = True
            else:
                return Response("Wrong password", 403)
        if request.form.get("action") == "announce" and authed:
            post_announcement(title=request.form.get("title",""), body=request.form.get("body",""), pinned=bool(request.form.get("pinned")))
    t = os.path.join(ROOT, "templates", "admin.html")
    if os.path.exists(t):
        return render_template("admin.html", authed=authed, members=get_all_members() if authed else [], announcements=get_announcements() if authed else [])
    return serve_index()

@platform_bp.route("/health")
def health():
    st = status()
    members = get_all_members() or []
    islands = get_recent_islands(limit=999) or []
    audio = get_audio_tracks() or []
    return jsonify({**st, "service":"triptokforge","version":"4.1","members":len(members),"islands":len(islands),"audio":len(audio)})
''')
print("✓ routes/platform.py")

# ══════════════════════════════════════════════════════════════
# 6. server.py — register forge_bp
# ══════════════════════════════════════════════════════════════
server_path = os.path.join(ROOT, "server.py")
src = open(server_path).read()
if "forge_bp" not in src:
    src = src.replace(
        "from routes.whitepages import whitepages_bp",
        "from routes.whitepages import whitepages_bp\nfrom routes.forge      import forge_bp"
    )
    src = src.replace(
        "app.register_blueprint(whitepages_bp)",
        "app.register_blueprint(whitepages_bp)\napp.register_blueprint(forge_bp)"
    )
    open(server_path, "w").write(src)
    print("✓ server.py — forge_bp registered")
else:
    print("✓ server.py — forge_bp already registered")

# ══════════════════════════════════════════════════════════════
# 7. Restart + verify
# ══════════════════════════════════════════════════════════════
import subprocess, time
print("\n▸ Restarting...")
subprocess.run(["sudo","systemctl","restart","islandforge"], check=True)
time.sleep(5)

for path in ["/", "/home", "/forge", "/dashboard", "/privacy", "/health"]:
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}",f"http://127.0.0.1:5000{path}"], capture_output=True, text=True)
    print(f"  {path:20s} → {r.stdout}")

print("\n✅ Full restore complete!")
print("   / and /home   → landing page with hero + features")
print("   /dashboard    → holographic player card")
print("   /forge        → Island Forge tool")
print("   /privacy      → privacy policy")
print("   /generate     → island generation endpoint")
print("   /upload_audio → audio upload")
print("   /api/stats    → Fortnite stats")
print("   /api/cosmetics → skin selector")
