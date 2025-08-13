#!/usr/bin/env python3
"""
Test runner script for UNSW CSE Chatbot Backend
Installs test dependencies and runs the complete test suite
"""

import subprocess
import sys
import os

def install_test_dependencies():
    """Install testing dependencies"""
    print("📦 Installing test dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "test/requirements-test.txt"
        ], check=True)
        print("✅ Test dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install test dependencies: {e}")
        return False

def run_tests():
    """Run the complete test suite"""
    print("🧪 Running test suite...")
    
    # Test commands to try in order of preference
    test_commands = [
        # Full test suite with coverage
        [sys.executable, "-m", "pytest", "test/", "--cov=ai", "--cov=rag", "--cov=services", "--cov=routes", "--cov-report=html", "--cov-report=term-missing", "-v"],
        
        # Fallback: Run tests without coverage
        [sys.executable, "-m", "pytest", "test/", "-v"],
        
        # Fallback: Run only unit tests
        [sys.executable, "-m", "pytest", "test/unit/", "-v"],
        
        # Final fallback: Run individual test files
        [sys.executable, "-m", "pytest", "test/unit/test_ai/test_prompt_manager.py", "-v"]
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        try:
            print(f"🔄 Attempting test run #{i}: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=os.getcwd())
            
            if result.returncode == 0:
                print(f"✅ Test run #{i} completed successfully!")
                return True
            else:
                print(f"⚠️ Test run #{i} failed with return code {result.returncode}")
                
        except FileNotFoundError:
            print(f"❌ Test run #{i} failed: pytest not found")
        except Exception as e:
            print(f"❌ Test run #{i} failed with error: {e}")
            
    print("❌ All test runs failed")
    return False

def check_python_version():
    """Check if Python version is compatible"""
    print(f"🐍 Python version: {sys.version}")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required for testing")
        return False
    
    print("✅ Python version is compatible")
    return True

def main():
    """Main test runner"""
    print("🎯 UNSW CSE Chatbot Backend Test Suite")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_test_dependencies():
        print("⚠️ Continuing without installing dependencies (they might already be installed)")
    
    # Run tests
    if run_tests():
        print("\n🎉 Tests completed successfully!")
        print("\n📊 Coverage Report:")
        print("- HTML report available at: htmlcov/index.html")
        print("- Open in browser to see detailed coverage")
        sys.exit(0)
    else:
        print("\n💡 Test Troubleshooting:")
        print("1. Ensure you're in the backend directory")
        print("2. Try running: python -m pip install pytest")
        print("3. Run individual tests: python -m pytest test/unit/test_ai/test_prompt_manager.py -v")
        print("4. Check the test README: test/README.md")
        sys.exit(1)

if __name__ == "__main__":
    main()