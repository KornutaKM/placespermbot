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
const point = (slug, title, visit = 40) => ({
  slug, title, emoji: "🏛", district: "Центр",
  latitude: 58.01, longitude: 56.2, visit_minutes: visit
});
const baseline = {
  city_slug: "perm", route_id: "0123456789abcdef",
  interest: "classic", interest_label: "Главные места",
  budget_minutes: 240, estimated_minutes: 150,
  visit_minutes: 120, walking_minutes: 30, spare_minutes: 90,
  distance_km: 2.5,
  places: [
    point("a", "Музей & театр"), point("b", "Парк"),
    point("c", "<img src=x onerror=alert(1)>")
  ],
  map_links: [{ url: "https://www.google.com/maps/dir/?api=1", mode: "walking" }]
};
const replies = {
  "a,b,c": baseline,
  "a,b": {
    ...baseline, route_id: "abcdef0123456789",
    estimated_minutes: 90, visit_minutes: 80, walking_minutes: 10,
    spare_minutes: 150, distance_km: 0.7, places: baseline.places.slice(0, 2)
  },
  "b,a": {
    ...baseline, route_id: "fedcba9876543210",
    estimated_minutes: 94, visit_minutes: 80, walking_minutes: 14,
    spare_minutes: 146, distance_km: 0.9,
    places: [baseline.places[1], baseline.places[0]]
  }
};
const calls = [];
let failReorder = false;
async function fetchMock(url, options = {}) {
  const method = options.method || "GET";
  const body = options.body ? JSON.parse(options.body) : null;
  calls.push({ url, method, body, headers: options.headers || {} });
  if (url === "/api/routes/perm/preview") {
    return { ok: true, json: async () => baseline };
  }
  if (url === "/api/routes/perm/edit") {
    assert.equal(body.base_route_id, baseline.route_id);
    assert.equal(body.interest, "classic");
    assert.equal(body.budget_minutes, 240);
    assert.equal(body.exclude_visited, false);
    assert.deepEqual(Object.keys(body).sort(),
      ["base_route_id", "budget_minutes", "exclude_visited", "interest",
       "place_slugs"].sort());
    const signature = body.place_slugs.join(",");
    if (failReorder || !replies[signature]) {
      return { ok: false, status: 422 };
    }
    return { ok: true, json: async () => replies[signature] };
  }
  if (url === "/api/me/routes/perm/save-edited") {
    assert.equal(body.base_route_id, baseline.route_id);
    assert.equal(body.expected_route_id, replies["b,a"].route_id);
    assert.deepEqual(Array.from(body.place_slugs), ["b", "a"]);
    assert.ok(!Object.hasOwn(body, "user_id"));
    return { ok: true, json: async () => ({
      city_slug: "perm", route_id: body.expected_route_id, saved: true
    }) };
  }
  if (url === "/api/me/guide/perm") {
    return { ok: true, json: async () => ({
      city_slug: "perm", stats: { saved_routes: 1 },
      visited_slugs: [], saved_routes: [],
      completed_routes: []
    }) };
  }
  throw Error("Unexpected request: " + method + " " + url);
}
const context = {
  window: {
    Telegram: { WebApp: { initData: "signed-telegram-token" } },
    scrollTo() {}
  },
  document, fetch: fetchMock,
  setTimeout() { return 1; }, clearTimeout() {}
};
vm.runInNewContext(
  source + "\nthis.__ui={state,navigate,buildPreview,editBuilderStop," +
  "saveBuiltRoute,updateBuilderOption};",
  context
);
const ui = context.__ui;
ui.state.catalog = {
  slug: "perm", name: "Пермь", places: [], routes: [], category_labels: {}
};
ui.state.cities = [{ slug: "perm", name: "Пермь" }];

async function run() {
  ui.navigate("builder");
  await ui.buildPreview();
  assert.equal(ui.state.builder.baseRouteId, baseline.route_id);
  assert.equal(ui.state.builder.edited, false);
  assert.match(nodes.get("screen").innerHTML, /Настроить остановки/);
  assert.match(nodes.get("screen").innerHTML, /data-builder-remove="2"/);
  assert.match(nodes.get("screen").innerHTML, /data-builder-move-up="1"/);
  assert.match(nodes.get("screen").innerHTML, /&lt;img src=x onerror/);
  assert.doesNotMatch(nodes.get("screen").innerHTML, /<img src=x onerror/);

  // Unsigned browser preview remains editable; saving is still disallowed.
  await ui.editBuilderStop("remove", 2);
  assert.equal(ui.state.builder.result.route_id, replies["a,b"].route_id);
  assert.equal(ui.state.builder.baseRouteId, baseline.route_id);
  assert.equal(ui.state.builder.edited, true);
  assert.equal(ui.state.builder.result.spare_minutes, 150);
  assert.match(nodes.get("screen").innerHTML, /отдельный вариант/);
  await ui.saveBuiltRoute();
  assert.equal(calls.filter(x => x.url.endsWith("/save-edited")).length, 0);

  failReorder = true;
  await ui.editBuilderStop("up", 1);
  assert.equal(ui.state.builder.result.route_id, replies["a,b"].route_id,
    "Rejected edit must keep the previously validated route");
  assert.equal(ui.state.builder.edited, true);
  failReorder = false;

  await ui.editBuilderStop("up", 1);
  assert.equal(ui.state.builder.result.route_id, replies["b,a"].route_id);
  assert.equal(ui.state.builder.baseRouteId, baseline.route_id);
  assert.deepEqual(
    Array.from(ui.state.builder.result.places, place => place.slug), ["b", "a"]
  );
  assert.equal(ui.state.builder.result.walking_minutes, 14);
  assert.equal(ui.state.builder.result.estimated_minutes, 94);

  ui.state.signed = true;
  ui.state.savedCity = "perm";
  ui.state.guideLoaded = true;
  ui.state.guide = {
    city_slug: "perm", stats: {}, visited_slugs: [],
    saved_routes: [], completed_routes: []
  };
  await ui.saveBuiltRoute();
  assert.equal(ui.state.builder.saved, true);
  assert.equal(ui.state.guide.stats.saved_routes, 1);
  assert.match(nodes.get("screen").innerHTML, /Маршрут сохранён/);
  assert.equal(calls.filter(x => x.url.endsWith("/save-edited")).length, 1);
  const count = calls.length;
  await ui.editBuilderStop("down", 0);
  await ui.saveBuiltRoute();
  assert.equal(calls.length, count, "Saved route actions must be inert");

  ui.updateBuilderOption("interest", "museums");
  assert.equal(ui.state.builder.result, null);
  assert.equal(ui.state.builder.baseRouteId, null);
  assert.equal(ui.state.builder.edited, false);
  assert.equal(ui.state.builder.saved, false);
  console.log("Mini App route editing, reject, reorder and signed save passed");
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
