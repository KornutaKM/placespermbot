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

const calls = [];
const route = {
  city_slug: "perm", route_id: "abcdef1234567890", interest: "classic",
  interest_label: "Главные места", budget_minutes: 240, estimated_minutes: 145,
  visit_minutes: 120, walking_minutes: 25, spare_minutes: 95,
  distance_km: 1.8,
  places: [
    { slug: "a", title: "Музей <img onerror=alert(1)>", emoji: "🏛",
      district: "Центр", visit_minutes: 60, latitude: 58, longitude: 56 },
    { slug: "b", title: "Парк", emoji: "🌿", district: "Центр",
      visit_minutes: 60, latitude: 58.01, longitude: 56.01 }
  ],
  map_links: [{
    url: "https://www.google.com/maps/dir/?api=1",
    mode: "walking"
  }]
};
let failSave = false;
const fetchMock = async (url, options = {}) => {
  const body = options.body ? JSON.parse(options.body) : null;
  calls.push({ url, method: options.method || "GET",
    headers: options.headers, body });
  if (url === "/api/routes/perm/preview") {
    if (body.budget_minutes === 360) {
      return { ok: true, json: async () => ({
        ...route, budget_minutes: 360, spare_minutes: 215
      }) };
    }
    return { ok: true, json: async () => route };
  }
  if (url === "/api/me/routes/perm/save") {
    if (failSave) return { ok: false, status: 409 };
    assert.equal(body.expected_route_id, route.route_id);
    assert.equal(body.interest, route.interest);
    assert.equal(body.budget_minutes, 240);
    return { ok: true, json: async () => ({
      saved: true, city_slug: "perm", route_id: route.route_id
    }) };
  }
  if (url === "/api/me/guide/perm") {
    return { ok: true, json: async () => ({
      city_slug: "perm",
      stats: { saved_routes: 1 },
      visited_slugs: [], saved_routes: [{ route_id: route.route_id }],
      completed_routes: []
    }) };
  }
  throw Error("Unexpected fetch " + url);
};
const context = {
  window: {
    Telegram: { WebApp: { initData: "signed-telegram-init-data" } },
    scrollTo() {}
  },
  document, fetch: fetchMock, setTimeout() { return 1; }, clearTimeout() {}
};
vm.runInNewContext(source + "\nthis.__ui = {" +
  "state, navigate, updateBuilderOption, builderBody, " +
  "renderBuilder, buildPreview, saveBuiltRoute, toggleBuilderMap, builderResultMarkup" +
  "};", context);
const ui = context.__ui;
ui.state.catalog = { slug: "perm", name: "Пермь", places: [],
  routes: [], category_labels: {} };
ui.state.cities = [{ slug: "perm", name: "Пермь" }];

async function test() {
  ui.navigate("builder");
  assert.match(nodes.get("screen").innerHTML, /Свой маршрут/);
  assert.match(nodes.get("screen").innerHTML, /data-builder-interest="free"/);
  assert.match(nodes.get("screen").innerHTML, /data-builder-budget="360"/);
  assert.match(nodes.get("screen").innerHTML, /Исключить уже посещённые/);

  ui.updateBuilderOption("exclude_visited", true);
  assert.equal(ui.state.builder.exclude_visited, false,
    "Unsigned users cannot enable visited-filter");
  ui.updateBuilderOption("budget_minutes", 360);
  assert.equal(ui.state.builder.budget_minutes, 360);
  await ui.buildPreview();
  assert.equal(ui.state.builder.result.budget_minutes, 360);
  assert.equal(ui.state.builder.result.spare_minutes, 215);
  assert.match(nodes.get("screen").innerHTML, /215/);
  assert.match(nodes.get("screen").innerHTML, /&lt;img onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(nodes.get("screen").innerHTML, /<img onerror/);
  assert.match(nodes.get("screen").innerHTML, /Построить маршрут/);
  assert.match(nodes.get("screen").innerHTML, /Сохранить в «Мой гид»/);
  assert.match(nodes.get("screen").innerHTML, /Показать остановки на карте/);
  let mounts = 0;
  let updates = 0;
  let destroys = 0;
  context.window.PlacesMap = {
    mount() {
      mounts++;
      return {
        update(places) { updates += places.length; },
        destroy() { destroys++; }
      };
    }
  };
  assert.equal(mounts, 0, "The map must be lazy");
  ui.toggleBuilderMap();
  assert.equal(mounts, 1);
  assert.equal(updates, 2);
  assert.match(nodes.get("screen").innerHTML, /id="builder-route-map"/);
  ui.toggleBuilderMap();
  assert.equal(destroys, 1);
  assert.equal(ui.state.builder.mapController, null);

  assert.match(nodes.get("screen").innerHTML,
    /class="builder-save"[^>]*disabled/,
    "Public browsing cannot save personal routes");

  const count = calls.length;
  await ui.saveBuiltRoute();
  assert.equal(calls.length, count);
  assert.equal(ui.state.builder.saved, false);
  ui.updateBuilderOption("budget_minutes", 240);
  assert.equal(ui.state.builder.result, null,
    "Changing options must clear stale preview");

  ui.state.signed = true;
  ui.state.savedCity = "perm";
  ui.state.guideLoaded = true;
  ui.state.guide = { city_slug: "perm", visited_slugs: [],
    stats: {}, saved_routes: [], completed_routes: [] };
  ui.updateBuilderOption("exclude_visited", true);
  assert.equal(ui.state.builder.exclude_visited, true);
  await ui.buildPreview();
  assert.equal(ui.state.builder.result.route_id, route.route_id);
  const previewCall = calls.filter(x => x.url.endsWith("/preview")).at(-1);
  assert.equal(previewCall.body.exclude_visited, true);
  assert.equal(previewCall.headers["X-Telegram-Init-Data"],
    "signed-telegram-init-data");

  failSave = true;
  await ui.saveBuiltRoute();
  assert.equal(ui.state.builder.result, null,
    "A stale server-issued route must be regenerated, not silently saved");
  assert.equal(ui.state.builder.saved, false);

  failSave = false;
  await ui.buildPreview();
  await ui.saveBuiltRoute();
  assert.equal(ui.state.builder.saved, true);
  assert.equal(ui.state.guide.stats.saved_routes, 1);
  assert.match(nodes.get("screen").innerHTML, /Маршрут сохранён/);
  const savedRequests = calls.filter(x => x.url.endsWith("/save"));
  assert.equal(savedRequests.at(-1).body.expected_route_id, route.route_id);
  const savedCount = savedRequests.length;
  await ui.saveBuiltRoute();
  assert.equal(calls.filter(x => x.url.endsWith("/save")).length, savedCount,
    "Saved preview cannot submit duplicate calls");

  // A new choice resets the save state and cannot reuse the old snapshot.
  ui.updateBuilderOption("interest", "museums");
  assert.equal(ui.state.builder.result, null);
  assert.equal(ui.state.builder.saved, false);

  console.log("Mini App route builder preview, security and save states passed");
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
