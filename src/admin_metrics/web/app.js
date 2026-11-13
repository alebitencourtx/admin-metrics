'use strict';
(() => {
const D = window.ADMIN_DATA, $ = id => document.getElementById(id);
if (!D) { $('freshness').textContent = 'Dados indisponíveis. Consulte as execuções e tente recarregar.'; return; }
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, decimals=0) => v == null || !Number.isFinite(v) ? '—' : v.toLocaleString('pt-BR',{maximumFractionDigits:decimals,minimumFractionDigits:decimals});
const pct = v => v == null ? '—' : num(v,2)+'%';
const fold = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const dt = v => v ? new Date(v).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})+' BRT' : '—';
const total = (rs,k) => rs.some(r=>r[k]!=null) ? rs.reduce((s,r)=>s+(r[k]??0),0) : null;
const rate = (rs,k) => {const good=rs.filter(r=>r.calls>0 && r[k]!=null && r[k]<=r.calls); return good.length ? 100*total(good,k)/total(good,'calls') : null;};
const weighted = rs => {const good=rs.filter(r=>r.calls>0 && r.mean_ms>0); return good.length ? good.reduce((s,r)=>s+r.calls*r.mean_ms,0)/total(good,'calls') : null;};
const status = (label,level='muted') => `<span class="status ${level}">${esc(label)}</span>`;
const empty = text => `<div class="empty">${esc(text)}</div>`;
const labels = {empty_response:'Resposta conciliada sem métricas',empty_response_recovered:'Dados retornaram após repetição da captura vazia',invalid_endpoint_record:'Endpoint declarado inválido',error_rate:'Taxa de erro elevada',rejection_rate:'Taxa de rejeição elevada',mean_latency:'Média de resposta elevada',latency_regression:'Regressão da média',collection:'Falha na coleta',open:'Aberto',recovering:'Em recuperação',resolved:'Resolvido',critical:'Crítico',attention:'Atenção',observation_time_not_increasing:'Instante não avançou',first_observation:'Primeira observação',valid:'Delta válido',day_changed:'Dia de referência mudou',incomplete_source:'Origem incompleta',unchanged_report:'Reporte sem mudança',invalid_counter:'Contador inválido',counter_reset_or_revision:'Reset ou revisão',inconsistent_delta:'Delta inconsistente',reported_clock_skew:'Horário declarado divergente',request_time_invalid:'requestTime inválido',history_lengths_differ:'Arrays históricos de comprimentos diferentes',uptime_downtime_conflict:'Uptime 100% com downtime positivo',zero_uptime_without_traffic:'Uptime zero sem tráfego',average_tps_above_peak:'TPS médio superior ao pico',counter_above_invocations:'Erro/rejeição maior que chamadas',zero_mean_with_traffic:'Média zero com chamadas',page_metadata_conflict:'Cobertura do total com páginas excedentes declaradas',duplicate_endpoint:'Identidade repetida na paginação',conflicting_endpoint:'Valores conflitantes para a mesma identidade',empty_report:'Reporte vazio',pagination_no_new_identity:'Paginação sem novas identidades',reported_total_reconciled:'Total de identidades conciliado',unknown:'Cobertura desconhecida',unconfirmed:'Cobertura não confirmada',record_limit:'Limite de identidades atingido',page_day_changed:'Páginas cruzaram o dia de referência',mixed_reference_day:'Dias de referência diferentes na captura',invalid_records:'Captura com registros inválidos'};
function label(k) { return labels[k] || k.replaceAll('_',' '); }
let page=0, visible=[], selected=''; const size=25, colors=['#087f73','#b86370','#497dab','#bd8b36','#8173ac','#4b948b','#b87949','#7f91a1'];
const last=D.runs.at(-1), reports=()=>last.reports.filter(r=>!selected||r.id===selected);
const scoped=()=>D.latest.filter(r=>!selected||r.reporter_id===selected);
const panorama=()=>D.panoramas[selected||'all']||null;
const panoramaRows=()=>panorama()?.rows||[];
const sourceHealth=id=>D.collection_health.sources.find(r=>r.id===id);
const outcomes={received:'Corpo HTTP recebido',valid:'Com dados válidos',empty:'HTTP 200 sem dados',http_error:'Falha HTTP',transport_error:'Falha de transporte',invalid_report:'Reporte inválido ou incompleto'};
const reporterIds=new Set(D.reporters.map(r=>r.id));
for(const r of D.reporters) $('reporter').insertAdjacentHTML('beforeend',`<option value="${esc(r.id)}">${esc(r.label)}</option>`);
for(const f of [...new Set(D.latest.map(r=>r.family))].sort()) $('family').insertAdjacentHTML('beforeend',`<option>${esc(f)}</option>`);
const encodeValue = value => typeof encodeURIComponent === 'function' ? encodeURIComponent(value) : String(value);
const decodeValue = value => {try{return typeof decodeURIComponent === 'function' ? decodeURIComponent(value) : value;}catch{return value;}};
function readFilters() {
 if(typeof location === 'undefined' || !location.search) return {};
 return location.search.replace(/^\?/,'').split('&').filter(Boolean).reduce((out,part)=>{const at=part.indexOf('='),key=decodeValue(at<0?part:part.slice(0,at)),value=decodeValue(at<0?'':part.slice(at+1));if(value)out[key]=value;return out;},{});
}
const initialFilters=readFilters();
if(initialFilters.reporter&&reporterIds.has(initialFilters.reporter)){selected=initialFilters.reporter;$('reporter').value=selected;}
if(initialFilters.q)$('search').value=initialFilters.q;
if(initialFilters.family)$('family').value=initialFilters.family;
const sortOptions=$('sort').options?[...$('sort').options].map(o=>o.value):[];
if(initialFilters.sort&&(!sortOptions.length||sortOptions.includes(initialFilters.sort)))$('sort').value=initialFilters.sort;
function syncFilters() {
 if(typeof history === 'undefined' || typeof history.replaceState !== 'function' || typeof location === 'undefined') return;
 const parts=[];
 if(selected)parts.push('reporter='+encodeValue(selected));
 if($('search').value.trim())parts.push('q='+encodeValue($('search').value.trim()));
 if($('family').value)parts.push('family='+encodeValue($('family').value));
 if($('sort').value&&$('sort').value!=='errors')parts.push('sort='+encodeValue($('sort').value));
 try{history.replaceState(null,'',location.pathname+(parts.length?'?'+parts.join('&'):'')+location.hash);}catch{}
}
function freshness() {
 const context=panorama(), latestSources=D.collection_health.sources.filter(r=>!selected||r.id===selected);
 const failed=latestSources.filter(r=>r.status!=='valid').length;
 const lastValid=context?context.rows.reduce((value,r)=>r.observed_at>value?r.observed_at:value,context.observed_at):null;
 const age=lastValid?Math.max(0,(Date.now()-Date.parse(lastValid))/3600000):null;
 const historical=context&&context.run_id!==D.meta.run_id;
 const failures=latestSources.filter(r=>r.status!=='valid');
 const details=selected?failures.map(r=>outcomes[r.status]).join('; '):[...new Set(failures.map(r=>r.status))].map(kind=>`${failures.filter(r=>r.status===kind).length} fonte(s): ${outcomes[kind]}`).join('; ');
 const next=`Próximas execuções previstas a cada ${D.rules.schedule_interval_hours}h, no minuto ${D.rules.schedule_minute} UTC (horário sujeito ao GitHub).`;
 $('freshness').classList.toggle('warning',failed>0||historical||age==null||age>D.rules.stale_after_hours);
 $('freshness').textContent=`Última tentativa: ${dt(selected?sourceHealth(selected)?.last_attempt_at:D.collection_health.last_attempt_at)}. Últimos dados válidos do panorama: ${dt(lastValid)}${age==null?'':` · há ${num(age,1)} h`}. ${latestSources.length-failed}/${latestSources.length} fontes com dados válidos nesta tentativa. ${details?details+'. ':''}${historical?'Exibindo dados anteriores — atualização sem dados suficientes ou comparáveis para renovar este panorama. ':''}${!context?'Nenhum ciclo completo disponível para este recorte. ':''}${age!=null&&age>D.rules.stale_after_hours?'Dados válidos desatualizados. ':''}${next}`;
 $('snapshot').textContent=`Tentativa: ${dt(D.meta.observed_at)} · ${D.runs.length} ciclo(s) na janela de ${D.meta.dashboard_history_days} dias · ${D.meta.retained_runs} retido(s) no histórico`;
 $('panorama-context').textContent=context?`${historical?'DADOS ANTERIORES':'CICLO ATUAL'} · DIA ${context.day}`:'SEM PANORAMA VÁLIDO';
 $('panorama-note').textContent=context?`Indicadores e ranking: um único ciclo de ${dt(context.observed_at)}, dia de referência ${context.day}. ${historical?'Valores preservados, sem combinar fontes de ciclos ou dias diferentes. ':''}Incidentes e saúde da coleta refletem a última tentativa.`:'Sem ciclo completo e com dia de referência comum. Métricas ausentes permanecem indisponíveis; não são convertidas em zero.';
}

