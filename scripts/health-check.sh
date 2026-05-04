#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Sentinel RAG - Health Check
# =============================================================================

echo "=== Sentinel RAG Health Check ==="
echo "Date: $(date)"
echo ""

# Container status
echo "--- Container Status ---"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
echo ""

# API readiness
echo "--- API Readiness ---"
curl -sf http://localhost:8000/api/v1/health/ready 2>/dev/null | python3 -m json.tool || echo "API unreachable"
echo ""

# Disk usage
echo "--- Disk Usage ---"
df -h / | tail -1
echo ""
docker system df
echo ""

# Memory
echo "--- Memory ---"
free -h
echo ""

echo "=== Check Complete ==="
