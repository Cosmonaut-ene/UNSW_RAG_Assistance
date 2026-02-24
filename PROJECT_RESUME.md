# 项目说明 & 面试技术手册

---

## 一、简历项目说明

> 直接复制下方内容填入简历"项目经历"模块，可根据篇幅选择中英文版本。

---

### 中文版

**UNSW CSE Open Day 智能问答系统**
*COMP9900 Capstone 团队项目 · 2025*
技术栈：Python · Flask · LangGraph · ChromaDB · Google Gemini · Vue 3 · Docker

- 主导构建基于 **Retrieval-Augmented Generation（RAG）** 的 UNSW CSE 校园开放日问答系统，为访客提供课程、项目及校园设施的精准信息查询服务
- 设计并实现 **LangGraph 图结构 RAG 流水线**，将 8 个处理节点（安全检测 → 查询改写 → HyDE → 混合检索 → 重排序 → CRAG 评级 → 生成 → 幻觉检测）编排为 DAG，消除了原有 if/elif 手动控制流，支持多路径回退策略
- 引入 **HyDE（Hypothetical Document Embeddings）** 技术：生成假设性文档桥接稀疏查询与长文档语义，使模糊查询的检索召回率显著提升
- 实现 **Cross-encoder 重排序**（ms-marco-MiniLM-L-6-v2）+ **CRAG 文档评级**，在 Top-30 混合检索结果中精选 Top-7，过滤低相关 chunk，显著降低生成幻觉率
- 构建 **混合检索系统**：向量检索（ChromaDB + sentence-transformers/all-MiniLM-L6-v2，本地运行无 API 限制）与 BM25 关键词检索融合，通过 Reciprocal Rank Fusion 合并评分
- 采用 **Contextual Retrieval** 技术（Anthropic 提出）：以 Gemini 为每个 PDF chunk 生成文档级摘要前缀，解决 chunk 脱离上下文导致检索失准问题
- 搭建 **RAGAS 评测框架**，编写 50+ 条 UNSW 真实 Q&A ground truth，覆盖 5 类场景（课程信息、学位项目、先修要求、入学条件、校园设施），用于量化评估 Answer Relevancy、Faithfulness 等指标
- 使用 **Docker Compose** 容器化部署全栈应用（Flask 后端 + Vue 3 前端），通过 volume bind-mount 实现后端热重载，HuggingFace 模型通过 named volume 持久化缓存
- 开发 Admin 管理后台：支持 PDF 文件上传/删除、UNSW 网页内容抓取（Selenium + BeautifulSoup）、向量库增量更新、聊天日志审计及数据导出

---

### English Version

**UNSW CSE Open Day AI Chatbot**
*COMP9900 Capstone Project · 2025*
Stack: Python · Flask · LangGraph · ChromaDB · Google Gemini · Vue 3 · Docker

- Built a production-ready **Retrieval-Augmented Generation (RAG)** chatbot serving UNSW CSE Open Day visitors with accurate information on courses, degree programs, and campus facilities
- Architected an **8-node LangGraph pipeline** (safety → rewrite → HyDE → hybrid retrieval → cross-encoder rerank → CRAG grading → generate → hallucination check), replacing procedural if/elif control flow with a DAG supporting multi-path fallback strategies
- Implemented **HyDE (Hypothetical Document Embeddings)**: generates plausible answers to bridge the semantic gap between short user queries and long documents, improving recall on vague queries
- Applied **cross-encoder reranking** (ms-marco-MiniLM-L-6-v2) and **Corrective RAG (CRAG)** document grading to select Top-7 from Top-30 hybrid search results, reducing hallucination rates
- Built a **hybrid search system** combining local sentence-transformers vector search (ChromaDB) with BM25 keyword search, fused via Reciprocal Rank Fusion
- Applied **Contextual Retrieval** (Anthropic technique): prepended Gemini-generated document summaries to every PDF chunk to preserve context during retrieval
- Established a **RAGAS evaluation pipeline** with 50+ manually curated ground-truth Q&A pairs across 5 categories for quantitative measurement of Answer Relevancy and Faithfulness
- Containerized the full-stack application with **Docker Compose**; backend code changes apply via bind-mount hot-reload, embedding model persisted via named volume
- Built an admin dashboard supporting PDF management, web scraping (Selenium + BeautifulSoup), incremental vector store updates, and chat log audit/export

