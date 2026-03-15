(function () {
  const payloadNode = document.getElementById("arena-data");
  const payload = payloadNode ? JSON.parse(payloadNode.textContent || "{}") : {};
  const viewport = document.getElementById("arenaViewport");
  const cameraRig = document.getElementById("cameraRig");
  const statusText = document.getElementById("arenaStatusText");
  const clockNode = document.getElementById("arenaClock");
  const hoverCapable = window.matchMedia("(hover: hover)").matches;

  const presets = {
    entry: { label: "Entry", position: "0 1.65 8.4", rotation: "0 0 0" },
    leaderboard: { label: "Leaderboard", position: "-4.8 1.65 -5.6", rotation: "0 52 0" },
    screen: { label: "Screen", position: "0 1.65 -1.6", rotation: "0 0 0" },
    counter: { label: "Counter", position: "0 1.65 2.8", rotation: "0 180 0" },
  };

  function setTextValue(id, value) {
    const node = document.getElementById(id);
    if (!node) {
      return;
    }
    const current = node.getAttribute("text") || {};
    node.setAttribute("text", { ...current, value });
  }

  function buildLeaderboardText(rows) {
    if (!rows || !rows.length) {
      return "NO LIVE ENTRIES\nSYNC PENDING";
    }
    return rows
      .map((row) => `#${row.rank} ${row.display_name}  ${row.wins}W / ${Number(row.kd).toFixed(2)} KD`)
      .join("\n");
  }

  function buildSignalText(lines) {
    const stack = (lines || []).filter(Boolean);
    if (!stack.length) {
      return "OPS SIGNAL\nQUEUE READY";
    }
    return stack.slice(0, 3).join("\n");
  }

  function buildTickerText(lines) {
    const stack = (lines || []).filter(Boolean);
    if (!stack.length) {
      return "ARENA DECK ONLINE";
    }
    return stack.join(" / ").toUpperCase();
  }

  function updateClock() {
    if (!clockNode) {
      return;
    }
    const formatter = new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "America/New_York",
    });
    clockNode.textContent = `${formatter.format(new Date())} ET`;
  }

  function highlightFocusables(target) {
    document.querySelectorAll(".arena-focusable").forEach((node) => {
      node.classList.toggle("is-targeted", node.dataset.focusTarget === target);
    });
  }

  function setActiveButtons(target) {
    document.querySelectorAll("[data-focus-target]").forEach((node) => {
      if (!node.classList.contains("arena-focus-btn")) {
        return;
      }
      node.classList.toggle("is-active", node.dataset.focusTarget === target);
    });
  }

  function focusTarget(target) {
    const preset = presets[target] || presets.entry;
    if (cameraRig) {
      cameraRig.setAttribute(
        "animation__move",
        `property: position; to: ${preset.position}; dur: 760; easing: easeInOutCubic`
      );
      cameraRig.setAttribute(
        "animation__turn",
        `property: rotation; to: ${preset.rotation}; dur: 760; easing: easeInOutCubic`
      );
    }
    if (statusText) {
      statusText.textContent = preset.label;
    }
    setActiveButtons(target);
    highlightFocusables(target);
  }

  function bindFocusTargets() {
    let hoverTimer = null;
    document.querySelectorAll("[data-focus-target]").forEach((node) => {
      const target = node.dataset.focusTarget;
      node.addEventListener("click", () => focusTarget(target));
      if (!hoverCapable) {
        return;
      }
      node.addEventListener("mouseenter", () => {
        hoverTimer = window.setTimeout(() => focusTarget(target), 110);
      });
      node.addEventListener("mouseleave", () => {
        if (hoverTimer) {
          window.clearTimeout(hoverTimer);
          hoverTimer = null;
        }
      });
    });
  }

  function bindSceneActions() {
    document.querySelectorAll("[data-scene-action='fullscreen']").forEach((node) => {
      node.addEventListener("click", async () => {
        if (!viewport || !viewport.requestFullscreen) {
          return;
        }
        try {
          await viewport.requestFullscreen();
        } catch (error) {
          console.warn("Fullscreen request failed", error);
        }
      });
    });
  }

  function createBox(attributes) {
    const node = document.createElement("a-box");
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function buildSeats() {
    const seatField = document.getElementById("seatField");
    if (!seatField || seatField.childNodes.length) {
      return;
    }

    const rowZ = [2.8, 1.15, -0.5, -2.15, -3.8];
    const seatX = [-4.4, -3.35, -2.3, -1.25, 1.25, 2.3, 3.35, 4.4];

    rowZ.forEach((z, rowIndex) => {
      const riser = createBox({
        position: `0 ${0.18 + rowIndex * 0.1} ${z}`,
        width: "10.8",
        height: "0.22",
        depth: "1.05",
        color: rowIndex % 2 === 0 ? "#111824" : "#0d141f",
        material: "metalness: 0.35; roughness: 0.65",
      });
      seatField.appendChild(riser);

      seatX.forEach((x) => {
        const seatBase = createBox({
          position: `${x} ${0.58 + rowIndex * 0.1} ${z}`,
          width: "0.78",
          height: "0.22",
          depth: "0.74",
          color: "#242d38",
          material: "metalness: 0.28; roughness: 0.44",
        });
        const seatBack = createBox({
          position: `${x} ${0.97 + rowIndex * 0.1} ${z + 0.2}`,
          width: "0.78",
          height: "0.66",
          depth: "0.18",
          color: "#202833",
          material: "metalness: 0.22; roughness: 0.38",
        });
        const seatGlow = createBox({
          position: `${x} ${0.42 + rowIndex * 0.1} ${z - 0.28}`,
          width: "0.62",
          height: "0.05",
          depth: "0.08",
          color: rowIndex % 2 === 0 ? "#14c8ff" : "#ff9a2e",
          material: `emissive: ${rowIndex % 2 === 0 ? "#14c8ff" : "#ff9a2e"}; emissiveIntensity: 0.8`,
        });
        seatField.appendChild(seatBase);
        seatField.appendChild(seatBack);
        seatField.appendChild(seatGlow);
      });
    });
  }

  function populateScene() {
    setTextValue("arenaScreenTitle", payload.feature_title || "Forge Finals Theater");
    setTextValue(
      "arenaScreenCopy",
      payload.feature_copy ||
        "Live match review, watch-party routing, and event night replays sit on the main screen."
    );
    setTextValue("arenaTickerText", buildTickerText(payload.ticker));
    setTextValue("arenaLeaderboardText", buildLeaderboardText(payload.leaderboard));
    setTextValue("arenaSignalText", buildSignalText(payload.announcement_lines));
  }

  populateScene();
  buildSeats();
  bindFocusTargets();
  bindSceneActions();
  updateClock();
  window.setInterval(updateClock, 30000);
  focusTarget("entry");
})();
