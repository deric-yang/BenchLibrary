#!/usr/bin/env python3
"""Evidence-first ECOP trace extraction and dashboard assembly. Stdlib only."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LAYERS = [
    {'id': 'A', 'title': '角色与执行规则'},
    {'id': 'B', 'title': '可用能力与调用定义'},
    {'id': 'C', 'title': '身份与运行环境'},
    {'id': 'D', 'title': '当前请求与任务目标'},
    {'id': 'E', 'title': '对话记录与记忆'},
    {'id': 'F', 'title': '工具调用与返回'},
]


def decode(value):
    for _ in range(5):
        if not isinstance(value, str):
            break
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            break
    return value


def obj(value):
    value = decode(value)
    return value if isinstance(value, dict) else {}


def display(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def units(call):
    result = []
    for i, message in enumerate(call['input'].get('messages', [])):
        for field in ('content', 'tool_calls', 'function_call'):
            if field in message and message[field] is not None:
                result.append((['messages', i, field], message.get('role', 'unknown'), display(message[field])))
    for field in ('tools', 'functions'):
        if field in call['input']:
            result.append(([field], field, display(call['input'][field])))
    return result


def extract(raw):
    trace = json.loads(raw)
    root = trace.get('root_span')
    if not isinstance(root, dict):
        raise ValueError('Unsupported trace: expected ECOP root_span object. Adapt the parser first.')
    spans, ancestors, paths = [], {}, {}
    seen = set()

    def walk(span, parents, path):
        sid = span.get('span_id')
        if not sid or sid in seen:
            raise ValueError('Missing or duplicate span_id; inspect trace before deduplication')
        seen.add(sid)
        spans.append(span)
        ancestors[sid], paths[sid] = parents, path
        for i, child in enumerate(span.get('children') or []):
            walk(child, parents + [span], path + f'/children/{i}')

    walk(root, [], '/root_span')
    start = root['start_time']
    leaves = sorted([s for s in spans if s.get('span_code') == 'LLM'], key=lambda s: s['start_time'])
    if not leaves:
        raise ValueError('No supported LLM spans found; do not report zero calls without inspection')
    calls, unconfirmed, dedup, warnings, wrappers = [], [], {}, [], []
    for span in leaves:
        sid = span['span_id']
        inp, out, ctx = (obj(span.get(k)) for k in ('input', 'output', 'context_data'))
        payload = obj(inp.get('payload'))
        sdk = obj(payload.get('open_ai_sdk_payload'))
        input_source = 'payload.open_ai_sdk_payload'
        comp = next((obj(v) for k, v in ctx.items() if k.endswith('llm_completion_result')), {})
        if not isinstance(sdk.get('messages'), list):
            if isinstance(inp.get('ark_messages'), list):
                sdk = {k:v for k,v in inp.items() if k in ('model','temperature','tools') and v is not None}
                sdk['messages'] = inp['ark_messages']
                input_source = 'input.ark_messages'
            elif isinstance(comp.get('messages'), list):
                sdk = {'messages':comp['messages']}
                input_source = 'context_data.*_llm_completion_result.messages; other SDK fields unavailable'
            else:
                sdk = {}
                input_source = 'unavailable'
                response_id = out.get('response_id')
                previous = dedup.get(response_id)
                if previous and previous[0]['spanId'] in [p['span_id'] for p in ancestors[sid]]:
                    previous[0]['observations'].append({'spanId':sid,'path':paths[sid],'relation':'nested response-id alias; input omitted'})
                    continue
                if not out and any(c.get('span_code') == 'LLM' for c in span.get('children') or []):
                    wrappers.append({'spanId':sid,'path':paths[sid],'reason':'No request/response evidence; contains child LLM observation'})
                    continue
                warnings.append(f'{sid}: SDK input unavailable; response evidence retained independently')
        parents = ancestors[sid]
        wrapper = next((s for s in reversed(parents) if s.get('span_code') == 'agent_loop_call_model'), None)
        loop = next((s for s in reversed(parents) if s.get('span_code') == 'runLoopOneTurn'), None)
        result = obj(obj(wrapper.get('output')).get('llmResult')) if wrapper else {}
        if result and (out.get('error') or not out.get('response_id') or result.get('response_id') != out.get('response_id')):
            result = {}
        last = obj(out.get('lastResponse'))
        comp = next((obj(v) for k, v in ctx.items() if k.endswith('llm_completion_result')), {})
        choice = (last.get('choices') or [{}])[0]
        message = obj(choice.get('message'))
        raw_texts = []
        for event in out.get('provider_item_events') or []:
            event = obj(event)
            if event.get('type') == 'response.output_item.done':
                for block in obj(event.get('item')).get('content') or []:
                    if isinstance(block,dict) and isinstance(block.get('text'),str):
                        raw_texts.append(block['text'])
        if not raw_texts and result and wrapper:
            raw_output = obj(obj(wrapper.get('output')).get('raw_model_output'))
            for event in raw_output.get('events') or []:
                event = obj(event)
                if event.get('type') == 'output_text.done' and isinstance(event.get('text'),str):
                    raw_texts.append(event['text'])
        raw_source = 'provider/raw output event' if raw_texts else 'LLM response field'
        text = '\n'.join(raw_texts) if raw_texts else (out.get('streamText') or out.get('content') or message.get('content') or obj(choice.get('delta')).get('content') or '')
        if not text and result.get('final_answer'):
            text = result['final_answer']
            raw_source = 'wrapper normalized final_answer; raw model text unavailable'

        tool_calls = result.get('tool_calls') or out.get('tool_calls') or message.get('tool_calls') or []
        response_id = out.get('response_id') or last.get('id') or comp.get('id')
        provider_model = result.get('model') or last.get('model') or comp.get('model')
        evidence = 'response_id' if response_id else ('observed_output' if text or tool_calls else 'unconfirmed')
        loop_info = None
        if loop:
            loop_parents = ancestors[loop['span_id']]
            loop_info = {'spanId': loop['span_id'], 'name': loop.get('span_name', ''),
                         'scopeId': loop_parents[-1]['span_id'] if loop_parents else None,
                         'scopeName': loop_parents[-1].get('span_name', '') if loop_parents else None}
        call = dict(spanId=sid, responseId=response_id, model=inp.get('model'), sdkModel=sdk.get('model'),
                    providerModel=provider_model, scene=payload.get('scene_code') or inp.get('scene_code') or obj(ctx.get('ark_sampling_params')).get('scene_code'),
                    start=(span['start_time'] - start) / 1e9, duration=span['duration'] / 1e9 if span.get('duration') is not None else None,
                    status=span.get('status'), usage=comp.get('usage') or out.get('usage') or last.get('usage') or {},
                    input=sdk, inputSource=input_source, outputSource=raw_source, output={'text': text, 'tool_calls': tool_calls, 'reasoning': out.get('reasoning')},
                    rawOutput=out, loop=loop_info, confirmation=evidence,
                    observations=[{'spanId': sid, 'path': paths[sid]}],
                    evidence={'path': paths[sid], 'wrapper': wrapper['span_id'] if wrapper else None,
                              'ancestors': [p['span_id'] for p in parents]})
        if evidence == 'unconfirmed':
            call['id'] = f'U{len(unconfirmed)+1:02d}'
            unconfirmed.append(call)
            continue
        # Do not collapse equal prompts with different response IDs.
        signature = json.dumps([sdk, call['output'], provider_model], sort_keys=True, ensure_ascii=False)
        if response_id and response_id in dedup:
            previous, old_signature = dedup[response_id]
            if old_signature != signature:
                raise ValueError(f'Conflicting observations for response {response_id}; review manually')
            previous['observations'] += call['observations']
            continue
        call['id'] = f'N{len(calls)+1:02d}'
        calls.append(call)
        if response_id:
            dedup[response_id] = (call, signature)
        else:
            warnings.append(f"{call['id']}: 无响应 ID，按独立 LLM Span 的生成内容计入；需审阅包装/重试关系")
    structures = []
    for s in spans:
        sid = s['span_id']
        parents = ancestors[sid]
        structures.append(dict(id=sid, parent=parents[-1]['span_id'] if parents else None,
                               sourceParent=s.get('parent_span_id'), name=s.get('span_name'), code=s.get('span_code'),
                               depth=len(parents), start=(s['start_time'] - start)/1e9,
                               duration=s.get('duration', 0)/1e9, status=s.get('status'), path=paths[sid],
                               children=[c['span_id'] for c in s.get('children') or []],
                               input=decode(s.get('input')), output=decode(s.get('output')),
                               context=decode(s.get('context_data'))))
    return dict(schemaVersion=1, traceId=trace.get('trace_id'), sha256=hashlib.sha256(raw).hexdigest(),
                duration=root.get('duration', 0)/1e9, timeUnit='ECOP nanoseconds → seconds',
                spanCount=len(spans), calls=calls, unconfirmed=unconfirmed, spans=structures,
                finalResponse=decode(trace.get('response')), request=decode(trace.get('request')),
                warnings=warnings, structuralLLMWrappers=wrappers, counts={'llmObservations': len(leaves), 'confirmed': len(calls),
                                          'unconfirmed': len(unconfirmed), 'structuralWrappers':len(wrappers), 'duplicateObservations':sum(len(c['observations'])-1 for c in calls)})


def draft(facts):
    contexts = []
    for call in facts['calls']:
        for steps, role, text in units(call):
            layer = 'B' if role in ('tools', 'functions') else ('A' if role == 'system' else 'F')
            contexts.append(dict(id=f'X{len(contexts)+1:03d}', layer=layer,
                                 title=f"待归类 · {call['id']} · {'.'.join(map(str,steps))}", pending=True,
                                 stability='mixed', lifetime='待核对',
                                 source={'label': '待核对来源', 'detail': '从实际模型请求提取；内容类别与来源需逐段审阅',
                                         'status': 'unresolved', 'refs': [call['spanId']]},
                                 occurrences=[{'call': call['id'], 'steps': steps}]))
    return dict(reviewed=False, title='待审阅的 Trace 轨迹', summary='', layers=LAYERS,
                phases=[{'id': 'review', 'title': '待审阅分组', 'description': '按时间排列不代表串行'}],
                calls=[dict(id=c['id'], title=c.get('scene') or c['id'], agent='待核对', purpose='', phase='review')
                       for c in facts['calls']], contexts=contexts, edges=[], notes=[])


def check(facts, analysis):
    if analysis.get('reviewed') is not True:
        raise ValueError('Review analysis.json and set reviewed=true after checking evidence')
    calls = {c['id']: c for c in facts['calls']}
    annotations = analysis.get('calls', [])
    if len(annotations) != len(calls) or {c['id'] for c in annotations} != set(calls):
        raise ValueError('Call annotations must cover every confirmed call exactly once')
    phases = {p['id'] for p in analysis['phases']}
    layers = {l['id'] for l in analysis.get('layers', LAYERS)}
    if not analysis.get('title') or not analysis.get('summary'):
        raise ValueError('Title and summary are required')
    for a in annotations:
        if set(a) - {'id', 'title', 'agent', 'purpose', 'phase'}:
            raise ValueError(f"Call annotations cannot replace extracted evidence: {a.get('id')}")
        if a.get('phase') not in phases or not all(a.get(k) for k in ('title', 'agent', 'purpose')):
            raise ValueError(f"Incomplete call annotation: {a.get('id')}")
    available = {}
    coverage = {}
    for call in calls.values():
        for steps, role, text in units(call):
            key = (call['id'], json.dumps(steps))
            available[key] = (role, text)
            coverage[key] = []
    result, seen = [], set()
    refs = {s['id'] for s in facts['spans']} | set(calls)
    for context in analysis.get('contexts', []):
        cid = context['id']
        if cid in seen or context.get('pending') or context.get('layer') not in layers:
            raise ValueError(f'Unreviewed, duplicate or invalid context: {cid}')
        seen.add(cid)
        source = context.get('source', {})
        if context.get('stability') not in ('fixed', 'dynamic', 'mixed') or not context.get('lifetime'):
            raise ValueError(f'{cid}: missing stability/lifetime')
        if source.get('status') not in ('observed', 'inferred', 'unresolved') or not source.get('label') or not source.get('detail'):
            raise ValueError(f'{cid}: source and evidence status required')
        if not set(source.get('refs', [])) <= refs:
            raise ValueError(f'{cid}: source references unknown evidence')
        selected, readers, roles = [], [], set()
        for occ in context.get('occurrences', []):
            key = (occ['call'], json.dumps(occ['steps']))
            if key not in available:
                raise ValueError(f'{cid}: unsupported input locator {key}')
            role, text = available[key]
            ranges = occ.get('ranges', [[0, len(text)]])
            if not ranges:
                raise ValueError(f'{cid}: empty ranges')
            parts = []
            for left, right in ranges:
                if not isinstance(left, int) or not isinstance(right, int) or not 0 <= left <= right <= len(text):
                    raise ValueError(f'{cid}: invalid character range')
                parts.append(text[left:right])
                coverage[key].append((left, right))
            selected.append(''.join(parts))
            readers.append(occ['call'])
            roles.add(role)
        if not selected or len(set(selected)) != 1:
            raise ValueError(f'{cid}: all occurrences must select identical text; split changed versions')
        order = {cid: i for i, cid in enumerate(calls)}
        readers = sorted(set(readers), key=order.get)
        result.append({**context, 'text': selected[0], 'readers': readers,
                       'firstSeen': readers[0], 'roles': sorted(roles)})
    for key, intervals in coverage.items():
        end = 0
        if not intervals:
            raise ValueError(f'Uncovered input unit: {key}')
        for left, right in sorted(intervals):
            if left > end:
                raise ValueError(f'Uncovered characters at {key}: {end}..{left}')
            end = max(end, right)
        if end != len(available[key][1]):
            raise ValueError(f'Uncovered tail at {key}: {end}')
    for edge in analysis.get('edges', []):
        if edge.get('from') not in calls or edge.get('to') not in calls or not edge.get('label'):
            raise ValueError('Edge must cite existing calls and explain the relationship')
    return result


def load_work(work):
    facts = json.loads((work/'facts.json').read_text())
    # Detect edits to deterministic facts: analysis belongs in analysis.json.
    original = (work/'source.json').read_bytes()
    if extract(original) != facts:
        raise ValueError('facts.json differs from source extraction; re-prepare or review parser changes')
    return facts, json.loads((work/'analysis.json').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('source', type=Path)
    prep.add_argument('--out', type=Path, required=True)
    for name in ('validate', 'build'):
        command = sub.add_parser(name)
        command.add_argument('--work', type=Path, required=True)
        if name == 'build':
            command.add_argument('--out', type=Path, required=True)
            command.add_argument('--include-original', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        if any((args.out/f).exists() for f in ('source.json', 'facts.json', 'analysis.json')):
            raise ValueError('Work files already exist; choose another work directory')
        raw = args.source.read_bytes()
        facts = extract(raw)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out/'source.json').write_bytes(raw)
        write_json(args.out/'facts.json', facts)
        write_json(args.out/'analysis.json', draft(facts))
        print(json.dumps({'counts': facts['counts'], 'sha256': facts['sha256'], 'reviewRequired': True}))
        return
    facts, analysis = load_work(args.work)
    contexts = check(facts, analysis)
    if args.command == 'build':
        args.out.mkdir(parents=True, exist_ok=True)
        for filename in ('index.html', 'app.js', 'styles.css'):
            shutil.copyfile(BASE/'assets'/filename, args.out/filename)
        annotations = {c['id']: c for c in analysis['calls']}
        data = {**facts, **{k: analysis[k] for k in ('title', 'summary', 'phases', 'edges', 'notes')},
                'layers': analysis.get('layers', LAYERS), 'contexts': contexts,
                'calls': [{**c, **annotations[c['id']]} for c in facts['calls']],
                'originalAvailable': args.include_original}
        # Standalone JS avoids file:// fetch restrictions. Data is rendered only via textContent.
        text = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        (args.out/'data.js').write_text('window.TRACE_DATA = '+text+';\n', encoding='utf-8')
        target = args.out/'trace-original.json'
        if args.include_original:
            shutil.copyfile(args.work/'source.json', target)
        elif target.exists():
            target.unlink()
    print(json.dumps({'validated': True, 'calls': len(facts['calls']), 'contexts': len(contexts),
                      'unconfirmed': len(facts['unconfirmed'])}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
