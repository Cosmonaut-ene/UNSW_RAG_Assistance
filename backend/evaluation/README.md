# RAG Evaluation System

A comprehensive evaluation framework for the UNSW CSE Chatbot RAG system using industry-standard RAGAS metrics.

## Overview

This evaluation system provides objective performance measurement of your RAG (Retrieval-Augmented Generation) system using four core metrics:

- **Faithfulness**: Measures factual accuracy against retrieved contexts
- **Answer Relevancy**: Evaluates relevance to the original query  
- **Context Recall**: Assesses coverage of relevant information in retrieval
- **Context Precision**: Measures signal-to-noise ratio of retrieved contexts

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install ragas==0.1.21 datasets==2.20.0
```

### 2. Setup Evaluation Datasets

```bash
python scripts/run_evaluation.py --setup-datasets
```

### 3. Run Quick Evaluation

```bash
python scripts/run_evaluation.py --mode quick --sample-size 10
```

## Components

### Core Modules

- **`metrics.py`**: RAGEvaluator class implementing RAGAS metrics
- **`datasets.py`**: EvaluationDataset for ground truth and test data creation
- **`pipeline.py`**: EvaluationPipeline for automated testing workflows
- **`config.py`**: Configuration settings and performance thresholds

### Test Data

- **Ground Truth**: 12+ carefully crafted UNSW-specific Q&A pairs
- **Test Queries**: Auto-generated variations and rephrasing of ground truth questions
- **Categories**: Course info, prerequisites, programs, campus, admissions

### Scripts

- **`run_evaluation.py`**: Standalone evaluation script with multiple modes
- **`evaluation_benchmark.py`**: Performance benchmarking and regression testing

## Usage Examples

### Command Line Evaluation

```bash
# Quick evaluation with 10 queries
python scripts/run_evaluation.py --mode quick --sample-size 10

# Full comprehensive evaluation  
python scripts/run_evaluation.py --mode full --sample-size 50

# Category analysis
python scripts/run_evaluation.py --mode category

# A/B test hybrid vs semantic search
python scripts/run_evaluation.py --mode ab-test

# Evaluate single query
python scripts/run_evaluation.py --mode single --query "What is COMP9900?"

# Disable hybrid search (semantic only)
python scripts/run_evaluation.py --mode quick --no-hybrid
```

### Python API Usage

```python
from evaluation.pipeline import EvaluationPipeline
from evaluation.metrics import RAGEvaluator

# Run comprehensive evaluation
pipeline = EvaluationPipeline(use_hybrid_search=True)
results = pipeline.run_comprehensive_evaluation(sample_size=20)

# Print summary
print(f"Overall Performance: {results['performance_analysis']['overall_performance']}")
print(f"Faithfulness: {results['aggregate_scores']['faithfulness']:.3f}")
print(f"Answer Relevancy: {results['aggregate_scores']['answer_relevancy']:.3f}")

# Evaluate single response
evaluator = RAGEvaluator()
result = evaluator.evaluate_response(
    query="What is COMP9900?",
    generated_answer="COMP9900 is a capstone project course...",
    retrieved_contexts=["COMP9900 course description", "Project requirements"],
    ground_truth_answer="Expected answer for comparison"
)
```

### Admin API Usage

The evaluation system integrates with the existing admin interface:

```bash
# Check evaluation system status
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/admin/evaluation/status

# Create evaluation datasets
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"sample_size": 50}' \
     http://localhost:5000/api/admin/evaluation/datasets/create

# Run comprehensive evaluation
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"sample_size": 20, "use_hybrid_search": true}' \
     http://localhost:5000/api/admin/evaluation/run

# Get evaluation results
curl -H "Authorization: Bearer <token>" \
     http://localhost:5000/api/admin/evaluation/results

# Get evaluation summary
curl -H "Authorization: Bearer <token>" \
     http://localhost:5000/api/admin/evaluation/summary