---

---

## 二、面试技术问答手册

> 以下为本项目涉及的核心技术点，按"问题 → 回答要点"格式整理，用于应对技术面试。

---

### Part 1：RAG 基础

---

**Q: 什么是 RAG？为什么不直接用 LLM 回答问题？**

RAG（Retrieval-Augmented Generation）是一种将信息检索与语言模型生成结合的架构。

纯 LLM 的问题：
1. **知识截止**：无法获取训练数据之外的信息（如最新课程信息）
2. **幻觉（Hallucination）**：模型倾向于自信地编造不存在的细节
3. **无法引用来源**：无法追溯答案的依据
4. **成本高**：将所有文档塞入 context window 开销极大

RAG 的解法：先从知识库中检索与问题相关的文档片段（chunk），再将这些片段作为 context 喂给 LLM 生成答案。答案有依据，可验证，且知识库可独立更新。

---

**Q: 本项目的 RAG 流水线有哪些节点？各自负责什么？**

本项目使用 LangGraph 构建了一个 8 节点 DAG：

| 节点 | 作用 |
|------|------|
| `safety_check` | 检测查询是否安全/与 UNSW 相关，对无关或有害问题直接拒绝 |
| `query_rewrite` | 用 LLM 改写歧义查询，提升检索质量；识别纯导航意图（NAVIGATION）或不相关请求（REDIRECT） |
| `hyde_generate` | 生成假设性文档（HyDE），扩展语义空间 |
| `retrieve` | 混合检索：向量检索 + BM25，Top-30 结果 |
| `rerank` | Cross-encoder 重排序，Top-30 → Top-7 |
| `grade_documents` | CRAG 评级：LLM 判断检索结果是否相关，不相关则走 fallback |
| `generate` | 用相关 chunk 作为 context，调用 Gemini 生成最终答案 |
| `hallucination_check` | 检查答案中是否含有幻觉特征短语（如"I don't know"、"INSUFFICIENT_CONTEXT"），最多重试一次 |

多路径 fallback：安全检测不通过 → 直接返回警告；文档评级不通过 → 调用 LLM 直接回答（无 RAG context）；幻觉检测不通过 → 重试一次后 fallback。

---

**Q: 为什么用 LangGraph 而不是直接写 if/elif？**

if/elif 方式的问题：
- 流程硬编码，添加节点需改动主干逻辑
- 难以实现有条件的跳转、重试循环
- 状态传递混乱，调试困难

LangGraph 的优势：
- 每个节点是独立函数，关注点分离
- **条件边（conditional edges）** 天然支持分支和循环（如幻觉检测后的重试）
- 共享 `RAGState` TypedDict 做状态管理，各节点读写同一状态对象
- 便于单独测试每个节点

---

### Part 2：检索技术

---

**Q: 什么是向量检索（Semantic Search）？embedding 是如何工作的？**

Embedding 是将文本映射到高维向量空间的过程。语义相似的文本在向量空间中距离更近。

流程：
1. 建库阶段：将每个 chunk 通过 embedding 模型转化为向量，存入 ChromaDB
2. 查询阶段：将用户问题也转化为向量，在库中做近似最近邻搜索（ANN），取余弦相似度最高的 k 个文档

本项目使用 `sentence-transformers/all-MiniLM-L6-v2`：
- 384 维向量
- 本地 CPU 运行，无 API 配额限制
- 适合短文本对齐（query-chunk 匹配）

---

**Q: 什么是 BM25？为什么要混合搜索？**

