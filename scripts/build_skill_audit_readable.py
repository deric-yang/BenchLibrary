#!/usr/bin/env python3
"""Derive a read-only presentation from the 43 already-published evidence bundles."""
import argparse,collections,hashlib,json,re,shlex
from pathlib import Path
TARGET='shop-risk-inspection-skill'
VERS={'1521':'0.0.4','1522':'0.0.6','1523':'0.0.8','1524':'0.0.9','1525':'0.1.3'}
DIMS={'1521':['数据安全与内容合规','hack/攻击应对','风险与薅羊毛操作拦截'],'1522':['当前 Query 承接','同 Session 历史承接','跨 Session 长期记忆承接','Loop 压缩后关键信息保真','跨 Agent 委派承接','Goal/Task 状态承接','商家画像承接'],'1523':['结果完成','结果正确','结果完整','表达清晰友好','响应效率'],'1524':['意图理解正确','必要信息澄清','Goal/Task 路由','SubAgent 路由','Skill 路由'],'1525':['策略-工具使用决策','工具-输入参数正确性','工具-执行结果有效性','效率-Loop轮次收敛有效性','效率-终止判断与结果验证']}
DESC={
'结果完成':'是否交付当前请求的核心目标，而非只解释、承诺或停在中间步骤。',
'结果正确':'交付的事实、数值、对象和结论是否有依据并满足用户条件。',
'结果完整':'是否覆盖完成任务所必需的信息、范围和结果，不以无依据的推断补全。',
'表达清晰友好':'结论、重点和下一步是否清楚易懂，语气和呈现是否合适。',
'响应效率':'根据任务类型核对首次可见输出和完整输出耗时；首思考耗时仅作诊断。',
'策略-工具使用决策':'该用的工具是否使用，选择和时机是否合理，有无不必要调用。',
'工具-输入参数正确性':'工具参数的对象、范围、格式与调用契约是否正确。',
'工具-执行结果有效性':'是否取得有效执行结果，并正确识别成功、失败、空结果或不可用。',
'效率-Loop轮次收敛有效性':'各轮是否带来有效进展，轮次是否按规则收敛，是否存在无效循环。',
'效率-终止判断与结果验证':'是否在目标完成且必要验证后停止，避免提前结束或无意义继续。',
'Skill 路由':'是否选择匹配当前意图的 Skill，避免漏选、错选或不必要加载。'}
TAGS={'ui-container','ui-table','ui-result-preview','store-risk-overview','ui-option-selector','compass-overview','ui-text','ui-title','ui-suggestions-list','experience-score-overview'}
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,separators=(',',':')))
def dec(x):
 if isinstance(x,str):
  try:return json.loads(x)
  except (ValueError,TypeError):return x
 return x
def strings(x,depth=0):
 if depth>12:return
 if isinstance(x,str):
  y=dec(x)
  if isinstance(y,(list,dict)):yield from strings(y,depth+1)
  else:yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y,depth+1)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y,depth+1)
def unpack(b):
 def u(x):
  if isinstance(x,dict):return b['strings'][x['$atlasString']]if set(x)=={'$atlasString'}else{k:u(v)for k,v in x.items()}
  return[u(v)for v in x]if isinstance(x,list)else x
 return u(b['data'])
def content_text(c):
 if isinstance(c,str):return c
 if isinstance(c,list):return '\n'.join(x.get('text','')for x in c if isinstance(x,dict)and x.get('type')in('text','input_text'))
 return ''
def unescape_mixed(s):
 # Once outer markup is decoded, nested JSON escapes belong to component data.
 if s.lstrip().startswith('<'):return s
 # Only decode an outer encoding layer from the known sideMixedContent field.
 for _ in range(4):
  if not re.search(r'\\(?:u003[cCeE]|n|")',s):break
  old=s
  s=re.sub(r'\\(?:u[0-9a-fA-F]{4}|["\\/bfnrt])',lambda m:json.loads('"'+m[0]+'"'),s)
  if s==old or ('<ui-'in s and '\\"'not in s[:200]):break
 return s
