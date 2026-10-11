"use strict";

const tg = window.Telegram?.WebApp ?? null;
const initData = tg?.initData || "";
const state = {
  cities: [], catalog: null, tab: "home", category: "all", search: "",
  signed: false, savedCity: null,
  favorites: new Set(), favoritesLoaded: false, favoritePending: new Set(),
  mapController: null, mapFilter: "all", mapSearch: "", mapSelected: null,
  guide: null, guideLoaded: false, guideSection: "favorites",
  visitPending: new Set(), routePending: new Set(),
  discovery: { query: "", category: "all", places: [], total: 0,
    hasMore: false, loading: false, error: false, version: 0, timer: null },
  builder: { budget_minutes: 240, interest: "classic", exclude_visited: false,
    result: null, busy: false, saving: false, saved: false, version: 0,
    showMap: false, mapController: null, baseRouteId: null, edited: false,
    replacement: null, alternatives: null }
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
    '<button class="quick-card green" type="button" data-open="builder"><span class="symbol">〽</span><strong>Свой маршрут ↗</strong><small>Время, интересы и остановки</small></button>' +
    '<button class="quick-card peach" type="button" data-category="free"><span class="symbol">✳</span><strong>Бесплатно ↗</strong><small>Город без лишних расходов</small></button>' +
    '<button class="quick-card purple" type="button" data-open="guide"><span class="symbol">♡</span><strong>Мой гид ↗</strong><small>Избранное, прогулки и история</small></button>' +
    '</div><button type="button" class="discovery-entry" data-open="discover">' +
    '<strong>Поиск по всей России ↗</strong><span>Достопримечательности всех ' +
    state.cities.length + ' городов в одном поиске</span></button>' +
    '<div class="stats"><div class="stat"><strong>' +
    catalog.places.length + '</strong><span>мест</span></div><div class="stat"><strong>' +
    catalog.routes.length + '</strong><span>маршрутов</span></div><div class="stat"><strong>' +
    state.cities.length + '</strong><span>городов</span></div></div>' +
    '<div class="section-title"><div><h2>Открой сейчас</h2><p class="tiny">Начни знакомство с городом</p></div>' +
    '<button type="button" data-open="places">Все места →</button></div>' +
    '<div class="places-list">' + topPlaces.map(placeCard).join("") + '</div>';
}


function drawDiscoveryResults() {
  if (state.tab !== "discover") return;
  const d = state.discovery;
  const counter = document.getElementById("discovery-count");
  const results = document.getElementById("discovery-results");
  if (!counter || !results) return;
  counter.textContent = d.loading ? "Поиск…" : d.total + " мест";
  if (d.query.trim().length < 2) {
    results.innerHTML = '<div class="empty"><strong>Откройте всю Россию</strong>' +
      'Введите минимум два символа названия, района, тега или города.</div>';
    return;
  }
  if (d.error) {
    results.innerHTML = '<div class="empty"><strong>Ошибка поиска</strong>' +
      'Проверьте соединение и попробуйте ещё раз.</div>' +
      '<button type="button" class="primary" data-discover-retry="true">Повторить поиск</button>';
    return;
  }
  const cards = d.places.map(place =>
    '<article class="discovery-result">' +
    '<span class="discovery-city">' + escapeText(place.city_name) + '</span>' +
    '<div class="discovery-place"><span class="discovery-icon">' +
    escapeText(place.emoji) + '</span><div><strong>' +
    escapeText(place.title) + '</strong><small>' +
    escapeText(place.category_label) + ' · ' + escapeText(place.district) +
    ' · ~' + escapeText(place.visit_minutes) + ' мин</small></div></div>' +
    '<p>' + escapeText(place.summary) + '</p>' +
    '<button type="button" data-discover-city="' + escapeText(place.city_slug) +
    '" data-discover-place="' + escapeText(place.place_slug) +
    '">Открыть место →</button></article>'
  ).join("");
  results.innerHTML = '<div class="discovery-list">' + cards + '</div>' +
    (d.loading ? '<div class="loading">Ищем по каталогам…</div>' : "") +
    (!d.loading && d.places.length === 0
      ? '<div class="empty"><strong>Совпадений нет</strong>Попробуйте другой запрос или категорию.</div>'
      : "") +
    (!d.loading && d.hasMore
      ? '<button class="primary" type="button" data-discover-more="true">Показать ещё</button>'
      : "");
}

