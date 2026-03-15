let allSkins = [];
const ROOM_THEME_STORAGE_KEY = "triptokforge.room.theme.v1";
const FORGE_RUN_STORAGE_KEY = "triptokforge.forge.latestRun.v1";
const ROOM_THEME_DETAILS = {
    coastal: {
        label: "Coastal Command",
        copy: "Sea-cliff atmosphere with bright horizon spill and open-floor telemetry.",
    },
    canopy: {
        label: "Canopy Garage",
        copy: "Dense green cover, mossy floor language, and softer forge lounge lighting.",
    },
    desert: {
        label: "Desert Relay",
        copy: "Sandstone routing, high-heat reflections, and wide-open sight lines.",
    },
    alpine: {
        label: "Alpine Deck",
        copy: "Cold-air contrast, glacier glow, and clean signal visibility.",
    },
    volcanic: {
        label: "Volcanic Core",
        copy: "High-energy magma ambience and aggressive forge-reactor mood.",
    },
    wetlands: {
        label: "Wetlands Lab",
        copy: "Humid bioluminescent relay space with softer edges and ambient fog.",
    },
};

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

function toNumber(value) {
    const numeric = parseFloat(String(value || "0").replace(/[%,$]/g, "").replace(/,/g, ""));
    return Number.isFinite(numeric) ? numeric : 0;
}

