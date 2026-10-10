"use strict";

/* Leaflet is an optional visual layer. The rest of the Mini App works without it. */
(function () {
  const DEFAULT_CENTER = [59.9386, 30.3141];
  const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

  function validCoordinates(place) {
    return Number.isFinite(place.latitude) &&
      Number.isFinite(place.longitude) &&
      Math.abs(place.latitude) <= 90 &&
      Math.abs(place.longitude) <= 180;
  }

  function safeText(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;",
      '"': "&quot;", "'": "&#39;"
    }[char]));
  }

  function mount(containerId, onSelect) {
    if (!window.L || typeof window.L.map !== "function") return null;
    const L = window.L;
    const map = L.map(containerId, {
      zoomControl: true,
      scrollWheelZoom: false,
      attributionControl: true
    }).setView(DEFAULT_CENTER, 11);

    L.tileLayer(TILES, {
      minZoom: 3,
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" ' +
        'target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>',
      /* Leaflet 1.9.4 supports image-layer referrerPolicy via L.TileLayer. */
      referrerPolicy: "strict-origin-when-cross-origin"
    }).addTo(map);

    const layer = L.layerGroup().addTo(map);
    let markers = [];

    function update(places, { fit = true } = {}) {
      layer.clearLayers();
      markers = [];
      const bounds = [];
      for (const place of places) {
        if (!validCoordinates(place)) continue;
        const coords = [place.latitude, place.longitude];
        const icon = L.divIcon({
          className: "places-pin",
          html: '<span aria-hidden="true">' + safeText(place.emoji) + "</span>",
          iconSize: [42, 42],
          iconAnchor: [21, 42]
        });
        const marker = L.marker(coords, {
          icon,
          title: String(place.title).slice(0, 120),
          alt: String(place.title).slice(0, 120),
          keyboard: true
        }).addTo(layer);
        marker.on("click", () => onSelect(place.slug));
        markers.push(marker);
        bounds.push(coords);
      }
      if (fit && bounds.length > 0) {
        if (bounds.length === 1) {
          map.setView(bounds[0], 13);
        } else {
          map.fitBounds(bounds, { padding: [34, 34], maxZoom: 13 });
        }
      }
      return markers.length;
    }

    return {
      update,
      count: () => markers.length,
      focus(coords) {
        if (Array.isArray(coords) && coords.length === 2 &&
          coords.every(Number.isFinite)) map.panTo(coords);
      },
      destroy() {
        layer.clearLayers();
        map.remove();
      }
    };
  }

  window.PlacesMap = { mount, validCoordinates };
}());
