#!/bin/bash
set -e

echo "Setting up Tesla Powerwall Management System..."

# Check if we're in the right directory
if [ ! -f "manage_power_clean.py" ]; then
    echo "Error: Please run this script from the Tesla directory"
    exit 1
fi

# Navigate to project root (ext_lib needs to be created here)
cd ..

echo "Installing dependencies..."
uv sync

echo "Creating ext_lib directory structure..."
mkdir -p ext_lib

echo "Cloning TeslaPy..."
if [ -d "ext_lib/TeslaPy" ]; then
    echo "TeslaPy already exists, updating..."
    cd ext_lib/TeslaPy
    git pull
    cd ../..
else
    cd ext_lib
    git clone https://github.com/tdorssers/TeslaPy.git TeslaPy
    cd ..
fi

echo "Installing TeslaPy dependencies..."
uv add geopy requests-oauthlib websocket_client selenium pywebview

echo "Setting up Constants configuration..."
if [ ! -f "lib/Constants.py" ]; then
    if [ -f "lib/Constants.py.sample" ]; then
        cp lib/Constants.py.sample lib/Constants.py
        echo "Created lib/Constants.py from template"
        echo "⚠️  Please edit lib/Constants.py with your Tesla API credentials and settings"
    else
        echo "Warning: lib/Constants.py.sample not found"
    fi
else
    echo "lib/Constants.py already exists"
fi

echo "Verifying setup..."
if [ -d "ext_lib/TeslaPy" ] && [ -f "ext_lib/TeslaPy/teslapy/__init__.py" ]; then
    echo "✅ TeslaPy successfully installed"
else
    echo "❌ TeslaPy installation failed"
    exit 1
fi

if [ -f "lib/Constants.py" ]; then
    echo "✅ Constants.py configured"
else
    echo "❌ Constants.py missing"
    exit 1
fi

echo ""
echo "Setup complete! Next steps:"
echo "1. Edit lib/Constants.py with your Tesla credentials and settings"
echo "2. Authenticate with Tesla by running (from Tesla directory):"
echo "   cd ../ext_lib/TeslaPy && python gui.py"
echo "3. Test the system with (from Tesla directory):"
echo "   uv run python manage_power_clean.py --dry-run"