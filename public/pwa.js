(function () {
  "use strict";
  var nimiLogo = "/public/nimi-logo.svg";
  var nimiIcon = "/public/icon-192.png";

  function setFavicon() {
    var links = document.querySelectorAll('link[rel~="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
    links.forEach(function (link) { link.href = nimiIcon; });
    if (!links.length) {
      var link = document.createElement("link");
      link.rel = "icon";
      link.href = nimiIcon;
      document.head.appendChild(link);
    }
  }

  function setHeaderLogo() {
    document.querySelectorAll('img[alt="logo"], img.logo, header img').forEach(function (img) {
      if (img.src.indexOf("/public/nimi-logo.svg") === -1) {
        img.src = nimiLogo;
        img.alt = "Nimi";
      }
    });
  }

  function applyBranding() {
    setFavicon();
    setHeaderLogo();
  }

  applyBranding();
  new MutationObserver(applyBranding).observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ["href", "src"]
  });

  var manifest = document.createElement("link");
  manifest.rel = "manifest";
  manifest.href = "/public/manifest.json";
  document.head.appendChild(manifest);

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