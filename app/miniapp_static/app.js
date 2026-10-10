"use strict";

const tg = window.Telegram?.WebApp ?? null;
const initData = tg?.initData || "";
const state = {
  cities: [], catalog: null, tab: "home", category: "all", search: "",
  signed: false, savedCity: null,
  favorites: new Set(), favoritesLoaded: false, favoritePending: new Set(),
  mapController: null, mapFilter: "all", mapSearch: "", mapSelected: null,
  guide: null, guideLoaded: false, guideSection: "favorites",
  visitPending: new Set(), routePending: new Set()
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
    (!state.signed
      ? '<div class="notice">Режим просмотра: откройте Mini App из Telegram, чтобы сохранять избранное и выбор города.</div>'
      : state.savedCity !== catalog.slug
        ? '<div class="notice">Выберите город, чтобы включить синхронизацию избранного.</div>'
        : !state.favoritesLoaded
          ? '<div class="notice">Избранное временно недоступно. Перезапустите Mini App.</div>'
          : "") +
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

function renderFavorites() {
  const catalog = state.catalog;
  const active = canEditFavorites();
  const saved = active ? catalog.places.filter(place =>
    state.favorites.has(place.slug)) : [];
  const notice = active ? "" : (
    !state.signed
      ? '<div class="notice">Избранное доступно после открытия гида в Telegram. В браузере можно просматривать места без сохранения.</div>'
      : state.savedCity !== catalog.slug
        ? '<div class="notice">Выберите текущий город через Telegram, чтобы увидеть избранное.</div>'
        : '<div class="notice">Не удалось загрузить избранное. Перезапустите Mini App и проверьте соединение.</div>'
  );
  screen.innerHTML = '<div class="page-heading"><div><h1>Избранное</h1>' +
    '<p>Твои сохранённые места · ' + escapeText(catalog.name) +
    '</p></div><span class="counter">' + saved.length + ' мест</span></div>' +
    notice +
    (active && saved.length === 0
      ? '<div class="empty"><strong>Здесь пока пусто</strong>' +
        'Сохрани понравившееся место, нажав ♡ на карточке.</div>' +
        '<button type="button" class="primary" data-open="places">Найти интересные места ↗</button>'
      : '<div class="places-list">' + saved.map(placeCard).join("") + '</div>');
}

async function loadFavorites(citySlug) {
  state.favorites = new Set();
  state.favoritesLoaded = false;
  if (!state.signed || state.savedCity !== citySlug) return;
  try {
    const result = await api("/api/me/favorites/" + encodeURIComponent(citySlug));
    if (result.city_slug !== citySlug || !Array.isArray(result.place_slugs)) {
      throw new Error("Invalid favorites payload");
    }
    state.favorites = new Set(result.place_slugs);
    state.favoritesLoaded = true;
  } catch (_) {
    notify("Не удалось загрузить избранное. Проверьте соединение.");
  }
}

async function toggleFavorite(placeSlug) {
  if (!canEditFavorites()) {
    notify("Откройте гид в Telegram и выберите город.");
    return;
  }
  const place = state.catalog.places.find(item => item.slug === placeSlug);
  if (!place || state.favoritePending.has(placeSlug)) return;
  const citySlug = state.catalog.slug;
  const wasFavorite = state.favorites.has(placeSlug);
  state.favoritePending.add(placeSlug);
  try {
    const result = await api(
      "/api/me/favorites/" + encodeURIComponent(citySlug) + "/" +
      encodeURIComponent(placeSlug),
      { method: wasFavorite ? "DELETE" : "PUT" }
    );
    if (result.city_slug !== citySlug || result.place_slug !== placeSlug ||
      result.is_favorite !== !wasFavorite) throw new Error("Invalid favorites response");
    if (state.catalog.slug !== citySlug) return;
    if (result.is_favorite) state.favorites.add(placeSlug);
    else state.favorites.delete(placeSlug);
    state.favoritePending.delete(placeSlug);
    if (state.guide) {
      state.guide.favorite_slugs = [...state.favorites];
      state.guide.stats.favorites = state.favorites.size;
    }
    if (state.tab === "home") renderHome();
    else if (state.tab === "guide") renderGuide();
    else if (state.tab === "places") drawPlaceResults();
    else if (state.tab === "map") drawMapPoints();
    else if (state.tab === "favorites") renderFavorites();
    if (sheetRoot.querySelector('button[data-favorite="' + placeSlug + '"]')) {
      openPlace(placeSlug);
    }
    notify(result.is_favorite ? "Добавлено в избранное" : "Удалено из избранного");
  } catch (_) {
    notify("Не удалось обновить избранное. Попробуйте ещё раз.");
  } finally {
    state.favoritePending.delete(placeSlug);
  }
}

function mapVisiblePlaces() {
  if (!state.catalog) return [];
  const term = state.mapSearch.trim().toLocaleLowerCase("ru");
  return state.catalog.places.filter(place => {
    if (!Number.isFinite(place.latitude) || !Number.isFinite(place.longitude) ||
      Math.abs(place.latitude) > 90 || Math.abs(place.longitude) > 180) return false;
    const category = state.mapFilter;
    if (category === "free" && !place.is_free) return false;
    if (category === "family" && !place.tags.includes("с детьми")) return false;
    if (!["all", "free", "family"].includes(category) &&
      place.category !== category) return false;
    if (!term) return true;
    return [place.title, place.district, place.summary, ...place.tags]
      .join(" ").toLocaleLowerCase("ru").includes(term);
  });
}

function selectMapPlace(slug) {
  if (state.tab !== "map") return;
  const place = mapVisiblePlaces().find(place => place.slug === slug);
  if (!place) return;
  state.mapSelected = slug;
  const preview = document.getElementById("map-preview");
  if (preview) preview.innerHTML = placeCard(place);
  state.mapController?.focus([place.latitude, place.longitude]);
}

function drawMapPoints() {
  if (state.tab !== "map") return;
  const places = mapVisiblePlaces();
  const count = document.getElementById("map-count");
  if (count) count.textContent = places.length + " мест на карте";
  const preview = document.getElementById("map-preview");
  if (state.mapSelected && !places.some(place => place.slug === state.mapSelected)) {
    state.mapSelected = null;
  }
  if (preview) {
    const selected = places.find(place => place.slug === state.mapSelected);
    preview.innerHTML = selected
      ? placeCard(selected)
      : '<div class="map-empty">' +
        (places.length ? "Выберите метку на карте или место в списке."
          : "Для этих фильтров достопримечательностей не найдено.") +
        "</div>";
  }
  const matches = document.getElementById("map-matches");
  if (matches) {
    matches.innerHTML = places.slice(0, 8).map(place =>
      '<button class="map-match" type="button" data-map-place="' +
      escapeText(place.slug) + '"><span>' + escapeText(place.emoji) +
      '</span><span>' + escapeText(place.title) + '</span><span>→</span></button>'
    ).join("");
  }
  const chips = document.querySelectorAll("[data-map-filter]");
  chips.forEach(button => {
    button.classList.toggle("active", button.dataset.mapFilter === state.mapFilter);
    button.setAttribute(
      "aria-pressed", String(button.dataset.mapFilter === state.mapFilter)
    );
  });
  if (state.mapController) state.mapController.update(places);
}

function renderMap() {
  const city = state.catalog;
  const categories = [
    ["all", "Все"], ["free", "✳ Бесплатно"], ["family", "♡ С детьми"],
    ...Object.entries(city.category_labels)
  ];
  screen.innerHTML =
    '<div class="page-heading"><div><h1>Карта города</h1><p>Исследуйте ' +
    escapeText(city.name) + ' поблизости</p></div></div>' +
    '<label class="search"><span>⌕</span><input id="map-search" type="search" ' +
    'autocomplete="off" placeholder="Найти место на карте…" ' +
    'aria-label="Поиск достопримечательностей на карте"></label>' +
    '<div class="chips map-chips" aria-label="Фильтры карты">' +
    categories.map(([key, text]) =>
      '<button class="chip" type="button" data-map-filter="' +
      escapeText(key) + '">' + escapeText(text) + '</button>'
    ).join("") + '</div>' +
    '<div class="map-frame"><div id="city-map" class="map-canvas" ' +
    'role="region" aria-label="Интерактивная карта достопримечательностей"></div>' +
    '<div id="map-fallback" class="map-fallback" hidden></div></div>' +
    '<p class="map-disclosure">Карта: © OpenStreetMap. Тайлы загружаются ' +
    'только при открытии раздела и передают картографическому сервису ' +
    'сетевой адрес браузера. Для построения реального пути используйте ' +
    'кнопку «На карте» в карточке места.</p>' +
    '<div class="section-title"><h2>Исследовать точки</h2>' +
    '<span class="counter" id="map-count"></span></div>' +
    '<div id="map-preview"></div>' +
    '<div id="map-matches" class="map-matches"></div>';

  const input = document.getElementById("map-search");
  input.value = state.mapSearch;
  input.addEventListener("input", event => {
    state.mapSearch = event.target.value;
    drawMapPoints();
  });

  try {
    state.mapController = window.PlacesMap?.mount(
      "city-map", placeSlug => selectMapPlace(placeSlug)
    ) || null;
  } catch (_) {
    state.mapController = null;
  }
  if (!state.mapController) {
    const fallback = document.getElementById("map-fallback");
    fallback.hidden = false;
    fallback.textContent = "Карта временно недоступна. Выберите место в списке ниже.";
    notify("Не удалось загрузить карту. Список мест доступен ниже.");
  }
  drawMapPoints();
}

function canUseGuide() {
  return state.signed && state.guideLoaded &&
    state.savedCity === state.catalog?.slug;
}

function visitedButton(place) {
  const marked = !!state.guide?.visited_slugs.includes(place.slug);
  const allowed = canUseGuide() && !state.visitPending.has(place.slug);
  return '<button type="button" class="visited-toggle ' +
    (marked ? "selected" : "") + '" data-visited="' +
    escapeText(place.slug) + '" aria-pressed="' + String(marked) +
    '" aria-label="' + escapeText(
      marked ? "Снять отметку о посещении: " + place.title :
        "Отметить как посещённое: " + place.title
    ) + '"' + (allowed ? "" : " disabled") + '>' +
    (marked ? "✓ Посещено" : "✓ Я здесь был") + "</button>";
}

async function loadGuide(citySlug) {
  state.guide = null;
  state.guideLoaded = false;
  if (!state.signed || state.savedCity !== citySlug) return;
  try {
    const snapshot = await api("/api/me/guide/" + encodeURIComponent(citySlug));
    if (snapshot.city_slug !== citySlug || !snapshot.stats ||
      !Array.isArray(snapshot.visited_slugs) ||
      !Array.isArray(snapshot.saved_routes) ||
      !Array.isArray(snapshot.completed_routes)) {
      throw new Error("Invalid My Guide response");
    }
    if (state.catalog?.slug !== citySlug || state.savedCity !== citySlug) return;
    state.guide = snapshot;
    state.guideLoaded = true;
  } catch (_) {
    notify("Не удалось загрузить «Мой гид». Проверьте подключение.");
  }
}

function guideRouteCard(route, finished = false) {
  const first = route.places[0];
  const label = finished ? "ПРОЙДЕННЫЙ МАРШРУТ" : "СОХРАНЁННЫЙ МАРШРУТ";
  const attr = finished ? "data-guide-history" : "data-guide-route";
  return '<article class="guide-route-card"><div class="guide-route-kicker">' +
    label + (route.completed ? ' · ✓ Пройден' : "") + '</div><h3>' +
    escapeText(route.interest_label) + '</h3><p>' +
    (first ? escapeText(first.emoji + " " + first.title) :
      "Места отсутствуют в актуальном каталоге") +
    (route.place_count > 1 ? ' и ещё ' + (route.place_count - 1) : "") + '</p>' +
    '<div class="guide-route-meta"><span>◷ ' + escapeText(route.budget_minutes) +
    ' мин</span><span>⌖ ' + escapeText(route.place_count) +
    ' точек</span>' +
    (route.unavailable_count
      ? '<span>Недоступно: ' + escapeText(route.unavailable_count) + '</span>'
      : "") + '</div>' +
    '<button class="guide-route-open" type="button" ' + attr + '="' +
    escapeText(route.route_id) + '">Подробнее →</button></article>';
}

function renderGuide() {
  const catalog = state.catalog;
  if (!canUseGuide()) {
    screen.innerHTML = '<div class="page-heading"><div><h1>Мой гид</h1>' +
      '<p>Личные открытия · ' + escapeText(catalog.name) +
      '</p></div></div>' +
      '<div class="guide-welcome"><span>✦</span><h2>Места, которые станут твоей историей</h2>' +
      '<p>' + (!state.signed
        ? "Откройте приложение через Telegram, чтобы видеть сохранённые маршруты и отмечать посещения."
        : state.savedCity !== catalog.slug
          ? "Выберите этот город в Telegram, чтобы открыть персональный гид."
          : "Не удалось загрузить профиль. Проверьте сеть и перезапустите Mini App.") +
      '</p><button class="primary" type="button" data-open="places">Исследовать места →</button></div>';
    return;
  }
  const guide = state.guide;
  const stats = guide.stats;
  const segments = [
    ["favorites", "♡ Избранное"], ["visited", "✓ Посещено"],
    ["saved", "〽 Маршруты"], ["history", "🏁 История"]
  ];
  let body = "";
  if (state.guideSection === "favorites") {
    const places = catalog.places.filter(place =>
      guide.favorite_slugs.includes(place.slug));
    body = places.length
      ? '<div class="places-list">' + places.map(placeCard).join("") + "</div>"
      : '<div class="empty"><strong>Пока без избранного</strong>' +
        'Нажмите ♡ на месте, которое хотите запомнить.</div>' +
        '<button type="button" class="primary" data-open="places">Найти места →</button>';
  } else if (state.guideSection === "visited") {
    const places = catalog.places.filter(place =>
      guide.visited_slugs.includes(place.slug));
    body = places.length
      ? '<div class="guide-visited-list">' + places.map(place =>
          '<div class="guide-visited-item">' + placeCard(place) +
          '<button class="guide-unvisit" type="button" data-visited="' +
          escapeText(place.slug) + '"' +
          (state.visitPending.has(place.slug) ? " disabled" : "") +
          '>Снять отметку о посещении</button></div>'
        ).join("") + "</div>"
      : '<div class="empty"><strong>История посещений пуста</strong>' +
        'Откройте карточку места и выберите «Я здесь был».</div>' +
        '<button type="button" class="primary" data-open="places">Исследовать места →</button>';
  } else if (state.guideSection === "saved") {
    body = guide.saved_routes.length
      ? '<div class="guide-routes-list">' +
        guide.saved_routes.map(route => guideRouteCard(route)).join("") + "</div>"
      : '<div class="empty"><strong>Нет сохранённых маршрутов</strong>' +
        'Маршруты, сохранённые в обычном Telegram-боте, появятся здесь.</div>' +
        '<button type="button" class="primary" data-open="routes">Готовые прогулки →</button>';
  } else {
    body = guide.completed_routes.length
      ? '<div class="guide-routes-list">' +
        guide.completed_routes.map(route => guideRouteCard(route, true)).join("") +
        "</div>"
      : '<div class="empty"><strong>Пока нет пройденных маршрутов</strong>' +
        'Отметьте сохранённый маршрут как пройденный, чтобы увидеть его в истории.</div>';
    if (stats.completed_routes > guide.completed_routes.length) {
      body += '<div class="notice">Некоторые старые прохождения сохранены без подробного снимка маршрута.</div>';
    }
  }
  screen.innerHTML = '<div class="page-heading"><div><h1>Мой гид</h1>' +
    '<p>Моя история · ' + escapeText(catalog.name) + '</p></div></div>' +
    '<div class="guide-hero"><span class="guide-hero-eyebrow">ЛИЧНЫЙ ДНЕВНИК</span>' +
    '<h2>Каждое место — новое открытие.</h2><p>Соберите свою историю города.</p></div>' +
    '<div class="guide-stats">' +
    [
      [stats.visited, "Посещено"], [stats.favorites, "Избранное"],
      [stats.saved_routes, "Сохранено"], [stats.completed_routes, "Пройдено"]
    ].map(([count, title]) =>
      '<div class="guide-stat"><strong>' + escapeText(count) +
      '</strong><span>' + escapeText(title) + '</span></div>'
    ).join("") + '</div>' +
    '<div class="guide-progress"><div><strong>Исследовано ' +
    escapeText(stats.visited) + ' из ' + escapeText(stats.catalog_places) +
    ' мест</strong><span>' + (stats.catalog_places
      ? Math.round(stats.visited / stats.catalog_places * 100)
      : 0) + '%</span></div><div class="guide-progress-track"><span style="width:' +
    Math.min(100, stats.catalog_places
      ? Math.round(stats.visited / stats.catalog_places * 100) : 0) + '%"></span></div></div>' +
    '<div class="guide-segments" aria-label="Разделы личного гида">' +
    segments.map(([value, label]) =>
      '<button type="button" data-guide-section="' + value +
      '" class="' + (state.guideSection === value ? "active" : "") +
      '" aria-pressed="' + String(state.guideSection === value) + '">' +
      label + '</button>'
    ).join("") + '</div>' +
    body;
}

async function toggleVisited(slug) {
  if (!canUseGuide()) {
    notify("Откройте гид в Telegram и выберите город.");
    return;
  }
  const city = state.catalog.slug;
  const place = state.catalog.places.find(place => place.slug === slug);
  if (!place || state.visitPending.has(slug)) return;
  const already = state.guide.visited_slugs.includes(slug);
  state.visitPending.add(slug);
  try {
    const result = await api(
      "/api/me/visited/" + encodeURIComponent(city) + "/" + encodeURIComponent(slug),
      { method: already ? "DELETE" : "PUT" }
    );
    if (result.city_slug !== city || result.place_slug !== slug ||
      result.is_visited !== !already) throw new Error("Invalid visit response");
    if (state.catalog.slug !== city || state.savedCity !== city) return;
    state.guide.visited_slugs = already
      ? state.guide.visited_slugs.filter(item => item !== slug)
      : [...state.guide.visited_slugs, slug];
    state.guide.stats.visited = state.guide.visited_slugs.length;
    state.visitPending.delete(slug);
    if (state.tab === "guide") renderGuide();
    const openVisited = sheetRoot.querySelector('button[data-visited="' + slug + '"]');
    if (openVisited) openPlace(slug);
    notify(already ? "Отметка посещения снята" : "Место отмечено как посещённое");
  } catch (_) {
    notify("Не удалось обновить посещение. Попробуйте ещё раз.");
  } finally {
    state.visitPending.delete(slug);
  }
}

function guideRouteSheet(route, { history = false, confirmDelete = false } = {}) {
  const routeId = escapeText(route.route_id);
  const places = route.places.map((place, index) =>
    '<li><b>' + (index + 1) + '</b><span>' +
    escapeText(place.emoji) + ' ' + escapeText(place.title) + '</span></li>'
  ).join("");
  const links = route.map_links.map((link, index) =>
    '<a class="map-link ' + (index ? "secondary" : "") +
    '" target="_blank" rel="noopener noreferrer" href="' +
    escapeText(link.url) + '">Карта · участок ' + (index + 1) + ' ↗</a>'
  ).join("");
  const actions = history ? "" : confirmDelete
    ? '<div class="guide-confirm"><strong>Удалить этот маршрут из сохранённых?</strong>' +
      '<p>История прохождения, если она есть, останется доступной.</p>' +
      '<button type="button" class="guide-danger" data-guide-delete-confirm="' +
      routeId + '">Да, удалить маршрут</button>' +
      '<button type="button" class="guide-cancel" data-guide-delete-cancel="' +
      routeId + '">Отмена</button></div>'
    : '<div class="guide-route-actions">' +
      (route.completed ? '<span class="guide-done">✓ Уже пройден</span>' :
        '<button type="button" data-guide-complete="' + routeId +
        '" ' + (state.routePending.has(route.route_id) ? "disabled" : "") +
        '>🏁 Отметить пройденным</button>') +
      '<button class="guide-delete-request" type="button" data-guide-delete-ask="' +
      routeId + '">Удалить из сохранённых</button></div>';

  openSheet('<div class="sheet-head"><div><div class="eyebrow">' +
    (history ? "🏁 ПРОЙДЕННЫЙ МАРШРУТ" : "〽 СОХРАНЁННЫЙ МАРШРУТ") +
    '</div><h2>' + escapeText(route.interest_label) +
    '</h2></div><button class="sheet-close" type="button" data-close ' +
    'aria-label="Закрыть">×</button></div>' +
    '<div class="detail-meta"><span>◷ ' + escapeText(route.budget_minutes) +
    ' мин</span><span>⌖ ' + escapeText(route.place_count) + ' точек</span></div>' +
    (route.unavailable_count ? '<div class="notice">Часть точек недоступна ' +
      'в текущем каталоге: ' + escapeText(route.unavailable_count) + '.</div>' : "") +
    (history ? '<p class="sheet-caption">Дата прохождения: ' +
      escapeText(route.completed_at) + '</p>' : "") +
    (places ? '<ol class="route-stops">' + places + '</ol>'
      : '<div class="empty">Сейчас ни одна точка маршрута не доступна.</div>') +
    '<p class="sheet-caption">Переходы и время в пути ориентировочны.</p>' +
    links + actions);
}

function openSavedGuideRoute(routeId, confirmDelete = false) {
  if (!canUseGuide()) return;
  const route = state.guide.saved_routes.find(item => item.route_id === routeId);
  if (route) guideRouteSheet(route, { confirmDelete });
}

function openCompletedGuideRoute(routeId) {
  if (!canUseGuide()) return;
  const route = state.guide.completed_routes.find(item => item.route_id === routeId);
  if (route) guideRouteSheet(route, { history: true });
}

async function completeGuideRoute(routeId) {
  if (!canUseGuide() || state.routePending.has(routeId)) return;
  const city = state.catalog.slug;
  if (!state.guide.saved_routes.some(route => route.route_id === routeId)) return;
  state.routePending.add(routeId);
  try {
    const result = await api(
      "/api/me/saved-routes/" + encodeURIComponent(city) + "/" +
      encodeURIComponent(routeId) + "/complete", { method: "PUT" }
    );
    if (result.city_slug !== city || result.route_id !== routeId ||
      typeof result.already_completed !== "boolean") {
      throw new Error("Invalid completion response");
    }
    if (state.catalog.slug !== city) return;
    await loadGuide(city);
    if (state.tab === "guide") renderGuide();
    closeSheet();
    notify(result.already_completed
      ? "Маршрут уже был пройден" : "Маршрут отмечен как пройденный");
  } catch (_) {
    notify("Не удалось отметить маршрут. Попробуйте ещё раз.");
  } finally {
    state.routePending.delete(routeId);
  }
}

async function deleteGuideRoute(routeId) {
  if (!canUseGuide() || state.routePending.has(routeId)) return;
  const city = state.catalog.slug;
  if (!state.guide.saved_routes.some(route => route.route_id === routeId)) return;
  state.routePending.add(routeId);
  try {
    const result = await api(
      "/api/me/saved-routes/" + encodeURIComponent(city) + "/" +
      encodeURIComponent(routeId), { method: "DELETE" }
    );
    if (result.city_slug !== city || result.route_id !== routeId ||
      result.deleted !== true) throw new Error("Invalid deletion response");
    if (state.catalog.slug !== city) return;
    await loadGuide(city);
    if (state.tab === "guide") renderGuide();
    closeSheet();
    notify("Маршрут удалён из сохранённых");
  } catch (_) {
    notify("Не удалось удалить маршрут. Попробуйте ещё раз.");
  } finally {
    state.routePending.delete(routeId);
  }
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
  if (state.mapController) {
    state.mapController.destroy();
    state.mapController = null;
  }
  if (tab === "home") renderHome();
  else if (tab === "places") renderPlaces();
  else if (tab === "map") renderMap();
  else if (tab === "guide") renderGuide();
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
    '<div class="detail-visited">' + visitedButton(place) +
    '<span>Отметить посещение в «Моём гиде»</span></div>' +
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
  state.mapSearch = "";
  state.mapFilter = "all";
  state.mapSelected = null;
  if (state.mapController) {
    state.mapController.destroy();
    state.mapController = null;
  }
  await loadFavorites(catalog.slug);
  await loadGuide(catalog.slug);
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
  if (trigger.dataset.visited) {
    void toggleVisited(trigger.dataset.visited);
    return;
  }
  if (trigger.dataset.guideSection) {
    state.guideSection = trigger.dataset.guideSection;
    renderGuide();
    return;
  }
  if (trigger.dataset.guideRoute) {
    openSavedGuideRoute(trigger.dataset.guideRoute);
    return;
  }
  if (trigger.dataset.guideHistory) {
    openCompletedGuideRoute(trigger.dataset.guideHistory);
    return;
  }
  if (trigger.dataset.mapPlace) {
    selectMapPlace(trigger.dataset.mapPlace);
    return;
  }
  if (trigger.dataset.mapFilter) {
    state.mapFilter = trigger.dataset.mapFilter;
    drawMapPoints();
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
  const visited = event.target.closest("button[data-visited]");
  if (visited) {
    void toggleVisited(visited.dataset.visited);
    return;
  }
  const complete = event.target.closest("button[data-guide-complete]");
  if (complete) {
    void completeGuideRoute(complete.dataset.guideComplete);
    return;
  }
  const requestDelete = event.target.closest("button[data-guide-delete-ask]");
  if (requestDelete) {
    openSavedGuideRoute(requestDelete.dataset.guideDeleteAsk, true);
    return;
  }
  const confirmDelete = event.target.closest("button[data-guide-delete-confirm]");
  if (confirmDelete) {
    void deleteGuideRoute(confirmDelete.dataset.guideDeleteConfirm);
    return;
  }
  const cancelDelete = event.target.closest("button[data-guide-delete-cancel]");
  if (cancelDelete) {
    openSavedGuideRoute(cancelDelete.dataset.guideDeleteCancel);
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
