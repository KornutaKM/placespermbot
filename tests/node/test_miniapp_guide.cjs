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
    handlers: {},
    addEventListener(name, fn) { this.handlers[name] = fn; },
    setAttribute() {}, removeAttribute() {},
    replaceChildren() { this.innerHTML = ""; },
    querySelector(selector) { return selector === ".overlay" ? element() : null; },
    querySelectorAll() { return []; }
  };
}
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  addEventListener() {},
  querySelectorAll() { return []; }
};
const calls = [];
const route = {
  route_id: "abcdef1234567890", interest_label: "Классика",
  budget_minutes: 240, place_count: 2, unavailable_count: 0,
  completed: false, created_at: "2026-10-10",
  places: [
    { slug: "p1", title: "Музей", emoji: "🏛" },
    { slug: "p2", title: "<img onerror=alert(1)>", emoji: "★" }
  ],
  map_links: [{
    url: "https://www.google.com/maps/dir/?api=1",
    mode: "walking"
  }]
};
const backend = {
  saved: [route], completed: [], visited: [],
  favorites: ["p1"], completedCount: 0
};
const makeSnapshot = () => ({
  city_slug: "perm",
  stats: {
    visited: backend.visited.length, favorites: backend.favorites.length,
    saved_routes: backend.saved.length,
    completed_routes: backend.completedCount, catalog_places: 100
  },
  favorite_slugs: [...backend.favorites],
  visited_slugs: [...backend.visited],
  saved_routes: backend.saved.map(item => ({ ...item })),
  completed_routes: backend.completed.map(item => ({ ...item }))
});
async function fetchMock(url, options = {}) {
  calls.push({ url, method: options.method || "GET", headers: options.headers || {} });
  const method = options.method || "GET";
  let data;
  if (url === "/api/me/guide/perm" && method === "GET") {
    data = makeSnapshot();
  } else if (url === "/api/me/visited/perm/p1" && method === "PUT") {
    backend.visited.push("p1");
    data = { city_slug: "perm", place_slug: "p1", is_visited: true };
  } else if (url === "/api/me/visited/perm/p1" && method === "DELETE") {
    backend.visited = [];
    data = { city_slug: "perm", place_slug: "p1", is_visited: false };
  } else if (
    url === "/api/me/saved-routes/perm/abcdef1234567890/complete" && method === "PUT"
  ) {
    backend.saved[0].completed = true;
    backend.completed = [{
      ...backend.saved[0], completed_at: "2026-10-11", completed: true
    }];
    backend.completedCount = 1;
    backend.visited = ["p1", "p2"];
    data = {
      city_slug: "perm", route_id: "abcdef1234567890",
      added: 2, already_visited: 0, unavailable: 0, already_completed: false
    };
  } else if (
    url === "/api/me/saved-routes/perm/abcdef1234567890" && method === "DELETE"
  ) {
    backend.saved = [];
    data = { city_slug: "perm", route_id: "abcdef1234567890", deleted: true };
  } else throw Error("Unexpected request: " + method + " " + url);
  return { ok: true, json: async () => data };
}
const context = {
  window: {
    Telegram: { WebApp: { initData: "signed-test-init-data" } },
    scrollTo() {}
  },
  document, fetch: fetchMock,
  setTimeout() { return 1; }, clearTimeout() {}
};
vm.runInNewContext(
  source + "\nthis.__guide = {state, navigate, loadGuide, toggleVisited, " +
  "renderGuide, openSavedGuideRoute, openCompletedGuideRoute, " +
  "completeGuideRoute, deleteGuideRoute, visitedButton};",
  context
);
const ui = context.__guide;
const place = {
  slug: "p1", title: "Музей", emoji: "🏛", category: "museum",
  category_label: "Музей", district: "Центр", summary: "Описание",
  visit_minutes: 60, is_free: false, tags: []
};
const placeTwo = { ...place, slug: "p2", title: "Второе место" };
ui.state.catalog = {
  slug: "perm", name: "Пермь", places: [place, placeTwo],
  routes: [], category_labels: {}
};
ui.state.signed = true;
ui.state.savedCity = "perm";
ui.state.favorites = new Set(["p1"]);
ui.state.favoritesLoaded = true;
ui.state.guideSection = "saved";

async function test() {
  await ui.loadGuide("perm");
  assert.equal(ui.state.guideLoaded, true);
  ui.navigate("guide");
  assert.match(document.getElementById("screen").innerHTML, /Мой гид/);
  assert.match(document.getElementById("screen").innerHTML, /МАРШРУТ/);
  assert.match(document.getElementById("screen").innerHTML, /Классика/);

  ui.openSavedGuideRoute("abcdef1234567890");
  assert.match(document.getElementById("sheet-root").innerHTML, /Отметить пройденным/);
  assert.match(document.getElementById("sheet-root").innerHTML,
    /&lt;img onerror=alert\(1\)&gt;/);
  ui.openSavedGuideRoute("abcdef1234567890", true);
  assert.match(document.getElementById("sheet-root").innerHTML,
    /Да, удалить маршрут/);
  assert.match(document.getElementById("sheet-root").innerHTML, /Отмена/);
  assert.equal(backend.saved.length, 1,
    "Opening the deletion confirmation must not delete anything");

  ui.state.guideSection = "visited";
  ui.renderGuide();
  assert.match(document.getElementById("screen").innerHTML,
    /История посещений пуста/);
  await ui.toggleVisited("p1");
  assert.deepEqual(backend.visited, ["p1"]);
  assert.match(document.getElementById("screen").innerHTML, /Снять отметку/);
  assert.match(ui.visitedButton(place), /aria-pressed="true"/);
  await ui.toggleVisited("p1");
  assert.deepEqual(backend.visited, []);

  ui.state.guideSection = "saved";
  await ui.completeGuideRoute("abcdef1234567890");
  assert.equal(ui.state.guide.stats.completed_routes, 1);
  assert.equal(ui.state.guide.stats.visited, 2);
  assert.match(document.getElementById("screen").innerHTML, /Пройден/);

  ui.state.guideSection = "history";
  ui.renderGuide();
  assert.match(document.getElementById("screen").innerHTML, /ПРОЙДЕННЫЙ МАРШРУТ/);
  ui.openCompletedGuideRoute("abcdef1234567890");
  assert.match(document.getElementById("sheet-root").innerHTML, /2026-10-11/);
  assert.doesNotMatch(document.getElementById("sheet-root").innerHTML,
    /data-guide-delete-confirm/);

  await ui.deleteGuideRoute("abcdef1234567890");
  assert.equal(ui.state.guide.saved_routes.length, 0);
  assert.equal(ui.state.guide.completed_routes.length, 1,
    "Deleting saved route must not remove completed history");

  const priorCalls = calls.length;
  ui.state.signed = false;
  ui.renderGuide();
  assert.match(document.getElementById("screen").innerHTML, /через Telegram/);
  assert.match(ui.visitedButton(place), /disabled/);
  await ui.toggleVisited("p1");
  await ui.completeGuideRoute("abcdef1234567890");
  assert.equal(calls.length, priorCalls,
    "Unsigned preview cannot write user data");
  assert.ok(calls.every(item =>
    item.headers["X-Telegram-Init-Data"] === "signed-test-init-data"
  ));
  console.log("My Guide dashboard, visits, route completion and history passed");
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
