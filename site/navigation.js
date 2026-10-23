(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.initNavigation(root.document, root);
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  function initNavigation(document, window) {
    const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;
    const panels = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));
    if (panels.some(panel => !panel)) return;
    const activate = (index, updateHash = true, moveFocus = false) => {
      const selected = (index + tabs.length) % tabs.length;
      tabs.forEach((tab, i) => {
        const active = i === selected;
        tab.setAttribute('aria-selected', String(active));
        tab.setAttribute('tabindex', active ? '0' : '-1');
        panels[i].hidden = !active;
        panels[i].setAttribute('aria-hidden', String(!active));
      });
      if (updateHash && window.history?.replaceState) window.history.replaceState(null, '', `#${panels[selected].id}`);
      if (moveFocus) tabs[selected].focus();
      if (typeof window.dispatchEvent === 'function' && typeof window.CustomEvent === 'function') window.dispatchEvent(new window.CustomEvent('maul1:viewchange', { detail: { panelId: panels[selected].id } }));
    };
    const selectHash = () => {
      const index = panels.findIndex(panel => `#${panel.id}` === window.location.hash);
      activate(index < 0 ? 0 : index, false);
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activate(index));
      tab.addEventListener('keydown', event => {
        let next = null;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = index + 1;
        if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = index - 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (next !== null) {
          event.preventDefault();
          activate(next, true, true);
        }
      });
    });
    window.addEventListener('hashchange', selectHash);
    selectHash();
    return { activate };
  }
  return { initNavigation };
});
