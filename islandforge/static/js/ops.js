(function () {
  const catalogNode = document.getElementById("llm-provider-catalog");
  const defaultsNode = document.getElementById("role-default-permissions");
  if (!catalogNode) return;

  let catalog = [];
  let roleDefaults = {};
  try {
    catalog = JSON.parse(catalogNode.textContent || "[]");
  } catch (_error) {
    catalog = [];
  }
  try {
    roleDefaults = JSON.parse((defaultsNode && defaultsNode.textContent) || "{}");
  } catch (_error) {
    roleDefaults = {};
  }

  function renderProviderMeta(container, provider) {
    if (!container) return;
    if (!provider) {
      container.innerHTML = "Select a provider to load model options, family defaults, and the reference source used in WhitePages.";
      return;
    }
    const models = Array.isArray(provider.models) ? provider.models : [];
    const modelList = models.length ? models.join(" | ") : "No models listed";
    container.innerHTML =
      "<strong>" +
      provider.provider +
      "</strong><br>" +
      provider.notes +
      "<br><span>Family: " +
      provider.family +
      "</span><br><span>Models: " +
      modelList +
      '</span><br><a href="' +
      provider.source +
      '" target="_blank" rel="noreferrer">Open reference</a>';
  }

  function syncProviderForm(form) {
    const providerSelect = form.querySelector("[data-provider-select]");
    const modelSelect = form.querySelector("[data-model-select]");
    const familyInput = form.querySelector("[data-family-input]");
    const meta = form.querySelector("[data-provider-meta]");
    if (!providerSelect || !modelSelect || !familyInput) return;

    const currentModel = modelSelect.dataset.currentModel || "";
    const provider = catalog.find((item) => item.provider === providerSelect.value);
    const models = provider && Array.isArray(provider.models) ? provider.models : [];

    modelSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = models.length ? "Select model" : "No models loaded";
    modelSelect.appendChild(placeholder);

    models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      if (model === currentModel) option.selected = true;
      modelSelect.appendChild(option);
    });

    if (currentModel && !models.includes(currentModel)) {
      const option = document.createElement("option");
      option.value = currentModel;
      option.textContent = currentModel;
      option.selected = true;
      modelSelect.appendChild(option);
    }

    if (provider && !familyInput.value.trim()) {
      familyInput.value = provider.family || "";
    }

    renderProviderMeta(meta, provider);
  }

  document.querySelectorAll("[data-provider-form]").forEach((form) => {
    const providerSelect = form.querySelector("[data-provider-select]");
    if (!providerSelect) return;
    providerSelect.addEventListener("change", function () {
      const modelSelect = form.querySelector("[data-model-select]");
      if (modelSelect) modelSelect.dataset.currentModel = "";
      const familyInput = form.querySelector("[data-family-input]");
      if (familyInput) familyInput.value = "";
      syncProviderForm(form);
    });
    syncProviderForm(form);
  });

  const kindSelect = document.querySelector("[data-profile-kind-select]");
  if (kindSelect) {
    const kindCopy = document.querySelector("[data-profile-kind-copy]");
    const humanPanel = document.querySelector('[data-profile-kind-panel="human"]');
    const botPanel = document.querySelector('[data-profile-kind-panel="bot"]');
    const roleInput = document.querySelector("[data-profile-role-input]");
    const permissionInputs = Array.from(document.querySelectorAll("[data-permission-key]"));

    const kindText = {
      admin: "Admin opens the full control plane, including channels, broadcasts, staff, bots, and system modules.",
      moderator: "Moderator focuses on community cleanup and post safety without broader site-control access.",
      bot_operator: "Bot Operator is the human login for a linked bot profile like ColorsTheForce and can be given moderation overrides when needed.",
      user: "User is a low-privilege internal profile for observation, QA, or future limited workflows.",
      bot: "Bot creates a site-owned AI profile with provider, model, scope, and guardrail controls.",
    };

    function applyRoleDefaults(role) {
      const defaults = roleDefaults[role] || {};
      permissionInputs.forEach((input) => {
        input.checked = Boolean(defaults[input.dataset.permissionKey]);
      });
    }

    function syncProfileKind() {
      const kind = kindSelect.value || "admin";
      const isBot = kind === "bot";
      if (humanPanel) humanPanel.hidden = isBot;
      if (botPanel) botPanel.hidden = !isBot;
      if (roleInput) roleInput.value = isBot ? "" : kind;
      if (kindCopy) kindCopy.textContent = kindText[kind] || "";
      if (!isBot) applyRoleDefaults(kind);
    }

    kindSelect.addEventListener("change", syncProfileKind);
    syncProfileKind();
  }

  function syncDraftSurface(form) {
    const select = form.querySelector("[data-surface-select]");
    if (!select) return;
    const surface = select.value || "announcement";
    form.querySelectorAll("[data-surface-panel]").forEach((panel) => {
      panel.hidden = panel.getAttribute("data-surface-panel") !== surface;
    });
  }

  document.querySelectorAll("[data-draft-form]").forEach((form) => {
    const select = form.querySelector("[data-surface-select]");
    if (!select) return;
    select.addEventListener("change", function () {
      syncDraftSurface(form);
    });
    syncDraftSurface(form);
  });

  const opsGrid = document.querySelector(".ops-grid");
  const opsPanels = Array.from(document.querySelectorAll(".ops-panel"));
  const controlFolds = Array.from(document.querySelectorAll("details.control-fold"));
  const panelStateKey = "triptokforge.ops.panelState.v2";
  const clusterStateKey = "triptokforge.ops.cluster.v1";
  const foldStateKey = "triptokforge.ops.folds.v1";
  const clusterTabs = Array.from(document.querySelectorAll("[data-cluster-tab]"));
  let savedPanelState = {};
  let savedFoldState = {};
  let activeCluster = window.localStorage.getItem(clusterStateKey) || "all";

  try {
    savedPanelState = JSON.parse(window.localStorage.getItem(panelStateKey) || "{}");
  } catch (_error) {
    savedPanelState = {};
  }
  try {
    savedFoldState = JSON.parse(window.localStorage.getItem(foldStateKey) || "{}");
  } catch (_error) {
    savedFoldState = {};
  }

  function panelStorageId(panel, index) {
    return panel.id || panel.dataset.panelId || "panel-" + index;
  }

  function persistPanelState() {
    const payload = {};
    opsPanels.forEach((panel, index) => {
      payload[panelStorageId(panel, index)] = {
        compact: panel.classList.contains("ops-panel--compact"),
        maximized: panel.classList.contains("ops-panel--maximized"),
      };
    });
    try {
      window.localStorage.setItem(panelStateKey, JSON.stringify(payload));
    } catch (_error) {
      // Ignore storage errors and keep the console interactive.
    }
  }

  function foldStorageId(fold, index) {
    return fold.id || "fold-" + index;
  }

  function persistFoldState() {
    const payload = {};
    controlFolds.forEach((fold, index) => {
      payload[foldStorageId(fold, index)] = {
        open: fold.open,
      };
    });
    try {
      window.localStorage.setItem(foldStateKey, JSON.stringify(payload));
    } catch (_error) {
      // Ignore storage errors and keep the console interactive.
    }
  }

  function panelRowSpan(panel) {
    if (!opsGrid || !panel) return;
    const computed = window.getComputedStyle(opsGrid);
    const rowSize = parseFloat(computed.getPropertyValue("grid-auto-rows")) || 10;
    const gap = parseFloat(computed.getPropertyValue("gap")) || 14;
    const height = panel.getBoundingClientRect().height;
    const span = Math.max(18, Math.ceil((height + gap) / (rowSize + gap)));
    panel.style.gridRowEnd = "span " + span;
  }

  function syncPanelDensity(panel) {
    const count = Number(panel.dataset.panelCount || "0");
    panel.classList.remove("ops-panel--highlight", "ops-panel--auto-compact");
    if (count === 0 && !panel.classList.contains("ops-panel--compact")) {
      panel.classList.add("ops-panel--auto-compact");
    }
    if (count > 0) {
      panel.classList.add("ops-panel--highlight");
    }
  }

  function syncOpsPanels() {
    opsPanels.forEach((panel) => {
      syncPanelDensity(panel);
      panelRowSpan(panel);
    });
  }

  function syncClusterFilter() {
    if (!clusterTabs.length) return;
    const availableClusters = new Set(
      opsPanels.map((panel) => panel.getAttribute("data-cluster") || "all")
    );
    if (activeCluster !== "all" && !availableClusters.has(activeCluster)) {
      activeCluster = "all";
    }
    clusterTabs.forEach((tab) => {
      const selected = (tab.getAttribute("data-cluster-tab") || "all") === activeCluster;
      tab.classList.toggle("is-active", selected);
    });
    opsPanels.forEach((panel) => {
      const cluster = panel.getAttribute("data-cluster") || "all";
      panel.hidden = activeCluster !== "all" && cluster !== activeCluster;
    });
  }

  function openFoldFromHash() {
    const hash = (window.location.hash || "").replace(/^#/, "");
    if (!hash) return;
    const target = document.getElementById(hash);
    if (!target) return;
    const panel = target.closest(".ops-panel");
    if (panel) {
      const panelCluster = panel.getAttribute("data-cluster") || "all";
      if (activeCluster !== "all" && panelCluster !== activeCluster) {
        activeCluster = panelCluster;
        try {
          window.localStorage.setItem(clusterStateKey, activeCluster);
        } catch (_error) {
          // Ignore storage errors and keep the console interactive.
        }
        syncClusterFilter();
      }
    }
    const fold = target.matches("details.control-fold") ? target : target.closest("details.control-fold");
    if (fold) {
      fold.open = true;
      persistFoldState();
    }
  }

  opsPanels.forEach((panel, index) => {
    const state = savedPanelState[panelStorageId(panel, index)] || {};
    if (state.compact) panel.classList.add("ops-panel--compact");
    if (state.maximized) panel.classList.add("ops-panel--maximized");
  });

  controlFolds.forEach((fold, index) => {
    const state = savedFoldState[foldStorageId(fold, index)];
    if (state && typeof state.open === "boolean") {
      fold.open = state.open;
    }
    fold.addEventListener("toggle", function () {
      persistFoldState();
      syncOpsPanels();
    });
  });

  opsPanels.forEach((panel) => {
    panel.querySelectorAll("[data-panel-action]").forEach((button) => {
      button.addEventListener("click", function () {
        const action = button.getAttribute("data-panel-action");
        if (action === "maximize") {
          panel.classList.toggle("ops-panel--maximized");
        }
        if (action === "compact") {
          panel.classList.toggle("ops-panel--compact");
        }
        syncOpsPanels();
        persistPanelState();
      });
    });
  });

  clusterTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      activeCluster = tab.getAttribute("data-cluster-tab") || "all";
      try {
        window.localStorage.setItem(clusterStateKey, activeCluster);
      } catch (_error) {
        // Ignore storage errors and keep the console interactive.
      }
      syncClusterFilter();
      syncOpsPanels();
    });
  });

  if (typeof ResizeObserver !== "undefined" && opsPanels.length) {
    const observer = new ResizeObserver(() => {
      syncOpsPanels();
    });
    opsPanels.forEach((panel) => observer.observe(panel));
  }

  window.addEventListener("resize", syncOpsPanels);
  window.addEventListener("hashchange", openFoldFromHash);
  syncClusterFilter();
  openFoldFromHash();
  syncOpsPanels();
  persistPanelState();
  persistFoldState();
})();
