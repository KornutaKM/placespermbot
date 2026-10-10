"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const base = path.join(__dirname, "../../app/miniapp_static");
const mapSource = fs.readFileSync(path.join(base, "map.js"), "utf8");
const appSource = fs.readFileSync(path.join(base, "app.js"), "utf8")
  .replace(/void main\(\);\s*$/, "");

const events = [];
const markers = [];
const layers = [];
const mockL = {
  map(id, options) {
    events.push(["mount", id, options]);
    return {
      setView(coords, zoom) { events.push(["setView", coords, zoom]); return this; },
      fitBounds(bounds, options) { events.push(["fitBounds", bounds, options]); return this; },
      panTo(coords) { events.push(["panTo", coords]); },
      remove() { events.push(["destroy"]); }
    };
  },
  tileLayer(url, options) {
    events.push(["tile", url, options]);
    return { addTo(map) { return this; } };
  },
  layerGroup() {
    const layer = {
      clearLayers() { events.push(["clear"]); },
      addTo(map) { return this; }
    };
    layers.push(layer);
    return layer;
  },
  divIcon(options) { return options; },
  marker(coords, options) {
    const marker = {
      coords, options, handlers: {},
      addTo(layer) { markers.push(marker); return this; },
      on(name, cb) { this.handlers[name] = cb; return this; }
    };
    return marker;
  }
};

function element() {
  return {
    innerHTML: "", textContent: "", value: "",
    classList: { toggle() {}, add() {}, remove() {} },
    setAttribute() {}, removeAttribute() {},
    addEventListener(eventName, callback) {
      this.handlers ||= {};
      this.handlers[eventName] = callback;
    },
    replaceChildren() {},
    querySelector() { return null; }, querySelectorAll() { return []; }
  };
}
const elements = new Map();
const doc = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  querySelectorAll() { return []; },
  addEventListener() {}
};
const ctx = {
  window: {
    L: mockL,
    Telegram: { WebApp: { initData: "" } },
    scrollTo() {}
  },
  document: doc,
  setTimeout() { return 1; }, clearTimeout() {},
  fetch() { throw Error("Map should not fetch user data"); }
};
vm.runInNewContext(mapSource, ctx);
vm.runInNewContext(
  appSource + "\nthis.__ui = {state, navigate, drawMapPoints, " +
  "selectMapPlace, mapVisiblePlaces};",
  ctx
);
const { state, navigate, drawMapPoints, selectMapPlace, mapVisiblePlaces } = ctx.__ui;

const first = {
  slug: "place-one", title: "Музей & театр",
  latitude: 58.009, longitude: 56.234, emoji: "🏛",
  is_free: true, tags: [], category: "museum", category_label: "Музей",
  summary: "Тест", district: "Центр", visit_minutes: 30
};
const second = {
  ...first, slug: "place-two", title: "Парк", latitude: 58.01,
  longitude: 56.235, emoji: "<img onerror=alert(1)>",
  is_free: false, category: "parks", category_label: "Парки"
};
const invalid = { ...first, slug: "bad", latitude: NaN };
state.catalog = {
  slug: "perm", name: "Пермь",
  places: [first, second, invalid], routes: [],
  category_labels: { museum: "Музей", parks: "Парки" }
};
state.cities = [{ slug: "perm", name: "Пермь" }];

assert.equal(ctx.window.PlacesMap.validCoordinates(first), true);
assert.equal(ctx.window.PlacesMap.validCoordinates(invalid), false);
assert.equal(events.filter(event => event[0] === "tile").length, 0,
  "The tile layer must not be requested before map navigation");

navigate("map");
assert.equal(state.tab, "map");
assert.equal(events.filter(event => event[0] === "mount").length, 1);
const tiles = events.find(event => event[0] === "tile");
assert.equal(tiles[1], "https://tile.openstreetmap.org/{z}/{x}/{y}.png");
assert.equal(tiles[2].referrerPolicy, "strict-origin-when-cross-origin");
assert.match(tiles[2].attribution, /OpenStreetMap contributors/);
assert.equal(state.mapController.count(), 2);
assert.match(doc.getElementById("map-count").textContent, /2 мест/);
assert.equal(mapVisiblePlaces().length, 2);
assert.match(markers[1].options.icon.html, /&lt;img/);
assert.doesNotMatch(markers[1].options.icon.html, /<img/);

markers[0].handlers.click();
assert.equal(state.mapSelected, "place-one");
assert.match(doc.getElementById("map-preview").innerHTML, /Музей &amp; театр/);
assert.ok(events.some(event => event[0] === "panTo"));

state.mapFilter = "free";
drawMapPoints();
assert.equal(state.mapController.count(), 1);
assert.equal(state.mapSelected, "place-one");

state.mapSearch = "нет совпадений";
drawMapPoints();
assert.equal(state.mapController.count(), 0);
assert.equal(state.mapSelected, null);
assert.match(doc.getElementById("map-preview").innerHTML, /не найдено/);

state.mapSearch = "";
state.mapFilter = "all";
drawMapPoints();
selectMapPlace("place-two");
assert.equal(state.mapSelected, "place-two");

navigate("home");
assert.equal(events.filter(event => event[0] === "destroy").length, 1);
assert.equal(state.mapController, null);

ctx.window.L = null;
navigate("map");
assert.equal(state.mapController, null);
assert.match(doc.getElementById("map-fallback").textContent,
  /Карта временно недоступна/);
assert.match(doc.getElementById("map-matches").innerHTML, /place-one/);
assert.equal(mapVisiblePlaces().length, 2,
  "Fallback results must not depend on Leaflet CDN availability");

console.log("Mini App interactive map lifecycle and filters passed");