function readStoredJson(key) {
    try {
        const raw = window.localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch (_error) {
        return null;
    }
}

function titleCaseSlug(value) {
    return String(value || "")
        .split(/[-_\s]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function describeWorldSize(cm) {
    const numeric = Number(cm || 0);
    if (!numeric) return "custom scale";
    const km = numeric / 100000;
    return `${km.toFixed(km >= 10 ? 0 : 1)}km world`;
}

function relativeAge(isoString) {
    if (!isoString) return "just now";
    const delta = Math.max(0, Date.now() - Date.parse(isoString));
    const minutes = Math.round(delta / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 48) return `${hours}h ago`;
    return `${Math.round(hours / 24)}d ago`;
}

function syncMemberSpace() {
    const storedTheme = readStoredJson(ROOM_THEME_STORAGE_KEY);
    const themeValue = document.getElementById("roomThemeValue");
    const themeCopy = document.getElementById("roomThemeCopy");
    if (themeValue && themeCopy) {
        const slug = storedTheme && storedTheme.slug ? storedTheme.slug : themeValue.textContent.trim().toLowerCase();
        const details = ROOM_THEME_DETAILS[slug] || {};
        themeValue.textContent = ((storedTheme && storedTheme.label) || details.label || titleCaseSlug(slug)).toUpperCase();
        themeCopy.textContent = (storedTheme && storedTheme.summary)
            || details.copy
            || "Room climate is synced from the active member suite selection.";
    }

    const latestRun = readStoredJson(FORGE_RUN_STORAGE_KEY);
    const runValue = document.getElementById("roomForgeValue");
    const runCopy = document.getElementById("roomForgeCopy");
    if (!runValue || !runCopy) return;

    if (!latestRun) {
        runValue.textContent = "Awaiting run";
        runCopy.textContent = "Generate and save a run in Forge to mirror its locker state back into the member hub.";
        return;
    }

    runValue.textContent = latestRun.output_folder_name || latestRun.island_name || "Latest run";
    runCopy.textContent = `${latestRun.plots_found || 0} plots from ${latestRun.source_audio || "active audio"} on a ${describeWorldSize(latestRun.world_size_cm)} build, ${relativeAge(latestRun.generated_at)}${latestRun.world_partition_warning ? ". World Partition required." : "."}`;
}

function normalizePercent(value, maxValue) {
    const numeric = toNumber(value);
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

function polygonPoint(cx, cy, radius, index, total, factor) {
    const angle = (-Math.PI / 2) + ((Math.PI * 2) / total) * index;
    return [
        cx + Math.cos(angle) * radius * factor,
        cy + Math.sin(angle) * radius * factor,
    ];
}

function updateNexusRadar(stats) {
    const plot = document.getElementById("nexusRadarPlot");
    if (!plot) return;
    const values = [
        Math.min(toNumber(stats.wins) / 500, 1),
        Math.min(toNumber(stats.kd) / 10, 1),
        Math.min(toNumber(stats.matches) / 5000, 1),
        Math.min(toNumber(stats.kills) / 10000, 1),
        Math.min(toNumber(stats.winPct) / 100, 1),
        Math.min(toNumber(stats.avgElim) / 10, 1),
    ];
    const points = values.map((value, index) => polygonPoint(120, 120, 92, index, values.length, Math.max(0.18, value)));
    plot.setAttribute("points", points.map((point) => `${point[0].toFixed(2)},${point[1].toFixed(2)}`).join(" "));
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

function buildLinePath(points) {
    if (!points.length) return "";
    return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point[0]} ${point[1]}`).join(" ");
}

function renderTimelineChart(timeline) {
    const svg = document.getElementById("activityChart");
    const legend = document.getElementById("activityLegend");
    const meta = document.getElementById("activityMeta");
    if (!svg || !legend || !timeline) return;

    const labels = timeline.labels || [];
    const series = timeline.series || [];
    const width = 720;
    const height = 240;
    const padding = { top: 18, right: 18, bottom: 34, left: 26 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const maxValue = Math.max(1, ...series.flatMap((item) => item.values || []));
    const stepX = labels.length > 1 ? plotWidth / (labels.length - 1) : plotWidth;

    const parts = [];
    for (let index = 0; index <= 4; index += 1) {
        const y = padding.top + (plotHeight / 4) * index;
        parts.push(`<line class="timeline-grid-line" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line>`);
    }
    parts.push(`<line class="timeline-baseline" x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"></line>`);

    labels.forEach((label, index) => {
        const x = padding.left + stepX * index;
        parts.push(`<text class="timeline-label" x="${x}" y="${height - 10}" text-anchor="middle">${escapeHtml(label)}</text>`);
    });

    series.forEach((item) => {
        const points = (item.values || []).map((value, index) => {
            const x = padding.left + stepX * index;
            const y = padding.top + plotHeight - ((value / maxValue) * plotHeight);
            return [x.toFixed(2), y.toFixed(2), value];
        });
        parts.push(`<path class="timeline-line" stroke="${item.color || "#31d0ff"}" d="${buildLinePath(points)}"></path>`);
        points.forEach((point) => {
            parts.push(`<circle class="timeline-point" cx="${point[0]}" cy="${point[1]}" r="4" fill="${item.color || "#31d0ff"}"></circle>`);
        });
    });

    svg.innerHTML = parts.join("");
    meta.textContent = `Last ${labels.length || 0} days`;
    legend.innerHTML = series.map((item) => {
        const values = item.values || [];
        const latest = values.length ? values[values.length - 1] : 0;
        return `<div class="timeline-legend__item">
      <span class="timeline-legend__swatch" style="background:${escapeHtml(item.color || "#31d0ff")}"></span>
      <span class="timeline-legend__label">${escapeHtml(item.label)}</span>
      <strong class="timeline-legend__value">${latest}</strong>
    </div>`;
    }).join("");
}

function renderMixList(containerId, items, metaBuilder) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = '<div class="chart-loading">No mix data is available yet.</div>';
        return;
    }
    const maxValue = Math.max(1, ...items.map((item) => Number(item.value || 0)));
    container.innerHTML = items.map((item) => {
        const width = Math.max(10, Math.min(100, (Number(item.value || 0) / maxValue) * 100));
        return `<div class="mix-row">
      <div class="mix-row__top">
        <div>
          <span class="mix-row__label">${escapeHtml(item.label)}</span>
        </div>
        <strong class="mix-row__value">${Number(item.value || 0)}</strong>
      </div>
      <span class="mix-row__meter"><span class="mix-row__fill" style="width:${width}%"></span></span>
      <span class="mix-row__meta">${escapeHtml(metaBuilder ? metaBuilder(item) : "")}</span>
    </div>`;
    }).join("");
}

function renderSpectrum(metrics, scope, sampleSize) {
    const container = document.getElementById("forgeSpectrum");
    const scopeNode = document.getElementById("forgeSpectrumScope");
    if (!container || !scopeNode) return;

    if (!metrics || !metrics.length) {
        container.innerHTML = '<div class="chart-loading">No forge spectrum is available yet.</div>';
        scopeNode.textContent = "No spectrum";
        return;
    }

    scopeNode.textContent = `${scope === "member" ? "Member weighted" : "Site weighted"} | ${sampleSize} sample${sampleSize === 1 ? "" : "s"}`;
    container.innerHTML = metrics.map((metric) => `
      <div class="spectrum-row">
        <div class="spectrum-row__top">
          <span class="spectrum-row__label">${escapeHtml(metric.label)}</span>
          <strong class="spectrum-row__value">${Number(metric.value || 0)}%</strong>
        </div>
        <span class="spectrum-row__meter"><span class="spectrum-row__fill" style="width:${Math.max(8, metric.value || 0)}%"></span></span>
      </div>
    `).join("");
}

function renderSystemMatrix(items) {
    const container = document.getElementById("systemMatrix");
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = '<div class="chart-loading">No system matrix is available yet.</div>';
        return;
    }
    container.innerHTML = items.map((item) => {
        const statusClass = String(item.status || "pending").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
        return `<article class="system-tile system-tile--${statusClass}">
      <div class="system-tile__top">
        <span class="system-tile__label">${escapeHtml(item.label)}</span>
        <span class="system-tile__badge">${escapeHtml(item.status)}</span>
      </div>
      <strong class="system-tile__value">${escapeHtml(item.value)}</strong>
      <p class="system-tile__detail">${escapeHtml(item.detail)}</p>
    </article>`;
    }).join("");
}

function renderTelemetryNotes(notes) {
    const container = document.getElementById("telemetryNotes");
    if (!container) return;
    if (!notes || !notes.length) {
        container.innerHTML = "";
        return;
    }
    container.innerHTML = notes.map((note) => `<div class="telemetry-note">${escapeHtml(note)}</div>`).join("");
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
            "s-score": stats.score || "--",
            "s-top5": stats.top5 || "--",
            "s-top10": stats.top10 || "--",
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
        setMeter("m-score", stats.score, 1000000);
        setMeter("m-top5", stats.top5, 2000);
        setMeter("m-top10", stats.top10, 4000);
        updateNexusRadar(stats);

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

async function loadTelemetry() {
    try {
        const response = await fetch("/api/dashboard/telemetry");
        const data = await response.json();
        if (!data.ok) {
            throw new Error("telemetry unavailable");
        }

        renderTimelineChart(data.timeline || {});
        renderMixList("volumeBoard", data.volume_mix || [], (item) => `${item.label} routed through the current site stack.`);
        renderMixList("channelMix", data.channel_mix || [], (item) => `${item.share || 0}% of the visible live guide mix.`);

        const forge = data.forge_spectrum || {};
        renderSpectrum(forge.metrics || [], forge.scope || "site", forge.sample_size || 0);
        renderSystemMatrix(data.system_matrix || []);
        renderTelemetryNotes(data.notes || []);
    } catch (error) {
        const fallback = '<div class="chart-loading">Telemetry deck is unavailable right now.</div>';
        ["volumeBoard", "channelMix", "forgeSpectrum", "systemMatrix", "telemetryNotes"].forEach((id) => {
            const node = document.getElementById(id);
            if (node) {
                node.innerHTML = fallback;
            }
        });
        const activityLegend = document.getElementById("activityLegend");
        const activityChart = document.getElementById("activityChart");
        if (activityLegend) activityLegend.innerHTML = fallback;
        if (activityChart) activityChart.innerHTML = "";
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
window.loadTelemetry = loadTelemetry;
window.filterSkins = filterSkins;
window.selectSkin = selectSkin;

document.addEventListener("DOMContentLoaded", function () {
    syncMemberSpace();
    loadStats();
    loadEcosystem();
    loadTelemetry();
    loadSkins();
});

window.addEventListener("storage", function (event) {
    if (event.key === ROOM_THEME_STORAGE_KEY || event.key === FORGE_RUN_STORAGE_KEY) {
        syncMemberSpace();
    }
});
