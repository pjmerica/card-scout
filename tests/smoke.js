// Smoke test: run the generated page's JS against the fresh data in a DOM stub.
//  1. render every tab x filter variant (fails on throw, empty output, "undefined"/NaN)
//  2. CLICK every wired control (tabs, chips, segmented switches, buttons, search) so a broken
//     onclick handler fails CI too
// Usage: node tests/smoke.js site/index.html
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(process.argv[2] || 'site/index.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('no inline script');

const els = {};
const lastLists = [];
const unesc = s => s.replace(/&#39;/g, "'").replace(/&amp;/g, '&').replace(/&quot;/g, '"');
function qsa(sel) {
  let src, re, key;
  if (sel === '#tabs button') { src = el('tabs').innerHTML; re = /data-tab="([^"]*)"/g; key = 'tab'; }
  else if (sel.includes('[data-v]')) { src = el('main').innerHTML; re = /<button[^>]*data-v="([^"]*)"/g; key = 'v'; }
  else if (sel === '.chip') { src = el('main').innerHTML; re = /class="chip[^"]*" data-v="([^"]*)"/g; key = 'v'; }
  else return [];
  const out = [...src.matchAll(re)].map(m => ({ dataset: { [key]: unesc(m[1]) }, onclick: null }));
  lastLists.push(out);
  return out;
}
function el(id) {
  return els[id] || (els[id] = { id, innerHTML: '', textContent: '', value: '', href: '', style: {}, dataset: {},
    setAttribute() {}, getAttribute() { return null; }, focus() {}, setSelectionRange() {}, querySelectorAll: qsa });
}
const ctx = { document: { getElementById: el, querySelectorAll: qsa, documentElement: { setAttribute() {}, getAttribute() { return null; } } },
  console, Date, Math, JSON, Set, Map, Object, Array, String, Number, RegExp, Error,
  localStorage: { getItem: () => null, setItem() {} }, matchMedia: () => ({ matches: false }), window: { scrollTo() {} },
  __lastLists: lastLists, __el: el };
vm.createContext(ctx);
const harness = `
;globalThis.__run = () => {
  const out = {};
  const check = (label) => {
    const h = document.getElementById('main').innerHTML;
    if (!h || h.length < 50) throw new Error('empty render ' + label);
    const bad = h.search(/undefined|NaN/);
    if (bad >= 0) throw new Error('undefined/NaN in ' + label + ': ' + h.slice(Math.max(0, bad - 120), bad + 40));
    return h;
  };
  const reset = (tab) => Object.assign(state, {tab, q:'', cardType:'personal', limit:50, cats:new Set(), newOnly:false, noFee:false, reachable:false});
  const variants = [{}, {cardType:'business'}, {noFee:true}, {reachable:true}, {q:'chase'}, {newOnly:true},
                    {cats:new Set(['Shopping & Card-Linked Offers'])}];
  for (const t of TABS) for (const v of variants) { reset(t.id); Object.assign(state, v); render(); out[t.id] = check(t.id + ' ' + JSON.stringify(v)).length; }

  let clicks = 0;
  const click = (b, label) => { if (b && typeof b.onclick === 'function') { b.onclick(); clicks++; check('after click ' + label); } };
  renderTabs();
  const tabs = __lastLists[__lastLists.length - 1].slice();
  for (const tb of tabs) {
    click(tb, 'tab ' + tb.dataset.tab);
    const before = __lastLists.length; render();
    for (const l of __lastLists.slice(before).map(x => x.slice())) for (const b of l) { click(b, tb.dataset.tab + ' ' + JSON.stringify(b.dataset)); reset(tb.dataset.tab); render(); }
    for (const id of ['noFee', 'reach', 'newBtn', 'more']) { const e = __el(id); click(e, tb.dataset.tab + ' #' + id); e.onclick = null; }
    const q = __el('q'); if (typeof q.oninput === 'function') { q.oninput({target:{value:'amex', selectionStart:4}}); clicks++; check(tb.dataset.tab + ' search'); q.oninput = null; }
    reset(tb.dataset.tab);
  }
  out.clicks = clicks;
  return out;
};`;
vm.runInContext(scripts[scripts.length - 1] + harness, ctx, { filename: 'page.js' });
const res = ctx.__run();
if (!el('stats').innerHTML.includes('stat')) throw new Error('header stats did not render');
if (res.clicks < 15) throw new Error('too few controls exercised: ' + res.clicks);
console.log('smoke OK:', JSON.stringify(res));
