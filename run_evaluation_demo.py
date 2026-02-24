#!/usr/bin/env python3
"""
Quick evaluation runner - run this script to start RAG evaluation
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import ragas
        print("✅ RAGAS available")
    except ImportError:
        print("❌ RAGAS not found")
        return False
        
    try:
        import datasets
        print("✅ Datasets available")
    except ImportError:
        print("❌ Datasets not found")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing RAGAS and datasets...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "ragas==0.1.21", "datasets==2.20.0"
        ])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_evaluation():
    """Run the evaluation"""
    print("🚀 Starting RAG evaluation...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    # First, setup datasets
    print("1️⃣ Setting up evaluation datasets...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/run_evaluation.py", 
            "--setup-datasets", "--sample-size", "20"
        ], cwd=backend_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Datasets created successfully")
        else:
            print("⚠️ Dataset creation had issues:")
            print(result.stdout)
            print(result.stderr)
    except Exception as e:
        print(f"❌ Dataset setup failed: {e}")
        return False
    
    # Run quick evaluation
    print("2️⃣ Running quick evaluation...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/run_evaluation.py",
            "--mode", "quick", "--sample-size", "5"
        ], cwd=backend_dir)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return False

def main():
    print("🎯 RAG Evaluation Quick Start")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not (Path("backend").exists() and Path("backend/scripts/run_evaluation.py").exists()):
        print("❌ Please run this script from the project root directory")
        print("💡 Current directory should contain 'backend/scripts/run_evaluation.py'")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        print("\n📦 Installing required dependencies...")
        if not install_dependencies():
            print("\n❌ Failed to install dependencies")
            print("💡 Try manually: pip install ragas==0.1.21 datasets==2.20.0")
            return 1
        
        # Check again after installation
        if not check_dependencies():
            print("❌ Dependencies still not available after installation")
            return 1
    
    # Run evaluation
    print("\n🚀 Running evaluation...")
    if run_evaluation():
        print("\n🎉 Evaluation completed successfully!")
        print("\n📊 For more options, try:")
        print("  python backend/scripts/run_evaluation.py --mode full --sample-size 20")
        print("  python backend/scripts/run_evaluation.py --mode category")
        print("  python backend/scripts/run_evaluation.py --mode ab-test")
        return 0
    else:
        print("\n❌ Evaluation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())