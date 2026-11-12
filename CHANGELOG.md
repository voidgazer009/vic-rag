# Changelog

## v0.1.1 — 2026-11-12
- 新增四层审核机制（REVIEW.md）：自动门禁 `scripts/audit.py`、事实核查、红队、专家评分。
- 新增 `review/baseline.json` 质量基线，评测不得倒退。
- 时效性资料补充 `last_reviewed` 和“以最新为准”提示。
- 新增 `review/BACKLOG.md` 每日迭代待办。

## v0.1.0 — 2026-11-12
- 通用 RAG 引擎（BM25 + 可选向量混合检索、RRF、同义词扩展、引用）。
- 四个知识库：trade、logistics、opc、social，各 6 篇资料、12 道评测题。
- MCP Server、HTTP API、CLI。
