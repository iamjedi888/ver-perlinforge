(function () {
    const bootstrap = window.ROOM_BOOTSTRAP || {};
    const themeMap = new Map((bootstrap.themes || []).map((theme) => [theme.slug, theme]));
    let currentTheme = bootstrap.theme || "coastal";

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

    function toMetricPairs(stats) {
        return [
            { label: "Wins", value: Number(stats.wins || 0), scale: 100 },
            { label: "K/D", value: Number(stats.kd || 0), scale: 10 },
            { label: "Tickets", value: Number(stats.tickets || 0), scale: 100 },
            { label: "Islands", value: Number(stats.islands || 0), scale: 20 },
            { label: "Uploads", value: Number(stats.uploads || 0), scale: 20 },
        ];
    }

    function pathFromPoints(points) {
        return points.map(function (point, index) {
            return (index === 0 ? "M" : "L") + " " + point[0].toFixed(1) + " " + point[1].toFixed(1);
        }).join(" ");
    }

    function renderTelemetryChart(stats) {
        const svg = document.getElementById("roomTelemetryChart");
        if (!svg) return;

        const width = 720;
        const height = 260;
        const padding = { top: 26, right: 20, bottom: 42, left: 28 };
        const usableWidth = width - padding.left - padding.right;
        const usableHeight = height - padding.top - padding.bottom;
        const items = toMetricPairs(stats);
        const stepX = usableWidth / Math.max(1, items.length - 1);

        const lines = [];
        for (let index = 0; index < 5; index += 1) {
            const y = padding.top + (usableHeight / 4) * index;
            lines.push('<line class="chart-grid" x1="' + padding.left + '" y1="' + y + '" x2="' + (width - padding.right) + '" y2="' + y + '"></line>');
        }
        lines.push('<line class="chart-axis" x1="' + padding.left + '" y1="' + (height - padding.bottom) + '" x2="' + (width - padding.right) + '" y2="' + (height - padding.bottom) + '"></line>');

        const points = items.map(function (item, index) {
            const x = padding.left + stepX * index;
            const normalized = Math.max(0.12, Math.min(1, (item.value || 0) / Math.max(1, item.scale)));
            const y = padding.top + usableHeight - usableHeight * normalized;
            return [x, y];
        });

        const areaPoints = [[padding.left, height - padding.bottom]].concat(points).concat([[width - padding.right, height - padding.bottom]]);
        const areaPath = pathFromPoints(areaPoints) + " Z";
        const linePath = pathFromPoints(points);

        const labels = items.map(function (item, index) {
            const x = padding.left + stepX * index;
            return '<text class="chart-label" x="' + x + '" y="' + (height - 12) + '" text-anchor="middle">' + escapeHtml(item.label) + '</text>';
        }).join("");

        const dots = points.map(function (point, index) {
            return '<circle class="chart-point" cx="' + point[0] + '" cy="' + point[1] + '" r="7"></circle>' +
                '<circle class="chart-cap" cx="' + point[0] + '" cy="' + point[1] + '" r="2.5"></circle>' +
                '<text class="chart-label" x="' + point[0] + '" y="' + (point[1] - 12) + '" text-anchor="middle">' + escapeHtml(items[index].value.toFixed(items[index].label === "K/D" ? 2 : 0)) + '</text>';
        }).join("");

        svg.innerHTML = lines.join("") +
            '<path class="chart-area" d="' + areaPath + '"></path>' +
            '<path class="chart-line" d="' + linePath + '"></path>' +
            dots +
            labels;
    }

    function renderAssetLocker(theme) {
        const locker = document.getElementById("assetLocker");
        if (!locker || !theme) return;
        locker.innerHTML = (theme.assets || []).map(function (asset) {
            return '<a class="asset-card" href="' + escapeHtml(asset.url) + '" target="_blank" rel="noreferrer">' +
                '<span class="asset-card__kind">' + escapeHtml(asset.kind) + '</span>' +
                '<strong>' + escapeHtml(asset.title) + '</strong>' +
                '<span class="asset-card__cta">Open Fab listing</span>' +
                '</a>';
        }).join("");
    }

    function renderThemeSummary(theme) {
        const titleNode = document.getElementById("themeSummaryTitle");
        const copyNode = document.getElementById("themeSummaryCopy");
        const dockTitle = document.getElementById("themeDockTitle");
        const dockCopy = document.getElementById("themeDockCopy");
        const screenTitle = document.getElementById("screenTitle");
        const screenAmbient = document.getElementById("screenAmbient");
        const setupList = document.getElementById("themeSetupList");
        if (!theme) return;

        if (titleNode) titleNode.textContent = theme.label || "";
        if (copyNode) copyNode.textContent = theme.summary || "";
        if (dockTitle) dockTitle.textContent = theme.label || "";
        if (dockCopy) dockCopy.textContent = theme.summary || "";
        if (screenTitle) screenTitle.textContent = theme.label || "";
        if (screenAmbient) screenAmbient.textContent = theme.ambient || "";
        if (setupList) {
            setupList.innerHTML = (theme.setup || []).map(function (item) {
                return "<li>" + escapeHtml(item) + "</li>";
            }).join("");
        }
    }

    function applyTheme(slug, persist) {
        const theme = themeMap.get(slug);
        if (!theme) return;

        currentTheme = slug;
        document.body.className = document.body.className
            .split(/\s+/)
            .filter(function (item) { return item && !item.startsWith("room-theme-"); })
            .concat(["room-theme-" + slug])
            .join(" ");

        document.querySelectorAll(".theme-chip").forEach(function (button) {
            button.classList.toggle("is-active", button.dataset.theme === slug);
        });

        renderThemeSummary(theme);
        renderAssetLocker(theme);
        renderTelemetryChart(bootstrap.stats || {});

        if (persist !== false) {
            fetch("/api/set_room_theme", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ theme: slug }),
            }).catch(function () {});
        }
    }

    async function loadLiveTelemetry() {
        try {
            const response = await fetch("/api/dashboard/telemetry");
            const payload = await response.json();
            if (!payload || !payload.ok) return;

            const forgeSpectrum = payload.forge_spectrum || {};
            const nextStats = {
                wins: Number(bootstrap.stats.wins || 0),
                kd: Number(bootstrap.stats.kd || 0),
                tickets: Number(bootstrap.stats.tickets || 0),
                islands: Number(bootstrap.stats.islands || 0),
                uploads: Number(forgeSpectrum.sample_size || bootstrap.stats.uploads || 0),
            };
            bootstrap.stats = nextStats;
            renderTelemetryChart(nextStats);
        } catch (error) {
            renderTelemetryChart(bootstrap.stats || {});
        }
    }

    document.querySelectorAll(".theme-chip").forEach(function (button) {
        button.addEventListener("click", function () {
            applyTheme(button.dataset.theme, true);
        });
    });

    applyTheme(currentTheme, false);
    loadLiveTelemetry();
})();
