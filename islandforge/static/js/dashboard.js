let allSkins = [];

function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, function (char) {
        return {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        }[char];
    });
}

function getDisplayName() {
    return document.body.dataset.displayName || "";
}

function normalizePercent(value, maxValue) {
    const numeric = parseFloat(String(value || "0").replace("%", ""));
    if (!Number.isFinite(numeric) || maxValue <= 0) {
        return 0;
    }
    return Math.max(8, Math.min(100, (numeric / maxValue) * 100));
}

function setMeter(id, value, maxValue) {
    const meter = document.getElementById(id);
    if (!meter) return;
    meter.style.width = `${normalizePercent(value, maxValue)}%`;
}

function renderServices(services) {
    const grid = document.getElementById("sourceGrid");
    if (!grid) return;
    if (!services.length) {
        grid.innerHTML = '<div class="source-loading">No source map is available yet.</div>';
        return;
    }

    grid.innerHTML = services.map((service) => {
        const statusClass = String(service.status || "idle").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
        return `<article class="source-card source-card--${statusClass}">
      <div class="source-card__top">
        <span class="source-card__label">${escapeHtml(service.label)}</span>
        <span class="source-card__status">${escapeHtml(service.status)}</span>
      </div>
      <strong class="source-card__value">${escapeHtml(service.value)}</strong>
      <span class="source-card__unit">${escapeHtml(service.unit)}</span>
      <p class="source-card__copy">${escapeHtml(service.detail)}</p>
    </article>`;
    }).join("");
}

async function loadStats() {
    const msg = document.getElementById("statsMsg");
    if (msg) {
        msg.textContent = "Refreshing telemetry rail...";
    }

    try {
        const response = await fetch(`/api/stats?name=${encodeURIComponent(getDisplayName())}`);
        const data = await response.json();
        if (!data.ok) {
            throw new Error("stats unavailable");
        }

        const stats = data.stats || {};
        const statMap = {
            "s-wins": stats.wins || "--",
            "s-kd": stats.kd || "--",
            "s-matches": stats.matches || "--",
            "s-kills": stats.kills || "--",
            "s-winpct": stats.winPct || "--",
            "s-avgelim": stats.avgElim || "--",
        };
        Object.entries(statMap).forEach(([id, value]) => {
            const node = document.getElementById(id);
            if (node) {
                node.textContent = value;
            }
        });

        const octoWins = document.getElementById("octoWins");
        const octoKd = document.getElementById("octoKd");
        if (octoWins) octoWins.textContent = stats.wins || "--";
        if (octoKd) octoKd.textContent = stats.kd || "--";

        setMeter("m-wins", stats.wins, 500);
        setMeter("m-kd", stats.kd, 10);
        setMeter("m-matches", stats.matches, 5000);
        setMeter("m-kills", stats.kills, 10000);
        setMeter("m-winpct", stats.winPct, 100);
        setMeter("m-avgelim", stats.avgElim, 10);

        if (msg) {
            msg.textContent = data.source === "mock"
                ? "Preview stats are active. Add FORTNITE_API_KEY to switch this rail to live player stats."
                : "Live Battle Royale stats synced from fortnite-api.com.";
        }
    } catch (error) {
        if (msg) {
            msg.textContent = "Stats are offline right now. The rest of the member hub is still live.";
        }
    }
}

async function loadEcosystem() {
    const mode = document.getElementById("ecoMode");
    const msg = document.getElementById("ecoMsg");
    if (mode) mode.textContent = "SYNCING";
    if (msg) msg.textContent = "Reading site telemetry and Fortnite surfaces.";

    try {
        const response = await fetch("/api/ecosystem/summary");
        const data = await response.json();
        if (!data.ok) {
            throw new Error("ecosystem unavailable");
        }

        const site = data.site || {};
        const signals = data.signals || {};
        const shop = signals.shop || {};
        const cosmetics = signals.cosmetics || {};
        const services = data.services || [];
        const statsService = services.find((service) => service.id === "fortnite-stats") || {};

        const ecoMembers = document.getElementById("ecoMembers");
        const ecoChannels = document.getElementById("ecoChannels");
        const ecoShop = document.getElementById("ecoShop");
        const ecoOutfits = document.getElementById("ecoOutfits");
        if (ecoMembers) ecoMembers.textContent = site.members != null ? site.members : "--";
        if (ecoChannels) ecoChannels.textContent = site.channels != null ? site.channels : "--";
        if (ecoShop) ecoShop.textContent = shop.entries != null ? shop.entries : "--";
        if (ecoOutfits) ecoOutfits.textContent = cosmetics.outfits != null ? cosmetics.outfits : "--";

        if (mode) {
            mode.textContent = data.identity && data.identity.epic_connected ? "LIVE GRID" : "OPEN GRID";
        }
        if (msg) {
            msg.textContent = statsService.status === "key-needed"
                ? "Public Fortnite feeds are live. Add FORTNITE_API_KEY to unlock player stat lookups."
                : "Public Fortnite feeds and keyed services are online.";
        }

        renderServices(services);
    } catch (error) {
        if (mode) mode.textContent = "DEGRADED";
        if (msg) {
            msg.textContent = "Ecosystem radar is unavailable right now. Core member tools are still live.";
        }
        renderServices([]);
    }
}

async function loadSkins() {
    try {
        const response = await fetch("/api/cosmetics");
        const data = await response.json();
        if (!data.ok || !data.skins || !data.skins.length) {
            throw new Error("no skins");
        }
        allSkins = data.skins;
        renderSkins(allSkins);
    } catch (error) {
        const grid = document.getElementById("skinGrid");
        if (grid) {
            grid.innerHTML = '<div class="skin-loading">Cosmetics could not be loaded.</div>';
        }
    }
}

function renderSkins(skins) {
    const grid = document.getElementById("skinGrid");
    if (!grid) return;
    if (!skins.length) {
        grid.innerHTML = '<div class="skin-loading">No skins found.</div>';
        return;
    }

    grid.innerHTML = skins.slice(0, 150).map((skin) => {
        const safeName = String(skin.name || "").replace(/'/g, "\\'");
        const safeImg = String(skin.img || "").replace(/'/g, "\\'");
        return `<button class="skin-item" type="button" onclick="selectSkin(this, '${skin.id}', '${safeName}', '${safeImg}')">
      <img src="${skin.img}" loading="lazy" alt="${skin.name}"/>
      <span class="skin-name">${skin.name}</span>
    </button>`;
    }).join("");
}

function filterSkins() {
    const search = document.getElementById("skinSearch");
    const query = search ? search.value.trim().toLowerCase() : "";
    renderSkins(query ? allSkins.filter((skin) => skin.name.toLowerCase().includes(query)) : allSkins);
}

async function selectSkin(button, id, name, img) {
    document.querySelectorAll(".skin-item").forEach((node) => node.classList.remove("active"));
    if (button) {
        button.classList.add("active");
    }

    const identitySkin = document.getElementById("identitySkin");
    if (identitySkin) {
        identitySkin.innerHTML = `<img src="${img}" id="skinImg" alt="${name}"/>`;
    }
    const cardSkinName = document.getElementById("cardSkinName");
    if (cardSkinName) {
        cardSkinName.textContent = name;
    }

    try {
        await fetch("/api/set_skin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, name, img }),
        });
    } catch (error) {
        // Visual selection still updates even if persistence fails.
    }
}

window.loadStats = loadStats;
window.loadEcosystem = loadEcosystem;
window.filterSkins = filterSkins;
window.selectSkin = selectSkin;

document.addEventListener("DOMContentLoaded", function () {
    loadStats();
    loadEcosystem();
    loadSkins();
});
