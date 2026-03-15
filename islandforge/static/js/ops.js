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
  if (!kindSelect) return;

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
})();
