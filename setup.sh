#!/bin/bash
# Setup script for Talenta API Python version
# Uses uv for fast package management

echo "🚀 Setting up Talenta API (Python with uv)..."
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Please install manually: https://github.com/astral-sh/uv"
        exit 1
    fi

    echo "✅ uv installed successfully"
else
    echo "✅ uv is already installed ($(uv --version))"
fi

echo ""

# Create virtual environment with uv
echo "Creating virtual environment with uv..."
uv venv venv

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
uv pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Copy config template if not exists
if [ ! -f "config_local.py" ]; then
    echo "Creating config_local.py from template..."
    cp config.py config_local.py
    echo "✅ Please edit config_local.py and add your credentials"
else
    echo "ℹ️  config_local.py already exists, skipping..."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config_local.py and add your credentials"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run clock in: python execute.py clockin"
echo "4. Run clock out: python execute.py clockout"
echo "5. Run scheduler: python scheduler.py"
echo ""
