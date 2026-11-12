
"""Build reviewed, provenance-aware Trace Atlas case bundles from retained ECOP evidence."""
import argparse,collections,hashlib,importlib.util,json,re
from pathlib import Path

def build(work,cases,adapter):
 spec=importlib.util.spec_from_file_location('atlas_adapter',adapter);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 scene_titles={'main_agent_loop_team':'业务 Agent 主循环','agent_loop_runtime_compact':'压缩会话摘要','conversation_title_generate':'生成会话标题','shop_risk_inspection_report_summary':'生成巡检归因摘要','function_summary_1':'整理知识召回菜单','qa_after_query_suggest_model':'生成后续提问','suggest_stand':'标准化推荐问题','suggest_sensitive_check':'校验推荐问题','intent_analyse':'分析用户意图','agent_loop_security_model':'执行安全检查','new_shop_trusteeship_op_summary':'生成待操作提示'}
 receipts=[]
 for wd in sorted(work.iterdir()):
  if not (wd/'source.json').exists():continue
  facts=mod.extract((wd/'source.json').read_bytes())
  # A nested transport identity with no retained request/output cannot establish another generation.
  ambiguous=[]
  spans={s['id']:s for s in facts['spans']}
  for c in facts['calls'][:]:
   if c['inputSource']=='unavailable' and any(spans[a]['code']=='LLM' for a in c['evidence']['ancestors']):
    facts['calls'].remove(c);c['confirmation']='nested_identity_only';c['id']='U%02d'%(len(facts['unconfirmed'])+1)
    c['uncertainty']='嵌套 LLM 仅保留另一响应标识，缺少请求与输出；不能确认独立生成，也不自动与外层合并。'
    facts['unconfirmed'].append(c);ambiguous.append(c['spanId'])
  for i,c in enumerate(facts['calls'],1):c['id']='N%02d'%i
  for c in facts['calls']+facts['unconfirmed']:
   if not c.get('scene'):
    s=spans[c['spanId']]
    compkeys=[k for k in (s.get('context') or {}) if k.endswith('_llm_completion_result')]
    if len(compkeys)==1:c['scene']=compkeys[0].removesuffix('_llm_completion_result')
  for c in facts['unconfirmed']:
   if c.get('providerModel'):
    c['reportedModelWithoutResponse']=c['providerModel']
    c['providerModel']=None
  facts['counts']['confirmed']=len(facts['calls']);facts['counts']['unconfirmed']=len(facts['unconfirmed'])
  facts['counts']['ambiguousNestedIdentity']=len(ambiguous)
  raw_case=json.loads((cases/(wd.name+'.json')).read_text());query=raw_case['trajectory']['source_query']
  notes=['统计覆盖本条完整 Trace 的业务与辅助 LLM；与业务事件子集分开。',
   'N 是有响应或生成证据的独立观测；U 是失败、无生成证据或嵌套身份待确认项。未确认不代表服务端从未执行。',
   '模型请求名、SDK 名与实际返回名分别保留；缺失 Token/输入保持未知。',
   '来源分类已按本批提示模板、消息字段与实际内容审阅；底层数据库、服务和持久记忆来源未由当前 Trace 证实时明确标为未证实。',
   '首次可见是本 Trace 中首次观测到的模型请求，不声称是内容最早生成时间。相同内容按来源和消息身份分别建档。',
   '同一 Loop 可能含主调用、重试和工具内部辅助调用；Loop 归属来自真实祖先，排序不表示串行因果。',
   '本页事实来自已留存的上游清洗归档；保留其原有占位符，未新增业务内容脱敏。']
  if ambiguous:notes.append('存在嵌套响应标识但缺少请求与输出的观测，已列入 U，不计入确认生成数。')
  annotations=[];contexts={};allcalls=sorted(facts['calls']+facts['unconfirmed'],key=lambda c:c['start'])
  for c in allcalls:
   title=scene_titles.get(c.get('scene'),'模型观测 · 场景未提供')
   names=[(t.get('function') or {}).get('name') or t.get('name') for t in c['output'].get('tool_calls') or [] if isinstance(t,dict)]
   if names:title+=' · '+', '.join(dict.fromkeys(n for n in names if n))
   purpose=('实际输出工具调用，参数与返回在原始证据中核对。' if names else '读取本节点实际输入并生成该场景输出；具体原文见右侧。')
   if c['id'].startswith('U'):purpose='缺少可确认生成证据；保留请求、错误及不确定性。'
   annotations.append({'id':c['id'],'title':title,'agent':c.get('scene') or '源记录未提供','purpose':purpose,'phase':'main' if c.get('scene')=='main_agent_loop_team' else 'aux'})
   for steps,role,text in mod.units(c):
    msg=c['input'].get('messages',[])[steps[1]] if steps[0]=='messages' else {}
    field=steps[-1];base='A' if role=='system' else 'E';label='角色与执行规则' if base=='A' else '对话记录'
    provenance='框架组装；底层来源未证实';status='unresolved';identity=str(steps)
    if field in ('tool_calls','function_call'):
     base='F';label='输入中的实际工具调用';provenance='模型请求内 assistant 调用字段';status='observed'
    elif role in ('tools','functions'):
     base='B';label='可调用工具定义';provenance='实际请求的能力 Schema；配置上游未证实'
    elif role=='tool':
     base='F';label='模型可见工具返回 / 已加载内容';identity=msg.get('tool_call_id') or str(steps);provenance='实际请求的 tool 消息；内部完整返回不等于本消息';status='observed'
    elif role=='assistant':
     label='此前助手文本';provenance='实际请求保留的 assistant 消息；生成来源未进一步证实'
    elif role=='user':
     isquery=(text.strip()==query.strip() or text.startswith('【当前用户问题'))
     if isquery or c.get('scene')=='conversation_title_generate':base='D';label='当前请求 / 待生成标题的问题'
     elif c.get('scene')=='shop_risk_inspection_report_summary':base='F';label='巡检摘要器实际收到的风险 JSON'
     else:label='输入中的用户对话 / 任务记录'
     provenance='实际请求 user 消息；角色不单独证明原始来源'
    intervals=[(0,len(text),base,label)]
    def add(a,b,layer,title):
     if 0<=a<=b<=len(text):intervals.append((a,b,layer,title))
    def section(marker,endmarker,layer,title,start=0):
     a=text.find(marker,start)
     if a<0:return
     b=text.find(endmarker,a+len(marker)) if endmarker else -1
     add(a,b if b>=0 else len(text),layer,title)
    scene=c.get('scene')
    if role=='system':
     if text.startswith('<system-reminder>') and '可用技能（Skills）' in text[:80]:
      add(0,len(text),'B','可用 Skill 目录与触发描述')
     elif text.startswith('<task-reminder>') or '用户已指定希望使用 Skill：' in text[:100]:
      add(0,len(text),'D','本次任务范围 / 指定 Skill')
     elif text.startswith(('<custom-task-execution-context>','<custom-task-creation-attempt>')):
      add(0,len(text),'C','任务执行身份与当前状态')
      m=re.search(r'"instruction":',text)
      if m:add(m.start(),text.rfind('}')+1,'A','运行时身份使用与操作约束')
     elif text.startswith('请继续当前已授权的任务'):
      add(0,len(text),'A','运行时继续执行 / 终态协议提醒')
     elif text.startswith(('# 商家画像','## 商家与店铺概况','# Agent memory')):
      add(0,len(text),'E','注入的 Agent 记忆')
      marks=list(re.finditer(r'(?m)^#{1,3} (.+)$',text))
      for i,m in enumerate(marks):
       end=marks[i+1].start() if i+1<len(marks) else len(text)
       title=m.group(1);layer='C' if any(x in title for x in ['商家画像','商家与店铺概况','千川商家画像']) else 'E'
       add(m.start(),end,layer,title)
     elif scene in ('main_agent_loop_team','agent_loop_security_model'):
      marks=list(re.finditer(r'(?m)^# (.+)$',text))
      for i,m in enumerate(marks):
       if m.group(1) in ('使用你的工具','Available tools'):
        add(m.start(),marks[i+1].start() if i+1<len(marks) else len(text),'B',m.group(1))
     if scene=='agent_loop_runtime_compact':
      task=text.find('# 七、当前任务')
      if task>=0:
       add(task,len(text),'E','摘要器当前待整理记录')
       for marker,end,layer,title in [
        ('当前日期：','现有摘要：','C','摘要器当前日期'),
        ('现有摘要：','本次会话聊天记录：','E','已有会话摘要'),
        ('本次会话聊天记录：','本次会话工具调用记录：','E','待压缩会话记录'),
        ('本次会话工具调用记录：',None,'F','待压缩工具 / Skill 记录')]:section(marker,end,layer,title,task)
     elif scene=='suggest_stand':
      for tag,layer,title in [('当前时间','C','当前时间'),('预存标准词库','B','候选标准问法'),('原始问题','D','待标准化问题')]:
       m=re.search('<'+tag+r'>[\s\S]*?</'+tag+'>',text)
       if m:add(m.start(),m.end(),layer,title)
     elif scene=='qa_after_query_suggest_model':
      marks=list(re.finditer(r'(?m)^(?:## \[(.+)\]|# Output Format.*)$',text))
      for i,m in enumerate(marks):
       title=m.group(1);end=marks[i+1].start() if i+1<len(marks) else len(text)
       if title:add(m.start(),end,{'商家提问':'D','关联标准提问词':'B'}.get(title,'E'),title)
     elif scene=='intent_analyse':
      start=text.find('## 用户输入')
      if start>=0:
       marks=list(re.finditer(r'(?m)^### (.+)$',text[start:]))
       for i,m in enumerate(marks):
        a=start+m.start();b=start+marks[i+1].start() if i+1<len(marks) else len(text);title=m.group(1)
        add(a,b,{'最新问题':'D','记忆':'E','Agent列表':'B','当前时间':'C','商家画像':'C','简化分析':'A'}.get(title,'A'),title)
     elif scene=='suggest_sensitive_check':section('-- 用户的输入如下:',None,'D','本次待校验推荐问题')
     elif scene=='function_summary_1':
      start=text.rfind('# INPUT')
      if start>=0:
       section('## 用户问题','## 菜单功能','D','召回整理器收到的问题',start);section('## 菜单功能',None,'F','知识召回的菜单素材',start)
     elif scene=='new_shop_trusteeship_op_summary':
      section('上下文信息：','卡片标题：','E','用户与助手已有输出');section('卡片标题：',None,'F','卡片与动作素材')
    cuts=sorted({v for x in intervals for v in x[:2]})
    ranges=[]
    if not text: ranges=[(0,0,base,label)]
    for left,right in zip(cuts,cuts[1:]):
     active=next(x for x in reversed(intervals) if x[0]<=left and x[1]>=right)
     if ranges and ranges[-1][1]==left and ranges[-1][2:]==active[2:]:ranges[-1]=(ranges[-1][0],right,*active[2:])
     else:ranges.append((left,right,*active[2:]))
    for left,right,layer,title in ranges:
     piece=text[left:right]
     stability='fixed' if layer in 'AB' and role in ('system','tools','functions') else 'dynamic'
     # Content identity is scoped by scene, role, message/call identity and source semantics.
     key=(layer,title,provenance,scene,role,identity,piece)
     occ={'call':c['id'],'steps':steps,'ranges':[[left,right]]}
     if key not in contexts:
      contexts[key]={'id':'K%04d'%(len(contexts)+1),'layer':layer,'title':title,'stability':stability,'lifetime':'当前角色 / 场景配置' if stability=='fixed' else '当前请求可见范围',
       'source':{'label':provenance,'detail':'从 '+c['inputSource']+' 的 '+'.'.join(map(str,steps))+' 按内容区间提取。仅证明该请求可见；无证据时不推断数据库、接口或长期存储来源。','status':status,'refs':[c['spanId']]},
       'occurrences':[]}
     contexts[key]['occurrences'].append(occ)
  analysis={'reviewed':True,'title':wd.name+' · Trace Atlas','summary':raw_case['diagnosis']['concrete_root_cause'],'layers':mod.LAYERS,
   'phases':[{'id':'main','title':'业务主循环','description':'由实际 scene_code 识别'},{'id':'aux','title':'辅助生成 / 其他观测','description':'按开始时间展示，不建立未经核实的串行边'}],
   'calls':annotations,'contexts':list(contexts.values()),'edges':[],'notes':notes}
  # Validate complete input coverage for both confirmed and unconfirmed retained requests.
  checked=mod.check({**facts,'calls':allcalls},analysis)
  cby={a['id']:a for a in annotations}
  atlas={**facts,'schemaVersion':2,'displayId':wd.name,'title':analysis['title'],'summary':analysis['summary'],'layers':mod.LAYERS,
   'contexts':checked,'notes':notes,'phases':analysis['phases'],'edges':[],
   'calls':[{**c,**cby[c['id']]} for c in facts['calls']],
   'unconfirmed':[{**c,**cby[c['id']]} for c in facts['unconfirmed']],
   'sourceArchiveSha256':raw_case['viewer_evidence']['source_archive_sha256'],
   'businessEventCount':len(raw_case['trajectory']['events']),'businessModelRequestCount':sum(e['kind']=='main_llm' for e in raw_case['trajectory']['events'])}
  # Lossless string interning: full inputs/outputs/span data remain available without repeated large strings.
  strings=[];intern={}
  def pack(v):
   if isinstance(v,str) and len(v)>=80:
    if v not in intern:intern[v]=len(strings);strings.append(v)
    return {'$atlasString':intern[v]}
   if isinstance(v,list):return [pack(x) for x in v]
   if isinstance(v,dict):
    if set(v)=={'$atlasString'}:raise ValueError('reserved marker collision')
    return {k:pack(x) for k,x in v.items()}
   return v
  packed=pack(atlas);bundle={'format':'trace-atlas-strings-v1','strings':strings,'data':packed}
  def unpack(v):
   if isinstance(v,dict) and set(v)=={'$atlasString'}:return strings[v['$atlasString']]
   if isinstance(v,dict):return {k:unpack(x) for k,x in v.items()}
   if isinstance(v,list):return [unpack(x) for x in v]
   return v
  assert unpack(packed)==atlas
  body=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).encode()
  dest=cases/(wd.name+'.atlas.json');dest.write_bytes(body)
  (wd/'facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2))
  (wd/'analysis.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2))
  receipts.append({'id':wd.name,'file':dest.name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'counts':facts['counts'],'contexts':len(checked),'spans':len(facts['spans']),'validatedCoverage':True,'losslessInterning':True})
 indexpath=cases/'index.json';idx=json.loads(indexpath.read_text())
 by={r['id']:r for r in receipts}
 for item in idx['cases']:item['atlas']={k:v for k,v in by[item['id']].items() if k not in ('id',)}
 idx['trace_atlas']={'method':'Trace Atlas / trace-trajectory-dashboard 1.0.0, adapted for this retained ECOP corpus','counts':dict(sum((collections.Counter(r['counts']) for r in receipts),collections.Counter())),'cases':len(receipts)}
 indexpath.write_text(json.dumps(idx,ensure_ascii=False,indent=2))
 (work.parent/'v3-atlas-build-receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
 print(json.dumps({'cases':len(receipts),'bytes':sum(r['bytes'] for r in receipts),'contexts':sum(r['contexts'] for r in receipts),'counts':idx['trace_atlas']['counts'],'maxCaseBytes':max(r['bytes'] for r in receipts)},ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--adapter',type=Path,required=True);a=ap.parse_args();build(a.work,a.cases,a.adapter)