BM25（Best Matching 25）是一种基于词频（TF）和逆文档频率（IDF）的概率排序模型，是经典的关键词搜索算法。

向量检索 vs BM25 各自的短板：
- **向量检索**：擅长语义理解，但对专有名词（如 `COMP9900`、`K17`）不敏感——"COMP9900"和"COMP1511"向量距离很近，但语义截然不同
- **BM25**：擅长精确词匹配，但无法理解同义词、改写

混合检索（Hybrid Search）用 **Reciprocal Rank Fusion（RRF）** 融合两路排名：
```
RRF_score = 1/(k + rank_vector) + 1/(k + rank_bm25)
```
兼顾语义理解与关键词精度。本项目混合评分阈值：`min_hybrid_score=70.0`，`min_bm25_score=3.0`，`min_rag_score=25.0`。

---

**Q: 什么是 HyDE？为什么要用它？**

HyDE（Hypothetical Document Embeddings，Gao et al. 2023）解决的问题：

**问题**：用户查询"COMP9900 有哪些要求？"只有 6 个词，但数据库里的相关文档有数百词。短查询向量与长文档向量语义距离大，导致召回率低。

**HyDE 解法**：
1. 用 LLM 基于查询生成一段 2-3 句的假设性答案（不要求准确，只要语义丰富）
2. 用这段假设文档的 embedding 去检索，而不是用原始查询

由于假设文档与真实文档结构相似（都是"document-like"文本），向量空间对齐更好。

本项目实现：双路检索（原始查询 + HyDE 文档），去重合并，综合排序。

---

**Q: 什么是 Cross-encoder Reranking？和 Bi-encoder 有什么区别？**

| | Bi-encoder | Cross-encoder |
|--|--|--|
| 工作方式 | 独立编码 query 和 doc，计算余弦相似度 | 将 query + doc 拼接，一起输入模型打分 |
| 速度 | 快（向量可预计算） | 慢（每对 (query, doc) 需推理一次） |
| 精度 | 较低（无法捕捉 query-doc 交互） | 高（充分建模 query-doc 语义交互） |
| 典型用途 | 初步召回（Top-100） | 精细重排序（Top-10 → Top-7） |

本项目用 Cross-encoder 做两阶段检索的第二阶段：
1. Bi-encoder（向量检索）粗召回 Top-30
2. Cross-encoder（`ms-marco-MiniLM-L-6-v2`）精细重排序 → Top-7

每个文档内容截断至 1500 字符避免超出 token 限制，重排分数写入 `metadata["rerank_score"]`。

---

**Q: 什么是 CRAG（Corrective RAG）？**

CRAG（Yan et al. 2024）的核心思想：在生成前加一道"相关性检查门"。

流程：
1. 从向量库检索文档
2. 用 LLM 评估这些文档与原始查询的相关性（二元判断：CORRECT / INCORRECT）
3. 如果 CORRECT → 正常生成
4. 如果 INCORRECT → 文档与查询无关，走 fallback（直接调用 LLM 无 RAG context 回答，或返回"不知道"）

本项目实现细节：
- 只取 Top-5 文档的前 300 字符做评估，节省 API 调用
- 评估 prompt 为二元 yes/no
- 评估失败时默认 CORRECT，避免误拦截正常查询

---

### Part 3：文档处理

---

**Q: 项目如何处理 PDF 文档？**

两步处理：

**Step 1：加载**
用 `PyMuPDF（fitz）` 按页提取文本，每页生成一个 `Document` 对象，附加 `content_type="pdf"` 元数据。

**Step 2：切块（Chunking）**
采用 spaCy 语义分句（`en_core_web_sm`）：
- 按句子分割后，每 3 句组成一个 chunk
- 对每个源文件，调用 Gemini 生成 1-2 句文档级摘要（同一 PDF 的摘要做内存缓存，避免重复调用）
- 每个 chunk 前缀：`[Document Context: {摘要}]\n\n{chunk 正文}`

