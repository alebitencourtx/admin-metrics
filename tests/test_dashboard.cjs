const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function dashboard() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: {sort:'errors', 'incident-status':'all', 'trend-metric':'error_pct'}[id] || '',
      innerHTML:'', textContent:'', clientWidth:900, listeners:{},
      classList:{toggle(){}}, insertAdjacentHTML(_, html){this.innerHTML += html;},
      addEventListener(name, callback){this.listeners[name] = callback;},
      showModal(){this.open = true;}, close(){this.open = false;}, focus(){},
    });
    return elements.get(id);
  }
  const endpoint = {entity_id:'abc', reporter_id:'ccvm', reporter:'Nome atualizado',
    endpoint:'https://example.com/open-banking/accounts/v2/accounts', path:'/open-banking/accounts/v2/accounts',
    family:'accounts', observed_at:'2026-11-12T18:00:00+00:00', day:'2026-11-12',
    calls:1000, errors:100, error_pct:10, rejections:0, rejection_pct:0,
    mean_ms:300, baseline_mean_ms:300, uptime:1, fresh:true, source_complete:true,
    recurrent_days:3, quality:[], interval_state:'valid', interval_calls:100,
    interval_errors:10, interval_error_pct:10};
  const rules = JSON.parse(fs.readFileSync('config/rules.json', 'utf8'));
  const source = {id:'ccvm', label:'Nome atualizado', observed_at:endpoint.observed_at,
    status:200, complete:true, records:1, probe_ms:10, issues:[], probes:[], coverage:'reported_total_reconciled'};
  const run = {run_id:'new', observed_at:endpoint.observed_at, reports:[source]};
  const data = {
    meta:{version:'1.1.0', run_id:'new', observed_at:endpoint.observed_at, dashboard_history_days:3,
      history_window_start:'2026-11-09T18:00:00+00:00', history_window_end:endpoint.observed_at,
      retained_runs:200}, rules, reporters:[{id:'ccvm', label:'Nome atualizado'}],
    runs:[run], latest:[endpoint], report_summary:[{...endpoint}],
    observation_trends:[{...endpoint, run_id:'new'}],
    points:[{...endpoint}], reported_history:[1,2,3].map(position=>({...endpoint, position})),
    incidents:[{id:'incident', entity_id:'abc', reporter_id:'ccvm', reporter:'Nome antigo',
      rule:'error_rate', status:'open', severity:'critical', last_seen:endpoint.observed_at,
      opened_at:endpoint.observed_at, samples:2, consecutive_samples:2, recovery_samples:0}],
  };
  const events = {};
  const document = {getElementById:element, querySelectorAll:()=>[],
    addEventListener(name, callback){events[name] = callback;}};
  const window = {ADMIN_DATA:data, innerWidth:1200, addEventListener(){}};
  const context = {window, document, setInterval(){}, setTimeout(){}, clearTimeout(){}, console};
  vm.runInNewContext(fs.readFileSync('src/admin_metrics/web/app.js', 'utf8'), context);
  return {element, events, data};
}

test('reporter selection keeps incidents after display-label changes', () => {
  const {element} = dashboard();
  element('reporter').value = 'ccvm';
  element('reporter').listeners.change();
  assert.equal(element('nav-count').textContent, 1);
  assert.match(element('incident-rows').innerHTML, /incident|Nome antigo/);
});

test('three-day chart axis stays fixed even with only one collected sample', () => {
  const {element} = dashboard();
  assert.match(element('history-heading').textContent, /últimos 3 dias/);
  assert.equal(element('sampling-label').textContent, 'AMOSTRAGEM A CADA 1H');
  assert.match(element('trend-note').textContent, /72h/);
  assert.match(element('trend-note').textContent, /não coletados ficam vazios/);
  for (const id of ['trend-chart', 'probe-chart']) {
    assert.match(element(id).innerHTML, /09\/11/);
    assert.match(element(id).innerHTML, /12\/11/);
    assert.doesNotMatch(element(id).innerHTML, /NaN|Infinity/);
  }
});

test('endpoint detail uses the same three-day observation window', () => {
  const {element, events} = dashboard();
  events.click({target:{closest(selector){return selector === '[data-entity]' ? {dataset:{entity:'abc'}} : null;}}});
  assert.equal(element('detail').open, true);
  assert.match(element('detail-chart').innerHTML, /09\/11/);
  assert.match(element('detail-chart').innerHTML, /12\/11/);
  assert.match(element('reported-errors').innerHTML, /D−3/);
  assert.doesNotMatch(element('reported-errors').innerHTML, /D−4/);
});
