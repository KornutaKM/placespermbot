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
    innerHTML: "", textContent: "", value: "",
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    replaceChildren() {}
  };
}
const nodes = new Map();
const document = {
  getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, element());
    return nodes.get(id);
  },
  addEventListener() {}, querySelectorAll() { return []; }
};
const place = (slug, title) => ({
  slug, title, emoji: "🏛", district: "Центр", visit_minutes: 40,
  latitude: 56.4, longitude: 40.4
});
const base = {
  city_slug: "suzdal", route_id: "0123456789abcdef",
  interest: "classic", interest_label: "Главные места",
  budget_minutes: 240, estimated_minutes: 145,
  visit_minutes: 120, walking_minutes: 25, spare_minutes: 95,
  distance_km: 1.8,
  places: [place("a", "Кремль"), place("b", "Торговые ряды"),
    place("c", "Собор")],
  map_links: [{url: "https://www.google.com/maps/dir/?api=1", mode: "walking"}]
};
const changed = {
  ...base, route_id: "abcdef0123456789",
  estimated_minutes: 150, walking_minutes: 30, spare_minutes: 90,
  places: [place("a", "Кремль"), place("d", "Другая точка <script>"),
    place("c", "Собор")]
};
const alternative = {
  slug: "d", title: "Другая точка <script>", emoji: "✨",
  estimated_minutes: 150, visit_minutes: 40,
  district: "Старый город", category: "sights"
};
const calls = [];
let failReplace = false;
async function fakeFetch(url, options = {}) {
  const body = options.body ? JSON.parse(options.body) : null;
  calls.push({url, method: options.method || "GET", body, headers: options.headers});
  if (url === "/api/routes/suzdal/preview") {
    return {ok: true, json: async () => base};
  }
  if (url === "/api/routes/suzdal/alternatives") {
    assert.equal(body.base_route_id, base.route_id);
    assert.deepEqual(Array.from(body.place_slugs), ["a", "b", "c"]);
    assert.equal(body.stop_index, 1);
    return {ok: true, json: async () => ({
      city_slug: "suzdal", base_route_id: base.route_id,
      stop_index: 1, alternatives: [alternative]
    })};
  }
  if (url === "/api/routes/suzdal/replace") {
    assert.equal(body.base_route_id, base.route_id);
    assert.equal(body.stop_index, 1);
    assert.equal(body.candidate_slug, "d");
    if (failReplace) return {ok: false, status: 422};
    return {ok: true, json: async () => changed};
  }
  if (url === "/api/me/routes/suzdal/save-replaced") {
    assert.equal(body.base_route_id, base.route_id);
    assert.equal(body.candidate_slug, "d");
    assert.equal(body.stop_index, 1);
    assert.equal(body.expected_route_id, changed.route_id);
    assert.deepEqual(Array.from(body.place_slugs), ["a", "b", "c"]);
    assert.ok(!Object.hasOwn(body, "user_id"));
    return {ok: true, json: async () => ({
      city_slug: "suzdal", route_id: changed.route_id, saved: true
    })};
  }
  if (url === "/api/me/guide/suzdal") {
    return {ok: true, json: async () => ({
      city_slug: "suzdal", visited_slugs: [],
      stats: {saved_routes: 1}, saved_routes: [], completed_routes: []
    })};
  }
  throw Error("Unexpected request: " + url);
}
const context = {
  window: {
    Telegram: {WebApp: {initData: "signed-init-data"}},
    scrollTo() {}
  },
  document, fetch: fakeFetch, setTimeout() {return 1;}, clearTimeout() {}
};
vm.runInNewContext(
  source + "\nthis.__view = {state, navigate, buildPreview, " +
  "showBuilderAlternatives, replaceBuilderStop, editBuilderStop, " +
  "saveBuiltRoute, updateBuilderOption};",
  context
);
const ui = context.__view;
ui.state.catalog = {
  slug: "suzdal", name: "Суздаль", places: [],
  routes: [], category_labels: {}
};
ui.state.cities = [{slug: "suzdal", name: "Суздаль"}];

async function run() {
  ui.navigate("builder");
  await ui.buildPreview();
  assert.match(nodes.get("screen").innerHTML, /data-builder-alternatives="1"/);
  assert.match(nodes.get("screen").innerHTML, /⇄/);
  await ui.showBuilderAlternatives(1);
  assert.match(nodes.get("screen").innerHTML, /Подходящие замены/);
  assert.match(nodes.get("screen").innerHTML, /data-builder-choose="d"/);
  assert.match(nodes.get("screen").innerHTML, /&lt;script&gt;/);
  assert.doesNotMatch(nodes.get("screen").innerHTML, /Другая точка <script>/);
  const beforeCount = calls.length;
  await ui.replaceBuilderStop("forged");
  assert.equal(calls.length, beforeCount,
    "Only a server-presented suggestion may be submitted");

  failReplace = true;
  await ui.replaceBuilderStop("d");
  assert.equal(ui.state.builder.result.route_id, base.route_id,
    "Rejected replacement leaves the old route");
  assert.ok(ui.state.builder.alternatives);
  failReplace = false;
  await ui.replaceBuilderStop("d");
  assert.equal(ui.state.builder.result.route_id, changed.route_id);
  assert.equal(ui.state.builder.replacement.candidate_slug, "d");
  assert.equal(ui.state.builder.edited, true);
  assert.equal(ui.state.builder.baseRouteId, base.route_id);
  assert.match(nodes.get("screen").innerHTML, /Остановка заменена/);
  assert.match(nodes.get("screen").innerHTML, /150/);
  const count = calls.length;
  await ui.editBuilderStop("up", 1);
  await ui.showBuilderAlternatives(0);
  assert.equal(calls.length, count,
    "Further route edits are disabled after a replacement");

  await ui.saveBuiltRoute();
  assert.equal(
    calls.filter(call => call.url.includes("/save-replaced")).length, 0,
    "Unsigned user cannot save even a valid public replacement"
  );
  ui.state.signed = true;
  ui.state.savedCity = "suzdal";
  ui.state.guideLoaded = true;
  ui.state.guide = {
    city_slug: "suzdal", visited_slugs: [],
    stats: {}, saved_routes: [], completed_routes: []
  };
  await ui.saveBuiltRoute();
  assert.equal(ui.state.builder.saved, true);
  assert.equal(ui.state.guide.stats.saved_routes, 1);
  assert.match(nodes.get("screen").innerHTML, /Маршрут сохранён/);
  assert.equal(
    calls.filter(call => call.url.endsWith("/save-replaced")).length, 1
  );
  ui.updateBuilderOption("interest", "architecture");
  assert.equal(ui.state.builder.replacement, null);
  assert.equal(ui.state.builder.baseRouteId, null);
  console.log("Mini App replacement selection, rollback and save passed");
}
run().catch(error => { console.error(error); process.exitCode = 1; });
