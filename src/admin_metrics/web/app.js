'use strict';
(() => {
const D = window.ADMIN_DATA, $ = id => document.getElementById(id);
if (!D) { $('freshness').textContent = 'Dados indisponíveis. Consulte as execuções e tente recarregar.'; return; }
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, decimals=0) => v == null || !Number.isFinite(v) ? '—' : v.toLocaleString('pt-BR',{maximumFractionDigits:decimals,minimumFractionDigits:decimals});
const pct = v => v == null ? '—' : num(v,2)+'%';
const dt = v => v ? new Date(v).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})+' BRT' : '—';
const total = (rs,k) => rs.some(r=>r[k]!=null) ? rs.reduce((s,r)=>s+(r[k]??0),0) : null;
const rate = (rs,k) => {const good=rs.filter(r=>r.calls>0 && r[k]!=null && r[k]<=r.calls); return good.length ? 100*total(good,k)/total(good,'calls') : null;};
const weighted = rs => {const good=rs.filter(r=>r.calls>0 && r.mean_ms>0); return good.length ? good.reduce((s,r)=>s+r.calls*r.mean_ms,0)/total(good,'calls') : null;};
const status = (label,level='muted') => `<span class="status ${level}">${esc(label)}</span>`;
const empty = text => `<div class="empty">${esc(text)}</div>`;
const labels = {error_rate:'Taxa de erro elevada',rejection_rate:'Taxa de rejeição elevada',mean_latency:'Média de resposta elevada',latency_regression:'Regressão da média',collection:'Falha na coleta',open:'Aberto',recovering:'Em recuperação',resolved:'Resolvido',critical:'Crítico',attention:'Atenção',first_observation:'Primeira observação',valid:'Delta válido',day_changed:'Dia de referência mudou',incomplete_source:'Origem incompleta',unchanged_report:'Reporte sem mudança',invalid_counter:'Contador inválido',counter_reset_or_revision:'Reset ou revisão',inconsistent_delta:'Delta inconsistente',reported_clock_skew:'Horário declarado divergente (>15 min)',request_time_invalid:'requestTime inválido',history_lengths_differ:'Arrays históricos de comprimentos diferentes',uptime_downtime_conflict:'Uptime 100% com downtime positivo',zero_uptime_without_traffic:'Uptime zero sem tráfego',average_tps_above_peak:'TPS médio superior ao pico',counter_above_invocations:'Erro/rejeição maior que chamadas',zero_mean_with_traffic:'Média zero com chamadas',page_metadata_conflict:'Cobertura do total com páginas excedentes declaradas',duplicate_endpoint:'Identidade repetida na paginação',conflicting_endpoint:'Valores conflitantes para a mesma identidade',empty_report:'Reporte vazio',pagination_no_new_identity:'Paginação sem novas identidades',reported_total_reconciled:'Total de identidades conciliado',unknown:'Cobertura desconhecida',unconfirmed:'Cobertura não confirmada'};
function label(k) { return labels[k] || k.replaceAll('_',' '); }
let page=0, visible=[], selected=''; const size=25, colors=['#087f73','#b86370','#497dab','#bd8b36','#8173ac','#4b948b','#b87949','#7f91a1'];
const last=D.runs.at(-1), reports=()=>last.reports.filter(r=>!selected||r.id===selected);
const scoped=()=>D.latest.filter(r=>!selected||r.reporter_id===selected);
const fresh=()=>scoped().filter(r=>r.fresh&&r.source_complete);
const reporterIds=new Set(D.reporters.map(r=>r.id));
for(const r of D.reporters) $('reporter').insertAdjacentHTML('beforeend',`<option value="${esc(r.id)}">${esc(r.label)}</option>`);
for(const f of [...new Set(D.latest.map(r=>r.family))].sort()) $('family').insertAdjacentHTML('beforeend',`<option>${esc(f)}</option>`);
function freshness() {
 const hours=Math.max(0,(Date.now()-Date.parse(D.meta.observed_at))/3600000), failed=reports().filter(r=>!r.complete||!r.records||r.status!==200).length;
 const old=hours>D.rules.stale_after_hours;
 $('freshness').classList.toggle('warning',old||failed>0);
 $('freshness').textContent = `${old?'Atualização atrasada':'Última coleta'}: ${dt(D.meta.observed_at)} · há ${num(hours,1)} h. ${failed?failed+' reporte(s) sem coleta completa; últimas métricas boas preservadas como antigas e excluídas dos indicadores atuais.':'Todos os reportes do recorte tiveram cobertura conciliada.'} ${old?'As métricas abaixo são do último ciclo e estão desatualizadas.':'Próximas execuções previstas a cada 2h, no minuto 17 UTC (horário sujeito ao GitHub).'} `;
 $('snapshot').textContent=`Observação: ${dt(D.meta.observed_at)} · ${D.runs.length} ciclo(s) retido(s)`;
}
function overview() {
 const rs=fresh(), validErrors=rs.filter(r=>r.calls>0&&r.errors!=null&&r.errors<=r.calls), src=reports(), ok=src.filter(r=>r.status===200&&r.complete&&r.records).length;
 const live=D.incidents.filter(i=>i.status!=='resolved'&&(!selected||i.reporter===D.reporters.find(r=>r.id===selected)?.label));
 $('nav-count').textContent=live.length;
 const cards=[['Fontes observadas',`${ok}<span class="unit">/ ${src.length}</span>`,'reportes com cobertura conciliada'],['Chamadas declaradas',num(total(rs,'calls')),'acumulado parcial do dia · '+num(rs.length)+' endpoints'],['Taxa de erro',pct(rate(rs,'errors')),num(total(validErrors,'errors'))+' / '+num(total(validErrors,'calls'))+' chamadas válidas'],['Média ponderada',num(weighted(rs),0)+'<span class="unit">ms</span>','média declarada × chamadas válidas; não p95']];
 $('kpis').innerHTML=cards.map(c=>`<article class="metric-card"><div class="metric-top">${c[0]}</div><div class="metric-number">${c[1]}</div><div class="metric-note">${c[2]}</div></article>`).join('');
 const ranked=rs.filter(r=>r.errors>0&&r.calls>=r.errors).sort((a,b)=>b.errors-a.errors), top=ranked.slice(0,5), errors=total(ranked,'errors')||0, share=errors?100*(total(top,'errors')||0)/errors:null;
 const critical=live.filter(i=>i.severity==='critical').length, recurrent=rs.filter(r=>r.recurrent_days>=3).length;
 $('executive-title').textContent=critical?`${critical} sinal(is) crítico(s) para investigar.`:live.length?`${live.length} sinal(is) de atenção no recorte.`:ok<src.length?'A cobertura exige investigação.':'Sem sinais acima dos limiares atuais.';
 $('executive-copy').textContent=rs.length?`${share==null?'Sem erros válidos reportados.':pct(share)+' dos erros válidos estão nos cinco endpoints de maior volume de erro.'} ${recurrent} endpoint(s) têm erro ≥5% em pelo menos três dias anteriores com ≥100 chamadas. Rejeição atual: ${pct(rate(rs,'rejections'))}.`:'Não há métricas completas no ciclo atual. Consulte a saúde da coleta e o contexto anterior na tabela de endpoints.';
 $('executive-foot').textContent=`${live.filter(i=>i.confirmed).length} sinal(is) confirmado(s) por persistência · critérios analíticos, sem conclusão causal`;
 $('concentration').textContent=share==null?'SEM BASE':pct(share)+' DO TOTAL';
 $('ranking').innerHTML=top.length?top.map((r,i)=>`<div class="rank-item"><span>0${i+1}</span><div><button class="rank-label" data-entity="${r.entity_id}" title="${esc(r.endpoint)}">${esc(r.reporter)} · ${esc(r.path)}</button><div class="rank-track"><span style="width:${100*r.errors/top[0].errors}%"></span></div></div><div class="rank-value">${num(r.errors)}<small>${pct(r.error_pct)} de ${num(r.calls)}</small></div></div>`).join(''):empty('Sem erros válidos declarados no ciclo atual.');
 $('reporter-cards').innerHTML=src.map(r=>{const good=r.complete&&r.records&&r.status===200, m=D.report_summary.find(x=>x.reporter_id===r.id);return `<button class="reporter-card" data-reporter="${esc(r.id)}"><span class="head">${esc(r.label)} ${status(good?'HTTP 200':'Falha',good?'good':'critical')}</span><p>${num(r.records)} identidades · média ${num(m?.mean_ms)} ms<br>Erro ${pct(m?.error_pct)} · ${num(r.probe_ms)} ms no Admin</p></button>`;}).join('');
}
function incidents() {
 const choice=$('incident-status').value;
 const allowed=new Set(D.reporters.filter(r=>!selected||r.id===selected).map(r=>r.label));
 const rs=D.incidents.filter(i=>allowed.has(i.reporter)&&(choice==='all'||i.status!=='resolved')&&(choice!=='critical'||i.severity==='critical'));
 rs.sort((a,b)=>(a.severity==='critical'?-1:1)-(b.severity==='critical'?-1:1)||b.last_seen.localeCompare(a.last_seen));
 $('incident-rows').innerHTML=rs.length?rs.map(i=>`<tr><td>${status(label(i.severity),i.severity)}<small>${esc(label(i.status))} · ${i.confirmed?'persistência confirmada':'sinal provisório'}</small></td><td><strong>${esc(i.reporter)}</strong><small>${esc(label(i.rule))}</small>${i.endpoint&&D.latest.some(r=>r.entity_id===i.entity_id)?`<button class="cell-path" data-entity="${esc(i.entity_id)}">${esc(i.endpoint)}</button>`:i.endpoint?`<small>${esc(i.endpoint)} · sem observação atual</small>`:''}</td><td>${esc(i.evidence)}<small>Último sinal: ${dt(i.last_seen)}</small></td><td>${dt(i.opened_at)}</td><td>${num(i.samples)} detecções<small>${num(i.consecutive_samples)} consecutivas · recuperação ${num(i.recovery_samples)}/${D.rules.recovery_samples}</small></td></tr>`).join(''):'<tr><td colspan="5">'+empty('Nenhum incidente neste filtro.')+'</td></tr>';
}
function chart(target, series, unit, valueFormatter=num) {
 const all=series.flatMap(s=>s.points).filter(p=>p.y!=null&&Number.isFinite(p.y));
 if(!all.length) {target.innerHTML=empty('Ainda não há amostras válidas para esta série.');return;}
 const W=900,H=235,L=64,R=24,T=18,B=43, times=all.map(p=>Date.parse(p.x)), min=Math.min(...times),max=Math.max(...times), hi=Math.max(1,...all.map(p=>p.y))*1.12;
 const x=v=>L+(max===min?(W-L-R)/2:(Date.parse(v)-min)/(max-min)*(W-L-R)), y=v=>H-B-v/hi*(H-T-B);
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(unit)} ao longo das observações"><title>${esc(unit)} · valores detalhados nos pontos</title>`;
 for(let i=0;i<4;i++) {const v=hi*i/3;svg+=`<line x1="${L}" y1="${y(v)}" x2="${W-R}" y2="${y(v)}" stroke="#e9eef1"/><text class="axis" x="${L-9}" y="${y(v)+3}" text-anchor="end">${esc(valueFormatter(v))}</text>`;}
 const ticks=[min,...(max>min?[min+(max-min)/2,max]:[])];
 ticks.forEach(t=>{svg+=`<text class="axis" x="${x(new Date(t).toISOString())}" y="${H-12}" text-anchor="middle">${esc(new Date(t).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}))}</text>`;});
 series.forEach((s,i)=>{const color=colors[i%colors.length];let segments=[],segment=[],prev;
  for(const p of s.points) {if(p.y==null||!Number.isFinite(p.y)|| (prev && (Date.parse(p.x)-Date.parse(prev.x)>3.5*3600000 || (p.day&&prev.day&&p.day!==prev.day)))) {if(segment.length)segments.push(segment);segment=[];} if(p.y!=null&&Number.isFinite(p.y))segment.push(p);prev=p;}
  if(segment.length)segments.push(segment);
  segments.forEach(ps=>{svg+=`<polyline points="${ps.map(p=>x(p.x)+','+y(p.y)).join(' ')}" fill="none" stroke="${color}" stroke-width="2"/>`;});
  for(const p of s.points.filter(p=>p.y!=null&&Number.isFinite(p.y))) svg+=`<circle class="point" tabindex="0" cx="${x(p.x)}" cy="${y(p.y)}" r="${all.length>100?2:4}" fill="${color}"><title>${esc(s.name)} · ${dt(p.x)} · ${esc(valueFormatter(p.y))} ${esc(unit)}${p.note?' · '+esc(p.note):''}</title></circle>`;
 });
 target.innerHTML=svg+'</svg><div class="legend">'+series.map((s,i)=>`<span><i style="background:${colors[i%colors.length]}"></i>${esc(s.name)}</span>`).join('')+'</div>';
}
function trends() {
 const metric=$('trend-metric').value, unit=metric==='error_pct'?'%':metric==='mean_ms'?'ms':'chamadas';
 const ss=D.reporters.filter(r=>!selected||r.id===selected).map(r=>({name:r.label,points:D.runs.map(run=>{const p=D.observation_trends.find(t=>t.run_id===run.run_id&&t.reporter_id===r.id); const source=run.reports.find(s=>s.id===r.id);return {x:source?.observed_at||run.observed_at,y:p?.[metric]??null,day:new Date(source?.observed_at||run.observed_at).toLocaleDateString('en-CA',{timeZone:'America/Sao_Paulo'}),note:p?num(p.calls)+' chamadas no dia; cobertura pode variar':'sem cobertura'};})}));
 $('trend-note').textContent=D.runs.length<2?'Primeira observação: a série crescerá nas próximas execuções. Dias anteriores declarados não são usados como coletas nossas.':`${D.runs.length} ciclos retidos · linhas interrompidas em ausência, atraso >3,5h ou mudança de dia. Passe sobre um ponto para ler o valor.`;
 chart($('trend-chart'),ss,unit,v=>num(v,metric==='error_pct'?1:0));
 const ps=D.reporters.filter(r=>!selected||r.id===selected).map(r=>({name:r.label,points:D.runs.map(run=>{const p=run.reports.find(x=>x.id===r.id);return{x:p?.observed_at||run.observed_at,y:p?.probe_ms??null,note:'HTTP '+(p?.status||0)};})}));
 chart($('probe-chart'),ps,'ms',v=>num(v));
}
function endpoints() {
 const query=$('search').value.trim().toLowerCase(),family=$('family').value,sort=$('sort').value;
 visible=scoped().filter(r=>(!query||(r.endpoint+' '+r.reporter).toLowerCase().includes(query))&&(!family||r.family===family));
 visible.sort((a,b)=>sort==='path'?a.path.localeCompare(b.path):(b[sort]??-1)-(a[sort]??-1)||a.path.localeCompare(b.path));
 page=Math.min(page,Math.max(0,Math.ceil(visible.length/size)-1));
 $('endpoint-count').textContent=`${visible.length} ENDPOINTS NO FILTRO`;
 $('endpoint-rows').innerHTML=visible.slice(page*size,(page+1)*size).map(r=>`<tr><td><div class="cell-label">${esc(r.reporter)}</div><button class="cell-path" data-entity="${r.entity_id}">${esc(r.path)}</button><small>${esc(r.family)}</small></td><td>${num(r.calls)}</td><td>${num(r.errors)}<small>${pct(r.error_pct)}</small></td><td>${pct(r.rejection_pct)}<small>${num(r.rejections)} rejeições</small></td><td>${num(r.mean_ms)}<small>média, não p95</small></td><td>${pct(r.uptime==null?null:100*r.uptime)}</td><td>${r.fresh&&r.source_complete?status('Ciclo atual','good'):status('Métrica antiga / parcial','attention')}<small>${r.quality.length} ocorrência(s) · ${r.recurrent_days} dia(s) com erro ≥5%</small></td></tr>`).join('')||'<tr><td colspan="7">'+empty('Nenhum endpoint encontrado.')+'</td></tr>';
 $('page-note').textContent=visible.length?`${page*size+1}–${Math.min((page+1)*size,visible.length)} de ${visible.length} · clique no endpoint para investigar`:'Sem resultados';
 $('prev').disabled=page===0;$('next').disabled=(page+1)*size>=visible.length;
}
function probes() {
 $('probe-rows').innerHTML=reports().map(r=>`<tr><td><strong>${esc(r.label)}</strong><small>${esc(r.cnpj)}</small></td><td>${status('HTTP '+r.status,r.status===200?'good':'critical')}<small>${esc(label(r.coverage))}</small></td><td>${num(r.records)}<small>${r.probes.length} tentativa(s)</small></td><td>${dt(r.observed_at)}</td><td>${num(r.probe_ms)} ms<small>última tentativa, não tempo do ETL</small></td><td>${r.issues.length?r.issues.map(k=>esc(label(k))).join('<br>'):'Sem inconsistência de coleta detectada'}<small><a href="${esc(r.url)}" target="_blank" rel="noopener">Origem Admin ↗</a></small></td></tr>`).join('');
}
function counts(values) {const out={};for(const v of values)out[v]=(out[v]||0)+1;return Object.entries(out).sort((a,b)=>b[1]-a[1]);}
function quality() {
 const rs=scoped(), flags=counts(rs.flatMap(r=>r.quality));
 $('quality-total').textContent=`${rs.filter(r=>r.quality.length).length} ENDPOINTS COM OCORRÊNCIAS`;
 $('quality-rules').innerHTML=flags.map(([k,n])=>`<div class="quality-item"><span>${esc(label(k))}<small>${esc(k)}</small></span><b>${num(n)}</b></div>`).join('')||empty('Sem inconsistências detectadas no recorte.');
 $('interval-rules').innerHTML=counts(rs.map(r=>r.interval_state)).map(([k,n])=>`<div class="quality-item"><span>${esc(label(k))}</span><b>${num(n)}</b></div>`).join('');
}
function detail(id) {
 const r=D.latest.find(x=>x.entity_id===id);
 if(!r) return;
 $('detail-title').textContent=r.reporter+' · '+r.path;
 const own=D.points.filter(p=>p.entity_id===id), prev=D.reported_history.filter(p=>p.entity_id===id);
 $('detail-body').innerHTML=`<p class="dialog-note">Observado em ${dt(r.observed_at)} · ${r.fresh&&r.source_complete?'ciclo atual com cobertura conciliada':'contexto antigo ou parcial; excluído dos KPIs atuais'}. Dia de referência ${esc(r.day)} (${esc(r.day_basis)}).</p><div class="detail-grid">${[['Chamadas',num(r.calls)],['Erros',pct(r.error_pct)],['Média declarada',num(r.mean_ms)+' ms'],['Média histórica de referência',num(r.baseline_mean_ms)+' ms']].map(c=>`<div class="detail-stat"><small>${c[0]}</small>${c[1]}</div>`).join('')}</div><h3>Comparação com a observação anterior</h3><p class="dialog-note">${esc(label(r.interval_state))}. ${r.interval_state==='valid'?`${num(r.interval_calls)} novas chamadas · ${num(r.interval_errors)} erros · taxa ${pct(r.interval_error_pct)}.`:'Não há intervalo comparável para calcular taxa.'} Nenhuma média intervalar ou p95 é inferida.</p><h3>Taxa de erro nas observações próprias</h3><div id="detail-chart" class="chart"></div><h3>Dias anteriores declarados pelo banco</h3><p class="dialog-note">D−1 é ontem segundo a convenção de dia do reporte. Este histórico veio no payload atual e pode ser revisado pela origem; não representa nossas coletas passadas. Recorrência: ${r.recurrent_days} dia(s) com erro ≥5% e ≥100 chamadas.</p><div class="table-wrap"><table><thead><tr><th>Posição</th><th>Chamadas</th><th>Erros / taxa</th><th>Rejeição</th><th>Média (ms)</th></tr></thead><tbody>${prev.map(p=>`<tr><td>D−${p.position}</td><td>${num(p.calls)}</td><td>${num(p.errors)} / ${pct(p.calls>0&&p.errors!=null&&p.errors<=p.calls?100*p.errors/p.calls:null)}</td><td>${num(p.rejections)}</td><td>${num(p.mean_ms)}</td></tr>`).join('')||'<tr><td colspan="5">Sem histórico declarado.</td></tr>'}</tbody></table></div><h3>Qualidade e proveniência</h3><div class="pill-list">${r.quality.map(q=>status(label(q),'attention')).join('')||status('Sem flags detectadas','good')}</div><div class="evidence">Endpoint declarado: <code>${esc(r.endpoint)}</code><br>SHA-256 bronze: <code>${esc(r.source_sha)}</code><br>Caminho JSON: <code>${esc(r.json_path)}</code><br>requestTime bruto: <code>${esc(r.request_time)}</code><br>Diferença observada: ${num(r.clock_offset_seconds)} segundos<br>Uptime declarado: ${pct(r.uptime==null?null:r.uptime*100)} · downtime parcial: ${num(r.downtime_seconds)} s<br>TPS médio / pico declarados: ${num(r.average_tps)} / ${num(r.peak_tps)}</div>`;
 chart($('detail-chart'),[{name:r.reporter,points:own.map(p=>({x:p.observed_at,y:p.source_complete?p.error_pct:null,day:p.observed_at.slice(0,10),note:num(p.calls)+' chamadas'}))}],'%',v=>num(v,1));
 $('detail').showModal();$('close-detail').focus();
}
function render() {freshness();overview();incidents();trends();endpoints();probes();quality();}
$('reporter').addEventListener('change',()=>{selected=$('reporter').value;page=0;render();});
$('incident-status').addEventListener('change',incidents);$('trend-metric').addEventListener('change',trends);
for(const id of ['search','family','sort']) $(id).addEventListener(id==='search'?'input':'change',()=>{page=0;endpoints();});
$('prev').addEventListener('click',()=>{page--;endpoints();});$('next').addEventListener('click',()=>{page++;endpoints();});
document.addEventListener('click',event=>{const entity=event.target.closest('[data-entity]');if(entity)detail(entity.dataset.entity);const reporter=event.target.closest('[data-reporter]');if(reporter&&reporterIds.has(reporter.dataset.reporter)){selected=reporter.dataset.reporter;$('reporter').value=selected;page=0;render();}});
$('close-detail').addEventListener('click',()=>$('detail').close());$('detail').addEventListener('click',e=>{if(e.target===$('detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('export').addEventListener('click',()=>{const columns=['reporter','endpoint','observed_at','fresh','source_complete','day','calls','errors','error_pct','rejections','rejection_pct','mean_ms','uptime','interval_state','interval_calls','interval_errors','interval_error_pct','source_sha']; const cell=v=>'"'+String(v??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"';const csv='\ufeff'+[columns.join(';'),...visible.map(r=>columns.map(k=>cell(r[k])).join(';'))].join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));const a=document.createElement('a');a.href=url;a.download='admin-metrics-endpoints.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
const rules=D.rules;$('rule-summary').innerHTML=`<ul><li>Erro ≥${rules.error_attention_pct}% com ≥${num(rules.minimum_calls)} chamadas; crítico ≥${rules.error_critical_pct}% com ≥${num(rules.critical_minimum_calls)}.</li><li>Rejeição ≥${rules.rejection_attention_pct}% com ≥${num(rules.minimum_calls)} chamadas, sem inferência de causa.</li><li>Média ≥${num(rules.latency_attention_ms)} ms: atenção; ≥${num(rules.latency_critical_ms)} ms: crítico, com amostra mínima.</li><li>Regressão ≥${rules.regression_multiplier}× a mediana de pelo menos três médias diárias anteriores válidas.</li><li>Falha do Admin: atenção na primeira coleta e crítica na segunda consecutiva. Recuperação: ${rules.recovery_samples} amostras válidas.</li></ul>`;
$('build-info').textContent='v'+D.meta.version+' · '+D.meta.run_id;
render();setInterval(freshness,60000);
const nav=[...document.querySelectorAll('.nav-item')],sections=nav.map(a=>document.querySelector(a.getAttribute('href')));
function activeSection(){const edge=window.innerWidth<=900?150:90;let active=sections[0];for(const s of sections)if(s.getBoundingClientRect().top<=edge)active=s;for(const a of nav){const yes=a.hash==='#'+active.id;a.classList.toggle('active',yes);if(yes)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');}}
document.addEventListener('scroll',activeSection,{passive:true});window.addEventListener('resize',activeSection);activeSection();
})();
