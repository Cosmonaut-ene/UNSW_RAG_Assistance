# RAG评估报告 - RAGAS 自动化评估结果

## ✅ 2026-09-10 真实重跑结果（当前最新，唯一可以在面试中直接引用的数字）

**评估日期**: 2026-09-10 14:33（本次会话实际执行，非转述历史文档）
**测试规模**: 30 条 RAGAS 评分查询 + 9 条行为测试查询（越界/导航类，二元 pass/fail，不计入 RAGAS 分数）
**耗时**: 5356.7 秒（约 89 分钟，30 条查询全部真实调用 Gemini API + 本地 embedding/reranker）
**产出文件**: `data/evaluation/results/eval_run_20260910_143440.json`（可溯源）
**运行方式**: `python scripts/run_evaluation.py --mode full --sample-size 30`，独立 venv + 仓库 `.env` 里的真实 `GOOGLE_API_KEY`

### 🐛 重跑前先修了一个真实 bug，不是走个流程

启动第一次评估时，日志里全程是 `[SearchEngine] Error during similarity search: Could not connect to tenant default_tenant`，30 条查询检索到的文档数量全是 0，所有回答都退化成无 context 的裸 LLM fallback。追查后发现真正的异常其实是 ChromaDB 抛出的 `attempt to write a readonly database`——`data/knowledge_base/vector_store/chroma.sqlite3` 文件属主是 `root`（大概率是之前用 Docker 跑评估留下的），当前用户没有写权限，上层代码把这个权限异常吞掉后只打出一条容易误导人的 "tenant" 提示。`sudo chown -R zhang:zhang data/` 修复后，重新验证向量库能正常检索出真实的 UNSW handbook 内容（6139 个 chunk），再重跑评估。**如果不修这个权限问题就直接跑评估，产出的所有分数都是"无检索裸答"的分数，没有意义。**

### 📊 核心性能指标（RAGAS，30 条查询，当前代码 = 2026-04 调优后的参数配置）

| 指标 | 分数 | 有效样本数 | 说明 |
|------|------|-----------|------|
| **Faithfulness（事实准确性）** | **0.984** | 22/30 | 优秀；另外 8 条是导航/越界类查询走了 fallback，无检索 context，RAGAS 跳过不计分 |
| **Answer Relevancy（答案相关性）** | **0.851** | 30/30 | 良好 |
| **Context Recall（上下文召回）** | **0.429** | 22/30 | 系统自己的 `performance_analysis` 标注为 "Poor" |
| **Context Precision（上下文精度）** | **0.452** | 18/30 | 系统自己的 `performance_analysis` 标注为 "Poor" |

Pipeline 自带的整体评级：`overall_performance: "acceptable"`（不是"优秀"，是"可接受"——这是代码自己算出来的，不是我加的措辞）。

**行为测试（behavioral tests，9条，越界/导航类查询）**：9/9 全部通过（pass_rate 1.0）——包括"悉尼这周天气""帮我调试 MIT 的作业""转学分能不能算"等问题，都被正确识别为越界或导航意图并走 fallback，没有被 RAG 硬答。这组测试证明的是"知道自己不知道"的能力，和上面 RAGAS 的检索质量是两回事，不要混着引用。

**延迟**：平均响应 15.2 秒/条，p95 29.4 秒，最慢 35.2 秒——这个延迟对一个每步都要调 LLM（安全检测+改写+HyDE 合一次调用、CRAG 逐文档分级、生成）的多节点 pipeline 是预期内的，但如果面试官问"生产环境能接受吗"，诚实的答案是"目前偏慢，值得用流式输出改善体验"。

**Fallback 比例**：30 条里 8 条（26.7%）走了 fallback（越界/导航/无相关文档），这个比例本身就说明了测试集里故意混入了不少"应该拒绝回答"的问题，不是纯粹考察检索能力的干净测试集。

### 面试如何讲这组数字

- **诚实的结论**：Faithfulness 和 Answer Relevancy 表现好（系统不瞎编、答得对题），但 Context Recall/Precision 是真正的短板——检索出来的文档里有一半以上是噪声或漏检。这和 2026-04 调优时观察到的"recall/precision 偏低"是同一个问题，调优后有改善（相比 4 月的 0.08-0.17 区间提升到了 0.43-0.45），但仍然没有达到"优秀"水平
- 不要说"全面超越行业标准"——precision/recall 目前只能算刚过及格线
- 可以主动讲清楚"重新跑之前先发现并修了一个数据侵蚀问题（vector store 权限）"这个故事本身——这恰恰证明了"没有可信的评估流程，连'调优是否有效'这种基本问题都无法回答"，是很好的工程严谨性证据

---

## 历史记录（2026-04，仅供参考，不要在面试中引用作为当前状态）

2026-04-03/04-04 曾做过一轮 30-query 的调优前后对比，用于验证参数从 `vector_k=20→50` 等的调整方向。当时的真实 JSON 产出显示：

| 指标 | 调优前 | 调优后 |
|------|--------|--------|
| Faithfulness | 0.805 | 0.718 |
| Answer Relevancy | 0.691 | 0.749 |
| Context Recall | 0.094 | 0.100 |
| Context Precision | 0.166 | 0.152 |

这组数字比本次（2026-09-10）的结果差很多，尤其是 Context Recall/Precision——**差异的主要原因很可能不是参数本身，而是当时的向量库检索是否也受过类似的权限或环境问题影响，已经无法回溯确认**（当时的 JSON 产出没有记录环境细节）。这也是为什么"用一次性跑出来的数字定论"是危险的——本次能发现权限问题，纯粹是因为过程记录得够细，而不是因为运气好。

### 当时的调优方法（流程仍然有效，仅数字已被本次重跑取代）

参数调优通过自动化三阶段流程完成：
1. **Random Search（50次）**：无 LLM 的 proxy metric（GT关键词召回 + 预期关键词命中 + chunk丰富度）
2. **Focused Grid Search**：在 top-5 区域精细化搜索
3. **RAGAS Validation**：对 top-5 配置运行完整 RAGAS 评估

调优工具：`backend/evaluation/retrieval_tuner.py` + `backend/scripts/run_tuner.py`

当前生效的参数配置（`backend/config/rag_config.py`，2026-09-10 代码核实）：

| 参数 | 值 |
|------|-----|
| `vector_k` | 50 |
| `max_hybrid_results` | 50 |
| `reranker_top_k` | 12 |
| `rag_weight` | 0.7 |
| `min_hybrid_score` | 50.0 |
| `min_bm25_score` | 1.0 |

---

## 🔧 诚实的改进建议

1. **Context Recall / Precision 是真正的短板**（0.43-0.45），不是"已经超越行业优秀水平"——如果继续做这个项目，这是第一优先级
2. **评估流程本身需要加固**：这次差点因为一个文件权限问题产出一份完全无意义的评估报告。建议在评估脚本里加一个前置校验（比如跑评估前先对向量库做一次真实的 `similarity_search` 冒烟测试，检索到 0 个文档就直接 fail fast，而不是让 30 条查询全部退化成裸答后才被发现）
3. 应该建立 CI 里的自动回归评测，每次改动 retrieval 参数后跑一次 30-query 集，防止指标跑偏没人发现——这份报告此前"两份文档拼在一起没人发现、内容严重过期"就是没有自动化回归检查的直接后果

---

*本报告已于 2026-09-10 基于本次真实重跑（`eval_run_20260910_143440.json`）改写，替换此前内部自相矛盾、部分数字无据可查、且底层数据被权限问题污染的历史版本。*
