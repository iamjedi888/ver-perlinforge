(function () {
  const trackHints = {
    soundcloud: "Paste a SoundCloud track or playlist URL.",
    youtube: "Paste a YouTube watch or playlist URL.",
    audio: "Paste a direct .mp3 or .ogg URL.",
  };

  const autoTokens = new Set(["", "auto", "auto detect", "auto-detect", "detect", "suggested"]);

  function setTrackHint() {
    const type = document.getElementById("wp-type");
    const hint = document.getElementById("wp-url-hint");
    if (!type || !hint) return;
    hint.textContent = trackHints[type.value] || "Paste a SoundCloud, YouTube, or direct audio URL.";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadTracks() {
    const list = document.getElementById("track-list");
    const count = document.getElementById("track-count");
    if (!list || !count) return;
    const response = await fetch("/api/whitepages/tracks");
    const data = await response.json();
    count.textContent = `${data.length} track${data.length === 1 ? "" : "s"}`;
    if (!data.length) {
      list.innerHTML = '<div class="empty"><div class="copy">No WhitePages tracks yet.</div></div>';
      return;
    }
    list.innerHTML = data.map((track) => `
      <article class="track-card">
        <div>
          <div class="track-title">${escapeHtml(track.title)}</div>
          <div class="mono">${escapeHtml(track.artist || "-")} · ${escapeHtml(track.source_type || "source")}</div>
          <div class="mono" style="margin-top:6px">${escapeHtml(track.embed_url || "")}</div>
        </div>
        <button type="button" class="btn danger" onclick="deleteTrack(${track.id})">Remove</button>
      </article>
    `).join("");
  }

  async function addTrack() {
    const title = document.getElementById("wp-title").value.trim();
    const artist = document.getElementById("wp-artist").value.trim();
    const sourceType = document.getElementById("wp-type").value.trim();
    const embedUrl = document.getElementById("wp-url").value.trim();
    if (!title || !embedUrl) {
      alert("Track title and URL are required.");
      return;
    }
    const response = await fetch("/api/whitepages/tracks", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ title, artist, source_type: sourceType, embed_url: embedUrl }),
    });
    const data = await response.json();
    if (!data.ok) {
      alert(data.error || "Unable to add track.");
      return;
    }
    document.getElementById("wp-title").value = "";
    document.getElementById("wp-artist").value = "";
    document.getElementById("wp-url").value = "";
    await loadTracks();
  }

  async function deleteTrack(trackId) {
    if (!confirm("Remove this WhitePages track?")) return;
    const response = await fetch(`/api/whitepages/tracks/${trackId}`, { method: "DELETE" });
    const data = await response.json();
    if (!data.ok) {
      alert(data.error || "Unable to delete track.");
      return;
    }
    await loadTracks();
  }

  function splitLines(value) {
    return String(value || "")
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function getProviderHint(urls) {
    const providers = new Set();
    urls.forEach((url) => {
      const signal = normalize(url);
      if (signal.includes("youtube.com") || signal.includes("youtu.be")) {
        providers.add("youtube");
      } else if (signal.includes("twitch.tv")) {
        providers.add("twitch");
      } else if (signal.includes("kick.com")) {
        providers.add("kick");
      } else if (signal.includes("streamable.com")) {
        providers.add("streamable");
      }
    });
    if (!providers.size) return "";
    if (providers.size === 1) return Array.from(providers)[0];
    return "mixed";
  }

  function getRotationMode(urls, searchTerms) {
    if (urls.length > 1) return "random_pool";
    if (searchTerms.length) return "queue";
    const joined = urls.join(" ").toLowerCase();
    if (
      joined.includes("/videos") ||
      joined.includes("/streams") ||
      joined.includes("/featured") ||
      joined.includes("youtube.com/@") ||
      joined.includes("youtube.com/channel/")
    ) {
      return "queue";
    }
    return "single";
  }

  function scoreHits(signal, terms) {
    return terms.reduce((score, term) => score + (signal.includes(term) ? 1 : 0), 0);
  }

  function detectCategory({ name, description, urls, searchTerms, providerHint }) {
    const signal = [name, description, providerHint, ...urls, ...searchTerms].join(" ").toLowerCase();
    const scores = {
      "Fortnite Competitive": 0,
      "Game Developers": 0,
      "Esports": 0,
      "Creative / UEFN": 0,
      "Gaming News": 0,
      "Community Picks": 0,
      "Chill / Music": 0,
    };

    const matched = [];
    const rules = [
      ["Fortnite Competitive", ["fortnite", "fncs", "cash cup", "ranked", "battle royale", "world cup", "competitive"], 2],
      ["Creative / UEFN", ["uefn", "verse", "creative 2.0", "fortnite creative", "build your first island", "unreal editor for fortnite"], 2],
      ["Game Developers", ["unreal engine", "unity", "gdc", "game developers conference", "devlog", "postmortem", "developer"], 2],
      ["Esports", ["esports", "valorant", "counter-strike", "cs2", "rocket league", "overwatch league", "tournament", "scrim", "finals"], 2],
      ["Gaming News", ["news", "ign", "gamespot", "kotaku", "digital foundry", "pokemon", "showcase", "state of play", "headline"], 2],
      ["Community Picks", ["creator", "community", "highlights", "clips", "sypherpk", "lachlan", "ali-a", "mythpat", "streamer"], 2],
      ["Chill / Music", ["music", "lofi", "ost", "soundtrack", "square enix", "final fantasy", "nier", "radio", "beats", "chill", "ambient"], 2],
    ];

    rules.forEach(([category, terms, weight]) => {
      const hits = scoreHits(signal, terms);
      if (hits > 0) {
        scores[category] += hits * weight;
        matched.push(...terms.filter((term) => signal.includes(term)).slice(0, 3));
      }
    });

    if (signal.includes("youtube.com/@") || signal.includes("twitch.tv/")) {
      scores["Community Picks"] += 1;
    }

    const best = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
    return {
      category: best && best[1] > 0 ? best[0] : "Community Picks",
      reasons: Array.from(new Set(matched)).slice(0, 6),
    };
  }

  function updateChannelIntel(applySuggested) {
    const nameInput = document.getElementById("channel-name");
    const categoryInput = document.getElementById("channel-category");
    const urlInput = document.getElementById("channel-url");
    const descriptionInput = document.getElementById("channel-description");
    const searchTermsInput = document.getElementById("channel-search-terms");
    const providerInput = document.getElementById("channel-provider");
    const rotationInput = document.getElementById("channel-rotation");
    if (!nameInput || !categoryInput || !urlInput || !descriptionInput || !searchTermsInput || !providerInput || !rotationInput) {
      return;
    }

    const urls = splitLines(urlInput.value);
    const searchTerms = splitLines(searchTermsInput.value);
    const providerSuggestion = getProviderHint(urls);
    const rotationSuggestion = getRotationMode(urls, searchTerms);
    const categorySuggestion = detectCategory({
      name: nameInput.value,
      description: descriptionInput.value,
      urls,
      searchTerms,
      providerHint: providerInput.value,
    });

    const categoryEl = document.getElementById("channel-detect-category");
    const providerEl = document.getElementById("channel-detect-provider");
    const rotationEl = document.getElementById("channel-detect-rotation");
    const reasonEl = document.getElementById("channel-detect-reason");
    const tagsEl = document.getElementById("channel-detect-tags");

    if (categoryEl) categoryEl.textContent = categorySuggestion.category;
    if (providerEl) providerEl.textContent = providerSuggestion || "manual / mixed";
    if (rotationEl) rotationEl.textContent = rotationSuggestion;
    if (reasonEl) {
      reasonEl.textContent = categorySuggestion.reasons.length
        ? `Signals: ${categorySuggestion.reasons.join(", ")}`
        : "Waiting for stronger title, source, or description signals.";
    }
    if (tagsEl) {
      const tags = [];
      if (urls.length) tags.push(`${urls.length} source${urls.length === 1 ? "" : "s"}`);
      if (searchTerms.length) tags.push(`${searchTerms.length} search term${searchTerms.length === 1 ? "" : "s"}`);
      if (providerSuggestion) tags.push(providerSuggestion);
      tags.push(rotationSuggestion);
      tagsEl.innerHTML = tags.map((tag) => `<span class="detector-chip">${escapeHtml(tag)}</span>`).join("");
    }

    if (applySuggested) {
      categoryInput.value = categorySuggestion.category;
      providerInput.value = providerSuggestion || providerInput.value || "auto";
      rotationInput.value = rotationSuggestion;
    }

    return {
      category: categorySuggestion.category,
      provider: providerSuggestion,
      rotation: rotationSuggestion,
    };
  }

  function bootChannelIntel() {
    const editorForm = document.querySelector('#channel-editor form');
    if (!editorForm) return;
    const inputs = [
      "channel-name",
      "channel-category",
      "channel-url",
      "channel-description",
      "channel-search-terms",
      "channel-provider",
      "channel-rotation",
    ]
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    inputs.forEach((input) => {
      input.addEventListener("input", () => updateChannelIntel(false));
      input.addEventListener("change", () => updateChannelIntel(false));
    });

    document.getElementById("channel-detect-btn")?.addEventListener("click", () => updateChannelIntel(false));
    document.getElementById("channel-apply-btn")?.addEventListener("click", () => updateChannelIntel(true));

    editorForm.addEventListener("submit", () => {
      const suggestion = updateChannelIntel(false);
      const categoryInput = document.getElementById("channel-category");
      const providerInput = document.getElementById("channel-provider");
      const rotationInput = document.getElementById("channel-rotation");
      if (categoryInput && autoTokens.has(normalize(categoryInput.value))) {
        categoryInput.value = suggestion.category;
      }
      if (providerInput && autoTokens.has(normalize(providerInput.value))) {
        providerInput.value = suggestion.provider || "";
      }
      if (rotationInput && autoTokens.has(normalize(rotationInput.value))) {
        rotationInput.value = suggestion.rotation;
      }
    });

    updateChannelIntel(false);
  }

  window.addTrack = addTrack;
  window.deleteTrack = deleteTrack;

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("wp-type")?.addEventListener("input", setTrackHint);
    setTrackHint();
    loadTracks().catch(() => {});
    bootChannelIntel();
  });
})();
