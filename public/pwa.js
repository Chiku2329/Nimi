(function () {
  "use strict";
  var icon = "/public/nimi-infinity.svg?v=5";
  var touchIcon = icon;
  var wordmark = "/public/nimi-logo.svg?v=5";

  function recoverStuckGuestAuth() {
    if (window.location.pathname !== "/login/callback") return;
    var params = new URLSearchParams(window.location.search);
    if ((params.get("success") || "").toLowerCase() !== "true") return;
    var key = "nimi_guest_auth_retry_at";
    var now = Date.now();
    try {
      var previous = Number(window.sessionStorage.getItem(key) || 0);
      if (previous && now - previous < 30000) return;
      window.sessionStorage.setItem(key, String(now));
    } catch (_) { return; }
    window.setTimeout(function () {
      if (window.location.pathname === "/login/callback") window.location.replace("/guest-auth");
    }, 8000);
  }
  recoverStuckGuestAuth();

  // Chainlit 2.12.0 uses React Dropzone for its composer upload control.
  // Bridge native file-picker selections through the same drop handler used
  // by drag-and-drop. This avoids relying on the frontend's file-input
  // change callback when the browser closes the picker without uploading.
  function installFilePickerBridge() {
    if (document.documentElement.dataset.nimiPickerBridge === "installed") return;
    document.documentElement.dataset.nimiPickerBridge = "installed";

    document.addEventListener("change", function (event) {
      var input = event.target;
      if (!input || input.id !== "upload-button-input" || !input.files || !input.files.length) return;

      var root = input.parentElement && input.parentElement.querySelector("button");
      if (!root) return;

      var transfer;
      var dropEvent;
      try {
        transfer = new DataTransfer();
        Array.prototype.forEach.call(input.files, function (file) {
          transfer.items.add(file);
        });
        dropEvent = new DragEvent("drop", {
          bubbles: true,
          cancelable: true,
          dataTransfer: transfer
        });
      } catch (_) {
        // Keep Chainlit's native handler intact if this browser cannot create
        // a synthetic DataTransfer/DragEvent.
        return;
      }

      // Stop React Dropzone's input-change path only after the fallback event
      // has been constructed successfully; the drop handler owns validation
      // and upload for both picker and drag-and-drop selections.
      event.stopImmediatePropagation();
      root.dispatchEvent(dropEvent);
      input.value = "";
    }, true);
  }
  installFilePickerBridge();

  function upsertLink(rel, href, type, sizes) {
    var links = document.querySelectorAll('link[rel="' + rel + '"]');
    if (!links.length) {
      var el = document.createElement("link");
      el.rel = rel;
      document.head.appendChild(el);
      links = [el];
    }
    Array.prototype.forEach.call(links, function (el) {
      el.href = href;
      if (type) el.type = type;
      if (sizes) el.sizes = sizes;
    });
  }
  function setBrandIcons() {
    upsertLink("icon", icon, "image/svg+xml", "any");
    upsertLink("shortcut icon", icon, "image/svg+xml");
    upsertLink("apple-touch-icon", touchIcon, "image/svg+xml", "any");
    document.querySelectorAll('img[alt="logo"], img.logo, header img').forEach(function (img) {
      if (img.src.indexOf("/public/nimi-infinity.svg") === -1) {
        img.src = icon;
        img.alt = "Nimi";
      }
    });
  }
  setBrandIcons();
  new MutationObserver(setBrandIcons).observe(document.documentElement, {childList: true, subtree: true});

  var manifestLink = document.querySelector('link[rel="manifest"]') || document.createElement("link");
  manifestLink.rel = "manifest";
  manifestLink.href = "/public/manifest.json?v=5";
  if (!manifestLink.isConnected) document.head.appendChild(manifestLink);
  [["theme-color", "#080b1b"], ["apple-mobile-web-app-capable", "yes"],
   ["apple-mobile-web-app-title", "Nimi"], ["mobile-web-app-capable", "yes"]].forEach(function (p) {
    var m = document.querySelector('meta[name="' + p[0] + '"]') || document.createElement("meta");
    m.name = p[0]; m.content = p[1];
    if (!m.isConnected) document.head.appendChild(m);
  });
  var installEvent = null, button = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault(); installEvent = e; if (button) return;
    button = document.createElement("button"); button.textContent = "Install Nimi";
    button.type = "button";
    button.style.cssText = "position:fixed;right:18px;bottom:18px;z-index:99999;border:0;border-radius:999px;padding:12px 18px;background:#d9d5e8;color:#17151d;font:600 14px system-ui;box-shadow:0 4px 18px #0005;cursor:pointer";
    button.addEventListener("click", async function () {
      if (!installEvent) return;
      installEvent.prompt(); await installEvent.userChoice; installEvent = null;
      button.remove(); button = null;
    });
    document.body.appendChild(button);
  });
  window.addEventListener("appinstalled", function () { installEvent = null; if (button) button.remove(); button = null; });
})();