这是 **Anthropic Contextual Retrieval** 技术：解决 chunk 碎片化导致检索时脱离上下文的问题。

---

**Q: 为什么需要 Chunking？chunk 大小如何选择？**

LLM 和向量检索都有 token 限制，无法直接处理整个文档。Chunking 将文档切成固定大小的片段。

Chunk 大小的权衡：
- 太小：chunk 失去上下文，语义不完整，召回准确率下降
- 太大：引入噪声，排序困难，超出 embedding 模型 token 限制

本项目参数配置（`CHUNK_CONFIG`）：
- `target_chunk_size=600`（字符）
- `min_chunk_size=200`
- `max_standalone_size=4000`
- PDF：3 句一个 chunk（语义边界，不截断句子）
- 爬虫内容：按 `## H2 标题` 切割后合并小节，保证结构完整性

---

### Part 4：向量数据库

---

**Q: 为什么选择 ChromaDB？**

ChromaDB 的优势：
- **嵌入式数据库**，无需独立服务进程（SQLite3 后端），适合 Docker 单容器部署
- 天然支持 LangChain 集成（`langchain-chroma`）
- 支持 metadata 过滤（按 `content_type`、`source` 筛选）
- 对于中小规模知识库（本项目数千个 chunk）性能足够

与 Pinecone/Weaviate 的区别：后者是云托管托管服务，有 API 成本，适合生产大规模场景。本项目作为课程 Demo 优先选择部署简单的本地方案。

---

**Q: 向量库如何做增量更新？**

本项目实现了两种更新模式：

**增量更新**（Admin 上传/删除文件触发）：
- 上传新 PDF → 解析 → 切块 → `add_documents_incremental()` 追加到 ChromaDB，不清空现有数据
- 删除文件 → `remove_documents_by_source()` 按 source URL 匹配删除对应 chunk

**全量重建**（`force_rebuild_vector_store()`）：
- 删除现有 ChromaDB 目录（避免 SQLite 锁）→ 重新处理所有 PDF 和爬虫内容 → 创建全新 ChromaDB
- 变更检测：通过 `source_files.txt` 记录上次处理的文件签名，下次启动时比对，仅在文件集有变化时触发自动重建

---

### Part 5：评测

---

**Q: 如何评估 RAG 系统的质量？**

本项目使用 **RAGAS（Retrieval Augmented Generation Assessment）** 框架：

| 指标 | 含义 |
|------|------|
| Answer Relevancy | 答案是否回答了用户的问题 |
| Faithfulness | 答案是否忠实于检索到的 context（无幻觉） |
| Context Precision | 检索到的文档有多少是真正相关的 |
| Context Recall | 相关文档有多少被检索到了 |

评测数据集：`backend/evaluation/datasets.py` 中手动编写了 50+ 条 Q&A ground truth，覆盖 5 类场景，使用 `ground_truth` 字段（RAGAS v0.2+ 规范）。

评测脚本：`backend/scripts/evaluation_benchmark.py` 调用真实 RAG 接口，对比模型答案与 ground truth，计算 RAGAS 指标。

---

### Part 6：系统设计

---

**Q: 整体系统架构是怎样的？**

```
用户
  ↓ HTTP
Vue 3 前端（:8080）
  ↓ REST API
Flask 后端（内部 :5000，Docker 映射 :3001）
  ↓
query_processor.py（缓存检查 → 会话历史）
  ↓
LangGraph RAG 图（graph_rag.py）
  ├── HuggingFace 本地 Embedding（ChromaDB 向量检索）
  ├── BM25 内存索引（关键词检索）
  ├── Cross-encoder Reranker（sentence-transformers）
  └── Google Gemini 2.5 Flash（改写/评级/生成）
```

数据层：
- ChromaDB：持久化向量库（SQLite3）
- JSONL 文件：聊天日志和缓存答案
- Docker Named Volume：HuggingFace 模型缓存（避免每次重启重下载）