async function requestDiscovery(more = false) {
  const d = state.discovery;
  const query = d.query.trim();
  if (d.loading || query.length < 2) return;
  const offset = more ? d.places.length : 0;
  const version = ++d.version;
  d.loading = true;
  d.error = false;
  if (!more) {
    d.places = [];
    d.total = 0;
    d.hasMore = false;
  }
  drawDiscoveryResults();
  try {
    const result = await api("/api/discover?q=" + encodeURIComponent(query) +
      "&category=" + encodeURIComponent(d.category) +
      "&offset=" + offset + "&limit=12");
    if (d.version !== version) return;
    if (!Array.isArray(result.places) || result.query !== query ||
      result.category !== d.category || result.offset !== offset ||
      !Number.isInteger(result.total) || typeof result.has_more !== "boolean") {
      throw new Error("Invalid discovery response");
    }
    d.places = more ? d.places.concat(result.places) : result.places;
    d.total = result.total;
    d.hasMore = result.has_more;
  } catch (_) {
    if (d.version === version) d.error = true;
  } finally {
    if (d.version === version) {
      d.loading = false;
      drawDiscoveryResults();
    }
  }
}

function renderDiscover() {
  const d = state.discovery;
  const categories = [
    ["all", "Все"], ["sights", "Достопримечательности"],
    ["museums", "Музеи"], ["parks", "Парки"],
    ["unusual", "Необычное"], ["free", "Бесплатно"],
    ["family", "С детьми"]
  ];
  screen.innerHTML =
    '<div class="page-heading"><div><h1>По всей России</h1>' +
    '<p>Поиск по ' + state.cities.length +
    ' городам без смены текущего города</p></div>' +
    '<span class="counter" id="discovery-count">0 мест</span></div>' +
    '<label class="search"><span>⌕</span><input id="discovery-query" type="search" ' +
    'autocomplete="off" aria-label="Поиск по всем городам" ' +
    'placeholder="Например, кремль, музей, Казань…"></label>' +
    '<div class="chips" aria-label="Категория поиска">' +
    categories.map(([key, name]) => '<button class="chip ' +
      (d.category === key ? "active" : "") + '" type="button" ' +
      'data-discover-category="' + key + '">' + name + '</button>').join("") +
    '</div><div id="discovery-results"></div>' +
    '<p class="sheet-caption">Сведения из городских каталогов. Перед визитом проверяйте часы и доступность.</p>';
  const input = document.getElementById("discovery-query");
  input.value = d.query;
  input.addEventListener("input", event => {
    d.query = event.target.value;
    ++d.version;
    d.loading = false;
    d.error = false;
    d.places = [];
    d.total = 0;
    d.hasMore = false;
    clearTimeout(d.timer);
    drawDiscoveryResults();
    if (d.query.trim().length >= 2) {
      d.timer = setTimeout(() => void requestDiscovery(), 250);
    }
  });
  drawDiscoveryResults();
}

