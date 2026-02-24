#!/usr/bin/env python3
"""
Docker-based RAG evaluation script with 30-query test set
Usage: python docker-evaluation.py
"""

import subprocess
import json
import time
import sys
from pathlib import Path

def check_docker_running():
    """Check if Docker is running"""
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def start_services():
    """Start Docker services"""
    print("🐳 Starting Docker services...")
    try:
        # Build and start services
        result = subprocess.run([
            "docker-compose", "up", "-d", "--build"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to start services: {result.stderr}")
            return False
        
        print("✅ Services started successfully")
        
        # Wait for services to be ready
        print("⏳ Waiting for services to be ready...")
        time.sleep(30)  # Give services time to start
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting services: {e}")
        return False

def check_service_health():
    """Check if services are healthy"""
    print("🏥 Checking service health...")
    
    try:
        # Check backend health
        result = subprocess.run([
            "curl", "-f", "http://localhost:3001/api/admin/health"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Backend service is healthy")
            return True
        else:
            print("⚠️ Backend service not ready, checking container logs...")
            # Show container logs
            subprocess.run(["docker-compose", "logs", "--tail=10", "backend"])
            return False
            
    except Exception as e:
        print(f"⚠️ Health check failed: {e}")
        return False

def run_evaluation_in_container():
    """Run evaluation inside the Docker container"""
    print("🚀 Running RAG evaluation with 30 queries in Docker container...")
    
    # Create evaluation command
    eval_commands = [
        # Install evaluation dependencies
        "pip install ragas==0.1.21 datasets==2.20.0",
        
        # Setup evaluation datasets with 30 queries
        "python scripts/run_evaluation.py --setup-datasets --sample-size 30",
        
        # Run comprehensive evaluation
        "python scripts/run_evaluation.py --mode full --sample-size 30 --save-results"
    ]
    
    for i, cmd in enumerate(eval_commands, 1):
        print(f"📋 Step {i}/3: {cmd}")
        
        try:
            result = subprocess.run([
                "docker-compose", "exec", "-T", "backend", "bash", "-c", cmd
            ], text=True, timeout=300)  # 5 minute timeout per command
            
            if result.returncode != 0:
                print(f"❌ Command failed: {cmd}")
                return False
            
            print(f"✅ Step {i} completed")
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Command timed out: {cmd}")
            return False
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False
    
    return True

def run_additional_evaluations():
    """Run additional evaluation modes"""
    print("📊 Running additional evaluation analyses...")
    
    additional_commands = [
        # Category analysis
        ("Category Analysis", "python scripts/run_evaluation.py --mode category"),
        
        # A/B test
        ("A/B Test (Hybrid vs Semantic)", "python scripts/run_evaluation.py --mode ab-test --sample-size 15"),
        
        # Performance benchmark
        ("Performance Benchmark", "python scripts/evaluation_benchmark.py")
    ]
    
    for name, cmd in additional_commands:
        print(f"🔍 Running {name}...")
        
        try:
            result = subprocess.run([
                "docker-compose", "exec", "-T", "backend", "bash", "-c", cmd
            ], text=True, timeout=600)  # 10 minute timeout
            
            if result.returncode == 0:
                print(f"✅ {name} completed successfully")
            else:
                print(f"⚠️ {name} had issues (continuing...)")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {name} timed out (continuing...)")
        except Exception as e:
            print(f"❌ Error in {name}: {e}")

def get_evaluation_results():
    """Retrieve evaluation results from container"""
    print("📋 Retrieving evaluation results...")
    
    try:
        # Get evaluation summary
        result = subprocess.run([
            "docker-compose", "exec", "-T", "backend", "bash", "-c",
            "python -c \"from evaluation.pipeline import EvaluationPipeline; p = EvaluationPipeline(); r = p.get_latest_results(); print('Results available:', r is not None)\""
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Results retrieved successfully")
            print(result.stdout)
        else:
            print("⚠️ Could not retrieve results summary")
            
    except Exception as e:
        print(f"❌ Error retrieving results: {e}")

def show_evaluation_api():
    """Show how to access evaluation results via API"""
    print("\n📡 Access evaluation results via API:")
    print("="*50)
    
    print("1. Get admin token:")
    print("curl -X POST http://localhost:3001/api/admin/login \\")
    print("  -H 'Content-Type: application/json' \\") 
    print("  -d '{\"email\": \"admin@unsw.edu.au\", \"password\": \"unswcse2025\"}'")
    
    print("\n2. Check evaluation status:")
    print("curl -H 'Authorization: Bearer <token>' \\")
    print("  http://localhost:3001/api/admin/evaluation/status")
    
    print("\n3. Get evaluation summary:")
    print("curl -H 'Authorization: Bearer <token>' \\")
    print("  http://localhost:3001/api/admin/evaluation/summary")
    
    print("\n4. Get detailed results:")
    print("curl -H 'Authorization: Bearer <token>' \\")
    print("  http://localhost:3001/api/admin/evaluation/results")

def main():
    print("🎯 Docker RAG Evaluation with 30-Query Test Set")
    print("="*60)
    
    # Check Docker
    if not check_docker_running():
        print("❌ Docker is not running. Please start Docker first.")
        return 1
    
    print("✅ Docker is running")
    
    # Start services
    if not start_services():
        print("❌ Failed to start Docker services")
        return 1
    
    # Wait and check health
    retry_count = 0
    max_retries = 6
    
    while retry_count < max_retries:
        if check_service_health():
            break
        
        retry_count += 1
        print(f"⏳ Waiting for services... (attempt {retry_count}/{max_retries})")
        time.sleep(15)
    
    if retry_count >= max_retries:
        print("❌ Services did not become healthy in time")
        print("💡 Try: docker-compose logs backend")
        return 1
    
    # Run evaluation
    if not run_evaluation_in_container():
        print("❌ Evaluation failed")
        return 1
    
    # Run additional analyses
    run_additional_evaluations()
    
    # Get results
    get_evaluation_results()
    
    # Show API access
    show_evaluation_api()
    
    print("\n🎉 Docker-based RAG evaluation completed!")
    print("📊 Check the container logs for detailed results:")
    print("   docker-compose logs backend | grep -A 20 'EVALUATION RESULTS'")
    
    print("\n🌐 Access via web interface:")
    print("   Frontend: http://localhost:8080/admin")
    print("   Backend API: http://localhost:3001/api/admin/evaluation/")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ Evaluation interrupted by user")
        print("🛑 To stop services: docker-compose down")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)