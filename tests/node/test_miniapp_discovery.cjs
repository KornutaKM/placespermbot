"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../app/miniapp_static/app.js"), "utf8"
).replace(/void main\(\);\s*$/, "");

function element() {
  return {
    innerHTML: "", textContent: "", value: "", handlers: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener(name, handler) { this.handlers[name] = handler; },
    setAttribute() {}, removeAttribute() {},
    replaceChildren() { this.innerHTML = ""; },
    querySelector() { return element(); }, querySelectorAll() { return []; }
  };
}
const elements = new Map();
const doc = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  addEventListener() {},
  querySelectorAll() { return []; }
};
const calls = [];
let resolveOld;
const malicious = {
  city_slug: "kazan", city_name: "Казань", place_slug: "kreml",
  title: "<img src=x onerror=alert(1)>",
  summary: "<script>danger</script>", emoji: "<svg/onload=alert(1)>",
  category_label: "Достопримечательности", district: "Центр",
  visit_minutes: 30
};
function response(body) { return { ok: true, json: async () => body }; }
const fetchMock = async (url, options) => {
  calls.push({ url, options });
  if (url.startsWith("/api/discover?")) {
    const params = new URLSearchParams(url.split("?")[1]);
    const q = params.get("q");
    if (q === "старый") return new Promise(resolve => { resolveOld = resolve; });
    if (q === "музей") {
      return response({
        query: q, category: params.get("category"), offset: Number(params.get("offset")),
        total: 13, has_more: true, places: [malicious]
      });
    }
    return response({
      query: q, category: params.get("category"), offset: Number(params.get("offset")),
      total: 1, has_more: false, places: [{ ...malicious, title: "Парк" }]
    });
  }
  if (url === "/api/catalogs/kazan") return response({
    slug: "kazan", name: "Казань",
    category_labels: { sights: "Достопримечательности" },
    routes: [], places: [{
      slug: "kreml", title: "Казанский кремль", summary: "Описание",
      emoji: "🏛", category_label: "Достопримечательности",
      district: "Центр", visit_minutes: 40, is_free: true, tags: [],
      map_url: "https://www.google.com/maps/search/?api=1&query=kazan"
    }]
  });
  throw Error("Unexpected request " + url);
};
const context = {
  URLSearchParams, document: doc,
  window: { Telegram: { WebApp: { initData: "" } }, scrollTo() {} },
  fetch: fetchMock,
  setTimeout() { return 1; }, clearTimeout() {}
};
vm.runInNewContext(
  source + "\nthis.__ui = {state, navigate, renderHome, renderDiscover, " +
  "requestDiscovery, openDiscoveryPlace, openCities};",
  context, { timeout: 1500 }
);

async function test() {
  const ui = context.__ui;
  const { state, navigate, renderHome, renderDiscover, requestDiscovery,
    openDiscoveryPlace, openCities } = ui;
  state.catalog = {
    slug: "perm", name: "Пермь", routes: [], places: [],
    category_labels: {}
  };
  state.cities = [
    { slug: "perm", name: "Пермь" },
    { slug: "kazan", name: "Казань" },
    { slug: "moscow", name: "Москва" }
  ];
  state.tab = "home";
  renderHome();
  assert.match(doc.getElementById("screen").innerHTML, /data-open="discover"/);
  assert.equal(calls.length, 0, "Discovery must not prefetch");

  navigate("discover");
  assert.equal(state.tab, "discover");
  assert.match(doc.getElementById("discovery-results").innerHTML, /минимум два/);
  const input = doc.getElementById("discovery-query");
  input.handlers.input({ target: { value: "музей" } });
  await requestDiscovery();
  const markup = doc.getElementById("discovery-results").innerHTML;
  assert.match(markup, /Казань/);
  assert.match(markup, /data-discover-place="kreml"/);
  assert.match(markup, /Показать ещё/);
  assert.match(markup, /&lt;img/);
  assert.match(markup, /&lt;script&gt;/);
  assert.doesNotMatch(markup, /<script>|<img src|<svg\/onload/);
  assert.equal(state.discovery.total, 13);

  // An out-of-order response must not repaint the current search.
  state.discovery.query = "старый";
  const old = requestDiscovery();
  state.discovery.query = "парк";
  ++state.discovery.version;
  state.discovery.loading = false;
  await requestDiscovery();
  resolveOld(response({
    query: "старый", category: "all", offset: 0, total: 1,
    has_more: false, places: [malicious]
  }));
  await old;
  assert.equal(state.discovery.places[0].title, "Парк");
  assert.doesNotMatch(doc.getElementById("discovery-results").innerHTML, /&lt;img/);

  // City picker is searchable without network requests or implicit city writes.
  const before = calls.length;
  openCities();
  const field = doc.getElementById("city-filter");
  assert.match(doc.getElementById("city-choices").innerHTML, /Казань/);
  field.value = "каз";
  field.handlers.input();
  assert.match(doc.getElementById("city-choices").innerHTML, /Казань/);
  assert.doesNotMatch(doc.getElementById("city-choices").innerHTML, /Москва/);
  assert.equal(calls.length, before);

  // A place opens only after the selected city's public catalog is loaded.
  await openDiscoveryPlace("kazan", "kreml");
  assert.equal(state.catalog.slug, "kazan");
  assert.equal(state.tab, "places");
  assert.match(doc.getElementById("sheet-root").innerHTML, /Казанский кремль/);
  assert.equal(calls.filter(c => c.url === "/api/catalogs/kazan").length, 1);
  assert.equal(calls.filter(c => c.options.method === "POST").length, 0,
    "Read-only browser mode must not write a user city");
  assert.equal(calls.filter(c => c.url.startsWith("/api/discover")).length, 3);
  console.log("Mini App cross-city discovery regression passed");
}
test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