async function openDiscoveryPlace(citySlug, placeSlug) {
  if (!state.cities.some(city => city.slug === citySlug)) return;
  if (state.catalog?.slug !== citySlug ||
      (initData && state.savedCity !== citySlug)) {
    const success = await chooseCity(citySlug);
    if (!success) return;
  }
  if (state.catalog?.slug !== citySlug) return;
  navigate("places");
  openPlace(placeSlug);
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

const BUILDER_INTERESTS = [
  ["classic", "🏛 Главные места"], ["museums", "🖼 Музеи"],
  ["architecture", "🏛 Архитектура"], ["walks", "🌿 Прогулки"],
  ["unusual", "✨ Необычные места"], ["family", "👨‍👩‍👧 С детьми"],
  ["free", "💸 Бесплатно"]
];

function builderBody() {
  const b = state.builder;
  return {
    budget_minutes: b.budget_minutes,
    interest: b.interest,
    exclude_visited: b.exclude_visited
  };
}

function updateBuilderOption(key, value) {
  if (state.tab !== "builder" || state.builder.busy || state.builder.saving) return;
  if (key === "exclude_visited" && !canUseGuide() && value) {
    notify("Чтобы исключить посещённые места, откройте приложение через Telegram.");
    return;
  }
  state.builder[key] = value;
  state.builder.version++;
  state.builder.result = null;
  state.builder.saved = false;
  state.builder.baseRouteId = null;
  state.builder.edited = false;
  state.builder.replacement = null;
  state.builder.alternatives = null;
  state.builder.showMap = false;
  renderBuilder();
}

function builderResultMarkup(route, saved) {
  if (!route) return "";
  const controlsEnabled = !state.builder.busy && !state.builder.saving &&
    !state.builder.saved && !state.builder.replacement;
  const stops = route.places.map((place, index) =>
    '<li><b>' + (index + 1) + '</b><span><strong>' +
    escapeText(place.emoji) + ' ' + escapeText(place.title) +
    '</strong><small>' + escapeText(place.district) + ' · осмотр ~' +
    escapeText(place.visit_minutes) + ' мин</small></span>' +
    '<div class="builder-stop-actions">' +
    '<button type="button" data-builder-move-up="' + index +
    '" aria-label="Переместить выше: ' + escapeText(place.title) + '"' +
    (!controlsEnabled || index === 0 ? " disabled" : "") + '>↑</button>' +
    '<button type="button" data-builder-move-down="' + index +
    '" aria-label="Переместить ниже: ' + escapeText(place.title) + '"' +
    (!controlsEnabled || index === route.places.length - 1 ? " disabled" : "") +
    '>↓</button>' +
    '<button type="button" class="builder-stop-remove" data-builder-remove="' +
    index + '" aria-label="Удалить остановку: ' + escapeText(place.title) + '"' +
    (!controlsEnabled || route.places.length < 2 ? " disabled" : "") +
    '>×</button>' +
    '<button type="button" class="builder-stop-replace" ' +
    'data-builder-alternatives="' + index +
    '" aria-label="Подобрать замену: ' + escapeText(place.title) + '"' +
    (!controlsEnabled ? " disabled" : "") +
    '>⇄</button></div></li>'
  ).join("");
  const links = route.map_links.map((link, index) =>
    '<a class="builder-map-link" target="_blank" rel="noopener noreferrer" href="' +
    escapeText(link.url) + '">Карта · ' +
    (link.mode === "transit" ? "транспортный переход" : "пеший участок") +
    (route.map_links.length > 1 ? " " + (index + 1) : "") + ' ↗</a>'
  ).join("");
  const canSave = state.signed && state.savedCity === state.catalog.slug;
  return '<section class="builder-result"><div class="builder-result-head">' +
    '<span>ГОТОВАЯ ПРОГУЛКА</span><h2>' +
    escapeText(route.interest_label) + '</h2><p>' +
    escapeText(route.places.length) + ' остановок · ~' +
    escapeText(route.distance_km) + ' км по прямой между точками</p></div>' +
    '<div class="builder-time-grid">' + [
      [route.estimated_minutes, "Всего, мин"],
      [route.visit_minutes, "Осмотр"],
      [route.walking_minutes, "Переходы"],
      [route.spare_minutes, "Резерв"]
    ].map(([minutes, label]) =>
      '<div><strong>' + escapeText(minutes) + '</strong><span>' +
      escapeText(label) + '</span></div>'
    ).join("") + '</div>' +
    '<div class="builder-edit-head"><strong>✎ Настроить остановки</strong>' +
    '<span>↑ ↓ порядок · × убрать</span></div>' +
    (state.builder.edited
      ? '<p class="builder-edited-note">Маршрут изменён и пересчитан. ' +
        'Можно сохранить как отдельный вариант.</p>' : "") +
    (state.builder.replacement
      ? '<div class="builder-replacement-notice">✓ Остановка заменена. ' +
        'Чтобы заменить ещё одну, сохраните вариант и постройте новый маршрут.</div>'
      : "") +
    '<ol class="builder-stops">' + stops + '</ol>' +
    (state.builder.alternatives
      ? '<section class="builder-alternatives"><h3>Подходящие замены</h3>' +
        '<p>Проверены время и пешие переходы до соседних остановок.</p>' +
        (state.builder.alternatives.items.length
          ? state.builder.alternatives.items.map(place =>
              '<button type="button" data-builder-choose="' +
              escapeText(place.slug) + '">' + escapeText(place.emoji) + ' ' +
              '<strong>' + escapeText(place.title) + '</strong>' +
              '<small>~' + escapeText(place.estimated_minutes) +
              ' мин весь маршрут · ' + escapeText(place.district) + '</small></button>'
            ).join("")
          : '<div class="empty">Нет безопасных замен при этих настройках.</div>') +
        '</section>' : "") +
    '<button class="builder-map-toggle" type="button" ' +
    'data-builder-map-toggle="yes">' +
    (state.builder.showMap ? "Скрыть карту" : "⌖ Показать остановки на карте") +
    '</button>' +
    (state.builder.showMap
      ? '<div class="builder-map" id="builder-route-map" ' +
        'role="region" aria-label="Карта остановок маршрута"></div>' +
        '<p class="builder-disclaimer">Карта показывает точки, но не ' +
        'строит путь по дорогам. Тайлы загружаются только по запросу.</p>'
      : "") +
    '<div class="builder-links">' + links + '</div>' +
    '<p class="builder-disclaimer">Время ходьбы рассчитано из скорости 4,5 км/ч ' +
    'и расстояний по прямой, а не по дорожной сети. Перед выходом проверьте путь ' +
    'и доступность мест.</p>' +
    (saved
      ? '<div class="builder-saved">✓ Маршрут сохранён в «Мой гид».</div>' +
        '<button class="builder-go-guide" type="button" data-builder-guide="yes">' +
        'Перейти к сохранённым маршрутам →</button>'
      : '<button class="builder-save" type="button" data-builder-save="yes" ' +
        (!canSave || state.builder.saving ? "disabled" : "") + '>' +
        (state.builder.saving ? "Сохраняем…" : "♡ Сохранить в «Мой гид»") +
        '</button>' +
        (!canSave
          ? '<p class="builder-disclaimer">Для сохранения откройте Mini App ' +
            'через Telegram и выберите свой город.</p>'
          : "")) + '</section>';
}

function renderBuilder() {
  const b = state.builder;
  if (b.mapController) {
    b.mapController.destroy();
    b.mapController = null;
  }
  screen.innerHTML = '<div class="page-heading"><div><h1>Свой маршрут</h1>' +
    '<p>Построй прогулку по ' + escapeText(state.catalog.name) +
    '</p></div></div>' +
    '<section class="builder-panel"><div class="builder-kicker">ШАГ 1 / ВРЕМЯ</div>' +
    '<h2>Сколько есть времени?</h2><div class="builder-budget-options">' +
    [120, 240, 360].map(minutes =>
      '<button type="button" data-builder-budget="' + minutes + '" ' +
      'aria-pressed="' + String(b.budget_minutes === minutes) +
      '" class="' + (b.budget_minutes === minutes ? "active" : "") + '"' +
      (b.busy || b.saving ? " disabled" : "") + '>' +
      (minutes / 60) + ' часа</button>'
    ).join("") + '</div><div class="builder-kicker">ШАГ 2 / ИНТЕРЕСЫ</div>' +
    '<h2>Что посмотреть?</h2><div class="builder-interests">' +
    BUILDER_INTERESTS.map(([value, label]) =>
      '<button type="button" data-builder-interest="' + value +
      '" aria-pressed="' + String(b.interest === value) +
      '" class="' + (b.interest === value ? "active" : "") + '"' +
      (b.busy || b.saving ? " disabled" : "") + '>' + label + "</button>"
    ).join("") + '</div>' +
    '<div class="builder-kicker">ШАГ 3 / НАСТРОЙКА</div>' +
    '<button class="builder-visited ' + (b.exclude_visited ? "active" : "") +
    '" type="button" data-builder-visited="' + String(!b.exclude_visited) +
    '" aria-pressed="' + String(b.exclude_visited) + '"' +
    (!canUseGuide() || b.busy || b.saving ? " disabled" : "") +
    '>✓ Исключить уже посещённые места ' +
    (b.exclude_visited ? "· Включено" : "· Выключено") + '</button>' +
    (!canUseGuide() ? '<p class="builder-hint">Этот фильтр работает ' +
      'только с вашими отметками посещения в Telegram.</p>' : "") +
    '<button class="builder-generate" type="button" data-builder-preview="yes" ' +
    (b.busy || b.saving ? "disabled" : "") + '>' +
    (b.busy ? "Строим маршрут…" : "✨ Построить маршрут") + '</button></section>' +
    builderResultMarkup(b.result, b.saved);
  if (b.showMap && b.result) {
    try {
      b.mapController = window.PlacesMap?.mount(
        "builder-route-map", slug => openPlace(slug)
      ) || null;
      if (b.mapController) b.mapController.update(b.result.places);
    } catch (_) {
      b.mapController = null;
    }
    if (!b.mapController) {
      const holder = document.getElementById("builder-route-map");
      if (holder) {
        holder.textContent = "Карта недоступна. Список остановок и ссылки ниже работают.";
      }
    }
  }
}

function toggleBuilderMap() {
  if (state.tab !== "builder" || !state.builder.result) return;
  state.builder.showMap = !state.builder.showMap;
  renderBuilder();
}

async function buildPreview() {
  if (state.tab !== "builder" || state.builder.busy || state.builder.saving) return;
  const city = state.catalog.slug;
  const b = state.builder;
  if (b.exclude_visited && !canUseGuide()) {
    notify("Этот фильтр доступен только в Telegram.");
    return;
  }
  b.busy = true;
  b.saved = false;
  b.result = null;
  b.baseRouteId = null;
  b.edited = false;
  b.replacement = null;
  b.alternatives = null;
  b.showMap = false;
  const version = ++b.version;
  renderBuilder();
  try {
    const preview = await api(
      "/api/routes/" + encodeURIComponent(city) + "/preview",
      { method: "POST", body: JSON.stringify(builderBody()) }
    );
    if (state.catalog.slug !== city || b.version !== version) return;
    if (preview.city_slug !== city || !preview.route_id ||
      !Array.isArray(preview.places) || !Array.isArray(preview.map_links)) {
      throw new Error("Invalid route preview");
    }
    b.result = preview;
    b.baseRouteId = preview.route_id;
    b.edited = false;
  } catch (_) {
    if (state.catalog.slug === city && b.version === version) {
      notify("Не удалось построить маршрут. Выберите другой интерес или время.");
    }
  } finally {
    if (b.version === version) {
      b.busy = false;
      if (state.tab === "builder" && state.catalog.slug === city) renderBuilder();
    }
  }
}

async function editBuilderStop(kind, rawIndex) {
  const b = state.builder;
  if (state.tab !== "builder" || !b.result ||
    b.busy || b.saving || b.saved || b.replacement || !b.baseRouteId) return;
  const index = Number(rawIndex);
  const stops = b.result.places.map(place => place.slug);
  if (!Number.isInteger(index) || index < 0 || index >= stops.length) return;
  if (kind === "remove") {
    if (stops.length < 2) return;
    stops.splice(index, 1);
  } else if (kind === "up") {
    if (index === 0) return;
    [stops[index - 1], stops[index]] = [stops[index], stops[index - 1]];
  } else if (kind === "down") {
    if (index === stops.length - 1) return;
    [stops[index + 1], stops[index]] = [stops[index], stops[index + 1]];
  } else {
    return;
  }
  const city = state.catalog.slug;
  b.busy = true;
  const version = ++b.version;
  renderBuilder();
  try {
    const preview = await api(
      "/api/routes/" + encodeURIComponent(city) + "/edit",
      {
        method: "POST",
        body: JSON.stringify({
          ...builderBody(), base_route_id: b.baseRouteId,
          place_slugs: stops
        })
      }
    );
    if (state.catalog.slug !== city || state.builder !== b ||
      b.version !== version) return;
    if (preview.city_slug !== city || !preview.route_id ||
      !Array.isArray(preview.places) || !Array.isArray(preview.map_links) ||
      preview.places.map(place => place.slug).join("|") !== stops.join("|")) {
      throw new Error("Invalid edited preview");
    }
    b.result = preview;
    b.edited = true;
    b.saved = false;
    b.alternatives = null;
    b.showMap = false;
    notify("Маршрут пересчитан");
  } catch (_) {
    if (state.catalog.slug === city && state.builder === b &&
      b.version === version) {
      notify("Изменение недоступно: проверьте время или расстояние перехода (до 5 км).");
    }
  } finally {
    if (state.builder === b && b.version === version) {
      b.busy = false;
      if (state.tab === "builder" && state.catalog.slug === city) renderBuilder();
    }
  }
}

async function showBuilderAlternatives(rawIndex) {
  const b = state.builder;
  if (state.tab !== "builder" || !b.result || !b.baseRouteId ||
    b.busy || b.saving || b.saved || b.replacement) return;
  const index = Number(rawIndex);
  if (!Number.isInteger(index) || index < 0 || index >= b.result.places.length) return;
  const city = state.catalog.slug;
  const slugs = b.result.places.map(place => place.slug);
  b.busy = true;
  b.alternatives = null;
  const version = ++b.version;
  renderBuilder();
  try {
    const reply = await api(
      "/api/routes/" + encodeURIComponent(city) + "/alternatives", {
        method: "POST",
        body: JSON.stringify({
          ...builderBody(), base_route_id: b.baseRouteId,
          place_slugs: slugs, stop_index: index
        })
      }
    );
    if (state.builder !== b || b.version !== version ||
      state.catalog.slug !== city) return;
    if (reply.city_slug !== city || reply.base_route_id !== b.baseRouteId ||
      reply.stop_index !== index || !Array.isArray(reply.alternatives)) {
      throw new Error("Invalid alternative suggestions");
    }
    b.alternatives = { index, original_slugs: slugs, items: reply.alternatives };
  } catch (_) {
    if (state.builder === b && b.version === version &&
      state.catalog.slug === city) {
      notify("Не удалось подобрать замены. Попробуйте другой маршрут.");
    }
  } finally {
    if (state.builder === b && b.version === version) {
      b.busy = false;
      if (state.tab === "builder" && state.catalog.slug === city) renderBuilder();
    }
  }
}

async function replaceBuilderStop(candidateSlug) {
  const b = state.builder;
  if (state.tab !== "builder" || !b.result || !b.alternatives ||
    b.busy || b.saving || b.saved || b.replacement) return;
  const choice = b.alternatives.items.find(place => place.slug === candidateSlug);
  if (!choice) return;
  const selection = b.alternatives;
  const city = state.catalog.slug;
  b.busy = true;
  const version = ++b.version;
  renderBuilder();
  try {
    const preview = await api(
      "/api/routes/" + encodeURIComponent(city) + "/replace", {
        method: "POST",
        body: JSON.stringify({
          ...builderBody(), base_route_id: b.baseRouteId,
          place_slugs: selection.original_slugs,
          stop_index: selection.index,
          candidate_slug: candidateSlug
        })
      }
    );
    if (state.builder !== b || b.version !== version ||
      state.catalog.slug !== city) return;
    const expected = [...selection.original_slugs];
    expected[selection.index] = candidateSlug;
    if (preview.city_slug !== city || !preview.route_id ||
      !Array.isArray(preview.places) || !Array.isArray(preview.map_links) ||
      preview.places.map(place => place.slug).join("|") !== expected.join("|")) {
      throw new Error("Invalid replacement preview");
    }
    b.result = preview;
    b.replacement = {
      original_slugs: selection.original_slugs,
      stop_index: selection.index,
      candidate_slug: candidateSlug
    };
    b.edited = true;
    b.alternatives = null;
    b.showMap = false;
    notify("Остановка заменена, маршрут пересчитан");
  } catch (_) {
    if (state.builder === b && b.version === version &&
      state.catalog.slug === city) {
      notify("Замена недоступна: проверьте бюджет и длину переходов.");
    }
  } finally {
    if (state.builder === b && b.version === version) {
      b.busy = false;
      if (state.tab === "builder" && state.catalog.slug === city) renderBuilder();
    }
  }
}

async function saveBuiltRoute() {
  if (!state.builder.result || state.builder.saving ||
    state.builder.busy || state.builder.saved) return;
  if (!state.signed || state.savedCity !== state.catalog.slug) {
    notify("Для сохранения откройте Mini App из Telegram.");
    return;
  }
  const city = state.catalog.slug;
  const b = state.builder;
  const version = b.version;
  const expectedId = b.result.route_id;
  b.saving = true;
  renderBuilder();
  try {
    const endpoint = b.replacement ? "/save-replaced" :
      (b.edited ? "/save-edited" : "/save");
    const payload = {
      ...builderBody(), expected_route_id: expectedId
    };
    if (b.replacement) {
      payload.base_route_id = b.baseRouteId;
      payload.place_slugs = b.replacement.original_slugs;
      payload.stop_index = b.replacement.stop_index;
      payload.candidate_slug = b.replacement.candidate_slug;
    } else if (b.edited) {
      payload.base_route_id = b.baseRouteId;
      payload.place_slugs = b.result.places.map(place => place.slug);
    }
    const reply = await api(
      "/api/me/routes/" + encodeURIComponent(city) + endpoint,
      { method: "POST", body: JSON.stringify(payload) }
    );
    if (state.catalog.slug !== city || b.version !== version) return;
    if (!reply.saved || reply.city_slug !== city || reply.route_id !== expectedId) {
      throw new Error("Invalid saved-route response");
    }
    b.saved = true;
    await loadGuide(city);
    notify("Маршрут сохранён в «Мой гид»");
  } catch (_) {
    if (state.catalog.slug === city && b.version === version) {
      b.result = null;
      b.baseRouteId = null;
      b.edited = false;
      b.replacement = null;
      b.alternatives = null;
      notify("Маршрут изменился или сохранение недоступно. Постройте его заново.");
    }
  } finally {
    if (b.version === version) {
      b.saving = false;
      if (state.tab === "builder" && state.catalog.slug === city) renderBuilder();
    }
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
    '<div class="builder-entry"><div><strong>Соберите свою прогулку</strong>' +
    '<p>Выберите 2, 4 или 6 часов и то, что интересно именно вам.</p></div>' +
    '<button type="button" data-open="builder">Собрать маршрут →</button></div>' +
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
  if (state.builder.mapController) {
    state.builder.mapController.destroy();
    state.builder.mapController = null;
  }
  if (tab === "home") renderHome();
  else if (tab === "places") renderPlaces();
  else if (tab === "map") renderMap();
  else if (tab === "guide") renderGuide();
  else if (tab === "builder") renderBuilder();
  else if (tab === "favorites") renderFavorites();
  else if (tab === "discover") renderDiscover();
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
  openSheet('<div class="sheet-head"><div><h2>Выберите город</h2>' +
    '<p>Открывайте места и маршруты: ' + state.cities.length + ' городов</p></div>' +
    '<button class="sheet-close" type="button" data-close aria-label="Закрыть">×</button></div>' +
    (!initData ? '<div class="notice">Без Telegram выбор действует только в этом просмотре.</div>' : "") +
    '<label class="search"><span>⌕</span><input id="city-filter" type="search" ' +
    'autocomplete="off" aria-label="Поиск города" placeholder="Найти город…"></label>' +
    '<div class="city-list" id="city-choices"></div>');
  const field = document.getElementById("city-filter");
  const redraw = () => {
    const query = field.value.trim().toLocaleLowerCase("ru").replaceAll("ё", "е");
    const matching = state.cities.filter(city =>
      city.name.toLocaleLowerCase("ru").replaceAll("ё", "е").includes(query)
    );
    document.getElementById("city-choices").innerHTML = matching.length
      ? matching.map(city => '<button type="button" class="city-choice ' +
        (state.catalog?.slug === city.slug ? "active" : "") +
        '" data-city="' + escapeText(city.slug) + '">' +
        escapeText(city.name) + '</button>').join("")
      : '<div class="empty">Город не найден</div>';
  };
  field.addEventListener("input", redraw);
  redraw();
}

async function loadCity(slug) {
  const catalog = await api("/api/catalogs/" + encodeURIComponent(slug));
  state.catalog = catalog;
  state.category = "all";
  state.search = "";
  state.mapSearch = "";
  state.mapFilter = "all";
  state.mapSelected = null;
  if (state.builder.mapController) {
    state.builder.mapController.destroy();
    state.builder.mapController = null;
  }
  state.builder = { budget_minutes: 240, interest: "classic",
    exclude_visited: false, result: null, busy: false, saving: false,
    saved: false, version: state.builder.version + 1,
    showMap: false, mapController: null, baseRouteId: null, edited: false,
    replacement: null, alternatives: null };
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
    return true;
  } catch (_) {
    notify("Не удалось сохранить город. Перезапустите Mini App из Telegram.");
    return false;
  }
}

screen.addEventListener("click", event => {
  const trigger = event.target.closest("button");
  if (!trigger) return;
  if (trigger.dataset.discoverCity && trigger.dataset.discoverPlace) {
    void openDiscoveryPlace(trigger.dataset.discoverCity, trigger.dataset.discoverPlace);
    return;
  }
  if (trigger.dataset.discoverCategory) {
    const d = state.discovery;
    d.category = trigger.dataset.discoverCategory;
    ++d.version;
    d.loading = false;
    clearTimeout(d.timer);
    d.places = [];
    d.total = 0;
    d.hasMore = false;
    renderDiscover();
    if (d.query.trim().length >= 2) void requestDiscovery();
    return;
  }
  if (trigger.dataset.discoverMore) {
    void requestDiscovery(true);
    return;
  }
  if (trigger.dataset.discoverRetry) {
    void requestDiscovery();
    return;
  }
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
  if (trigger.dataset.builderAlternatives !== undefined) {
    void showBuilderAlternatives(trigger.dataset.builderAlternatives);
    return;
  }
  if (trigger.dataset.builderChoose !== undefined) {
    void replaceBuilderStop(trigger.dataset.builderChoose);
    return;
  }
  if (trigger.dataset.builderMoveUp !== undefined) {
    void editBuilderStop("up", trigger.dataset.builderMoveUp);
    return;
  }
  if (trigger.dataset.builderMoveDown !== undefined) {
    void editBuilderStop("down", trigger.dataset.builderMoveDown);
    return;
  }
  if (trigger.dataset.builderRemove !== undefined) {
    void editBuilderStop("remove", trigger.dataset.builderRemove);
    return;
  }
  if (trigger.dataset.builderBudget) {
    updateBuilderOption("budget_minutes", Number(trigger.dataset.builderBudget));
    return;
  }
  if (trigger.dataset.builderInterest) {
    updateBuilderOption("interest", trigger.dataset.builderInterest);
    return;
  }
  if (trigger.dataset.builderVisited) {
    updateBuilderOption("exclude_visited", trigger.dataset.builderVisited === "true");
    return;
  }
  if (trigger.dataset.builderPreview) {
    void buildPreview();
    return;
  }
  if (trigger.dataset.builderMapToggle) {
    toggleBuilderMap();
    return;
  }
  if (trigger.dataset.builderSave) {
    void saveBuiltRoute();
    return;
  }
  if (trigger.dataset.builderGuide) {
    state.guideSection = "saved";
    navigate("guide");
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
