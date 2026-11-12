import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('readable',Path(__file__).parents[1]/'scripts/build_skill_audit_readable.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class ReadableEvidenceTests(unittest.TestCase):
 def test_nested_action_json_keeps_quotes(self):
  payload={'items':[{'title':'售后单','button':{'text':'查看详情','action':{'options':{'post_body':json.dumps({'action':'callback','content':{'id':'demo'}})}}}}]}
  side='<ui-container>\n<ui-suggestions-list>'+json.dumps(payload,ensure_ascii=False)+'</ui-suggestions-list></ui-container>'
  obj={'action':{'options':{'post_body':json.dumps({'sideMixedContent':side})}}}
  result=b.component('ui-result-preview',obj,0)
  self.assertEqual(result['blocks'][0]['kind'],'business_lines')
  self.assertIn('售后单',result['blocks'][0]['lines'])
  self.assertNotIn('callback',str(result))
 def test_business_history_excludes_system_tools_and_injection(self):
  msgs=[{'role':'system','content':'secret'},{'role':'user','content':'上一问'},{'role':'assistant','content':'上一答'},{'role':'tool','content':'protocol'},{'role':'user','content':'<system-reminder>internal</system-reminder>'},{'role':'user','content':'【当前用户问题】本轮\n\n## 行动点提交上下文\ninternal'}]
  d={'trajectory':{'events':[{'kind':'main_llm','message_tail':msgs}],'source_query':'本轮','historical_answer':'完成'},'viewer_evidence':{'root_span_code':'ChatStream','first_context_current_query_index':None}}
  result=b.chat(d)
  self.assertEqual(result['anchor_index'],5)
  self.assertEqual([m['role']for m in result['history']],['user','assistant'])
  self.assertEqual(len(result['omitted_injected_user_messages']),1)
 def test_placeholder_is_not_delivered_answer(self):
  self.assertEqual(b.delivery('<action-demo>')[0]['kind'],'unavailable')
 def test_missing_verdict_stays_unknown(self):
  d={'historical_machine_evaluation':{'labels':{}},'viewer_evidence':{'selection_group':'target_loaded_historical_fail'}}
  result=b.metrics(d)
  self.assertEqual(len(result['all']),25)
  self.assertTrue(all(x['label']=='unknown'for x in result['all']))
  self.assertFalse(result['triggers'])
 def test_only_real_loop_ancestors_form_rows(self):
  spans=[{'id':'root','parent':None,'code':'root','name':'root','start':0,'duration':2,'path':'/root'},{'id':'loop','parent':'root','code':'runLoopOneTurn','name':'Loop执行-1','start':0,'duration':2,'path':'/root/loop'},{'id':'aux','parent':'loop','code':'llm_request','name':'辅助生成','start':0,'duration':1,'path':'/root/loop/aux'}]
  a={'spans':spans,'calls':[],'unconfirmed':[],'counts':{}}
  self.assertEqual(len(b.loops({},a)['rows']),1)
if __name__=='__main__':unittest.main()
