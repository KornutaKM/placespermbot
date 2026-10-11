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
    innerHTML: "", value: "", textContent: "", handlers: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener(name, cb) { this.handlers[name] = cb; },
    setAttribute() {}, removeAttribute() {},
    querySelector() { return element(); }, querySelectorAll() { return []; },
    replaceChildren() { this.innerHTML = ""; }
  };
}
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  querySelectorAll() { return []; }, addEventListener() {}
};
const calls = [];
let shouldFail = false;
const cities = Array.from({ length: 100 }, (_, i) => ({
  rank: i + 1, name: "Город " + (i + 1),
  slug: "city-" + (i + 1), guide_available: false
}));
cities[0] = { rank: 1, name: "Москва", slug: "moscow", guide_available: true };
cities[1] = {
  rank: 2, name: "<img src=x onerror=alert(1)>",
  slug: "pending", guide_available: false
};
cities[99] = { rank: 100, name: "Абакан", slug: "abakan", guide_available: false };
const ctx = {
  window: { Telegram: { WebApp: { initData: "" } }, scrollTo() {} },
  document, setTimeout() { return 1; }, clearTimeout() {},
  fetch: async (url, options) => {
    calls.push({ url, options });
    if (shouldFail) return { ok: false };
    if (url !== "/api/city-coverage") throw Error("Unexpected URL " + url);
    return { ok: true, json: async () => ({
      target_count: 100, ready_count: 1, pending_count: 99,
      cities, ranking_date: "2025-01-01"
    }) };
  }
};
vm.runInNewContext(
  source + "\nthis.__ui = {state, renderHome, openTopCities};",
  ctx, { timeout: 1500 }
);
async function test() {
  const { state, renderHome, openTopCities } = ctx.__ui;
  state.cities = [{ slug: "moscow", name: "Москва" }];
  state.catalog = {
    slug: "moscow", name: "Москва", places: [], routes: [], category_labels: {}
  };
  renderHome();
  assert.match(document.getElementById("screen").innerHTML, /data-top100="true"/);
  assert.equal(calls.length, 0, "Directory must be lazy-loaded");
  await openTopCities();
  assert.equal(calls.length, 1);
  const markup = document.getElementById("top100-results").innerHTML;
  assert.match(markup, /data-city="moscow"/);
  assert.match(markup, /Каталог готовится/);
  assert.match(markup, /&lt;img/);
  assert.doesNotMatch(markup, /<img src/);
  assert.doesNotMatch(markup, /data-city="abakan"/);
  assert.match(document.getElementById("sheet-root").innerHTML, /1 путеводителей из 100/);
  const filter = document.getElementById("top100-filter");
  filter.value = "абакан";
  filter.handlers.input();
  const narrowed = document.getElementById("top100-results").innerHTML;
  assert.match(narrowed, /Абакан/);
  assert.doesNotMatch(narrowed, /data-city="abakan"/);
  assert.doesNotMatch(narrowed, /Москва/);
  assert.ok(calls.every(c => !c.options.method || c.options.method === "GET"));
  shouldFail = true;
  await openTopCities();
  assert.match(document.getElementById("toast").textContent, /Не удалось/);
  console.log("Top-100 public coverage UI regression passed");
}
test().catch(err => { console.error(err); process.exitCode = 1; });
