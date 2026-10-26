(function (root) {
  'use strict';
  const stations = [
    {id:'DENL1', label:'DENL1 · upstream river discharge', lat:30.464079, lon:-90.99038, detail:'USGS 07378500'},
    {id:'NWCL1', label:'NWCL1 · Lake Pontchartrain', lat:30.027222, lon:-90.113335, detail:'NOAA CO-OPS 8761927'},
    {id:'MDLL1', label:'MDLL1 · independent lake gauge', lat:30.1996389, lon:-90.12275, detail:'USGS 301200090072400 · Crossover 4'},
    {id:'MCHL1', label:'MCHL1 · Pass Manchac', lat:30.283333, lon:-90.396111, detail:'HADS CE678A12 · shadow-only; forecast-ineligible', shadow:true},
    {id:'MAUL1', label:'MAUL1 · Amite River at Highway 22', lat:30.30769444, lon:-90.6087222, detail:'USGS 07380215 · 00065 native gage height'}
  ];
  function escape(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
  function init(document, window) {
    const target = document.getElementById('console-network-map');
    if (!target) return null;
    if (!window.L) {
      target.innerHTML = '<p class="research-empty">Interactive map unavailable; the verified station list remains available beside this panel.</p>';
      return null;
    }
    target.replaceChildren();
    const theme = window.MAUL1ChartTheme;
    const map = window.L.map(target, {scrollWheelZoom:false, keyboard:true, zoomControl:true}).setView([30.27, -90.52], 9);
    window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(map);
    for (const station of stations) {
      const marker = window.L.marker([station.lat, station.lon], {
        keyboard:true,
        title:station.label,
        icon:window.L.divIcon({
          className:'',
          html:`<span class="station-map-marker${station.shadow?' is-shadow':''}" style="background:${theme.stationColors[station.id]}" aria-hidden="true"></span>`,
          iconSize:[18,18], iconAnchor:[9,9]
        })
      }).addTo(map);
      marker.bindPopup(`<strong>${escape(station.label)}</strong><br>${escape(station.detail)}${station.shadow?'<br><b>Shadow-only context; excluded from frozen forecasts.</b>':''}`);
    }
    window.addEventListener('maul1:viewchange', event => {
      if (event.detail?.panelId === 'current-forecast-view') window.requestAnimationFrame(() => map.invalidateSize());
    });
    window.addEventListener('resize', () => map.invalidateSize());
    return map;
  }
  if (typeof module === 'object' && module.exports) module.exports = {stations, init};
  if (root && root.document) root.addEventListener('load', () => init(root.document, root));
})(typeof window !== 'undefined' ? window : null);
