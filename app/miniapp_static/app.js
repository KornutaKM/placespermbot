"use strict";

const tg = window.Telegram?.WebApp ?? null;
const initData = tg?.initData || "";
const state = {
  cities: [], catalog: null, tab: "home", category: "all", search: "",
  signed: false, savedCity: null,
  favorites: new Set(), favoritesLoaded: false, favoritePending: new Set()
};
const screen = document.getElementById("screen");
const sheetRoot = document.getElementById("sheet-root");
const cityName = document.getElementById("city-name");
const toast = document.getElementById("toast");
let toastTimeout;

function escapeText(value) {
  return String(value ?? "").replace(/[&<>"']/g, symbol => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;"
  }[symbol]));
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3600);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (initData) headers["X-Telegram-Init-Data"] = initData;
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    ...options, headers, credentials: "same-origin", cache: "no-store"
  });
  if (!response.ok) throw new Error("HTTP " + response.status);
  return response.json();
}

function placeVisual(place) {
  const color = place.is_free ? "green" : (
    place.category.includes("museum") ? "purple" : "amber"
  );
  return '<div class="place-visual ' + color + '"><span>' +
    escapeText(place.emoji) + "</span></div>";
}

function canEditFavorites() {
  return state.signed && state.favoritesLoaded &&
    state.savedCity === state.catalog?.slug;
}

function favoriteButton(place) {
  const active = state.favorites.has(place.slug);
  const editable = canEditFavorites() && !state.favoritePending.has(place.slug);
  return '<button type="button" class="favorite-toggle ' +
    (active ? "selected" : "") + '" data-favorite="' +
    escapeText(place.slug) + '" aria-pressed="' + String(active) +
    '" aria-label="' + (active ? "Удалить из избранного: " : "В избранное: ") +
    escapeText(place.title) + '"' + (editable ? "" : " disabled") +
    ' title="' + (editable ? "Избранное в Telegram" : "Нужна авторизация Telegram") +
    '">' + (active ? "♥" : "♡") + "</button>";
}

function placeCard(place) {
  return '<article class="place-card">' + placeVisual(place) +
    '<div class="place-info"><span class="kicker">' +
    escapeText(place.category_label) + '</span><h3>' +
    escapeText(place.title) + '</h3><p>' +
    escapeText(place.summary) + '</p><div class="place-footer"><span>' +
    escapeText(place.district) + ' · ~' +
    escapeText(place.visit_minutes) +
    ' мин</span><div class="place-actions">' + favoriteButton(place) +
    '<button class="place-more" type="button" data-place="' +
    escapeText(place.slug) + '">Подробнее ↗</button></div></div></article>';
}

function renderHome() {
  const catalog = state.catalog;
  const topPlaces = catalog.places.slice(0, 3);
  screen.innerHTML = '<section class="hero"><div class="hero-content">' +
    '<div class="eyebrow">Твой город · твои открытия</div>' +
    '<h1>Город, который хочется открывать.</h1>' +
    '<p>Находи атмосферные места, выбирай готовые прогулки и смотри город по-новому.</p>' +
    '<div class="hero-mark"><span>⌖ ' + escapeText(catalog.name) + '</span> ' +
    escapeText(catalog.places.length) + ' мест для открытий</div></div></section>' +
    (state.signed ? "" : '<div class="notice">Режим просмотра: откройте Mini App из Telegram, чтобы сохранять избранное и выбор города.</div>') +
    '<div class="section-title"><div><h2>С чего начнём?</h2>' +
    '<p class="tiny">Все впечатления в одном месте</p></div></div>' +
    '<div class="quick-grid">' +
    '<button class="quick-card" type="button" data-open="places"><span class="symbol">⌖</span><strong>Куда сходить ↗</strong><small>Места, которые стоит увидеть</small></button>' +
    '<button class="quick-card green" type="button" data-open="routes"><span class="symbol">〽</span><strong>Маршруты ↗</strong><small>Прогулки с готовыми точками</small></button>' +
    '<button class="quick-card peach" type="button" data-category="free"><span class="symbol">✳</span><strong>Бесплатно ↗</strong><small>Город без лишних расходов</small></button>' +
    '<button class="quick-card purple" type="button" data-category="family"><span class="symbol">♡</span><strong>С детьми ↗</strong><small>Места для всей семьи</small></button>' +
    '</div><div class="stats"><div class="stat"><strong>' +
    catalog.places.length + '</strong><span>мест</span></div><div class="stat"><strong>' +
    catalog.routes.length + '</strong><span>маршрутов</span></div><div class="stat"><strong>' +
    state.cities.length + '</strong><span>городов</span></div></div>' +
    '<div class="section-title"><div><h2>Открой сейчас</h2><p class="tiny">Начни знакомство с городом</p></div>' +
    '<button type="button" data-open="places">Все места →</button></div>' +
    '<div class="places-list">' + topPlaces.map(placeCard).join("") + '</div>';
}

