"""
channels_page.py  —  drop-in HTML string for the /channels route in server.py

Usage inside server.py:
    from channels_page import build_channels_page

    @app.route("/channels")
    def channels():
        rows = get_channels()   # oracle_db function
        return build_channels_page(rows, shell=_shell)
"""

def build_channels_page(channels: list, shell: str = "") -> str:
    """
    channels: list of dicts with keys: id, name, category, embed_url, description
    shell:    the _shell(title, body) HTML wrapper from server.py
    """

    # ── Group by category ──────────────────────────────────────
    from collections import OrderedDict
    groups: dict = OrderedDict()
    for ch in channels:
        cat = ch.get("category", "Uncategorised")
        groups.setdefault(cat, []).append(ch)

    # ── Category icon map ──────────────────────────────────────
    icons = {
        "Fortnite Competitive":         "🎯",
        "Game Developers":              "🛠️",
        "Esports":                      "🏆",
        "Creative / UEFN":              "🗺️",
        "Chill / Music":                "🎵",
        "Gaming News":                  "📰",
        "US News — Rhode Island":       "🗺️",
        "US News — New England":        "🍂",
        "US News — New York":           "🗽",
        "US News — LA & California":    "🌴",
        "World News — Mexico":          "🇲🇽",
        "World News — Slovakia":        "🇸🇰",
        "World News — Ukraine":         "🇺🇦",
        "World News — Japan":           "🇯🇵",
        "World News — India":           "🇮🇳",
        "World News — China":           "🇨🇳",
        "World News — United Nations":  "🌐",
        "World News — International":   "🌍",
    }

    # ── Build channel list HTML ────────────────────────────────
    guide_html = ""
    for cat, items in groups.items():
        icon = icons.get(cat, "📺")
        # category header (click to collapse)
        guide_html += f"""
        <div class="cat-header" onclick="toggleCat(this)">
            <span class="cat-icon">{icon}</span>
            <span class="cat-name">{cat}</span>
            <span class="cat-count">{len(items)}</span>
            <span class="cat-arrow">▾</span>
        </div>
        <div class="cat-body">"""

        for ch in items:
            cid       = ch.get("id", "")
            name      = ch.get("name", "")
            desc      = ch.get("description", "")
            embed_url = ch.get("embed_url", "")
            guide_html += f"""
            <div class="ch-row" onclick="loadChannel('{embed_url}', '{name}')"
                 data-url="{embed_url}" data-name="{name}">
                <span class="ch-dot"></span>
                <div class="ch-info">
                    <span class="ch-name">{name}</span>
                    <span class="ch-desc">{desc}</span>
                </div>
                <span class="ch-play">▶</span>
            </div>"""

        guide_html += "\n        </div>"  # close cat-body

    # ── Suggest form (shown inline at bottom of guide) ─────────
    suggest_html = """
        <div class="suggest-wrap">
            <div class="suggest-toggle" onclick="toggleSuggest()">+ Suggest a Channel</div>
            <div id="suggest-form" style="display:none">
                <input id="sg-name" type="text"   placeholder="Channel name" />
                <input id="sg-cat"  type="text"   placeholder="Category" />
                <input id="sg-url"  type="text"   placeholder="Stream URL (Twitch / YouTube / Kick)" />
                <input id="sg-desc" type="text"   placeholder="Short description" />
                <button onclick="submitSuggest()">Submit</button>
            </div>
        </div>"""

    body = f"""
<style>
/* ── Layout ───────────────────────────────────────────────── */
.ch-shell {{
    display: flex;
    height: calc(100vh - 57px);
    background: var(--bg);
    overflow: hidden;
}}

/* Guide panel */
.ch-guide {{
    width: 320px;
    min-width: 220px;
    max-width: 520px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
    overflow: hidden;
    flex-shrink: 0;
    transition: width 0.2s;
}}
.ch-guide.collapsed {{
    width: 0 !important;
    min-width: 0;
    border: none;
}}

/* Drag handle */
.ch-drag {{
    width: 5px;
    cursor: col-resize;
    background: var(--border);
    flex-shrink: 0;
    transition: background 0.15s;
}}
.ch-drag:hover {{ background: var(--accent); }}

/* Player panel */
.ch-player {{
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
}}

/* Player toolbar */
.ch-toolbar {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}}
.ch-toolbar .ch-title {{
    flex: 1;
    font-size: .85rem;
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.ch-toolbar button {{
    background: var(--border2);
    border: none;
    color: #ccc;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: .75rem;
    transition: background .15s;
}}
.ch-toolbar button:hover {{ background: var(--accent); color: #000; }}

/* Iframe */
#ch-iframe {{
    flex: 1;
    border: none;
    width: 100%;
    height: 100%;
    display: block;
    background: #000;
}}

/* Placeholder */
.ch-placeholder {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #444;
    gap: 12px;
    font-size: .9rem;
}}
.ch-placeholder .ph-icon {{ font-size: 3rem; opacity: .3; }}

/* Guide inner scroll */
.ch-guide-inner {{
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: var(--border2) transparent;
}}

/* Category header */
.cat-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 2;
    transition: background .15s;
}}
.cat-header:hover {{ background: var(--border); }}
.cat-icon  {{ font-size: .9rem; }}
.cat-name  {{ flex: 1; font-size: .78rem; font-weight: 700; color: #bbb;
              text-transform: uppercase; letter-spacing: .06em; }}
.cat-count {{ font-size: .7rem; color: #555; background: var(--border2);
              padding: 1px 6px; border-radius: 10px; }}
.cat-arrow {{ font-size: .7rem; color: #555; transition: transform .2s; }}
.cat-header.closed .cat-arrow {{ transform: rotate(-90deg); }}

/* Category body */
.cat-body {{
    overflow: hidden;
    transition: max-height .25s ease;
    max-height: 9000px;
}}
.cat-body.closed {{ max-height: 0; }}

/* Channel row */
.ch-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    cursor: pointer;
    border-bottom: 1px solid var(--border);
    transition: background .12s;
}}
.ch-row:hover {{ background: var(--border); }}
.ch-row.active {{ background: var(--border2); border-left: 3px solid var(--accent); }}
.ch-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #333;
    flex-shrink: 0;
    transition: background .15s;
}}
.ch-row.active .ch-dot,
.ch-row:hover .ch-dot {{ background: var(--accent); }}
.ch-info {{ flex: 1; min-width: 0; }}
.ch-name {{ display: block; font-size: .82rem; color: #ddd; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ch-desc {{ display: block; font-size: .7rem; color: #555;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ch-play {{ font-size: .7rem; color: #444; flex-shrink: 0; }}
.ch-row:hover .ch-play {{ color: var(--accent); }}

/* Suggest */
.suggest-wrap {{
    padding: 12px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
}}
.suggest-toggle {{
    font-size: .75rem;
    color: var(--accent2);
    cursor: pointer;
    text-align: center;
    padding: 6px;
    border: 1px solid var(--border2);
    border-radius: 4px;
    transition: background .15s;
}}
.suggest-toggle:hover {{ background: var(--border); }}
#suggest-form {{
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
#suggest-form input {{
    background: var(--border);
    border: 1px solid var(--border2);
    color: #ddd;
    padding: 6px 8px;
    border-radius: 4px;
    font-size: .78rem;
}}
#suggest-form button {{
    background: var(--accent2);
    border: none;
    color: #000;
    padding: 7px;
    border-radius: 4px;
    cursor: pointer;
    font-size: .78rem;
    font-weight: 700;
}}
#suggest-form button:hover {{ opacity: .85; }}

/* Guide toggle btn */
.guide-toggle {{
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    background: var(--border2);
    border: 1px solid var(--border);
    color: #bbb;
    border-radius: 0 4px 4px 0;
    padding: 6px 4px;
    cursor: pointer;
    font-size: .65rem;
    z-index: 10;
    writing-mode: vertical-rl;
    display: none;
}}
.guide-toggle:hover {{ background: var(--accent); color: #000; }}
.ch-guide.collapsed ~ .ch-drag ~ .ch-player .guide-toggle {{ display: block; }}

/* Fullscreen */
:fullscreen .ch-shell   {{ height: 100vh; }}
:-webkit-full-screen .ch-shell {{ height: 100vh; }}
</style>

<div class="ch-shell" id="ch-shell">

    <!-- Guide -->
    <div class="ch-guide" id="ch-guide">
        <div class="ch-guide-inner" id="ch-guide-inner">
            {guide_html}
        </div>
        {suggest_html}
    </div>

    <!-- Drag handle -->
    <div class="ch-drag" id="ch-drag"></div>

    <!-- Player -->
    <div class="ch-player" id="ch-player">

        <!-- Hidden guide toggle (shows when guide is collapsed) -->
        <button class="guide-toggle" id="guide-toggle" onclick="expandGuide()" title="Show channel guide">☰ Guide</button>

        <!-- Toolbar -->
        <div class="ch-toolbar">
            <span class="ch-title" id="ch-title">Select a channel from the guide →</span>
            <button onclick="toggleGuide()" title="Hide/show channel guide">⇔ Guide</button>
            <button onclick="toggleFullscreen()" title="Fullscreen">⛶ Full</button>
        </div>

        <!-- Iframe / placeholder -->
        <div id="ch-placeholder" class="ch-placeholder">
            <span class="ph-icon">📺</span>
            <span>Pick a channel from the guide to start watching</span>
        </div>
        <iframe id="ch-iframe" src="" allow="autoplay; fullscreen; picture-in-picture"
                allowfullscreen style="display:none"></iframe>
    </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────
let activeRow = null;
let guideVisible = true;

// ── Load channel ───────────────────────────────────────────
function loadChannel(url, name) {{
    if (!url) return;

    // Stop global music player if running
    stopMusicPlayer();

    // Highlight row
    if (activeRow) activeRow.classList.remove('active');
    activeRow = event.currentTarget || document.querySelector(`[data-url="${{url}}"]`);
    if (activeRow) activeRow.classList.add('active');

    // Update title
    document.getElementById('ch-title').textContent = '📺 ' + name;

    // Show iframe, hide placeholder
    document.getElementById('ch-placeholder').style.display = 'none';
    const iframe = document.getElementById('ch-iframe');
    iframe.style.display = 'block';
    iframe.src = url;
}}

// ── Stop music player ──────────────────────────────────────
function stopMusicPlayer() {{
    // Global audio element (persistent player uses id="global-audio" or window.globalAudio)
    try {{
        const a = window.globalAudio || document.getElementById('global-audio');
        if (a && !a.paused) {{
            a.pause();
            // Update play button icon if present
            const btn = document.getElementById('player-play-btn');
            if (btn) btn.textContent = '▶';
        }}
    }} catch(e) {{}}
    // Also try any playing audio/video elements
    document.querySelectorAll('audio, video').forEach(m => {{
        if (!m.paused) m.pause();
    }});
}}

// ── Toggle guide ───────────────────────────────────────────
function toggleGuide() {{
    const guide = document.getElementById('ch-guide');
    guideVisible = !guideVisible;
    guide.classList.toggle('collapsed', !guideVisible);
}}

function expandGuide() {{
    guideVisible = true;
    document.getElementById('ch-guide').classList.remove('collapsed');
}}

// ── Collapsible categories ─────────────────────────────────
function toggleCat(header) {{
    const body = header.nextElementSibling;
    const open = !body.classList.contains('closed');
    body.classList.toggle('closed', open);
    header.classList.toggle('closed', open);
}}

// ── Fullscreen ─────────────────────────────────────────────
function toggleFullscreen() {{
    const shell = document.getElementById('ch-shell');
    if (!document.fullscreenElement) {{
        shell.requestFullscreen().catch(() => {{
            // fallback: try iframe
            const f = document.getElementById('ch-iframe');
            if (f && f.requestFullscreen) f.requestFullscreen();
        }});
    }} else {{
        document.exitFullscreen();
    }}
}}

// ── Drag to resize guide ───────────────────────────────────
(function() {{
    const drag  = document.getElementById('ch-drag');
    const guide = document.getElementById('ch-guide');
    let dragging = false, startX = 0, startW = 0;

    drag.addEventListener('mousedown', e => {{
        dragging = true;
        startX   = e.clientX;
        startW   = guide.offsetWidth;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }});

    window.addEventListener('mousemove', e => {{
        if (!dragging) return;
        const delta = e.clientX - startX;
        const newW  = Math.max(180, Math.min(600, startW + delta));
        guide.style.width = newW + 'px';
    }});

    window.addEventListener('mouseup', () => {{
        dragging = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }});
}})();

// ── Suggest channel ────────────────────────────────────────
function toggleSuggest() {{
    const f = document.getElementById('suggest-form');
    f.style.display = f.style.display === 'none' ? 'flex' : 'none';
}}

async function submitSuggest() {{
    const name = document.getElementById('sg-name').value.trim();
    const cat  = document.getElementById('sg-cat').value.trim();
    const url  = document.getElementById('sg-url').value.trim();
    const desc = document.getElementById('sg-desc').value.trim();
    if (!name || !url) {{ alert('Name and URL are required.'); return; }}

    const r = await fetch('/api/suggest_channel', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{name, category: cat, embed_url: url, description: desc}})
    }});
    const d = await r.json();
    if (d.ok) {{
        alert('Thanks! Your suggestion has been submitted for review.');
        document.getElementById('sg-name').value = '';
        document.getElementById('sg-url').value  = '';
        document.getElementById('sg-desc').value = '';
        toggleSuggest();
    }} else {{
        alert('Error: ' + (d.error || 'unknown'));
    }}
}}
</script>
"""

    if shell:
        return shell("Channels", body)
    return body
