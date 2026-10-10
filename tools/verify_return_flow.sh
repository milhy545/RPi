#!/usr/bin/env bash
# Verification script for return-to-dashboard flow

set -euo pipefail

echo "=== Return Service Flow Verification ==="
echo "1. Checking return service endpoints in python API..."
uv run python -c "from rpi_dashboard.services import return_service; print('Return service config:', return_service.get_config())"

echo "2. Verifying return telemetry state..."
uv run python -c "from rpi_dashboard.services import return_service; return_service.return_to_dashboard(reason='verification_script', source='verify_return_flow.sh'); print('Last return:', return_service.get_last_return())"

echo "3. Running return service unit tests..."
uv run pytest tests/test_return_service.py -q

echo "=== Return Flow Verification Complete ==="
