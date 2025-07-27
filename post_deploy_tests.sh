#!/bin/bash
# Post-deployment validation script
# Runs all integration tests after deployment

echo "=================================================="
echo "POST-DEPLOYMENT VALIDATION"
echo "=================================================="
echo "Date: $(date)"
echo "Server: gtmcp-mcp"
echo ""

# Check if server is running
if systemctl is-active --quiet gtmcp-mcp; then
    echo "✅ MCP server is running"
else
    echo "❌ MCP server is not running!"
    echo "Starting server..."
    sudo systemctl start gtmcp-mcp
    sleep 3
fi

echo ""
echo "Running integration tests..."
echo ""

# Run integration tests
./test_suite.py --post-deploy

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ POST-DEPLOYMENT VALIDATION PASSED"
    echo "=================================================="
    echo "Server is ready for production use!"
else
    echo ""
    echo "=================================================="
    echo "❌ POST-DEPLOYMENT VALIDATION FAILED"
    echo "=================================================="
    echo "Please investigate failures before using in production!"
fi

exit $EXIT_CODE