function drawPlaceResults() {
  const query = state.search.trim().toLocaleLowerCase("ru");
  const visible = state.catalog.places.filter(place => {
    if (state.category === "free" && !place.is_free) return false;
    if (state.category === "family" && !place.tags.includes("с детьми")) return false;
    if (!["all", "free", "family"].includes(state.category)
      && place.category !== state.category) return false;
    if (!query) return true;
    return [place.title, place.district, place.summary, ...place.tags]
      .join(" ").toLocaleLowerCase("ru").includes(query);
  });
  document.getElementById("count").textContent = visible.length + " мест";
  document.getElementById("results").innerHTML = visible.length
    ? visible.map(placeCard).join("")
    : '<div class="empty"><strong>Ничего не нашлось</strong>Попробуйте другой запрос или категорию.</div>';
}

function renderPlaces() {
  const city = state.catalog;
  const options = [
    ["all", "Все места"], ["free", "✳ Бесплатно"], ["family", "♡ С детьми"],
    ...Object.entries(city.category_labels)
  ];
  screen.innerHTML =
    '<div class="page-heading"><div><h1>Куда сходить</h1><p>Выбирай места по интересам</p></div>' +
    '<span class="counter" id="count"></span></div>' +
    '<label class="search"><span>⌕</span><input id="search" type="search" ' +
    'autocomplete="off" placeholder="Название, район, атмосфера…" aria-label="Поиск мест"></label>' +
    '<div class="chips" aria-label="Категории">' + options.map(([key, name]) =>
      '<button class="chip ' + (state.category === key ? "active" : "") +
      '" data-filter="' + escapeText(key) + '" type="button">' +
      escapeText(name) + '</button>'
    ).join("") + '</div><div class="places-list" id="results"></div>';
  const searchField = document.getElementById("search");
  searchField.value = state.search;
  searchField.addEventListener("input", event => {
    state.search = event.target.value;
    drawPlaceResults();
  });
  drawPlaceResults();
}

function routeCard(route, number) {
  return '<article class="route-card"><div class="route-number">МАРШРУТ / ' +
    String(number).padStart(2, "0") + '</div><h3>' +
    escapeText(route.title) + '</h3><p>' +
    escapeText(route.summary) + '</p><div class="route-meta"><span>◷ ' +
    escapeText(route.duration_minutes) + ' мин</span><span>⌁ ' +
    escapeText(route.distance_km) + ' км</span><span>⌖ ' +
    route.place_slugs.length + ' точек</span></div>' +
    '<button data-route="' + escapeText(route.slug) +
    '" type="button">Посмотреть маршрут ↗</button></article>';
}

function renderRoutes() {
  const city = state.catalog;
  screen.innerHTML = '<div class="page-heading"><div><h1>Маршруты</h1>' +
    '<p>Готовые прогулки по ' + escapeText(city.name) +
    '</p></div><span class="counter">' +
    city.routes.length + ' маршрутов</span></div>' +
    '<div class="notice">Длительность и расстояние ориентировочные. Перед прогулкой проверьте транспорт и доступность мест.</div>' +
    '<div class="routes-list">' +
    city.routes.map((route, index) => routeCard(route, index + 1)).join("") +
    '</div>';
}

