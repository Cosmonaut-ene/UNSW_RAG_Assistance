#!/usr/bin/env python3
"""
Retrieval parameter tuner entry point.

Usage:
  python scripts/run_tuner.py --mode random [--n 50]
  python scripts/run_tuner.py --mode grid
  python scripts/run_tuner.py --mode validate [--top 5] [--sample-size 30]
"""

import argparse
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieval parameter tuner")
    parser.add_argument(
        "--mode",
        choices=["random", "grid", "validate"],
        required=True,
        help="Tuning mode",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=50,
        help="Number of random trials (--mode random only)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top configs to validate (--mode validate only)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Query sample size for RAGAS validation",
    )
    args = parser.parse_args()

    from evaluation.retrieval_tuner import TunerOrchestrator

    tuner = TunerOrchestrator()

    if args.mode == "random":
        print(f"=== Phase 1: Random Search ({args.n} trials) ===")
        tuner.run_random_search(n=args.n)

    elif args.mode == "grid":
        print("=== Phase 2: Focused Grid Search ===")
        tuner.run_focused_search()

    elif args.mode == "validate":
        print(f"=== Phase 3: RAGAS Validation (top {args.top}, sample={args.sample_size}) ===")
        tuner.run_ragas_validation(top_k=args.top, sample_size=args.sample_size)

    return 0


if __name__ == "__main__":
    sys.exit(main())