def visible(x):
 if x is None:return ''
 if isinstance(x,(str,int,float)):return str(x)
 if isinstance(x,list):return ' · '.join(filter(None,(visible(y)for y in x)))
 if isinstance(x,dict):
  keys=['title','content','text','subTitle','subtitle','label','value','unit','tag','lines','description']
  vals=[visible(x[k])for k in keys if k in x and x[k]not in(None,'')]
  return ' · '.join(dict.fromkeys(v for v in vals if v))
 return ''
def side_contents(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('sideMixedContent','sideFooterContent')and isinstance(v,str)and v:yield unescape_mixed(v)
   elif k=='post_body':
    y=dec(v)
    if isinstance(y,(dict,list)):yield from side_contents(y)
   elif isinstance(v,(dict,list)):yield from side_contents(v)
 elif isinstance(x,list):
  for y in x:yield from side_contents(y)
def component(tag,o,depth):
 if tag in ('ui-text','ui-title'):return {'kind':'text','text':o.get('text')or o.get('content')or'', 'style':o.get('size')or o.get('theme')}
 if tag=='store-risk-overview':
  return {'kind':'risk_cards','items':[{'title':x.get('title',''),'value':x.get('value'),'tag':visible(x.get('tag')),'action_label':x.get('action',{}).get('actionName')}for x in o.get('items',[])]}
 if tag=='ui-table':
  cols=o.get('columns',[]);rows=o.get('list')or o.get('data')or[]
  return {'kind':'table','columns':[x.get('title')or x.get('key')for x in cols],'rows':[[visible(r.get(c['key']))for c in cols]for r in rows],'row_count':len(rows)}
 if tag=='ui-result-preview':
  side=list(side_contents(o));return {'kind':'report','title':o.get('title','历史报告'),'description':o.get('description',''),'blocks':[b for s in side for b in delivery(s,depth+1)] if depth<4 else[],'has_retained_body':bool(side)}
 if tag=='ui-option-selector':
  return {'kind':'options','title':o.get('title','请选择'),'status':o.get('status'),'submitted_title':o.get('submittedTitle'),'questions':[{'title':q.get('title'),'options':[{'prefix':v.get('prefix'),'title':v.get('title')}for v in q.get('options',[])]}for q in o.get('questions',[])],'answers':[x.get('selected_label')or x.get('custom_input')or x.get('selected_value')for x in o.get('result',{}).get('answers',[])]}
 if tag=='compass-overview':
  metrics=[]
  for root in (o.get('data')or{}).values():
   if not isinstance(root,dict):continue
   for row in root.get('data',[]):
    for meta in root.get('basic_meta',[]):
     v=row.get(meta.get('index_name'),{})
     if isinstance(v,dict):
      value=next((v[k]for k in ['value_display','display_value','format_value','value_str','value']if k in v),None)
      if value is None and isinstance(v.get('index_value',{}).get('value'),dict):
       raw=v['index_value']['value'];value=str(raw.get('value','未留存'))
       if meta.get('attribute',{}).get('extra',{}).get('unit')!='number':value+='（协议原值；显示单位未核验）'
      if value is None:
       # Some records use a nested value payload. Preserve an explicit gap rather than infer units.
       value=visible({k:x for k,x in v.items()if k not in['extension','chart']})or'值未能从已留存协议核验'
     else:value=v
     metrics.append({'title':meta.get('index_display')or meta.get('index_name'),'value':value})
  return {'kind':'metric_cards','items':metrics,'note':'按历史卡片字段展示；未重新取数。'}
 # This covers nested report sections without exposing action payloads.
 sections=[]
 def walk(v):
  if isinstance(v,list):
   for x in v:walk(x)
  elif isinstance(v,dict):
   line=visible({k:x for k,x in v.items()if k in ['title','subtitle','subTitle','content','text','label','value','unit','description']})
   if line:sections.append(line)
   for k,x in v.items():
    if k in ['items','groups','sections','children','list','data','rows','button','tag','tags','lines']:walk(x)
 walk(o)
 return {'kind':'business_lines','component':tag,'lines':sections,'unavailable':not bool(sections)}
def clean_text(s):
 s=re.sub(r'</?(?:'+ '|'.join(TAGS)+r')(?:\s[^>]*)?>','',s)
 s=re.sub(r'<br\s*/?>','\n',s)
 return s.strip()
def delivery(text,depth=0):
 text=content_text(text);blocks=[];cursor=0
 for m in re.finditer(r'<([\w-]+)>\s*',text):
  tag=m[1]
  if tag not in TAGS or tag=='ui-container' or m.start()<cursor:continue
  before=clean_text(text[cursor:m.start()])
  if before:blocks.append({'kind':'text','text':before})
  try:o,n=json.JSONDecoder().raw_decode(text[m.end():])
  except ValueError:
   # No guessing for unsupported/broken component JSON.
   end=text.find('</'+tag+'>',m.end())
   blocks.append({'kind':'unavailable','text':'历史卡片内容无法可靠解析；原始协议已保留在证据入口。','component':tag})
   cursor=end+len(tag)+3 if end>=0 else len(text);continue
  if isinstance(o,dict):blocks.append(component(tag,o,depth))
  else:blocks.append({'kind':'unavailable','text':'历史卡片的数据结构无法可靠解析。','component':tag})
  cursor=m.end()+n
 tail=clean_text(text[cursor:])
 if tail:
  # A model placeholder is not a delivered answer.
  if re.fullmatch(r'<(?:action|instance|subagent|mcp)[^>]*>',tail.strip(),re.I):blocks.append({'kind':'unavailable','text':'源记录只保留内部占位符，未保留展开后的交付内容；不把它当作回答。'})
  else:blocks.append({'kind':'text','text':tail})
 return blocks
def chat(data):
 first=next((e for e in data['trajectory']['events']if e['kind']=='main_llm'),None)
 msgs=first.get('message_tail',[])if first else[]
 anchor=data['viewer_evidence'].get('first_context_current_query_index')
 query=data['trajectory']['source_query'];method='retained_exact_anchor'
 if not isinstance(anchor,int):
  matches=[]
  for i,m in enumerate(msgs):
   t=content_text(m.get('content'))
   if m.get('role')=='user'and t.startswith('【当前用户问题'):
    t=re.sub(r'^【当前用户问题[^】]*】\s*','',t)
    if t.strip()==query.strip()or t.startswith(query.strip()+'\n\n## 行动点提交上下文'):matches.append(i)
  if len(matches)==1:anchor=matches[0];method='exact_query_in_explicit_current_user_wrapper'
 prior=[];omitted=[]
 if isinstance(anchor,int):
  for i,m in enumerate(msgs[:anchor]):
   if m.get('role')not in('user','assistant'):continue
   t=content_text(m.get('content'))
   if not t.strip():continue
   # Only explicit framework wrappers are removed; business prose is retained.
   t=re.sub(r'^【(?:本轮历史问题|当前用户问题)[^】]*】\s*','',t)
   if m['role']=='user'and re.match(r'^\s*<(?:system-reminder|task-reminder|custom-task-|runtime-)',t):
    omitted.append({'message_index':i,'reason':'explicit framework injection'});continue
   if '## 行动点提交上下文'in t:t=t.split('## 行动点提交上下文')[0].rstrip()
   prior.append({'role':m['role'],'blocks':delivery(t),'source_message_index':i})
 history_state='recorded'if prior else'earlier_dialogue_not_provided'if isinstance(anchor,int)else'boundary_unavailable'
 return {'history':prior,'history_state':history_state,'anchor_index':anchor,'anchor_method':method,'omitted_injected_user_messages':omitted,'query':{'role':'user','label':'原任务问题（定时触发）'if data['viewer_evidence']['root_span_code']=='schedule_task_execute_triggered_run'else'用户当时提问','blocks':delivery(query)},'answer':{'role':'assistant','label':'Agent 实际交付回答','blocks':delivery(data['trajectory']['historical_answer'])},'note':'聊天视图只呈现业务对话与留存交付；系统、工具消息和原模型占位符在独立证据入口。卡片为历史内容的只读重建，不发起原业务操作。'}
def short(s,n=190):
 s=re.sub(r'\s+',' ',str(s)).strip();return s if len(s)<=n else s[:n]+'…'
def tool_summary(s):
 ip=dec(s.get('input'))or{};out=dec(s.get('output'))or{};args=dec(ip.get('input_json'))or{};payload=dec(out.get('output_json'))or{}
 args=args if isinstance(args,dict)else{};payload=payload if isinstance(payload,dict)else{}
 tool=ip.get('tool_code')or ip.get('tool_name')or s['name'];command=args.get('command','');params=args.get('arguments')or{}
 result=dec(payload.get('Result'));result=result if isinstance(result,dict)else{}
 route=payload.get('Route')or''
 if not route and command.startswith('actionTool '):
  parts=shlex.split(command);route=parts[1]if len(parts)>1 else''
  if '--argument'in parts:
   params=dec(parts[parts.index('--argument')+1])
 params=payload.get('Arguments')or params;params=params if isinstance(params,dict)else{}
 title=tool;task='执行 '+tool;facts=[];target=False
 if tool=='skillTool':
  name=params.get('skill_name')or payload.get('SkillName')or'名称未留存'
  title='加载 '+name;task='取得本轮业务规则';target=name==TARGET
  if isinstance(payload.get('Data'),dict)and payload['Data']:facts.append('返回 Skill 正文；是否在模型输入中可见另列核验。')
 elif route=='shop_risk_inspection_report':
  title='查询店铺风险总览';task='获取风险诊断';target=True
  codes=params.get('inspect_codes')
  facts.append('请求 '+str(len(codes))+' 项：'+', '.join(codes) if isinstance(codes,list)else'检查范围参数未完整留存。')
 elif route=='shop_risk_inspection_detail':
  title='查询单项风险详情';task='获取单项明细';target=True;facts.append('查询指标：'+str(params.get('inspect_code','未留存')))
 elif tool in('subAgentTool','handoffTool'):
  task='委派局部任务'if tool=='subAgentTool'else'移交会话责任';title=task
  facts.append(short(params.get('query')or args.get('query')or args.get('user_intent')or params.get('task')or'交接参数详见原始证据。'))
 elif tool=='askUserTool':task='向用户澄清';title='提出澄清问题'
 elif tool=='readFileTool':task='读取已有材料';title='读取文件';facts.append(short(args.get('file_path')or args.get('path')or command or'文件路径见原始证据。'))
 else:
  if route:title=tool+' · '+route
  if args.get('user_intent'):facts.append(short(args['user_intent']))
  elif command:facts.append(short(command))
 if result:
  for key,label in [('healthy','健康结果'),('risk_count','命中风险类型'),('urgent_count','高危风险类型'),('attention_count','关注风险类型'),('total','总数'),('message','返回文案')]:
   if key in result:facts.append(label+'：'+str(result[key]))
  if result.get('instance_id'):facts.append('已返回卡片实例；实例标识不是交付正文。')
 status=out.get('status')or payload.get('Status')or'未留存'
 err=out.get('err')or payload.get('error')or''
 if err:facts.append('错误：'+short(err))
 elif not result and tool!='skillTool':
  facts.append('执行状态：'+str(status))
  if payload:facts.append('返回字段：'+', '.join(k for k in payload if k not in['Arguments','DefaultParams','Render','RequireAuth','RPCService','RPCMethod','MethodDescription','RouteDescription']))
 return {'span_id':s['id'],'source_path':s['path'],'tool':tool,'title':title,'task':task,'facts':facts,'status':status,'target_tool':target,'route':route,'parameters':{k:v for k,v in params.items()if k in['inspect_codes','inspect_code']},'error':bool(err)}
def target_doc(c):
 for i,m in enumerate((c.get('input')or{}).get('messages',[])):
  if m.get('role')!='tool':continue
  for text in strings(m.get('content')):
   text=text.replace('\\n','\n')
   if '# 店铺风险巡检与单项详情'in text and 'inspect_codes'in text:
    return {'call_id':c['id'],'message_index':i,'text':text}
 return None
def loops(data,a):
 spans={s['id']:s for s in a['spans']};calls=a['calls']+a['unconfirmed']
 real=[s for s in a['spans']if s['code']=='runLoopOneTurn'];real.sort(key=lambda s:s['start'])
 def ancestor(s):
  while s:
   if s['code']=='runLoopOneTurn':return s['id']
   s=spans.get(s['parent'])
  return None
 tools=[tool_summary(s)for s in a['spans']if s['code']=='agent_loop_tool_call']
 toolloop={t['span_id']:ancestor(spans[t['span_id']])for t in tools}
 loads=[]
 for s in a['spans']:
  if s['code']!='skill_load':continue
  o=dec(s['output']);i=dec(s['input']);o=o if isinstance(o,dict)else{};i=i if isinstance(i,dict)else{}
  if (o.get('skill_code')or o.get('skillName')or i.get('skill_code')or i.get('skillName'))==TARGET:
   loads.append({'span_id':s['id'],'source_path':s['path'],'loop_id':ancestor(s),'start':s['start'],'status':o.get('load_status','未留存'),'version':o.get('skill_version')or o.get('version')})
 docs={c['id']:target_doc(c)for c in calls if c.get('scene')in('main_agent_loop_team','main_agent_loop')}
 scopes=list(dict.fromkeys(s['parent']for s in real));rows=[]
 for s in real:
  cc=[c for c in calls if c.get('loop',{} )and c['loop']['spanId']==s['id']]
  main=[c for c in cc if c.get('scene')in('main_agent_loop_team','main_agent_loop')]
  tt=[t for t in tools if toolloop[t['span_id']]==s['id']]
  ll=[l for l in loads if l['loop_id']==s['id']]
  visible_docs=[docs[c['id']]for c in main if docs.get(c['id'])]
  relation=[];clauses=[]
  for l in ll:relation.append({'status':'observed','text':'本轮有目标 Skill 加载记录：'+l['status']+'；版本 '+str(l['version']or'未留存'),'refs':[l['span_id']]})
  if visible_docs:relation.append({'status':'observed','text':'目标 Skill 正文可见于本轮 '+', '.join(x['call_id']for x in visible_docs)+' 的 tool 输入。','refs':[x['call_id']for x in visible_docs]})
  if not ll and not visible_docs:relation.append({'status':'unresolved','text':'本轮未见目标 Skill 加载或正文可见证据；历史 ActiveSkills/目录提及不等同于本轮加载。','refs':[s['id']]})
  for t in tt:
   if t['route']not in('shop_risk_inspection_report','shop_risk_inspection_detail'):continue
   doc=visible_docs[0]if visible_docs else None
   needle='不得删除、增加、重排或由模型推测全量调用中的'if t['route'].endswith('report')else'不得在单项详情分支调用全量报告工具'
   line=next((x.strip()for x in (doc or{}).get('text','').splitlines()if needle in x),'')
   if line:
    match=re.search(r'"inspect_codes"\s*:\s*(\[[^\]]+\])',doc['text'].replace('\\"','"'))
    actual=t['parameters'].get('inspect_codes')
    if t['route'].endswith('report') and match and isinstance(actual,list):
     expected=dec(match[1])
     if isinstance(expected,list):
      same=expected==actual
      clauses.append({'status':'observed','quote':'','meaning':'条款示例固定 '+str(len(expected))+' 项；实际请求 '+str(len(actual))+' 项；列表与顺序'+('一致。'if same else'不一致。')+'这是可核验的参数差异，不单独证明失败原因。','refs':[doc['call_id'],t['span_id']],'message_index':doc['message_index']})
    clauses.append({'status':'observed','quote':line,'meaning':'该工具调用与模型可见的全量参数条款对应。'if t['route'].endswith('report')else'该工具调用与模型可见的单项详情条款对应。','refs':[doc['call_id'],t['span_id']],'message_index':doc['message_index']})
   else:clauses.append({'status':'unresolved','quote':'','meaning':'本轮工具名与目标能力相关，但未取得本轮模型可见的对应条款，不据此作因果判断。','refs':[t['span_id']]})
  texts=[c['output'].get('text','')for c in main if c.get('output',{}).get('text')]
  outcomes=[]
  for c in main:
   out=c.get('output')or{}
   if c['id'].startswith('U'):outcomes.append(c['id']+' 未确认生成；保留失败/重试证据。')
   elif out.get('tool_calls'):outcomes.append(c['id']+' 产出 '+str(len(out['tool_calls']))+' 个工具调用。')
   elif out.get('text'):
    text=out['text']
    outcomes.append(c['id']+' '+('输出内部卡片占位符，实际交付见上方聊天。'if re.search(r'<(?:action-|subagent-|mcp-)',text)else'生成文字答复：'+short(text)))
   else:outcomes.append(c['id']+' 未保留可读输出。')
  tasks=list(dict.fromkeys(t['task']for t in tt))
  title='、'.join(tasks)if tasks else'生成回复内容'if texts else'模型请求与状态推进'
  rows.append({'id':s['id'],'name':s['name'],'scope':scopes.index(s['parent'])+1,'start':s['start'],'duration':s['duration'],'title':title,'tools':tt,'outcomes':outcomes,'target_relation':relation,'clauses':clauses,'model_calls':[{'id':c['id'],'actual_model':c.get('providerModel'),'status':'unconfirmed'if c['id'].startswith('U')else'confirmed'}for c in main],'auxiliary_count':len(cc)-len(main),'source_path':s['path']})
 return {'rows':rows,'outside_loop_tools':[t for t in tools if toolloop[t['span_id']]is None],'target_loads':loads,'target_body_first_visible':next(({'call_id':c['id'],'loop':c.get('loop'),'message_index':docs[c['id']]['message_index']}for c in sorted(calls,key=lambda c:c['start'])if docs.get(c['id'])),None),'all_generation_counts':a['counts'],'note':'每张卡对应真实 runLoopOneTurn 祖先，不把工具内辅助 LLM 当作新业务 Loop。动作摘要是可见调用/返回的展示，不是根因推断；完整输入输出可按需打开。'}
def metrics(data):
 L=data['historical_machine_evaluation']['labels'];allm=[]
 for rid,names in DIMS.items():
  for name in names:
   x=L.get(rid)or{};value=x.get('labels',{}).get(name);reason=x.get('reasons',{}).get(name)
   known=value in('pass','fail','na')and bool(reason)
   selected=rid in('1523','1525')or(rid=='1524'and name=='Skill 路由')
   allm.append({'rule_id':rid,'version':VERS[rid],'name':name,'label':value if known else'unknown','reason':reason if known else'不可核验：缺少该指标的有效历史标签或对应理由。','initial_screening_metric':selected,'category':'route'if rid=='1524'else'quality'if rid in('1523','1525')else'context'if rid=='1522'else'safety','description':DESC.get(name),'source_path':'historical_machine_evaluation.labels.'+rid+'.labels.'+name})
 group=data['viewer_evidence']['selection_group'];fails=[x for x in allm if x['label']=='fail']
 initial=[x for x in fails if x['initial_screening_metric']]
 triggers=[x for x in fails if group=='target_loaded_historical_fail'or(x['rule_id']=='1524'and x['name']=='Skill 路由')]
 return {'group':group,'all':allm,'triggers':[{'rule_id':x['rule_id'],'name':x['name'],'category':x['category']}for x in triggers],'quality_fail':any(x['category']=='quality'for x in fails),'skill_route_fail':any(x['name']=='Skill 路由'for x in fails),'expanded_only':not bool(initial),'historical_basis_note':'本案按已冻结选择清单入选。所有标签/理由来自当时机评；后续归因并未覆盖历史标签。'}
def build(root,evidence,audit):
 D=root/'site/activities/skill-audit/cases';idx=json.loads((D/'index.json').read_text());receipts=[];counts=collections.Counter();mcount=collections.Counter()
 targets=set(json.loads((evidence/'target-selection.json').read_text())['case_ids']);routes=set(json.loads((evidence/'routing-selection.json').read_text())['case_ids'])
 assert len(targets)==32 and len(routes)==11 and not targets&routes
 for item in idx['cases']:
  p=D/item['file'];raw=p.read_bytes();assert sha(raw)==item['sha256']
  d=json.loads(raw);a=unpack(json.loads((D/item['atlas']['file']).read_text()))
  expected='target_loaded_historical_fail'if d['case_id']in targets else'additional_routing_fail'
  assert d['case_id']in targets|routes and d['viewer_evidence']['selection_group']==expected
  view={'schema':1,'id':item['id'],'case_id':d['case_id'],'original_sha256':sha(raw),'atlas_sha256':item['atlas']['sha256'],'metrics':metrics(d),'chat':chat(d),'loops':loops(d,a)}
  assert view['metrics']['triggers'],item['id']
  file=item['id']+'.view.json';write(D/file,view);data=(D/file).read_bytes()
  item['presentation']={'file':file,'bytes':len(data),'sha256':sha(data)}
  item['historical_selection']={k:view['metrics'][k]for k in ['group','triggers','quality_fail','skill_route_fail','expanded_only']}
  counts.update({'quality_fail':view['metrics']['quality_fail'],'skill_route_fail':view['metrics']['skill_route_fail'],'overlap':view['metrics']['quality_fail']and view['metrics']['skill_route_fail'],'expanded_only':view['metrics']['expanded_only']})
  counts['history_'+view['chat']['history_state']]+=1
  for m in view['metrics']['all']:mcount[(m['rule_id'],m['name'],m['label'])]+=1
  receipts.append({'id':item['id'],'source_unchanged':sha(p.read_bytes())==item['sha256'],'metrics':len(view['metrics']['all']),'triggers':view['metrics']['triggers'],'expanded_only':view['metrics']['expanded_only'],'history_state':view['chat']['history_state'],'history_messages':len(view['chat']['history']),'loops':len(view['loops']['rows']),'target_loads':len(view['loops']['target_loads']),'view':item['presentation']})
 assert len(receipts)==43 and all(x['metrics']==25 for x in receipts)
 defs=[{'rule_id':rid,'version':VERS[rid],'name':name,'description':DESC[name],'fail_count':mcount[(rid,name,'fail')],'pass_count':mcount[(rid,name,'pass')],'na_count':mcount[(rid,name,'na')],'unknown_count':mcount[(rid,name,'unknown')]}for rid in ['1523','1525','1524']for name in DIMS[rid]if name in DESC]
 source={'schema':1,'original_plan':{'quality_rules':['1523@0.0.8','1525@0.1.3'],'routing_rule':'1524@0.0.9 / Skill 路由','metrics':defs,'A':'Skill 路由 = Fail','B_raw':'结果质量或过程质量任一维度 = Fail','union':'A 与 B-raw 可重叠；标签用于发现候选，不代表目标 Skill 已承担责任。'},'actual_selection':{'target_loaded_any_fail':32,'additional_skill_route_fail':11,'total':43,'quality_fail':counts['quality_fail'],'skill_route_fail':counts['skill_route_fail'],'overlap':counts['overlap'],'initial_A_or_B':counts['quality_fail']+counts['skill_route_fail']-counts['overlap'],'expanded_only':counts['expanded_only'],'expanded_ids':[x['id']for x in receipts if x['expanded_only']],'note':'实际诊断选样比最初 A/B 更宽：目标加载组采用五条规则中任一有效 Fail，额外包含只在安全/上下文维度 Fail 的 3 条。此处明确保留口径差异，不将它们伪称为质量或路由 Fail。'},'funnel':json.loads((evidence/'funnel-summary.json').read_text()),'prefilter':json.loads((evidence/'diagnostic-prefilter-policy.json').read_text()),'development':json.loads((evidence/'preparation-summary.json').read_text())['development_inventory'],'sources':[{'file':p.name,'sha256':sha(p.read_bytes())}for p in sorted(evidence.iterdir())if p.is_file()],'limitations':['历史有效性审计按当时冻结 schema/别名/统计一致性执行，不证明 Judge 语义正确。','原严格恢复阶段 329 条中严格可重放为 0；后来经授权改用统一支持的 Builder 输入做探索。43 是历史诊断选样，不能称为 43 条严格可复现样本。','归因、历史筛选和后来实验是三层信息；本站此次只改历史看板，不同步或干预进行中的候选实验。','NA 不等于 Pass；未知明确标为不可核验。没有用后来复核标签覆盖原始表现。']}
 write(D/'selection-evidence.json',source);raw=(D/'selection-evidence.json').read_bytes();idx['selection_evidence']={'file':'selection-evidence.json','bytes':len(raw),'sha256':sha(raw)}
 idx['presentation_version']=4;write(D/'index.json',idx)
 write(audit,{'cases':receipts,'counts':dict(counts),'source_labels_checked':43,'source_payloads_unchanged':43,'original_atlas_unchanged':43,'metric_slots':43*25,'initial_metric_slots':43*11,'all_trigger_evidence_verified':True})
 print(json.dumps({'cases':len(receipts),'counts':dict(counts),'view_bytes':sum(x['view']['bytes']for x in receipts)},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);a=p.parse_args();build(a.root,a.evidence,a.audit)
