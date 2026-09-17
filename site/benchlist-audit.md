# BenchList · 公开发布引用审计

核验日期：2026-09-14。

仅计入有第一方来源的自身发布正文或附录证据；对照列和第三方结果不增加计数。
按统计模型去重；GPT-5.6 变体合并，GPT-6 独立。没有证据不代表未参评。
模型覆盖率分母包括窗口内未取得引用证据的模型；月度趋势按实际型号发布日期归月。
这是人工核验快照，日期未自动滚动；引用频次不代表性能得分。

## GDPval-AA v2

以 OpenAI GDPval 公开职业任务为基础，Artificial Analysis 用统一代理框架生成交付物并盲评排序；v2 是 AA 评测口径版本，结果通常以 Elo 表示。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table 2；p26 General Agent methodology
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p182 §8.13.4 GDPval-AA v2
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p193 GDPval-AA v2
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：GDPval-AA v2 行
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：GDPval-AA v2 行
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：GDPval-AA v2 行
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals 表：GDPval-AA v2 行
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p1 GDPval-AA v2
- Gemini 3.6 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-6-flash/) · Capabilities 表：GDPval-AA v2 行
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Capabilities 表：GDPval-AA v2 行
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-8-flash/) · Capabilities 表：GDPval-AA v2 行
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark Results：GDPval-AA v2 行
- GLM-5.3-Flash：[发布来源](https://huggingface.co/zai-org/GLM-5.3-Flash) · 评测图及 GDPval-AA v2 方法脚注
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Benchmark 表：GDPval-AA v2 (ELO)
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，GDPval-AA v2 official 行
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p134 §8.11.4
- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/) · Evaluation / Results，July2026表，自身列
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / GDPval-AA v2
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / AGENTIC / GDPval-AA v2
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-methodology) · PDF p2 / benchmark方法
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p2 / General Agentic
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → GDPval-AA v2 (ELO)
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → GDPval-AA v2 行 → Solar Pro 4 列

## AA-Briefcase

Artificial Analysis 的长程知识工作评测，完整集包含四个多周项目、91个任务和大量工作文件；公开 Lite 示例为四个任务，并非完整四个项目开放。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：AA-Briefcase；p26外部评测说明
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals 表：AA-Briefcase
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p182 AA-Briefcase
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p193 AA-Briefcase
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p137 §8.11.7

## GDP.pdf

Surge AI 的专业 PDF 接地推理基准，专家设计问题与分项rubric，考查表格、图表、跨页证据和多文档综合，公开任务与原始PDF。

- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-8-flash/) · Capabilities 表：GDP.PDF (all pass)
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Capabilities 表：GDP.pdf
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表：gdp.pdf 行
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表：gdp.pdf 行
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表：gdp.pdf 行
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p252 Table8.1.A：GDP.pdf
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p125 §8.10.1

## APEX-Agents

Mercor 的跨应用专业代理任务基准，覆盖投资银行、管理咨询、公司法务；模型需操作工作文件和软件并完成可评阅交付物。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：APEX-Agents
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals 表：APEX-Agents
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · p9 Table1：APEX Agents；p8方法
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · p9 Table1：APEX Agents；p8方法
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Benchmark 表：APEX-Agents
- MiniMax M3：[发布来源](https://huggingface.co/MiniMaxAI/MiniMax-M3/resolve/main/figures/benchmark.jpeg) · Cowork 表：Apex-Agents；表下方法
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，APEX-Agents (Pass@1) 行
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / APEX-Agents
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → APEX-Agents
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → APEX-Agents 行 → Solar Pro 4 列
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · APEX Agents · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · APEX Agents · Seed2.1 Pro 列

## AutomationBench

Zapier AutomationBench 评估代理发现并调用API、遵循业务规则、跨SaaS应用执行工作流并达到目标状态；公开任务与私有held-out分开计量。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Professional work 表：AutomationBench
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Tool use 表：AutomationBench
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Tool use 表：AutomationBench
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Tool use 表：AutomationBench
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p195 AutomationBench
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p183–184 AutomationBench
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p2 AutomationBench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark Results：AutomationBench；方法脚注
- GLM-5.3-Flash：[发布来源](https://huggingface.co/zai-org/GLM-5.3-Flash) · 评测图与AutomationBench方法脚注
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2；p26方法
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · p32 方法、p33 Table3：Automation-Bench (Pass@1)
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · General Agent 表：Automation-Bench (Pass@1)
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Capabilities 表：AutomationBench；方法链接
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，AutomationBench v1.0.6 行
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p295–296 AutomationBench
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Introduction 评测表：AutomationBench (Public)
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Introduction 评测表：AutomationBench (Public)
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p136 §8.11.6
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / AutomationBench Public
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / AutomationBench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / AutomationBench (v1.0.6)
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / AGENTIC / AutomationBench v1.0.6
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / AutomationBench v1.0.6
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## SpreadsheetBench v2

正式名称 SpreadsheetBench2，覆盖真实商业电子表格的生成、调试、可视化等工作流，要求对复杂多表工作簿进行规划、修改和验证。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：SpreadsheetBench2

## AA-AnalystAgent Bench

Artificial Analysis 的私有定量代理任务集，使用电子表格和文档回答业务及科学分析问题；80题、14领域，公开少量示例。


## Finance Agent Bench v2

Vals Finance Agent Benchmark v2 评估金融研究代理使用SEC文件、网页检索、历史价格和计算工具进行多源研究；927道专家审核题，设public/validation/held-out分区。

- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p290 §8.17.2 Finance Agent
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：FinanceAgentv2；p26外部评测说明
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p224 Finance Agent
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-8-flash/) · Capabilities 表：Vals Finance Agent v2
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列

## JobBench

JobBench以65个任务、35种职业为核心，用异构且可能矛盾的业务材料要求代理完成可核验工作产物，提供专家rubric及人类自动化意愿分析。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：JobBench；p26方法
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p1–2 JobBench
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，JobBench 行
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Benchmark Results / Language / Agent：JobBench
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Benchmark Results / Language / Agent：JobBench
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · General Agent 表：JobBench
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / JobBench
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## Apex-Accounting

Mercor与Ramp共同构建的月末结账与会计代理评测；160个held-out任务、10个业务世界，另开放第11个示例世界与运行框架。


## Harvey Legal Agent Bench

Harvey Legal Agent Benchmark 是复杂法律代理工作的公开评测资源；另有Artificial Analysis LAB-AA与Vals held-out评测，任务集、评分方式和开放状态须分别标注。

- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p181 §8.13.3 Legal Agent Benchmark
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p192–193 §8.15.2 Legal Agent Benchmark
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：Harvey LAB-AA；p26方法
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-8-flash/) · Capabilities 表：Harvey LAB (all pass)；linked methodology
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals 表：Harvey LAB (Vals)
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p292 Legal Agent Benchmark
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p224 Legal Agent Benchmark
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Capabilities 表：Harvey LAB-AA
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p133–134 §8.11.3

## DRACO

