#!/bin/bash
# Setup script for Talenta API Python version

echo "🚀 Setting up Talenta API (Python)..."
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Installing uv..."
    echo ""

    # Install uv using the official installer
    curl -LsSf https://astral.sh/uv/install.sh | sh

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install uv."
        echo "Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    # Source the cargo environment to make uv available
    source $HOME/.cargo/env

    echo "✅ uv installed successfully"
else
    echo "✅ uv is available ($(uv --version))"
fi

echo ""

# Create virtual environment with uv
echo "Creating virtual environment with uv..."
uv venv venv --python 3.11

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
fi

echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies with uv
echo "Installing dependencies with uv..."
uv pip install -r pyproject.toml

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Copy config template if not exists
if [ ! -f "src/config/config_local.py" ]; then
    echo "Creating src/config/config_local.py..."
    echo "✅ Please edit src/config/config_local.py and add your credentials"
else
    echo "ℹ️  src/config/config_local.py already exists, skipping..."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit src/config/config_local.py and add your credentials"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run clock in: python -m src.cli.execute clockin"
echo "4. Run clock out: python -m src.cli.execute clockout"
echo "5. Run scheduler: python -m src.cli.scheduler"
echo ""
