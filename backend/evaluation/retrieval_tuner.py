"""
Retrieval parameter tuner for the UNSW RAG system.

Workflow:
  1. Random search (proxy metric, no LLM) — ~50 trials
  2. Focused grid search around the best region — ~20 trials
  3. RAGAS validation on top-5 configs — ~30 min

Run via: python scripts/run_tuner.py --mode random|grid|validate
"""

import json
import math
import random
import re
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .tuner_config import (
    BASELINE_CONFIG,
    SEARCH_SPACE,
    TUNER_SETTINGS,
    RetrievalConfig,
)

# ──────────────────────────────────────────────
# Proxy Metric (no LLM, no network calls)
# ──────────────────────────────────────────────

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "will",
    "are", "been", "were", "they", "their", "about", "which", "when",
    "also", "into", "more", "some", "such", "than", "then", "there",
    "these", "those", "what", "your", "each", "can", "course", "courses",
    "unsw", "students", "student", "include", "including", "study",
    "program", "programs", "school", "university", "faculty",
}


def _extract_gt_terms(text: str) -> List[str]:
    """Extract meaningful keywords from ground truth text."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    return [w for w in words if w not in _STOPWORDS]


def proxy_score(
    retrieved_docs: List[Dict[str, Any]],
    ground_truth: str,
    expected_keywords: List[str],
) -> float:
    """
    Compute a fast, LLM-free retrieval quality score.

    Args:
        retrieved_docs: List of dicts with 'page_content' key
        ground_truth: Expected answer string
        expected_keywords: Pre-annotated keywords from the test dataset

    Returns:
        Float in [0, 1], higher is better
    """
    weights = TUNER_SETTINGS["proxy_weights"]
    rich_min = TUNER_SETTINGS["rich_chunk_min_len"]

    all_text = " ".join(
        d.get("page_content", d.get("content", "")) for d in retrieved_docs
    ).lower()

    if not all_text.strip():
        return 0.0

    # 1. Ground-truth keyword recall
    gt_terms = _extract_gt_terms(ground_truth)
    if gt_terms:
        gt_recall = sum(1 for t in gt_terms if t in all_text) / len(gt_terms)
    else:
        gt_recall = 0.0

    # 2. expected_context_keywords hit rate
    if expected_keywords:
        kw_hits = sum(1 for k in expected_keywords if k.lower() in all_text)
        kw_score = kw_hits / len(expected_keywords)
    else:
        kw_score = 0.0

    # 3. Rich chunk ratio (penalise metadata-only results)
    if retrieved_docs:
        rich = sum(
            1 for d in retrieved_docs
            if len(d.get("page_content", d.get("content", ""))) >= rich_min
        )
        richness = rich / len(retrieved_docs)
    else:
        richness = 0.0

    return (
        weights["gt_recall"] * gt_recall
        + weights["kw_hits"] * kw_score
        + weights["richness"] * richness
    )


# ──────────────────────────────────────────────
# Retrieval Runner (no LLM calls)
# ──────────────────────────────────────────────

class RetrievalRunner:
    """
    Executes the retrieval-only portion of the pipeline for a given config.
    Caches the vector store + BM25 index so they are built only once.
    Skips: query rewriting, HyDE, CRAG, LLM generation.
    """

    def __init__(self) -> None:
        print("[Tuner] Initialising RetrievalRunner (loading vector store + BM25)…")
        from rag.vector_store import load_vector_store
        self._vector_store = load_vector_store()

        from rag.bm25_search import BM25SearchEngine
        self._bm25 = BM25SearchEngine(self._vector_store)

        print("[Tuner] RetrievalRunner ready.")

    def run(self, query: str, config: RetrievalConfig) -> List[Dict[str, Any]]:
        """
        Run retrieval with the given config and return the final reranked docs.
        """
        # 1. Vector search
        from rag.search_engine import search_documents_with_scores
        raw_results = search_documents_with_scores(query, k=config.vector_k)
        rag_results = [
            {
                "page_content": doc.page_content,
                "metadata": {**doc.metadata, "rag_score": 100},
            }
            for doc, _score in raw_results
        ]

        # 2. BM25 search (reuse cached index)
        bm25_raw = self._bm25.search(query, top_k=config.max_hybrid_results * 2)

        # 3. Hybrid combination (replicate HybridSearchEngine.combine_results logic
        #    but with config-supplied weights / thresholds, no re-init of BM25)
        hybrid_docs = self._hybrid_combine(
            rag_results, bm25_raw, config
        )

        # 4. Rerank
        from rag.reranker import rerank_documents
        reranked = rerank_documents(query, hybrid_docs, top_k=config.reranker_top_k)
        return reranked

    def _hybrid_combine(
        self,
        rag_results: List[Dict],
        bm25_results: List[Dict],
        config: RetrievalConfig,
    ) -> List[Dict]:
        """Lightweight replication of HybridSearchEngine.combine_results."""
        seen: set = set()
        all_docs: List[Dict] = []

        # Add RAG docs
        for r in rag_results:
            content = r.get("page_content", "")
            key = content[:100]
            if key and key not in seen:
                seen.add(key)
                r.setdefault("metadata", {})
                r["metadata"]["rag_score"] = 100
                r["metadata"]["bm25_score"] = 0
                all_docs.append(r)

        # Merge BM25 docs
        for b in bm25_results:
            content = b.get("content", b.get("page_content", ""))
            key = content[:100]
            raw_bm25 = b.get("bm25_score", b.get("metadata", {}).get("bm25_score", 0))
            norm_bm25 = min(raw_bm25 * 10, 100)

            if key and key not in seen:
                seen.add(key)
                all_docs.append({
                    "page_content": content,
                    "metadata": {
                        **b.get("metadata", {}),
                        "rag_score": 0,
                        "bm25_score": norm_bm25,
                    },
                })
            else:
                # Merge BM25 score into existing doc
                for doc in all_docs:
                    if doc.get("page_content", "")[:100] == key:
                        doc["metadata"]["bm25_score"] = norm_bm25
                        break

        # Compute hybrid scores and filter
        bm25_w = 1.0 - config.rag_weight
        filtered: List[Dict] = []
        for doc in all_docs:
            meta = doc["metadata"]
            rag_s = meta.get("rag_score", 0)
            bm25_s = meta.get("bm25_score", 0)
            hybrid_s = rag_s * config.rag_weight + bm25_s * bm25_w
            meta["hybrid_score"] = hybrid_s

            if (
                hybrid_s >= config.min_hybrid_score
                or rag_s >= config.min_rag_score
                or bm25_s >= config.min_bm25_score
            ):
                filtered.append(doc)

        filtered.sort(key=lambda x: x["metadata"]["hybrid_score"], reverse=True)
        return filtered[: config.max_hybrid_results]


# ──────────────────────────────────────────────
# Parameter Searcher
# ──────────────────────────────────────────────

class ParameterSearcher:
    """Random search + focused grid search over SEARCH_SPACE."""

    def __init__(self, seed: int = TUNER_SETTINGS["random_seed"]) -> None:
        self._rng = random.Random(seed)

    def random_configs(self, n: int) -> List[RetrievalConfig]:
        """Sample n random configs from SEARCH_SPACE."""
        configs: List[RetrievalConfig] = []
        for _ in range(n):
            params = {k: self._rng.choice(v) for k, v in SEARCH_SPACE.items()}
            configs.append(RetrievalConfig(**params))
        return configs

    def focused_configs(self, top_results: List[Dict[str, Any]]) -> List[RetrievalConfig]:
        """
        Build a focused grid from the top results.
        For each param, take the most common value among top configs
        and the adjacent values in SEARCH_SPACE.
        """
        if not top_results:
            return []

        top_params = [r["config"] for r in top_results]

        # Find most frequent value per param
        best: Dict[str, Any] = {}
        for key in SEARCH_SPACE:
            values = [p[key] for p in top_params if key in p]
            best[key] = max(set(values), key=values.count)

        # Gather candidates: best ± 1 step
        candidates: Dict[str, List[Any]] = {}
        for key, space in SEARCH_SPACE.items():
            b = best[key]
            idx = space.index(b) if b in space else 0
            neighbours = {space[i] for i in [idx - 1, idx, idx + 1] if 0 <= i < len(space)}
            candidates[key] = sorted(neighbours, key=lambda x: (isinstance(x, str), x))

        # Cartesian product (cap at 64 to avoid explosion)
        keys = list(candidates.keys())
        grid = list(product(*[candidates[k] for k in keys]))
        self._rng.shuffle(grid)
        grid = grid[:64]

        return [RetrievalConfig(**dict(zip(keys, row))) for row in grid]


# ──────────────────────────────────────────────
# Tuner Orchestrator
# ──────────────────────────────────────────────

class TunerOrchestrator:
    """Coordinates the full tuning workflow."""

    def __init__(self, results_dir: Optional[str] = None) -> None:
        if results_dir is None:
            results_dir = str(Path(__file__).parent.parent / "data" / "evaluation" / "results")
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)

        self._runner: Optional[RetrievalRunner] = None
        self._queries: List[Dict] = []

    # ── Data loading ──────────────────────────────────────────

    def _ensure_runner(self) -> RetrievalRunner:
        if self._runner is None:
            self._runner = RetrievalRunner()
        return self._runner

    def _load_queries(self) -> List[Dict]:
        if self._queries:
            return self._queries

        path = Path(__file__).parent.parent / "data" / "evaluation" / "test_queries.json"
        if not path.exists():
            raise FileNotFoundError(f"Test queries not found at {path}. Run setup-datasets first.")

        with open(path) as f:
            queries = json.load(f)

        # Only keep queries that have ground_truth
        self._queries = [q for q in queries if q.get("ground_truth", "").strip()]
        print(f"[Tuner] Loaded {len(self._queries)} queries with ground truth.")
        return self._queries

    # ── Core evaluation loop ──────────────────────────────────

    def _evaluate_config(
        self, config: RetrievalConfig, queries: List[Dict], verbose: bool = False
    ) -> float:
        """Score a single config using the proxy metric. Returns mean score."""
        runner = self._ensure_runner()
        scores: List[float] = []

        for q in queries:
            try:
                docs = runner.run(q["query"], config)
                s = proxy_score(
                    docs,
                    q.get("ground_truth", ""),
                    q.get("expected_context_keywords", []),
                )
                scores.append(s)
            except Exception as e:
                if verbose:
                    print(f"  [Tuner] Query failed: {e}")
                scores.append(0.0)

        return float(sum(scores) / len(scores)) if scores else 0.0

    def _run_search(
        self, configs: List[RetrievalConfig], label: str
    ) -> List[Dict[str, Any]]:
        """Evaluate a list of configs and return sorted results."""
        queries = self._load_queries()
        results: List[Dict[str, Any]] = []

        # Always include baseline
        baseline_score = self._evaluate_config(BASELINE_CONFIG, queries)
        print(f"[Tuner] Baseline proxy score: {baseline_score:.4f}")

        total = len(configs)
        best_so_far = baseline_score

        for i, cfg in enumerate(configs, 1):
            t0 = time.time()
            score = self._evaluate_config(cfg, queries)
            elapsed = time.time() - t0
            results.append({"config": cfg.as_dict(), "proxy_score": round(score, 6)})

            if score > best_so_far:
                best_so_far = score
                marker = " ← best"
            else:
                marker = ""

            print(
                f"[Tuner] [{label}] {i:3d}/{total} | score={score:.4f} | "
                f"best={best_so_far:.4f} | {elapsed:.1f}s{marker}"
            )

        results.sort(key=lambda x: x["proxy_score"], reverse=True)
        return results

    # ── Public API ────────────────────────────────────────────

    def run_random_search(self, n: int = TUNER_SETTINGS["n_random"]) -> List[Dict]:
        """Phase 1: random search."""
        searcher = ParameterSearcher()
        configs = searcher.random_configs(n)
        print(f"[Tuner] Starting random search: {n} configs…")
        results = self._run_search(configs, "random")
        self._save_results(results, "random")
        self._print_top(results, k=5, label="Random Search")
        return results

    def run_focused_search(self, top_results: Optional[List[Dict]] = None) -> List[Dict]:
        """Phase 2: focused grid search around the best region from phase 1."""
        if top_results is None:
            top_results = self._load_latest_results("random")

        top_k = TUNER_SETTINGS["top_k_focused"]
        searcher = ParameterSearcher()
        configs = searcher.focused_configs(top_results[:top_k])

        if not configs:
            print("[Tuner] No focused configs generated.")
            return []

        print(f"[Tuner] Starting focused grid search: {len(configs)} configs…")
        results = self._run_search(configs, "focused")

        # Merge with random results and re-sort
        all_results = (top_results or []) + results
        all_results.sort(key=lambda x: x["proxy_score"], reverse=True)
        # Deduplicate by config
        seen_cfgs: set = set()
        deduped: List[Dict] = []
        for r in all_results:
            key = json.dumps(r["config"], sort_keys=True)
            if key not in seen_cfgs:
                seen_cfgs.add(key)
                deduped.append(r)

        self._save_results(deduped, "grid")
        self._print_top(deduped, k=5, label="Focused Grid (merged)")
        return deduped

    def run_ragas_validation(
        self,
        top_results: Optional[List[Dict]] = None,
        top_k: int = TUNER_SETTINGS["top_k_validate"],
        sample_size: int = 30,
    ) -> Dict[str, Any]:
        """Phase 3: validate top-k configs with full RAGAS evaluation."""
        if top_results is None:
            top_results = self._load_latest_results("grid") or self._load_latest_results("random")

        if not top_results:
            raise RuntimeError("No prior tuning results found. Run random/grid search first.")

        candidates = top_results[:top_k]
        print(f"[Tuner] Validating top {len(candidates)} configs with RAGAS (sample_size={sample_size})…")

        from .pipeline import EvaluationPipeline

        validation_results: List[Dict[str, Any]] = []

        for rank, candidate in enumerate(candidates, 1):
            cfg = RetrievalConfig.from_dict(candidate["config"])
            print(f"\n[Tuner] Validating config {rank}/{len(candidates)}: {cfg.as_dict()}")
            print(f"        proxy_score={candidate['proxy_score']:.4f}")

            pipeline = EvaluationPipeline(retrieval_config=cfg)
            report = pipeline.run_comprehensive_evaluation(sample_size=sample_size)

            agg = report.get("aggregate_scores", {})
            validation_results.append({
                "rank": rank,
                "config": cfg.as_dict(),
                "proxy_score": candidate["proxy_score"],
                "context_recall": agg.get("context_recall"),
                "context_precision": agg.get("context_precision"),
                "faithfulness": agg.get("faithfulness"),
                "answer_relevancy": agg.get("answer_relevancy"),
                "full_report": report,
            })

            print(
                f"  context_recall={agg.get('context_recall', 'N/A'):.4f}  "
                f"context_precision={agg.get('context_precision', 'N/A'):.4f}"
            )

        # Baseline for comparison
        print("\n[Tuner] Running RAGAS baseline…")
        baseline_pipeline = EvaluationPipeline()
        baseline_report = baseline_pipeline.run_comprehensive_evaluation(sample_size=sample_size)
        baseline_agg = baseline_report.get("aggregate_scores", {})

        output = {
            "baseline": {
                "config": BASELINE_CONFIG.as_dict(),
                "context_recall": baseline_agg.get("context_recall"),
                "context_precision": baseline_agg.get("context_precision"),
                "faithfulness": baseline_agg.get("faithfulness"),
                "answer_relevancy": baseline_agg.get("answer_relevancy"),
            },
            "candidates": validation_results,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        self._save_results(output, "validation")
        self._print_validation_table(output)
        return output

    # ── Helpers ───────────────────────────────────────────────

    def _save_results(self, data: Any, label: str) -> Path:
        ts = int(time.time())
        path = self._results_dir / f"tuner_{label}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[Tuner] Results saved to {path}")
        return path

    def _load_latest_results(self, label: str) -> List[Dict]:
        files = sorted(self._results_dir.glob(f"tuner_{label}_*.json"), reverse=True)
        if not files:
            print(f"[Tuner] No saved results found for label '{label}'.")
            return []
        print(f"[Tuner] Loading results from {files[0]}")
        with open(files[0]) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        # validation output is a dict — return candidates list
        return data.get("candidates", [])

    @staticmethod
    def _print_top(results: List[Dict], k: int = 5, label: str = "") -> None:
        print(f"\n{'─'*60}")
        print(f"  Top {k} configs — {label}")
        print(f"{'─'*60}")
        for i, r in enumerate(results[:k], 1):
            print(f"  #{i}  score={r['proxy_score']:.4f}  config={r['config']}")
        print(f"{'─'*60}\n")

    @staticmethod
    def _print_validation_table(output: Dict[str, Any]) -> None:
        baseline = output["baseline"]
        candidates = output["candidates"]

        def fmt(v: Any) -> str:
            return f"{v:.4f}" if isinstance(v, float) else str(v)

        print(f"\n{'═'*80}")
        print("  RAGAS Validation Results")
        print(f"{'═'*80}")
        header = f"{'':>6}  {'recall':>8}  {'prec':>8}  {'faith':>8}  {'relevancy':>10}  config"
        print(header)
        print(f"{'─'*80}")

        bl = baseline
        print(
            f"{'BASE':>6}  {fmt(bl['context_recall']):>8}  {fmt(bl['context_precision']):>8}  "
            f"{fmt(bl['faithfulness']):>8}  {fmt(bl['answer_relevancy']):>10}  (current)"
        )

        for r in candidates:
            tag = f"#{r['rank']}"
            cfg_short = f"vk={r['config'].get('vector_k')} rk={r['config'].get('reranker_top_k')}"
            print(
                f"{tag:>6}  {fmt(r['context_recall']):>8}  {fmt(r['context_precision']):>8}  "
                f"{fmt(r['faithfulness']):>8}  {fmt(r['answer_relevancy']):>10}  {cfg_short}"
            )

        print(f"{'═'*80}\n")
