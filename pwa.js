(function () {
  function add(tag, attrs) {
    var el = document.createElement(tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    document.head.appendChild(el);
  }
  add("link", {rel: "manifest", href: "/public/manifest.json"});
  add("link", {rel: "apple-touch-icon", href: "/public/icon-192.png"});
  add("meta", {name: "theme-color", content: "#4f46e5"});
})();
