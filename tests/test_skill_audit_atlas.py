
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("atlas_extract", Path(__file__).resolve().parents[1] / "scripts/skill_audit_atlas_extract.py")
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)

def span(sid, code="LLM", inp=None, out=None, children=None, ctx=None):
    return {"span_id": sid, "span_name": code, "span_code": code, "start_time": 0,
            "duration": 1000000000, "input": inp, "output": out,
            "context_data": ctx or {}, "children": children or []}

def sdk():
    return {"model": "requested-alias", "payload": {"scene_code": "main_agent_loop_team",
            "open_ai_sdk_payload": {"model": "sdk-alias", "messages": [{"role": "user", "content": "test"}]}}}

def extract(root):
    return atlas.extract(json.dumps({"root_span": root}).encode())

class AtlasExtractionTests(unittest.TestCase):
    def test_failed_retry_cannot_borrow_successful_wrapper_output(self):
        failed = span("failed", inp=sdk(), out={"error": "unavailable"})
        success = span("success", inp=sdk(), out={"response_id": "r1"})
        wrapper = span("wrapper", "agent_loop_call_model", out={
            "llmResult": {"response_id": "r1", "model": "actual-provider", "final_answer": "normalized"},
            "raw_model_output": {"events": [{"type": "output_text.done", "text": "<final-output>raw"}]}
        }, children=[failed, success])
        data = extract(span("root", "ChatStream", children=[wrapper]))
        self.assertEqual(len(data["unconfirmed"]), 1)
        self.assertEqual(data["unconfirmed"][0]["output"]["text"], "")
        self.assertIsNone(data["unconfirmed"][0]["providerModel"])
        self.assertEqual(data["calls"][0]["output"]["text"], "<final-output>raw")
        self.assertEqual(data["calls"][0]["providerModel"], "actual-provider")

    def test_ark_request_and_observed_content_are_preserved(self):
        data = extract(span("ark", inp={"ark_messages": [{"role": "system", "content": "rule"}],
                                      "model": "ark-alias", "temperature": 0.1, "scene_code": "function_summary_1"},
                            out={"content": "answer"}))
        call = data["calls"][0]
        self.assertEqual(call["input"]["messages"][0]["content"], "rule")
        self.assertEqual(call["confirmation"], "observed_output")
        self.assertEqual(call["inputSource"], "input.ark_messages")
        self.assertIsNone(call["providerModel"])

    def test_conflicting_response_id_stops_deduplication(self):
        a = span("a", inp=sdk(), out={"response_id": "r", "streamText": "one"})
        b = span("b", inp=sdk(), out={"response_id": "r", "streamText": "two"})
        with self.assertRaisesRegex(ValueError, "Conflicting observations"):
            extract(span("root", "ChatStream", children=[a, b]))

    def test_structural_wrapper_not_counted_as_request(self):
        child = span("child", inp={"model": "ep-alias"},
            out={"lastResponse": {"id": "r", "model": "actual", "choices": [{"delta": {"content": "title"}}]}},
            ctx={"conversation_title_generate_llm_completion_result": {"messages": [{"role": "user", "content": "question"}]}})
        data = extract(span("root", "ChatStream", children=[span("wrap", inp={"ClientStream": None}, children=[child])]))
        self.assertEqual(data["counts"]["llmObservations"], 2)
        self.assertEqual(data["counts"]["confirmed"], 1)
        self.assertEqual(data["counts"]["unconfirmed"], 0)
        self.assertEqual(data["counts"]["structuralWrappers"], 1)
        self.assertIn("context_data", data["calls"][0]["inputSource"])

    def test_nested_same_identity_alias_keeps_observation_without_extra_generation(self):
        child = span("child", inp={"model": "transport-alias"}, out={"response_id": "r"})
        parent = span("parent", inp=sdk(), out={"response_id": "r", "streamText": "answer"}, children=[child])
        data = extract(span("root", "ChatStream", children=[parent]))
        self.assertEqual(data["counts"]["confirmed"], 1)
        self.assertEqual(data["counts"]["duplicateObservations"], 1)
        self.assertEqual(len(data["calls"][0]["observations"]), 2)

if __name__ == "__main__":
    unittest.main()
