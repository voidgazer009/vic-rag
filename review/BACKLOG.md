# 每日迭代待办（按顺序取，完成打勾，可随时补充）

每天只做一件事，但要做到优秀。知识库内容按 trade → logistics → opc → social 轮换。

## 内容（每次：新增 2 篇资料 + ≥ 4 道评测题，含 1 道“资料中没有”类题目）
- [ ] trade：外贸合同关键条款（质量、索赔、不可抗力、仲裁）
- [ ] logistics：危险品与带电货物运输（UN38.3、MSDS、DGR）
- [ ] opc：AI 一人公司的法律与财务基础（主体、发票、合同、跨境收款）
- [ ] social：YouTube 长视频 SEO（标题、描述、章节、缩略图）
- [ ] trade：样品流程与验厂/质检（AQL 抽样）
- [ ] logistics：海运保险与货损索赔
- [ ] opc：用 vic-rag + MCP 搭建客服 Agent 实战
- [ ] social：TikTok Shop / Instagram Shopping 带货基础
- [ ] trade：主要市场认证速查（CE、FCC、FDA、UKCA、RoHS）
- [ ] logistics：海外仓与 FBA 入仓规则
- [ ] opc：Newsletter 与私域订阅变现
- [ ] social：多语言内容与本地化

## 引擎
- [ ] 负向检测：最高分过低时返回“无可靠资料”标记（配合红队“资料中没有”题）
- [ ] 可选 Reranker（bge-reranker，OpenAI 兼容 /rerank 接口）
- [ ] 资料 front matter 的 `last_reviewed` 在检索结果中返回，回答可提示时效
- [ ] GitHub Actions CI（如权限允许）
- [ ] 接入 vic-agents：trade.lead_hunter 调用 trade 知识库
