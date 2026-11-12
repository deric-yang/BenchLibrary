
(()=>{'use strict';
const NS='http://www.w3.org/2000/svg',cache=new Map(),statusNames={observed:'可见证据',inferred:'推断',unresolved:'上游未证实'};
function e(tag,text,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x}
const json=v=>typeof v==='string'?v:JSON.stringify(v,null,2);
const pre=v=>e('pre',json(v),'atlas-raw');
function btn(text,fn,cls='atlas-button'){const b=e('button',text,cls);b.type='button';b.addEventListener('click',fn);return b}
function modal(title,content){const d=e('dialog',undefined,'atlas-dialog');const h=e('header');h.append(e('h3',title),btn('关闭',()=>d.close()));d.append(h,content);document.body.append(d);d.addEventListener('close',()=>d.remove());d.showModal();return d}
function unpack(bundle){if(bundle.format!=='trace-atlas-strings-v1')throw Error('未知 Atlas 数据格式');function f(v){if(v&&typeof v==='object'&&!Array.isArray(v)){if(Object.keys(v).length===1&&Number.isInteger(v.$atlasString))return bundle.strings[v.$atlasString];return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,f(x)]));}return Array.isArray(v)?v.map(f):v;}return f(bundle.data)}
async function load(item){if(cache.has(item.id))return cache.get(item.id);const pin=item.atlas;if(!pin)throw Error('源材料未提供 Atlas 索引');const r=await fetch('cases/'+pin.file,{credentials:'omit'});if(!r.ok)throw Error('HTTP '+r.status);const bytes=await r.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');if(hash!==pin.sha256||bytes.byteLength!==pin.bytes)throw Error('Atlas 数据完整性不符');const d=unpack(JSON.parse(new TextDecoder().decode(bytes)));if(d.displayId!==item.id)throw Error('案例身份不符');cache.set(item.id,d);while(cache.size>2)cache.delete(cache.keys().next().value);return d;}
window.mountTraceAtlas=async function(host,item){host.append(e('p','正在读取完整 Trace 的调用与上下文…','atlas-loading'));try{const d=await load(item);if(!host.isConnected)return;draw(host,d);host.dataset.atlasReady=item.id;}catch(err){if(host.isConnected){host.replaceChildren(e('p','轨迹不可用：'+err.message+'。源案例仍保留。','unavailable'),btn('重试',()=>{host.replaceChildren();window.mountTraceAtlas(host,item)}));host.dataset.atlasError=err.message;}}};
function draw(host,d){
 host.replaceChildren();host.classList.add('atlas');const calls=[...d.calls,...d.unconfirmed].sort((a,b)=>a.start-b.start),byId=new Map(calls.map(c=>[c.id,c])),scopeIds=[...new Set(calls.map(c=>c.loop?.scopeId).filter(Boolean))];
 let pinned=(calls.find(c=>c.scene==='main_agent_loop_team'&&c.id.startsWith('N'))||calls[0]).id,current=pinned;
 const loopName=c=>c.loop?'作用域 '+(scopeIds.indexOf(c.loop.scopeId)+1)+' · '+c.loop.name:'辅助 / 无 Loop 祖先';
 const summary=e('div',undefined,'atlas-summary');const text=e('div');text.append(e('h3','Trace Atlas · '+d.displayId),e('p',d.counts.llmObservations+' 个 LLM Span · '+d.counts.confirmed+' 次确认生成 · '+d.counts.unconfirmed+' 个未确认观测','caption'));
 const full=btn('全屏对照',()=>{const marker=document.createComment('atlas-place');host.before(marker);full.hidden=true;const dialog=e('dialog',undefined,'atlas-fullscreen');host.classList.add('is-fullscreen');const close=btn('退出全屏',()=>dialog.close(),'atlas-button atlas-close-full');dialog.append(close,host);document.body.append(dialog);dialog.addEventListener('close',()=>{marker.replaceWith(host);full.hidden=false;host.classList.remove('is-fullscreen');dialog.remove();scheduleLines();},{once:true});dialog.showModal();scheduleLines();});summary.append(text,full);host.append(summary);
 const stage=e('div',undefined,'atlas-stage'),nodes=e('nav',undefined,'atlas-nodes');nodes.setAttribute('aria-label','实际模型请求与生成节点');const svg=document.createElementNS(NS,'svg');svg.classList.add('atlas-lines');svg.setAttribute('aria-hidden','true');
 const connection=e('div',undefined,'atlas-connections'),legend=e('span','读取关系汇总 →','atlas-connection-label');connection.append(legend);const groupButtons=new Map();
 for(const l of d.layers){const b=btn(l.id+' 0',()=>{const g=left.querySelector('[data-layer="'+l.id+'"]');if(g)g.scrollIntoView({block:'nearest'});},'atlas-group-key');b.dataset.layer=l.id;connection.append(b);groupButtons.set(l.id,b);}
 const bodies=e('div',undefined,'atlas-body'),left=e('section',undefined,'atlas-contexts'),right=e('section',undefined,'atlas-output');left.setAttribute('aria-label','本节点实际读取的上下文');right.setAttribute('aria-label','所选节点模型原始输出');bodies.append(left,right);stage.append(nodes,svg,connection,bodies);host.append(stage);
 const state=e('p',undefined,'atlas-state');const clear=btn('取消固定',()=>{pinned=null;state.textContent='未固定 · 悬停或聚焦预览，点击固定。';mark();});const actions=e('div',undefined,'atlas-actions');actions.append(state,clear);host.append(actions);
 const buttons=new Map();
 for(const c of calls){const b=e('button',undefined,'atlas-node '+(c.id.startsWith('U')?'unconfirmed':''));b.dataset.call=c.id;b.type='button';b.append(e('span',c.id+' · '+(c.id.startsWith('U')?'未确认':'已确认'),'atlas-node-id'),e('strong',c.title),e('small',c.providerModel||'实际模型未提供'),e('span',loopName(c),'atlas-loop'));
  b.title=c.title+'\n'+loopName(c)+'\n'+(c.duration==null?'耗时未知':c.duration.toFixed(3)+' 秒')+' · '+c.start.toFixed(3)+' 秒开始';
  b.addEventListener('pointerenter',()=>show(c.id));b.addEventListener('focus',()=>show(c.id));b.addEventListener('click',()=>{pinned=c.id;show(c.id);});
  b.addEventListener('keydown',ev=>{if(ev.key==='Escape'){pinned=null;mark();state.textContent='已取消固定';}});buttons.set(c.id,b);nodes.append(b);
 }
 nodes.addEventListener('pointerleave',()=>{if(pinned)show(pinned)});
 function mark(){for(const [id,b]of buttons){b.classList.toggle('active',id===current);b.classList.toggle('pinned',id===pinned);b.setAttribute('aria-pressed',String(id===pinned));}}
 function show(id){const c=byId.get(id);current=id;host.dataset.activeCall=id;mark();state.textContent=(id===pinned?'已固定 ':'预览 ')+id+' · 点击节点固定，悬停临时查看。';left.replaceChildren();right.replaceChildren();
  const ctx=d.contexts.filter(x=>x.readers.includes(id));left.append(e('h4','实际读取的上下文 · '+ctx.length+' 个片段'));
  if(!ctx.length)left.append(e('p',c.inputSource==='unavailable'?'不可用：源记录未提供本节点输入。':'源记录未提供可分类的消息 / 工具定义。','unavailable'));
  for(const layer of d.layers){const group=ctx.filter(x=>x.layer===layer.id),b=groupButtons.get(layer.id);b.textContent=layer.id+' '+group.length;b.disabled=!group.length;b.title=layer.title+' · 本节点读取 '+group.length+' 个片段';if(!group.length)continue;
   const section=e('section',undefined,'atlas-context-group');section.dataset.layer=layer.id;section.append(e('h5',layer.id+' · '+layer.title));
   for(const x of group){const card=e('button',undefined,'atlas-context-card');card.type='button';card.dataset.context=x.id;
    card.append(e('strong',x.title),e('span',x.id+' · '+statusNames[x.source.status]+' · '+(x.stability==='fixed'?'固定':x.stability==='mixed'?'混合':'动态'),'atlas-context-meta'),e('span',x.roles.join(' / ')+' · 首次可见 '+x.firstSeen,'atlas-context-meta'),e('span',x.text||'空单元 · 原记录为空','atlas-context-preview'));
    card.addEventListener('click',()=>{const body=e('div');body.append(e('p',x.source.label),e('p',x.source.detail),e('p','作用范围：'+x.lifetime+'；读取节点：'+x.readers.join('、')),pre(x.text),e('h4','精确输入位置与来源引用'),pre({source:x.source,occurrences:x.occurrences}));modal(x.id+' · '+x.title,body);});section.append(card);
   }left.append(section);
  }
  right.append(e('h4',id+' · 模型原始输出'),e('p',c.purpose,'caption'),e('span',loopName(c),'atlas-loop'));
  const meta=e('dl',undefined,'atlas-meta');for(const [label,value]of [['请求模型',c.model],['SDK 模型',c.sdkModel],['返回模型',c.providerModel],['耗时',c.duration==null?'未知':c.duration.toFixed(3)+' 秒'],['输入来源',c.inputSource],['输出来源',c.outputSource]]){meta.append(e('dt',label),e('dd',value==null?'源记录未提供':String(value)));}const metaFold=e('details',undefined,'atlas-model-details');metaFold.append(e('summary','模型与参数 · 展开核验'),meta);
  if(c.uncertainty)right.append(e('p',c.uncertainty,'unavailable'));
  right.append(e('p',c.providerModel||'实际返回模型：源记录未提供','atlas-actual-model'));const out=c.output||{};if(out.text)right.append(pre(out.text));
  if(out.tool_calls?.length){right.append(e('h5','原始工具调用'),pre(out.tool_calls));}
  if(!out.text&&!out.tool_calls?.length)right.append(e('p',c.id.startsWith('U')?'未取得可确认生成内容；错误与响应证据如下。':'源记录未提供文本或工具调用内容；不等同于模型输出为空。','unavailable'),pre(c.rawOutput));
  const controls=e('div',undefined,'atlas-output-actions');controls.append(btn('完整模型输入',()=>modal(id+' · 完整请求',pre(c.inputSource==='unavailable'?{unavailable:true,reason:'源记录未提供请求',evidence:c.evidence}:c.input))),btn('完整模型输出',()=>modal(id+' · 原始响应',pre({output:c.output,rawOutput:c.rawOutput,usage:c.usage,responseId:c.responseId,outputSource:c.outputSource,evidence:c.evidence}))),btn('模型 / Loop 证据',()=>modal(id+' · 调用证据',pre({spanId:c.spanId,observations:c.observations,loop:c.loop,requestModel:c.model,sdkModel:c.sdkModel,actualModel:c.providerModel,usage:c.usage,confirmation:c.confirmation,evidence:c.evidence}))));right.append(metaFold,controls);
  left.scrollTop=0;right.scrollTop=0;scheduleLines();
 }
 let frame;function scheduleLines(){if(frame)cancelAnimationFrame(frame);frame=requestAnimationFrame(lines);}
 function lines(){if(!host.isConnected)return;svg.replaceChildren();const sr=stage.getBoundingClientRect();svg.setAttribute('viewBox','0 0 '+sr.width+' '+sr.height);const nr=buttons.get(current).getBoundingClientRect(),nrAll=nodes.getBoundingClientRect();const x=Math.max(8,Math.min(sr.width-8,nr.left+nr.width/2-sr.left)),y=nrAll.bottom-sr.top;
  for(const b of groupButtons.values()){if(b.disabled)continue;const r=b.getBoundingClientRect();const path=document.createElementNS(NS,'path');path.setAttribute('d','M '+x+' '+y+' Q '+x+' '+(y+12)+' '+(r.left+r.width/2-sr.left)+' '+(r.top-sr.top));svg.append(path);}
 }
 nodes.addEventListener('scroll',scheduleLines,{passive:true});left.addEventListener('scroll',scheduleLines,{passive:true});const resize=new ResizeObserver(scheduleLines);resize.observe(stage);host.atlasCleanup=()=>{resize.disconnect();if(frame)cancelAnimationFrame(frame);};
 // Auxiliary tables are collapsed; the three principal panes remain together.
 const more=e('div',undefined,'atlas-evidence');
 function fold(title,make){const f=e('details',undefined,'evidence-fold'),s=e('summary',title),body=e('div',undefined,'fold-body');f.append(s,body);let done=false;f.addEventListener('toggle',()=>{if(f.open&&!done){done=true;body.append(make());}});more.append(f);return f}
 fold('调用清单 · 包含失败与辅助生成',()=>{const box=e('div',undefined,'atlas-table-wrap'),t=e('table');const head=e('tr');for(const label of ['节点','场景 / 用途','实际模型','Loop','开始 / 耗时'])head.append(e('th',label));t.append(head);for(const c of calls){const r=e('tr'),td=e('td');td.append(btn(c.id,()=>{pinned=c.id;show(c.id);buttons.get(c.id).scrollIntoView({block:'nearest',inline:'center'});stage.scrollIntoView({block:'nearest'});}));r.append(td,e('td',c.title),e('td',c.providerModel||'未提供'),e('td',loopName(c)),e('td',c.start.toFixed(3)+'s / '+(c.duration==null?'未知':c.duration.toFixed(3)+'s')));t.append(r);}box.append(t);return box});
 fold('上下文矩阵 · 精确读取关系',()=>{const box=e('div',undefined,'atlas-table-wrap'),t=e('table'),head=e('tr');head.append(e('th','内容片段'),...calls.map(c=>e('th',c.id)));t.append(head);for(const x of d.contexts){const r=e('tr');r.append(e('th',x.id+' '+x.layer+' '+x.title),...calls.map(c=>e('td',x.readers.includes(c.id)?(x.firstSeen===c.id?'首次':'●'):'—')));t.append(r);}box.append(t);return box});
 fold('完整 Span 树 · '+d.spans.length+' 个节点',()=>{const map=new Map(d.spans.map(s=>[s.id,s]));function tree(s){const f=e('details',undefined,'atlas-span');f.append(e('summary',s.code+' · '+s.name+' · '+s.id));let built=false;f.addEventListener('toggle',()=>{if(!f.open||built)return;built=true;f.append(btn('查看此 Span 原文',()=>modal(s.code+' · '+s.name,pre(s))));for(const id of s.children){if(map.has(id))f.append(tree(map.get(id)));}});return f}const box=e('div');for(const s of d.spans.filter(s=>!s.parent))box.append(tree(s));return box});
 fold('事实口径、来源与未证实项',()=>{const box=e('div');for(const n of [...d.notes,...d.warnings])box.append(e('p',n));box.append(pre({sourceArchiveSha256:d.sourceArchiveSha256,normalizedSourceSha256:d.sha256,counts:d.counts,businessEventCount:d.businessEventCount,businessModelRequestCount:d.businessModelRequestCount,structuralLLMWrappers:d.structuralLLMWrappers}));return box});
 host.append(more);show(pinned);
}
})();