Perplexity于2026年2月提出的深度研究评测，从真实用户请求构造任务，覆盖十个领域，检查多源研究报告的事实、覆盖、表达和引用。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p178–179 §8.12.2 DRACO
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p165–166 §8.10.4 DRACO
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p207–209 DRACO
- Claude Opus 4.7：[发布来源](https://anthropic.com/claude-opus-4-7-system-card) · p201 DRACO
- MiniMax M3：[发布来源](https://huggingface.co/MiniMaxAI/MiniMax-M3/resolve/main/figures/benchmark.jpeg) · Cowork表 DRACO 行；底部DRACO方法
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p268–269 §8.14.4 DRACO；Figure8.14.4.A
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，DRACO 行及脚注

## ResearchRubrics

Scale于2025年11月推出的开放式研究评测，101个问题配专家编写的加权分项rubric，支持检查研究回答的完整性与正确性。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 正文 Table2：ResearchRubrics；p28正文分析
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → ResearchRubrics

## Agents' Last Exam

Agents' Last Exam评估在专业软件与可执行环境中完成高价值职业任务的长程代理；同时提供严格完成率与分项成绩，存在ALE-CLI等子集/执行口径。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Computer use / Agents' Last Exam
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：Agents' Last Exam
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：Agents' Last Exam
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Professional 表：Agents' Last Exam
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Evaluation / Results：Agent's Last Exam 行；方法PDF p3
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark Results：Agents' Last Exam (ALE-CLI)
- GLM-5.3-Flash：[发布来源](https://huggingface.co/zai-org/GLM-5.3-Flash) · 评测图：Agents' Last Exam；方法脚注
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2；p26方法
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Introduction评测表：Agents' Last Exam
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Introduction评测表：Agents' Last Exam
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · General Agent 表：ALE (Pass/Score)
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Language / Agent表：Agents' Last Exam
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Language / Agent表：Agents' Last Exam
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · p32 方法、p33 Table3：Agents’ Last Exam (Pass@1)
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/blog/seed2-1-officially-released-advancing-ai-productivity) · General agent 部分：ALE专段和双图说明
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Knowledge Work / Agent 区，ALE-CLI 行及脚注
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / Agents’ Last Exam
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / Agent’s Last Exam
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / Agents’ Last Exam (ALE-CLI)
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / AGENTIC / Agents’ Last Exam
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · Agents’ Last Exam

## ArtifactsBench

ArtifactsBench以1825个任务评估视觉代码生成，覆盖SVG、数据可视化、Web应用和交互内容；结合实际渲染、功能/交互与多模态裁判评价。

- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Benchmark表：ArtifactsBench
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → ArtifactsBench

## τ³-Banking

Sierra τ-Knowledge 引入银行客服场景τ-Banking（AA及模型报告常标τ³-Banking）；代理与用户模拟器对话，从698篇政策文档检索规则并调用工具完成目标状态。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：τ³-Banking；p26第三方AA说明
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Benchmark表：τ³-Banking
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p2 / General Agentic
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → τ³-Banking
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → τ³-Banking 行 → Solar Pro 4 列

## OfficeQA Pro V2

OfficeQA Pro V2于2026年8月发布，包含90个更难的多文档问题，以美国财政部历史报告PDF语料检查解析、检索与接地推理。


## Terminal-Bench 4.0

Stanford/Harbor/Laude 的终端工作流评测；4.0含66题，统一8小时预算并更新资源、验证器，删除8题、修复19题。结果必须固定版本、harness、effort及试验次数。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-and-mythos-5-1) · A new performance frontier / Terminal-Bench 4.0
- Claude Mythos 5.1：[发布来源](https://www.anthropic.com/claude-fable-and-mythos-5-1) · Terminal-Bench 4.0 图及表
- Gemini 3.8 Flash：[发布来源](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) · 发布页完整性能表 / Terminal-Bench 4.0
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Benchmark Results / Agentic
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Coding 表 / Terminal-Bench 4.0

## DeepSWE v1.1

Datacurve原创软件工程任务集：113题、91个仓库、5种语言。v1.1采用独立环境验证提交补丁；参考实现不回传上游，旨在降低公开PR答案泄漏风险。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · p168 §8.3
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · p153 §8.3
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / DeepSWE v1.1
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / DeepSWE v1.1
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / DeepSWE v1.1
- Gemini 3.8 Flash：[发布来源](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) · 发布性能表 / DeepSWE v1.1
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · pp2–3 Software engineering
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Agentic / DeepSWE v1.1
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Appendix / Coding Agent / DeepSWE 1.1
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · pp26–27 Evaluation setup / Table 2
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / DeepSWE v1.1
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals / DeepSWE v1.1
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Coding 表 / DeepSWE v1.1
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / DeepSWE1.1
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / DeepSWE1.1
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / DeepSWE (v1.1)
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / CODING / DeepSWE v1.1
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / DeepSWE1.1
- Grok 4.5：[发布来源](https://x.ai/news/grok-4-5) · Real-world engineering excellence / 自身柱与文字表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-methodology) · PDF p2 / benchmark方法
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## FrontierCode 1.1

Cognition 的代码可合并性评测：Extended 150题、Main为最难100题。来源于开源项目真实PR，maintainer撰写任务与评分标准；v1.1区分合法查文档和查答案，违规网络取答案计零。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · pp168–170 §8.4
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · pp154–156 §8.4
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals / FrontierCode v1.1 Extended
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Coding 表 / FrontierCode Main、Extended

## NL2Repo-Bench

NL2RepoBench要求从自然语言规格生成完整可运行仓库，官方104题，每题配套测试环境。与修改已有仓库的任务互补。

- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Agentic / NL2Repo-Bench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / NL2Repo；Footnotes
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / NL2Repo-Bench
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / NL2Repo-Bench；Notes
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Appendix / Coding Agent / NL2Repo-Bench
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / NL2Repo
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Evaluation / NL2Repo
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Evaluation / NL2Repo
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / NL2Repo
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / NL2Repo
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / NL2Repo-Bench
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / NL2Repo-Bench
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / NL2Repo
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / Summary / NL2Repo
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / NL2Repo
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / NL2Repo
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / NL2Repo
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / CODING / NL2Repo
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / NL2repo
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / NL2repo
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / NL2Repo-Bench
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → NL2Repo-Bench
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · NL2Repo-Bench
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · NL2Repo-Bench

## Terminal-Bench 2.1

Terminal-Bench 2.1是2.0的89题修订版，官方公告说明修复28题。可用于同版本历史横向比较；AA当前v1.5已用4.0替换2.1。

- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / Terminal-Bench 2.1
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / Terminal-Bench 2.1
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / Terminal-Bench 2.1
- Gemini 3.8 Flash：[发布来源](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) · 发布性能表 / Terminal-Bench 2.1
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p3 Terminal-Bench2.1
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Agentic / Terminal-Bench 2.1
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Appendix / Coding Agent / Terminal Bench2.1
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · pp26–27 / Table2
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark及Footnotes / Terminal Bench2.1
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / Terminal Bench2.1
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / Terminal-Bench 2.1；Notes
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p115–117 §8.3
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/) · Evaluation / Results，July2026表，自身列
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / Terminal Bench 2.1
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Evaluation / Terminal Bench 2.1
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Evaluation / Terminal Bench 2.1
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / Terminal Bench 2.1
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / Terminal Bench 2.1
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / Terminal Bench 2.1
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / CODING / Terminal Bench 2.1
- Grok 4.5：[发布来源](https://x.ai/news/grok-4-5) · Real-world engineering excellence / 自身柱与文字表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-methodology) · PDF p2 / benchmark方法
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p4 / Coding and Multimodal
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → Terminal-Bench v2.1 行 → Solar Pro 4 列
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · Terminal-Bench 2.1
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · Terminal-Bench 2.1

## Terminal-Bench-Science 0.1

Terminal-Bench-Science 0.1包含70个科学研究终端任务，跨生命、物理、地球、数学、工程科学，由领域专家编写与审阅，公开Harbor运行方式。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-and-mythos-5-1) · A new performance frontier / Terminal-Bench-Science0.1
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · 顶部主图 / Terminal-Bench Science0.1

## SWE-bench Pro

Scale的SWE-Bench Pro包含1865题：Public731、Private276、Held-out858。公开与held-out OSS取强copyleft仓库，私有集取合作企业代码；降低污染风险而非保证无污染。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · p168 §8.2
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · p153 §8.2
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / SWE-Bench Pro
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / SWE-Bench Pro
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Coding 表 / SWE-Bench Pro
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Appendix / Coding Agent / SWE-bench Pro
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / SWE-bench Pro；Notes
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p116 §8.2
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p187–189 §6.4
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/) · Evaluation / Results，July2026表，自身列
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / SWE Pro
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / SWE Pro
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / SWE-Bench Pro
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SWE-bench Pro
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SWE-bench Pro
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / SWE-bench Pro
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / SWE-bench Pro
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SWE-bench Pro
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / Summary / SWE-bench Pro
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / SWE-Bench Pro
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / SWE-bench Pro
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SWE-Pro
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SWE-Pro
- Grok 4.5：[发布来源](https://x.ai/news/grok-4-5) · Real-world engineering excellence / 自身柱与文字表
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p3 / General Agentic and Agentic Coding
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · 发布正文 / 核心能力与评测说明
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → SWE-Bench Pro
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · SWE-Pro Bench
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · SWE-Pro Bench

## FrontierSWE v2

FrontierSWE v2于2026年9月介绍，34个长时程工程/科研任务，每题5次试验、每次20小时；新加入21题并使用proximus harness，分数与v1 dominance不能直接对应。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · p170 §8.5 FrontierSWE v2

## ProgramBench

ProgramBench含200个二进制程序重建任务：给可执行文件与文档，不得联网或反编译；超过248000行为测试，以Resolved、Almost（≥95%测试）和平均测试通过率分开报告。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · pp175–176 §8.11.1
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Agentic / ProgramBench Almost@1
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2 / ProgramBench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / ProgramBench Almost Solved
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / ProgramBench
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / ProgramBench；Notes
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · pp159–160 §8.9.1
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p121–122 §8.8
- Kimi K2.7 Code：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.7-Code) · Evaluation / Program Bench
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / ProgramBench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / ProgramBench (Almost Solved)
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / ProgramBench Almost Solved
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · ProgramBench
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · ProgramBench

## SWE-Marathon v1.1

SWE-Marathon由Abundant AI维护，评估多小时的软件工程任务并含GPU任务。v1.1于7月发布；约800GB指公开S3轨迹总集，不是单次trial日志。

- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / SWE-Marathon(v1.1); footnotes
- Grok 4.6：[发布来源](https://media.x.ai/v1/website/card-4p6-4cd2dc57.pdf) · PDF p13 §2.5
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / SWE-Marathon (v1.1)

## SWE-Atlas（QnA / TW/ RF）

本行按SWE Atlas家族汇总：Scale的Codebase QnA124题、Test Writing90题、Refactoring70题，各有独立任务和评分。确认采用仅表示至少一个子集，不能推定三个都报；QnA是AA Coding Index成分。

- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p3 SWE-Atlas Codebase QnA
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / SWE Atlas 三行；Notes
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / SWE-Atlas QnA
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## MLS-Bench-Lite

MLS-Bench-Lite为140题全集中的官方30题子集，覆盖12个机器学习研究领域，推荐每题5小时探索预算；验证时间另计。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2 / MLS-Bench-Lite
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Appendix / Coding Agent / MLS-Bench-Lite
- Kimi K2.7 Code：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.7-Code) · Evaluation / MLS Bench Lite
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / MLS-Bench-Lite

## PostTrainBench v1.1

PostTrainBench在4个指定base模型×7个下游评测上测自主后训练；官方每run一张H100、10小时。v1.1增加污染、外部API与历史trace查阅审计及模型身份检查，违规run回退base分。

- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / PostTrainBench V1.1

## CyberGym

CyberGym包含1507个漏洞、188个项目，主要要求据漏洞描述和代码生成能复现漏洞的PoC；它衡量漏洞分析/复现，不等于完整安全能力。

- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Agentic / CyberGym
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / CyberGym; footnote
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview#benchmark-appendix) · Agentic Coding / CyberGym
- Grok 4.6：[发布来源](https://media.x.ai/v1/website/card-4p6-4cd2dc57.pdf) · PDF p29 §7.1
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p48–49 §3.3.2
- Gemini 3.5 Flash Cyber：[发布来源](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/) · Cyber型号专节 / CyberGym图
- Gemini 3.8 Flash Cyber：[发布来源](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) · Cyber型号专节 / CyberGym图
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / Cybergym
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Evaluation / Cybergym
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Evaluation / Cybergym
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / CyberGym
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / CyberGym
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p24 / §2.2.1.2 CyberGym
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p6 / Safety / CyberGym
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · CyberGym
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p19 · Table 5 · CyberGym

## CursorBench 3.2.0

CursorBench基于Cursor内部实际会话与受控代码源，以Cursor Blame追溯需求和参考变更，评估正确性、质量、效率。3.2于7月8日更新，9月10日当前已升级4.0；完整任务未公开。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-and-mythos-5-1) · CursorBench3.2.0 图/表
- Claude Opus 5：[发布来源](https://www.anthropic.com/news/claude-opus-5) · Performance and cost-effectiveness / CursorBench3.2
- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals / CursorBenchv3.2

## Artificial Analysis Coding Agent Index v1.4

AA Coding Agent Index是独立运行的组合指数。原v1.4为历史版本；当前v1.5等权合成DeepSWE v1.1(113)、Terminal-Bench4.0(66)、SWE-Atlas-QnA(124)，每题3次取平均pass@1。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Coding 表 / AA Coding Agent Index v1.4

## APEX-SWE

Mercor与Cognition的APEX-SWE主榜保留集为Integration100题与Observability100题，另公开50题dev set与运行harness；评测跨服务集成与利用telemetry诊断生产问题，主榜200题不能视作完整公开可自跑。

- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Evals / APEX-SWE

## OSWorld 2.0

OSWorld 2.0 是长时程桌面与网站操作评测：108 个任务、7 个专业领域，人类完成时间中位数约 1.6 小时；同时提供严格成功率和 partial score。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / Visual Agent & Coding
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Computer use 表 / OSWorld 2.0
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · System Card p177–178 §8.12.3 / OSWorld 2.0
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/evals-methodology/gemini-3-8-flash/) · PDF p3 方法、p4结果表
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table 2 / Vision
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页尾完整性能表 / Vision / OSWorld 2.0
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use 表 / OSWorld 2.0
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use 表 / OSWorld 2.0
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use 表 / OSWorld 2.0
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / OSWorld2.0
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / VISION / OSWorld 2.0
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## BabyVision

BabyVision 用 388 个视觉推理问题诊断细粒度辨别、跟踪、空间与模式等基础视觉能力，覆盖22个子任务。它尽量降低语言知识依赖，但并非没有文字指令。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / BabyVision
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · PDF p33 Table3
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 完整性能表 / Vision
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / BabyVision
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / BabyVision w/tools
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / BabyVision
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / BabyVision
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / VISION / BabyVision
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / BabyVision
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / BabyVision w/CI
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → BabyVision
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · BabyVision
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · BabyVision

## ZeroBench

ZeroBench 包含100个高难度视觉推理主问题，并有拆分子问题。需分别记录 main/sub、pass@1、pass@5与要求连续成功的pass^5；发布初期的“零分”指特定严格指标。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / ZeroBench
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · PDF p33 Table3 / ZeroBench-main
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / ZeroBench (w.Tool)
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / ZeroBench (Pass@5)
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Evaluation / ZeroBench (Pass@5)
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / ZeroBench-main w/tools
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / ZEROBench_sub
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / ZEROBench主题与子题
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / ZEROBench主题与子题
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · ZeroBench main/sub
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · ZeroBench main/sub

## Perception Bench

PerceptionBench 从42个既有基准的失败案例归纳出10种原子视觉技能，含3000个问题，用于尽量隔离感知本身的缺陷。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / Visual Perception & Grounding
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / Vision
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## CharXiv

CharXiv 面向真实科学图表理解，包含描述与推理两类问题；本表各发布主要使用 Reasoning / RQ 子集，应在名称中明确。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / CharXiv (RQ)
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/evals-methodology/gemini-3-8-flash/) · PDF p2方法、p4结果 / CharXiv Reasoning
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / CharXiv(RQ)
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页尾性能表 / CharXiv (Reasoning)
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / CharXiv-RQ (w.Tool)
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p129–130 §8.10.5
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p196–197 §6.11.3
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/) · Evaluation / Results，July2026表，自身列
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / CharXiv RQ
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / CharXiv RQ
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / CharXiv RQ
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / CharXiv RQ
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / CharXiv RQ
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / CharXiv RQ
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / CharXiv RQ
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / CharXiv RQ
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / VISION / CharXiv Reasoning w/ Tools
- GLM-5V-Turbo：[发布来源](https://arxiv.org/html/2604.26752v1#S2.SS3) · §2.3 Broad training / multimodal RL evaluation paragraph / CharXiv
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / CharXiv RQ
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p4 / Coding and Multimodal
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → CharXiv-DQ/RQ
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · CharXiv-DQ/RQ
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · CharXiv-DQ/RQ

## OmniDocBench

OmniDocBench 评测真实文档的文本、公式、表格与阅读顺序等解析能力。文档类型数和标注随版本更新；原文9类是历史版本描述，当前仓库介绍为10类。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / OmniDocBench
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / OmniDocBench 1.5
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / OmniDocBench1.5
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / OmniDocBench1.5
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / OmniDocBench1.5
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / OmniDocBench1.5
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p5 / Multimodal

## MMMU-Pro

MMMU-Pro 在 MMMU 基础上过滤纯文本可解题、增加候选项，并设置图内题干形式，用于多学科图文推理。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / MMMU-Pro
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / MMMU-Pro
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / MMMU-Pro
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表 / MMMU Pro
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表 / MMMU Pro
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Multimodal 表 / MMMU Pro
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / MMMU-Pro
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / MMMU-Pro
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / MMMU-Pro
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / MMMU-Pro
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MMMU-Pro
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MMMU-Pro
- GLM-5V-Turbo：[发布来源](https://arxiv.org/html/2604.26752v1#S2.SS3) · §2.3 Broad training / multimodal RL evaluation paragraph / MMMU_Pro
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MMMU-Pro
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / MMMU-Pro
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p5 / Multimodal
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → MMMU_Pro
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · MMMU-Pro
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · MMMU-Pro

## HLE

原版 Humanity’s Last Exam（HLE）含2500个专家知识与推理问题，覆盖100多个领域，包含文本和图像。HLE-Full、text-only、HLE-Verified以及工具设置需要分开。

- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · PDF p32方法、p33 Table3
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / HLE-Full
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 通用能力表 / HLE及HLE w/tools
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 完整性能表 / HLE (w.tools)
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · PDF p176–178 §8.12.1 / HLE
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- GPT-5.5 Pro：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p115、122 §8.9.1
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p188、192 §6.10.1
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / HLE（工具/无工具）
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / HLE（工具/无工具）
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Evaluation / HLE（工具/无工具）
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / HLE（工具/无工具）
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / HLE-Full（工具/无工具）
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / HLE
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / HLE
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / HLE
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / HLE
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / HLE（工具/无工具）
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / HLE / HLE (w/ Tools)
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / HLE / HLE (w/ Tools)
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / HLE w/ Tools
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / AGENTIC / HLE w/ Tools
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / HLE（工具/无工具）
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / HLE
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / STEM图 / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → HLE
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → HLE (w/o tools)
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → HLE (no-tool,text only)

## AA-Omniscience

AA-Omniscience 用6000个问题覆盖6大领域、42个主题，联合衡量知识正确性和不知道时的弃答行为。指标会惩罚错误回答，不能当作普通准确率。


## CritPt

CritPt 包含71个研究级物理复合挑战、约190个检查点，涉及11个方向，使用机器可检查答案评估专业物理推理。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / CritPt
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark Results / Reasoning / CritPt
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / CritPt
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / CritPT
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / CritPT

## GPQA Diamond

GPQA Diamond 是生物、物理和化学专家设计的高难度科学问答子集，强调专业知识与科学推理。

- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf) · PDF p33 Table3 / GPQA-Diamond
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Academic 表 / GPQA Diamond
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / GPQA Diamond
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 通用能力表 / GPQA Diamond
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Academic 表 / GPQA Diamond
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Academic 表 / GPQA Diamond
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Academic 表 / GPQA Diamond
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark Results / GPQA Diamond
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p190 §6.6
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / GPQA Diamond
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / GPQA Diamond
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Evaluation / GPQA Diamond
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / GPQA-Diamond
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / GPQA Diamond
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / GPQA Diamond
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / GPQA Diamond
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / GPQA-Diamond
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / GPQA-Diamond
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / GPQA Diamond
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / GPQA Diamond
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / STEM图 / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → GPQA-Diamond
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → GPQA-Diamond
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → GPQA Diamond 行 → Solar Pro 4 列
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → GPQA Diamond

## HMMT2602

HMMT 2026 February 的 MathArena 可自动评测集合包含33题，覆盖竞赛数学，以最终答案判分。

- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation Results / Comparison across Modes / HMMT 2026 Feb
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark Results / HMMT Feb 2026
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / HMMT 2026 Feb
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / HMMT 2026 Feb
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / HMMT Feb 26
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / HMMT Feb 26
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / HMMT Feb26
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / HMMT Feb. 2026
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / HMMT Feb. 2026
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / HMMT 2026 Feb
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / HMMT 2026 Feb
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → HMMT2602

## AIME26

AIME 2026 由 AIME I 和 II 共30道竞赛数学题组成，通常按整数最终答案准确率评价。

- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark Results / AIME 2026
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / AIME 2026
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / AIME26
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / AIME26
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / AIME26
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / AIME 2026
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / AIME 2026
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → AIME26
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → AIME2026
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → AIME 2026 行 → Solar Pro 4 列

## ARC-AGI-2

ARC-AGI-2 通过少量彩色网格输入输出样例，要求模型推断并应用陌生转换规则，是静态抽象泛化评测。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Abstract reasoning 表 / ARC-AGI-2
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · System Card p185–186 §8.14.1
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · System Card p196–197 §8.16
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表

## ARC-AGI-3

ARC-AGI-3 是交互式陌生环境评测，要求模型探索动作、发现规则与目标、规划并根据反馈适应；得分结合相对人类行动效率。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Abstract reasoning 表 / ARC-AGI-3
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · System Card p186 / ARC-AGI-3及发布正文
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Abstract reasoning 表 / ARC-AGI-3
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Abstract reasoning 表 / ARC-AGI-3
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Abstract reasoning 表 / ARC-AGI-3

## BrowseComp

1266个难检索、答案简短且可核验的网页调查问题，衡量多跳搜索的持续性与准确性；不等同开放式研究报告质量。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Professional work表：BrowseComp
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use表：BrowseComp
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use表：BrowseComp
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Computer use表：BrowseComp
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p152 summary；p162 BrowseComp
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：BrowseComp
- MiniMax M3：[发布来源](https://huggingface.co/MiniMaxAI/MiniMax-M3/resolve/main/figures/benchmark.jpeg) · Cowork：BrowseComp；方法说明
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- GPT-5.5 Pro：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p115、123–124
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p192–193 §6.10.2
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / BrowseComp
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / BrowseComp
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / BrowseComp
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / BrowseComp / BrowseComp (w/ Context Manage)
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / Agent overview / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → BrowseComp 行 → Solar Pro 4 列
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → BrowseComp

## DeepSearchQA

Google提出900题、17领域的多步网页检索评测，要求穷尽答案集合并去重，使用precision/recall/F1检查覆盖率和正确性。

- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p164–165 §8.10.3 DeepSearchQA
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：DeepSearchQA (F1)
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · p2 DeepSearchQA
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / DeepSearchQA
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p1 / General Agentic
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列

## Toolathlon-Verified

Toolathlon于2026年6月发布的人工核验最终版，检查真实软件环境中的长期工具执行与结果状态；需固定Verified版本，不能把未注明版本的Toolathlon分数直接等同。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：Toolathlon-Verified
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p182–183 §8.13.6 Toolathlon Verified
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p194–195 §8.15.5 Toolathlon-Verified
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark Results：Toolathlon-Verified
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · General Agent表：Toolathlon Verified
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Language / Agent：Toolathlon Verified (Pass@1)
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Language / Agent：Toolathlon Verified (Pass@1)
- DeepSeek-V4-Pro-0813：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) · Introduction评测表：Toolathlon-Verified
- DeepSeek-V4-Flash-Vision-Exp：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp) · Introduction评测表：Toolathlon-Verified
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：Toolathlon-Verified
- DeepSeek-V4-Flash-0731：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) · Evaluation / Toolathlon-Verified
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / Toolathlon Verified
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / AGENTIC / Toolathlon Verified
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / Toolathlon Verified
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列

