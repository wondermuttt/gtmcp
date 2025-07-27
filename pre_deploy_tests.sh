#!/bin/bash
# Pre-deployment test script
# Runs all unit tests before deployment

echo "=================================================="
echo "PRE-DEPLOYMENT TESTS"
echo "=================================================="
echo "Date: $(date)"
echo "Running unit tests..."
echo ""

# Run unit tests
./test_suite.py --pre-deploy

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ PRE-DEPLOYMENT TESTS PASSED"
    echo "=================================================="
    echo "Ready for deployment!"
else
    echo ""
    echo "=================================================="
    echo "❌ PRE-DEPLOYMENT TESTS FAILED" 
    echo "=================================================="
    echo "Please fix failing tests before deployment!"
fi

exit $EXIT_CODE