```

## Evaluation Metrics Explained

### Faithfulness Score (0-1)
- **Measures**: How factually accurate the answer is based on retrieved context
- **Good**: >0.8 | **Acceptable**: 0.7-0.8 | **Poor**: <0.7
- **Improvement**: Enhance context relevance, reduce hallucinations

### Answer Relevancy Score (0-1)  
- **Measures**: How well the answer addresses the original question
- **Good**: >0.8 | **Acceptable**: 0.7-0.8 | **Poor**: <0.7
- **Improvement**: Better query understanding, more focused responses

### Context Recall Score (0-1)
- **Measures**: How well the retrieval covers all relevant information
- **Good**: >0.8 | **Acceptable**: 0.7-0.8 | **Poor**: <0.7  
- **Improvement**: Increase retrieval diversity, improve embeddings

### Context Precision Score (0-1)
- **Measures**: Signal-to-noise ratio of retrieved contexts
- **Good**: >0.8 | **Acceptable**: 0.7-0.8 | **Poor**: <0.7
- **Improvement**: Better ranking, reduce irrelevant retrievals

## Performance Benchmarking

### Run Benchmark Suite

```bash
python scripts/evaluation_benchmark.py
```

This runs:
1. **Configuration Comparison**: Hybrid vs Semantic search
2. **Category Analysis**: Performance across different query types  
3. **Regression Testing**: Compare against baseline performance

### Baseline Management

Save current results as baseline for future regression testing:

```bash
# Run evaluation and save as baseline
python scripts/run_evaluation.py --mode full --sample-size 30 --save-results
cp evaluation_results_*.json data/evaluation/baseline_results.json
```

## File Structure

```
backend/evaluation/
├── __init__.py           # Module initialization
├── config.py             # Configuration and thresholds
├── datasets.py           # Ground truth and test data management  
├── metrics.py            # RAGAS evaluation implementation
├── pipeline.py           # Automated evaluation workflows
└── README.md            # This file

backend/scripts/
├── run_evaluation.py     # Standalone evaluation script
└── evaluation_benchmark.py # Performance benchmarking

backend/test/unit/test_evaluation/
├── test_datasets.py      # Dataset creation tests
├── test_metrics.py       # RAGAS metrics tests  
└── test_pipeline.py      # Pipeline integration tests

data/evaluation/
├── ground_truth.json     # UNSW-specific Q&A pairs
├── test_queries.json     # Generated test queries
└── results/              # Evaluation results storage
```

## Integration with Existing System

The evaluation system seamlessly integrates with your existing RAG pipeline:

- **Uses existing search engines**: Vector store, hybrid search, BM25
- **Leverages existing query processing**: Query enhancement, safety checking
- **Integrates with admin interface**: API endpoints for web-based evaluation
- **Follows existing patterns**: Same logging, error handling, configuration

## Common Use Cases

### Development Workflow

1. **Before changes**: Run baseline evaluation
2. **After changes**: Run new evaluation  
3. **Compare results**: Use benchmark script to detect regressions
4. **Iterate**: Improve based on specific metric feedback

### Production Monitoring

1. **Weekly evaluations**: Track performance trends over time
2. **A/B testing**: Compare different configurations
3. **Category analysis**: Identify weak areas needing improvement
4. **Alert on regressions**: Automated performance monitoring

### Research & Optimization

1. **Parameter tuning**: Test different retrieval settings
2. **Algorithm comparison**: Hybrid vs semantic vs keyword search
3. **Quality assessment**: Objective measurement for academic presentation
4. **Data-driven decisions**: Use metrics to guide improvements

## Troubleshooting

### Common Issues

**ImportError: No module named 'ragas'**
```bash
pip install ragas==0.1.21 datasets==2.20.0
```

**No evaluation datasets found**
```bash
python scripts/run_evaluation.py --setup-datasets
```

**RAGAS API timeout errors**  
- Reduce batch size in config.py
- Check internet connection (RAGAS uses external LLM)
- Increase timeout in RAGAS_CONFIG

**Empty evaluation results**
- Ensure vector store is populated
- Check if RAG system is responding correctly
- Verify test queries are appropriate

### Performance Tips

- Start with small sample sizes (10-20) for testing
- Use `--mode quick` for faster iterations
- Run comprehensive evaluations during low-usage periods
- Cache results to avoid re-evaluation of same queries

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check system status before evaluation
from evaluation.pipeline import EvaluationPipeline
pipeline = EvaluationPipeline()
# Check if datasets exist, RAGAS available, etc.
```

## Contributing

When adding new evaluation features:

1. Add comprehensive unit tests in `test/unit/test_evaluation/`
2. Update this README with new functionality
3. Follow existing code patterns and error handling
4. Test with small samples first before large evaluations

## Performance Expectations

### Timing
- **Single query evaluation**: ~3-10 seconds
- **Quick evaluation (10 queries)**: ~1-2 minutes  
- **Full evaluation (50 queries)**: ~5-15 minutes
- **Category analysis**: ~10-20 minutes
- **A/B testing**: ~5-10 minutes

### Accuracy
- **Good RAG systems**: Avg scores >0.8 across metrics
- **Acceptable systems**: Avg scores >0.7 across metrics  
- **Needs improvement**: Avg scores <0.7 across metrics

The evaluation system provides objective, research-grade measurement of your RAG system's performance, enabling data-driven optimization and continuous quality improvement.