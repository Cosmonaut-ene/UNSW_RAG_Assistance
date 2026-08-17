# SPEC.md — UNSW CSE Open Day Chatbot 重构

> SDD（Spec-Driven Development）驱动文档。开发前先读这份文件，明确当前任务所属模块。
> 模块完成 → PR → review → merge → 更新本文件状态（状态更新单独 commit：`docs(spec): mark <module> as completed`）。
> 禁止跳过 PR，禁止功能未完成时更新状态。

---

## 0. 待你决定的开放项

以下几项只有你能定，请在开工前把下面的 `[ ]` 改成 `[x]` 或填空，其余部分（技术栈、RAG 架构、模块清单）已经在讨论中定下来了，不需要你重新选。

**VPS / 云服务商**（跑 k3s 单节点，前面定的方向）
- [ ] DigitalOcean
- [ ] Vultr
- [ ] Oracle Cloud Free Tier
- [ ] 其他：__Hetzner___

**域名**：____________________（没有的话，先留空，用 VPS 公网 IP 起步也可以，域名 + HTTPS 可以晚点补）

**目标上线时间**：_2026年8月底_（哪怕是粗略的"某月底"，用来判断下面模块清单要不要压缩范围）

**这一轮先做哪个方向**（三选一，决定你先开哪个分支）
- [x] 按下面「模块清单」的既定顺序（阶段 A→E，RAG 质量优先，K8s 部署放后面）
- [ ] 先把 K8s/CI/CD 部署跑通，哪怕 RAG 还带着已知问题——优先拥有一个「能给别人访问的 demo 链接」
- [ ] 两条线并行（如果你时间充裕，且不介意上下文切换）

**Demo 的 MVP 范围**（面试官点开链接，最少要能看到什么）
- [ ] 能问答、有 K8s 部署链接即可，RAG 质量问题可以留在 README 里坦白说明「已知问题+计划」
- [ ] 至少要完成阶段 A+B（检索分数不再造假）才愿意公开链接
- [x] 全部 17 项（13 项 RAG 修复 + 4 项基础设施）在 2026-08-31 前全部完成才公开链接

**协作方式确认**：代码由我（Claude）实现，你负责确认/裁决每一项 SPEC 决策并做最终 review；基础设施模块里需要账号/密钥操作的步骤（Hetzner 注册、API token、SSH 密钥、GitHub secrets、`terraform apply`）需要你配合执行，我会在对应模块开发到那一步时明确列出需要你做的具体操作。

---

## 1. 背景与目标

这是一个 COMP9900 capstone 项目（UNSW CSE Open Day 问答机器人），当前技术栈：Flask + LangGraph RAG pipeline（Gemini 2.5 Flash + ChromaDB + BM25 + cross-encoder rerank）+ Vue3 前端。

本轮重构的目的**不是修一个"坏掉的产品"**，而是：

1. 引入 AU 2026 招聘市场对 entry/junior RAG·后端岗位的常见技术栈要求（K8s、CI/CD、可观测性、IaC），做成一个可被面试官实际访问的 demo
2. 借着这次重构，逐节点拷问现有 RAG pipeline 的设计合理性，把"能跑"的实现改成"每一步都能讲清楚为什么这么做"的实现
3. 过程本身采用 SDD：先写清楚需求和架构，再按模块开发。协作方式已调整为——你负责确认/裁决 SPEC 里的每一项决策，代码由我实现，你做最终 review；面试时的"讲述能力"通过你对每个决策的 why 有清楚认知来保证，而不是靠亲手敲代码

---

## 2. 技术栈决策（已确定）

| 模块 | 决策 | 备注 |
|---|---|---|
| 容器编排 | k3s 单节点 | 部署在低成本 VPS，manifest 语法和生产 EKS/GKE 一致 |
| 本地开发 | 保留 `docker-compose.dev.yml` | 与 K8s 部署解耦，互不影响 |
| CI/CD | GitHub Actions + GHCR | push main → 自动 build/test → 部署需手动 approve（GitHub Environments） |
| 测试门禁 | backend pytest + frontend vitest 必须通过 | 未通过不进入构建/部署阶段 |
| IaC | Terraform | 范围仅限 VPS 供应 + DNS，不做多节点/多云 |
| 可观测性 | OpenTelemetry（RAG pipeline 每节点独立 span）→ Grafana Cloud 免费层 | VPS 上只跑轻量 OTel collector，不自建 Prometheus/Grafana |

**决策依据**：AU 2026 RAG/AI Engineer 岗位 JD 高频要求 Kubernetes、Docker、CI/CD、可观测性（详见对话中 WebSearch 调研结果，来源含 SEEK、Platform Engineering Recruitment Australia 等）。

---

## 3. RAG Pipeline 重新设计（已确定架构）

逐节点审查后的目标架构，核心原则：**把"自由文本 + 字符串猜测"统一改成"结构化字段 + 明确契约"**。

