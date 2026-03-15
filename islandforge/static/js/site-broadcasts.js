(function () {
  if (window.__triptokSiteBroadcastsLoaded) {
    return;
  }
  window.__triptokSiteBroadcastsLoaded = true;

  const cards = Array.from(document.querySelectorAll("[data-site-broadcast]"));
  if (!cards.length) {
    return;
  }

  const modalStack = document.querySelector("[data-site-broadcast-modal-stack]");

  function storageKey(card) {
    return `tf-broadcast-dismissed:${card.dataset.broadcastId}:${card.dataset.displayMode}`;
  }

  function storageBucket(card) {
    const dismissMode = (card.dataset.dismissMode || "manual").toLowerCase();
    if (dismissMode === "persistent") {
      return window.localStorage;
    }
    if (dismissMode === "manual") {
      return window.sessionStorage;
    }
    return null;
  }

  function rememberDismissal(card) {
    if (card.dataset.closable !== "1") {
      return;
    }
    const bucket = storageBucket(card);
    if (!bucket) {
      return;
    }
    try {
      bucket.setItem(storageKey(card), "1");
    } catch (error) {
      // Ignore storage issues and still dismiss locally.
    }
  }

  function wasDismissed(card) {
    if (card.dataset.closable !== "1") {
      return false;
    }
    const bucket = storageBucket(card);
    if (!bucket) {
      return false;
    }
    try {
      return bucket.getItem(storageKey(card)) === "1";
    } catch (error) {
      return false;
    }
  }

  function syncModalState() {
    if (!modalStack) {
      return;
    }
    const visibleCards = modalStack.querySelectorAll("[data-site-broadcast]");
    modalStack.classList.toggle("is-empty", visibleCards.length === 0);
  }

  function dismissCard(card, persist, instant) {
    if (!card || card.dataset.state === "dismissed") {
      return;
    }
    card.dataset.state = "dismissed";
    if (persist) {
      rememberDismissal(card);
    }
    if (instant) {
      card.remove();
      syncModalState();
      return;
    }
    card.classList.add("is-dismissed");
    window.setTimeout(() => {
      card.remove();
      syncModalState();
    }, 280);
  }

  let modalSeen = false;
  cards.forEach((card) => {
    if (wasDismissed(card)) {
      dismissCard(card, false, true);
      return;
    }

    if (card.dataset.displayMode === "modal") {
      if (modalSeen) {
        dismissCard(card, false, true);
        return;
      }
      modalSeen = true;
    }

    window.requestAnimationFrame(() => {
      card.classList.add("is-live");
    });

    const closeButton = card.querySelector("[data-broadcast-close]");
    if (closeButton) {
      closeButton.addEventListener("click", () => {
        dismissCard(card, true, false);
      });
    }

    const dismissMode = (card.dataset.dismissMode || "manual").toLowerCase();
    const durationSeconds = Number(card.dataset.duration || "8");
    if (dismissMode === "auto" && Number.isFinite(durationSeconds) && durationSeconds > 0) {
      window.setTimeout(() => {
        dismissCard(card, false, false);
      }, durationSeconds * 1000);
    }
  });

  syncModalState();
})();
