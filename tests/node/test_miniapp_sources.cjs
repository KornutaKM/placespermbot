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
    innerHTML: "", textContent: "", dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
    querySelector() { return element(); }, querySelectorAll() { return []; },
    replaceChildren() {}
  };
}
const elements = new Map();
const doc = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  querySelectorAll() { return []; }, addEventListener() {}
};
const context = {
  window: { Telegram: { WebApp: { initData: "" } }, scrollTo() {} },
  document: doc, setTimeout() { return 1; }, clearTimeout() {},
  fetch() { throw Error("Provenance rendering must not call network"); }
};
vm.runInNewContext(
  source + "\nthis.__ui = {state, sourceDetails, openPlace};",
  context, { timeout: 1000 }
);

const { state, sourceDetails, openPlace } = context.__ui;
const sourceData = {
  name: "Музей <сайта>",
  url: "https://museum.example/objects?id=5&lang=ru",
  checked_at: "2026-10-11"
};
const valid = sourceDetails({ source: sourceData });
assert.match(valid, /Откуда сведения/);
assert.match(valid, /href="https:\/\/museum.example\/objects\?id=5&amp;lang=ru"/);
assert.match(valid, /rel="noopener noreferrer"/);
assert.match(valid, /Дата редакционной записи: 2026-10-11/);
assert.match(valid, /Музей &lt;сайта&gt;/);

const dangerous = sourceDetails({ source: {
  name: '<img src=x onerror="alert(1)">',
  url: "javascript:alert(1)",
  checked_at: "<script>alert(1)</script>"
} });
assert.doesNotMatch(dangerous, /href=/);
assert.doesNotMatch(dangerous, /<script>|<img src/);
assert.match(dangerous, /не указана/);
assert.match(sourceDetails({}), /Источник не указан/);

const wikidata = sourceDetails({ source: {
  name: "Wikidata contributors (CC0)",
  url: "https://www.wikidata.org/wiki/Q123456",
  checked_at: "2026-10-11"
} });
assert.match(wikidata, /Дата выгрузки Wikidata: 2026-10-11/);
assert.match(wikidata, /www\.wikidata\.org\/wiki\/Q123456/);
assert.match(wikidata, /Wikidata:Licensing/);
assert.match(wikidata, /не проверены на месте/);


const injected = sourceDetails({ source: {
  name: "Safe", url: 'https://museum.example/" onclick="alert(1)',
  checked_at: "2026-10-11"
} });
assert.doesNotMatch(injected, /href=/);

const place = {
  slug: "a", title: "Музей", emoji: "🏛",
  category_label: "Музей", summary: "Описание", district: "Центр",
  visit_minutes: 45, is_free: false, tags: [], source: sourceData,
  map_url: "https://maps.example/place"
};
state.catalog = {
  slug: "perm", name: "Пермь", places: [place], routes: [],
  category_labels: {}
};
openPlace("a");
const detail = doc.getElementById("sheet-root").innerHTML;
assert.match(detail, /Откуда сведения/);
assert.match(detail, /museum.example/);
assert.match(detail, /Уточните|уточните/);
place.evidence = {
  status: "official_tourism_listing",
  checked_on: "2026-10-11",
  evidence_url: "https://gotoomsk.ru/places/istoriko-kulturnyj-kompleks-omskaya-krepost/",
  finding: "Туринфоцентр перечисляет объект."
};
openPlace("a");
const tourismDetail = doc.getElementById("sheet-root").innerHTML;
assert.match(tourismDetail, /официального туристского инфоцентра/);
assert.match(tourismDetail, /Это не гарантия доступа/);
assert.doesNotMatch(tourismDetail, /сайте оператора/);

place.evidence.evidence_url = 'javascript:alert("unsafe")';
openPlace("a");
const blockedLinkDetail = doc.getElementById("sheet-root").innerHTML;
assert.doesNotMatch(blockedLinkDetail, /href="javascript:/);

console.log("Mini App provenance UI regression passed");
