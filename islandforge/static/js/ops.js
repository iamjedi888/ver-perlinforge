(function () {
  const catalogNode = document.getElementById("llm-provider-catalog");
  if (!catalogNode) return;

  let catalog = [];
  try {
    catalog = JSON.parse(catalogNode.textContent || "[]");
  } catch (_error) {
    catalog = [];
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
})();
