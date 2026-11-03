(function () {
  "use strict";
  var icon = "/public/nimi-infinity.svg?v=3";
  var touchIcon = "/public/icon-512.png?v=3";
  var wordmark = "/public/nimi-logo.svg?v=3";

  function upsertLink(rel, href, type, sizes) {
    var selector = 'link[rel="' + rel + '"]';
    var links = document.querySelectorAll(selector);
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
    upsertLink("apple-touch-icon", touchIcon, "image/png", "512x512");
    document.querySelectorAll('img[alt="logo"], img.logo, header img').forEach(function (img) {
      if (img.src.indexOf("/public/nimi-infinity.svg") === -1) {
        img.src = icon;
        img.alt = "Nimi";
      }
    });
  }

  function applyBranding() { setBrandIcons(); }
  applyBranding();
  new MutationObserver(applyBranding).observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ["href", "src"]
  });

  var manifestLink = document.querySelector('link[rel="manifest"]') || document.createElement("link");
  manifestLink.rel = "manifest";
  manifestLink.href = "/public/manifest.json?v=3";
  document.head.appendChild(manifestLink);

  [["theme-color", "#0c0e14"], ["apple-mobile-web-app-capable", "yes"],
   ["apple-mobile-web-app-title", "Nimi"], ["mobile-web-app-capable", "yes"]]
    .forEach(function (p) {
      var m = document.querySelector('meta[name="' + p[0] + '"]') || document.createElement("meta");
      m.name = p[0]; m.content = p[1]; document.head.appendChild(m);
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
  window.addEventListener("appinstalled", function () {
    installEvent = null; if (button) button.remove(); button = null;
  });
})();