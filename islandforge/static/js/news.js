let prefs = { interests: [], filter_negative: true, default_interests: [] };
let currentCategory = "all";
let newsCache = [];
let categoryMeta = {};
let interestsMeta = {};

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatRelativeTime(isoString) {
    if (!isoString) return "Recently";
    const published = new Date(isoString);
    const deltaMinutes = Math.max(1, Math.round((Date.now() - published.getTime()) / 60000));

    if (deltaMinutes < 60) return `${deltaMinutes}m ago`;
    if (deltaMinutes < 1440) return `${Math.round(deltaMinutes / 60)}h ago`;
    return `${Math.round(deltaMinutes / 1440)}d ago`;
}

function setStatus(text, tone = "default") {
    const status = document.getElementById("newsStatus");
    const toneClass = tone === "warning" ? " status-pill--warning" : "";
    status.innerHTML = `<span class="status-pill${toneClass}">${escapeHtml(text)}</span>`;
}

async function loadPrefs() {
    const response = await fetch("/api/news/preferences");
    prefs = await response.json();
    document.getElementById("filterNegative").checked = prefs.filter_negative;
}

async function loadInterests() {
    const response = await fetch("/api/news/interests");
    interestsMeta = await response.json();

    const grid = document.getElementById("interestsGrid");
    grid.innerHTML = Object.entries(interestsMeta).map(([id, meta]) => `
        <div class="interest-item">
            <input
                type="checkbox"
                class="interest-checkbox"
                value="${escapeHtml(id)}"
                id="int_${escapeHtml(id)}"
                ${prefs.interests.includes(id) ? "checked" : ""}
                onchange="savePrefs()"
            >
            <label for="int_${escapeHtml(id)}">${escapeHtml(meta.name)}</label>
            <span class="interest-meta">${escapeHtml(meta.category_label)}</span>
        </div>
    `).join("");
}

async function loadCategories() {
    const response = await fetch("/api/news/categories");
    categoryMeta = await response.json();
}

async function savePrefs() {
    const selected = Array.from(document.querySelectorAll(".interest-checkbox:checked"))
        .map((checkbox) => checkbox.value);

    prefs.interests = selected.length ? selected : (prefs.default_interests || []);
    prefs.filter_negative = document.getElementById("filterNegative").checked;

    await fetch("/api/news/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            interests: prefs.interests,
            filter_negative: prefs.filter_negative,
        }),
    });

    await loadNews(currentCategory);
}

function updateTicker(news) {
    const ticker = document.getElementById("tickerContent");

    if (!news.length) {
        ticker.innerHTML = "No curated headlines available right now.";
        return;
    }

    const text = news
        .slice(0, 10)
        .map((item) => `${item.source} / ${item.title}`)
        .join("  |  ");

    ticker.innerHTML = `<span>${escapeHtml(text)}</span>`;
}

function renderNews(news) {
    const grid = document.getElementById("newsGrid");

    if (!news.length) {
        grid.innerHTML = `
            <div class="empty-state">
                No stories matched this category and preference mix.
                Try enabling more interests or switching back to All Signal.
            </div>
        `;
        return;
    }

    grid.innerHTML = news.map((item) => `
        <a class="news-card" href="${escapeHtml(item.link)}" target="_blank" rel="noopener">
            <div class="news-meta">
                <span class="news-source">${escapeHtml(item.source)}</span>
                <span class="news-category">${escapeHtml((categoryMeta[item.category] || {}).label || item.category)}</span>
                <span class="news-time">${escapeHtml(formatRelativeTime(item.published))}</span>
            </div>
            <h3 class="news-title">${escapeHtml(item.title)}</h3>
            <p class="news-summary">${escapeHtml(item.summary || "")}</p>
        </a>
    `).join("");
}

async function loadNews(category = "all") {
    currentCategory = category;
    setStatus(`Refreshing ${category === "all" ? "all signal" : ((categoryMeta[category] || {}).label || category)}...`);

    const endpoint = category === "all"
        ? "/api/news/latest"
        : `/api/news/category/${encodeURIComponent(category)}`;

    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        newsCache = data.news || [];
        renderNews(newsCache);
        updateTicker(newsCache);
        setStatus(`${newsCache.length} curated stories loaded`);
    } catch (error) {
        console.error("Error loading news:", error);
        setStatus("News feed offline", "warning");
        document.getElementById("newsGrid").innerHTML = `
            <div class="empty-state">
                The curated feed is temporarily unavailable.
                Try again in a minute.
            </div>
        `;
    }
}

function togglePrefs() {
    const panel = document.getElementById("prefsPanel");
    panel.classList.toggle("open");
    panel.setAttribute("aria-hidden", panel.classList.contains("open") ? "false" : "true");
}

document.addEventListener("DOMContentLoaded", async () => {
    await Promise.all([loadPrefs(), loadCategories()]);
    await loadInterests();
    await loadNews("all");

    document.querySelectorAll(".tab-btn").forEach((tab) => {
        tab.addEventListener("click", async () => {
            document.querySelectorAll(".tab-btn").forEach((button) => button.classList.remove("active"));
            tab.classList.add("active");
            await loadNews(tab.dataset.cat);
        });
    });

    setInterval(() => loadNews(currentCategory), 300000);
});
