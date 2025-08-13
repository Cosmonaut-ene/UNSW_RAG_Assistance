#!/bin/bash
# Simple test runner script for UNSW CSE Chatbot Backend Tests

echo "🧪 UNSW CSE Chatbot Backend Test Suite"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker image name
IMAGE_NAME="capstone-project-25t2-9900-f10a-almond-backend"

echo -e "${BLUE}📦 Checking Docker image...${NC}"
if ! docker images | grep -q "$IMAGE_NAME"; then
    echo -e "${YELLOW}🔧 Building Docker image...${NC}"
    docker-compose -f docker-compose.dev.yml build backend
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Docker image build failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Docker image ready${NC}"

# Simple test runner function
run_tests() {
    local test_path="$1"
    local description="$2"
    
    echo -e "${BLUE}🔄 $description${NC}"
    
    docker run --rm \
        -v "$(pwd)/backend:/app" \
        --workdir /app \
        -e KNOWLEDGE_BASE_ROOT="/tmp/test_data" \
        -e ADMIN_PASSWORD="test-password" \
        -e SECRET_KEY="test-secret-key" \
        -e GOOGLE_API_KEY="test-api-key" \
        "$IMAGE_NAME" \
        sh -c 'pip install --user -r test/requirements-test.txt > /dev/null 2>&1 && export PATH=/home/appuser/.local/bin:$PATH && python -m pytest '"$test_path"' -v --tb=short'
}

# Test options
case "${1:-all}" in
    "prompt")
        run_tests "test/unit/test_ai/test_prompt_manager.py" "Running AI Prompt Manager tests"
        ;;
    "auth")
        run_tests "test/unit/test_services/test_auth.py" "Running Authentication Service tests"
        ;;
    "ai")
        run_tests "test/unit/test_ai/" "Running all AI module tests"
        ;;
    "services")
        run_tests "test/unit/test_services/" "Running all Service layer tests"
        ;;
    "unit")
        run_tests "test/unit/" "Running all Unit tests"
        ;;
    "coverage")
        echo -e "${BLUE}📊 Running tests with coverage report${NC}"
        docker run --rm \
            -v "$(pwd)/backend:/app" \
            --workdir /app \
            -e KNOWLEDGE_BASE_ROOT="/tmp/test_data" \
            -e ADMIN_PASSWORD="test-password" \
            -e SECRET_KEY="test-secret-key" \
            -e GOOGLE_API_KEY="test-api-key" \
            "$IMAGE_NAME" \
            sh -c 'pip install --user -r test/requirements-test.txt > /dev/null 2>&1 && export PATH=/home/appuser/.local/bin:$PATH && python -m pytest test/unit/test_ai/test_prompt_manager.py test/unit/test_services/test_auth.py --cov=ai --cov=services --cov-report=term-missing'
        ;;
    "quick")
        echo -e "${BLUE}⚡ Running quick verification tests${NC}"
        run_tests "test/unit/test_ai/test_prompt_manager.py -k 'test_get_rag_prompt_template_structure or test_rag_prompt_template_rendering'" "Running core functionality tests"
        ;;
    "all"|*)
        echo -e "${BLUE}🎯 Running complete test suite${NC}"
        echo -e "${YELLOW}⏰ This may take a few minutes...${NC}"
        run_tests "test/unit/" "Running all unit tests"
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Testing complete!${NC}"
echo ""
echo "💡 Usage:"
echo "  ./run-tests.sh              # Run all tests"  
echo "  ./run-tests.sh quick        # Run quick verification tests"
echo "  ./run-tests.sh prompt       # Run prompt manager tests"
echo "  ./run-tests.sh auth         # Run authentication tests"
echo "  ./run-tests.sh ai           # Run AI module tests"
echo "  ./run-tests.sh services     # Run service layer tests"
echo "  ./run-tests.sh coverage     # Run tests with coverage report"