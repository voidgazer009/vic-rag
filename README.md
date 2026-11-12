# Vic RAG · 通用行业知识库引擎

> 任何行业、任何 AI 都能用的 RAG（检索增强生成）系统。一个通用引擎 + 可插拔的行业知识包，通过 **MCP / HTTP API / CLI** 接入 Claude、ChatGPT、Cursor、Dify、n8n 或你自己的 Agent。
>
> A universal, model-agnostic RAG engine with pluggable industry knowledge packs, exposed over MCP, HTTP and CLI.

由 **Vic** 打造，服务外贸、国际物流、AI 一人公司、全球自媒体四条业务线，也可以 10 分钟扩展到任何行业。

## 内置四个知识库

| ID | 知识库 | 覆盖内容 | 评测 hit@5 / MRR |
|---|---|---|---|
| `trade` | 外贸 | Incoterms 2020、付款方式与 UCP600 信用证、报价核算与出口退税、HS 编码与单证、客户开发与开发信、术语速查 | 1.00 / 0.94 |
| `logistics` | 国际物流 | 整箱拼箱与集装箱规格、空运快递计费重、海运附加费、提单与电放、美国 ISF/欧盟 ICS2 清关、物流方式决策 | 1.00 / 1.00 |
| `opc` | AI 一人公司 | 商业模式、Agent/RAG/MCP/Skills 技术栈、价值定价与产品阶梯、SOP 自动化、LTV/CAC 等指标、冷启动获客 | 1.00 / 0.96 |
| `social` | 全球自媒体 | 平台定位、短视频钩子与脚本、LinkedIn B2B 社交销售、内容日历与一稿多发、数据指标、广告披露与版权 | 1.00 / 0.96 |

评测集在每个知识包的 `eval.jsonl`，运行 `vic-rag eval` 复现（纯 BM25 模式，无需任何 API Key）。

## 为什么是“通用”的
- **引擎与行业解耦**：解析、结构化切块、混合检索、RRF 融合、引用、评测全部通用；行业差异只写在 `pack.yaml`（同义词/行话、切块参数、回答提示词）和资料文件夹里。
- **模型无关**：默认纯 BM25（中英文混合分词，零依赖、离线可用）；可选接入任何 OpenAI 兼容的 Embedding 接口（OpenAI、硅基流动、Ollama、vLLM、Jina…）或本地 fastembed（bge-small-zh），自动变成稠密 + 关键词混合检索。
- **AI 无关**：MCP Server 给 Claude Desktop / Claude Code / Cursor 等；HTTP API 给 GPTs Actions、Dify、Coze、n8n、Make；CLI 给脚本和定时任务。
- **你的资料优先**：每个知识库都能导入你自己的 PDF / Word / Markdown / HTML / CSV，与内置资料一起检索，回答带出处。

## 快速开始

```bash
git clone https://github.com/voidgazer009/vic-rag.git
cd vic-rag
pip install -e ".[mcp]"          # 只要 CLI 可以 pip install -e .

vic-rag list                      # 查看知识库
vic-rag search trade "信用证没写交单期怎么办"
vic-rag context logistics "60x50x40cm 18kg 走快递计费重多少"   # 生成带引用的提示词
vic-rag eval                      # 跑评测
```

## 接入 Claude Desktop / Cursor（MCP）

```json
{
  "mcpServers": {
    "vic-rag": {
      "command": "vic-rag",
      "args": ["mcp"]
    }
  }
}
```

提供的工具：`list_knowledge_bases`、`search`、`get_context`、`add_document`、`kb_stats`。同时兼容 MCP Python SDK 1.x 与 2.x。

## HTTP API（GPTs / Dify / n8n）

```bash
VIC_RAG_API_TOKEN=换成你的密钥 vic-rag http --host 0.0.0.0 --port 8765
curl -X POST localhost:8765/search -H "Authorization: Bearer 换成你的密钥" \
     -d '{"kb":"opc","query":"LTV 怎么算","k":3}'
```

接口：`GET /kbs`、`POST /search {kb, query, k, tags}`、`POST /context {kb, question, k}`。

## 导入你自己的资料

```bash
vic-rag add trade ~/Documents/报价表/        # 文件夹或单个文件
pip install pypdf python-docx               # 需要 PDF / Word 时
```

资料保存在 `~/.vic-rag/<知识库>/docs/`（可用 `VIC_RAG_HOME` 修改），索引按文件指纹自动增量判断是否重建。Markdown 可写 front matter 的 `tags`，检索时用 `--tag` 过滤。

## 打开稠密向量检索（可选）

```bash
# 任意 OpenAI 兼容接口
export VIC_RAG_EMBEDDER=openai
export VIC_RAG_EMBED_BASE_URL=https://api.openai.com/v1
export VIC_RAG_EMBED_API_KEY=sk-...
export VIC_RAG_EMBED_MODEL=text-embedding-3-small
# 或本地模型
pip install fastembed && export VIC_RAG_EMBEDDER=fastembed   # 默认 BAAI/bge-small-zh-v1.5
vic-rag build
```

## 新建一个行业知识包（10 分钟）

```
packs/your-industry/
├── pack.yaml      # id、名称、描述、同义词、切块参数、回答提示词
├── docs/          # 资料：md / txt / html / csv / json / pdf / docx
└── eval.jsonl     # {"q": "问题", "expect": ["应命中的文件名或原文片段"]}
```

复制 `packs/trade/pack.yaml` 改一改即可。也可以设置 `VIC_RAG_PACKS` 指向你自己的知识包目录。

## 架构

```
资料 → 解析(loaders) → 按标题结构切块+重叠(chunker) → 中英混合分词 → BM25
                                                     └→ 可选 Embedding → 向量
提问 → 行业同义词扩展 → BM25 ∥ 向量 → RRF 融合 → 去重 → 带 [编号] 引用的上下文 → 任意大模型
```

## 路线图
- [x] v0.1 通用引擎、四个知识库、MCP/HTTP/CLI、评测
- [ ] Reranker 重排（bge-reranker）
- [ ] 每个知识库扩充到 30+ 篇资料与 50+ 评测题
- [ ] 接入 [vic-agents](https://github.com/voidgazer009/vic-agents)：每个 Agent 查询自己公司的知识库

## 说明
知识库内容为 Vic 原创整理，用于学习和业务参考。法规、税率、运价、平台规则会变化，重要决策请以官方最新公告、银行、货代和专业人士意见为准。

## License
MIT © Vic
