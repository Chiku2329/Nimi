(function () {
  "use strict";

  function addLink(rel, href) {
    var link = document.createElement("link");
    link.rel = rel;
    link.href = href;
    document.head.appendChild(link);
  }

  function addMeta(name, content) {
    var meta = document.createElement("meta");
    meta.name = name;
    meta.content = content;
    document.head.appendChild(meta);
  }

  // Install metadata for desktop browsers and mobile home-screen installation.
  addLink("manifest", "/public/manifest.json");
  addLink("icon", "/public/favicon.png");
  addLink("apple-touch-icon", "/public/icon-192.png");
  addMeta("theme-color", "#4f46e5");
  addMeta("apple-mobile-web-app-capable", "yes");
  addMeta("apple-mobile-web-app-title", "Nimi");
  addMeta("apple-mobile-web-app-status-bar-style", "default");
  addMeta("mobile-web-app-capable", "yes");

  // Keep the native browser install flow. The browser decides when installation
  // is available; no fake download link or unsupported install prompt is shown.
  var deferredInstallPrompt = null;
  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
    window.dispatchEvent(new CustomEvent("nimi-install-available"));
  });

  window.addEventListener("appinstalled", function () {
    deferredInstallPrompt = null;
    window.dispatchEvent(new CustomEvent("nimi-installed"));
  });

  // Expose a small, documented hook for a future in-app install button.
  window.nimiInstallApp = async function () {
    if (!deferredInstallPrompt) return false;
    deferredInstallPrompt.prompt();
    var result = await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    return result && result.outcome === "accepted";
  };
})();
