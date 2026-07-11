#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "========================================"
echo "  BrainWise Logistics - Database Seed"
echo "========================================"
echo ""

# Navigate to backend
cd "$BACKEND_DIR"

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q 2>/dev/null

# Run migrations
echo "Running migrations..."
python manage.py migrate --verbosity 0

# Seed the database
echo ""
python manage.py seed_data --clear

echo ""
echo "Setup complete! Start the servers with:"
echo "  Backend:   cd backend && source .venv/bin/activate && python manage.py runserver"
echo "  Frontend:  cd frontend && npm run dev"
