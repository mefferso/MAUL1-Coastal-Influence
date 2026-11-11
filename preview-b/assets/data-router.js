(()=>{
'use strict';
const SNAPSHOT='e236d8946fe7acbfb764f1ba60960f9bb806881e';
const ROOT=`https://raw.githubusercontent.com/mefferso/MAUL1-Coastal-Influence/${SNAPSHOT}/site/`;
const nativeFetch=window.fetch.bind(window);
function resolve(input,init={}){const request=input instanceof Request?input:null;const method=(init.method||request?.method||'GET').toUpperCase();if(!['GET','HEAD'].includes(method))return Promise.reject(new TypeError('Design B is read-only; only GET and HEAD are allowed.'));const raw=typeof input==='string'?input:input.url;const u=new URL(raw,location.href);if(u.origin===location.origin&&/(^|\/)data\//.test(u.pathname)){const rel=u.pathname.slice(u.pathname.indexOf('/data/')+6);return nativeFetch(ROOT+'data/'+rel+u.search,{...init,method});}return nativeFetch(input,init)}
window.fetch=resolve;
function pinLinks(root=document){for(const a of root.querySelectorAll('a[href]')){const h=a.getAttribute('href');if(!h)continue;if(h.startsWith('data/'))a.href=ROOT+h;if(h.startsWith('https://github.com/mefferso/MAUL1-Coastal-Influence/blob/main/'))a.href=h.replace('/blob/main/','/blob/'+SNAPSHOT+'/');}}
addEventListener('DOMContentLoaded',()=>{pinLinks();new MutationObserver(records=>records.forEach(r=>r.addedNodes.forEach(n=>{if(n.nodeType===1){if(n.matches?.('a[href]'))pinLinks(n.parentElement||document);pinLinks(n)}}))).observe(document.body,{childList:true,subtree:true});});
window.MAUL1DesignB=Object.freeze({snapshot:SNAPSHOT,sourceRoot:ROOT,readJSON(path){if(!/^[a-zA-Z0-9_./-]+\.json$/.test(path)||path.includes('..'))return Promise.reject(new TypeError('Invalid snapshot path'));return nativeFetch(ROOT+path).then(r=>{if(!r.ok)throw Error(`Snapshot HTTP ${r.status}`);return r.json()})}});
})();
