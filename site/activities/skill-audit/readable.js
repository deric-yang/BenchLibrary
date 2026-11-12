'use strict';
window.SkillAuditReadable=(()=>{
 const e=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n};
 const fold=(title,body,cls='')=>{const d=e('details',undefined,'evidence-fold '+cls);d.append(e('summary',title),body);return d};
 const safeUrl=s=>{try{const u=new URL(s);return ['http:','https:'].includes(u.protocol)?u.href:null}catch{return null}};
 function inline(n,s){
  const re=/(!?\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*|\x60([^\x60]+)\x60)/g;let end=0;
  for(const m of s.matchAll(re)){n.append(document.createTextNode(s.slice(end,m.index)));
   if(m[2]!==undefined){const href=safeUrl(m[3]);if(href){const a=e('a',(m[0][0]==='!'?'原始附件：':'')+(m[2]||'链接'));a.href=href;a.target='_blank';a.rel='noopener noreferrer';n.append(a)}else n.append(document.createTextNode(m[0]))}
   else n.append(e(m[4]?'strong':'code',m[4]||m[5]));end=m.index+m[0].length;
  }n.append(document.createTextNode(s.slice(end)));
 }
 function table(columns,rows){const wrap=e('div',undefined,'business-table-wrap'),t=e('table',undefined,'business-table'),h=e('thead'),hr=e('tr'),body=e('tbody');for(const c of columns)hr.append(e('th',c));h.append(hr);t.append(h,body);for(const row of rows){const r=e('tr');for(const c of row){const td=e('td');inline(td,String(c??''));r.append(td)}body.append(r)}wrap.append(t);return wrap}
 function markdown(s){const box=e('div',undefined,'business-prose'),lines=String(s||'').replace(/\r/g,'').split('\n');let i=0;
  while(i<lines.length){const line=lines[i];if(!line.trim()){i++;continue}
   if(i+1<lines.length&&line.includes('|')&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){const cells=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(v=>v.trim());const head=cells(line),rows=[];i+=2;while(i<lines.length&&lines[i].includes('|'))rows.push(cells(lines[i++]));box.append(table(head,rows));continue}
   if(/^\s*---+\s*$/.test(line)){box.append(e('hr'));i++;continue}
   const h=line.match(/^#{1,6}\s+(.*)/),li=line.match(/^\s*(?:[-*]|\d+[.)、])\s+(.*)/);
   const p=e(h?'h4':li?'p':'p',undefined,li?'business-bullet':'');inline(p,h?h[1]:li?'• '+li[1]:line);box.append(p);i++;
  }return box;
 }
 function blocks(list){const box=e('div',undefined,'business-content');for(const b of list||[]){
  if(b.kind==='text'){box.append(markdown(b.text));continue}
  if(b.kind==='risk_cards'||b.kind==='metric_cards'){const grid=e('div',undefined,'business-cards');for(const x of b.items){const c=e('article',undefined,'business-card');c.append(e('span',x.title),e('strong',x.value??'未留存'));if(x.tag)c.append(e('small',x.tag));if(x.action_label)c.append(e('span',x.action_label+' · 历史入口','passive-action'));grid.append(c)}box.append(grid);if(b.note)box.append(e('p',b.note,'caption'));continue}
  if(b.kind==='table'){box.append(table(b.columns,b.rows));continue}
  if(b.kind==='report'){const head=e('div',undefined,'report-preview');head.append(e('strong',b.title),e('p',b.description));if(b.blocks?.length)head.append(fold('展开当时留存的报告',blocks(b.blocks),'historical-report'));else head.append(e('p','源记录未保留报告正文。','unavailable'));box.append(head);continue}
  if(b.kind==='options'){const card=e('div',undefined,'historical-options');card.append(e('h4',b.title));for(const q of b.questions){card.append(e('p',q.title));for(const o of q.options)card.append(e('p',[o.prefix,o.title].filter(Boolean).join(' · '),'option-choice'))}if(b.answers.length)card.append(e('p','当时选择：'+b.answers.join('、')));if(b.submitted_title)card.append(e('p',b.submitted_title));box.append(card);continue}
  if(b.kind==='business_lines'){const ul=e('ul',undefined,'business-lines');for(const line of b.lines){const li=e('li');inline(li,line);ul.append(li)}box.append(b.lines.length?ul:e('p','这张历史卡片没有可核验的可读字段。','unavailable'));continue}
  box.append(e('p',b.text||'该历史内容不可核验；完整材料保留在证据入口。','unavailable'));
 }return box}
 function message(m){const x=e('article',undefined,'chat-message readable-message role-'+m.role);x.dataset.role=m.role;x.append(e('h4',m.label||(m.role==='user'?'用户':'Agent')),blocks(m.blocks));return x}
 function chat(v){const box=e('div',undefined,'readable-chat'),hist=e('div',undefined,'history-messages');for(const m of v.history)hist.append(message(m));const title=v.history.length?'已有前文 · '+v.history.length+' 条业务消息':'前文 · 源记录未提供更早业务对话';if(!v.history.length)hist.append(e('p','当前输入未留存更早业务对话，不代表商家从未有过前文。','unavailable'));const d=fold(title,hist,'prior-context');d.dataset.historyKind=v.history_state;box.append(d,message(v.query),message(v.answer),e('p',v.note,'caption'));return box}
 const cats={quality:'质量',route:'路由',safety:'安全',context:'上下文'};
 const statuses={pass:'Pass',fail:'Fail',na:'NA',unknown:'不可核验'};
 function metricCard(m,trigger=false){const d=e('details',undefined,'metric-card '+m.label);d.dataset.metric=m.rule_id+':'+m.name;d.dataset.label=m.label;
  const s=e('summary');s.append(e('span',m.name),e('b',statuses[m.label]||'不可核验','metric-status'));d.append(s);if(trigger)d.append(e('span','实际入选触发项','trigger-tag'));const b=e('div',undefined,'metric-reason');b.append(e('small','规则 '+m.rule_id+' @ '+m.version),e('p',m.reason));if(m.description)b.append(e('p','指标含义：'+m.description,'caption'));b.append(e('code',m.source_path,'source-ref'));d.append(b);return d}
 function metrics(v){const box=e('section',undefined,'selection-metrics');box.dataset.section='selection';box.append(e('span','原始筛选表现 · 保留当时标签','eyebrow'),e('h3',v.expanded_only?'按扩展口径入选：最初 11 项均未 Fail':'当时哪些异常使本案入选？'));
  const hit=e('div',undefined,'selection-triggers');for(const x of v.triggers)hit.append(e('span',cats[x.category]+' · '+x.name+' = Fail','trigger-chip'));box.append(hit,e('p',v.group==='target_loaded_historical_fail'?'来自 32 条目标加载异常组：已加载目标 Skill，且五条规则任一有效指标 Fail。':'来自 11 条额外路由异常组：Skill 路由 = Fail，且不在前述 32 条中。','caption'));
  if(v.expanded_only)box.append(e('p','此案例仅在安全 / 上下文补充维度异常；不能计作质量或 Skill 路由 Fail。','criterion-notice'));
  const grid=e('div',undefined,'metric-grid');for(const m of v.all.filter(x=>x.initial_screening_metric))grid.append(metricCard(m,v.triggers.some(t=>t.rule_id===m.rule_id&&t.name===m.name)));box.append(grid,e('p','点击指标查看原判分理由。NA 表示不适用，不能当作 Pass；后续诊断不覆盖历史标签。','caption'));
  const extra=e('div',undefined,'metric-grid');for(const m of v.all.filter(x=>!x.initial_screening_metric))extra.append(metricCard(m,v.triggers.some(t=>t.rule_id===m.rule_id&&t.name===m.name)));
  const additional=fold('其余 14 项历史指标（含扩展口径的入选原因）',extra);if(v.expanded_only){const triggerDetails=v.all.filter(m=>!m.initial_screening_metric&&v.triggers.some(t=>t.rule_id===m.rule_id&&t.name===m.name));const visible=e('div',undefined,'extra-trigger');for(const m of triggerDetails)visible.append(metricCard(m,true));box.append(visible)}box.append(additional);return box;
 }
 function source(d){const box=e('div',undefined,'selection-source');box.append(e('h2','最初如何筛选，43 条又如何形成？'),e('p','原方案 A：Skill 路由 = Fail。B-raw：结果质量或过程质量任一项 = Fail。A 与 B-raw 可重叠。下列 11 项参与最初筛选；表中计数只针对本页 43 条历史案例。'));
  const groups=[['1523','结果质量 · 规则 1523 @ 0.0.8'],['1525','过程质量 · 规则 1525 @ 0.1.3'],['1524','Skill 路由 · 规则 1524 @ 0.0.9']];
  for(const[id,title]of groups){box.append(e('h3',title));const defs=e('div',undefined,'criteria-list');for(const m of d.original_plan.metrics.filter(x=>x.rule_id===id)){const row=e('article');row.append(e('h4',m.name),e('p',m.description),e('small','Fail '+m.fail_count+' · Pass '+m.pass_count+' · NA '+m.na_count+' · 不可核验 '+m.unknown_count));defs.append(row)}box.append(defs)}
  box.append(e('p','同属规则 1524 的意图理解、必要澄清、Goal/Task 路由、SubAgent 路由，以及规则 1521 的安全 3 项、1522 的上下文 7 项，均不属于最初的 11 项 A/B 筛选指标。','caption'));
  box.append(e('p','原方案中，B-raw 只是质量异常候选；B 须经证据复核并具有可检验的 Skill 修改路径。A1 / B1 表示其中涉及目标 Skill 的部分。需修改工具、Runtime、system 或模型配置的问题归 C；Judge 误判、多因或证据不足归 U。这些是后续归因层，不回写原始入选标签。','caption'));
  const actual=e('div',undefined,'actual-criteria');actual.append(e('h3','实际诊断选样：40 条符合 A/B，另有 3 条扩展样本'),e('p','32 条：开发池中已加载目标 Skill，五条规则任一有效指标 Fail，并排除独立标记为其他工具安全性不确定的样本。11 条：开发池中 Skill 路由 Fail、且不在前述 32 条内。两组选样无重复。'),e('p','43 条中：质量 Fail 34，Skill 路由 Fail 12，两者重叠 6，因此 A ∪ B-raw = 34 + 12 − 6 = 40。'),e('p',d.actual_selection.note));
  const extras=e('p');for(const[id,label]of [['C01','风险与薅羊毛操作拦截'],['C24','同 Session 历史承接'],['C41','跨 Session 长期记忆承接']]){const a=e('a',id+' · '+label+' Fail');a.href='#case-'+id;extras.append(a,document.createTextNode('　'))}actual.append(extras);box.append(actual);
  const funnel=e('div',undefined,'selection-funnel');funnel.append(e('h3','从源任务到开发侧 43 条'),e('p','任务 8692 / 数据集 4633，2026-11-04 至 11-10：6,413 条唯一 Trace → 排除旧保留集关联后 5,101 → 版本与标签审计有效 1,653 → 诊断候选 329。'),e('p','329 是以下集合去重后的并集：目标元数据命中 274（使用主 Skill 或 ContextActiveSkills 提及）、Skill 路由 Fail 28、按伪名排序取非目标且机评无 Fail 的对照 20、保留仍有效的既有诊断案例 196。四项有重叠，不能相加。元数据命中不等同于实际加载。'),e('p','此后按商家、会话、长 Query 近重复等关联隔离为 107 组，冻结为开发 230 / 验证 99；开发中 226 条属于历史曝光或关联组。开发侧目标加载 188 条，其中有历史 Fail 32 条；再补未包含的路由 Fail 11 条，形成此页 43 条。验证内容未进入本页。'));
  box.append(funnel);const strict=e('div',undefined,'criterion-notice');strict.append(e('h3','原严格恢复门槛与后续诊断选样不同'),e('p','原方案要求先排除：Trace / 前文或轮次边界缺失、历史工具协议不完整、必要图片或文件不可恢复、实时动态取数、记忆 / system / AppState 等必要状态不可固定、机评无效或矛盾未解决、业务副作用不可隔离。严格门槛下 329 条中获准重放为 0。'),e('p','后来经授权以 Builder 当前支持的输入继续探索，才形成后续诊断和开发分桶。这里展示历史选样与原标签，不宣称通过原严格门槛，也不以新运行分数替代历史分数。'));box.append(strict);const notes=e('div');for(const n of d.limitations)notes.append(e('p',n));const refs=e('dl');for(const x of d.sources){refs.append(e('dt',x.file),e('dd',x.sha256,'source-ref'))}notes.append(e('h4','冻结来源摘要及 SHA-256'),refs);box.append(fold('来源版本、有效性与样本限制',notes));return box;
 }
 function loops(v){const box=e('div',undefined,'compact-loops');box.append(e('p',v.note,'caption'));const load=e('div',undefined,'skill-load-summary');
  load.append(e('strong','目标 Skill：shop-risk-inspection-skill'));if(v.target_loads.length){for(const l of v.target_loads)load.append(e('p',(l.loop_id?'Loop 内加载':l.start<(v.rows[0]?.start??Infinity)?'进入首个 Loop 前加载':'Loop 外加载记录')+' · '+l.status+' · 版本 '+(l.version||'未留存')+' · '+l.start.toFixed(2)+'s'));}else load.append(e('p','完整 Trace 中未找到目标 Skill 的实际加载 Span。元数据命中不作为加载证明。'));
  if(v.target_body_first_visible)load.append(e('p','正文首次可核验地进入主模型输入：'+v.target_body_first_visible.call_id+' · 消息索引 '+v.target_body_first_visible.message_index));else load.append(e('p','没有核验到目标正文进入主模型输入。','caption'));box.append(load);
  for(const l of v.rows){const card=e('article',undefined,'loop-card');card.dataset.loopId=l.id;const head=e('header');head.append(e('span','作用域 '+l.scope+' · '+l.name+' · '+l.start.toFixed(2)+'s','case-meta'),e('h4',l.title));card.append(head);
   for(const t of l.tools){const tool=e('div',undefined,'loop-tool');tool.append(e('strong',t.title));const ul=e('ul');for(const f of t.facts)ul.append(e('li',f));tool.append(ul);card.append(tool)}
   for(const o of l.outcomes)card.append(e('p',o,'loop-outcome'));
   const relation=e('div',undefined,'skill-relation');for(const r of l.target_relation)relation.append(e('p',(r.status==='observed'?'已观测 · ':'证据不足 · ')+r.text));for(const c of l.clauses){const q=e('div',undefined,'clause-link');q.append(e('p',c.meaning));if(c.quote)q.append(e('blockquote',c.quote));q.append(e('small','证据 '+c.refs.join(' → ')+'；对应关系不等于已证明因果。'));relation.append(q)}card.append(relation);
   const evidence=e('div');evidence.append(e('p','真实 Loop Span：'+l.id),e('p','源路径：'+l.source_path));for(const c of l.model_calls)evidence.append(e('p',c.id+' · '+(c.actual_model||'模型字段未留存')+' · '+(c.status==='confirmed'?'确认生成':'未确认观测')));evidence.append(e('p','本轮另有 '+l.auxiliary_count+' 个辅助调用观测；不新增业务 Loop。'));card.append(fold('本轮证据位置与模型',evidence,'loop-evidence'));box.append(card);
  }
  if(v.outside_loop_tools.length){const other=e('div');for(const t of v.outside_loop_tools)other.append(e('p',t.title+'：'+t.facts.join('；')));box.append(fold('未归属真实 Loop 的工具记录 · '+v.outside_loop_tools.length,other))}
  return box;
 }
 async function pinned(meta){if(!meta?.file)throw Error('缺少展示文件的完整性清单');const r=await fetch('cases/'+meta.file,{credentials:'omit'});if(!r.ok)throw Error('HTTP '+r.status);const bytes=await r.arrayBuffer(),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');if(bytes.byteLength!==meta.bytes||hash!==meta.sha256)throw Error('展示材料完整性校验失败');return JSON.parse(new TextDecoder().decode(bytes))}
 return {blocks,chat,metrics,source,loops,pinned};
})();
