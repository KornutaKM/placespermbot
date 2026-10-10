"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../app/miniapp_static/app.js"), "utf8"
).replace(/void main\(\);\s*$/, "");

function mockElement() {
  return {
    innerHTML: "", textContent: "", value: "", dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    setAttribute() {}, removeAttribute() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    replaceChildren() {}
  };
}

const elements = new Map();
function getElementById(id) {
  if (!elements.has(id)) elements.set(id, mockElement());
  return elements.get(id);
}
const calls = [];
let favorites = new Set(["a"]);
const fetchMock = async (url, options) => {
  calls.push({ url, options });
  const json = () => {
    if (url === "/api/me/favorites/perm" && options.method === undefined) {
      return { city_slug: "perm", place_slugs: [...favorites] };
    }
    if (url === "/api/me/favorites/perm/a" && options.method === "PUT") {
      favorites.add("a");
      return { city_slug: "perm", place_slug: "a", is_favorite: true };
    }
    if (url === "/api/me/favorites/perm/a" && options.method === "DELETE") {
      favorites.delete("a");
      return { city_slug: "perm", place_slug: "a", is_favorite: false };
    }
    throw new Error("Unexpected request " + url);
  };
  return { ok: true, json: async () => json() };
};
const documentMock = {
  getElementById, addEventListener() {},
  querySelectorAll() { return []; }
};
const context = {
  document: documentMock,
  window: {
    Telegram: { WebApp: { initData: "signed-test-init-data" } },
    scrollTo() {}
  },
  fetch: fetchMock,
  setTimeout() { return 1; },
  clearTimeout() {}
};
vm.runInNewContext(
  source + "\nthis.__ui = { state, loadFavorites, toggleFavorite, " +
    "renderFavorites, favoriteButton, renderHome, renderPlaces };",
  context,
  { timeout: 1000 }
);

async function test() {
  const { state, loadFavorites, toggleFavorite, favoriteButton, renderFavorites } =
    context.__ui;
  const place = {
    slug: "a", title: "Место", category: "museum",
    category_label: "Музей", summary: "Описание", district: "Центр",
    emoji: "🏛", visit_minutes: 40, is_free: false, tags: []
  };
  state.catalog = {
    slug: "perm", name: "Пермь", places: [place], routes: [],
    category_labels: { museum: "Музей" }
  };
  state.signed = true;
  state.savedCity = "perm";
  state.tab = "places";

  await loadFavorites("perm");
  assert.equal(state.favoritesLoaded, true);
  assert.equal(state.favorites.has("a"), true);
  assert.match(favoriteButton(place), /aria-pressed="true"/);

  await toggleFavorite("a");
  assert.equal(state.favorites.has("a"), false);
  assert.equal(state.favoritePending.size, 0);
  assert.match(getElementById("results").innerHTML, /data-favorite="a"/);
  assert.doesNotMatch(
    getElementById("results").innerHTML, /data-favorite="a"[^>]*disabled/
  );

  state.tab = "favorites";
  await toggleFavorite("a");
  assert.equal(state.favorites.has("a"), true);
  assert.match(getElementById("screen").innerHTML, /Место/);
  assert.match(favoriteButton(place), /aria-pressed="true"/);

  const count = calls.length;
  state.signed = false;
  await toggleFavorite("a");
  assert.equal(calls.length, count);
  assert.match(favoriteButton(place), /disabled/);
  renderFavorites();
  assert.match(getElementById("screen").innerHTML, /Режим просмотра|после открытия/);
  assert.ok(calls.every(call =>
    call.options.headers["X-Telegram-Init-Data"] === "signed-test-init-data"
  ));
  console.log("Mini App favorite UI transitions passed");
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