---

**Q: 为什么 Embedding 用本地模型而不是 Google 的？**

原因有两个：

1. **API 配额**：Google `text-embedding-004` 免费版有调用次数限制；本地 `all-MiniLM-L6-v2` 无限制，知识库重建时需批量处理数千个 chunk，配额很快耗尽
2. **延迟**：本地推理（CPU）对于批量 embedding 比网络 API 更稳定，不受网络抖动影响

代价：模型质量略低于 Google 的大规模 embedding 模型，但对本项目场景（短英文文本对齐）已足够。

---

**Q: 项目中如何处理多轮对话？**

`query_processor.py` 中：
1. 按 `session_id` 从聊天日志中取最近 5 轮已成功回答的对话
2. 超过 200 字符的答案截断，节省 token
3. 格式化为 `User: ...\nAssistant: ...` 文本块
4. 拼入 Gemini prompt 的对话历史中

会话历史用于 Gemini 的多轮理解，但不影响 RAG 检索（检索仍基于当前问题，避免历史噪声干扰向量搜索）。

---

**Q: 有哪些 fallback 机制？**

| 触发条件 | Fallback 行为 |
|----------|--------------|
| 安全检测失败（不相关/有害问题） | 返回固定警告语，不调用检索 |
| 查询意图为"纯导航"（NAVIGATION） | 调用 Gemini 直接回答，不走 RAG |
| CRAG 评级为 INCORRECT（文档不相关） | 调用 Gemini 直接回答（无 RAG context） |
| 幻觉检测触发 | 重试一次生成，仍幻觉则走 fallback LLM |
| 整个流水线异常 | 返回"I do not know the answer" |
| 缓存命中 | 直接返回缓存结果，跳过整个流水线 |

---

**Q: 如何保证用户数据安全和 API Key 安全？**

- `.env` 文件含 `GOOGLE_API_KEY`，`.gitignore` 明确排除 `.env` 和 `key.json`，不进入版本控制
- `data/` 目录（含向量库、聊天日志）同样被 `.gitignore` 排除
- Admin 接口使用 JWT Token 鉴权，token 有效期 1 小时
- `SECRET_KEY` 用于签名 JWT，通过环境变量注入，不硬编码

---

### Part 7：常见追问

---

**Q: 项目中遇到的最大技术挑战是什么？**

参考答案：

> 最大挑战是**检索质量与生成幻觉的平衡**。初版只用向量检索，对 COMP9900 这类专有课程代码召回率不稳定；BM25 对同义词无能为力。引入混合检索后评分融合的阈值需要反复调试（`min_hybrid_score=70`）。
>
> 同时，纯 embedding 对短 chunk 的语义损失问题促使我们引入 Contextual Retrieval（为每个 chunk 前缀文档摘要），这显著降低了"答非所问"的比例。
>
> 工程上，ChromaDB 的 SQLite 并发锁问题在 Docker 热重载时反复出现，最终通过重建时先删除整个目录、增量更新时使用独立 async 队列解决。

---

**Q: 如果要继续优化，你会优先做什么？**

参考答案：

> 1. **评测驱动优化**：目前 RAGAS 评测是事后分析。下一步会建立 CI 中的自动评测流水线，每次修改流水线参数后自动回归测试，防止指标退化
> 2. **更好的 Chunking**：当前 PDF 用 spaCy 按句分割，对表格、代码块支持差。可以引入 Unstructured.io 或 LlamaParse 做结构化提取
> 3. **换用更强的 Embedding 模型**：`all-mpnet-base-v2` 或 `bge-m3`（支持中英文混合），提升语义对齐精度
> 4. **流式输出（Streaming）**：当前等待完整答案再返回，对长答案延迟明显。LangChain 的 `streaming=True` 可改善体验

---

*文档生成日期：2026-02-24*
*项目仓库：https://github.com/Cosmonaut-ene/UNSW_RAG_Assistance*
