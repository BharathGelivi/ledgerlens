'use strict';
const $ = id => document.getElementById(id);
const state = { data:null, page:1, total:0, view:'overview' };
const names = {S:'Completed',P:'Pending',D:'Denied',V:'Reversed'};
const classes = {S:'completed',P:'pending',D:'denied',V:'reversed'};
const number = n => Number(n).toLocaleString('en-IN');
function el(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function notify(text){$('notice').hidden=!text;$('notice').textContent=text;}
async function request(path,options={}){
  const response=await fetch(path,options);
  if(!response.ok){let detail='Request failed ('+response.status+')';try{const body=await response.json();if(typeof body.detail==='string')detail=body.detail;}catch{}throw new Error(detail);}
  return response.json();
}
function utc(value){return value?String(value).replace('T',' ').replace(/\.\d+.*$/,'').replace('+00:00',''):'—';}
function badge(text,kind){return el('span',text,'pill '+(kind||''));}
function setView(view){
  state.view=view;
  document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==view);
  document.querySelectorAll('.nav').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  $('breadcrumb').textContent='Workspace / '+({overview:'Overview',transactions:'Transactions',pipeline:'Pipeline & quality',learn:'How it works'}[view]);
  if(view==='transactions')loadTransactions().catch(e=>notify(e.message));
  if(view==='pipeline')loadIssues().catch(e=>notify(e.message));
}
function renderMetrics(data){
  const c=data.counts, metrics=[['Current records',c.payments,'Latest unambiguous states'],['Source payloads',c.raw_records,'Preserved unique source versions'],['Quarantined',c.quarantine,'Invalid rows retained for review'],['Ambiguous keys',c.conflicts,'Excluded from published totals']];
  $('metrics').replaceChildren(...metrics.map(([label,value,detail],i)=>{const node=el('div',undefined,'metric'+(i>1&&value?' attention':''));node.append(el('span',label,'metric-label'),el('b',number(value),'metric-value'),el('span',detail,'metric-detail'));return node;}));
}
function renderStatuses(data){
  const counts=Object.fromEntries(data.statuses.map(s=>[s.status,s.records])), total=data.counts.payments;
  $('status-list').replaceChildren(...['S','P','D','V'].map(status=>{const node=el('div',undefined,'status-item'),title=el('div',undefined,'status-title'),bar=el('div',undefined,'status-bar'),fill=el('span');title.append(el('span',names[status]),el('b',number(counts[status]||0)));fill.style.width=(total?(counts[status]||0)/total*100:0)+'%';bar.append(fill);node.append(title,bar);return node;}));
}
function svgNode(tag,attributes,text){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,value);if(text!==undefined)node.textContent=text;return node;}
function renderChart(){
  const currency=$('chart-currency').value, points=state.data.activity.filter(r=>r.currency===currency);
  $('chart').replaceChildren();
  if(!points.length){$('chart').append(el('p','No completed-activity groups for this currency.','muted'));return;}
  const width=650,height=210,left=65,right=20,top=15,bottom=35,values=points.map(p=>Number(p.completed_signed_amount));
  const low=Math.min(0,...values),high=Math.max(1,...values),range=high-low;
  const x=i=>left+i*(width-left-right)/Math.max(1,points.length-1), y=v=>top+(high-v)/range*(height-top-bottom);
  const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':`Signed completed activity in ${currency}, by UTC initiation date`});
  for(let i=0;i<=4;i++){const v=low+range*i/4;svg.append(svgNode('line',{x1:left,y1:y(v),x2:width-right,y2:y(v),stroke:'#e6ece6','stroke-width':1}),svgNode('text',{x:left-10,y:y(v)+3,'text-anchor':'end'},new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(v)));}
  svg.append(svgNode('text',{x:left,y:9},currency),svgNode('text',{x:width-right,y:height,'text-anchor':'end'},'Initiation date · UTC'));
  const d=points.map((p,i)=>(i?'L':'M')+x(i)+' '+y(Number(p.completed_signed_amount))).join(' ');
  svg.append(svgNode('path',{d,fill:'none',stroke:'#186960','stroke-width':2.5}));
  points.forEach((p,i)=>{const circle=svgNode('circle',{cx:x(i),cy:y(Number(p.completed_signed_amount)),r:3,fill:'#186960'});circle.append(svgNode('title',{},`${p.activity_date_utc}: ${p.completed_signed_amount} ${currency}`));svg.append(circle);if(points.length<=6||i===0||i===points.length-1||i===Math.floor(points.length/2))svg.append(svgNode('text',{x:x(i),y:height-17,'text-anchor':'middle'},p.activity_date_utc.slice(5)));});
  $('chart').append(svg);$('chart-range').textContent=points[0].activity_date_utc+' — '+points.at(-1).activity_date_utc;
}
function renderRuns(data){
  $('run-rows').replaceChildren(...data.runs.map(run=>{const tr=el('tr'),source=el('td',run.run_id);source.append(el('small',run.source));const status=el('td');status.append(badge(run.status,run.status==='failed'?'failed':''));tr.append(source,status,el('td',number(run.input_records),'number'),el('td',run.new_unique_records===undefined?'—':number(run.new_unique_records),'number'),el('td',run.replayed_or_duplicate_records===undefined?'—':number(run.replayed_or_duplicate_records),'number'),el('td',run.elapsed_seconds+' s','number'));return tr;}));
  $('test-list').replaceChildren(...data.tests.map(test=>{const node=el('div',undefined,'test-item');node.append(el('span',test.name.replaceAll('_',' ')),badge(test.status,test.status==='pass'?'':'failed'));return node;}));
  if(!data.tests.length)$('test-list').append(el('p','Run the pipeline to publish test evidence.','muted small'));
  $('replay').disabled=data.job.running;$('replay').textContent=data.job.running?'Refresh in progress…':'Replay latest input ↻';
}
async function loadWorkspace(){
  const data=await request('/workspace');state.data=data;
  const previousCurrency=$('chart-currency').value;
  $('dataset').textContent=data.dataset==='synthetic'?'Synthetic demonstration':'External dataset · verify source';$('dataset').className='badge'+(data.dataset==='synthetic'?' warn':'');
  $('chart-currency').replaceChildren(...data.currencies.map(r=>new Option(r.currency,r.currency)));
  if(data.currencies.some(r=>r.currency===previousCurrency))$('chart-currency').value=previousCurrency;
  else if(data.currencies.some(r=>r.currency==='USD'))$('chart-currency').value='USD';
  const selected=$('currency').value;$('currency').replaceChildren(new Option('All currencies',''),...data.currencies.map(r=>new Option(r.currency,r.currency)));$('currency').value=selected;
  $('ai-state').textContent=data.ai_connected?'Cloud AI configured · one call per question':'SQL evidence mode · AI not connected';
  $('ai-state').className='badge'+(data.ai_connected?'':' warn');
  $('published-at').textContent=data.published_run?'Published '+utc(data.published_run.started_at)+' UTC':'';
  renderMetrics(data);renderStatuses(data);renderChart();renderRuns(data);
  if(data.job.error)notify(data.job.error);else if(!data.job.running)notify('');
  if(state.view==='transactions')await loadTransactions();if(state.view==='pipeline')await loadIssues();
  if(data.job.running)setTimeout(()=>loadWorkspace().catch(e=>notify(e.message)),1800);
}
async function loadTransactions(){
  const query=new URLSearchParams({search:$('search').value,status:$('status').value,currency:$('currency').value,page:state.page});
  const result=await request('/transactions?'+query);state.total=result.total;
  $('record-count').textContent=number(result.total)+' matching records';$('page-label').textContent='Page '+state.page+' of '+Math.max(1,Math.ceil(result.total/30));
  $('previous').disabled=state.page<=1;$('next').disabled=state.page*30>=result.total;
  $('transaction-rows').replaceChildren(...result.rows.map(row=>{const tr=el('tr'),id=el('td',row.transaction_id);id.append(el('small',row.event_code));const status=el('td');status.append(badge(names[row.status],classes[row.status]));const action=el('td'),button=el('button','Trace ↗','trace-button');button.setAttribute('aria-label','Trace '+row.transaction_id+' '+row.event_code);button.onclick=()=>showTrace(row).catch(e=>notify(e.message));action.append(button);tr.append(id,status,el('td',row.amount+' '+row.currency,'number'),el('td',utc(row.updated_at)),action);return tr;}));
  if(!result.rows.length){const row=el('tr'),cell=el('td','No current records match these filters.');cell.colSpan=5;row.append(cell);$('transaction-rows').append(row);}
}
async function showTrace(row){
  const data=await request('/trace?'+new URLSearchParams({transaction_id:row.transaction_id,event_code:row.event_code}));
  $('trace-title').textContent=row.transaction_id+' / '+row.event_code;$('trace-meaning').textContent=data.conflicts.length?'Conflicting latest values: this key is excluded from current records and totals. '+data.meaning:data.meaning;
  $('version-list').replaceChildren(...data.versions.map(version=>{const li=el('li');li.append(badge(names[version.status],classes[version.status]),el('p',utc(version.updated_at)+' UTC · '+version.amount+' '+version.currency),el('span','Observed '+version.times_observed+' times · fingerprint '+version.record_hash.slice(0,16)));return li;}));
  $('trace-json').textContent=JSON.stringify(data,null,2);$('trace-panel').hidden=false;$('trace-panel').focus();$('trace-panel').scrollIntoView({behavior:'smooth',block:'nearest'});
}
async function loadIssues(){
  const data=await request('/issues'),nodes=[];
  for(const row of data.conflicts){const node=el('div',undefined,'issue'),button=el('button','Inspect conflicting versions ↗','suggestion');button.onclick=()=>{setView('transactions');showTrace(row).catch(e=>notify(e.message));};node.append(el('b','Ambiguous latest value'),el('p',row.transaction_id+' / '+row.event_code+' · '+row.conflicting_versions+' versions'),button);nodes.push(node);}
  for(const row of data.quarantine){const node=el('div',undefined,'issue');node.append(el('span',row.reason),el('small',row.record_hash));nodes.push(node);}
  if(!nodes.length)nodes.push(el('p','No quarantined records or ambiguous latest keys in the published dataset.','muted small'));
  $('issue-list').replaceChildren(...nodes);
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>setView(b.dataset.go));
$('reload').onclick=()=>loadWorkspace().catch(e=>notify(e.message));$('chart-currency').onchange=renderChart;
$('filter-form').onsubmit=e=>{e.preventDefault();state.page=1;loadTransactions().catch(e=>notify(e.message));};
$('previous').onclick=()=>{state.page--;loadTransactions().catch(e=>notify(e.message));};$('next').onclick=()=>{state.page++;loadTransactions().catch(e=>notify(e.message));};
$('close-trace').onclick=()=>$('trace-panel').hidden=true;
$('replay').onclick=async()=>{try{$('replay').disabled=true;const result=await request('/replay',{method:'POST',headers:{'X-LedgerLens':'workspace'}});notify(result.message);await loadWorkspace();}catch(e){notify(e.message);$('replay').disabled=false;}};
document.querySelectorAll('.suggestion').forEach(b=>b.onclick=()=>{$('question').value=b.textContent;$('question').focus();});
$('ask-form').onsubmit=async e=>{e.preventDefault();$('ask-button').disabled=true;$('ask-button').textContent='Investigating…';try{const result=await request('/investigate',{method:'POST',headers:{'Content-Type':'application/json','X-LedgerLens':'workspace'},body:JSON.stringify({question:$('question').value})});$('answer').hidden=false;$('answer-mode').textContent=result.mode==='cloud-ai'?'AI EXPLANATION · VERIFY AGAINST EVIDENCE':'SQL EVIDENCE · NO AI CALL MADE';$('answer-text').textContent=result.answer;$('answer-evidence').textContent=JSON.stringify(result.evidence,null,2);}catch(error){notify(error.message);}finally{$('ask-button').disabled=false;$('ask-button').textContent='Investigate ↗';}};
loadWorkspace().catch(e=>notify(e.message));
