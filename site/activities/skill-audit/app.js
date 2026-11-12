'use strict';
const owners={judge:'评测判定',tool:'工具',execution:'执行',model_api:'模型接口',runtime:'运行时 / 权限',unknown:'尚不确定'};
let active='all',rows=[];
const search=document.querySelector('#case-search'),list=document.querySelector('#case-list');
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function pretty(v){if(typeof v==='string'){try{return JSON.stringify(JSON.parse(v),null,2);}catch{return v;}}return JSON.stringify(v,null,2);}
function code(v){return node('pre',pretty(v),'evidence-code');}
function fold(title,child,open=false){const d=node('details',undefined,'evidence-fold');d.append(node('summary',title));const b=node('div',undefined,'fold-body');b.append(child);d.append(b);d.open=open;return d;}
function field(container,label,value){if(value===undefined||value===null)return;container.append(node('dt',label));const dd=node('dd');if(Array.isArray(value)){const ul=node('ul');for(const x of value)ul.append(node('li',typeof x==='object'?pretty(x):String(x)));dd.append(ul);}else dd.textContent=typeof value==='object'?pretty(value):String(value);container.append(dd);}
function applyFilter(){const q=search.value.trim().toLowerCase();let count=0;for(const r of rows){const show=(active==='all'||r.dataset.owner===active)&&r.dataset.search.toLowerCase().includes(q);r.hidden=!show;if(show)count++;}document.querySelector('#result-count').textContent=count+' 条';document.querySelector('#empty').hidden=count>0;document.querySelectorAll('[data-filter]').forEach(b=>{const on=b.dataset.filter===active;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));});}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.filter;applyFilter();}));
document.querySelectorAll('[data-owner-filter]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.ownerFilter;search.value='';applyFilter();document.querySelector('#catalog').scrollIntoView();}));
search.addEventListener('input',applyFilter);
const themeButton=document.querySelector('#theme-toggle');
function theme(mode){document.documentElement.dataset.theme=mode;themeButton.textContent=mode==='dark'?'浅色':'深色';themeButton.setAttribute('aria-label',mode==='dark'?'切换浅色模式':'切换深色模式');}
let saved=null;try{saved=localStorage.getItem('benchlibrary-audit-theme')}catch{}
theme(saved==='dark'?'dark':'light');
themeButton.addEventListener('click',()=>{const mode=document.documentElement.dataset.theme==='dark'?'light':'dark';theme(mode);try{localStorage.setItem('benchlibrary-audit-theme',mode)}catch{}});
const labels={issue_title:'问题标题',primary_owner:'首要责任',confidence:'置信度（审阅原文）',historical_fail_is_supported:'历史 Fail 是否得到支持',skill_only_fix_supported:'是否支持仅修改 Skill',concrete_root_cause:'具体根因',earliest_deviation:'最早偏离点',expected_behavior:'期望行为',actual_behavior:'实际行为',skill_clause:'对应 Skill 条款',evidence_paths:'证据位置',alternative_explanations:'替代解释与反证',proposed_minimal_skill_change:'Skill 修改建议',regression_assertions:'回归断言',protected_normal_behavior:'需要保护的正常行为',uncertainties:'尚未解决的问题'};
function diagnosisView(d){const dl=node('dl',undefined,'diagnosis');for(const [key,value]of Object.entries(d)){if(key==='case_id')continue;field(dl,labels[key]||key,value);}return dl;}
function trajectoryView(t){
 const wrap=node('div',undefined,'trajectory');
 wrap.append(node('p',t.message_reconstruction||'本页按结构化轨迹展示。','caption'));
 let previous=[];
 for(const event of t.events){
  const main=event.kind==='main_llm',body=node('div');
  const identity=event.input?.tool_code||event.input?.tool_name||event.model||event.kind;
  const title='#'+event.event_index+' · '+(main?'模型请求':event.kind==='skill_load'?'加载 Skill':'工具调用')+' · '+(typeof identity==='object'?pretty(identity):identity);
  const meta=node('dl',undefined,'event-meta');
  field(meta,'事件路径',event.source_span_path);
  if(main){
   field(meta,'模型记录',event.model);field(meta,'场景',event.scene);
   const prefix=event.message_common_prefix_with_previous_main;
   if(!Number.isInteger(prefix)||prefix<0||prefix>previous.length){
    body.append(node('p','消息恢复失败：公共前缀范围异常；保留原始事件供核对。','error'));previous=[];
   }else{
    const messages=previous.slice(0,prefix).concat(event.message_tail||[]);previous=messages;
    const msgs=node('div',undefined,'messages');
    for(const [i,m]of messages.entries()){const item=node('div',undefined,'message');item.append(node('h4',String(i)+' · '+String(m.role||m.type||'message')),code(m));msgs.append(item);}
    body.append(fold('模型输入上下文 · '+messages.length+' 条消息（恢复公共前缀）',msgs));
   }
  }else if(event.input!==undefined)body.append(fold('完整调用输入',code(event.input),true));
  body.prepend(meta);
  body.append(fold('完整调用输出 / 错误',code(event.output),true));
  const out=event.output;
  if(out&&typeof out==='object')for(const k of ['app_state','output_json'])if(typeof out[k]==='string'&&out[k]){try{body.append(fold(k+' · JSON 解码视图',code(JSON.parse(out[k]))));}catch{}}
  body.append(fold('该事件原始 JSON',code(event)));
  wrap.append(fold(title,body));
 }
 return wrap;
}
async function loadCase(row,item,body){
 if(row.dataset.loaded==='true'||row.dataset.loading==='true')return;
 row.dataset.loading='true';body.replaceChildren(node('p','正在加载完整证据…','loading'));
 try{
  const res=await fetch('cases/'+item.file,{credentials:'omit'});if(!res.ok)throw Error('HTTP '+res.status);
  const bytes=await res.arrayBuffer();
  if(bytes.byteLength!==item.bytes)throw Error('案例字节数不匹配');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
  if(hash!==item.sha256)throw Error('案例 SHA-256 不匹配');
  const data=JSON.parse(new TextDecoder().decode(bytes));
  if(data.case_id!==item.case_id||data.display_id!==item.id)throw Error('案例身份不匹配');
  body.replaceChildren();
  const links=node('div',undefined,'case-actions');
  const direct=node('a','此案例直达链接');direct.href='#case-'+item.id;
  const download=node('a','下载本案例完整 JSON');download.href='cases/'+item.file;download.download=item.id+'.json';
  links.append(direct,download);body.append(links);
  const intro=node('dl',undefined,'diagnosis');field(intro,'原始案例编号',data.case_id);field(intro,'原始提问',data.trajectory.source_query);
  field(intro,'首要责任',owners[item.owner]);field(intro,'置信度',data.diagnosis.confidence);field(intro,'具体根因',data.diagnosis.concrete_root_cause);
  body.append(intro);
  body.append(fold('完整诊断 · 现象、根因、条款、反证与回归断言',diagnosisView(data.diagnosis),true));
  body.append(fold('历史回答 · 完整原文',code(data.trajectory.historical_answer)));
  const judges=node('div',undefined,'judges');
  for(const[id,value]of Object.entries(data.historical_machine_evaluation.labels||{})){
   const j=node('section',undefined,'judge-rule');j.append(node('h4','原评测规则 '+id),code(value));judges.append(j);
  }
  body.append(fold('历史评测 · 全部标签和理由（不视为真值）',judges));
  body.append(fold('执行轨迹 · 全部 '+data.trajectory.events.length+' 个业务事件',trajectoryView(data.trajectory)));
  if(data.adjudicated)body.append(fold('初次诊断 · 保留后续裁定前的原记录',diagnosisView(data.initial_diagnosis)));
  body.append(fold('来源校验与提取范围',code({provenance:data.source_provenance,publication_note:data.publication_note,message_reconstruction:data.trajectory.message_reconstruction})));
  body.append(fold('完整材料 · JSON 原文',code(data)));
  row.dataset.loaded='true';
 }catch(e){const p=node('p','证据加载失败：'+e.message+'。案例仍保留在统计分母中。','error');const b=node('button','重新加载','chip');b.addEventListener('click',()=>loadCase(row,item,body));body.replaceChildren(p,b);}
 finally{delete row.dataset.loading;}
}
function jump(){const id=location.hash.slice(1);const target=document.getElementById(id);if(target&&target.classList.contains('case-row')){active='all';search.value='';applyFilter();target.open=true;target.scrollIntoView({block:'start'});}}
async function init(){
 try{
  const res=await fetch('cases/index.json',{credentials:'omit'});if(!res.ok)throw Error('HTTP '+res.status);
  const data=await res.json();if(data.total_cases!==43||data.cases.length!==43)throw Error('案例数量不符');
  list.replaceChildren();
  for(const item of data.cases){
   const row=node('details',undefined,'case-row full-case');row.id='case-'+item.id;row.dataset.owner=item.owner;row.dataset.search=[item.id,item.case_id,item.title,item.query,item.root_cause,owners[item.owner]].join(' ');
   const summary=node('summary');summary.append(node('span',item.id+' · '+owners[item.owner]+' · '+item.events+' 个事件','case-meta'),node('h3',item.title),node('p',item.query,'case-query'));
   const verdict=node('span',item.historical_fail_is_supported?'历史异常有证据支持':'历史异常需复核','verdict');
   summary.append(verdict,node('span','展开完整案例 ＋','expand'));
   const body=node('div',undefined,'full-case-body');row.append(summary,body);row.addEventListener('toggle',()=>{if(row.open)loadCase(row,item,body);});list.append(row);
  }
  rows=[...list.children];applyFilter();jump();window.addEventListener('hashchange',jump);
 }catch(e){list.replaceChildren(node('p','案例列表读取失败：'+e.message+'。请刷新重试。','error'));}
}
init();