```
safety_check（结构化四分类：SAFE/HARMFUL/OFF_TOPIC/INJECTION）
  → query_rewrite（已合并 HyDE，结构化输出 {intent, rewritten_query, hypothetical_document}）
    → retrieve（向量检索真实分数 + BM25 融合 + HyDE检索，不重复计算）
      → rerank（cross-encoder，top_k=12）
        → grade_documents / CRAG（逐篇结构化过滤，覆盖全部候选）
          → generate（精简调用，去掉重复的安全检查/改写，prompt 加注入防线）
            → hallucination_check（引用校验[确定性] + 忠实度检查[结构化LLM]）
              → END（真实答案 / 拒答 / fallback_node 兜底答案，三种终止状态独立）
```

完整的问题清单、每个节点的具体 bug、以及这张架构图的可视化版本记录在本次对话生成的 Artifact 里（RAG 节点审查笔记）。

---

## 4. 模块清单与状态跟踪

状态用：`未开始` / `进行中` / `已完成`。完成后连同 PR 链接一起更新，且必须是 merge 之后才能标记。

### 阶段 A · 无风险清理（可并行，无架构依赖）

| # | 模块 | 分支建议 | 状态 | PR |
|---|---|---|---|---|
| A1 | 修复 `hyde_search` 内重复检索 rewritten_query | `fix/hyde-duplicate-search` | 未开始 | |
| A2 | `generate_node` 去掉重复的安全检查/query改写 | `fix/generate-node-dedup` | 未开始 | |
| A3 | HyDE prompt 去掉编造课程代码的指令 | `fix/hyde-prompt-fabrication` | 未开始 | |

### 阶段 B · 检索质量根基

| # | 模块 | 分支建议 | 状态 | PR | 依赖 |
|---|---|---|---|---|---|
| B1 | 修复向量检索分数被硬编码为 100 | `fix/vector-score-hardcoded` | 未开始 | | — |
| B2 | 排查 context_recall 绝对值偏低的根因 | `chore/context-recall-investigation` | 未开始 | | 依赖 B1 |

### 阶段 C · 结构化输出范式

| # | 模块 | 分支建议 | 状态 | PR | 依赖 |
|---|---|---|---|---|---|
| C1 | `safety_check` 改为单次结构化四分类 | `feat/safety-check-structured` | 未开始 | | — |
| C2 | 生成 prompt 加分隔符 + 间接注入防线 | `feat/generation-injection-defense` | 未开始 | | 建议与 C1 同一 PR |
| C3 | 合并 `query_rewrite` 与 `hyde_generate` 为单次结构化调用 | `refactor/merge-query-rewrite-hyde` | 未开始 | | 依赖 C1 |

### 阶段 D · 质量把关重写

| # | 模块 | 分支建议 | 状态 | PR | 依赖 |
|---|---|---|---|---|---|
| D1 | 重写 CRAG 为逐篇结构化过滤，覆盖全部候选 | `refactor/crag-per-chunk-filtering` | 未开始 | | — |
| D2 | 统一两份生成 prompt，修正 INSUFFICIENT_CONTEXT 定义冲突 | `refactor/unify-generation-prompts` | 未开始 | | — |
| D3 | 重写 `hallucination_check` 为忠实度+引用校验 | `refactor/hallucination-check-rewrite` | 未开始 | | 依赖 D2 |

### 阶段 E · 收尾整合

| # | 模块 | 分支建议 | 状态 | PR | 依赖 |
|---|---|---|---|---|---|
| E1 | 所有 RAG 可调参数收敛到统一 config，禁止硬编码 | `refactor/unify-rag-config` | 未开始 | | 依赖 B1、D1、D3 |
| E2 | `fallback_node` 按 `fallback_reason` 定制 prompt，清理死代码 | `refactor/fallback-node-reasons` | 未开始 | | 依赖 C3、D1、D3 |

### 基础设施模块（技术栈引入，可与上面并行）

| # | 模块 | 分支建议 | 状态 | PR |
|---|---|---|---|---|
| I1 | k3s 单节点部署（Deployment/Service/Ingress + Helm chart） | `feat/k3s-deployment` | 未开始 | |
| I2 | GitHub Actions CI/CD（build/test/GHCR/手动部署 approve） | `feat/cicd-pipeline` | 未开始 | |
| I3 | Terraform（VPS + DNS 供应） | `feat/terraform-vps` | 未开始 | |
| I4 | OpenTelemetry tracing（RAG pipeline 每节点 span）+ Grafana Cloud 接入 | `feat/otel-tracing` | 未开始 | |

---

## 5. 验收标准

每个模块 PR 需满足：
- 对应的 bug/问题描述里提到的失败场景，有对应的测试用例（unit 或 integration）覆盖
- 不引入新的硬编码魔法数字（阶段 E1 之后，新参数一律进统一 config）
- Conventional Commits 规范，PR 走 review，不允许自行 merge 到 main
- 阶段 D/E 涉及 RAGAS 评测的模块，PR 描述里附上修改前后的评测对比（参考 `EVALUATION_REPORT_100_QUERIES.md` 的格式）

---

## 6. Git 工作流（遵循全局规范）

- `main` 稳定分支，禁止直接提交
- 分支命名：`feat/` · `fix/` · `refactor/` · `chore/` + 短横线描述（见上面各模块建议分支名）
- Conventional Commits
- 功能完成 → PR → review → merge → 更新本文件对应模块状态（独立 commit：`docs(spec): mark <module> as completed`）
