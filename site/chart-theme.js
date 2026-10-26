(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.MAUL1ChartTheme = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const colors = {
    station: {
      DENL1: '#a3592a', NWCL1: '#147d92', MDLL1: '#7562a5',
      MCHL1: '#806649', MAUL1: '#173f5f'
    },
    model: {
      persistence: '#68767e',
      phase5a_maul1_only: '#317c9a',
      phase5a_coastal: '#7562a5',
      phase5b_coastal_tidal: '#b56b2b',
      phase5b_full_multivariable: '#3d7868',
      challenger: '#b45260'
    },
    datum: {navd88: '#158177', mllw: '#147d92', residual: '#7562a5'}
  };
  const chartConfig = overrides => Object.assign({
    responsive: true,
    displaylogo: false,
    displayModeBar: 'hover',
    scrollZoom: false,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'toggleSpikelines', 'hoverClosestCartesian', 'hoverCompareCartesian']
  }, overrides || {});
  const layout = (title, overrides) => {
    const base = {
      autosize: true,
      showlegend: true,
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {family: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', size: 12, color: '#334d59'},
      title: {text: title || '', x: 0.02, xanchor: 'left', font: {size: 14, color: '#173b4b'}},
      margin: {l: 58, r: 20, t: 50, b: 56},
      xaxis: {showgrid: true, gridcolor: '#e5ecee', automargin: true, title: {font: {size: 11}}},
      yaxis: {showgrid: true, gridcolor: '#e5ecee', automargin: true, title: {font: {size: 11}}},
      legend: {orientation: 'h', y: -0.22, x: 0, font: {size: 10}},
      hovermode: 'x unified',
      uirevision: 'maul1-console'
    };
    return Object.assign(base, overrides || {});
  };
  return {colors, stationColors: colors.station, modelColors: colors.model, chartConfig, layout};
});
