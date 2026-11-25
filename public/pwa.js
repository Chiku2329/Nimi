(function () {
  "use strict";
  var icon = "/public/nimi-infinity.svg?v=6";
  var touchIcon = icon;
  var wordmark = "/public/nimi-logo.svg?v=6";

  // The splash is a first-paint brand surface. Dismiss it as soon as the
  // application main region mounts; do not wait for the composer/textarea.
  function dismissStartupBrandingWhenReady() {
    function start() {
      if (!document.body) return;
      var finished = false;
      var observer = new MutationObserver(check);
      function finish() {
        if (finished) return;
        finished = true;
        document.body.classList.add("nimi-app-ready");
        observer.disconnect();
      }
      function check() {
        var main = document.querySelector("#root main");
        if (main && main.getBoundingClientRect().width > 0) finish();
      }
      observer.observe(document.documentElement, { childList: true, subtree: true });
      check();
      // Fail open on login/error pages; never leave the cover stuck.
      window.setTimeout(finish, 8000);
    }
    if (document.body) start();
    else document.addEventListener("DOMContentLoaded", start, { once: true });
  }
  dismissStartupBrandingWhenReady();

  recoverStuckGuestAuth();

  // Chainlit 2.12.0 uses React Dropzone for file uploads. Bridge native
  // file-picker selections through the composer-level drop handler, which
  // is also used by drag-and-drop.
  function installFilePickerBridge() {
    if (document.documentElement.dataset.nimiPickerBridge === "installed") return;
    document.documentElement.dataset.nimiPickerBridge = "installed";

    // The Chainlit paperclip button's React Dropzone click handler is not
    // opening its hidden input in this deployment. Forward the real user click
    // synchronously so the browser's user-activation permission is preserved.
    document.addEventListener("click", function (event) {
      var target = event.target;
      var button = target && target.closest ? target.closest("#upload-button") : null;
      if (!button) return;
      var input = document.getElementById("upload-button-input");
      if (!input || input.disabled) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      input.click();
    }, true);

    document.addEventListener("change", function (event) {
      var input = event.target;
      if (!input || input.id !== "upload-button-input" || !input.files || !input.files.length) return;

      // Chainlit's composer-level dropzone owns the upload callback. Its
      // hidden input is a direct child of the root element.
      var dropInput = document.getElementById("#upload-drop-input");
      var root = dropInput && dropInput.parentElement;
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
  }
  setBrandIcons();
  new MutationObserver(setBrandIcons).observe(document.documentElement, {childList: true, subtree: true});

  var manifestLink = document.querySelector('link[rel="manifest"]') || document.createElement("link");
  manifestLink.rel = "manifest";
  manifestLink.href = "/public/manifest.json?v=6";
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
