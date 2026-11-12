# Skill audit 的 Trace Atlas 适配

本页采用 trace-trajectory-dashboard（Trace Atlas 1.0.0）的方法。事实抽取和语义分类分别保存；不是把单条示例的调用数或 Loop 编号复制到本批案例。

- 源是开发机留存的 43 份上游清洗 Trace 归档；不新增业务脱敏，不把归档放进 Git。
- 全树有 318 个 LLM Span。279 次有响应/生成证据，38 个未确认观测，1 个纯结构包装节点。业务子集为 300 个事件、160 次主循环请求，两种统计范围分开。
- C03 的嵌套 LLM 只留另一响应 ID，缺少请求与输出。无法证明独立生成，也不自动并入外层，列入未确认。
- 同响应 ID 但输入或输出冲突时停止自动去重；嵌套同 ID 且无独立输入的观测保留在 observations。不同 ID 不凭相同 prompt 合并。
- 保留请求名、SDK 配置名、实际返回名。失败/未确认观测没有可证实的实际返回模型，原日志报告字段另行保存，不能冒充实际模型。
- agent_loop_call_model 可能包裹失败和 fallback。仅 response_id 匹配才继承其输出和模型；否则失败节点不能借用 fallback 的成功结果。
- 支持标准 SDK payload、Ark messages 和 completion-result 留存消息。缺失 SDK 字段明确标明不可用，不从其他节点臆造。
- Loop 来自实际 runLoopOneTurn 祖先，并保留 scope ID。辅助调用即使在 Loop 内，也与主调用分组区分；时间顺序不自动构造因果边。
- 1,889 个上下文片段覆盖全部保留请求的 messages.content、tool_calls、function_call、tools/functions，包括未确认请求。混合 system 消息按精确字符范围拆为 A–F。
- 内容分类按本批真实模板与消息字段审阅；来源未被证实时保持 unresolved。输入可见与底层数据来源是两种不同证据。
- 原始输出优先 provider output_item.done/raw output_text.done；框架 final_answer 和最终商家交付分列。160 次主循环请求的输出与独立提取证据交叉核验一致。
- 案例与 Atlas JSON 通过 SHA-256/字节数逐案校验，按需加载。字符串池仅去掉重复存储，构建时逐值还原并断言完全相等，无截断。
- 原文用 textContent 展示。保持外部脚本 CSP，不引入 CDN。

重建只在开发机执行，输入工作目录含逐案例 source.json，cases 目录含冻结的原案例及索引：

    python3 scripts/build_skill_audit_atlas.py --work WORK --cases CASES --adapter scripts/skill_audit_atlas_extract.py

脚本产出逐案事实、审阅后的分类与校验记录。已验证覆盖并不代替来源语义审阅。公开 payload 不在 Git 中，普通源码克隆不能重建真实案例。
