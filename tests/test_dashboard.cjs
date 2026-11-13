const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function dashboard({mutate=()=>{}, now='2026-11-12T18:10:00+00:00', url=''}={}) {
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
  const snapshot={run_id:'new',observed_at:endpoint.observed_at,day:endpoint.day,rows:[{...endpoint}]};
  data.panoramas={all:snapshot,ccvm:snapshot};
  data.collection_health={status:'healthy',valid_sources:1,total_sources:1,last_attempt_at:endpoint.observed_at,last_valid_at:endpoint.observed_at,sources:[{id:'ccvm',status:'valid',last_attempt_at:endpoint.observed_at,last_valid_at:endpoint.observed_at}]};
  mutate(data);
  const events = {};
  const document = {getElementById:element, querySelectorAll:()=>[],
    addEventListener(name, callback){events[name] = callback;}};
  const window = {ADMIN_DATA:data, innerWidth:1200, addEventListener(){}};
  const location = {search:url, pathname:'/', hash:''};
  const history = {replaceState(){}};
  class Clock extends Date {static now(){return Date.parse(now);}}
  const context = {window, document, location, history, Date:Clock, setInterval(){}, setTimeout(){}, clearTimeout(){}, console};
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

function failedCollection(data, kind='empty') {
  data.panoramas.all.run_id = 'old';
  data.panoramas.ccvm = data.panoramas.all;
  data.panoramas.all.rows.forEach(r=>r.fresh=false);
  data.latest.forEach(r=>r.fresh=false);
  const source=data.runs.at(-1).reports[0];
  Object.assign(source,{status:kind==='empty'?200:503,records:0,complete:false,issues:[kind==='empty'?'empty_report':'http_503']});
  Object.assign(data.collection_health,{status:'unavailable',valid_sources:0});
  data.collection_health.sources[0].status=kind;
}

test('recent successful attempt renders concrete schedule without placeholders', () => {
  const {element}=dashboard();
  assert.match(element('freshness').textContent,/cada 1h, no minuto 17 UTC/);
  assert.doesNotMatch(element('freshness').textContent,/\$\{/);
  assert.match(element('freshness').textContent,/1\/1 fontes com dados válidos/);
});

test('fresh attempt with empty data keeps previous KPIs and identifies their reference day', () => {
  const {element}=dashboard({mutate:failedCollection});
  assert.match(element('kpis').innerHTML,/1[.\s]?000/);
  assert.match(element('kpis').innerHTML,/0<span class="unit">\/ 1/);
  assert.match(element('panorama-context').textContent,/DADOS ANTERIORES.*2026-11-12/);
  assert.match(element('freshness').textContent,/HTTP 200 sem dados/);
  assert.match(element('freshness').textContent,/Última tentativa:.*Últimos dados válidos/);
  assert.match(element('panorama-note').textContent,/sem combinar fontes/);
  assert.doesNotMatch(element('freshness').textContent,/\$\{/);
});

test('HTTP failure has a distinct diagnosis and preserves panorama', () => {
  const {element}=dashboard({mutate:data=>failedCollection(data,'http_error')});
  assert.match(element('freshness').textContent,/Falha HTTP/);
  assert.doesNotMatch(element('freshness').textContent,/HTTP 200 sem dados/);
  assert.match(element('kpis').innerHTML,/1[.\s]?000/);
});

test('data age remains stale even when the latest attempt is recent', () => {
  const {element}=dashboard({now:'2026-11-13T03:31:00+00:00',mutate:data=>{
    failedCollection(data);
    data.collection_health.last_attempt_at='2026-11-13T03:30:00+00:00';
  }});
  assert.match(element('freshness').textContent,/há 9,5 h/);
  assert.match(element('freshness').textContent,/Dados válidos desatualizados/);
  assert.match(element('freshness').textContent,/00:30/);
});

test('no prior valid cycle leaves metrics unavailable rather than inventing zero traffic', () => {
  const {element}=dashboard({mutate:data=>{failedCollection(data);data.panoramas={};}});
  assert.match(element('freshness').textContent,/Nenhum ciclo completo disponível/);
  assert.match(element('panorama-context').textContent,/SEM PANORAMA VÁLIDO/);
  assert.match(element('kpis').innerHTML,/—/);
});


test('execution monitor differentiates empty response from HTTP error and opens evidence', () => {
  const {element,events}=dashboard({mutate:data=>{
    failedCollection(data,'http_error');
    data.runs[0].execution_url='https://github.com/alebitencourtx/admin-metrics/actions/runs/123';
    data.runs[0].reports[0].probes=[{page:1,attempt:1,capture_attempt:1,status:503,error:'http_503',duration_ms:17,bytes:280}];
  }});
  assert.match(element('execution-rows').innerHTML,/HTTP 503/);
  assert.match(element('execution-rows').innerHTML,/0\/1 com dados/);
  events.click({target:{closest(selector){return selector==='[data-execution]'?{dataset:{execution:'new',executionReporter:'ccvm'}}:null;}}});
  assert.equal(element('execution-detail').open,true);
  assert.match(element('execution-body').innerHTML,/http_503/);
  assert.match(element('execution-body').innerHTML,/actions\/runs\/123/);
  const empty=dashboard({mutate:failedCollection});
  assert.match(empty.element('execution-rows').innerHTML,/HTTP 200 · vazio/);
});

test('execution monitor paginates without dropping previous extraction evidence', () => {
  const {element}=dashboard({mutate:data=>{
    data.runs=Array.from({length:25},(_,i)=>({...data.runs[0],run_id:'r'+i}));
  }});
  assert.match(element('execution-page-note').textContent,/1–12 de 25/);
  element('execution-next').listeners.click();
  assert.match(element('execution-page-note').textContent,/13–24 de 25/);
  element('execution-next').listeners.click();
  assert.match(element('execution-page-note').textContent,/25–25 de 25/);
  assert.equal(element('execution-next').disabled,true);
});

test('endpoint search folds accents', () => {
  const {element}=dashboard({mutate:data=>{data.latest[0].reporter='Aymoré';}});
  element('search').value='aymore';
  element('search').listeners.input();
  assert.match(element('endpoint-rows').innerHTML,/Aymoré/);
});

test('filters initialize from the URL', () => {
  const {element}=dashboard({url:'?reporter=ccvm&q=accounts&sort=mean_ms'});
  assert.equal(element('reporter').value,'ccvm');
  assert.equal(element('search').value,'accounts');
  assert.equal(element('sort').value,'mean_ms');
});

test('resolved incidents expose the resolution time', () => {
  const {element}=dashboard({mutate:data=>{
    Object.assign(data.incidents[0],{status:'resolved',severity:'attention',
      resolved_at:'2026-11-12T19:00:00+00:00'});
  }});
  assert.match(element('incident-rows').innerHTML,/resolvido/);
});

test('preserved panorama outside the 72h window explains the empty own series', () => {
  const {element,events}=dashboard({mutate:data=>{
    const previous={calls:[1000,1000,1000],errors:[100,100,100],
      rejections:[0,0,0],mean_ms:[300,300,300]};
    data.latest[0].previous=previous;
    data.panoramas.all.run_id='old';
    data.panoramas.all.rows[0].previous=previous;
    data.panoramas.ccvm=data.panoramas.all;
    data.latest[0].fresh=false;
    data.points=[];
  }});
  events.click({target:{closest(selector){return selector==='[data-entity]'
    ? {dataset:{entity:'abc',contextRun:'old'}} : null;}}});
  assert.match(element('detail-chart').innerHTML,/fora da janela de 72h/);
});