## MCP-Atlas

Scale的MCP工具能力评测，在可复现Docker环境使用真实MCP服务器完成多步任务，采用rubric与LLM裁判；需注明public/full分区与工具配置。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：MCP-Atlas
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p181 §8.13.2 MCP Atlas
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p293 §8.17.5 MCP Atlas
- MiniMax M3：[发布来源](https://huggingface.co/MiniMaxAI/MiniMax-M3/resolve/main/figures/benchmark.jpeg) · Cowork：MCP Atlas；底部方法
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：MCP Atlas (Public)
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / MCPAtlas Public
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / MCPAtlas Public
- Kimi K2.7 Code：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.7-Code) · Evaluation / MCP Atlas
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / MCP-Atlas
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / MCP-Atlas
- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark 表 / GLM-5.1 列 / MCP-Atlas (Public Set)
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark 表 / GLM-5.2 列 / MCP-Atlas (Public Set)
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / MCP-Atlas
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MCP-Atlas
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-methodology) · PDF p2 / benchmark方法
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p1 / General Agentic
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → MCP-Atlas
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → MCP-Atlas 行 → Solar Pro 4 列
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p10 · Table 2 · MCP-Atlas
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p10 · Table 2 · MCP-Atlas

## OfficeQA Pro