function endpointTitle(r) {
 const families={'automatic-payments':'Pagamentos automáticos','credit-cards-accounts':'Cartões de crédito',accounts:'Contas',financings:'Financiamentos',loans:'Empréstimos',customers:'Cadastro',consents:'Consentimentos','variable-incomes':'Renda variável'};
 const endings={limits:'Limites',balances:'Saldos','transactions-current':'Transações atuais',transactions:'Transações','recurring-payments':'Pagamentos recorrentes','recurring-consents':'Consentimentos recorrentes',payments:'Pagamentos','scheduled-instalments':'Parcelas programadas',warranties:'Garantias'};
 const tail=r.path.split('/').at(-1), family=families[r.family]||r.family;
 return family+(endings[tail]?' / '+endings[tail]:'');
}
function overview() {
 const rs=panoramaRows(), validErrors=rs.filter(r=>r.calls>0&&r.errors!=null&&r.errors<=r.calls), src=reports(), ok=src.filter(r=>r.status===200&&r.complete&&r.records).length;
 const allowed=new Set(D.reporters.filter(r=>!selected||r.id===selected).map(r=>r.id));
 const live=D.incidents.filter(i=>i.status!=='resolved'&&allowed.has(i.reporter_id));
 $('nav-count').textContent=live.length;
 const cards=[['Fontes na última tentativa',`${ok}<span class="unit">/ ${src.length}</span>`,'reportes com métricas utilizáveis'],['Chamadas declaradas',num(total(rs,'calls')),'dia '+(panorama()?.day||'indisponível')+' · '+num(rs.length)+' endpoints'],['Taxa de erro',pct(rate(rs,'errors')),num(total(validErrors,'errors'))+' / '+num(total(validErrors,'calls'))+' chamadas válidas'],['Média ponderada',num(weighted(rs),0)+'<span class="unit">ms</span>','média declarada × chamadas válidas; não p95']];
 $('kpis').innerHTML=cards.map(c=>`<article class="metric-card"><div class="metric-top">${c[0]}</div><div class="metric-number">${c[1]}</div><div class="metric-note">${c[2]}</div></article>`).join('');
 const ranked=rs.filter(r=>r.errors>0&&r.calls>=r.errors).sort((a,b)=>b.errors-a.errors), top=ranked.slice(0,5), errors=total(ranked,'errors')||0, share=errors?100*(total(top,'errors')||0)/errors:null;
 const critical=live.filter(i=>i.severity==='critical').length, recurrent=rs.filter(r=>r.recurrent_days>=D.rules.recurrent_minimum_days).length;
 $('executive-title').textContent=critical?`${critical} ${critical===1?'sinal crítico':'sinais críticos'} para investigar.`:live.length?`${live.length} ${live.length===1?'sinal':'sinais'} de atenção no recorte.`:ok<src.length?'A cobertura exige investigação.':'Sem sinais acima dos limiares atuais.';
 $('executive-copy').innerHTML=rs.length?`<span class="executive-insight">${share==null?'Sem erros válidos reportados.':'<strong>'+pct(share)+'</strong> dos erros válidos estão nos cinco endpoints do ranking.'}</span><span class="executive-insight"><strong>${recurrent} endpoints</strong> têm erro ≥${D.rules.error_attention_pct}% em pelo menos ${D.rules.recurrent_minimum_days} dias anteriores, com ≥${num(D.rules.minimum_calls)} chamadas por dia.</span><span class="executive-insight">Rejeição atual: <strong>${pct(rate(rs,'rejections'))}</strong>.</span>`:'Não há métricas completas no ciclo atual. Consulte a saúde da coleta e o contexto anterior na tabela de endpoints.';
 $('executive-foot').textContent=`${live.filter(i=>i.confirmed).length} sinal(is) confirmado(s) por persistência · critérios analíticos, sem conclusão causal`;
 $('concentration').textContent=share==null?'SEM BASE':pct(share)+' DO TOTAL';
 $('ranking').innerHTML=top.length?top.map((r,i)=>`<div class="rank-item"><span>0${i+1}</span><div><button class="rank-label" data-entity="${r.entity_id}" data-context-run="${esc(panorama()?.run_id)}" title="${esc(r.endpoint)}"><span class="rank-reporter">${esc(r.reporter)} · ${esc(endpointTitle(r))}</span><span class="rank-path">${esc(r.path)}</span></button><div class="rank-track"><span style="width:${100*r.errors/top[0].errors}%"></span></div></div><div class="rank-value">${num(r.errors)}<small>${pct(r.error_pct)} de ${num(r.calls)}</small></div></div>`).join(''):empty('Sem erros válidos declarados no ciclo atual.');
 $('reporter-cards').innerHTML=src.map(r=>{const h=sourceHealth(r.id), context=D.panoramas[r.id], rs=context?.rows||[], good=h?.status==='valid', healthLabel=h?.status==='empty'?'HTTP 200 sem dados':h?.status==='invalid_report'?'Reporte inválido':good?'HTTP 200':'Falha';return `<button class="reporter-card" data-reporter="${esc(r.id)}"><span class="head">${esc(r.label)} ${status(healthLabel,good?'good':r.status===200?'attention':'critical')}</span><p>${num(r.records)} identidades na tentativa · ${num(r.probe_ms)} ms no Admin<br>Últimos dados válidos: ${dt(h?.last_valid_at)}<br>Média ${num(weighted(rs))} ms · erro ${pct(rate(rs,'errors'))}</p></button>`;}).join('');
}
function incidents() {
 const choice=$('incident-status').value;
 const allowed=new Set(D.reporters.filter(r=>!selected||r.id===selected).map(r=>r.id));
 const rs=D.incidents.filter(i=>allowed.has(i.reporter_id)&&(choice==='all'||i.status!=='resolved')&&(choice!=='critical'||i.severity==='critical'));
 rs.sort((a,b)=>(a.severity==='critical'?-1:1)-(b.severity==='critical'?-1:1)||b.last_seen.localeCompare(a.last_seen));
 $('incident-rows').innerHTML=rs.length?rs.map(i=>`<tr><td>${status(label(i.severity),i.severity)}<small>${esc(label(i.status))}${i.status==='resolved'&&i.resolved_at?` · resolvido ${dt(i.resolved_at)}`:''} · ${i.confirmed?'persistência confirmada':'sinal provisório'}</small></td><td><strong>${esc(i.reporter)}</strong><small>${esc(label(i.rule))}</small>${i.endpoint&&D.latest.some(r=>r.entity_id===i.entity_id)?`<button class="cell-path" data-entity="${esc(i.entity_id)}">${esc(i.endpoint)}</button>`:i.endpoint?`<small>${esc(i.endpoint)} · sem observação atual</small>`:''}</td><td>${esc(i.evidence)}<small>Último sinal: ${dt(i.last_seen)}</small></td><td>${dt(i.opened_at)}</td><td>${num(i.samples)} detecções<small>${num(i.consecutive_samples)} consecutivas · recuperação ${num(i.recovery_samples)}/${D.rules.recovery_samples}</small></td></tr>`).join(''):'<tr><td colspan="5">'+empty('Nenhum incidente neste filtro.')+'</td></tr>';
}
function chart(target, series, unit, valueFormatter=num, emptyMessage='Ainda não há amostras válidas para esta série.') {
 const all=series.flatMap(s=>s.points).filter(p=>p.y!=null&&Number.isFinite(p.y));
 if(!all.length) {target.innerHTML=empty(emptyMessage);return;}
 const W=Math.max(320,target.clientWidth||900),H=250,L=85,R=24,T=18,B=46, min=Date.parse(D.meta.history_window_start),max=Date.parse(D.meta.history_window_end), hi=Math.max(1,...all.map(p=>p.y))*1.12;
 const x=v=>L+(max===min?(W-L-R)/2:(Date.parse(v)-min)/(max-min)*(W-L-R)), y=v=>H-B-v/hi*(H-T-B);
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(unit)} ao longo das observações"><title>${esc(unit)} · valores detalhados nos pontos</title>`;
 for(let i=0;i<4;i++) {const v=hi*i/3;svg+=`<line x1="${L}" y1="${y(v)}" x2="${W-R}" y2="${y(v)}" stroke="#e9eef1"/><text class="axis" x="${L-9}" y="${y(v)+3}" text-anchor="end">${esc(valueFormatter(v))}</text>`;}
 const ticks=[min,...(max>min?(W>=550?[min+(max-min)/2,max]:[max]):[])];
 ticks.forEach(t=>{svg+=`<text class="axis" x="${x(new Date(t).toISOString())}" y="${H-12}" text-anchor="${max===min?'middle':t===min?'start':t===max?'end':'middle'}">${esc(new Date(t).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}))}</text>`;});
 series.forEach((s,i)=>{const color=colors[i%colors.length];let segments=[],segment=[],prev;
  for(const p of s.points) {if(p.y==null||!Number.isFinite(p.y)|| (prev && (Date.parse(p.x)-Date.parse(prev.x)>D.rules.chart_gap_hours*3600000 || (p.day&&prev.day&&p.day!==prev.day)))) {if(segment.length)segments.push(segment);segment=[];} if(p.y!=null&&Number.isFinite(p.y))segment.push(p);prev=p;}
  if(segment.length)segments.push(segment);
  segments.forEach(ps=>{svg+=`<polyline points="${ps.map(p=>x(p.x)+','+y(p.y)).join(' ')}" fill="none" stroke="${color}" stroke-width="2"/>`;});
  for(const p of s.points.filter(p=>p.y!=null&&Number.isFinite(p.y))) svg+=`<circle class="point" tabindex="0" cx="${x(p.x)}" cy="${y(p.y)}" r="${all.length>100?2:4}" fill="${color}"><title>${esc(s.name)} · ${dt(p.x)} · ${esc(valueFormatter(p.y))} ${esc(unit)}${p.note?' · '+esc(p.note):''}</title></circle>`;
 });
 target.innerHTML=svg+'</svg><div class="legend">'+series.map((s,i)=>`<span><i style="background:${colors[i%colors.length]}"></i>${esc(s.name)}</span>`).join('')+'</div>';
}
function trends() {
 const metric=$('trend-metric').value, unit=metric==='error_pct'?'%':metric==='mean_ms'?'ms':'chamadas';
 const ss=D.reporters.filter(r=>!selected||r.id===selected).map(r=>({name:r.label,points:D.runs.map(run=>{const p=D.observation_trends.find(t=>t.run_id===run.run_id&&t.reporter_id===r.id); const source=run.reports.find(s=>s.id===r.id);return {x:source?.observed_at||run.observed_at,y:p?.[metric]??null,day:new Date(source?.observed_at||run.observed_at).toLocaleDateString('en-CA',{timeZone:'America/Sao_Paulo'}),note:p?num(p.calls)+' chamadas no dia; cobertura pode variar':'sem cobertura'};})}));
 $('trend-note').textContent=`Janela de ${D.meta.dashboard_history_days*24}h · ${D.runs.length} ciclos disponíveis · dados desde ${dt(D.runs[0].observed_at)}. Lacunas >${num(D.rules.chart_gap_hours,1)}h, ausência e mudança de dia interrompem linhas. Períodos não coletados ficam vazios.`;
 chart($('trend-chart'),ss,unit,v=>num(v,metric==='error_pct'?1:0));
 const ps=D.reporters.filter(r=>!selected||r.id===selected).map(r=>({name:r.label,points:D.runs.map(run=>{const p=run.reports.find(x=>x.id===r.id);return{x:p?.observed_at||run.observed_at,y:p?.probe_ms??null,note:'HTTP '+(p?.status||0)};})}));
 chart($('probe-chart'),ps,'ms',v=>num(v));
}
function endpoints() {
 const query=fold($('search').value.trim()),family=$('family').value,sort=$('sort').value;
 visible=scoped().filter(r=>(!query||fold(r.endpoint+' '+r.reporter).includes(query))&&(!family||r.family===family));
 visible.sort((a,b)=>sort==='path'?a.path.localeCompare(b.path):(b[sort]??-1)-(a[sort]??-1)||a.path.localeCompare(b.path));
 page=Math.min(page,Math.max(0,Math.ceil(visible.length/size)-1));
 $('endpoint-count').textContent=`${visible.length} ENDPOINTS NO FILTRO`;
 $('endpoint-rows').innerHTML=visible.slice(page*size,(page+1)*size).map(r=>`<tr><td><div class="cell-label">${esc(r.reporter)}</div><button class="cell-path" data-entity="${r.entity_id}">${esc(r.path)}</button><small>${esc(r.family)}</small></td><td>${num(r.calls)}</td><td>${num(r.errors)}<small>${pct(r.error_pct)}</small></td><td>${pct(r.rejection_pct)}<small>${num(r.rejections)} rejeições</small></td><td>${num(r.mean_ms)}<small>média, não p95</small></td><td>${pct(r.uptime==null?null:100*r.uptime)}</td><td>${r.fresh&&r.source_complete?status('Ciclo atual','good'):status('Métrica antiga / parcial','attention')}<small>${r.quality.length} ocorrência(s) · ${r.recurrent_days} dia(s) com erro ≥${D.rules.error_attention_pct}%</small></td></tr>`).join('')||'<tr><td colspan="7">'+empty('Nenhum endpoint encontrado.')+'</td></tr>';
 $('page-note').textContent=visible.length?`${page*size+1}–${Math.min((page+1)*size,visible.length)} de ${visible.length} · clique no endpoint para investigar`:'Sem resultados';
 $('prev').disabled=page===0;$('next').disabled=(page+1)*size>=visible.length;
}
function probes() {
 $('probe-rows').innerHTML=reports().map(r=>`<tr><td><strong>${esc(r.label)}</strong><small>${esc(r.cnpj)}</small></td><td>${status('HTTP '+r.status,sourceHealth(r.id)?.status==='valid'?'good':r.status===200?'attention':'critical')}<small>${esc(outcomes[sourceHealth(r.id)?.status]||label(r.coverage))}</small></td><td>${num(r.records)}<small>${r.probes.length} tentativa(s)</small></td><td>${dt(r.observed_at)}</td><td>${num(r.probe_ms)} ms<small>última tentativa, não tempo do ETL</small></td><td>${r.issues.length?r.issues.map(k=>esc(label(k))).join('<br>'):'Sem inconsistência de coleta detectada'}<small><a href="${esc(r.url)}" target="_blank" rel="noopener">Origem Admin ↗</a></small></td></tr>`).join('');
}
let executionPage=0;
const executionSize=12;
function executionOutcome(r) {
 if(r.data_status)return r.data_status;
 if(r.status===0)return 'transport_error';
 if(r.status!==200)return 'http_error';
 if(!r.records&&(r.complete||r.issues.includes('empty_report')))return 'empty';
 return r.complete&&r.records?'valid':'invalid_report';
}
function executions() {
 const sources=D.reporters.filter(r=>!selected||r.id===selected), runs=[...D.runs].reverse();
 executionPage=Math.min(executionPage,Math.max(0,Math.ceil(runs.length/executionSize)-1));
 $('execution-count').textContent=`${runs.length} EXTRAÇÕES · ${sources.length} API(S)`;
 $('execution-head').innerHTML='<tr><th>Extração / horário BRT</th><th>Saúde da coleta</th>'+sources.map(r=>`<th>${esc(r.label)}</th>`).join('')+'</tr>';
 $('execution-rows').innerHTML=runs.slice(executionPage*executionSize,(executionPage+1)*executionSize).map(run=>{
  const reports=sources.map(r=>run.reports.find(p=>p.id===r.id)), good=reports.filter(r=>r&&executionOutcome(r)==='valid').length;
  return `<tr><td><strong>${dt(run.observed_at)}</strong><small>${esc(run.run_id)}</small></td><td>${status(`${good}/${sources.length} com dados`,good===sources.length?'good':'attention')}</td>${sources.map((source,i)=>{const r=reports[i];if(!r)return '<td>'+status('Não observada')+'</td>';const kind=executionOutcome(r);return `<td><button class="execution-cell" aria-label="${esc(source.label+' · '+dt(run.observed_at)+' · '+outcomes[kind])}" data-execution="${esc(run.run_id)}" data-execution-reporter="${esc(source.id)}">${status(kind==='valid'?`HTTP ${r.status} · ${num(r.records)} reg.`:kind==='empty'?'HTTP 200 · vazio':`HTTP ${r.status||'—'}`,kind==='valid'?'good':kind==='empty'?'attention':'critical')}<small>${esc(outcomes[kind])} · ${r.probes.length} tentativa(s)</small></button></td>`;}).join('')}</tr>`;
 }).join('');
 $('execution-page-note').textContent=`${executionPage*executionSize+1}–${Math.min((executionPage+1)*executionSize,runs.length)} de ${runs.length} extrações · clique numa API para detalhar`;
 $('execution-prev').disabled=executionPage===0;
 $('execution-next').disabled=(executionPage+1)*executionSize>=runs.length;
}
function executionDetail(runId, reporterId) {
 const run=D.runs.find(r=>r.run_id===runId), report=run?.reports.find(r=>r.id===reporterId);
 if(!report)return;
 const kind=executionOutcome(report), link=/^https:\/\/github\.com\/[^/]+\/[^/]+\/actions\/runs\/\d+$/.test(run.execution_url||'')?`<a class="button secondary" href="${esc(run.execution_url)}" target="_blank" rel="noopener">Abrir execução no Actions ↗</a>`:'<p class="footnote">Esta extração antiga não tem vínculo do Actions registrado.</p>';
 $('execution-title').textContent=report.label+' · '+dt(run.observed_at);
 $('execution-body').innerHTML=`<p class="dialog-note">${esc(outcomes[kind])} · ${num(report.records)} identidades retornadas. ${report.status===200&&!report.records?'HTTP 200 confirma a resposta HTTP; o corpo não trouxe métricas utilizáveis.':''}</p><div class="detail-grid"><div class="detail-stat"><small>HTTP final</small>${report.status||'—'}</div><div class="detail-stat"><small>Dados utilizáveis</small>${kind==='valid'?'Sim':'Não'}</div><div class="detail-stat"><small>Tentativas HTTP</small>${report.probes.length}</div><div class="detail-stat"><small>Última tentativa</small>${num(report.probe_ms)} ms</div></div><p>Fonte Admin: <a href="${esc(report.url)}" target="_blank" rel="noopener">${esc(report.url)}</a></p><p class="dialog-note">Diagnóstico: ${report.issues.map(k=>esc(label(k))).join('; ')||'Sem inconsistência de coleta detectada'}. Instante da captura: ${dt(report.observed_at)}.</p>${link}<h3>Todas as tentativas preservadas</h3><p class="footnote">Duração mede a requisição ao Admin, não a latência dos serviços declarados. Captura identifica a repetição após resposta vazia; tentativa HTTP identifica o retry de transporte/HTTP dentro da captura.</p><div class="table-wrap"><table><thead><tr><th>Captura / tentativa</th><th>Horário BRT</th><th>HTTP</th><th>Duração</th><th>Bytes</th><th>Resultado</th></tr></thead><tbody>${report.probes.map(p=>`<tr><td>${p.capture_attempt||1} / ${p.attempt}</td><td>${dt(p.observed_at||report.observed_at)}</td><td>${p.status||'—'}</td><td>${num(p.duration_ms)} ms</td><td>${num(p.bytes)}</td><td>${esc(p.error||outcomes[p.data_status||(p===report.probes.at(-1)?kind:'received')]||'Corpo HTTP recebido')}<small>SHA-256: ${esc(p.source_sha||'Sem corpo completo')}</small></td></tr>`).join('')}</tbody></table></div><p class="footnote">Os hashes permanecem no histórico. Os bytes brutos têm retenção dos dois ciclos recentes por pacote.</p>`;
 $('execution-detail').showModal();$('close-execution').focus();
}
function counts(values) {const out={};for(const v of values)out[v]=(out[v]||0)+1;return Object.entries(out).sort((a,b)=>b[1]-a[1]);}
function quality() {
 const rs=scoped(), flags=counts(rs.flatMap(r=>r.quality));
 $('quality-total').textContent=`${rs.filter(r=>r.quality.length).length} ENDPOINTS COM OCORRÊNCIAS`;
 $('quality-rules').innerHTML=flags.map(([k,n])=>`<div class="quality-item"><span>${esc(label(k))}<small>${esc(k)}</small></span><b>${num(n)}</b></div>`).join('')||empty('Sem inconsistências detectadas no recorte.');
 $('interval-rules').innerHTML=counts(rs.map(r=>r.interval_state)).map(([k,n])=>`<div class="quality-item"><span>${esc(label(k))}</span><b>${num(n)}</b></div>`).join('');
}
function reportedChart(target, points, metric, unit) {
 const values=[...points].reverse().map(p=>({position:p.position,value:metric==='error_pct'?(p.calls>0&&p.errors!=null&&p.errors<=p.calls?100*p.errors/p.calls:null):p.mean_ms,calls:p.calls}));
 const max=Math.max(1,...values.map(p=>p.value||0)), W=Math.max(320,target.clientWidth||420),H=195,B=35,T=28,step=(W-40)/Math.max(1,values.length);
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(metric==='error_pct'?'Taxa de erro':'Média declarada')} nos dias anteriores"><title>Dias anteriores declarados pelo banco</title>`;
 values.forEach((p,i)=>{const x=20+i*step,bar=p.value==null?0:(H-B-T)*p.value/max;svg+=`<rect x="${x+step*.22}" y="${H-B-bar}" width="${step*.56}" height="${bar}" rx="3" fill="${metric==='error_pct'?'#b86370':'#087f73'}"><title>D−${p.position}: ${num(p.value,metric==='error_pct'?1:0)} ${unit} · ${num(p.calls)} chamadas</title></rect><text x="${x+step/2}" y="${H-B-bar-6}" text-anchor="middle" class="axis">${esc(num(p.value,metric==='error_pct'?1:0))}</text><text x="${x+step/2}" y="${H-12}" text-anchor="middle" class="axis">D−${p.position}</text>`;});
 target.innerHTML=values.length?svg+'</svg>':empty('Sem histórico diário declarado.');
}
function detail(id, contextRun) {
 const r=(contextRun?Object.values(D.panoramas).find(s=>s.run_id===contextRun&&s.rows.some(x=>x.entity_id===id))?.rows.find(x=>x.entity_id===id):null)||D.latest.find(x=>x.entity_id===id);
 if(!r) return;
 const outsideWindow=Boolean(contextRun)&&!D.runs.some(run=>run.run_id===contextRun);
 $('detail-title').textContent=r.reporter+' · '+r.path;
 const own=D.points.filter(p=>p.entity_id===id), prev=contextRun?r.previous.calls.slice(0,D.meta.dashboard_history_days).map((calls,i)=>({position:i+1,calls,errors:r.previous.errors[i],rejections:r.previous.rejections[i],mean_ms:r.previous.mean_ms[i]})):D.reported_history.filter(p=>p.entity_id===id);
 $('detail-body').innerHTML=`<p class="dialog-note">Observado em ${dt(r.observed_at)} · ${contextRun?(r.fresh?'ciclo atual usado no panorama':'panorama anterior preservado, com data de referência explícita'):(r.fresh&&r.source_complete?'ciclo atual com métricas utilizáveis':'último contexto da fonte, antigo ou parcial')}. Dia de referência ${esc(r.day)} (${esc(r.day_basis)}).</p><div class="detail-grid">${[['Chamadas',num(r.calls)],['Erros',pct(r.error_pct)],['Média declarada',num(r.mean_ms)+' ms'],['Média histórica de referência',num(r.baseline_mean_ms)+' ms']].map(c=>`<div class="detail-stat"><small>${c[0]}</small>${c[1]}</div>`).join('')}</div><h3>Comparação com a observação anterior</h3><p class="dialog-note">${esc(label(r.interval_state))}. Erros: ${esc(label(r.interval_error_state||r.interval_state))}; rejeições: ${esc(label(r.interval_rejection_state||r.interval_state))}. ${r.interval_from?'De '+dt(r.interval_from)+' até '+dt(r.interval_to)+'. ':''}${r.interval_state==='valid'?`${num(r.interval_calls)} novas chamadas · ${num(r.interval_errors)} erros · taxa ${pct(r.interval_error_pct)}.`:'Não há intervalo comparável para calcular taxa.'} Nenhuma média intervalar ou p95 é inferida.</p><h3>Taxa de erro nas observações próprias</h3>${outsideWindow?'<p class="dialog-note">Este panorama foi preservado fora da janela de 72h; não há série própria publicada para este recorte.</p>':''}<div id="detail-chart" class="chart"></div><h3>Dias anteriores declarados pelo banco</h3><p class="dialog-note">D−1 é ontem segundo a convenção de dia do reporte. Este histórico veio no payload atual e pode ser revisado pela origem; não representa nossas coletas passadas. Recorrência: ${r.recurrent_days} dia(s) com erro ≥${D.rules.error_attention_pct}% e ≥${num(D.rules.minimum_calls)} chamadas, considerando até ${D.rules.reported_history_days} dias declarados. A visualização mostra apenas os três dias mais recentes.</p><div class="two-column"><div><h3>Taxa de erro declarada (%)</h3><div id="reported-errors"></div></div><div><h3>Média declarada (ms)</h3><div id="reported-mean"></div></div></div><div class="table-wrap"><table><thead><tr><th>Posição</th><th>Chamadas</th><th>Erros / taxa</th><th>Rejeição</th><th>Média (ms)</th></tr></thead><tbody>${prev.map(p=>`<tr><td>D−${p.position}</td><td>${num(p.calls)}</td><td>${num(p.errors)} / ${pct(p.calls>0&&p.errors!=null&&p.errors<=p.calls?100*p.errors/p.calls:null)}</td><td>${num(p.rejections)}</td><td>${num(p.mean_ms)}</td></tr>`).join('')||'<tr><td colspan="5">Sem histórico declarado.</td></tr>'}</tbody></table></div><h3>Qualidade e proveniência</h3><div class="pill-list">${r.quality.map(q=>status(label(q),'attention')).join('')||status('Sem flags detectadas','good')}</div><div class="evidence">Endpoint declarado: <code>${esc(r.endpoint)}</code><br>SHA-256 bronze: <code>${esc(r.source_sha)}</code><br>Caminho JSON: <code>${esc(r.json_path)}</code><br>requestTime bruto: <code>${esc(r.request_time)}</code><br>Diferença observada: ${num(r.clock_offset_seconds)} segundos<br>Uptime declarado: ${pct(r.uptime==null?null:r.uptime*100)} · downtime parcial: ${num(r.downtime_seconds)} s<br>TPS médio / pico declarados: ${num(r.average_tps)} / ${num(r.peak_tps)}</div>`;
 $('detail').showModal();
 chart($('detail-chart'),[{name:r.reporter,points:own.map(p=>({x:p.observed_at,y:p.source_complete?p.error_pct:null,day:p.day,note:num(p.calls)+' chamadas'}))}],'%',v=>num(v,1),outsideWindow?'Panorama preservado fora da janela de 72h; sem pontos próprios publicados.':'Ainda não há amostras válidas para esta série.');
 reportedChart($('reported-errors'),prev,'error_pct','%');reportedChart($('reported-mean'),prev,'mean_ms','ms');
 $('close-detail').focus();
}
function render() {freshness();overview();incidents();trends();endpoints();probes();executions();quality();}
$('reporter').addEventListener('change',()=>{selected=$('reporter').value;page=0;executionPage=0;syncFilters();render();});
$('incident-status').addEventListener('change',incidents);$('trend-metric').addEventListener('change',trends);
for(const id of ['search','family','sort']) $(id).addEventListener(id==='search'?'input':'change',()=>{page=0;syncFilters();endpoints();});
$('prev').addEventListener('click',()=>{page--;endpoints();});$('next').addEventListener('click',()=>{page++;endpoints();});
document.addEventListener('click',event=>{const execution=event.target.closest('[data-execution]');if(execution)executionDetail(execution.dataset.execution,execution.dataset.executionReporter);const entity=event.target.closest('[data-entity]');if(entity)detail(entity.dataset.entity,entity.dataset.contextRun);const reporter=event.target.closest('[data-reporter]');if(reporter&&reporterIds.has(reporter.dataset.reporter)){selected=reporter.dataset.reporter;$('reporter').value=selected;page=0;executionPage=0;syncFilters();render();}});
$('execution-prev').addEventListener('click',()=>{executionPage--;executions();});
$('execution-next').addEventListener('click',()=>{executionPage++;executions();});
$('close-execution').addEventListener('click',()=>$('execution-detail').close());
$('execution-detail').addEventListener('click',e=>{if(e.target===$('execution-detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('close-detail').addEventListener('click',()=>$('detail').close());$('detail').addEventListener('click',e=>{if(e.target===$('detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('export').addEventListener('click',()=>{const columns=['reporter_id','reporter','endpoint','observed_at','fresh','source_complete','day','day_basis','request_time','json_path','quality','calls','errors','error_pct','rejections','rejection_pct','mean_ms','uptime','interval_state','interval_calls','interval_errors','interval_error_pct','source_sha']; const cell=v=>'"'+String(v??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"';const csv='\ufeff'+[columns.join(';'),...visible.map(r=>columns.map(k=>cell(r[k])).join(';'))].join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));const a=document.createElement('a');a.href=url;a.download='admin-metrics-endpoints.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
const rules=D.rules;$('rule-summary').innerHTML=`<ul><li>Erro ≥${rules.error_attention_pct}% com ≥${num(rules.minimum_calls)} chamadas; crítico ≥${rules.error_critical_pct}% com ≥${num(rules.critical_minimum_calls)}.</li><li>Rejeição ≥${rules.rejection_attention_pct}% com ≥${num(rules.minimum_calls)} chamadas, sem inferência de causa.</li><li>Média ≥${num(rules.latency_attention_ms)} ms: atenção; ≥${num(rules.latency_critical_ms)} ms: crítico, com amostra mínima.</li><li>Regressão ≥${rules.regression_multiplier}× a mediana de pelo menos ${rules.baseline_minimum_days} médias diárias anteriores válidas.</li><li>Falha do Admin: atenção na primeira coleta e crítica após ${rules.confirmation_samples} falhas consecutivas. Recuperação: ${rules.recovery_samples} amostras válidas.</li></ul>`;
$('history-heading').textContent=`Observações próprias · últimos ${D.meta.dashboard_history_days} dias`;
$('sampling-label').textContent=`AMOSTRAGEM A CADA ${D.rules.schedule_interval_hours}H`;
$('app-version').textContent='v'+D.meta.version;
$('build-info').textContent='v'+D.meta.version+' · '+D.meta.run_id;
render();setInterval(freshness,60000);
const nav=[...document.querySelectorAll('.nav-item')],sections=nav.map(a=>document.querySelector(a.getAttribute('href')));
function activeSection(){const edge=window.innerWidth<=900?150:90;let active=sections[0];for(const s of sections)if(s.getBoundingClientRect().top<=edge)active=s;for(const a of nav){const yes=a.hash==='#'+active.id;a.classList.toggle('active',yes);if(yes)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');}}
document.addEventListener('scroll',activeSection,{passive:true});let resizeTimer;window.addEventListener('resize',()=>{activeSection();clearTimeout(resizeTimer);resizeTimer=setTimeout(trends,150);});activeSection();
})();
