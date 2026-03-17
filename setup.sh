#!/usr/bin/env bash
# setup.sh — First-time setup for Personal Knowledge Base
set -e

echo "📚 Personal Knowledge Base — Setup"
echo "==================================="

# Check Python version
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Create virtualenv
echo ""
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -U pip
pip install -r requirements.txt

# Download spaCy transformer model
echo ""
echo "Downloading spaCy NER model (en_core_web_trf)..."
python -m spacy download en_core_web_trf

# Set up .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Created .env from template. Please edit it:"
    echo "  1. Set DISCORD_BOT_TOKEN"
    echo "  2. Optionally set X_BEARER_TOKEN for full Twitter thread support"
else
    echo "✅ .env already exists"
fi

# Create data directory
mkdir -p data

# Initialize database
echo ""
echo "Initializing SQLite database..."
python -c "
import sys; sys.path.insert(0, '.')
from kb.database import init_db
init_db()
print('✅ Database initialized at data/knowledge.db')
"

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your DISCORD_BOT_TOKEN"
echo "  2. Activate venv: source .venv/bin/activate"
echo "  3. Run the bot: python bot.py"
echo "  4. Or query directly: python query.py \"your question\""
echo ""
echo "Discord bot commands:"
echo "  Drop a URL → auto-ingest"
echo "  Upload a PDF → auto-ingest"
echo "  !ask <query> → semantic search"
echo "  !entity <name> → find by entity"
echo "  !recent → show recent"
echo "  !stats → KB stats"