function updateNav() {
  document.querySelectorAll(".nav-tab").forEach(button => {
    const active = button.dataset.tab === state.tab;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
}

function navigate(tab) {
  state.tab = tab;
  updateNav();
  if (!state.catalog) return;
  if (tab === "home") renderHome();
  else if (tab === "places") renderPlaces();
  else if (tab === "favorites") renderFavorites();
  else renderRoutes();
  window.scrollTo({ top: 0, behavior: "instant" });
}

function openSheet(content) {
  sheetRoot.innerHTML = '<div class="overlay"><section class="sheet" role="dialog" ' +
    'aria-modal="true" aria-label="Подробности"><div class="sheet-handle"></div>' +
    content + '</section></div>';
  const overlay = sheetRoot.querySelector(".overlay");
  overlay.addEventListener("click", event => {
    if (event.target === overlay) closeSheet();
  });
  sheetRoot.querySelectorAll("[data-close]").forEach(btn =>
    btn.addEventListener("click", closeSheet)
  );
}

function closeSheet() {
  sheetRoot.replaceChildren();
}

function openPlace(slug) {
  const place = state.catalog.places.find(item => item.slug === slug);
  if (!place) return;
  openSheet('<div class="sheet-head"><div><div class="detail-symbol">' +
    escapeText(place.emoji) + '</div><h2>' + escapeText(place.title) +
    '</h2><p>' + escapeText(place.category_label) + '</p></div>' +
    '<button class="sheet-close" type="button" data-close aria-label="Закрыть">×</button></div>' +
    '<p class="detail-summary">' + escapeText(place.summary) + '</p>' +
    '<div class="detail-meta"><span>⌖ ' + escapeText(place.district) +
    '</span><span>◷ ~' + escapeText(place.visit_minutes) + ' мин</span>' +
    (place.is_free ? '<span>✳ Бесплатно</span>' : "") + '</div>' +
    '<div class="detail-favorite">' + favoriteButton(place) +
    '<span>Сохранить место в избранном</span></div>' +
    '<p class="sheet-caption">Перед посещением уточните часы работы и условия доступа.</p>' +
    '<a class="map-link" target="_blank" rel="noopener noreferrer" href="' +
    escapeText(place.map_url) + '">Открыть на карте ↗</a>');
}

function openRoute(slug) {
  const route = state.catalog.routes.find(item => item.slug === slug);
  if (!route) return;
  const stops = route.place_slugs.map(slug =>
    state.catalog.places.find(item => item.slug === slug)
  ).filter(Boolean);
  const list = stops.map((place, index) =>
    '<li><b>' + (index + 1) + '</b><span>' +
    escapeText(place.emoji) + ' ' + escapeText(place.title) +
    '</span></li>'
  ).join("");
  const mapLinks = route.map_links.map((link, index) =>
    '<a class="map-link ' + (index ? "secondary" : "") +
    '" target="_blank" rel="noopener noreferrer" href="' +
    escapeText(link.url) + '">Открыть ' +
    (link.mode === "transit" ? "транспортный переход" : "участок маршрута") +
    (route.map_links.length > 1 ? " " + (index + 1) : "") +
    ' ↗</a>'
  ).join("");
  openSheet('<div class="sheet-head"><div><div class="eyebrow">ГОТОВАЯ ПРОГУЛКА</div>' +
    '<h2>' + escapeText(route.title) + '</h2></div>' +
    '<button class="sheet-close" type="button" data-close aria-label="Закрыть">×</button></div>' +
    '<p class="detail-summary">' + escapeText(route.summary) + '</p>' +
    '<div class="detail-meta"><span>◷ ' +
    route.duration_minutes + ' мин</span><span>⌁ ' +
    route.distance_km + ' км</span><span>⌖ ' +
    stops.length + ' точек</span></div>' +
    '<ol class="route-stops">' + list + '</ol>' +
    '<p class="sheet-caption">Переходы по дорогам могут отличаться от расчёта. Длинные участки показываются отдельно для проверки транспорта.</p>' +
    mapLinks);
}

function openCities() {
  const choices = state.cities.map(city =>
    '<button type="button" class="city-choice ' +
    (state.catalog?.slug === city.slug ? "active" : "") +
    '" data-city="' + escapeText(city.slug) + '">' +
    escapeText(city.name) + '</button>'
  ).join("");
  openSheet('<div class="sheet-head"><div><h2>Выберите город</h2>' +
    '<p>Открывайте места и маршруты в любом из 35 городов</p></div>' +
    '<button class="sheet-close" type="button" data-close aria-label="Закрыть">×</button></div>' +
    (!initData ? '<div class="notice">Без Telegram выбор действует только в этом просмотре.</div>' : "") +
    '<div class="city-list">' + choices + '</div>');
}

async function loadCity(slug) {
  const catalog = await api("/api/catalogs/" + encodeURIComponent(slug));
  state.catalog = catalog;
  state.category = "all";
  state.search = "";
  await loadFavorites(catalog.slug);
  cityName.textContent = catalog.name;
  navigate(state.tab);
}

async function chooseCity(slug) {
  try {
    if (initData) {
      await api("/api/me/city", {
        method: "POST",
        body: JSON.stringify({ city_slug: slug })
      });
      state.savedCity = slug;
      state.signed = true;
    }
    await loadCity(slug);
    closeSheet();
    notify(initData ? "Город сохранён" : "Город выбран для просмотра");
  } catch (_) {
    notify("Не удалось сохранить город. Перезапустите Mini App из Telegram.");
  }
}

screen.addEventListener("click", event => {
  const trigger = event.target.closest("button");
  if (!trigger) return;
  if (trigger.dataset.favorite) {
    void toggleFavorite(trigger.dataset.favorite);
    return;
  }
  if (trigger.dataset.open) navigate(trigger.dataset.open);
  if (trigger.dataset.category) {
    state.category = trigger.dataset.category;
    navigate("places");
  }
  if (trigger.dataset.filter) {
    state.category = trigger.dataset.filter;
    renderPlaces();
  }
  if (trigger.dataset.place) openPlace(trigger.dataset.place);
  if (trigger.dataset.route) openRoute(trigger.dataset.route);
});

sheetRoot.addEventListener("click", event => {
  const favorite = event.target.closest("button[data-favorite]");
  if (favorite) {
    void toggleFavorite(favorite.dataset.favorite);
    return;
  }
  const button = event.target.closest("button[data-city]");
  if (button) void chooseCity(button.dataset.city);
});
document.getElementById("city-trigger").addEventListener("click", openCities);
document.querySelectorAll("[data-tab]").forEach(button =>
  button.addEventListener("click", () => navigate(button.dataset.tab))
);
document.addEventListener("keydown", event => {
  if (event.key === "Escape") closeSheet();
});

async function main() {
  try {
    tg?.ready();
    tg?.expand();
    const citiesResult = await api("/api/cities");
    state.cities = citiesResult.cities;
    if (!state.cities.length) throw new Error("No cities");
    let selected = null;
    if (initData) {
      try {
        const profile = await api("/api/me");
        selected = profile.city_slug;
        state.signed = true;
        state.savedCity = selected;
      } catch (_) {
        notify("Сессия Telegram устарела. Перезапустите Mini App.");
      }
    }
    const initial = selected || (
      state.cities.some(city => city.slug === "saint-petersburg")
        ? "saint-petersburg" : state.cities[0].slug
    );
    await loadCity(initial);
    if (state.signed && !selected) openCities();
  } catch (_) {
    screen.innerHTML = '<div class="empty"><strong>Не удалось открыть гид</strong>' +
      'Проверьте подключение и попробуйте открыть Mini App заново.</div>';
  }
}
void main();