Databricks原版133题专业文档接地推理评测，基于历史美国财政部公报；完整246题另作OfficeQA Full，PDF直接读取与预解析文本方式分开比较。

- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2：OfficeQA Pro
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p180 §8.13.1 OfficeQA
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p191–192 §8.15.1 OfficeQA
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p252 Table8.1.A：OfficeQA Pro；p289方法
- MiniMax M3：[发布来源](https://huggingface.co/MiniMaxAI/MiniMax-M3/resolve/main/figures/benchmark.jpeg) · Cowork：OfficeQA Pro；底部方法
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · p9 Table1：OfficeQA-Pro及表注
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · p9 Table1：OfficeQA-Pro及表注
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview/resolve/main/assets/benchmark-appendix.jpg) · Benchmark Appendix：OfficeQA Pro
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p131 §8.11.1
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / VISION / OfficeQA Pro
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · OfficeQA-Pro · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · OfficeQA-Pro · Seed2.1 Pro 列

## Terminal-Bench 3.0

74题、7领域的终端与跨领域长任务版本，采用隔离验证器。现已演进到4.0；前身FrontierBench v0.1需另标版本，不能将其分数直接混合。

- Grok 4.6：[发布来源](https://x.ai/news/grok-4-6) · Benchmarks / Terminal-Bench 3.0
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / Terminal Bench 3.0
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Benchmark Results / Agentic
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / Terminal Bench 3.0
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / TerminalBench 3.0

## SWE-bench Multilingual

300题，42仓库，9种编程语言；根据真实issue/PR构造，以功能修复和回归测试评分。公开PR可能污染，分数也已趋高。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · PDF p168 §8.2
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · PDF p153 §8.2
- Tencent Hy4 preview：[发布来源](https://huggingface.co/tencent/Hy4-preview) · Benchmark Appendix / SWE-bench Multilingual
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p116 §8.2
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p187–189 §6.4
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / SWE Multilingual
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / SWE Multilingual
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / SWE-Bench Multilingual
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SWE-bench Multilingual
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SWE-bench Multilingual
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / SWE-bench Multilingual
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SWE-bench Multilingual
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SWE-Multilingual
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SWE-Multilingual
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · 发布正文 / 核心能力与评测说明
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → SWE Multilingual

## SWE-bench Multimodal

在软件工程issue中加入截图、设计图等视觉上下文。与一般图像问答和SWE-bench Multilingual是不同任务；需记录具体harness与评测切分。

- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · PDF p168 §8.2
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · PDF p153 §8.2 / p197 Appendix9.3
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p116 §8.2
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p187–189 §6.4
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / SWE-MM

## ExploitGym

正式v1为869个漏洞场景，覆盖用户态、V8及Linux内核；从已知漏洞及触发输入推进到实际利用。原论文898题与当前v1不同，必须锁定版本、2h/6h预算和防作弊修复。

- GPT-5.6 Sol：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.2 / Figure34
- GPT-5.6 Terra：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.2 / Figure34
- GPT-5.6 Luna：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.2 / Figure34
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Cybersecurity 表 / ExploitGym
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · PDF pp42–44 §3.3.5
- Claude Mythos 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · PDF pp50–52 §3.3.4
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / ExploitGym
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Benchmark Results / ExploitGym
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / ExploitGym (2h / 6h)
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p25（印刷页24）/ ExploitGym

## ExploitBench

41个V8环境的漏洞利用能力阶梯，16个经验证的能力标记。平均flags、Cap%与完整利用数不同，跨厂商比较要固定seed与union聚合方式。

- GPT-5.6 Sol：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.1 / Figure33
- GPT-5.6 Terra：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.1 / Figure33
- GPT-5.6 Luna：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.1 / Figure33
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Cybersecurity 表 / ExploitBench
- Claude Opus 5：[发布来源](https://www.anthropic.com/claude-opus-5-system-card) · PDF pp37–38 §3.3.1
- Claude Mythos 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-system-card) · PDF pp46–48 §3.3.1
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark / ExploitBench
- GLM-5.3：[发布来源](https://huggingface.co/zai-org/GLM-5.3) · Benchmark 表 / GLM-5.3 列 / ExploitBench

## SEC-bench Pro

当前官方仓库344例，含V8、SpiderMonkey和Linux；原论文/2026年5月版183例仅两个JS引擎。OpenAI明确用183题旧版，不能将其结果标成现行344题版。

- GPT-5.6 Sol：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.3 / Figure35
- GPT-5.6 Terra：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.3 / Figure35
- GPT-5.6 Luna：[发布来源](https://deploymentsafety.openai.com/gpt-5-6) · §9.1.2.4.3 / Figure35
- DeepSeek-V4.1-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) · Benchmark Results / SEC-Bench Pro
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Cybersecurity 表 / SEC-Bench Pro

## HLE-Verified

HLE的1811题verified版本，含经复核与修订的题目；独立于原2500题集。

- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/evals-methodology/gemini-3-8-flash/) · PDF p3 / Scientific Reasoning、p4结果

## MathVision

以包含视觉信息的数学竞赛问题评估多模态数学推理。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / MathVision
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / Math-Vision
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / MathVision
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / MathVision
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / MathVision
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / MathVision
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / MathVision
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MathVision
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MathVision
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MathVision
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → MathVision
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · MathVision
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · MathVision

## WorldVQA

评估从图像识别实体所需的视觉世界知识，区别于纯感知和复杂推理。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · 多模态表 / WorldVQA
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / WorldVQA ForceAnswer
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / WorldVQA
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / WorldVQA
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → WorldVQA
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · WorldVQA
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p51 · Appendix C Table 9 · WorldVQA

## Video-MME

覆盖多种时长与主题的视频理解评测，需注明字幕、音频和帧采样配置。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Video Intelligence & Agents / VideoMME(w.Sub)
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / Video-MME(w.sub)
- Doubao Seed2.1 Pro：[发布来源](https://seed.bytedance.com/en/seed2_1) · Evaluation Results / Video-MME
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / VideoMME（有/无字幕）
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / VideoMME (w sub.)
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / VideoMME
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / VideoMME
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / VideoMME
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / VideoMME w/sub
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → VideoMME
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p52 · Appendix C Table 10 · VideoMME
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p52 · Appendix C Table 10 · VideoMME

## MMVU

以多学科专家问题评估视频内容理解与推理。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Video Intelligence & Agents / MMVU
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · PDF p27 Table2 / MMVU
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页尾性能表 / MMVU
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MMVU
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / MMVU
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / GLM-5.3-Flash 列 / VISION / MMVU
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → MMVU

## LVBench

评估长视频的信息理解与提取，最长可达两小时。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Video Intelligence & Agents / LVBench
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/evals-methodology/gemini-3-8-flash/) · PDF p2 / Multimodal、p4结果
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / LVBench
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / LVBench
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / LVBench
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 模型表现 / 视觉语言 / LVBench
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / LVBench
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → LVBench
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p52 · Appendix C Table 10 · LVBench
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p52 · Appendix C Table 10 · LVBench

## ScreenSpot-Pro

评估高分辨率专业桌面界面中的目标定位能力。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Visual Agent & Coding / ScreenSpot Pro
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Computer use 表 / ScreenSpot-Pro
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / ScreenSpot Pro
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / ScreenSpot Pro
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p4 / Coding and Multimodal

## OpenAI MRCR v2

长对话中的多轮、多目标检索任务，需固定needle数量和上下文长度区间。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · General Capabilities / MRCR v2 256K(8-needle)
- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Long context 表 / MRCR v2
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Long context 表 / OpenAI MRCR v2
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Long context 表 / OpenAI MRCR v2
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Long context 表 / OpenAI MRCR v2
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Spark 1.3：[发布来源](https://research.meta.ai/static/muse-spark-1-3-multimodal-evaluation-methodology) · PDF p1–3 / per-benchmark methodology

## FrontierMath v2

专家编写的高难数学任务，Tier1–3与Tier4应分列。

- GPT-6 Astra：[发布来源](https://openai.com/zh-Hans-CN/index/gpt-6-astra/) · Academic / FrontierMath Tier1–3(v2)与Tier4(v2)
- GPT-5.6 Sol：[发布来源](https://openai.com/index/gpt-5-6/) · Academic / FrontierMath v2
- GPT-5.6 Terra：[发布来源](https://openai.com/index/gpt-5-6/) · Academic / FrontierMath v2
- GPT-5.6 Luna：[发布来源](https://openai.com/index/gpt-5-6/) · Academic / FrontierMath v2

## Terminal-Bench 2.0

在终端及隔离环境完成真实多步骤任务的2.0版本，以任务执行检查成功率评分。

- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark / Terminal-Bench 2.0
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / Terminal Bench 2.0
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / Terminal Bench 2.0
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / Terminal-Bench2.0
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / Terminal-Bench2.0
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / Terminal-Bench2.0
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / Terminal-Bench 2.0
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / Terminal-Bench 2.0
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / Terminal Bench2.0-Terminus
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / Terminal Bench2.0-Terminus
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p189 §6.5
- Claude Opus 4.7：[发布来源](https://anthropic.com/claude-opus-4-7-system-card) · p193 §8.3
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / Agent overview / Hy3-preview柱
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1 Evaluation Settings；§8.2 Table4 / M2.7自身列
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → TerminalBench 2
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → Terminal Bench 2.0

## SWE-bench Verified

由人工核验可解性的500个真实GitHub issue组成的软件修复评测子集。

- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p116 §8.2
- Claude Mythos Preview：[发布来源](https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf) · p187–189 §6.4
- Claude Opus 4.7：[发布来源](https://anthropic.com/claude-opus-4-7-system-card) · p191–192
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p194–195
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p251、253
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p251、253
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p.153 §8.2
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / SWE Verified
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / SWE Verified
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / SWE-Bench Verified
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SWE-bench Verified
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SWE-bench Verified
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SWE-bench Verified
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SWE-Verified
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SWE-Verified
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p3 / General Agentic and Agentic Coding
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / Agent overview / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → SWE-Bench Verified
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → SWE-Bench Verified (OpenHands) 行 → Solar Pro 4 列

## OSWorld-Verified

在真实桌面操作系统中通过视觉、鼠标与键盘完成任务的经核验版本。

- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p115
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/) · Evaluation / Results，July2026表，自身列
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p194 summary
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p251 summary
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p251 summary
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / OSWorld-Verified
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / OSWorld-Verified
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / OSWorld-Verified
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p3 / General Agentic and Agentic Coding
- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → OSWorld-Verfied

## Toolathlon

Tool Decathlon原始108个跨应用工具操作任务，按执行后的状态与产物检查完成度。

- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark / Tool-Decathlon
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark / Tool-Decathlon
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / Toolathlon
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / Toolathlon
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / Toolathlon
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / Tool Decathlon
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / Toolathlon
- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p134–135 §8.11.5
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p226–227 §8.13.7
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p295 Table8.17.8.A
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p294–295 §8.17.8
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Toolathlon
- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · Benchmark overview / M2.7自身红色柱
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p10 · Table 2 · Toolathlon
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p10 · Table 2 · Toolathlon

## GDPval

OpenAI面向44种职业的真实知识工作任务，模型产出文档等交付物；原始评估包含与人类作品比较。

- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → GDPval
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · GDPval · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · GDPval · Seed2.1 Pro 列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- GPT-5.5 Pro：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列

## GDPval-AA (pre-v2)

Artificial Analysis基于GDPval职业任务的代理交付盲评排序；此行保留未明确v2的早期发布口径。

- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results，May2026表，自身列
- Claude Opus 4.7：[发布来源](https://anthropic.com/claude-opus-4-7-system-card) · p211 §8.10.5
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p195、226 §8.13.6
- Claude Fable 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p252、294 §8.17.7
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / GDPval-AA
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / GDPval-AA
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · 发布正文 / 核心能力与评测说明

## FinanceAgent v1.1

面向金融信息检索、分析与决策任务的FinanceAgent1.1版本。

- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Claude Opus 4.7：[发布来源](https://anthropic.com/claude-opus-4-7-system-card) · p210 §8.10.2；v1.1身份由Opus4.8 card p224回溯明确
- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · Finance Agent v1.1 · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · Finance Agent v1.1 · Seed2.1 Pro 列

## FrontierMath (original)

Epoch组织数学专家编写的高难度数学题评测；按Tier1–3与Tier4区分难度。

- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- GPT-5.5 Pro：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列

## FrontierCode v1

Cognition与开源维护者建立的150项任务，使用正确性、质量和可合入标准评估代码。

- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p115、117–118

## CursorBench (unspecified version)

Cursor从实际代理使用中整理的代码任务，在Cursor生产代理框架中评测。

- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p118–119 §8.5

## LiveCodeBench v6

连续收集带发布日期的编程竞赛题，v6为固定发布批次；以可执行测试评估代码。

- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / LiveCodeBench v6
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / LiveCodeBench v6
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / LiveCodeBench v6
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / LiveCodeBench v6
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / LiveCodeBench v6
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / LiveCodeBench v6
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / LiveCodeBench v6
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / LiveCodeBench v6
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → LiveCodeBench(v6)

## τ²-bench

在用户与代理可共同操作的环境内，通过工具与政策完成电信、航空、零售客服任务。

- GPT-5.4 mini：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.4 nano：[发布来源](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) · 正文下部 Coding / Tool-calling / Intelligence / MM / Long context 分组表，自身列
- GPT-5.5：[发布来源](https://openai.com/index/introducing-gpt-5-5/) · Evaluations：对应命名行及自身列
- Gemma 4 31B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 12B Unified：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E4B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- Gemma 4 E2B：[发布来源](https://ai.google.dev/gemma/docs/core/model_card_4) · Benchmark Results，IT模型自身列
- DiffusionGemma 26B A4B：[发布来源](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · Benchmark Results，DiffusionGemma自身列
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本表 / TAU2Bench
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本表 / TAU2Bench
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → Tau2-all

## GDM-MRCR v2

Google DeepMind的长上下文多轮共指消解任务；模型在多轮相似写作请求中找出指定次序的回复并复制，v2报告8needle等设置。

- Gemini 3.5 Flash-Lite：[发布来源](https://deepmind.google/models/evals-methodology/gemini-3-5-flash-lite/) · p3 Long Context；modelcard Results
- Gemini 3.5 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-5-flash/) · Evaluation / Results MRCRv2行；配套方法PDF Long Context段链接Google自有仓库
- Gemini 3.6 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-6-flash/) · Evaluation / Results MRCRv2行；配套方法PDF Long Context段链接Google自有仓库
- Gemini 3.7 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-7-flash/) · Evaluation / Results MRCRv2行；配套方法PDF Long Context段链接Google自有仓库
- Gemini 3.8 Flash：[发布来源](https://deepmind.google/models/model-cards/gemini-3-8-flash/) · Evaluation / Results MRCRv2行；配套方法PDF Long Context段链接Google自有仓库
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / MRCR-v2 128K / footnote

## HealthBench

开放的医疗对话能力与安全评测，5,000段多轮对话，按医生编写的情境rubric评分；Hard和Professional分别保留独立行。

- GPT-5.5：[发布来源](https://deploymentsafety.openai.com/gpt-5-5) · §5.1 Table 7，自身列
- GPT-5.5 Instant：[发布来源](https://deploymentsafety.openai.com/gpt-5-5-instant) · §5.1 Table 5，自身列
- GPT-5.6 Sol (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- GPT-5.6 Luna (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p.138 Figure 8.12.1.A / p.115 summary
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p.188–189 §8.15
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p.198–199 §8.17
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p.252 summary；p.297–298 §8.18

## HealthBench Pro

又称HealthBench Professional；525个医生编写的临床咨询、文书和医学研究对话，按医生审定rubric评分。

- GPT-5.5：[发布来源](https://deploymentsafety.openai.com/gpt-5-5) · §5.1 Table 7，自身列
- GPT-5.5 Instant：[发布来源](https://deploymentsafety.openai.com/gpt-5-5-instant) · §5.1 Table 5，自身列
- GPT-5.6 Sol (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- GPT-5.6 Luna (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- Claude Sonnet 5：[发布来源](https://anthropic.com/claude-sonnet-5-system-card) · p.138 Figure 8.12.1.A / p.115 summary
- Claude Opus 5：[发布来源](https://anthropic.com/claude-opus-5-system-card) · p.188–189 §8.15
- Claude Fable 5.1：[发布来源](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card) · p.198–199 §8.17
- Claude Mythos 5：[发布来源](https://anthropic.com/claude-fable-5-mythos-5-system-card) · p.252 summary；p.297–298 §8.18
- Claude Opus 4.8：[发布来源](https://anthropic.com/claude-opus-4-8-system-card) · p.228 §8.14.1
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列

## HealthBench Hard

HealthBench中针对现有前沿模型仍较困难的开放医疗对话子集；保持Hard标签，不与完整HealthBench汇总分合并。

- GPT-5.5：[发布来源](https://deploymentsafety.openai.com/gpt-5-5) · §5.1 Table 7，自身列
- GPT-5.5 Instant：[发布来源](https://deploymentsafety.openai.com/gpt-5-5-instant) · §5.1 Table 5，自身列
- GPT-5.6 Sol (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- GPT-5.6 Luna (August)：[发布来源](https://deploymentsafety.openai.com/gpt-5-6-august-update) · §5.1 Table 6，自身列
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表

## IMOAnswerBench

以简短答案判定的竞赛数学评测；应固定数据版本与答案判分。

- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark / IMOAnswerBench
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark / IMOAnswerBench
- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / IMOAnswerBench
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / IMOAnswerBench
- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / IMO-AnswerBench
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / IMOAnswerBench
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / IMOAnswerBench
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / IMOAnswerBench
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / IMOAnswerBench
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / IMOAnswerBench
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / IMOAnswerBench
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / IMOAnswerBench
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / STEM图 / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列

## HMMT Nov. 2025

2025 年 11 月 HMMT 数学竞赛题评测，与 2026 年 2 月场次分开。

- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark / HMMT Nov. 2025
- GLM-5.2：[发布来源](https://huggingface.co/zai-org/GLM-5.2) · Benchmark / HMMT Nov. 2025

## ZClawBench

在 OpenClaw 环境评测多步工具与任务执行的智能体基准。

- GLM-5-Turbo：[发布来源](https://docs.z.ai/guides/llm/glm-5-turbo) · Introducing GLM-5-Turbo / Step 2 ZClawBench
- GLM-5V-Turbo：[发布来源](https://arxiv.org/html/2604.26752v1#S5) · §5 Evaluation / Figure 5

## Vision2Web

评测根据视觉参考开发网站并验证交互行为的分层智能体基准。

- GLM-5V-Turbo：[发布来源](https://arxiv.org/html/2604.26752v1#S5) · §5 Evaluation / Multimodal Coding / Figure 4
- GLM-5.3-Flash：[发布来源](https://z.ai/blog/glm-5.3-flash) · 页末完整性能表 / Vision2Web

## Vending Bench 2

模型经营一家模拟自动售货业务一年，按期末账户余额评分；考察持续工具调用、采购、定价与长期一致性。

- GLM-5.1：[发布来源](https://huggingface.co/zai-org/GLM-5.1) · Benchmark / Vending Bench 2

## KernelBench Level 3

将完整机器学习架构中的 PyTorch 计算实现为 GPU 内核，评测正确性与相对参考实现的加速比；Level 3 与单算子级别应区分。

- GLM-5.1：[发布来源](https://docs.z.ai/guides/llm/glm-5.1) · Long-horizon task optimization / KernelBench Level 3
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / Kernel Bench L3
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / Kernel Bench L3

## MCPMark

在真实MCP服务环境执行多步读写操作，使用程序验证最终状态；原始版本与6月12日推出的Verified修订版分开记录。

- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / MCPMark
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / MCPMark
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / MCPMark
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / MCP-Mark
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MCP-Mark

## MCPMark Verified

MCPMark对环境版本与验证器稳定性进行修订后的任务集；2026年6月12日起成为默认版本。

- Kimi K2.7 Code：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.7-Code) · Evaluation / MCP Mark Verified
- Kimi K3：[发布来源](https://github.com/MoonshotAI/Kimi-K3/blob/main/k3_tech_report.pdf) · p27 Table2 / MCPMark-Verified

## SciCode

科学家整理的科研编程评测，80个主问题拆成338个子问题；考察将科学知识转成计算代码。

- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / SciCode
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / SciCode
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SciCode
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SciCode
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p4 / Coding and Multimodal
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）

## MMLU-Pro

比MMLU更重推理的多学科选择题集合，常见题目扩为十选项。

- DeepSeek-V4-Flash：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) · Evaluation / MMLU-Pro
- DeepSeek-V4-Pro：[发布来源](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · Evaluation / MMLU-Pro
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / MMLU-Pro
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / MMLU-Pro
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / MMLU-Pro
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / MMLU-Pro
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / MMLU-Pro
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / MMLU-Pro
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MMLU-Pro
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → MMLU PRO
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → MMLU-Pro
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → MMLU-Pro 行 → Solar Pro 4 列

## SuperGPQA

覆盖285个研究生细分学科的知识与推理题库，包含大量长尾领域。

- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SuperGPQA
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SuperGPQA
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SuperGPQA
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / SuperGPQA
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / SuperGPQA
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / SuperGPQA
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SuperGPQA
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SuperGPQA
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → SuperGPQA

## LongBench v2

503道长上下文多选任务，覆盖文档、对话、代码仓库与结构化数据理解。

- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / LongBench v2
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / LongBench v2
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / LongBench v2
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / LongBench v2

## SpreadsheetBench v1

从真实Excel论坛问题构建的表格操作基准，原始完整集912题、2729个测试表格；与工作流任务版v2分开统计。

- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / SpreadSheetBench-v1
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SpreadSheetBench-v1
- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法

## CoWorkBench

Qwen内部长程办公与生产力任务集，覆盖计算机、财务、法律、医疗等工作场景。

- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / CoWorkBench
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / CoWorkBench
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / CoWorkBench
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / CoWorkBench
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Performance / CoWorkBench
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Performance / CoWorkBench

## ClawEval-MM

Qwen发布表中单列的ClawEval多模态工具使用评测；Claw-Eval官方提供multimodal任务分区。具体版本/子集规模应随发布脚注记录。

- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / ClawEval-MM Pass@3
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / ClawEval-MM
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Performance / ClawEval-MM
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Performance / ClawEval-MM

## DeepSWE v1.0

评测真实软件工程任务的DeepSWE 1.0版本；须与任务更新后的1.1分开记录。

- Grok 4.5：[发布来源](https://x.ai/news/grok-4-5) · Real-world engineering excellence / 自身柱与文字表

## ERQA

通过图像问答测试面向实体交互的空间与物理推理。

- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / ERQA
- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / ERQA
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / ERQA
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / ERQA
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / ERQA
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / ERQA
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / ERQA
- Qwen3.8-Max-0902：[发布来源](https://x.com/Alibaba_Qwen/status/2094968708288680276) · 第二张附图 / ERQA
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## SimpleVQA

面向真实图像、可核验视觉事实的问答；观察能力与世界知识可能同时影响结果。

- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SimpleVQA
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SimpleVQA
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SimpleVQA
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / SimpleVQA
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / SimpleVQA
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / SimpleVQA
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表
- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## MedXpertQA

医学专家级问题，分别有文本与多模态子集，二者协议与分数须分别标注。

- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / MedXpertQA-MM
- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表

## LiveCodeBench Pro

按时间更新的编程任务Pro版本；本轮Meta报告采用2025Q2子集，不能与v6混同。

- Meta Muse Spark：[发布来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology) · PDF p5 / 自身结果表

## WebArena-Verified

在可交互网页应用中完成多步骤任务的Verified任务集，以环境最终状态判定成功。

- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p101（印刷页100）Figure44 / Muse Spark1.1列

## OmniSpatial

通过不同图像与场景问题衡量空间理解与推理，须核实具体空间子能力。

- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## ChartMuseum

真实图表中的复杂视觉理解与推理问答，与单纯图表数据提取有所不同。

- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## ChartQAPro

图表问答的更困难Pro任务，要求理解图表并结合多步骤推理。

- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## WildArtifactBench

让智能体生成实际文件产物，以人工与自动评委分别进行成对比较并拟合Elo；不只是图像问答。

- Meta Muse Spark 1.2：[发布来源](https://research.meta.ai/static/muse-spark-1-2-multimodal-evaluation-methodology) · PDF p2–4 / 自身多模态评测方法

## AA-LCR

Artificial Analysis长上下文推理任务，考察长文档中的信息整合与推断。

- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → AA-LCR
- Solar Pro 4：[发布来源](https://www.upstage.ai/blog/en/solar-pro-4) · Solar Open 2 and Solar Pro 4: Which One, When → AA-LCR 行 → Solar Pro 4 列
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / AA-LCR
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / AA-LCR
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / AA-LCR
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）

## IFBench

使用可验证规则衡量复杂指令遵循；检查多条约束是否被同时满足。

- Qwen3.8-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.8-27B) · Evaluation / IFBench
- Qwen3.8-Flash-Next：[发布来源](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) · Evaluation / IFBench
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / IFBench
- Qwen3.5-Omni-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / IFBench
- Qwen3.5-Omni-Flash：[发布来源](https://qwen.ai/blog?id=qwen3.5-omni) · 文本/视觉表 / IFBench
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / IFBench
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / IFBench
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / IFBench
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）
- Solar Pro 3 (260323)：[发布来源](https://www.upstage.ai/blog/en/solar-pro-3-0323) · Full Benchmark Details → 配图 solar pro3_overview → Solar Pro 3 列 → IFBench
- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → IFBench

## GAIA2

在有状态模拟应用与动态事件中完成多轮工具任务，测试执行、搜索、歧义处理、适应与时间能力。

- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p2 / General Agentic

## WildClawBench

真实长任务的开放智能体评测，涉及生产力、编程、搜索、创作等；全套60题与文本子集须区分。

- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p2 / General Agentic
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列

## SkillsBench

测量智能体利用模块化说明与工具技能完成专业任务的效果，用隐藏执行测试评分。

- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / SkillsBench Avg5
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / SkillsBench Avg5
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / SkillsBench
- Qwen3.6-Max-Preview：[发布来源](https://qwen.ai/blog?id=qwen3.6-max-preview) · Performance / SkillsBench
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / SkillsBench
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / Skillsbench
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / Skillsbench
- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p3 / General Agentic and Agentic Coding
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → SkillsBench
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p11 · §2.3.2 Results

## ClawEval

在工具环境中衡量多步骤任务完成与稳定性；pass率和多次全成功等指标须区分。

- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / Claw Eval
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / Claw-Eval
- Qwen3.6-27B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-27B) · Evaluation / Claw-Eval
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / ClawEval
- Qwen3.7-Max：[发布来源](https://qwen.ai/blog?id=qwen3.7) · Performance / ClawEval
- Qwen3.7-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.7-plus) · Performance / ClawEval（文本版）
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法

## FrontierScience

困难科学问题评测，Olympiad与Research两类问题分别衡量竞赛式与研究式能力。

- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / STEM图 / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列

## WideSearch

要求广泛检索和汇总多项结果的搜索任务；工具、搜索服务和答案完整性评分影响结果。

- Kimi K2.6：[发布来源](https://huggingface.co/moonshotai/Kimi-K2.6) · Evaluation / WideSearch
- Qwen3.6-35B-A3B：[发布来源](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · Evaluation / WideSearch
- Qwen3.6-Plus：[发布来源](https://qwen.ai/blog?id=qwen3.6) · 模型表现 / WideSearch
- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / WideSearch
- Meta Muse Spark 1.1：[发布来源](https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report) · PDF p104（印刷页103）/ §5.2.1 WideSearch
- Tencent Hy3 preview：[发布来源](https://github.com/Tencent-Hunyuan/Hy3-preview) · README / Benchmarks / Agent overview / Hy3-preview柱
- Tencent Hy3：[发布来源](https://github.com/Tencent-Hunyuan/Hy3) · README / benchmark appendix / Hy3自身列
- MiniMax M2.7：[发布来源](https://arxiv.org/html/2605.26494v1) · §8.1方法；§8.2 Table4 / Ours-M2.7自身列（2026-05-26系列技术报告）

## PaperBench

要求复现机器学习论文的实验与代码，以结构化研究产物规则评分，需固定运行预算。

- Qwen3.8-Max：[发布来源](https://qwen.ai/blog?id=qwen3.8) · Performance / PaperBench
- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → PaperBench

## LiveSQLBench

真实数据库上的SQL任务；M3明确采用LiveSQLBench-Base-Full v1，共600题、22个PostgreSQL数据库。

- MiniMax M3：[发布来源](https://www.minimax.io/blog/minimax-m3) · Benchmark完整表 / M3自身列与下方方法

## BEAM

面向多轮或长上下文记忆与整合的评测；此处采用128K上下文设置。

- Meta Muse Glimmer 30B：[发布来源](https://research.meta.ai/static/muse-glimmer-methodology) · PDF p7 / Reasoning and General Capabilities

## MLE-bench Lite

MLE-bench的较小竞赛任务子集，测试训练模型及提交预测的机器学习工程能力。

- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · Benchmark overview / M2.7自身红色柱

## Multi-SWE-bench

多语言真实仓库issue修复任务，与SWE-bench Multilingual是不同数据集。

- MiniMax M2.7：[发布来源](https://www.minimax.io/news/minimax-m27-en) · Benchmark overview / M2.7自身红色柱

## MultiChallenge

评估多轮对话中的指令保持、隐含记忆、自洽和可靠版本编辑。

- Solar Open 2：[发布来源](https://huggingface.co/upstage/Solar-Open2-250B) · Evaluation → English benchmark table → Solar Open 2 列 → Multi-Challenge
- Seed2.0 Lite (260428)：[发布来源](https://seed.bytedance.com/en/seed2) · 模型评测表 → Seed2.0 Lite（0428）首列 → MultiChallenge

## Workspace Bench

衡量Agent在含大量异构文件及依赖关系的工作区中检索、推理与执行任务；完整版388任务，另有100任务Lite子集。

- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · Workspace Bench · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · Workspace Bench · Seed2.1 Pro 列

## PresentBench

通过238个含背景材料的幻灯片生成任务，以逐实例细粒度二元检查项评价产物。

- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · PresentBench · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · PresentBench · Seed2.1 Pro 列

## OneMillion Bench

400个专家构造任务覆盖法律、金融、工业、医疗和自然科学，评估来源检索、证据冲突处理和专业约束下的多步Agent能力。

- Doubao Seed2.1 Turbo：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · OneMillion Bench · Seed2.1 Turbo 列
- Doubao Seed2.1 Pro：[发布来源](https://lf3-static.bytednsdoc.com/obj/eden-cn/lapzild-tss/ljhwZthlaukjlkulzlp/seed2.1/Seed2_1_Model_Card.pdf) · PDF p9 · Table 1 · OneMillion Bench · Seed2.1 Pro 列
